"""Gera o aplicativo de desktop do PlusEduc (janela própria) com o PyInstaller e, opcionalmente, o instalador.

    python scripts/build_exe.py --installer  # dist/installer/PlusEduc-Setup-<versão>.exe (precisa do Inno Setup 6)
    python scripts/build_exe.py              # pasta dist/PlusEduc/ com PlusEduc.exe (inicia mais rápido)
    python scripts/build_exe.py --onefile    # um único dist/PlusEduc.exe (extrai para uma pasta temporária ao abrir)
    python scripts/build_exe.py --skip-ui    # não recompila a interface (usa PlusEduc-UI/dist existente)
    python scripts/build_exe.py --console    # mantém o console (útil para depurar; o padrão é sem console)

Requer ``pip install -r requirements-build.txt`` e Node.js (para compilar a interface). O aplicativo só depende
do MongoDB. Gera para o sistema e o Python em que for executado.
"""
from __future__ import annotations

import argparse
import os
import re
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


def find_iscc() -> Path:
    local_programs = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs"
    candidates = [shutil.which("ISCC")] + [
        base / "Inno Setup 6" / "ISCC.exe"
        for base in (local_programs, Path(os.environ.get("ProgramFiles(x86)", "")), Path(os.environ.get("ProgramFiles", "")))
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    raise SystemExit("Inno Setup 6 não encontrado. Instale com: winget install JRSoftware.InnoSetup")


def app_version() -> str:
    match = re.search(r'app_version: str = "([^"]+)"', (ROOT / "app" / "core" / "config.py").read_text(encoding="utf-8"))
    return match.group(1) if match else "0.0.0"


def build_installer() -> Path:
    version = app_version()
    subprocess.run([str(find_iscc()), f"/DAppVersion={version}", str(ROOT / "installer" / "PlusEduc.iss")], check=True)
    return DIST / "installer" / f"PlusEduc-Setup-{version}.exe"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--onefile", action="store_true")
    parser.add_argument("--skip-ui", action="store_true")
    parser.add_argument("--console", action="store_true")
    parser.add_argument("--installer", action="store_true", help="também gera o instalador (Setup.exe)")
    args = parser.parse_args()
    if args.installer and args.onefile:
        raise SystemExit("--installer usa a pasta dist/PlusEduc: rode sem --onefile")

    ui_dist = UI_ROOT / "dist" if args.skip_ui else build_ui()
    if not (ui_dist / "index.html").is_file():
        raise SystemExit(f"Interface compilada não encontrada em {ui_dist}")

    for folder in (WORK, DIST):
        shutil.rmtree(folder, ignore_errors=True)
    command = [
        sys.executable, "-m", "PyInstaller", str(ROOT / "run_server.py"),
        "--name", "PlusEduc", "--noconfirm", "--clean", "--onefile" if args.onefile else "--onedir",
        "--console" if args.console else "--noconsole",
        "--distpath", str(DIST), "--workpath", str(WORK), "--specpath", str(WORK),
        "--paths", str(ROOT), "--icon", str(ROOT / "assets" / "pluseduc.ico"),
        "--add-data", f"{ROOT / 'app' / 'compute' / 'grade_stats.cl'}{os.pathsep}app/compute",
        "--add-data", f"{ui_dist}{os.pathsep}web",  # interface embutida; uma pasta web ao lado do .exe a substitui
        "--collect-data", "reportlab",
        "--collect-all", "webview",  # janela nativa (pywebview + Edge WebView2)
    ]
    for module in HIDDEN_IMPORTS:
        command += ["--hidden-import", module]
    subprocess.run(command, check=True)

    target = DIST if args.onefile else DIST / "PlusEduc"
    shutil.copy2(ROOT / ".env.example", target / ".env.example")
    size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file()) / 2**20
    print(f"\nAplicativo: {target / 'PlusEduc.exe'}  ({size:.0f} MB no total)")
    if args.installer:
        print(f"Instalador: {build_installer()}")


if __name__ == "__main__":
    main()
