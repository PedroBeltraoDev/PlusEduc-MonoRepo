"""Gera o build de produção do backend: ``build/app`` só com bytecode (.pyc), sem os fontes .py.

    python scripts/build_backend.py

O bytecode é específico da versão do Python usada aqui (ex.: 3.12): execute o build com o mesmo
interpretador que vai rodar o servidor. Para subir o resultado: ``python scripts/serve.py`` dentro de ``build/``.
"""
from __future__ import annotations

import compileall
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"


def main() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    shutil.copytree(ROOT / "app", BUILD / "app", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "requirements.txt", BUILD / "requirements.txt")
    (BUILD / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "serve.py", BUILD / "scripts" / "serve.py")

    # legacy=True grava x.pyc ao lado de x.py (em vez de __pycache__), o único layout que o Python
    # importa sem o fonte; optimize=1 remove os `assert` (docstrings ficam: o FastAPI as usa no OpenAPI).
    if not compileall.compile_dir(BUILD / "app", force=True, quiet=1, legacy=True, optimize=1):
        raise SystemExit("Falha ao compilar o backend")
    for source in (BUILD / "app").rglob("*.py"):
        source.unlink()

    # Teste de fumaça: importa a aplicação a partir do build, sem nenhum .py disponível.
    smoke = subprocess.run(
        [sys.executable, "-c", "import app.main; print('import ok')"],
        cwd=BUILD, capture_output=True, text=True, env={**os.environ, "JWT_SECRET": "build-smoke-test-only"},
    )
    if smoke.returncode != 0:
        raise SystemExit(f"O build não importa:\n{smoke.stderr}")
    compiled = sum(1 for _ in (BUILD / "app").rglob("*.pyc"))
    print(f"Build em {BUILD} ({compiled} módulos compilados, Python {sys.version.split()[0]}).")


if __name__ == "__main__":
    main()
