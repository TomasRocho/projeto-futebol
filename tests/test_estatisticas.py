# pyright: reportArgumentType=false, reportOptionalMemberAccess=false, reportReturnType=false

"""Ranking e estatísticas da pelada, com cenário montado direto no banco (determinístico).

Pelada 1 (Azul: João, Ana | Verde: Pedro):
  1. Azul 1 x 2 Verde   gol do João (assist. Ana); gol do Pedro; gol contra do João
  2. Azul 1 x 0 Verde   gol do João
  3. Azul 0 x 0 Verde   pênaltis 4 x 3 -> empate nas estatísticas
  4. em andamento       gol da Ana (assist. João)
Pelada 2 (Azul: Bia | Verde: Pedro):
  1. Azul 0 x 2 Verde   dois gols do Pedro
"""

from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Escalacao, Gol, Jogador, Partida, Pelada, Time


@pytest.fixture
def cenario(session: Session) -> dict:
    j = {n: Jogador(nome=n, rating=3) for n in ("João", "Ana", "Pedro", "Bia")}
    session.add_all(j.values())
    session.flush()

    def pelada(dia: int, azul: list[str], verde: list[str], partidas: list[dict]) -> tuple[int, int, int]:
        p = Pelada(data=date(2026, 11, dia), numero_times=2, jogadores_por_time=6)
        session.add(p)
        session.flush()
        eq = {"A": Time(pelada_id=p.id, nome="Azul"), "V": Time(pelada_id=p.id, nome="Verde")}
        session.add_all(eq.values())
        session.flush()
        for numero, spec in enumerate(partidas, start=1):
            pen = spec.get("pen", (None, None))
            pt = Partida(
                pelada_id=p.id, numero=numero, equipe_a_id=eq["A"].id, equipe_b_id=eq["V"].id,
                encerrada=spec.get("encerrada", True), penaltis_a=pen[0], penaltis_b=pen[1],
            )
            session.add(pt)
            session.flush()
            session.add_all(
                Escalacao(partida_id=pt.id, jogador_id=j[n].id, equipe_id=eq[lado].id)
                for lado, nomes in (("A", azul), ("V", verde)) for n in nomes
            )
            session.flush()
            session.add_all(
                Gol(
                    partida_id=pt.id, equipe_id=eq[lado].id, autor_id=j[autor].id,
                    assistente_id=j[assist].id if assist else None, gol_contra=contra,
                )
                for lado, autor, assist, contra in spec.get("gols", [])
            )
            session.flush()
        return p.id, eq["A"].id, eq["V"].id

    p1, azul1, verde1 = pelada(14, ["João", "Ana"], ["Pedro"], [
        {"gols": [("A", "João", "Ana", False), ("V", "Pedro", None, False), ("V", "João", None, True)]},
        {"gols": [("A", "João", None, False)]},
        {"pen": (4, 3)},
        {"gols": [("A", "Ana", "João", False)], "encerrada": False},
    ])
    p2, _, _ = pelada(21, ["Bia"], ["Pedro"], [
        {"gols": [("V", "Pedro", None, False), ("V", "Pedro", None, False)]},
    ])
    session.commit()
    return {"p1": p1, "p2": p2, "azul1": azul1, "verde1": verde1} | {n: x.id for n, x in j.items()}


def _linhas(itens: list[dict]) -> list[tuple[int, str, int]]:
    return [(i["posicao"], i["jogador"]["nome"], i["valor"]) for i in itens]


# --- /ranking ---


def test_ranking_gols_geral(client: TestClient, cenario: dict):
    r = client.get("/ranking")  # tipo=gols é o padrão
    assert r.status_code == 200
    assert _linhas(r.json()) == [(1, "Pedro", 3), (2, "João", 2), (3, "Ana", 1)]  # Bia (0) fica de fora


def test_ranking_empate_divide_posicao(client: TestClient, cenario: dict):
    r = client.get("/ranking", params={"tipo": "assistencias"})
    assert _linhas(r.json()) == [(1, "Ana", 1), (1, "João", 1)]

    r = client.get("/ranking", params={"tipo": "vitorias"})
    assert _linhas(r.json()) == [(1, "Pedro", 2), (2, "Ana", 1), (2, "João", 1)]


def test_ranking_de_uma_pelada(client: TestClient, cenario: dict):
    r = client.get("/ranking", params={"tipo": "gols", "pelada_id": cenario["p1"]})
    assert _linhas(r.json()) == [(1, "João", 2), (2, "Ana", 1), (2, "Pedro", 1)]

    r = client.get("/ranking", params={"tipo": "vitorias", "pelada_id": cenario["p2"]})
    assert _linhas(r.json()) == [(1, "Pedro", 1)]


def test_ranking_traz_estatisticas_completas(client: TestClient, cenario: dict):
    pedro = next(i for i in client.get("/ranking").json() if i["jogador"]["nome"] == "Pedro")
    assert pedro["estatisticas"] == {
        "partidas": 4, "vitorias": 2, "empates": 1, "derrotas": 1, "gols": 3, "assistencias": 0,
    }


def test_ranking_erros(client: TestClient, cenario: dict):
    assert client.get("/ranking", params={"tipo": "cartoes"}).status_code == 422
    assert client.get("/ranking", params={"pelada_id": 999}).status_code == 404


def test_ranking_vazio(client: TestClient):
    assert client.get("/ranking").json() == []


# --- /peladas/{id}/estatisticas ---


def test_estatisticas_da_pelada(client: TestClient, cenario: dict):
    r = client.get(f"/peladas/{cenario['p1']}/estatisticas")
    assert r.status_code == 200
    est = r.json()
    assert est["pelada_id"] == cenario["p1"]
    assert est["partidas_encerradas"] == 3
    assert est["equipes"] == [
        # gols contam na hora (inclui o da partida 4); V/E/D só das encerradas
        {"id": cenario["azul1"], "nome": "Azul", "partidas": 3, "vitorias": 1, "empates": 1,
         "derrotas": 1, "gols_marcados": 3, "gols_sofridos": 2},
        {"id": cenario["verde1"], "nome": "Verde", "partidas": 3, "vitorias": 1, "empates": 1,
         "derrotas": 1, "gols_marcados": 2, "gols_sofridos": 3},
    ]
    assert _linhas(est["artilheiros"]) == [(1, "João", 2), (2, "Ana", 1), (2, "Pedro", 1)]


def test_estatisticas_pelada_vazia_e_404(client: TestClient):
    pid = client.post(
        "/peladas", json={"data": "2026-11-14", "numero_times": 2, "jogadores_por_time": 6},
        headers={"X-API-Key": "chave-de-teste"},
    ).json()["id"]
    assert client.get(f"/peladas/{pid}/estatisticas").json() == {
        "pelada_id": pid, "partidas_encerradas": 0, "equipes": [], "artilheiros": [],
    }
    assert client.get("/peladas/999/estatisticas").status_code == 404


# --- /jogadores/{id} continua igual depois do refactor ---


def test_detalhe_do_jogador(client: TestClient, cenario: dict):
    est = client.get(f"/jogadores/{cenario['João']}").json()["estatisticas"]
    assert est == {"partidas": 3, "vitorias": 1, "empates": 1, "derrotas": 1, "gols": 2, "assistencias": 1}
    est = client.get(f"/jogadores/{cenario['Bia']}").json()["estatisticas"]
    assert est == {"partidas": 1, "vitorias": 0, "empates": 0, "derrotas": 1, "gols": 0, "assistencias": 0}
