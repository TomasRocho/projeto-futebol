import os

# Antes de importar o app: config de teste, banco em memória.
os.environ["API_KEY"] = "chave-de-teste"
os.environ["DATABASE_URL"] = "sqlite://"

from collections.abc import Iterator  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

import app.models  # noqa: E402, F401
from app.db import make_engine  # noqa: E402


@pytest.fixture
def session() -> Iterator[Session]:
    """Banco novo em memória para cada teste, com FKs ligadas."""
    engine = make_engine("sqlite://", poolclass=StaticPool)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()
