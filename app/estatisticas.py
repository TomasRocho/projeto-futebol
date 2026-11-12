"""Estatísticas calculadas na hora a partir de gol, partida e escalacao (nada é guardado).

Regras (Diagrama-Classes.md):
- Gol contra não conta como gol do autor; conta no placar do time beneficiado.
- Pênaltis só decidem o rodízio: nas estatísticas a partida é empate.
- V/E/D e "partidas" só contam partidas encerradas. Gols e assistências contam
  assim que são registrados (inclusive na partida em andamento).
"""

from collections import defaultdict

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.models import Escalacao, Gol, Partida
from app.schemas import Estatisticas


def estatisticas_jogador(session: Session, jogador_id: int) -> Estatisticas:
    gols = session.exec(
        select(func.count())
        .select_from(Gol)
        .where(Gol.autor_id == jogador_id, ~col(Gol.gol_contra))
    ).one()
    assistencias = session.exec(
        select(func.count()).select_from(Gol).where(Gol.assistente_id == jogador_id)
    ).one()

    # Em qual equipe o jogador jogou cada partida encerrada.
    jogos = session.exec(
        select(Escalacao.partida_id, Escalacao.equipe_id)
        .join(Partida, col(Partida.id) == Escalacao.partida_id)
        .where(Escalacao.jogador_id == jogador_id, col(Partida.encerrada))
    ).all()

    est = Estatisticas(partidas=len(jogos), gols=gols, assistencias=assistencias)
    if not jogos:
        return est

    # Placar dessas partidas: gols por (partida, equipe beneficiada).
    placar: dict[tuple[int, int], int] = defaultdict(int)
    total: dict[int, int] = defaultdict(int)
    rows = session.exec(
        select(Gol.partida_id, Gol.equipe_id, func.count())
        .where(col(Gol.partida_id).in_([pid for pid, _ in jogos]))
        .group_by(col(Gol.partida_id), col(Gol.equipe_id))
    ).all()
    for partida_id, equipe_id, n in rows:
        placar[(partida_id, equipe_id)] = n
        total[partida_id] += n

    for partida_id, equipe_id in jogos:
        meus = placar[(partida_id, equipe_id)]
        deles = total[partida_id] - meus
        if meus > deles:
            est.vitorias += 1
        elif meus < deles:
            est.derrotas += 1
        else:
            est.empates += 1
    return est
