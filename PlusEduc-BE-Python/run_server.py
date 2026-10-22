"""Ponto de entrada do PlusEduc como aplicativo de desktop (PlusEduc.exe) ou via ``python run_server.py``.

Sobe a API e a interface numa porta local e abre uma janela própria (Edge WebView2, sem navegador).
Configuração (``.env``) e log ficam na pasta PlusEduc em ``%APPDATA%`` (criada na primeira execução); um ``.env`` ao
lado do executável (uso portátil) tem prioridade.

    PlusEduc.exe [--port 8080] [--browser] [--headless] [--host 127.0.0.1]

    --browser   abre o navegador padrão em vez da janela própria
    --headless  só o servidor, sem janela nem navegador (ex.: para outra máquina acessar com --host 0.0.0.0)
"""
from __future__ import annotations

import argparse
import ctypes
import logging
import multiprocessing
import os
import secrets
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
BASE_DIR = Path(sys.executable).parent if FROZEN else Path(__file__).resolve().parent
# Instalado em "Arquivos de Programas" a pasta pode ser somente leitura: configuração e log vão para o perfil do usuário.
if FROZEN and not (BASE_DIR / ".env").is_file():
    CONFIG_DIR = Path(os.environ.get("APPDATA", BASE_DIR)) / "PlusEduc"
else:
    CONFIG_DIR = BASE_DIR
LOG_FILE = CONFIG_DIR / "PlusEduc.log"
DEFAULT_ENV = """# Configuração do PlusEduc (criada automaticamente na primeira execução).
MONGODB_URI=mongodb://localhost:27017
MONGODB_DATABASE=escola_db
JWT_SECRET={secret}
# Opcional: chave do Gemini para gerar atividades por IA (vazio usa o modo de demonstração)
GEMINI_API_KEY=
# Atualização automática: consulta a última release do GitHub ao abrir (nunca impede o app de iniciar sem internet)
# UPDATE_CHECK_ENABLED=true
# UPDATE_REPO=PedroBeltraoDev/PlusEduc-MonoRepo
"""


def prepare_environment() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    os.chdir(CONFIG_DIR)  # o .env é lido do diretório atual
    env_file = CONFIG_DIR / ".env"
    if FROZEN and not env_file.exists():
        env_file.write_text(DEFAULT_ENV.format(secret=secrets.token_urlsafe(48)), encoding="utf-8")
    if sys.stdout is None or sys.stderr is None:  # executável sem console: o log vai para um arquivo
        sys.stdout = sys.stderr = open(LOG_FILE, "a", encoding="utf-8", buffering=1)
    # Uma pasta "web" ao lado do executável tem prioridade; senão, a interface embutida no pacote.
    bundled = Path(getattr(sys, "_MEIPASS", BASE_DIR)) / "web"
    for candidate in (BASE_DIR / "web", bundled):
        if candidate.is_dir():
            os.environ.setdefault("FRONTEND_DIST", str(candidate))
            break


def free_port(host: str, preferred: int) -> int:
    """A porta pedida, ou a próxima livre (a 8080 costuma estar com Apache/IIS no Windows)."""
    for port in range(preferred, preferred + 50):
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1" if host == "0.0.0.0" else host, port)) != 0:
                return port
    raise SystemExit(f"Nenhuma porta livre entre {preferred} e {preferred + 49}")


def env_file_defines(name: str) -> bool:
    env_file = CONFIG_DIR / ".env"
    if not env_file.is_file():
        return False
    for line in env_file.read_text(encoding="utf-8").splitlines():
        key, _, value = line.partition("=")
        if key.strip().upper() == name and value.strip():
            return True
    return False


def show_error(message: str) -> None:
    print(message, file=sys.stderr)
    if os.name == "nt":
        ctypes.windll.user32.MessageBoxW(0, f"{message}\n\nDetalhes em {LOG_FILE}", "PlusEduc", 0x10)


def open_window(address: str) -> None:
    """Janela nativa com a interface. Só retorna quando o usuário a fecha."""
    import webview

    webview.create_window("PlusEduc", address, width=1280, height=820, min_size=(980, 640))
    webview.start(private_mode=False, storage_path=str(CONFIG_DIR / "webview"))  # mantém o login entre execuções


def start_update_check(server, headless: bool) -> None:
    """Liga a verificação de atualização (em segundo plano) e informa como encerrar o app para o instalador."""
    from app.main import app

    def request_exit() -> None:
        server.should_exit = True
        try:
            import webview

            for window in list(webview.windows):
                window.destroy()
        except Exception:  # noqa: BLE001 - sem janela (modo --browser) só o servidor precisa parar
            pass
        threading.Timer(20, os._exit, args=(0,)).start()  # garante que nada segure os arquivos que o instalador troca

    manager = app.state.update_manager
    manager.configure_runtime(headless=headless, request_exit=request_exit)
    manager.start()


def main() -> None:
    parser = argparse.ArgumentParser(description="PlusEduc: API e interface web")
    parser.add_argument("--host", default="127.0.0.1", help="use 0.0.0.0 para aceitar outras máquinas da rede")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--browser", action="store_true", help="abrir o navegador padrão em vez da janela própria")
    parser.add_argument("--headless", action="store_true", help="só o servidor, sem janela nem navegador")
    args = parser.parse_args()

    prepare_environment()
    if not os.environ.get("JWT_SECRET") and not env_file_defines("JWT_SECRET"):
        os.environ["JWT_SECRET"] = secrets.token_urlsafe(48)
        logging.getLogger("pluseduc").warning(
            "JWT_SECRET não definido: gerado um segredo temporário (as sessões caem ao reiniciar). Defina-o no .env."
        )

    import uvicorn

    from app.main import app  # importado só agora: ele lê o .env do diretório atual

    port = free_port(args.host, args.port)
    address = f"http://{'127.0.0.1' if args.host == '0.0.0.0' else args.host}:{port}"
    print(f"PlusEduc em {address}" + (f" (porta {args.port} em uso)" if port != args.port else ""))

    server = uvicorn.Server(uvicorn.Config(app, host=args.host, port=port))
    start_update_check(server, headless=args.headless)
    if args.headless:
        server.run()
        return

    thread = threading.Thread(target=server.run, name="pluseduc-server", daemon=True)
    thread.start()
    deadline = time.monotonic() + 60
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.1)
    if not server.started:
        show_error("O servidor do PlusEduc não iniciou (veja se o MongoDB está em execução).")
        return

    try:
        if args.browser:
            webbrowser.open(address)
            thread.join()
        else:
            open_window(address)
    except Exception as exc:  # noqa: BLE001 - sem WebView2 não há janela; avisa em vez de ficar invisível
        show_error(f"Não foi possível abrir a janela ({type(exc).__name__}: {exc}). Use --browser para abrir no navegador.")
    finally:
        server.should_exit = True
        thread.join(timeout=5)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
