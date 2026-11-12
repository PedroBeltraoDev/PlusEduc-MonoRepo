"""Documentação da API (Sprint 10): toda rota sai no OpenAPI com resumo em português, grupo e perfil de acesso."""

from app.api.openapi_docs import TAGS, access_of
from tests.test_permissions_sprint8 import policy

METHODS = {"get", "post", "put", "patch", "delete"}
EXPECTED_ACCESS = {"public": {"público"}, "any": {"qualquer usuário autenticado", "TEACHER ou ADMIN; STUDENT apenas para o próprio registro"},
                   "student": {"STUDENT"}, "staff": {"TEACHER ou ADMIN", "ADMIN"}}


def operations(client):
    schema = client.get("/openapi.json").json()
    return schema, [(method.upper(), path, operation) for path, item in schema["paths"].items() for method, operation in item.items() if method in METHODS]


def test_every_route_has_summary_group_and_access(client):
    schema, rows = operations(client)
    assert len(rows) >= 99
    group_names = {tag["name"] for tag in schema["tags"]}
    assert group_names <= {name for name, _ in TAGS.values()}
    for method, path, operation in rows:
        auto_generated = operation["operationId"].split("_api_")[0].split("_health_")[0].replace("_", " ").title()
        assert operation.get("summary") and operation["summary"] != auto_generated, f"{method} {path} sem resumo próprio"
        assert operation["tags"] and operation["tags"][0] in group_names, f"{method} {path} sem grupo"
        assert operation["description"].startswith("**Acesso:**"), f"{method} {path} sem perfil de acesso"


def test_documented_access_matches_the_permission_matrix(client):
    _, rows = operations(client)
    for method, path, operation in rows:
        assert operation["x-acesso"] == access_of(method, path)
        assert operation["x-acesso"] in EXPECTED_ACCESS[policy(method, path)], f"{method} {path}: documentação diz {operation['x-acesso']}"
        if operation["x-acesso"] == "público":
            assert operation.get("security") == []
        else:
            assert "401" in operation["responses"]


def test_api_description_explains_authentication(client):
    info = client.get("/openapi.json").json()["info"]
    assert "Authorization: Bearer" in info["description"] and "/api/auth/refresh" in info["description"]
