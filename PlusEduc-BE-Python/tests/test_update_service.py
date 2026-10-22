import hashlib
import importlib.util
import os
import time
from pathlib import Path

import httpx
import pytest

from app.core.config import Settings
from app.services import update_service as svc
from app.services.update_service import ReleaseInfo, UpdateError, UpdateManager

REPO = "PedroBeltraoDev/PlusEduc-MonoRepo"
INSTALLER = b"MZ" + b"\x00" * 2048
INSTALLER_SHA = hashlib.sha256(INSTALLER).hexdigest()
ASSET_URL = f"https://github.com/{REPO}/releases/download/v0.2.0/PlusEduc-Setup.exe"


def release_payload(tag="v0.2.0", **overrides):
    payload = {
        "tag_name": tag,
        "draft": False,
        "prerelease": False,
        "body": "Novidades da versão",
        "assets": [
            {
                "name": "PlusEduc-Setup.exe",
                "state": "uploaded",
                "size": len(INSTALLER),
                "digest": f"sha256:{INSTALLER_SHA}",
                "browser_download_url": ASSET_URL,
            }
        ],
    }
    payload.update(overrides)
    return payload


def make_settings(**overrides) -> Settings:
    return Settings(app_env="test", jwt_secret="x" * 32, **overrides)


def api_transport(response: httpx.Response | Exception):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "api.github.com"
        assert request.url.path == f"/repos/{REPO}/releases/latest"
        if isinstance(response, Exception):
            raise response
        return response

    return httpx.MockTransport(handler)


def wait_for(predicate, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return False


# --- versões -------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("candidate", "current", "expected"),
    [
        ("0.2.0", "0.1.0", True),
        ("v0.1.1", "0.1.0", True),
        ("0.10.0", "0.9.0", True),  # comparação numérica, não de texto
        ("1.0", "0.9.9", True),
        ("0.1.0", "0.1.0", False),
        ("v0.1.0", "0.1.0", False),
        ("0.0.9", "0.1.0", False),
        ("1.0.0", "1.0.0-rc.1", True),  # final > pré-lançamento
        ("1.0.0-rc.2", "1.0.0-rc.1", True),
        ("1.0.0-rc.1", "1.0.0", False),
        ("1.0.0-beta.11", "1.0.0-beta.2", True),
        ("lixo", "0.1.0", False),
        ("0.2.0", "lixo", False),
    ],
)
def test_is_newer(candidate, current, expected):
    assert svc.is_newer(candidate, current) is expected


def test_parse_version_rejects_invalid():
    assert svc.parse_version("") is None
    assert svc.parse_version("a.b.c") is None
    assert svc.parse_version(None) is None  # type: ignore[arg-type]


def test_version_is_single_source_for_build():
    from app.version import __version__

    spec = importlib.util.spec_from_file_location("build_exe", Path(__file__).parents[1] / "scripts" / "build_exe.py")
    build_exe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_exe)
    assert build_exe.app_version() == __version__
    assert Settings().app_version == __version__


# --- URLs confiáveis -----------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        f"http://github.com/{REPO}/releases/download/v1/PlusEduc-Setup.exe",  # sem https
        f"https://evil.com/{REPO}/releases/download/v1/PlusEduc-Setup.exe",
        f"https://github.com.evil.com/{REPO}/releases/download/v1/PlusEduc-Setup.exe",
        f"https://user@github.com/{REPO}/releases/download/v1/PlusEduc-Setup.exe",
        f"https://github.com:8443/{REPO}/releases/download/v1/PlusEduc-Setup.exe",
        "https://github.com/OutroDono/Outro/releases/download/v1/PlusEduc-Setup.exe",
        f"https://github.com/{REPO}/archive/main.zip",
        f"https://github.com/{REPO}/releases/download/../../x/y/releases/download/a.exe",
        "",
    ],
)
def test_untrusted_asset_urls_are_rejected(url):
    assert svc.is_trusted_asset_url(url, REPO) is False


def test_trusted_asset_url_is_case_insensitive_on_repo():
    assert svc.is_trusted_asset_url(ASSET_URL.replace("PedroBeltraoDev", "pedrobeltraodev"), REPO)


# --- parsing da release --------------------------------------------------------------------------------------


def test_parse_release_picks_stable_installer_asset():
    release = svc.parse_release(release_payload(), REPO)
    assert release.version == "0.2.0"
    assert release.asset_name == "PlusEduc-Setup.exe"
    assert release.asset_url == ASSET_URL
    assert release.asset_size == len(INSTALLER)
    assert release.asset_sha256 == INSTALLER_SHA
    assert release.page_url == f"https://github.com/{REPO}/releases/tag/v0.2.0"
    assert release.notes == "Novidades da versão"


def test_parse_release_prefers_stable_name_over_versioned():
    versioned = {**release_payload()["assets"][0], "name": "PlusEduc-Setup-0.2.0.exe"}
    payload = release_payload(assets=[versioned, release_payload()["assets"][0]])
    assert svc.parse_release(payload, REPO).asset_name == "PlusEduc-Setup.exe"
    assert svc.parse_release(release_payload(assets=[versioned]), REPO).asset_name == "PlusEduc-Setup-0.2.0.exe"


def test_parse_release_without_installer_asset_still_reports_version():
    release = svc.parse_release(release_payload(assets=[{"name": "notas.txt"}]), REPO)
    assert release.version == "0.2.0"
    assert release.asset_url is None


def test_parse_release_ignores_asset_from_untrusted_url():
    asset = {**release_payload()["assets"][0], "browser_download_url": "https://evil.example/PlusEduc-Setup.exe"}
    assert svc.parse_release(release_payload(assets=[asset]), REPO).asset_url is None


def test_parse_release_without_digest_or_size():
    asset = {"name": "PlusEduc-Setup.exe", "browser_download_url": ASSET_URL, "size": "x", "digest": None}
    release = svc.parse_release(release_payload(assets=[asset]), REPO)
    assert release.asset_url == ASSET_URL
    assert release.asset_sha256 is None
    assert release.asset_size is None


@pytest.mark.parametrize("payload", [None, [], "x", {"tag_name": "nao-e-versao"}, {"tag_name": 3}, {}])
def test_parse_release_rejects_garbage(payload):
    with pytest.raises(UpdateError) as caught:
        svc.parse_release(payload, REPO)
    assert caught.value.status == "error"


def test_parse_release_ignores_drafts_and_prereleases():
    for flag in ("draft", "prerelease"):
        with pytest.raises(UpdateError) as caught:
            svc.parse_release(release_payload(**{flag: True}), REPO)
        assert caught.value.status == "no_release"


# --- consulta ao GitHub --------------------------------------------------------------------------------------


def test_fetch_latest_release_ok():
    release = svc.fetch_latest_release(REPO, 5, api_transport(httpx.Response(200, json=release_payload())))
    assert release is not None and release.version == "0.2.0"


def test_fetch_latest_release_without_any_release_returns_none():
    body = {"message": "Not Found"}
    assert svc.fetch_latest_release(REPO, 5, api_transport(httpx.Response(404, json=body))) is None


@pytest.mark.parametrize(
    "error",
    [httpx.ConnectError("sem rede"), httpx.ConnectTimeout("lento"), httpx.ReadTimeout("lento"), httpx.RemoteProtocolError("x")],
)
def test_fetch_latest_release_offline(error):
    with pytest.raises(UpdateError) as caught:
        svc.fetch_latest_release(REPO, 5, api_transport(error))
    assert caught.value.status == "offline"


def test_fetch_latest_release_rate_limited():
    reset = str(int(time.time()) + 3600)
    headers = {"x-ratelimit-remaining": "0", "x-ratelimit-reset": reset}
    response = httpx.Response(403, json={"message": "API rate limit exceeded"}, headers=headers)
    with pytest.raises(UpdateError) as caught:
        svc.fetch_latest_release(REPO, 5, api_transport(response))
    assert caught.value.status == "rate_limited"
    assert 3000 < caught.value.retry_after_seconds <= 3700

    with pytest.raises(UpdateError) as caught:
        svc.fetch_latest_release(REPO, 5, api_transport(httpx.Response(429, headers={"retry-after": "7200"})))
    assert caught.value.status == "rate_limited" and caught.value.retry_after_seconds == 7200


@pytest.mark.parametrize(
    "response",
    [httpx.Response(500), httpx.Response(403, json={"message": "forbidden"}), httpx.Response(200, text="<html>")],
)
def test_fetch_latest_release_other_failures(response):
    with pytest.raises(UpdateError) as caught:
        svc.fetch_latest_release(REPO, 5, api_transport(response))
    assert caught.value.status == "error"


def test_fetch_latest_release_rejects_invalid_repo():
    with pytest.raises(UpdateError):
        svc.fetch_latest_release("../../etc/passwd", 5, api_transport(httpx.Response(200)))


# --- download ------------------------------------------------------------------------------------------------


def download_transport(*, body=INSTALLER, status=200, redirect_to=None):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "github.com" and redirect_to:
            return httpx.Response(302, headers={"location": redirect_to})
        return httpx.Response(status, content=body)

    return httpx.MockTransport(handler)


def release_info(**overrides) -> ReleaseInfo:
    base = dict(
        version="0.2.0", tag="v0.2.0", page_url="x", notes="", asset_name="PlusEduc-Setup.exe",
        asset_url=ASSET_URL, asset_size=len(INSTALLER), asset_sha256=INSTALLER_SHA,
    )
    base.update(overrides)
    return ReleaseInfo(**base)


def test_download_follows_github_redirect_and_verifies(tmp_path):
    storage = "https://release-assets.githubusercontent.com/github-production-release-asset/1/PlusEduc-Setup.exe"
    progress = []
    path = svc.download_installer(release_info(), REPO, tmp_path, progress.append, download_transport(redirect_to=storage))
    assert path.read_bytes() == INSTALLER
    assert path.name == "PlusEduc-Setup-0.2.0.exe"
    assert progress and progress[-1] == 1.0
    assert not list(tmp_path.glob("*.part"))


def test_download_refuses_redirect_to_other_host(tmp_path):
    transport = download_transport(redirect_to="https://evil.example/a.exe")
    with pytest.raises(UpdateError, match="não confiável"):
        svc.download_installer(release_info(), REPO, tmp_path, None, transport)
    assert not list(tmp_path.iterdir())


def test_download_refuses_untrusted_asset_url(tmp_path):
    with pytest.raises(UpdateError):
        svc.download_installer(release_info(asset_url="https://evil.example/a.exe"), REPO, tmp_path, None, download_transport())


def test_download_rejects_hash_mismatch_and_discards_file(tmp_path):
    with pytest.raises(UpdateError, match="SHA-256"):
        svc.download_installer(release_info(asset_sha256="0" * 64), REPO, tmp_path, None, download_transport())
    assert not list(tmp_path.iterdir())


def test_download_rejects_size_mismatch(tmp_path):
    with pytest.raises(UpdateError):
        svc.download_installer(release_info(asset_size=len(INSTALLER) + 1), REPO, tmp_path, None, download_transport())
    with pytest.raises(UpdateError):  # maior que o informado
        svc.download_installer(release_info(asset_size=100), REPO, tmp_path, None, download_transport())
    assert not list(tmp_path.iterdir())


def test_download_rejects_non_executable(tmp_path):
    html = b"<html>erro</html>" + b"\x00" * 100
    release = release_info(asset_size=len(html), asset_sha256=hashlib.sha256(html).hexdigest())
    with pytest.raises(UpdateError, match="executável"):
        svc.download_installer(release, REPO, tmp_path, None, download_transport(body=html))
    assert not list(tmp_path.iterdir())


def test_download_http_error_and_network_failure(tmp_path):
    with pytest.raises(UpdateError, match="HTTP 404"):
        svc.download_installer(release_info(), REPO, tmp_path, None, download_transport(status=404))

    def broken(request):
        raise httpx.ConnectError("caiu")

    with pytest.raises(UpdateError, match="interrompido"):
        svc.download_installer(release_info(), REPO, tmp_path, None, httpx.MockTransport(broken))
    assert not list(tmp_path.iterdir())


# --- gerenciador ---------------------------------------------------------------------------------------------


def combined_transport(api: httpx.Response | Exception):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.github.com":
            if isinstance(api, Exception):
                raise api
            return api
        return httpx.Response(200, content=INSTALLER)

    return httpx.MockTransport(handler)


def manager_for(api, tmp_path, **kwargs) -> UpdateManager:
    kwargs.setdefault("frozen", True)
    kwargs.setdefault("platform", "win32")
    return UpdateManager(make_settings(), current_version="0.1.0", transport=combined_transport(api), temp_root=tmp_path, **kwargs)


def test_manager_reports_available_update(tmp_path):
    manager = manager_for(httpx.Response(200, json=release_payload()), tmp_path)
    manager.check_now()
    snapshot = manager.snapshot()
    assert snapshot["status"] == "available"
    assert snapshot["updateAvailable"] is True
    assert snapshot["latestVersion"] == "0.2.0"
    assert snapshot["currentVersion"] == "0.1.0"
    assert snapshot["canInstall"] is True
    assert snapshot["releaseUrl"].endswith("/releases/tag/v0.2.0")


def test_manager_up_to_date_changes_nothing(tmp_path):
    manager = manager_for(httpx.Response(200, json=release_payload("v0.1.0")), tmp_path)
    manager.check_now()
    snapshot = manager.snapshot()
    assert snapshot["status"] == "up_to_date" and snapshot["updateAvailable"] is False and snapshot["canInstall"] is False


def test_manager_older_release_is_not_an_update(tmp_path):
    manager = manager_for(httpx.Response(200, json=release_payload("v0.0.5")), tmp_path)
    manager.check_now()
    assert manager.snapshot()["updateAvailable"] is False


def test_manager_no_release_published(tmp_path):
    manager = manager_for(httpx.Response(404, json={"message": "Not Found"}), tmp_path)
    manager.check_now()
    assert manager.snapshot()["status"] == "no_release" and manager.snapshot()["updateAvailable"] is False


def test_manager_offline_and_rate_limit_never_raise(tmp_path):
    offline = manager_for(httpx.ConnectError("sem rede"), tmp_path)
    offline.check_now()
    assert offline.snapshot()["status"] == "offline"

    limited = manager_for(httpx.Response(429), tmp_path)
    limited.check_now()
    assert limited.snapshot()["status"] == "rate_limited"
    assert limited._retry_after >= svc.RATE_LIMIT_MIN_BACKOFF_SECONDS


def test_manager_unexpected_exception_is_contained(tmp_path):
    def explode(request):
        raise RuntimeError("bug")

    manager = UpdateManager(make_settings(), transport=httpx.MockTransport(explode), temp_root=tmp_path)
    manager.check_now()
    assert manager.snapshot()["status"] == "error"


def test_manager_disabled_does_not_touch_network(tmp_path):
    def forbidden(request):
        raise AssertionError("não deveria consultar a rede")

    manager = UpdateManager(make_settings(update_check_enabled=False), transport=httpx.MockTransport(forbidden), temp_root=tmp_path)
    manager.start()
    manager.check_now()
    assert manager.snapshot()["status"] == "disabled"
    assert manager._thread is None


def test_manager_invalid_repo_is_reported_without_thread(tmp_path):
    manager = UpdateManager(make_settings(update_repo="isso não é um repo"), temp_root=tmp_path)
    manager.start()
    assert manager.snapshot()["status"] == "error" and manager._thread is None


def test_manager_start_checks_in_background(tmp_path):
    manager = manager_for(httpx.Response(200, json=release_payload()), tmp_path, initial_delay_seconds=0)
    started = time.monotonic()
    manager.start()
    assert time.monotonic() - started < 1  # start() não espera a rede
    assert wait_for(lambda: manager.snapshot()["status"] == "available")
    manager.stop()


def test_manual_check_is_throttled(tmp_path):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(404)

    manager = UpdateManager(make_settings(), transport=httpx.MockTransport(handler), temp_root=tmp_path)
    manager.check_if_allowed()
    manager.check_if_allowed()
    assert len(calls) == 1


def test_install_downloads_launches_and_exits(tmp_path):
    launched, exited = [], []
    manager = manager_for(httpx.Response(200, json=release_payload()), tmp_path, launcher=launched.append)
    manager.configure_runtime(headless=False, request_exit=lambda: exited.append(True))
    manager.check_now()
    manager.request_install()
    assert wait_for(lambda: exited)
    assert len(launched) == 1 and launched[0].read_bytes() == INSTALLER
    assert manager.snapshot()["download"]["state"] == "launching"


def test_install_failure_is_reported_and_retryable(tmp_path):
    launched = []
    bad_asset = {**release_payload()["assets"][0], "digest": "sha256:" + "0" * 64}
    manager = manager_for(httpx.Response(200, json=release_payload(assets=[bad_asset])), tmp_path, launcher=launched.append)
    manager.configure_runtime(headless=False, request_exit=lambda: None)
    manager.check_now()
    manager.request_install()
    assert wait_for(lambda: manager.snapshot()["download"]["state"] == "error")
    assert "SHA-256" in manager.snapshot()["download"]["error"]
    assert launched == []  # instalador não validado nunca é executado
    assert not list(tmp_path.glob("pluseduc-update-*/*"))
    manager.request_install()  # pode tentar de novo
    assert wait_for(lambda: manager.snapshot()["download"]["state"] == "error")


def test_install_launcher_failure_is_reported(tmp_path):
    def failing(path):
        raise OSError("sem permissão")

    exited = []
    manager = manager_for(httpx.Response(200, json=release_payload()), tmp_path, launcher=failing)
    manager.configure_runtime(headless=False, request_exit=lambda: exited.append(1))
    manager.check_now()
    manager.request_install()
    assert wait_for(lambda: manager.snapshot()["download"]["state"] == "error")
    assert exited == []  # se o instalador não subiu, o app continua aberto


@pytest.mark.parametrize(
    ("frozen", "platform", "headless"),
    [(False, "win32", False), (True, "linux", False), (True, "win32", True)],
)
def test_install_refused_when_not_installed_app_or_headless(tmp_path, frozen, platform, headless):
    manager = manager_for(httpx.Response(200, json=release_payload()), tmp_path, frozen=frozen, platform=platform)
    manager.configure_runtime(headless=headless, request_exit=None)
    manager.check_now()
    snapshot = manager.snapshot()
    assert snapshot["updateAvailable"] is True and snapshot["canInstall"] is False
    with pytest.raises(UpdateError):
        manager.request_install()


def test_runtime_can_declare_the_app_as_installed_for_nuitka_builds(tmp_path):
    """O Nuitka não define ``sys.frozen``: ``run_server`` informa por ``configure_runtime(frozen=True)``."""
    manager = manager_for(httpx.Response(200, json=release_payload()), tmp_path, frozen=False, platform="win32")
    manager.configure_runtime(headless=False, request_exit=None, frozen=True)
    manager.check_now()
    assert manager.snapshot()["canInstall"] is True


def test_install_refused_without_available_update(tmp_path):
    manager = manager_for(httpx.Response(404), tmp_path)
    manager.check_now()
    with pytest.raises(UpdateError):
        manager.request_install()


def test_release_without_installer_asset_cannot_be_installed(tmp_path):
    manager = manager_for(httpx.Response(200, json=release_payload(assets=[])), tmp_path)
    manager.check_now()
    snapshot = manager.snapshot()
    assert snapshot["updateAvailable"] is True and snapshot["canInstall"] is False
    with pytest.raises(UpdateError):
        manager.request_install()


def test_old_download_folders_are_cleaned(tmp_path):
    old = tmp_path / "pluseduc-update-velha"
    new = tmp_path / "pluseduc-update-nova"
    old.mkdir()
    new.mkdir()
    ancient = time.time() - 3 * 86400
    os.utime(old, (ancient, ancient))
    manager = UpdateManager(
        make_settings(), transport=httpx.MockTransport(lambda r: httpx.Response(404)), temp_root=tmp_path, initial_delay_seconds=60
    )
    manager.start()
    manager.stop()
    assert not old.exists() and new.exists()


# --- servidor de teste local (UPDATE_API_BASE) ----------------------------------------------------------------


def test_api_base_defaults_to_github_and_accepts_only_loopback_test_servers():
    assert svc.resolve_api_base("") == (svc.GITHUB_API, None)
    assert svc.resolve_api_base("https://api.github.com/") == (svc.GITHUB_API, None)
    assert svc.resolve_api_base("http://127.0.0.1:9099") == ("http://127.0.0.1:9099", "http://127.0.0.1:9099")
    assert svc.resolve_api_base("http://localhost:9099/") == ("http://localhost:9099", "http://localhost:9099")
    for bad in ("https://evil.example", "http://evil.example:80", "http://127.0.0.1", "http://127.0.0.1:9/x", "ftp://127.0.0.1:9", "https://127.0.0.1:9"):
        with pytest.raises(UpdateError):
            svc.resolve_api_base(bad)


def test_manager_with_invalid_api_base_reports_error_and_never_connects(tmp_path):
    manager = UpdateManager(make_settings(update_api_base="https://evil.example"), temp_root=tmp_path)
    manager.start()
    assert manager.snapshot()["status"] == "error" and manager._thread is None


def test_manager_with_local_test_server_accepts_only_that_origin(tmp_path):
    origin = "http://127.0.0.1:9099"
    asset = {**release_payload()["assets"][0], "browser_download_url": f"{origin}/PlusEduc-Setup.exe"}
    hosts = []

    def handler(request: httpx.Request) -> httpx.Response:
        hosts.append(request.url.host)
        if request.url.path.endswith("/releases/latest"):
            return httpx.Response(200, json=release_payload(assets=[asset]))
        return httpx.Response(200, content=INSTALLER)

    launched = []
    manager = UpdateManager(
        make_settings(update_api_base=origin), current_version="0.1.0", transport=httpx.MockTransport(handler),
        launcher=launched.append, frozen=True, platform="win32", temp_root=tmp_path,
    )
    manager.configure_runtime(headless=False, request_exit=lambda: None)
    manager.check_now()
    assert manager.snapshot()["canInstall"] is True
    manager.request_install()
    assert wait_for(lambda: launched)
    assert set(hosts) == {"127.0.0.1"}

    # um asset apontando para o GitHub (ou outro host) não vale quando a origem confiável é o servidor local
    other = {**asset, "browser_download_url": ASSET_URL}
    assert svc.parse_release(release_payload(assets=[other]), REPO, origin).asset_url is None
