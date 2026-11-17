"""Estatísticas calculadas na hora a partir de gol, partida e escalacao (nada é guardado).

Regras (Diagrama-Classes.md):
- Gol contra não conta como gol do autor; conta no placar do time beneficiado.
- Pênaltis só decidem o rodízio: nas estatísticas a partida é empate.
- V/E/D e "partidas" só contam partidas encerradas. Gols e assistências contam
  assim que são registrados (inclusive na partida em andamento).

Tudo é calculado em lote (poucas queries, não uma por jogador).
"""

from collections import Counter, defaultdict

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import Escalacao, Gol, Jogador, Partida, Pelada, Time
from app.schemas import (
    EquipeEstatisticas,
    Estatisticas,
    JogadorRef,
    PeladaEstatisticas,
    RankingItem,
    TipoRanking,
)


def calcular(
    session: Session, *, pelada_id: int | None = None, jogador_id: int | None = None
) -> dict[int, Estatisticas]:
    """Estatísticas por jogador_id. Só aparece quem tem algum número diferente de zero."""
    est: dict[int, Estatisticas] = defaultdict(Estatisticas)

    def na_pelada(q):
        return q.where(Partida.pelada_id == pelada_id) if pelada_id is not None else q

    # Gols (sem gol contra) e assistências
    for coluna, campo, extra in (
        (col(Gol.autor_id), "gols", ~col(Gol.gol_contra)),
        (col(Gol.assistente_id), "assistencias", col(Gol.assistente_id).is_not(None)),
    ):
        q = (
            select(coluna, func.count())
            .join(Partida, col(Partida.id) == Gol.partida_id)
            .where(extra)
            .group_by(coluna)
        )
        if jogador_id is not None:
            q = q.where(coluna == jogador_id)
        for jid, n in session.exec(na_pelada(q)).all():
            if jid is not None:
                setattr(est[jid], campo, n)

    # Partidas e V/E/D: só partidas encerradas
    q = (
        select(Escalacao.partida_id, Escalacao.jogador_id, Escalacao.equipe_id)
        .join(Partida, col(Partida.id) == Escalacao.partida_id)
        .where(col(Partida.encerrada))
    )
    if jogador_id is not None:
        q = q.where(Escalacao.jogador_id == jogador_id)
    jogos = session.exec(na_pelada(q)).all()

    placar = placares(session, {pid for pid, _, _ in jogos})
    for partida_id, jid, equipe_id in jogos:
        e = est[jid]
        e.partidas += 1
        meus, deles = placar[partida_id, equipe_id], placar[partida_id, None] - placar[partida_id, equipe_id]
        if meus > deles:
            e.vitorias += 1
        elif meus < deles:
            e.derrotas += 1
        else:
            e.empates += 1
    return dict(est)


def estatisticas_jogador(session: Session, jogador_id: int) -> Estatisticas:
    return calcular(session, jogador_id=jogador_id).get(jogador_id, Estatisticas())


def ranking(
    session: Session, tipo: TipoRanking, pelada_id: int | None = None
) -> list[RankingItem]:
    """Quem tem valor > 0, do maior para o menor. Empate divide a posição (1, 1, 3)."""
    est = {jid: e for jid, e in calcular(session, pelada_id=pelada_id).items() if getattr(e, tipo) > 0}
    nomes = dict(
        session.exec(select(Jogador.id, Jogador.nome).where(col(Jogador.id).in_(est.keys()))).all()
    )
    ordenados = sorted(est.items(), key=lambda item: (-getattr(item[1], tipo), nomes[item[0]]))

    itens: list[RankingItem] = []
    for i, (jid, e) in enumerate(ordenados):
        valor = getattr(e, tipo)
        posicao = itens[-1].posicao if itens and itens[-1].valor == valor else i + 1
        itens.append(
            RankingItem(
                posicao=posicao, jogador=JogadorRef(id=jid, nome=nomes[jid]), valor=valor, estatisticas=e
            )
        )
    return itens


def estatisticas_pelada(session: Session, pelada: Pelada) -> PeladaEstatisticas:
    equipes = session.exec(
        select(Time).where(Time.pelada_id == pelada.id).order_by(col(Time.id))
    ).all()
    partidas = session.exec(select(Partida).where(Partida.pelada_id == pelada.id)).all()
    placar = placares(session, {p.id for p in partidas})  # pyright: ignore[reportArgumentType]

    por_equipe = {
        e.id: EquipeEstatisticas(id=e.id, nome=e.nome)  # pyright: ignore[reportArgumentType]
        for e in equipes
    }
    for p in partidas:
        a, b = por_equipe[p.equipe_a_id], por_equipe[p.equipe_b_id]
        ga, gb = placar[p.id, a.id], placar[p.id, b.id]
        a.gols_marcados += ga
        a.gols_sofridos += gb
        b.gols_marcados += gb
        b.gols_sofridos += ga
        if p.encerrada:
            a.partidas += 1
            b.partidas += 1
            if ga == gb:
                a.empates += 1
                b.empates += 1
            else:
                vencedor, perdedor = (a, b) if ga > gb else (b, a)
                vencedor.vitorias += 1
                perdedor.derrotas += 1

    return PeladaEstatisticas(
        pelada_id=pelada.id,  # pyright: ignore[reportArgumentType]
        partidas_encerradas=sum(p.encerrada for p in partidas),
        equipes=list(por_equipe.values()),
        artilheiros=ranking(session, "gols", pelada_id=pelada.id),
    )


def placares(session: Session, partida_ids: set[int]) -> Counter:
    """Gols por (partida, equipe beneficiada) e total por (partida, None)."""
    placar: Counter = Counter()
    if not partida_ids:
        return placar
    rows = session.exec(
        select(Gol.partida_id, Gol.equipe_id, func.count())
        .where(col(Gol.partida_id).in_(partida_ids))
        .group_by(col(Gol.partida_id), col(Gol.equipe_id))
    ).all()
    for partida_id, equipe_id, n in rows:
        placar[partida_id, equipe_id] = n
        placar[partida_id, None] += n
    return placar
