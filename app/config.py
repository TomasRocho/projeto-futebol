from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Sem default de propósito: sem API_KEY o app nem sobe (fail closed).
    api_key: str
    database_url: str = "sqlite:///./futebol.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]  (campos vêm do ambiente)
