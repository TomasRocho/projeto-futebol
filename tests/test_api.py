from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import require_admin
from app.main import app


def test_health():
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}


def test_api_so_existe_sob_prefixo(client: TestClient):
    # URL absoluta ignora o base_url (.../api) da fixture
    assert client.get("http://testserver/jogadores").status_code == 404
    assert client.get("http://testserver/api/jogadores").status_code == 200


def test_admin_check():
    with TestClient(app) as client:
        assert client.get("/api/admin/check").status_code == 401
        assert client.get("/api/admin/check", headers={"X-API-Key": "errada"}).status_code == 401
        r = client.get("/api/admin/check", headers={"X-API-Key": "chave-de-teste"})
        assert r.status_code == 204


def _app_protegido() -> TestClient:
    mini = FastAPI()

    @mini.post("/escrita", dependencies=[Depends(require_admin)])
    def escrita():
        return {"ok": True}

    return TestClient(mini)


def test_escrita_sem_chave():
    assert _app_protegido().post("/escrita").status_code == 401


def test_escrita_chave_errada():
    r = _app_protegido().post("/escrita", headers={"X-API-Key": "errada"})
    assert r.status_code == 401


def test_escrita_chave_certa():
    r = _app_protegido().post("/escrita", headers={"X-API-Key": "chave-de-teste"})
    assert r.status_code == 200
