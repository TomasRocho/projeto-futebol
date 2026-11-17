"""Exporta o OpenAPI do app para um arquivo, sem subir o servidor.

Uso (da raiz do repo): poetry run python scripts/openapi.py frontend/openapi.json
O frontend gera os tipos TypeScript a partir desse arquivo (npm run gen:api).
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("API_KEY", "so-para-gerar-o-schema")  # o schema não depende da chave

from app.main import app  # noqa: E402

destino = Path(sys.argv[1] if len(sys.argv) > 1 else "openapi.json")
destino.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False) + "\n")
print(f"OpenAPI salvo em {destino}")
