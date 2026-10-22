import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture
def web_client(tmp_path):
    (tmp_path / "index.html").write_text('<div id="root"></div>', encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    settings = Settings(
        app_env="test",
        jwt_secret="test-only-secret-that-is-not-production",
        mongodb_uri="mongodb://127.0.0.1:27018",
        mongodb_server_selection_timeout_ms=50,
        mongodb_connect_timeout_ms=50,
        frontend_dist=str(tmp_path),
        opencl_enabled=False,
    )
    with TestClient(create_app(settings)) as client:
        yield client


def test_serves_index_and_assets(web_client):
    assert 'id="root"' in web_client.get("/").text
    assert web_client.get("/assets/app.js").text == "console.log(1)"


def test_client_routes_fall_back_to_index(web_client):
    response = web_client.get("/turmas/abc/detalhes")
    assert response.status_code == 200
    assert 'id="root"' in response.text


def test_missing_files_and_unknown_api_paths_are_404(web_client):
    assert web_client.get("/assets/nao-existe.js").status_code == 404
    assert web_client.get("/api/nao-existe").status_code == 404


def test_api_and_docs_keep_priority_over_the_interface(web_client):
    assert web_client.get("/health").json()["service"] == "PlusEduc API"
    assert web_client.get("/openapi.json").status_code == 200
    assert web_client.get("/api/classrooms").status_code == 401


def test_no_frontend_mounted_by_default(client):
    assert client.get("/").status_code == 404
