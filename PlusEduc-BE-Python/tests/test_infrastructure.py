def test_cors_headers_are_compatible_with_frontend(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_http_errors_keep_the_common_api_shape(client):
    response = client.get("/missing")

    assert response.status_code == 404
    payload = response.json()
    assert payload["status"] == 404
    assert payload["error"] == "HTTP Error"
    assert payload["message"]
    assert "timestamp" in payload
