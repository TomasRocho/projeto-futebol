from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import create_db
from app.routers import jogadores, peladas


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db()
    yield


app = FastAPI(title="Projeto Futebol", lifespan=lifespan)
app.include_router(jogadores.router)
app.include_router(peladas.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
