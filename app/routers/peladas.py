from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, func, select

from app.auth import require_admin
from app.db import SessionDep, get_or_404
from app.estado import estado_pelada
from app.models import Jogador, Pelada, Presenca, Time
from app.schemas import (
    PeladaCreate,
    PeladaEstado,
    PeladaPublic,
    PresencaCreate,
    PresencasDefinir,
    PresencaUpdate,
)

router = APIRouter(prefix="/peladas", tags=["peladas"])
admin = [Depends(require_admin)]


def _buscar(session: Session, pelada_id: int) -> Pelada:
    return get_or_404(session, Pelada, pelada_id, "Pelada não encontrada")


def _buscar_presenca(session: Session, pelada_id: int, jogador_id: int) -> Presenca:
    return get_or_404(
        session,
        Presenca,
        {"pelada_id": pelada_id, "jogador_id": jogador_id},
        "Jogador não está nesta pelada",
    )


def _ja_sorteada(session: Session, pelada_id: int) -> bool:
    return session.exec(select(Time.id).where(Time.pelada_id == pelada_id)).first() is not None


# --- Pelada ---


@router.get("", response_model=list[PeladaPublic])
def listar(session: SessionDep):
    return session.exec(
        select(Pelada).order_by(col(Pelada.data).desc(), col(Pelada.id).desc())
    ).all()


@router.post(
    "", response_model=PeladaPublic, status_code=status.HTTP_201_CREATED, dependencies=admin
)
def criar(dados: PeladaCreate, session: SessionDep):
    pelada = Pelada(**dados.model_dump())
    session.add(pelada)
    session.commit()
    session.refresh(pelada)
    return pelada


@router.get("/{pelada_id}", response_model=PeladaEstado)
def estado(pelada_id: int, session: SessionDep):
    return estado_pelada(session, _buscar(session, pelada_id))


@router.delete("/{pelada_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=admin)
def remover(pelada_id: int, session: SessionDep) -> None:
    session.delete(_buscar(session, pelada_id))  # CASCADE leva equipes, presenças, partidas...
    session.commit()


# --- Presenças ---


@router.put("/{pelada_id}/presencas", response_model=PeladaEstado, dependencies=admin)
def definir_presencas(pelada_id: int, dados: PresencasDefinir, session: SessionDep):
    """Substitui a lista de presentes. Só antes do sorteio (depois, use POST/DELETE)."""
    pelada = _buscar(session, pelada_id)
    if _ja_sorteada(session, pelada_id):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Pelada já sorteada: use POST/DELETE em /presencas para quem chegou ou saiu",
        )

    ids = set(dados.jogador_ids)
    existentes = set(session.exec(select(Jogador.id).where(col(Jogador.id).in_(ids))).all())
    if faltando := sorted(ids - existentes):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Jogadores não encontrados: {faltando}"
        )

    for presenca in session.exec(select(Presenca).where(Presenca.pelada_id == pelada_id)).all():
        session.delete(presenca)
    session.flush()
    session.add_all(Presenca(pelada_id=pelada_id, jogador_id=jid) for jid in ids)
    session.commit()
    return estado_pelada(session, pelada)


@router.post(
    "/{pelada_id}/presencas",
    response_model=PeladaEstado,
    status_code=status.HTTP_201_CREATED,
    dependencies=admin,
)
def adicionar_presenca(pelada_id: int, dados: PresencaCreate, session: SessionDep):
    """Quem chega (inclusive atrasado) entra como esperando."""
    pelada = _buscar(session, pelada_id)
    if session.get(Jogador, dados.jogador_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Jogador não encontrado")
    if session.get(Presenca, {"pelada_id": pelada_id, "jogador_id": dados.jogador_id}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Jogador já está nesta pelada")

    session.add(Presenca(pelada_id=pelada_id, jogador_id=dados.jogador_id))
    session.commit()
    return estado_pelada(session, pelada)


@router.patch(
    "/{pelada_id}/presencas/{jogador_id}", response_model=PeladaEstado, dependencies=admin
)
def mover_jogador(pelada_id: int, jogador_id: int, dados: PresencaUpdate, session: SessionDep):
    """Move o jogador de equipe (null = esperando). A escalação da partida em andamento não muda."""
    pelada = _buscar(session, pelada_id)
    presenca = _buscar_presenca(session, pelada_id, jogador_id)

    if dados.equipe_id is not None and dados.equipe_id != presenca.equipe_id:
        equipe = session.get(Time, dados.equipe_id)
        if equipe is None or equipe.pelada_id != pelada_id:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Equipe não pertence a esta pelada"
            )
        tamanho = session.exec(
            select(func.count()).select_from(Presenca).where(Presenca.equipe_id == equipe.id)
        ).one()
        if tamanho >= pelada.jogadores_por_time:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Equipe {equipe.nome} já está cheia")

    presenca.equipe_id = dados.equipe_id
    session.add(presenca)
    session.commit()
    return estado_pelada(session, pelada)


@router.delete(
    "/{pelada_id}/presencas/{jogador_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=admin,
)
def remover_presenca(pelada_id: int, jogador_id: int, session: SessionDep) -> None:
    """Jogador foi embora. A equipe dele fica com um a menos (sem reposição)."""
    _buscar(session, pelada_id)
    session.delete(_buscar_presenca(session, pelada_id, jogador_id))
    session.commit()
