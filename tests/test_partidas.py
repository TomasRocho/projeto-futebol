# pyright: reportArgumentType=false, reportOptionalMemberAccess=false

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Partida

ADMIN = {"X-API-Key": "chave-de-teste"}


def _pelada_sorteada(client: TestClient, n: int = 12, numero_times: int = 2) -> tuple[int, dict]:
    pid = client.post(
        "/peladas",
        json={"data": "2026-11-14", "numero_times": numero_times, "jogadores_por_time": 6},
        headers=ADMIN,
    ).json()["id"]
    ids = [
        client.post("/jogadores", json={"nome": f"J{i:02}", "rating": 3}, headers=ADMIN).json()["id"]
        for i in range(n)
    ]
    client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": ids}, headers=ADMIN)
    estado = client.post(f"/peladas/{pid}/sorteio", headers=ADMIN).json()
    return pid, estado


def _comecar(client: TestClient, pid: int) -> dict:
    r = client.post(f"/peladas/{pid}/partidas", headers=ADMIN)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture
def partida(client: TestClient) -> dict:
    """Partida em andamento, com 2 jogadores de cada lado à mão."""
    pid, _ = _pelada_sorteada(client)
    p = _comecar(client, pid)
    a1, a2 = (j["id"] for j in p["equipe_a"]["jogadores"][:2])
    b1, b2 = (j["id"] for j in p["equipe_b"]["jogadores"][:2])
    return p | {"A": p["equipe_a"]["id"], "B": p["equipe_b"]["id"], "a1": a1, "a2": a2, "b1": b1, "b2": b2}


def _gol(client: TestClient, partida: dict, **body):
    return client.post(f"/partidas/{partida['id']}/gols", json=body, headers=ADMIN)


# --- Começar partida ---


def test_comecar_partida(client: TestClient):
    pid, estado = _pelada_sorteada(client)
    p = _comecar(client, pid)

    assert p["numero"] == 1
    assert p["encerrada"] is False
    assert (p["penaltis_a"], p["penaltis_b"]) == (None, None)
    assert p["gols"] == []
    # escalação = elenco de cada equipe em quadra
    for lado, equipe in zip(("equipe_a", "equipe_b"), estado["equipes"]):
        assert p[lado]["id"] == equipe["id"]
        assert p[lado]["gols"] == 0
        assert p[lado]["jogadores"] == equipe["jogadores"]

    em_andamento = client.get(f"/peladas/{pid}").json()["partida_em_andamento"]
    assert em_andamento["id"] == p["id"]
    assert client.get(f"/partidas/{p['id']}").json() == p


def test_comecar_com_3_times_usa_as_equipes_em_quadra(client: TestClient):
    pid, estado = _pelada_sorteada(client, n=18, numero_times=3)
    em_quadra = [e["id"] for e in estado["equipes"] if e["ordem_fila"] is None]
    p = _comecar(client, pid)
    assert [p["equipe_a"]["id"], p["equipe_b"]["id"]] == em_quadra


def test_comecar_sem_sorteio_409(client: TestClient):
    pid = client.post(
        "/peladas", json={"data": "2026-11-14", "numero_times": 2, "jogadores_por_time": 6},
        headers=ADMIN,
    ).json()["id"]
    assert client.post(f"/peladas/{pid}/partidas", headers=ADMIN).status_code == 409


def test_comecar_com_partida_em_andamento_409(client: TestClient):
    pid, _ = _pelada_sorteada(client)
    _comecar(client, pid)
    assert client.post(f"/peladas/{pid}/partidas", headers=ADMIN).status_code == 409


def test_comecar_com_equipe_vazia_409(client: TestClient):
    pid, estado = _pelada_sorteada(client, n=2)  # 1 jogador por equipe
    unico = estado["equipes"][0]["jogadores"][0]["id"]
    client.delete(f"/peladas/{pid}/presencas/{unico}", headers=ADMIN)
    r = client.post(f"/peladas/{pid}/partidas", headers=ADMIN)
    assert r.status_code == 409
    assert "sem jogadores" in r.json()["detail"]


def test_numero_da_partida_incrementa(client: TestClient, session: Session):
    pid, _ = _pelada_sorteada(client)
    p1 = _comecar(client, pid)
    session.get(Partida, p1["id"]).encerrada = True  # até existir o /encerrar
    session.commit()
    assert _comecar(client, pid)["numero"] == 2


def test_escalacao_e_foto_do_inicio(client: TestClient, partida: dict):
    pid = partida["pelada_id"]
    client.patch(f"/peladas/{pid}/presencas/{partida['a1']}", json={"equipe_id": None}, headers=ADMIN)
    client.delete(f"/peladas/{pid}/presencas/{partida['b1']}", headers=ADMIN)
    depois = client.get(f"/partidas/{partida['id']}").json()
    assert depois["equipe_a"]["jogadores"] == partida["equipe_a"]["jogadores"]
    assert depois["equipe_b"]["jogadores"] == partida["equipe_b"]["jogadores"]


def test_partida_404_e_401(client: TestClient):
    assert client.get("/partidas/999").status_code == 404
    assert client.post("/peladas/999/partidas", headers=ADMIN).status_code == 404
    pid, _ = _pelada_sorteada(client)
    assert client.post(f"/peladas/{pid}/partidas").status_code == 401


# --- Gols ---


def test_gol_com_assistencia(client: TestClient, partida: dict):
    r = _gol(client, partida, equipe_id=partida["A"], autor_id=partida["a1"], assistente_id=partida["a2"])
    assert r.status_code == 201
    p = r.json()
    assert (p["equipe_a"]["gols"], p["equipe_b"]["gols"]) == (1, 0)
    (gol,) = p["gols"]
    assert gol["autor"]["id"] == partida["a1"]
    assert gol["assistente"]["id"] == partida["a2"]
    assert gol["gol_contra"] is False


def test_gol_contra(client: TestClient, partida: dict):
    # b1 (do B) faz contra: beneficia o A
    r = _gol(client, partida, equipe_id=partida["A"], autor_id=partida["b1"], gol_contra=True)
    assert r.status_code == 201
    p = r.json()
    assert (p["equipe_a"]["gols"], p["equipe_b"]["gols"]) == (1, 0)
    assert p["gols"][0]["assistente"] is None


@pytest.mark.parametrize(
    ("body", "msg"),
    [
        (dict(equipe="X", autor="a1"), "não está jogando"),
        (dict(equipe="A", autor="fora"), "autor não está escalado"),
        (dict(equipe="A", autor="b1"), "gol_contra=true"),
        (dict(equipe="A", autor="a1", contra=True), "adversária"),
        (dict(equipe="A", autor="b1", contra=True, assist="b2"), "não tem assistência"),
        (dict(equipe="A", autor="a1", assist="a1"), "mesma pessoa"),
        (dict(equipe="A", autor="a1", assist="b1"), "outra equipe"),
        (dict(equipe="A", autor="a1", assist="fora"), "assistente não está escalado"),
    ],
)
def test_gol_invalido(client: TestClient, partida: dict, body: dict, msg: str):
    (fora,) = [
        client.post("/jogadores", json={"nome": "Fora", "rating": 1}, headers=ADMIN).json()["id"]
    ]
    ids = partida | {"fora": fora, "X": 999}
    r = _gol(
        client, partida,
        equipe_id=ids[body["equipe"]],
        autor_id=ids[body["autor"]],
        assistente_id=ids[body["assist"]] if "assist" in body else None,
        gol_contra=body.get("contra", False),
    )
    assert r.status_code == 422
    assert msg in r.json()["detail"]
    assert client.get(f"/partidas/{partida['id']}").json()["gols"] == []


def test_gol_em_partida_encerrada_409(client: TestClient, session: Session, partida: dict):
    session.get(Partida, partida["id"]).encerrada = True
    session.commit()
    r = _gol(client, partida, equipe_id=partida["A"], autor_id=partida["a1"])
    assert r.status_code == 409


def test_apagar_gol(client: TestClient, partida: dict):
    p = _gol(client, partida, equipe_id=partida["B"], autor_id=partida["b1"]).json()
    gol_id = p["gols"][0]["id"]
    url = f"/partidas/{partida['id']}/gols/{gol_id}"

    assert client.delete(url).status_code == 401
    assert client.delete(url, headers=ADMIN).status_code == 204
    depois = client.get(f"/partidas/{partida['id']}").json()
    assert depois["gols"] == []
    assert depois["equipe_b"]["gols"] == 0
    assert client.delete(url, headers=ADMIN).status_code == 404


def test_apagar_gol_de_partida_encerrada_409(client: TestClient, session: Session, partida: dict):
    gol_id = _gol(client, partida, equipe_id=partida["A"], autor_id=partida["a1"]).json()["gols"][0]["id"]
    session.get(Partida, partida["id"]).encerrada = True
    session.commit()
    assert client.delete(f"/partidas/{partida['id']}/gols/{gol_id}", headers=ADMIN).status_code == 409


def test_gol_conta_nas_estatisticas(client: TestClient, partida: dict):
    _gol(client, partida, equipe_id=partida["A"], autor_id=partida["a1"], assistente_id=partida["a2"])
    est = client.get(f"/jogadores/{partida['a1']}").json()["estatisticas"]
    assert est["gols"] == 1
    assert est["partidas"] == 0  # ainda não encerrada


def test_gol_401(client: TestClient, partida: dict):
    r = client.post(
        f"/partidas/{partida['id']}/gols", json={"equipe_id": partida["A"], "autor_id": partida["a1"]}
    )
    assert r.status_code == 401
