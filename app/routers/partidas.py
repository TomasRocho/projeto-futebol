from collections import Counter, defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, col, func, select

from app.auth import require_admin
from app.db import SessionDep, get_or_404
from app.estado import estado_pelada
from app.estatisticas import placares
from app.models import Escalacao, Gol, Jogador, Partida, Pelada, Presenca, Time
from app.rodizio import aplicar_rodizio, placar
from app.schemas import (
    EncerrarPartida,
    EquipePartida,
    EquipePlacar,
    GolCreate,
    GolPublic,
    JogadorPublic,
    JogadorRef,
    PartidaDetalhe,
    PartidaPlacar,
    PeladaEstado,
)

router = APIRouter(tags=["partidas"])
admin = [Depends(require_admin)]

_422 = status.HTTP_422_UNPROCESSABLE_CONTENT


def _buscar(session: Session, partida_id: int) -> Partida:
    return get_or_404(session, Partida, partida_id, "Partida não encontrada")


def _exigir_em_andamento(partida: Partida) -> None:
    if partida.encerrada:
        raise HTTPException(status.HTTP_409_CONFLICT, "Partida já encerrada")


def detalhe_partida(session: Session, partida: Partida) -> PartidaDetalhe:
    equipes = {
        e.id: e
        for e in session.exec(
            select(Time).where(col(Time.id).in_([partida.equipe_a_id, partida.equipe_b_id]))
        ).all()
    }
    escalados = session.exec(
        select(Escalacao, Jogador)
        .join(Jogador, col(Jogador.id) == Escalacao.jogador_id)
        .where(Escalacao.partida_id == partida.id)
        .order_by(col(Jogador.nome))
    ).all()
    gols = session.exec(
        select(Gol).where(Gol.partida_id == partida.id).order_by(col(Gol.id))
    ).all()

    elenco: dict[int, list[JogadorPublic]] = defaultdict(list)
    nomes: dict[int, str] = {}
    for esc, jogador in escalados:
        elenco[esc.equipe_id].append(JogadorPublic.model_validate(jogador))
        nomes[esc.jogador_id] = jogador.nome
    placar = Counter(g.equipe_id for g in gols)

    def equipe(eid: int) -> EquipePartida:
        return EquipePartida(id=eid, nome=equipes[eid].nome, gols=placar[eid], jogadores=elenco[eid])

    def ref(jid: int | None) -> JogadorRef | None:
        return JogadorRef(id=jid, nome=nomes[jid]) if jid is not None else None

    return PartidaDetalhe(
        id=partida.id,  # pyright: ignore[reportArgumentType]
        pelada_id=partida.pelada_id,
        numero=partida.numero,
        encerrada=partida.encerrada,
        penaltis_a=partida.penaltis_a,
        penaltis_b=partida.penaltis_b,
        equipe_a=equipe(partida.equipe_a_id),
        equipe_b=equipe(partida.equipe_b_id),
        gols=[
            GolPublic(
                id=g.id,  # pyright: ignore[reportArgumentType]
                equipe_id=g.equipe_id,
                autor=ref(g.autor_id),  # pyright: ignore[reportArgumentType]
                assistente=ref(g.assistente_id),
                gol_contra=g.gol_contra,
            )
            for g in gols
        ],
    )


# --- Partida ---


@router.post(
    "/peladas/{pelada_id}/partidas",
    response_model=PartidaDetalhe,
    status_code=status.HTTP_201_CREATED,
    dependencies=admin,
)
def comecar_partida(pelada_id: int, session: SessionDep):
    """Começa a próxima partida com as duas equipes em quadra e grava a escalação."""
    get_or_404(session, Pelada, pelada_id, "Pelada não encontrada")
    if session.exec(
        select(Partida.id).where(Partida.pelada_id == pelada_id, ~col(Partida.encerrada))
    ).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Já tem uma partida em andamento")

    em_quadra = session.exec(
        select(Time)
        .where(Time.pelada_id == pelada_id, col(Time.ordem_fila).is_(None))
        .order_by(col(Time.id))
    ).all()
    if not em_quadra:
        raise HTTPException(status.HTTP_409_CONFLICT, "Pelada ainda não foi sorteada")
    if len(em_quadra) != 2:  # invariante do sorteio/rodízio
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Esperava 2 equipes em quadra, achei {len(em_quadra)}"
        )
    a, b = em_quadra

    presencas = session.exec(
        select(Presenca).where(col(Presenca.equipe_id).in_([a.id, b.id]))
    ).all()
    for equipe in (a, b):
        if not any(p.equipe_id == equipe.id for p in presencas):
            raise HTTPException(status.HTTP_409_CONFLICT, f"Equipe {equipe.nome} está sem jogadores")

    ultimo = session.exec(
        select(func.max(Partida.numero)).where(Partida.pelada_id == pelada_id)
    ).one()
    partida = Partida(
        pelada_id=pelada_id,
        numero=(ultimo or 0) + 1,
        equipe_a_id=a.id,  # pyright: ignore[reportArgumentType]
        equipe_b_id=b.id,  # pyright: ignore[reportArgumentType]
    )
    session.add(partida)
    session.flush()
    session.add_all(
        Escalacao(partida_id=partida.id, jogador_id=p.jogador_id, equipe_id=p.equipe_id)  # pyright: ignore[reportArgumentType]
        for p in presencas
    )
    session.commit()
    return detalhe_partida(session, partida)


@router.get("/peladas/{pelada_id}/partidas", response_model=list[PartidaPlacar])
def listar_partidas(pelada_id: int, session: SessionDep):
    """Partidas do dia, em ordem, com o placar de cada uma."""
    get_or_404(session, Pelada, pelada_id, "Pelada não encontrada")
    partidas = session.exec(
        select(Partida).where(Partida.pelada_id == pelada_id).order_by(col(Partida.numero))
    ).all()
    nomes = dict(session.exec(select(Time.id, Time.nome).where(Time.pelada_id == pelada_id)).all())
    placar_ = placares(session, {p.id for p in partidas})  # pyright: ignore[reportArgumentType]

    def equipe(p: Partida, eid: int) -> EquipePlacar:
        return EquipePlacar(id=eid, nome=nomes[eid], gols=placar_[p.id, eid])

    return [
        PartidaPlacar(
            id=p.id,  # pyright: ignore[reportArgumentType]
            numero=p.numero,
            encerrada=p.encerrada,
            penaltis_a=p.penaltis_a,
            penaltis_b=p.penaltis_b,
            equipe_a=equipe(p, p.equipe_a_id),
            equipe_b=equipe(p, p.equipe_b_id),
        )
        for p in partidas
    ]


@router.get("/partidas/{partida_id}", response_model=PartidaDetalhe)
def detalhe(partida_id: int, session: SessionDep):
    return detalhe_partida(session, _buscar(session, partida_id))


@router.post("/partidas/{partida_id}/encerrar", response_model=PeladaEstado, dependencies=admin)
def encerrar(partida_id: int, session: SessionDep, dados: EncerrarPartida | None = None):
    """Encerra a partida e aplica o rodízio. Devolve o novo estado da pelada."""
    partida = _buscar(session, partida_id)
    _exigir_em_andamento(partida)
    pelada = session.get_one(Pelada, partida.pelada_id)

    gols_a, gols_b = placar(session, partida)
    pa, pb = (dados.penaltis_a, dados.penaltis_b) if dados else (None, None)
    mandou_penaltis = pa is not None or pb is not None

    if gols_a == gols_b and pelada.numero_times < 4:
        if pa is None or pb is None:
            raise HTTPException(
                _422, f"Empate em {gols_a} x {gols_b}: informe penaltis_a e penaltis_b"
            )
        if pa == pb:
            raise HTTPException(_422, "Os pênaltis não podem terminar empatados")
    elif mandou_penaltis:
        motivo = (
            "empate com 4 equipes não tem pênaltis (as duas saem)"
            if gols_a == gols_b
            else f"não houve empate ({gols_a} x {gols_b})"
        )
        raise HTTPException(_422, f"Sem pênaltis: {motivo}")

    partida.penaltis_a, partida.penaltis_b = pa, pb
    partida.encerrada = True
    session.add(partida)
    aplicar_rodizio(session, pelada, partida, gols_a, gols_b)
    session.commit()
    return estado_pelada(session, pelada)


# --- Gols ---


@router.post(
    "/partidas/{partida_id}/gols",
    response_model=PartidaDetalhe,
    status_code=status.HTTP_201_CREATED,
    dependencies=admin,
)
def registrar_gol(partida_id: int, dados: GolCreate, session: SessionDep):
    partida = _buscar(session, partida_id)
    _exigir_em_andamento(partida)

    lados = {partida.equipe_a_id, partida.equipe_b_id}
    if dados.equipe_id not in lados:
        raise HTTPException(_422, "A equipe não está jogando esta partida")
    adversaria = (lados - {dados.equipe_id}).pop()

    def equipe_do(jogador_id: int, papel: str) -> int:
        esc = session.get(Escalacao, {"partida_id": partida_id, "jogador_id": jogador_id})
        if esc is None:
            raise HTTPException(_422, f"O {papel} não está escalado nesta partida")
        return esc.equipe_id

    equipe_autor = equipe_do(dados.autor_id, "autor")
    if dados.gol_contra:
        if equipe_autor != adversaria:
            raise HTTPException(
                _422, "Gol contra: o autor tem que jogar pela equipe adversária da beneficiada"
            )
        if dados.assistente_id is not None:
            raise HTTPException(_422, "Gol contra não tem assistência")
    elif equipe_autor != dados.equipe_id:
        raise HTTPException(
            _422, "O autor joga pela outra equipe (se foi gol contra, mande gol_contra=true)"
        )

    if dados.assistente_id is not None:
        if dados.assistente_id == dados.autor_id:
            raise HTTPException(_422, "Autor e assistente são a mesma pessoa")
        if equipe_do(dados.assistente_id, "assistente") != dados.equipe_id:
            raise HTTPException(_422, "O assistente joga pela outra equipe")

    session.add(Gol(partida_id=partida_id, **dados.model_dump()))
    session.commit()
    return detalhe_partida(session, partida)


@router.delete(
    "/partidas/{partida_id}/gols/{gol_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=admin,
)
def apagar_gol(partida_id: int, gol_id: int, session: SessionDep) -> None:
    """Corrige um gol lançado errado. Depois de encerrada não dá (o rodízio já foi aplicado)."""
    partida = _buscar(session, partida_id)
    gol = session.get(Gol, gol_id)
    if gol is None or gol.partida_id != partida_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Gol não encontrado nesta partida")
    _exigir_em_andamento(partida)
    session.delete(gol)
    session.commit()
