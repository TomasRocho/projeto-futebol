from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col, select

from app.auth import require_admin
from app.db import SessionDep, get_or_404
from app.estatisticas import estatisticas_jogador
from app.models import Jogador
from app.schemas import JogadorCreate, JogadorDetalhe, JogadorPublic, JogadorUpdate

router = APIRouter(prefix="/jogadores", tags=["jogadores"])
admin = [Depends(require_admin)]


def _buscar(session: Session, jogador_id: int) -> Jogador:
    return get_or_404(session, Jogador, jogador_id, "Jogador não encontrado")


@router.get("", response_model=list[JogadorPublic])
def listar(session: SessionDep):
    return session.exec(select(Jogador).order_by(col(Jogador.nome))).all()


@router.post(
    "", response_model=JogadorPublic, status_code=status.HTTP_201_CREATED, dependencies=admin
)
def criar(dados: JogadorCreate, session: SessionDep):
    jogador = Jogador(**dados.model_dump())
    session.add(jogador)
    session.commit()
    session.refresh(jogador)
    return jogador


@router.get("/{jogador_id}", response_model=JogadorDetalhe)
def detalhe(jogador_id: int, session: SessionDep):
    jogador = _buscar(session, jogador_id)
    return JogadorDetalhe(
        id=jogador_id,
        nome=jogador.nome,
        rating=jogador.rating,
        estatisticas=estatisticas_jogador(session, jogador_id),
    )


@router.patch("/{jogador_id}", response_model=JogadorPublic, dependencies=admin)
def editar(jogador_id: int, dados: JogadorUpdate, session: SessionDep):
    jogador = _buscar(session, jogador_id)
    jogador.sqlmodel_update(dados.model_dump(exclude_unset=True))
    session.add(jogador)
    session.commit()
    session.refresh(jogador)
    return jogador


@router.delete("/{jogador_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=admin)
def remover(jogador_id: int, session: SessionDep) -> None:
    jogador = _buscar(session, jogador_id)
    session.delete(jogador)
    try:
        session.commit()
    except IntegrityError:  # RESTRICT: tem presença/escalação
        session.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Jogador tem histórico (presença ou partidas) e não pode ser apagado"
        ) from None
