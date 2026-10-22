import httpx
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.update_service import UpdateManager
from tests.test_update_service import INSTALLER, make_settings, release_payload, wait_for

INSTALL_HEADERS = {"X-PlusEduc-Update": "1"}


def build_client(tmp_path, api_response, *, launcher=None, frozen=True):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.github.com":
            if isinstance(api_response, Exception):
                raise api_response
            return api_response
        return httpx.Response(200, content=INSTALLER)

    settings = make_settings(
        mongodb_uri="mongodb://127.0.0.1:27018",
        mongodb_server_selection_timeout_ms=50,
        mongodb_connect_timeout_ms=50,
        opencl_enabled=False,
    )
    manager = UpdateManager(
        settings,
        current_version="0.1.0",
        transport=httpx.MockTransport(handler),
        launcher=launcher or (lambda path: None),
        frozen=frozen,
        platform="win32",
        temp_root=tmp_path,
    )
    manager.configure_runtime(headless=False, request_exit=lambda: None)
    return TestClient(create_app(settings, update_manager=manager)), manager


def test_version_endpoint(client):
    response = client.get("/api/app/version")
    assert response.status_code == 200
    assert response.json() == {"version": Settings().app_version}


def test_app_startup_never_checks_for_updates_by_itself(client):
    payload = client.get("/api/app/update").json()
    assert payload["status"] == "pending" and payload["updateAvailable"] is False
    assert client.app.state.update_manager._thread is None


def test_update_endpoint_reports_new_version(tmp_path):
    client, manager = build_client(tmp_path, httpx.Response(200, json=release_payload("v0.3.0")))
    with client:
        manager.check_now()
        payload = client.get("/api/app/update").json()
    assert payload["updateAvailable"] is True
    assert payload["latestVersion"] == "0.3.0" and payload["currentVersion"] == "0.1.0"
    assert payload["canInstall"] is True
    assert payload["download"] == {"state": "idle", "progress": 0.0, "error": None}


@pytest.mark.parametrize(
    ("api_response", "status"),
    [
        (httpx.Response(404), "no_release"),
        (httpx.ConnectError("sem rede"), "offline"),
        (httpx.Response(200, json=release_payload("v0.1.0")), "up_to_date"),
    ],
)
def test_update_endpoint_states_without_update(tmp_path, api_response, status):
    client, manager = build_client(tmp_path, api_response)
    with client:
        response = client.post("/api/app/update/check")
        assert response.status_code == 200
        assert response.json()["status"] == status
        assert response.json()["updateAvailable"] is False
        assert response.json()["canInstall"] is False


def test_install_requires_custom_header(tmp_path):
    launched = []
    client, manager = build_client(tmp_path, httpx.Response(200, json=release_payload("v0.3.0")), launcher=launched.append)
    with client:
        manager.check_now()
        assert client.post("/api/app/update/install").status_code == 400
        assert client.post("/api/app/update/install", headers={"X-PlusEduc-Update": "0"}).status_code == 400
    assert launched == [] and manager.snapshot()["download"]["state"] == "idle"


def test_install_endpoint_triggers_update_flow(tmp_path):
    launched = []
    client, manager = build_client(tmp_path, httpx.Response(200, json=release_payload("v0.3.0")), launcher=launched.append)
    with client:
        manager.check_now()
        response = client.post("/api/app/update/install", headers=INSTALL_HEADERS)
        assert response.status_code == 202
        assert wait_for(lambda: launched)
        assert client.get("/api/app/update").json()["download"]["state"] in ("launching", "downloading")
    assert launched[0].read_bytes() == INSTALLER


def test_install_without_update_or_outside_installed_app_is_conflict(tmp_path):
    client, manager = build_client(tmp_path, httpx.Response(404))
    with client:
        manager.check_now()
        assert client.post("/api/app/update/install", headers=INSTALL_HEADERS).status_code == 409

    client, manager = build_client(tmp_path, httpx.Response(200, json=release_payload("v0.3.0")), frozen=False)
    with client:
        manager.check_now()
        assert client.post("/api/app/update/install", headers=INSTALL_HEADERS).status_code == 409
        assert client.get("/api/app/update").json()["canInstall"] is False
