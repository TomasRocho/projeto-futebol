"""Em produção, o mesmo servidor entrega a API (/api) e o build do React (frontend/dist).

- /assets/...      arquivos do build (JS/CSS com hash no nome: pode cachear "para sempre")
- /favicon.svg ... outros arquivos que existem no dist
- qualquer outra   devolve o index.html; quem decide a página é o React Router
- /api/...         nunca cai aqui: rota de API inexistente continua dando 404 em JSON
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DIST_PADRAO = Path(__file__).resolve().parent.parent / "frontend" / "dist"


class _AssetsComCache(StaticFiles):
    async def get_response(self, path, scope):
        resposta = await super().get_response(path, scope)
        if resposta.status_code == 200:
            resposta.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resposta


def montar_frontend(app: FastAPI, dist: Path = DIST_PADRAO) -> bool:
    """Liga o frontend se o build existir. Devolve False (e não faz nada) se não existir,
    que é o caso em dev, quando o React roda no Vite."""
    indice = dist / "index.html"
    if not indice.is_file():
        return False
    raiz = dist.resolve()

    if (dist / "assets").is_dir():
        app.mount("/assets", _AssetsComCache(directory=dist / "assets"), name="assets")

    @app.get("/{caminho:path}", include_in_schema=False)
    def spa(caminho: str):
        if caminho == "api" or caminho.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not Found")
        arquivo = (raiz / caminho).resolve()
        # só serve arquivo que está DENTRO do dist (nada de ../../.env)
        if caminho and arquivo.is_file() and arquivo.is_relative_to(raiz):
            return FileResponse(arquivo)
        return FileResponse(indice, headers={"Cache-Control": "no-cache"})

    return True
