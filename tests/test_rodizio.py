"""Encerrar partida + rodízio. Cenários de Diagrama-Classes.md ("Fila e rodízio" e "Empate").

O sorteio cria as equipes nesta ordem: Azul, Vermelho (em quadra), Verde (fila 1), Amarelo (fila 2).
Na 1ª partida, A = Azul e B = Vermelho.
"""

from fastapi.testclient import TestClient

ADMIN = {"X-API-Key": "chave-de-teste"}


# --- helpers ---


def _pelada(client: TestClient, n: int, numero_times: int = 2, por_time: int = 6) -> int:
    pid = client.post(
        "/peladas",
        json={"data": "2026-11-14", "numero_times": numero_times, "jogadores_por_time": por_time},
        headers=ADMIN,
    ).json()["id"]
    ids = [
        client.post("/jogadores", json={"nome": f"J{i:02}", "rating": 3}, headers=ADMIN).json()["id"]
        for i in range(n)
    ]
    client.put(f"/peladas/{pid}/presencas", json={"jogador_ids": ids}, headers=ADMIN)
    client.post(f"/peladas/{pid}/sorteio", headers=ADMIN)
    return pid


def _estado(client: TestClient, pid: int) -> dict:
    return client.get(f"/peladas/{pid}").json()


def _equipes(estado: dict) -> dict[str, tuple[int | None, set[int]]]:
    """nome -> (ordem_fila, ids do elenco)"""
    return {
        e["nome"]: (e["ordem_fila"], {j["id"] for j in e["jogadores"]}) for e in estado["equipes"]
    }


def _fila(estado: dict) -> list[str]:
    return [e["nome"] for e in estado["equipes"] if e["ordem_fila"] is not None]


def _em_quadra(estado: dict) -> list[str]:
    return [e["nome"] for e in estado["equipes"] if e["ordem_fila"] is None]


def _esperando(estado: dict) -> set[int]:
    return {j["id"] for j in estado["esperando"]}


def _comecar(client: TestClient, pid: int) -> dict:
    r = client.post(f"/peladas/{pid}/partidas", headers=ADMIN)
    assert r.status_code == 201, r.text
    return r.json()


def _gol(client: TestClient, partida: dict, lado: str) -> None:
    equipe = partida[f"equipe_{lado}"]
    r = client.post(
        f"/partidas/{partida['id']}/gols",
        json={"equipe_id": equipe["id"], "autor_id": equipe["jogadores"][0]["id"]},
        headers=ADMIN,
    )
    assert r.status_code == 201, r.text


def _encerrar(client: TestClient, partida: dict, **penaltis):
    return client.post(
        f"/partidas/{partida['id']}/encerrar", json=penaltis or None, headers=ADMIN
    )


def _jogar(client: TestClient, pid: int, vencedor: str | None, **penaltis) -> dict:
    """Começa, faz 1 gol do vencedor ('a'/'b'; None = 0 x 0) e encerra. Devolve o novo estado."""
    p = _comecar(client, pid)
    if vencedor:
        _gol(client, p, vencedor)
    r = _encerrar(client, p, **penaltis)
    assert r.status_code == 200, r.text
    return r.json()


# --- 2 equipes ---


def test_2_times_vitoria_sem_avulsos(client: TestClient):
    pid = _pelada(client, 12)
    antes = _equipes(_estado(client, pid))
    p = _comecar(client, pid)
    _gol(client, p, "a")
    depois = _encerrar(client, p).json()

    assert _equipes(depois) == antes  # ninguém sai de quadra, ninguém troca
    assert depois["partida_em_andamento"] is None
    assert client.get(f"/partidas/{p['id']}").json()["encerrada"] is True

    vencedor = p["equipe_a"]["jogadores"][0]["id"]
    perdedor = p["equipe_b"]["jogadores"][0]["id"]
    assert client.get(f"/jogadores/{vencedor}").json()["estatisticas"]["vitorias"] == 1
    assert client.get(f"/jogadores/{perdedor}").json()["estatisticas"]["derrotas"] == 1


def test_2_times_avulsos_entram_no_perdedor(client: TestClient):
    pid = _pelada(client, 14)  # 12 jogam, 2 esperam
    antes = _estado(client, pid)
    esperavam = _esperando(antes)
    azul_antes, vermelho_antes = _equipes(antes)["Azul"][1], _equipes(antes)["Vermelho"][1]

    depois = _jogar(client, pid, vencedor="a")  # Vermelho perde
    azul, vermelho = _equipes(depois)["Azul"][1], _equipes(depois)["Vermelho"][1]

    assert azul == azul_antes
    assert len(vermelho) == 6
    assert esperavam <= vermelho
    assert _esperando(depois) == vermelho_antes - vermelho
    assert len(_esperando(depois)) == 2


def test_mais_avulsos_que_jogadores_no_perdedor(client: TestClient):
    pid = _pelada(client, 16)  # 12 jogam, 4 esperam
    estado = _estado(client, pid)
    esperavam = _esperando(estado)
    vermelho = sorted(_equipes(estado)["Vermelho"][1])
    for jid in vermelho[:4]:  # 4 vão embora: Vermelho fica com 2
        client.delete(f"/peladas/{pid}/presencas/{jid}", headers=ADMIN)

    depois = _jogar(client, pid, vencedor="a")
    novo_vermelho = _equipes(depois)["Vermelho"][1]
    assert len(novo_vermelho) == 2 and novo_vermelho <= esperavam  # o time inteiro trocou
    assert _esperando(depois) == (esperavam - novo_vermelho) | set(vermelho[4:])


def test_empate_2_times_exige_penaltis(client: TestClient):
    pid = _pelada(client, 13)  # 1 avulso, para ver quem perdeu
    (avulso,) = _esperando(_estado(client, pid))
    p = _comecar(client, pid)

    for body in ({}, {"penaltis_a": 3}, {"penaltis_a": 4, "penaltis_b": 4},
                 {"penaltis_a": -1, "penaltis_b": 2}):
        assert _encerrar(client, p, **body).status_code == 422, body

    depois = _encerrar(client, p, penaltis_a=3, penaltis_b=5).json()  # A (Azul) perde nos pênaltis
    assert avulso in _equipes(depois)["Azul"][1]
    partida = client.get(f"/partidas/{p['id']}").json()
    assert (partida["penaltis_a"], partida["penaltis_b"]) == (3, 5)

    # nas estatísticas, pênalti = empate
    jogador = p["equipe_b"]["jogadores"][0]["id"]
    est = client.get(f"/jogadores/{jogador}").json()["estatisticas"]
    assert (est["vitorias"], est["empates"], est["derrotas"]) == (0, 1, 0)


def test_penaltis_sem_empate_422(client: TestClient):
    pid = _pelada(client, 12)
    p = _comecar(client, pid)
    _gol(client, p, "a")
    r = _encerrar(client, p, penaltis_a=5, penaltis_b=4)
    assert r.status_code == 422
    assert "não houve empate" in r.json()["detail"]


# --- 3 equipes ---


def test_3_times_perdedor_vai_para_fila(client: TestClient):
    pid = _pelada(client, 21, numero_times=3, por_time=7)

    depois = _jogar(client, pid, vencedor="a")  # Azul x Vermelho: Vermelho perde
    assert _em_quadra(depois) == ["Azul", "Verde"]
    assert _fila(depois) == ["Vermelho"]

    p2 = _comecar(client, pid)
    assert (p2["equipe_a"]["nome"], p2["equipe_b"]["nome"]) == ("Azul", "Verde")
    _gol(client, p2, "b")  # Azul perde
    depois = _encerrar(client, p2).json()
    assert _em_quadra(depois) == ["Vermelho", "Verde"]
    assert _fila(depois) == ["Azul"]


def test_3_times_avulsos_vao_com_o_perdedor_para_fila(client: TestClient):
    pid = _pelada(client, 23, numero_times=3, por_time=7)  # 2 esperam
    esperavam = _esperando(_estado(client, pid))
    depois = _jogar(client, pid, vencedor="a")
    ordem, vermelho = _equipes(depois)["Vermelho"]
    assert ordem == 1
    assert esperavam <= vermelho


def test_empate_3_times_vai_nos_penaltis(client: TestClient):
    pid = _pelada(client, 21, numero_times=3, por_time=7)
    p = _comecar(client, pid)
    assert _encerrar(client, p).status_code == 422
    depois = _encerrar(client, p, penaltis_a=5, penaltis_b=4).json()  # Vermelho perde
    assert _fila(depois) == ["Vermelho"]


# --- 4 equipes ---


def test_4_times_derrota(client: TestClient):
    pid = _pelada(client, 24, numero_times=4)
    depois = _jogar(client, pid, vencedor="a")
    assert _em_quadra(depois) == ["Azul", "Verde"]
    assert _fila(depois) == ["Amarelo", "Vermelho"]


def test_4_times_empate_proibe_penaltis(client: TestClient):
    pid = _pelada(client, 24, numero_times=4)
    p = _comecar(client, pid)
    r = _encerrar(client, p, penaltis_a=5, penaltis_b=4)
    assert r.status_code == 422
    assert "4 equipes" in r.json()["detail"]


def test_4_times_empate_na_primeira_partida_ordem_sorteada(client: TestClient):
    pid = _pelada(client, 26, numero_times=4)  # 2 esperam
    esperavam = _esperando(_estado(client, pid))

    depois = _jogar(client, pid, vencedor=None)  # 0 x 0: as duas saem
    assert _em_quadra(depois) == ["Verde", "Amarelo"]
    fila = _fila(depois)
    assert set(fila) == {"Azul", "Vermelho"}
    frente = fila[0]
    assert esperavam <= _equipes(depois)[frente][1]  # avulsos entram na que ficou na frente


def test_4_times_empate_quem_esta_ha_mais_tempo_vai_para_o_fim(client: TestClient):
    pid = _pelada(client, 26, numero_times=4)

    # Partida 1: Azul ganha do Vermelho. Azul está em quadra desde a 1, Verde entra na 2.
    depois = _jogar(client, pid, vencedor="a")
    assert _em_quadra(depois) == ["Azul", "Verde"]
    assert _fila(depois) == ["Amarelo", "Vermelho"]
    esperavam = _esperando(depois)  # os 2 que saíram do Vermelho

    # Partida 2: Azul x Verde, 0 x 0. Azul (há mais tempo) vai para o fim; Verde fica na frente.
    depois = _jogar(client, pid, vencedor=None)
    assert _em_quadra(depois) == ["Vermelho", "Amarelo"]
    assert _fila(depois) == ["Verde", "Azul"]
    assert esperavam <= _equipes(depois)["Verde"][1]


# --- Erros ---


def test_encerrar_erros(client: TestClient):
    pid = _pelada(client, 12)
    p = _comecar(client, pid)
    _gol(client, p, "a")
    assert client.post(f"/partidas/{p['id']}/encerrar").status_code == 401
    assert client.post("/partidas/999/encerrar", headers=ADMIN).status_code == 404
    assert _encerrar(client, p).status_code == 200
    assert _encerrar(client, p).status_code == 409  # já encerrada


def test_varias_partidas_seguidas(client: TestClient):
    """Fluxo completo com 4 equipes: o rodízio mantém sempre 2 em quadra e 2 na fila."""
    pid = _pelada(client, 27, numero_times=4)
    for vencedor in ("a", "b", None, "a", None, "b"):
        estado = _jogar(client, pid, vencedor)
        assert len(_em_quadra(estado)) == 2
        assert sorted(e["ordem_fila"] for e in estado["equipes"] if e["ordem_fila"]) == [1, 2]
        assert sum(len(e["jogadores"]) for e in estado["equipes"]) == 24
        assert len(estado["esperando"]) == 3


# --- Lista de partidas do dia ---


def test_listar_partidas_do_dia(client: TestClient):
    pid = _pelada(client, 12)
    assert client.get(f"/peladas/{pid}/partidas").json() == []

    _jogar(client, pid, vencedor="a")
    _jogar(client, pid, vencedor=None, penaltis_a=2, penaltis_b=4)
    andamento = _comecar(client, pid)
    _gol(client, andamento, "b")

    r = client.get(f"/peladas/{pid}/partidas")
    assert r.status_code == 200
    linhas = [
        (p["numero"], p["encerrada"], p["equipe_a"]["nome"], p["equipe_a"]["gols"],
         p["equipe_b"]["gols"], p["equipe_b"]["nome"], p["penaltis_a"], p["penaltis_b"])
        for p in r.json()
    ]
    assert linhas == [
        (1, True, "Azul", 1, 0, "Vermelho", None, None),
        (2, True, "Azul", 0, 0, "Vermelho", 2, 4),
        (3, False, "Azul", 0, 1, "Vermelho", None, None),
    ]
    assert client.get("/peladas/999/partidas").status_code == 404
