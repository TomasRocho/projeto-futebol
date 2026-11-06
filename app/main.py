from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import create_db


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db()
    yield


app = FastAPI(title="Projeto Futebol", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
