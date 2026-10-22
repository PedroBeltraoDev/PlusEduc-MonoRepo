"""Gera o executável do PlusEduc (API + interface web) com o PyInstaller.

    python scripts/build_exe.py            # pasta dist/PlusEduc/ com PlusEduc.exe (inicia mais rápido)
    python scripts/build_exe.py --onefile  # um único dist/PlusEduc.exe (extrai para uma pasta temporária ao abrir)
    python scripts/build_exe.py --skip-ui  # não recompila a interface (usa PlusEduc-UI/dist existente)

Requer ``pip install pyinstaller`` e Node.js (para compilar a interface). O executável só depende do
MongoDB: coloque o ``.env`` ao lado do .exe (veja ``.env.example``, copiado junto). Gera para o sistema e o
Python em que for executado.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT.parent / "PlusEduc-UI"
WORK = ROOT / "build" / "pyinstaller"
DIST = ROOT / "dist"
HIDDEN_IMPORTS = (
    "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on",
)


def build_ui() -> Path:
    if shutil.which("npm") is None:
        raise SystemExit("Node.js/npm não encontrado: instale-o ou use --skip-ui com uma interface já compilada")
    if not (UI_ROOT / "node_modules").is_dir():
        subprocess.run("npm ci", cwd=UI_ROOT, shell=True, check=True)
    subprocess.run("npm run build", cwd=UI_ROOT, shell=True, check=True)
    return UI_ROOT / "dist"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--onefile", action="store_true")
    parser.add_argument("--skip-ui", action="store_true")
    args = parser.parse_args()

    ui_dist = UI_ROOT / "dist" if args.skip_ui else build_ui()
    if not (ui_dist / "index.html").is_file():
        raise SystemExit(f"Interface compilada não encontrada em {ui_dist}")

    for folder in (WORK, DIST):
        shutil.rmtree(folder, ignore_errors=True)
    command = [
        sys.executable, "-m", "PyInstaller", str(ROOT / "run_server.py"),
        "--name", "PlusEduc", "--noconfirm", "--clean", "--onefile" if args.onefile else "--onedir",
        "--distpath", str(DIST), "--workpath", str(WORK), "--specpath", str(WORK),
        "--paths", str(ROOT),
        "--add-data", f"{ROOT / 'app' / 'compute' / 'grade_stats.cl'}{os.pathsep}app/compute",
        "--collect-data", "reportlab",
    ]
    for module in HIDDEN_IMPORTS:
        command += ["--hidden-import", module]
    subprocess.run(command, check=True)

    target = DIST if args.onefile else DIST / "PlusEduc"
    shutil.copytree(ui_dist, target / "web")
    shutil.copy2(ROOT / ".env.example", target / ".env.example")
    executable = target / "PlusEduc.exe"
    size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file()) / 2**20
    print(f"\nExecutável: {executable}  ({size:.0f} MB no total)")


if __name__ == "__main__":
    main()
