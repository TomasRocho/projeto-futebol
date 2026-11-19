# Receita do servidor de produção (Render). Duas etapas:
#   1) monta o build do React (precisa de Node só aqui)
#   2) imagem final: Python + API + o build pronto (sem Node, sem node_modules)

# ---------- 1) Frontend ----------
FROM node:24-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---------- 2) Backend ----------
FROM python:3.14-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VIRTUALENVS_CREATE=false
WORKDIR /app

RUN pip install --no-cache-dir poetry==2.3.4
COPY pyproject.toml poetry.lock ./
RUN poetry install --only main --no-interaction --no-ansi && rm -rf /root/.cache

COPY app/ app/
COPY --from=frontend /app/frontend/dist frontend/dist

# Não roda como root
RUN useradd --create-home pelada
USER pelada

# O Render informa a porta na variável PORT
EXPOSE 8000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
