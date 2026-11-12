# pyright: reportArgumentType=false, reportOptionalMemberAccess=false
# (ids dos models são "int | None" até o flush; nos testes isso é ruído)

from datetime import date

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Escalacao, Gol, Jogador, Partida, Pelada, Presenca, Time

ADMIN = {"X-API-Key": "chave-de-teste"}


def _criar(client: TestClient, nome: str = "João", rating: int = 3) -> dict:
    r = client.post("/jogadores", json={"nome": nome, "rating": rating}, headers=ADMIN)
    assert r.status_code == 201, r.text
    return r.json()


# --- CRUD ---


def test_criar_e_detalhar(client: TestClient):
    j = _criar(client, "  João  ", 4)
    assert j == {"id": j["id"], "nome": "João", "rating": 4}  # nome sem espaços nas pontas

    r = client.get(f"/jogadores/{j['id']}")  # leitura pública, sem chave
    assert r.status_code == 200
    assert r.json()["estatisticas"] == {
        "partidas": 0, "vitorias": 0, "empates": 0, "derrotas": 0, "gols": 0, "assistencias": 0,
    }


def test_listar_ordenado_por_nome(client: TestClient):
    for nome in ("Pedro", "Ana", "João"):
        _criar(client, nome)
    assert [j["nome"] for j in client.get("/jogadores").json()] == ["Ana", "João", "Pedro"]


def test_escrita_exige_chave(client: TestClient):
    j = _criar(client)
    assert client.post("/jogadores", json={"nome": "X", "rating": 1}).status_code == 401
    assert client.patch(f"/jogadores/{j['id']}", json={"rating": 1}).status_code == 401
    assert client.delete(f"/jogadores/{j['id']}").status_code == 401


def test_validacao(client: TestClient):
    for body in (
        {"nome": "X", "rating": 6},
        {"nome": "X", "rating": -1},
        {"nome": "", "rating": 3},
        {"nome": "   ", "rating": 3},
        {"nome": "X"},
    ):
        assert client.post("/jogadores", json=body, headers=ADMIN).status_code == 422, body


def test_patch_parcial(client: TestClient):
    j = _criar(client, "João", 3)
    r = client.patch(f"/jogadores/{j['id']}", json={"rating": 5}, headers=ADMIN)
    assert r.status_code == 200
    assert r.json() == {"id": j["id"], "nome": "João", "rating": 5}


def test_patch_null_e_invalido(client: TestClient):
    j = _criar(client)
    for body in ({"rating": None}, {"nome": None}, {"rating": 9}):
        r = client.patch(f"/jogadores/{j['id']}", json=body, headers=ADMIN)
        assert r.status_code == 422, body


def test_404(client: TestClient):
    assert client.get("/jogadores/999").status_code == 404
    assert client.patch("/jogadores/999", json={"rating": 1}, headers=ADMIN).status_code == 404
    assert client.delete("/jogadores/999", headers=ADMIN).status_code == 404


def test_apagar_sem_historico(client: TestClient):
    j = _criar(client)
    r = client.delete(f"/jogadores/{j['id']}", headers=ADMIN)
    assert r.status_code == 204
    assert r.content == b""
    assert client.get(f"/jogadores/{j['id']}").status_code == 404


def test_apagar_com_historico_409(client: TestClient, session: Session):
    j = _criar(client)
    pelada = Pelada(data=date(2026, 11, 12), numero_times=2, jogadores_por_time=6)
    session.add(pelada)
    session.flush()
    session.add(Presenca(pelada_id=pelada.id, jogador_id=j["id"]))
    session.commit()

    assert client.delete(f"/jogadores/{j['id']}", headers=ADMIN).status_code == 409
    assert client.get(f"/jogadores/{j['id']}").status_code == 200  # continua lá


# --- Estatísticas ---


def test_estatisticas(client: TestClient, session: Session):
    """João e Ana no Azul, Pedro no Verde, 4 partidas:
    1. Azul 1 x 2 Verde  (gol do João c/ assist. da Ana; gol do Pedro; gol contra do João)
    2. Azul 1 x 0 Verde  (gol do João)
    3. Azul 0 x 0 Verde, pênaltis 4 x 3  -> conta como empate
    4. em andamento: gol da Ana c/ assist. do João -> conta gol/assist., não conta partida
    """
    joao, ana, pedro = (Jogador(nome=n, rating=3) for n in ("João", "Ana", "Pedro"))
    pelada = Pelada(data=date(2026, 11, 12), numero_times=2, jogadores_por_time=6)
    session.add_all([joao, ana, pedro, pelada])
    session.flush()
    azul, verde = Time(pelada_id=pelada.id, nome="Azul"), Time(pelada_id=pelada.id, nome="Verde")
    session.add_all([azul, verde])
    session.flush()

    def partida(numero, gols, encerrada=True, penaltis=(None, None)):
        p = Partida(
            pelada_id=pelada.id, numero=numero, equipe_a_id=azul.id, equipe_b_id=verde.id,
            encerrada=encerrada, penaltis_a=penaltis[0], penaltis_b=penaltis[1],
        )
        session.add(p)
        session.flush()
        session.add_all(
            Escalacao(partida_id=p.id, jogador_id=j.id, equipe_id=e.id)
            for j, e in ((joao, azul), (ana, azul), (pedro, verde))
        )
        session.flush()
        session.add_all(
            Gol(
                partida_id=p.id, equipe_id=eq.id, autor_id=autor.id,
                assistente_id=assist.id if assist else None, gol_contra=contra,
            )
            for eq, autor, assist, contra in gols
        )
        session.flush()

    partida(1, [(azul, joao, ana, False), (verde, pedro, None, False), (verde, joao, None, True)])
    partida(2, [(azul, joao, None, False)])
    partida(3, [], penaltis=(4, 3))
    partida(4, [(azul, ana, joao, False)], encerrada=False)
    session.commit()

    def est(j):
        return client.get(f"/jogadores/{j.id}").json()["estatisticas"]

    assert est(joao) == {
        "partidas": 3, "vitorias": 1, "empates": 1, "derrotas": 1, "gols": 2, "assistencias": 1,
    }
    assert est(ana) == {
        "partidas": 3, "vitorias": 1, "empates": 1, "derrotas": 1, "gols": 1, "assistencias": 1,
    }
    assert est(pedro) == {
        "partidas": 3, "vitorias": 1, "empates": 1, "derrotas": 1, "gols": 1, "assistencias": 0,
    }
