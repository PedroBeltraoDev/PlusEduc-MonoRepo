"""Gera o build de produção do backend, sem os fontes .py, para rodar com o interpretador Python como antes.

    python scripts/build_backend.py            # build/app só com bytecode (.pyc), como as .class do Java
    python scripts/build_backend.py --nuitka   # build/app.<tag>.pyd: o pacote traduzido para C e compilado em código nativo
    python scripts/build_backend.py --standalone  # build/PlusEduc-API/PlusEduc-API.exe: o servidor inteiro, com Python embutido

Nos dois primeiros modos não há executável: o resultado é importado pelo Python (``python scripts/serve.py`` dentro de ``build/``,
ou ``uvicorn app.main:app``). O bytecode e a extensão nativa são específicos da versão do Python usada aqui (ex.: 3.12):
execute o build com o mesmo interpretador que vai rodar o servidor. O ``--nuitka`` exige ``pip install -r
requirements-compile.txt`` e um compilador C (MSVC ou o MinGW64 que o próprio Nuitka baixa na primeira vez; leva alguns
minutos). O padrão (bytecode) continua sendo o caminho mais simples e é o fallback.

``--standalone`` vai além: compila também as bibliotecas Python (FastAPI, Starlette, Uvicorn, Pydantic, PyMongo...) e
embute o runtime do Python, gerando uma pasta com ``PlusEduc-API.exe`` que não precisa do interpretador nem dos fontes.
Os pacotes que já vêm prontos do pip com código nativo (numpy, pydantic-core, bcrypt, pyopencl...) são copiados como estão.
"""
from __future__ import annotations

import argparse
import compileall
import importlib.util
import os
import re
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


def nuitka_environment() -> dict[str, str]:
    """Ambiente do Nuitka; falha cedo se ele não estiver instalado."""
    if importlib.util.find_spec("nuitka") is None:
        raise SystemExit("Nuitka não encontrado: pip install -r requirements-compile.txt")
    shutil.rmtree(NUITKA_WORK, ignore_errors=True)
    # O Python da Microsoft Store guarda o cache do Nuitka num caminho enorme e a extração do MinGW falha (limite de 260
    # caracteres): usa um cache curto, a menos que NUITKA_CACHE_DIR já esteja definido.
    env = dict(os.environ)
    if "WindowsApps" in sys.base_prefix and "NUITKA_CACHE_DIR" not in env:
        env["NUITKA_CACHE_DIR"] = str(Path(os.environ.get("SystemDrive", "C:") + "\\") / "nuitka-cache")
    return env


def compile_standalone(jobs: int) -> Path:
    """Compila o servidor inteiro (``run_api.py``, ``app`` e as bibliotecas) com o Nuitka --standalone: pasta com o
    ``PlusEduc-API.exe`` e o runtime do Python embutido, sem precisar do interpretador nem dos fontes."""
    env = nuitka_environment()
    version = re.search(r'version = "(\d+(?:\.\d+){0,3})"', (ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    file_version = ".".join(((version.group(1) if version else "0") + ".0.0.0").split(".")[:4])
    command = [
        sys.executable, "-m", "nuitka", str(ROOT / "run_api.py"), "--standalone", "--output-filename=PlusEduc-API.exe",
        f"--output-dir={NUITKA_WORK}", "--remove-output", "--assume-yes-for-downloads", f"--jobs={jobs}", "--lto=no",
        "--windows-console-mode=force",  # servidor de console: logs e Ctrl+C
        "--company-name=PlusEduc", "--product-name=PlusEduc API", "--file-description=PlusEduc API",
        f"--file-version={file_version}", f"--product-version={file_version}",
        "--include-package=app", "--include-package=uvicorn",  # uvicorn escolhe loop/protocolo por nome em tempo de execução
        "--include-package-data=reportlab", "--include-package-data=pyopencl",
        f"--include-data-files={ROOT / 'app' / 'compute' / 'grade_stats.cl'}=app/compute/grade_stats.cl",
        "--nofollow-import-to=pytest,tkinter,IPython,setuptools,PyInstaller,nuitka,webview",
    ]
    subprocess.run(command, check=True, cwd=ROOT, env=env)
    produced = NUITKA_WORK / "run_api.dist"
    if not (produced / "PlusEduc-API.exe").is_file():
        raise SystemExit(f"O Nuitka não gerou {produced / 'PlusEduc-API.exe'}")
    target = BUILD / "PlusEduc-API"
    shutil.move(str(produced), target)
    shutil.copy2(ROOT / ".env.example", target / ".env.example")
    shutil.rmtree(NUITKA_WORK, ignore_errors=True)
    return target


def compile_native(jobs: int) -> int:
    """Traduz o pacote ``app`` para C e o compila numa extensão nativa (``app.<tag>.pyd``) com o Nuitka."""
    env = nuitka_environment()
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
    parser.add_argument("--standalone", action="store_true", help="compila o servidor inteiro num PlusEduc-API.exe (Nuitka)")
    args = parser.parse_args()
    if args.standalone and args.nuitka:
        raise SystemExit("Use --nuitka (só o pacote app) ou --standalone (servidor inteiro), não os dois")

    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir()
    if args.standalone:
        target = compile_standalone(args.jobs)
        smoke = subprocess.run(
            [str(target / "PlusEduc-API.exe"), "--check"], capture_output=True, text=True,
            env={"SystemRoot": os.environ.get("SystemRoot", ""), "PATH": "", "JWT_SECRET": "build-smoke-test-only"},  # sem o Python no PATH
        )
        if smoke.returncode != 0 or "import ok" not in smoke.stdout:
            raise SystemExit(f"O executável não inicia:\n{smoke.stdout}\n{smoke.stderr}")
        size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file()) / 2**20
        print(f"Servidor em {target / 'PlusEduc-API.exe'} ({size:.0f} MB, Python embutido). Copie .env.example para .env ao lado dele.")
        return
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
