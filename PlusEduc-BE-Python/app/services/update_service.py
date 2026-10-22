"""Atualização do aplicativo de desktop: descobre a última release no GitHub, baixa o instalador e o executa.

Princípios:
- a verificação roda em segundo plano, com timeout curto, e qualquer falha (sem internet, sem release, limite de
  requisições do GitHub) só muda o estado exposto à interface: nunca derruba nem atrasa a inicialização;
- o instalador só é baixado de ``https://github.com/<UPDATE_REPO>/releases/download/...`` (e dos hosts de armazenamento
  ``*.githubusercontent.com`` para onde o GitHub redireciona) e só é executado depois de conferir tamanho e SHA-256
  informados pela release e o cabeçalho de executável do Windows.
"""
from __future__ import annotations

import hashlib
import logging
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import quote, urljoin, urlsplit

import httpx

from app.core.config import Settings
from app.version import __version__

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
INSTALLER_ASSET_NAME = "PlusEduc-Setup.exe"  # nome estável do asset no release (o site de download aponta para ele)
_VERSIONED_ASSET = re.compile(r"^PlusEduc-Setup-.+\.exe$")
_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
MAX_INSTALLER_BYTES = 500 * 1024 * 1024
MAX_REDIRECTS = 5
# /SILENT mostra só a barra de progresso; o app já se encerra, /CLOSEAPPLICATIONS cobre qualquer processo remanescente.
INSTALLER_ARGS = ("/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS")
RATE_LIMIT_MIN_BACKOFF_SECONDS = 15 * 60
MANUAL_CHECK_MIN_INTERVAL_SECONDS = 30


# --------------------------------------------------------------------------------------------- versões


def _parse_version_key(text: str) -> tuple | None:
    match = re.fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?", text.strip())
    if not match:
        return None
    major, minor, patch, prerelease = match.groups()
    if prerelease is None:
        pre_key: tuple = (1,)  # uma versão final é maior que qualquer pré-lançamento da mesma numeração
    else:
        identifiers = tuple((0, int(part), "") if part.isdigit() else (1, 0, part) for part in prerelease.split("."))
        pre_key = (0, *identifiers)
    return (int(major), int(minor or 0), int(patch or 0), pre_key)


def parse_version(text: str) -> tuple | None:
    """Chave de ordenação de uma versão semântica (``0.2.0``, ``v1.4``, ``1.0.0-rc.1``) ou ``None`` se inválida."""
    return _parse_version_key(text) if isinstance(text, str) else None


def is_newer(candidate: str, current: str) -> bool:
    candidate_key, current_key = parse_version(candidate), parse_version(current)
    return candidate_key is not None and current_key is not None and candidate_key > current_key


def normalize_version(text: str) -> str:
    return text.strip().removeprefix("v").removeprefix("V")


# --------------------------------------------------------------------------------------------- release do GitHub


class UpdateError(Exception):
    """Falha esperada da atualização; ``status`` indica o estado mostrado à interface."""

    def __init__(self, status: str, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.retry_after_seconds = retry_after_seconds


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag: str
    page_url: str
    notes: str
    asset_name: str | None = None
    asset_url: str | None = None
    asset_size: int | None = None
    asset_sha256: str | None = None


def valid_repo(repo: str) -> bool:
    return bool(_REPO_PATTERN.fullmatch(repo)) and ".." not in repo


def resolve_api_base(value: str) -> tuple[str, str | None]:
    """API de releases a consultar e, só para testes locais, a origem de onde o instalador pode ser baixado.

    O padrão é a API do GitHub. ``UPDATE_API_BASE`` aceita apenas um servidor de teste em ``http://127.0.0.1``
    (ou ``localhost``): nunca um endereço externo diferente do GitHub.
    """
    value = value.strip().rstrip("/") or GITHUB_API
    if value == GITHUB_API:
        return GITHUB_API, None
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        port = None
    if parts.scheme == "http" and parts.hostname in ("127.0.0.1", "localhost") and port and not parts.path.strip("/"):
        return value, value
    raise UpdateError("error", "UPDATE_API_BASE inválido: só https://api.github.com ou um servidor de teste em http://127.0.0.1")


def is_trusted_asset_url(url: str, repo: str, local_origin: str | None = None) -> bool:
    """URL de download do asset: exatamente ``https://github.com/<repo>/releases/download/...``."""
    if local_origin:
        return url.startswith(local_origin + "/") and ".." not in url
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    return (
        parts.scheme == "https"
        and parts.hostname == "github.com"
        and port in (None, 443)
        and not parts.username
        and not parts.password
        and parts.path.lower().startswith(f"/{repo.lower()}/releases/download/")
        and ".." not in parts.path
    )


def _is_trusted_redirect(url: str, local_origin: str | None = None) -> bool:
    """Destinos para onde o GitHub redireciona o download (armazenamento de releases)."""
    if local_origin:
        return url.startswith(local_origin + "/")
    try:
        parts = urlsplit(url)
        host = parts.hostname or ""
        port = parts.port
    except ValueError:
        return False
    on_github = host == "github.com" or host.endswith(".githubusercontent.com")
    return parts.scheme == "https" and on_github and port in (None, 443) and not parts.username


def _select_asset(assets: object, repo: str, local_origin: str | None) -> dict | None:
    if not isinstance(assets, list):
        return None
    candidates = [a for a in assets if isinstance(a, dict) and isinstance(a.get("name"), str)]
    candidates.sort(key=lambda a: (a["name"] != INSTALLER_ASSET_NAME, a["name"]))
    for asset in candidates:
        if asset["name"] != INSTALLER_ASSET_NAME and not _VERSIONED_ASSET.fullmatch(asset["name"]):
            continue
        if asset.get("state", "uploaded") != "uploaded":
            continue
        if not is_trusted_asset_url(str(asset.get("browser_download_url", "")), repo, local_origin):
            logger.warning("Asset %s ignorado: URL de download fora de github.com/%s", asset["name"], repo)
            continue
        return asset
    return None


def parse_release(payload: object, repo: str, local_origin: str | None = None) -> ReleaseInfo:
    """Converte a resposta de ``releases/latest`` em ``ReleaseInfo``; ``UpdateError`` se vier algo inesperado."""
    if not isinstance(payload, dict):
        raise UpdateError("error", "Resposta inesperada do GitHub")
    if payload.get("draft") or payload.get("prerelease"):
        raise UpdateError("no_release", "A última release é um rascunho ou pré-lançamento")
    tag = payload.get("tag_name")
    version = normalize_version(tag) if isinstance(tag, str) else ""
    if parse_version(version) is None:
        raise UpdateError("error", "Tag da release sem versão válida")
    notes = payload.get("body")
    release = ReleaseInfo(
        version=version,
        tag=tag,
        page_url=f"https://github.com/{repo}/releases/tag/{quote(tag, safe='')}",
        notes=notes.strip()[:2000] if isinstance(notes, str) else "",
    )
    asset = _select_asset(payload.get("assets"), repo, local_origin)
    if asset is None:
        return release
    size = asset.get("size")
    digest = str(asset.get("digest") or "")
    sha256 = digest.removeprefix("sha256:") if digest.lower().startswith("sha256:") else ""
    return replace(
        release,
        asset_name=asset["name"],
        asset_url=asset["browser_download_url"],
        asset_size=size if isinstance(size, int) and 0 < size <= MAX_INSTALLER_BYTES else None,
        asset_sha256=sha256.lower() if _SHA256.fullmatch(sha256) else None,
    )


def _rate_limit_wait(response: httpx.Response) -> float:
    try:
        if "retry-after" in response.headers:
            return max(float(response.headers["retry-after"]), RATE_LIMIT_MIN_BACKOFF_SECONDS)
        reset = float(response.headers["x-ratelimit-reset"]) - time.time()
        return max(reset, RATE_LIMIT_MIN_BACKOFF_SECONDS)
    except (KeyError, ValueError):
        return RATE_LIMIT_MIN_BACKOFF_SECONDS


def fetch_latest_release(
    repo: str, timeout: float, transport: httpx.BaseTransport | None = None, api_base: str = GITHUB_API
) -> ReleaseInfo | None:
    """Última release publicada, ou ``None`` se o repositório ainda não tem nenhuma (404)."""
    if not valid_repo(repo):
        raise UpdateError("error", "UPDATE_REPO inválido: use o formato dono/repositório")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"PlusEduc/{__version__}",
    }
    try:
        with httpx.Client(timeout=timeout, transport=transport, headers=headers) as client:
            response = client.get(f"{api_base}/repos/{repo}/releases/latest")
    except httpx.HTTPError as exc:  # sem internet, DNS, timeout, TLS...
        raise UpdateError("offline", f"Sem acesso ao GitHub ({type(exc).__name__})") from exc

    if response.status_code == 404:
        return None
    if response.status_code == 429 or (
        response.status_code == 403
        and (response.headers.get("x-ratelimit-remaining") == "0" or "rate limit" in response.text.lower())
    ):
        raise UpdateError("rate_limited", "Limite de consultas do GitHub atingido", _rate_limit_wait(response))
    if response.status_code != 200:
        raise UpdateError("error", f"GitHub respondeu HTTP {response.status_code}")
    try:
        payload = response.json()
    except ValueError as exc:
        raise UpdateError("error", "Resposta do GitHub não é JSON") from exc
    return parse_release(payload, repo, None if api_base == GITHUB_API else api_base)


# --------------------------------------------------------------------------------------------- download


def download_installer(
    release: ReleaseInfo,
    repo: str,
    dest_dir: Path,
    progress: Callable[[float], None] | None = None,
    transport: httpx.BaseTransport | None = None,
    local_origin: str | None = None,
) -> Path:
    """Baixa e valida o instalador da release. Apaga o arquivo parcial em qualquer falha."""
    if not release.asset_url or not is_trusted_asset_url(release.asset_url, repo, local_origin):
        raise UpdateError("error", "A release não traz um instalador de origem confiável")
    target = dest_dir / f"PlusEduc-Setup-{release.version}.exe"
    partial = target.with_suffix(".part")
    limit = release.asset_size or MAX_INSTALLER_BYTES
    timeout = httpx.Timeout(connect=10.0, read=30.0, write=30.0, pool=10.0)
    try:
        with httpx.Client(timeout=timeout, transport=transport, headers={"User-Agent": f"PlusEduc/{__version__}"}) as client:
            url = release.asset_url
            for _ in range(MAX_REDIRECTS + 1):
                with client.stream("GET", url, follow_redirects=False) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers.get("location", ""))
                        if not _is_trusted_redirect(url, local_origin):
                            raise UpdateError("error", "Download redirecionado para um endereço não confiável")
                        continue
                    if response.status_code != 200:
                        raise UpdateError("error", f"Download falhou (HTTP {response.status_code})")
                    _stream_to_file(response, partial, limit, release, progress)
                    break
            else:
                raise UpdateError("error", "Redirecionamentos demais no download")
    except httpx.HTTPError as exc:
        partial.unlink(missing_ok=True)
        raise UpdateError("error", f"Download interrompido ({type(exc).__name__})") from exc
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    partial.replace(target)
    return target


def _stream_to_file(
    response: httpx.Response, partial: Path, limit: int, release: ReleaseInfo, progress: Callable[[float], None] | None
) -> None:
    total = int(response.headers.get("content-length") or 0) or release.asset_size or 0
    if total and total > limit:
        raise UpdateError("error", "Instalador maior que o tamanho informado pela release")
    digest, received = hashlib.sha256(), 0
    with partial.open("wb") as out:
        for chunk in response.iter_bytes(64 * 1024):
            received += len(chunk)
            if received > limit:
                raise UpdateError("error", "Instalador maior que o tamanho informado pela release")
            digest.update(chunk)
            out.write(chunk)
            if progress and total:
                progress(min(received / total, 1.0))
    if release.asset_size and received != release.asset_size:
        raise UpdateError("error", "Tamanho do instalador baixado difere do informado pela release")
    if release.asset_sha256 and digest.hexdigest() != release.asset_sha256:
        raise UpdateError("error", "Verificação SHA-256 do instalador falhou: arquivo descartado")
    with partial.open("rb") as check:
        if check.read(2) != b"MZ":
            raise UpdateError("error", "O arquivo baixado não é um executável do Windows")


def launch_installer(path: Path) -> None:
    """Inicia o instalador desvinculado do app (que se encerra em seguida)."""
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([str(path), *INSTALLER_ARGS], cwd=str(path.parent), close_fds=True, creationflags=flags)


# --------------------------------------------------------------------------------------------- gerenciador


class UpdateManager:
    """Estado da atualização: última verificação, download em andamento e disparo do instalador."""

    def __init__(
        self,
        settings: Settings,
        *,
        current_version: str = __version__,
        transport: httpx.BaseTransport | None = None,
        launcher: Callable[[Path], None] = launch_installer,
        frozen: bool | None = None,
        platform: str | None = None,
        initial_delay_seconds: float = 2.0,
        temp_root: Path | None = None,
    ) -> None:
        self.enabled = settings.update_check_enabled
        self.repo = settings.update_repo.strip()
        self.interval_seconds = settings.update_check_interval_hours * 3600
        self.timeout = settings.update_request_timeout_seconds
        self._api_error: UpdateError | None = None
        try:
            self.api_base, self.local_origin = resolve_api_base(settings.update_api_base)
        except UpdateError as exc:
            self._api_error, self.api_base, self.local_origin = exc, GITHUB_API, None
        self.current_version = current_version
        self._transport = transport
        self._launcher = launcher
        self._frozen = bool(getattr(sys, "frozen", False)) if frozen is None else frozen
        self._platform = platform or sys.platform
        self._initial_delay = initial_delay_seconds
        self._temp_root = temp_root

        self._lock = threading.Lock()  # protege o estado exposto; nunca é mantido durante I/O de rede
        self._check_lock = threading.Lock()  # uma verificação por vez
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._request_exit: Callable[[], None] | None = None
        self._headless = False

        self._status = "pending" if self.enabled else "disabled"
        self._message = ""
        self._release: ReleaseInfo | None = None
        self._checked_at: datetime | None = None
        self._last_check_monotonic = 0.0
        self._retry_after = 0.0
        self._download_state = "idle"  # idle | downloading | launching | error
        self._download_progress = 0.0
        self._download_error = ""

    # configuração do processo -------------------------------------------------------------------------------

    def configure_runtime(self, *, headless: bool, request_exit: Callable[[], None] | None, frozen: bool | None = None) -> None:
        """Informado por ``run_server``: sem janela (headless) não há usuário para acompanhar o instalador.

        ``frozen`` cobre o executável compilado pelo Nuitka, que não define ``sys.frozen`` como o PyInstaller.
        """
        self._headless = headless
        self._request_exit = request_exit
        if frozen is not None:
            self._frozen = frozen

    @property
    def can_install(self) -> bool:
        return self.enabled and self._frozen and self._platform == "win32" and not self._headless

    # verificação ---------------------------------------------------------------------------------------------

    def start(self) -> None:
        """Dispara a verificação periódica em segundo plano (thread daemon, nunca bloqueia a inicialização)."""
        if not self.enabled or self._thread is not None:
            return
        if not valid_repo(self.repo) or self._api_error:
            message = self._api_error.message if self._api_error else "UPDATE_REPO inválido: use o formato dono/repositório"
            self._set_check_result("error", message)
            return
        self._thread = threading.Thread(target=self._loop, name="pluseduc-update-check", daemon=True)
        self._thread.start()
        self._cleanup_old_downloads()

    def stop(self) -> None:
        self._stop.set()

    def _cleanup_old_downloads(self) -> None:
        """Remove instaladores de atualizações anteriores (pastas temporárias com mais de um dia)."""
        root = self._temp_root or Path(tempfile.gettempdir())
        try:
            for folder in root.glob("pluseduc-update-*"):
                if folder.is_dir() and time.time() - folder.stat().st_mtime > 86400:
                    shutil.rmtree(folder, ignore_errors=True)
        except OSError:
            pass

    def _loop(self) -> None:
        if self._stop.wait(self._initial_delay):
            return
        while not self._stop.is_set():
            self.check_now()
            with self._lock:
                wait = max(self.interval_seconds, self._retry_after)
            if self._stop.wait(wait):
                return

    def check_now(self) -> None:
        """Consulta o GitHub (uma verificação por vez). Nunca lança exceção."""
        if not self.enabled or not self._check_lock.acquire(blocking=False):
            return
        try:
            self._last_check_monotonic = time.monotonic()
            try:
                release = fetch_latest_release(self.repo, self.timeout, self._transport, self.api_base)
            except UpdateError as exc:
                logger.info("Verificação de atualização: %s (%s)", exc.message, exc.status)
                with self._lock:
                    self._retry_after = exc.retry_after_seconds or 0.0
                self._set_check_result(exc.status, exc.message)
                return
            except Exception:  # noqa: BLE001 - a verificação não pode quebrar o app
                logger.exception("Falha inesperada ao verificar atualização")
                self._set_check_result("error", "Falha inesperada ao verificar atualização")
                return
            with self._lock:
                self._retry_after = 0.0
            if release is None:
                self._set_check_result("no_release", "Nenhuma versão publicada ainda")
            elif is_newer(release.version, self.current_version):
                logger.info("Nova versão disponível: %s (instalada: %s)", release.version, self.current_version)
                self._set_check_result("available", "", release)
            else:
                self._set_check_result("up_to_date", "", release)
        finally:
            self._check_lock.release()

    def check_if_allowed(self) -> None:
        """Verificação pedida pela interface, no máximo uma a cada 30 s."""
        if time.monotonic() - self._last_check_monotonic >= MANUAL_CHECK_MIN_INTERVAL_SECONDS and self._retry_after <= 0:
            self.check_now()

    def _set_check_result(self, status: str, message: str, release: ReleaseInfo | None = None) -> None:
        with self._lock:
            self._status = status
            self._message = message
            self._release = release if status in ("available", "up_to_date") else None
            self._checked_at = datetime.now(timezone.utc)

    # instalação ----------------------------------------------------------------------------------------------

    def request_install(self) -> None:
        with self._lock:
            if self._status != "available" or self._release is None:
                raise UpdateError("error", "Não há atualização disponível")
            if not self.can_install:
                raise UpdateError("error", "Este modo de execução não permite instalar atualizações automaticamente")
            if not self._release.asset_url:
                raise UpdateError("error", "A release não traz o instalador; baixe-o na página da release")
            if self._download_state in ("downloading", "launching"):
                return
            release = self._release
            self._download_state, self._download_progress, self._download_error = "downloading", 0.0, ""
        threading.Thread(target=self._install_worker, args=(release,), name="pluseduc-update-install", daemon=True).start()

    def _install_worker(self, release: ReleaseInfo) -> None:
        folder: Path | None = None
        try:
            folder = Path(tempfile.mkdtemp(prefix="pluseduc-update-", dir=self._temp_root))
            installer = download_installer(release, self.repo, folder, self._set_progress, self._transport, self.local_origin)
            with self._lock:
                self._download_state = "launching"
            self._launcher(installer)
            logger.info("Instalador %s iniciado; encerrando o aplicativo para a atualização", installer.name)
            if self._request_exit is not None:
                self._request_exit()
        except UpdateError as exc:
            self._fail_install(exc.message, folder)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao atualizar o aplicativo")
            self._fail_install("Não foi possível iniciar o instalador", folder)

    def _fail_install(self, message: str, folder: Path | None) -> None:
        logger.warning("Atualização não concluída: %s", message)
        if folder is not None:
            shutil.rmtree(folder, ignore_errors=True)
        with self._lock:
            self._download_state, self._download_error = "error", message

    def _set_progress(self, value: float) -> None:
        self._download_progress = value

    # estado exposto à interface ------------------------------------------------------------------------------

    def snapshot(self) -> dict:
        with self._lock:
            release = self._release
            available = self._status == "available" and release is not None
            return {
                "currentVersion": self.current_version,
                "status": self._status,
                "message": self._message,
                "updateAvailable": available,
                "latestVersion": release.version if release else None,
                "releaseUrl": release.page_url if release else None,
                "releaseNotes": release.notes if release and available else None,
                "installerSize": release.asset_size if release else None,
                "canInstall": bool(available and self.can_install and release and release.asset_url),
                "checkedAt": self._checked_at,
                "download": {
                    "state": self._download_state,
                    "progress": round(self._download_progress, 3),
                    "error": self._download_error or None,
                },
            }
