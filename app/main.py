from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import create_db
from app.routers import estatisticas, jogadores, partidas, peladas


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db()
    yield


app = FastAPI(title="Projeto Futebol", lifespan=lifespan)
app.include_router(jogadores.router)
app.include_router(peladas.router)
app.include_router(partidas.router)
app.include_router(estatisticas.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
