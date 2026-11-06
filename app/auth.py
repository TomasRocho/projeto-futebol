import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import Settings, get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_admin(
    key: str | None = Depends(_api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    """Dependency das rotas de escrita. Leitura não usa isto."""
    if key is None or not secrets.compare_digest(key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="X-API-Key ausente ou inválida",
        )
