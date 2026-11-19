from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Sem default de propósito: sem API_KEY o app nem sobe (fail closed).
    api_key: str
    # Local: SQLite. Produção: a connection string do Neon (PostgreSQL).
    database_url: str = "sqlite:///./futebol.db"

    @field_validator("database_url")
    @classmethod
    def _driver_postgres(cls, url: str) -> str:
        """O Neon entrega "postgresql://..."; o SQLAlchemy precisa saber que o driver é o psycopg 3."""
        for prefixo in ("postgres://", "postgresql://"):
            if url.startswith(prefixo):
                return "postgresql+psycopg://" + url.removeprefix(prefixo)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]  (campos vêm do ambiente)
