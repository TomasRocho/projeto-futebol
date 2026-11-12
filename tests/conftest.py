import os

# Antes de importar o app: config de teste, banco em memória.
os.environ["API_KEY"] = "chave-de-teste"
os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import Engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

from app import models  # noqa: E402, F401  (registra as tabelas)
from app.db import get_session, make_engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402


@pytest.fixture
def engine() -> Iterator[Engine]:
    """Banco novo em memória para cada teste, com FKs ligadas."""
    eng = make_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    with Session(engine) as s:
        yield s


@pytest.fixture
def client(engine: Engine) -> Iterator[TestClient]:
    """Cliente HTTP da API usando o mesmo banco do teste."""

    def _session() -> Iterator[Session]:
        with Session(engine) as s:
            yield s

    fastapi_app.dependency_overrides[get_session] = _session
    with TestClient(fastapi_app) as c:
        yield c
    fastapi_app.dependency_overrides.clear()
