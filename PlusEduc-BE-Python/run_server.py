"""Ponto de entrada do executável (PlusEduc.exe) e de ``python run_server.py``.

Lê o ``.env`` da pasta do executável, serve a API e, se existir a pasta ``web`` ao lado, a interface.

    PlusEduc.exe [--host 127.0.0.1] [--port 8080] [--no-browser]
"""
from __future__ import annotations

import argparse
import logging
import multiprocessing
import os
import secrets
import sys
import threading
import webbrowser
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
BASE_DIR = Path(sys.executable).parent if FROZEN else Path(__file__).resolve().parent


def prepare_environment() -> None:
    # O .env e a pasta da interface ficam ao lado do executável, não no diretório de onde ele foi aberto.
    os.chdir(BASE_DIR)
    if (BASE_DIR / "web").is_dir():
        os.environ.setdefault("FRONTEND_DIST", str(BASE_DIR / "web"))


def main() -> None:
    parser = argparse.ArgumentParser(description="PlusEduc: API e interface web")
    parser.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 para aceitar outras máquinas da rede")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--no-browser", action="store_true", help="não abrir o navegador ao iniciar")
    args = parser.parse_args()

    prepare_environment()
    if not os.environ.get("JWT_SECRET") and not _env_file_defines("JWT_SECRET"):
        os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)
        logging.getLogger("pluseduc").warning(
            "JWT_SECRET não definido: gerado um segredo temporário (as sessões caem ao reiniciar). Defina-o no .env."
        )

    import uvicorn

    from app.main import app  # importado só agora: ele lê o .env do diretório atual

    if not args.no_browser and os.environ.get("FRONTEND_DIST"):
        threading.Timer(2.0, webbrowser.open, args=(f"http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{args.port}",)).start()
    uvicorn.run(app, host=args.host, port=args.port)


def _env_file_defines(name: str) -> bool:
    env_file = BASE_DIR / ".env"
    if not env_file.is_file():
        return False
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip().upper() == name and value.strip():
            return True
    return False


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
