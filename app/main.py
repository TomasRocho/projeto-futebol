from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI, status

from app.auth import require_admin
from app.db import create_db
from app.routers import estatisticas, jogadores, partidas, peladas


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db()
    yield


app = FastAPI(title="Projeto Futebol", lifespan=lifespan)

# Toda a API fica sob /api: em produção o mesmo servidor serve o build do React,
# e /jogadores (página) não pode colidir com /api/jogadores (JSON).
api = APIRouter(prefix="/api")
api.include_router(jogadores.router)
api.include_router(peladas.router)
api.include_router(partidas.router)
api.include_router(estatisticas.router)


@api.get("/health", tags=["sistema"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@api.get(
    "/admin/check",
    tags=["sistema"],
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def admin_check() -> None:
    """204 se o X-API-Key está certo, 401 se não. O frontend usa para validar a chave."""


app.include_router(api)
