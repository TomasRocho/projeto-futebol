"""FastAPI servindo o build do React (produção). Usa um dist falso em pasta temporária."""

from pathlib import Path

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from app.frontend import montar_frontend


@pytest.fixture
def dist(tmp_path: Path) -> Path:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>APP</html>")
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log(1)")
    (tmp_path / "favicon.svg").write_text("<svg/>")
    (tmp_path.parent / "segredo.txt").write_text("não pode vazar")
    return tmp_path


@pytest.fixture
def client(dist: Path) -> TestClient:
    app = FastAPI()
    api = APIRouter(prefix="/api")

    @api.get("/health")
    def health():
        return {"status": "ok"}

    app.include_router(api)
    assert montar_frontend(app, dist)
    return TestClient(app)


def test_raiz_e_rotas_do_react_devolvem_index(client: TestClient):
    for url in ("/", "/peladas/3", "/jogadores/12", "/ranking?tipo=gols"):
        r = client.get(url)
        assert r.status_code == 200, url
        assert r.text == "<html>APP</html>"
        assert r.headers["cache-control"] == "no-cache"


def test_arquivos_do_build(client: TestClient):
    r = client.get("/assets/index-abc123.js")
    assert r.status_code == 200
    assert "immutable" in r.headers["cache-control"]
    assert client.get("/favicon.svg").text == "<svg/>"


def test_api_continua_api(client: TestClient):
    assert client.get("/api/health").json() == {"status": "ok"}
    r = client.get("/api/nao-existe")
    assert r.status_code == 404
    assert r.json() == {"detail": "Not Found"}


def test_nao_serve_arquivo_fora_do_dist(client: TestClient):
    for url in ("/../segredo.txt", "/%2e%2e/segredo.txt", "/assets/../../segredo.txt"):
        assert "não pode vazar" not in client.get(url).text, url


def test_sem_build_nao_faz_nada(tmp_path: Path):
    app = FastAPI()
    assert montar_frontend(app, tmp_path / "nao-existe") is False
    assert TestClient(app).get("/").status_code == 404
