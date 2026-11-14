"""Rodízio aplicado ao encerrar uma partida. Regras em Diagrama-Classes.md ("Fila e rodízio").

- Perdedor = menos gols; se empatou, menos pênaltis (2 ou 3 equipes).
- Avulsos: saem do perdedor tantos jogadores aleatórios quantos estão esperando,
  e quem esperava entra no lugar (se tiver mais gente esperando do que no time,
  o time inteiro sai e entra um sorteio dos que esperavam).
- 2 equipes: ninguém sai de quadra, só a troca de avulsos.
- 3 ou 4 equipes: o perdedor (já com os avulsos) vai para o fim da fila e entra o 1º da fila.
- Empate com 4 equipes: as duas saem e entram as duas primeiras da fila. Quem estava há mais
  tempo em quadra vai para o fim; a outra fica na frente dela e recebe os avulsos.
  Se entraram juntas, a ordem é sorteada.
"""

import random

from sqlmodel import Session, col, func, select

from app.models import Gol, Partida, Pelada, Presenca, Time

rng = random.Random()


def placar(session: Session, partida: Partida) -> tuple[int, int]:
    gols = dict(
        session.exec(
            select(Gol.equipe_id, func.count())
            .where(Gol.partida_id == partida.id)
            .group_by(col(Gol.equipe_id))
        ).all()
    )
    return gols.get(partida.equipe_a_id, 0), gols.get(partida.equipe_b_id, 0)


def aplicar_rodizio(
    session: Session, pelada: Pelada, partida: Partida, gols_a: int, gols_b: int, rng: random.Random = rng
) -> None:
    """Atualiza presenças e fila. Espera a partida já com os pênaltis validados."""
    a, b = partida.equipe_a_id, partida.equipe_b_id

    if gols_a == gols_b and pelada.numero_times == 4:
        entrada_a, entrada_b = _entrou_em(session, partida, a), _entrou_em(session, partida, b)
        if entrada_a == entrada_b:
            frente, fundo = rng.sample([a, b], 2)
        elif entrada_a < entrada_b:  # A está em quadra há mais tempo
            frente, fundo = b, a
        else:
            frente, fundo = a, b
        _trocar_avulsos(session, pelada.id, frente, rng)  # pyright: ignore[reportArgumentType]
        _girar_fila(session, pelada.id, saem=[frente, fundo])  # pyright: ignore[reportArgumentType]
        return

    if gols_a != gols_b:
        perdedor = b if gols_a > gols_b else a
    else:
        assert partida.penaltis_a is not None and partida.penaltis_b is not None
        perdedor = b if partida.penaltis_a > partida.penaltis_b else a

    _trocar_avulsos(session, pelada.id, perdedor, rng)  # pyright: ignore[reportArgumentType]
    if pelada.numero_times >= 3:
        _girar_fila(session, pelada.id, saem=[perdedor])  # pyright: ignore[reportArgumentType]


def _trocar_avulsos(session: Session, pelada_id: int, equipe_id: int, rng: random.Random) -> None:
    esperando = session.exec(
        select(Presenca)
        .where(Presenca.pelada_id == pelada_id, col(Presenca.equipe_id).is_(None))
        .order_by(col(Presenca.jogador_id))
    ).all()
    elenco = session.exec(
        select(Presenca).where(Presenca.equipe_id == equipe_id).order_by(col(Presenca.jogador_id))
    ).all()

    k = min(len(esperando), len(elenco))
    saem, entram = rng.sample(list(elenco), k), rng.sample(list(esperando), k)
    for p in saem:
        p.equipe_id = None
    for p in entram:
        p.equipe_id = equipe_id
    session.add_all(saem + entram)


def _girar_fila(session: Session, pelada_id: int, saem: list[int]) -> None:
    """Os primeiros da fila entram em quadra (um para cada equipe que sai); `saem` vão
    para o fim da fila, nessa ordem."""
    fila = session.exec(
        select(Time)
        .where(Time.pelada_id == pelada_id, col(Time.ordem_fila).is_not(None))
        .order_by(col(Time.ordem_fila))
    ).all()
    entram, resto = fila[: len(saem)], fila[len(saem) :]
    for equipe in entram:
        equipe.ordem_fila = None
        session.add(equipe)

    nova_fila = list(resto) + [session.get_one(Time, eid) for eid in saem]
    for posicao, equipe in enumerate(nova_fila, start=1):
        equipe.ordem_fila = posicao
        session.add(equipe)


def _entrou_em(session: Session, partida: Partida, equipe_id: int) -> int:
    """Número da partida em que a equipe entrou em quadra (início da sequência atual)."""
    anteriores = session.exec(
        select(Partida)
        .where(Partida.pelada_id == partida.pelada_id, Partida.numero <= partida.numero)
        .order_by(col(Partida.numero).desc())
    ).all()
    entrada = partida.numero
    for p in anteriores:
        if equipe_id not in (p.equipe_a_id, p.equipe_b_id):
            break
        entrada = p.numero
    return entrada
