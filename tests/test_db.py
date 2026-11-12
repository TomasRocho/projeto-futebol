# pyright: reportArgumentType=false, reportOptionalMemberAccess=false
# (ids dos models são "int | None" até o flush; nos testes isso é ruído)

"""Garante que as constraints do Modelo-Relacional valem de verdade no banco."""

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.models import Escalacao, Gol, Jogador, Partida, Pelada, Presenca, Time


def _cenario(s: Session) -> dict:
    """Pelada com 2 equipes, 1 partida e 2 jogadores escalados (um em cada lado)."""
    joao, pedro = Jogador(nome="João", rating=3), Jogador(nome="Pedro", rating=4)
    pelada = Pelada(data=date(2026, 11, 7), numero_times=2, jogadores_por_time=6)
    s.add_all([joao, pedro, pelada])
    s.flush()
    azul, verde = Time(pelada_id=pelada.id, nome="Azul"), Time(pelada_id=pelada.id, nome="Verde")
    s.add_all([azul, verde])
    s.flush()
    s.add_all(
        [
            Presenca(pelada_id=pelada.id, jogador_id=joao.id, equipe_id=azul.id),
            Presenca(pelada_id=pelada.id, jogador_id=pedro.id, equipe_id=verde.id),
        ]
    )
    partida = Partida(pelada_id=pelada.id, numero=1, equipe_a_id=azul.id, equipe_b_id=verde.id)
    s.add(partida)
    s.flush()
    s.add_all(
        [
            Escalacao(partida_id=partida.id, jogador_id=joao.id, equipe_id=azul.id),
            Escalacao(partida_id=partida.id, jogador_id=pedro.id, equipe_id=verde.id),
        ]
    )
    s.commit()
    return dict(joao=joao, pedro=pedro, pelada=pelada, azul=azul, verde=verde, partida=partida)


def _falha(s: Session, obj) -> None:
    s.add(obj)
    with pytest.raises(IntegrityError):
        s.flush()
    s.rollback()


def test_foreign_keys_ligadas(session: Session):
    assert session.exec(text("PRAGMA foreign_keys")).one()[0] == 1  # type: ignore[call-overload]


def test_cenario_valido(session: Session):
    c = _cenario(session)
    session.add(Gol(partida_id=c["partida"].id, equipe_id=c["azul"].id, autor_id=c["joao"].id))
    session.commit()


def test_rating_fora_do_intervalo(session: Session):
    _falha(session, Jogador(nome="X", rating=6))


def test_numero_times_invalido(session: Session):
    _falha(session, Pelada(data=date(2026, 1, 1), numero_times=5, jogadores_por_time=6))


def test_presenca_em_equipe_de_outra_pelada(session: Session):
    c = _cenario(session)
    outra = Pelada(data=date(2026, 11, 14), numero_times=2, jogadores_por_time=6)
    session.add(outra)
    session.commit()
    _falha(session, Presenca(pelada_id=outra.id, jogador_id=c["joao"].id, equipe_id=c["azul"].id))


def test_gol_de_quem_nao_esta_escalado(session: Session):
    c = _cenario(session)
    fora = Jogador(nome="Fora", rating=2)
    session.add(fora)
    session.commit()
    _falha(session, Gol(partida_id=c["partida"].id, equipe_id=c["azul"].id, autor_id=fora.id))


def test_gol_contra_com_assistente(session: Session):
    c = _cenario(session)
    gol = Gol(
        partida_id=c["partida"].id,
        equipe_id=c["verde"].id,
        autor_id=c["joao"].id,
        assistente_id=c["pedro"].id,
        gol_contra=True,
    )
    _falha(session, gol)


def test_penaltis_empatados(session: Session):
    c = _cenario(session)
    p = session.get(Partida, c["partida"].id)
    assert p
    p.penaltis_a, p.penaltis_b = 3, 3
    _falha(session, p)


def test_penaltis_so_um_lado(session: Session):
    c = _cenario(session)
    p = session.get(Partida, c["partida"].id)
    assert p
    p.penaltis_a = 4
    _falha(session, p)


def test_nao_apaga_jogador_com_historico(session: Session):
    c = _cenario(session)
    session.delete(c["joao"])
    with pytest.raises(IntegrityError):
        session.flush()


def test_apagar_pelada_apaga_tudo_dela(session: Session):
    c = _cenario(session)
    session.add(Gol(partida_id=c["partida"].id, equipe_id=c["azul"].id, autor_id=c["joao"].id))
    session.commit()

    session.delete(c["pelada"])
    session.commit()

    for modelo in (Time, Presenca, Partida, Escalacao, Gol):
        assert session.exec(select(modelo)).all() == [], modelo.__name__
    assert len(session.exec(select(Jogador)).all()) == 2  # jogadores ficam
