"""Gera o build de produção do backend, sem os fontes .py, para rodar com o interpretador Python como antes.

    python scripts/build_backend.py            # build/app só com bytecode (.pyc), como as .class do Java
    python scripts/build_backend.py --nuitka   # build/app.<tag>.pyd: o pacote traduzido para C e compilado em código nativo

Nos dois modos não há executável: o resultado é importado pelo Python (``python scripts/serve.py`` dentro de ``build/``,
ou ``uvicorn app.main:app``). O bytecode e a extensão nativa são específicos da versão do Python usada aqui (ex.: 3.12):
execute o build com o mesmo interpretador que vai rodar o servidor. O ``--nuitka`` exige ``pip install -r
requirements-compile.txt`` e um compilador C (MSVC ou o MinGW64 que o próprio Nuitka baixa na primeira vez; leva alguns
minutos). O padrão (bytecode) continua sendo o caminho mais simples e é o fallback.
"""
from __future__ import annotations

import argparse
import compileall
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
NUITKA_WORK = ROOT / "build-nuitka"  # fora de build/ para sobreviver à limpeza abaixo e ser descartado no fim


def compile_bytecode() -> int:
    shutil.copytree(ROOT / "app", BUILD / "app", ignore=shutil.ignore_patterns("__pycache__"))
    # legacy=True grava x.pyc ao lado de x.py (em vez de __pycache__), o único layout que o Python
    # importa sem o fonte; optimize=1 remove os `assert` (docstrings ficam: o FastAPI as usa no OpenAPI).
    if not compileall.compile_dir(BUILD / "app", force=True, quiet=1, legacy=True, optimize=1):
        raise SystemExit("Falha ao compilar o backend")
    for source in (BUILD / "app").rglob("*.py"):
        source.unlink()
    return sum(1 for _ in (BUILD / "app").rglob("*.pyc"))


def compile_native(jobs: int) -> int:
    """Traduz o pacote ``app`` para C e o compila numa extensão nativa (``app.<tag>.pyd``) com o Nuitka."""
    if importlib.util.find_spec("nuitka") is None:
        raise SystemExit("Nuitka não encontrado: pip install -r requirements-compile.txt")
    shutil.rmtree(NUITKA_WORK, ignore_errors=True)
    # O Python da Microsoft Store guarda o cache do Nuitka num caminho enorme e a extração do MinGW falha (limite de 260
    # caracteres): usa um cache curto, a menos que NUITKA_CACHE_DIR já esteja definido.
    env = dict(os.environ)
    if "WindowsApps" in sys.base_prefix and "NUITKA_CACHE_DIR" not in env:
        env["NUITKA_CACHE_DIR"] = str(Path(os.environ.get("SystemDrive", "C:") + "\\") / "nuitka-cache")
    command = [
        sys.executable, "-m", "nuitka", "--mode=module", "app", "--include-package=app",
        f"--output-dir={NUITKA_WORK}", "--remove-output", "--assume-yes-for-downloads", f"--jobs={jobs}", "--lto=no",
    ]
    subprocess.run(command, check=True, cwd=ROOT, env=env)
    extensions = list(NUITKA_WORK.glob("app.*.pyd")) + list(NUITKA_WORK.glob("app.*.so"))
    if len(extensions) != 1:
        raise SystemExit(f"O Nuitka deveria gerar uma única extensão app.*, gerou: {extensions}")
    shutil.copy2(extensions[0], BUILD / extensions[0].name)
    shutil.rmtree(NUITKA_WORK, ignore_errors=True)
    # O kernel OpenCL é lido do disco (compilado pelo driver ao executar): fica no mesmo caminho relativo ao pacote.
    (BUILD / "app" / "compute").mkdir(parents=True)
    shutil.copy2(ROOT / "app" / "compute" / "grade_stats.cl", BUILD / "app" / "compute" / "grade_stats.cl")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nuitka", action="store_true", help="compila o pacote app para código nativo em vez de bytecode")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4, help="tarefas de compilação do Nuitka em paralelo")
    args = parser.parse_args()

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir()
    shutil.copy2(ROOT / "requirements.txt", BUILD / "requirements.txt")
    (BUILD / "scripts").mkdir()
    shutil.copy2(ROOT / "scripts" / "serve.py", BUILD / "scripts" / "serve.py")
    compiled = compile_native(args.jobs) if args.nuitka else compile_bytecode()

    # Teste de fumaça: importa a aplicação a partir do build, sem nenhum .py disponível.
    smoke = subprocess.run(
        [sys.executable, "-c", "import app.main; print('import ok')"],
        cwd=BUILD, capture_output=True, text=True, env={**os.environ, "JWT_SECRET": "build-smoke-test-only"},
    )
    if smoke.returncode != 0:
        raise SystemExit(f"O build não importa:\n{smoke.stderr}")
    kind = "extensão nativa (Nuitka)" if args.nuitka else "módulos em bytecode"
    print(f"Build em {BUILD} ({compiled} {kind}, Python {sys.version.split()[0]}).")


if __name__ == "__main__":
    main()
