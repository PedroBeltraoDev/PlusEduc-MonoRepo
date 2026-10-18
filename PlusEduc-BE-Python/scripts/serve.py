"""Sobe a API em modo produção com vários processos (paralelismo real entre requisições).

    python scripts/serve.py [--host 0.0.0.0] [--port 8080] [--workers N]

Cada processo cria o próprio cliente MongoDB e as próprias threads de rota, então a CPU (PDF, bcrypt,
validação Pydantic) escala com o número de processos. Padrão: um por núcleo, no máximo 4 (``WEB_CONCURRENCY``
também é respeitada). Em desenvolvimento continue usando ``uvicorn app.main:app --reload``.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import uvicorn

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def default_workers() -> int:
    configured = os.getenv("WEB_CONCURRENCY")
    return int(configured) if configured else max(1, min(os.cpu_count() or 1, 4))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--workers", type=int, default=default_workers())
    args = parser.parse_args()
    uvicorn.run("app.main:app", host=args.host, port=args.port, workers=args.workers)
