# pyright: reportArgumentType=false, reportOptionalMemberAccess=false, reportReturnType=false

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models import Partida, Presenca, Time

ADMIN = {"X-API-Key": "chave-de-teste"}
PELADA = {"data": "2026-11-14", "numero_times": 2, "jogadores_por_time": 6}


def _pelada(client: TestClient, **extra) -> int:
    r = client.post("/peladas", json=PELADA | extra, headers=ADMIN)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _jogadores(client: TestClient, *nomes: str, rating: int = 3) -> list[int]:
    ids = []
    for nome in nomes:
        r = client.post("/jogadores", json={"nome": nome, "rating": rating}, headers=ADMIN)
        ids.append(r.json()["id"])
    return ids


def _equipes(session: Session, pelada_id: int, *nomes_fila: tuple[str, int | None]) -> list[int]:
    """Simula o sorteio criando as equipes direto no banco."""
    equipes = [Time(pelada_id=pelada_id, nome=n, ordem_fila=f) for n, f in nomes_fila]
    session.add_all(equipes)
    session.commit()
    return [e.id for e in equipes]


def _nomes(jogadores: list[dict]) -> list[str]:
    return [j["nome"] for j in jogadores]


# --- Pelada ---


def test_criar_e_estado_vazio(client: TestClient):
    pid = _pelada(client)
    r = client.get(f"/peladas/{pid}")
    assert r.status_code == 200
    assert r.json() == PELADA | {
        "id": pid, "equipes": [], "esperando": [], "partida_em_andamento": None,
    }


def test_validacao_pelada(client: TestClient):
    for extra in ({"numero_times": 1}, {"numero_times": 5}, {"jogadores_por_time": 8},
                  {"data": "ontem"}):
        r = client.post("/peladas", json=PELADA | extra, headers=ADMIN)
        assert r.status_code == 422, extra


def test_listar_mais_recente_primeiro(client: TestClient):
    _pelada(client, data="2026-11-07")
    _pelada(client, data="2026-11-21")
    _pelada(client, data="2026-11-14")
    assert [p["data"] for p in client.get("/peladas").json()] == [
        "2026-11-21", "2026-11-14", "2026-11-07",
    ]


def test_escrita_exige_chave(client: TestClient):
    pid = _pelada(client)
    assert client.post("/peladas", json=PELADA).status_code == 401
    assert client.delete(f"/peladas/{pid}").status_code == 401
    assert client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": []}).status_code == 401
    assert client.post(f"/peladas/{pid}/presencas", json={"jogador_id": 1}).status_code == 401
    assert client.patch(f"/peladas/{pid}/presencas/1", json={"equipe_id": None}).status_code == 401
    assert client.delete(f"/peladas/{pid}/presencas/1").status_code == 401


def test_404(client: TestClient):
    assert client.get("/peladas/999").status_code == 404
    assert client.delete("/peladas/999", headers=ADMIN).status_code == 404
    r = client.put("/peladas/999/presencas", json={"jogador_ids": []}, headers=ADMIN)
    assert r.status_code == 404


def test_apagar_pelada_mantem_jogadores(client: TestClient, session: Session):
    pid = _pelada(client)
    ids = _jogadores(client, "Ana", "João")
    client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": ids}, headers=ADMIN)

    assert client.delete(f"/peladas/{pid}", headers=ADMIN).status_code == 204
    assert client.get(f"/peladas/{pid}").status_code == 404
    assert session.exec(select(Presenca)).all() == []
    assert len(client.get("/jogadores").json()) == 2


# --- Presenças ---


def test_definir_presencas_substitui_lista(client: TestClient):
    pid = _pelada(client)
    ana, joao, pedro = _jogadores(client, "Ana", "João", "Pedro")
    url = f"/peladas/{pid}/presencas"

    r = client.put(url, json={"jogador_ids": [pedro, ana, ana]}, headers=ADMIN)  # duplicado ok
    assert r.status_code == 200
    assert _nomes(r.json()["esperando"]) == ["Ana", "Pedro"]

    r = client.put(url, json={"jogador_ids": [joao]}, headers=ADMIN)
    assert _nomes(r.json()["esperando"]) == ["João"]


def test_definir_presencas_jogador_inexistente(client: TestClient):
    pid = _pelada(client)
    (ana,) = _jogadores(client, "Ana")
    r = client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": [ana, 998, 999]}, headers=ADMIN)
    assert r.status_code == 422
    assert "[998, 999]" in r.json()["detail"]
    assert client.get(f"/peladas/{pid}").json()["esperando"] == []  # nada mudou


def test_definir_presencas_depois_do_sorteio_409(client: TestClient, session: Session):
    pid = _pelada(client)
    _equipes(session, pid, ("Azul", None), ("Verde", None))
    r = client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": []}, headers=ADMIN)
    assert r.status_code == 409


def test_adicionar_presenca(client: TestClient):
    pid = _pelada(client)
    (ana,) = _jogadores(client, "Ana")
    url = f"/peladas/{pid}/presencas"

    r = client.post(url, json={"jogador_id": ana}, headers=ADMIN)
    assert r.status_code == 201
    assert _nomes(r.json()["esperando"]) == ["Ana"]

    assert client.post(url, json={"jogador_id": ana}, headers=ADMIN).status_code == 409
    assert client.post(url, json={"jogador_id": 999}, headers=ADMIN).status_code == 422


def test_mover_jogador(client: TestClient, session: Session):
    pid = _pelada(client)
    ana, joao = _jogadores(client, "Ana", "João")
    client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": [ana, joao]}, headers=ADMIN)
    azul = _equipes(session, pid, ("Azul", None), ("Verde", None))[0]

    r = client.patch(f"/peladas/{pid}/presencas/{ana}", json={"equipe_id": azul}, headers=ADMIN)
    assert r.status_code == 200
    estado = r.json()
    assert _nomes(estado["equipes"][0]["jogadores"]) == ["Ana"]
    assert _nomes(estado["esperando"]) == ["João"]

    r = client.patch(f"/peladas/{pid}/presencas/{ana}", json={"equipe_id": None}, headers=ADMIN)
    assert _nomes(r.json()["esperando"]) == ["Ana", "João"]


def test_mover_jogador_erros(client: TestClient, session: Session):
    pid = _pelada(client)
    outra = _pelada(client, data="2026-11-21")
    ids = _jogadores(client, *[f"J{i}" for i in range(7)])
    client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": ids}, headers=ADMIN)
    (azul,) = _equipes(session, pid, ("Azul", None))
    (de_outra,) = _equipes(session, outra, ("Azul", None))
    url = f"/peladas/{pid}/presencas"

    # equipe de outra pelada / inexistente
    assert client.patch(f"{url}/{ids[0]}", json={"equipe_id": de_outra}, headers=ADMIN).status_code == 422
    assert client.patch(f"{url}/{ids[0]}", json={"equipe_id": 999}, headers=ADMIN).status_code == 422
    # body sem equipe_id (é obrigatório, mesmo que null)
    assert client.patch(f"{url}/{ids[0]}", json={}, headers=ADMIN).status_code == 422
    # jogador que não está na pelada
    (fora,) = _jogadores(client, "Fora")
    assert client.patch(f"{url}/{fora}", json={"equipe_id": azul}, headers=ADMIN).status_code == 404

    # enche a equipe (6 por time) e o 7º leva 409
    for jid in ids[:6]:
        assert client.patch(f"{url}/{jid}", json={"equipe_id": azul}, headers=ADMIN).status_code == 200
    assert client.patch(f"{url}/{ids[6]}", json={"equipe_id": azul}, headers=ADMIN).status_code == 409
    # mover para a própria equipe cheia não é erro
    assert client.patch(f"{url}/{ids[0]}", json={"equipe_id": azul}, headers=ADMIN).status_code == 200


def test_remover_presenca(client: TestClient):
    pid = _pelada(client)
    ana, joao = _jogadores(client, "Ana", "João")
    client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": [ana, joao]}, headers=ADMIN)

    assert client.delete(f"/peladas/{pid}/presencas/{ana}", headers=ADMIN).status_code == 204
    assert _nomes(client.get(f"/peladas/{pid}").json()["esperando"]) == ["João"]
    assert client.delete(f"/peladas/{pid}/presencas/{ana}", headers=ADMIN).status_code == 404


# --- Estado ---


def test_estado_completo(client: TestClient, session: Session):
    """Equipes em quadra primeiro, depois a fila; rating médio; avulsos; partida em andamento."""
    pid = _pelada(client, numero_times=3)
    ana, bia = _jogadores(client, "Ana", "Bia", rating=5)
    caio, davi = _jogadores(client, "Caio", "Davi", rating=2)
    (edu,) = _jogadores(client, "Edu", rating=1)
    client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": [ana, bia, caio, davi, edu]},
               headers=ADMIN)
    _, azul, verde = _equipes(session, pid, ("Amarelo", 1), ("Azul", None), ("Verde", None))
    for jid, eq in ((ana, azul), (caio, azul), (bia, verde)):
        session.get(Presenca, {"pelada_id": pid, "jogador_id": jid}).equipe_id = eq
    session.add(Partida(pelada_id=pid, numero=1, equipe_a_id=azul, equipe_b_id=verde))
    session.commit()

    estado = client.get(f"/peladas/{pid}").json()
    assert [(e["nome"], e["ordem_fila"], e["rating_medio"], _nomes(e["jogadores"]))
            for e in estado["equipes"]] == [
        ("Azul", None, 3.5, ["Ana", "Caio"]),
        ("Verde", None, 5.0, ["Bia"]),
        ("Amarelo", 1, None, []),
    ]
    assert _nomes(estado["esperando"]) == ["Davi", "Edu"]
    assert estado["partida_em_andamento"] == {
        "id": estado["partida_em_andamento"]["id"], "numero": 1,
        "equipe_a_id": azul, "equipe_b_id": verde,
    }
