from collections.abc import Iterator

from sqlalchemy import Engine, event
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def make_engine(url: str, **kwargs) -> Engine:
    """Cria o engine. No SQLite, liga as FKs em TODA conexão nova."""
    is_sqlite = url.startswith("sqlite")
    if is_sqlite:
        # O FastAPI pode usar a conexão em outra thread.
        kwargs.setdefault("connect_args", {"check_same_thread": False})

    engine = create_engine(url, **kwargs)

    if is_sqlite:

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.close()

    return engine


engine = make_engine(get_settings().database_url)


def create_db() -> None:
    import app.models  # noqa: F401  (registra as tabelas no metadata)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
