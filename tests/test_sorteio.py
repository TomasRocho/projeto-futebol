# pyright: reportArgumentType=false, reportOptionalMemberAccess=false

import random
from collections import Counter

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Partida, Presenca, Time
from app.sorteio import diferenca, sortear_times, tamanhos

ADMIN = {"X-API-Key": "chave-de-teste"}


# --- Algoritmo (função pura) ---


@pytest.mark.parametrize(
    ("presentes", "n_times", "por_time", "esperado"),
    [
        (12, 2, 6, [6, 6]),
        (15, 2, 6, [6, 6]),  # 3 sobram
        (10, 3, 7, [4, 3, 3]),  # pouca gente: incompletos por igual
        (28, 4, 7, [7, 7, 7, 7]),
        (2, 2, 6, [1, 1]),
    ],
)
def test_tamanhos(presentes, n_times, por_time, esperado):
    assert tamanhos(presentes, n_times, por_time) == esperado


def _com_ratings(ratings: list[int]) -> list[tuple[int, int]]:
    return list(enumerate(ratings, start=1))


def _somas(resultado, jogadores) -> list[int]:
    rating = dict(jogadores)
    return [sum(rating[j] for j in t) for t in resultado.times]


def test_todos_aparecem_uma_vez():
    jogadores = _com_ratings([3] * 17)
    r = sortear_times(jogadores, 2, 7, random.Random(1))
    ids = [j for t in r.times for j in t] + r.avulsos
    assert sorted(ids) == list(range(1, 18))
    assert [len(t) for t in r.times] == [7, 7]
    assert len(r.avulsos) == 3


def test_equilibrio_perfeito_quando_possivel():
    jogadores = _com_ratings([5, 5, 4, 4, 3, 3, 2, 2, 1, 1, 0, 0])
    r = sortear_times(jogadores, 2, 6, random.Random(42))
    assert _somas(r, jogadores)[0] == _somas(r, jogadores)[1] == 15


@pytest.mark.parametrize("seed", range(30))
def test_equilibrio_com_ratings_aleatorios(seed):
    """28 jogadores, 4 times de 7: diferença entre o mais forte e o mais fraco <= 1."""
    rng = random.Random(seed)
    jogadores = _com_ratings([rng.randint(0, 5) for _ in range(28)])
    r = sortear_times(jogadores, 4, 7, random.Random(seed))
    somas = _somas(r, jogadores)
    assert max(somas) - min(somas) <= 1, somas


def test_refazer_da_times_diferentes():
    jogadores = _com_ratings([3, 3, 3, 3, 2, 2, 2, 2, 4, 4, 4, 4])
    divisoes = {
        frozenset(frozenset(t) for t in sortear_times(jogadores, 2, 6, random.Random(s)).times)
        for s in range(20)
    }
    assert len(divisoes) > 1


def test_diferenca():
    assert diferenca([[(1, 5), (2, 1)], [(3, 3)]]) == 3


# --- Endpoint ---


def _pelada_com_presentes(client: TestClient, n: int, numero_times=2, por_time=6) -> int:
    r = client.post(
        "/peladas",
        json={"data": "2026-11-14", "numero_times": numero_times, "jogadores_por_time": por_time},
        headers=ADMIN,
    )
    pid = r.json()["id"]
    ids = [
        client.post("/jogadores", json={"nome": f"J{i:02}", "rating": i % 6}, headers=ADMIN).json()["id"]
        for i in range(n)
    ]
    client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": ids}, headers=ADMIN)
    return pid


def _resumo(estado: dict) -> list[tuple[str, int | None, int]]:
    return [(e["nome"], e["ordem_fila"], len(e["jogadores"])) for e in estado["equipes"]]


def test_sorteio_2_times(client: TestClient):
    pid = _pelada_com_presentes(client, 12)
    r = client.post(f"/peladas/{pid}/sorteio", headers=ADMIN)
    assert r.status_code == 200
    estado = r.json()
    assert _resumo(estado) == [("Azul", None, 6), ("Vermelho", None, 6)]
    assert estado["esperando"] == []


def test_sorteio_3_times_com_avulsos(client: TestClient):
    pid = _pelada_com_presentes(client, 23, numero_times=3, por_time=7)
    estado = client.post(f"/peladas/{pid}/sorteio", headers=ADMIN).json()
    assert _resumo(estado) == [("Azul", None, 7), ("Vermelho", None, 7), ("Verde", 1, 7)]
    assert len(estado["esperando"]) == 2


def test_sorteio_4_times_incompletos(client: TestClient):
    pid = _pelada_com_presentes(client, 22, numero_times=4, por_time=6)
    estado = client.post(f"/peladas/{pid}/sorteio", headers=ADMIN).json()
    assert _resumo(estado) == [
        ("Azul", None, 6), ("Vermelho", None, 6), ("Verde", 1, 5), ("Amarelo", 2, 5),
    ]
    assert estado["esperando"] == []


def test_refazer_sorteio(client: TestClient, session: Session):
    pid = _pelada_com_presentes(client, 14)
    client.post(f"/peladas/{pid}/sorteio", headers=ADMIN)
    r = client.post(f"/peladas/{pid}/sorteio", headers=ADMIN)
    assert r.status_code == 200
    assert _resumo(r.json()) == [("Azul", None, 6), ("Vermelho", None, 6)]
    assert len(r.json()["esperando"]) == 2
    # equipes antigas sumiram e ninguém perdeu a presença
    assert len(session.exec(select(Time)).all()) == 2
    assert len(session.exec(select(Presenca)).all()) == 14


def test_sorteio_depois_da_partida_409(client: TestClient, session: Session):
    pid = _pelada_com_presentes(client, 12)
    estado = client.post(f"/peladas/{pid}/sorteio", headers=ADMIN).json()
    a, b = (e["id"] for e in estado["equipes"])
    session.add(Partida(pelada_id=pid, numero=1, equipe_a_id=a, equipe_b_id=b))
    session.commit()
    assert client.post(f"/peladas/{pid}/sorteio", headers=ADMIN).status_code == 409


def test_sorteio_sem_gente_suficiente_409(client: TestClient):
    pid = _pelada_com_presentes(client, 2, numero_times=3)
    assert client.post(f"/peladas/{pid}/sorteio", headers=ADMIN).status_code == 409


def test_sorteio_404_e_401(client: TestClient):
    assert client.post("/peladas/999/sorteio", headers=ADMIN).status_code == 404
    pid = _pelada_com_presentes(client, 12)
    assert client.post(f"/peladas/{pid}/sorteio").status_code == 401


def test_sorteio_equilibra_no_endpoint(client: TestClient):
    pid = _pelada_com_presentes(client, 28, numero_times=4, por_time=7)
    estado = client.post(f"/peladas/{pid}/sorteio", headers=ADMIN).json()
    somas = [sum(j["rating"] for j in e["jogadores"]) for e in estado["equipes"]]
    assert max(somas) - min(somas) <= 1, somas
    assert Counter(len(e["jogadores"]) for e in estado["equipes"]) == {7: 4}
