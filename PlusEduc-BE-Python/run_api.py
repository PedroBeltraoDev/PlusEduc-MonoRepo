"""Ponto de entrada do servidor da API como programa único (``PlusEduc-API.exe``, gerado por
``python scripts/build_backend.py --standalone``) ou via ``python run_api.py``.

    PlusEduc-API.exe [--host 0.0.0.0] [--port 8080] [--workers N] [--check]

Equivale a ``scripts/serve.py``, mas dentro do executável compilado: o ``.env`` é lido da pasta do programa (veja
``.env.example``) e o kernel OpenCL ``app/compute/grade_stats.cl`` fica ao lado, com fallback em CPU se não houver GPU.
Cada worker é um processo (``multiprocessing`` em modo spawn), com o próprio cliente MongoDB. ``--check`` só importa a
aplicação e sai (teste de fumaça do build).
"""
from __future__ import annotations

import argparse
import multiprocessing
import os
import sys
from pathlib import Path

COMPILED = bool(getattr(sys, "frozen", False)) or "__compiled__" in globals()
BASE_DIR = Path(sys.executable).resolve().parent if COMPILED else Path(__file__).resolve().parent


def default_workers() -> int:
    configured = os.getenv("WEB_CONCURRENCY")
    return int(configured) if configured else max(1, min(os.cpu_count() or 1, 4))


def main() -> None:
    parser = argparse.ArgumentParser(description="PlusEduc: servidor da API")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--workers", type=int, default=default_workers())
    parser.add_argument("--check", action="store_true", help="importa a aplicação e sai")
    args = parser.parse_args()

    os.chdir(BASE_DIR)  # o .env é lido do diretório atual (a pasta do programa)
    if not os.environ.get("JWT_SECRET") and not (BASE_DIR / ".env").is_file():
        raise SystemExit(f"Crie {BASE_DIR / '.env'} a partir de .env.example (defina JWT_SECRET e a conexão com o MongoDB).")

    if args.check:
        import app.main  # noqa: F401

        print("import ok")
        return

    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, workers=args.workers)


if __name__ == "__main__":
    multiprocessing.freeze_support()  # necessário para os workers (spawn) no executável compilado
    main()
