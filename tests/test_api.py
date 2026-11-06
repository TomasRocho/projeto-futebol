from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.auth import require_admin
from app.main import app


def test_health():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}


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
