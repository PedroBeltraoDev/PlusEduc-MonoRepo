"""Gera o aplicativo de desktop do PlusEduc (janela própria) e, opcionalmente, o instalador.

    python scripts/build_exe.py --installer  # dist/installer/PlusEduc-Setup-<versão>.exe (precisa do Inno Setup 6)
    python scripts/build_exe.py              # pasta dist/PlusEduc/ com PlusEduc.exe (inicia mais rápido)
    python scripts/build_exe.py --onefile    # um único dist/PlusEduc.exe (extrai para uma pasta temporária ao abrir)
    python scripts/build_exe.py --skip-ui    # não recompila a interface (usa PlusEduc-UI/dist existente)
    python scripts/build_exe.py --console    # mantém o console (útil para depurar; o padrão é sem console)
    python scripts/build_exe.py --nuitka     # backend compilado para código nativo (C → .exe) em vez de bytecode

O padrão é o PyInstaller (bytecode do backend dentro do executável; build de ~1 min) e continua sendo o caminho
recomendado e o fallback. ``--nuitka`` traduz o backend (``app/``, ``run_server.py`` e as bibliotecas Python) para C e
o compila (vários minutos na primeira vez; baixa um MinGW64 para o cache do usuário se não houver MSVC instalado).
O frontend (build do Vite) é o mesmo nos dois modos e o kernel OpenCL continua sendo compilado pelo driver ao executar.
Os dois modos geram a mesma estrutura em ``dist/PlusEduc/``, que o instalador (Inno Setup) empacota sem mudanças.

Requer ``pip install -r requirements-build.txt`` e Node.js (para compilar a interface). O aplicativo só depende
do MongoDB. Gera para o sistema e o Python em que for executado.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI_ROOT = ROOT.parent / "PlusEduc-UI"
WORK = ROOT / "build" / "pyinstaller"
NUITKA_WORK = ROOT / "build" / "nuitka"
DIST = ROOT / "dist"
HIDDEN_IMPORTS = (
    "uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets.auto", "uvicorn.lifespan.on",
)
# Nuitka: pacotes carregados por nome em tempo de execução ou que trazem DLLs/dados que ele não deduz sozinho.
NUITKA_PACKAGES = ("uvicorn",)
NUITKA_PACKAGE_DATA = ("reportlab", "pyopencl")


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
    match = re.search(r'__version__ = "([^"]+)"', (ROOT / "app" / "version.py").read_text(encoding="utf-8"))
    return match.group(1) if match else "0.0.0"


def build_installer() -> Path:
    version = app_version()
    subprocess.run([str(find_iscc()), f"/DAppVersion={version}", str(ROOT / "installer" / "PlusEduc.iss")], check=True)
    return DIST / "installer" / f"PlusEduc-Setup-{version}.exe"


def build_pyinstaller(args: argparse.Namespace, ui_dist: Path) -> Path:
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
    return DIST if args.onefile else DIST / "PlusEduc"


def build_nuitka(args: argparse.Namespace, ui_dist: Path) -> Path:
    """Compila o backend com o Nuitka e deixa o resultado onde o PyInstaller deixaria (``dist/PlusEduc``)."""
    if importlib.util.find_spec("nuitka") is None:
        raise SystemExit("Nuitka não encontrado: pip install -r requirements-build.txt")
    for folder in (NUITKA_WORK, DIST):
        shutil.rmtree(folder, ignore_errors=True)
    # O Python da Microsoft Store guarda o cache do Nuitka num caminho enorme e a extração do MinGW falha (limite de 260
    # caracteres): usa um cache curto, a menos que NUITKA_CACHE_DIR já esteja definido.
    env = dict(os.environ)
    if "WindowsApps" in sys.base_prefix and "NUITKA_CACHE_DIR" not in env:
        env["NUITKA_CACHE_DIR"] = str(Path(os.environ.get("SystemDrive", "C:") + "\\") / "nuitka-cache")
    numeric = re.match(r"\d+(?:\.\d+){0,3}", app_version())
    file_version = ".".join(((numeric.group(0) if numeric else "0") + ".0.0.0").split(".")[:4])
    command = [
        sys.executable, "-m", "nuitka", str(ROOT / "run_server.py"),
        "--onefile" if args.onefile else "--standalone", "--output-filename=PlusEduc.exe",
        f"--output-dir={NUITKA_WORK}", "--remove-output", "--assume-yes-for-downloads",
        f"--jobs={args.jobs}", "--lto=no",  # sem LTO a compilação é bem mais rápida e o app é limitado por E/S de banco
        f"--windows-console-mode={'force' if args.console else 'disable'}",
        f"--windows-icon-from-ico={ROOT / 'assets' / 'pluseduc.ico'}",
        "--company-name=PlusEduc", "--product-name=PlusEduc", "--file-description=PlusEduc",
        f"--file-version={file_version}", f"--product-version={file_version}",
        "--include-package=app",  # rotas, serviços e repositórios
        *(f"--include-package={name}" for name in NUITKA_PACKAGES),
        *(f"--include-package-data={name}" for name in NUITKA_PACKAGE_DATA),
        *(f"--include-module={name}" for name in HIDDEN_IMPORTS),
        f"--include-data-files={ROOT / 'app' / 'compute' / 'grade_stats.cl'}=app/compute/grade_stats.cl",
        f"--include-data-dir={ui_dist}=web",
        "--nofollow-import-to=pytest,tkinter,IPython,setuptools,PyInstaller,Nuitka",
    ]
    subprocess.run(command, check=True, cwd=ROOT, env=env)

    DIST.mkdir(parents=True)
    if args.onefile:
        shutil.move(str(NUITKA_WORK / "PlusEduc.exe"), DIST / "PlusEduc.exe")
        return DIST
    produced = NUITKA_WORK / "run_server.dist"
    if not (produced / "PlusEduc.exe").is_file():
        raise SystemExit(f"O Nuitka não gerou {produced / 'PlusEduc.exe'}")
    shutil.move(str(produced), DIST / "PlusEduc")
    return DIST / "PlusEduc"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--onefile", action="store_true")
    parser.add_argument("--skip-ui", action="store_true")
    parser.add_argument("--console", action="store_true")
    parser.add_argument("--installer", action="store_true", help="também gera o instalador (Setup.exe)")
    parser.add_argument("--nuitka", action="store_true", help="compila o backend para código nativo com o Nuitka")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 4, help="tarefas de compilação do Nuitka em paralelo")
    args = parser.parse_args()
    if args.installer and args.onefile:
        raise SystemExit("--installer usa a pasta dist/PlusEduc: rode sem --onefile")

    ui_dist = UI_ROOT / "dist" if args.skip_ui else build_ui()
    if not (ui_dist / "index.html").is_file():
        raise SystemExit(f"Interface compilada não encontrada em {ui_dist}")

    target = (build_nuitka if args.nuitka else build_pyinstaller)(args, ui_dist)
    shutil.copy2(ROOT / ".env.example", target / ".env.example")
    size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file()) / 2**20
    print(f"\nAplicativo ({'Nuitka' if args.nuitka else 'PyInstaller'}): {target / 'PlusEduc.exe'}  ({size:.0f} MB no total)")
    if args.installer:
        print(f"Instalador: {build_installer()}")


if __name__ == "__main__":
    main()
