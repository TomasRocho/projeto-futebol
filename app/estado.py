"""Monta o estado atual de uma pelada (usado pelo GET da pelada e pelas ações que a alteram)."""

from collections import defaultdict

from sqlmodel import Session, col, select

from app.models import Jogador, Partida, Pelada, Presenca, Time
from app.schemas import EquipeEstado, JogadorPublic, PartidaResumo, PeladaEstado


def estado_pelada(session: Session, pelada: Pelada) -> PeladaEstado:
    equipes = session.exec(select(Time).where(Time.pelada_id == pelada.id)).all()
    presentes = session.exec(
        select(Presenca, Jogador)
        .join(Jogador, col(Jogador.id) == Presenca.jogador_id)
        .where(Presenca.pelada_id == pelada.id)
        .order_by(col(Jogador.nome))
    ).all()

    elenco: dict[int, list[JogadorPublic]] = defaultdict(list)
    esperando: list[JogadorPublic] = []
    for presenca, jogador in presentes:
        pub = JogadorPublic.model_validate(jogador)
        if presenca.equipe_id is None:
            esperando.append(pub)
        else:
            elenco[presenca.equipe_id].append(pub)

    # Em quadra (ordem_fila None) primeiro, depois a fila em ordem.
    equipes = sorted(equipes, key=lambda e: (e.ordem_fila is not None, e.ordem_fila or 0, e.id))

    partida = session.exec(
        select(Partida).where(Partida.pelada_id == pelada.id, ~col(Partida.encerrada))
    ).first()

    return PeladaEstado(
        id=pelada.id,  # pyright: ignore[reportArgumentType]
        data=pelada.data,
        numero_times=pelada.numero_times,
        jogadores_por_time=pelada.jogadores_por_time,
        equipes=[
            EquipeEstado(
                id=e.id,  # pyright: ignore[reportArgumentType]
                nome=e.nome,
                ordem_fila=e.ordem_fila,
                rating_medio=_media([j.rating for j in elenco[e.id]]),  # pyright: ignore[reportArgumentType]
                jogadores=elenco[e.id],  # pyright: ignore[reportArgumentType]
            )
            for e in equipes
        ],
        esperando=esperando,
        partida_em_andamento=PartidaResumo.model_validate(partida) if partida else None,
    )


def _media(valores: list[int]) -> float | None:
    return round(sum(valores) / len(valores), 2) if valores else None
