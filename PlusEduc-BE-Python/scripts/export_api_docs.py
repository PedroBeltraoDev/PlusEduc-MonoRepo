"""Gera a documentação da API a partir do esquema OpenAPI do próprio backend.

    python scripts/export_api_docs.py            (a partir de PlusEduc-BE-Python, com o .venv ativo)

Saídas (na raiz do repositório):
* ``docs/api/openapi.json`` — esquema OpenAPI 3.1 completo (importável no Postman, Insomnia etc.);
* ``docs/API.md`` — referência legível: autenticação, exemplos, todas as rotas por grupo e os campos de cada corpo.

Não precisa do MongoDB nem do servidor em execução: o esquema é montado em memória.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))
os.environ.setdefault("JWT_SECRET", "apenas-para-gerar-a-documentacao")
os.environ.setdefault("MONGODB_REQUIRED", "false")

from app.api.openapi_docs import API_DESCRIPTION  # noqa: E402
from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402

METHODS = ("get", "post", "put", "patch", "delete")

EXAMPLES = """
## Exemplos de uso

Os exemplos usam `curl` contra o servidor local (`http://127.0.0.1:8080`). Troque os valores entre `<>`.

### 1. Entrar e guardar o token

```bash
curl -s -X POST http://127.0.0.1:8080/api/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "<e-mail>", "password": "<senha>"}'
```

```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIs...",
  "refreshToken": "eyJhbGciOiJIUzI1NiIs...",
  "tokenType": "Bearer",
  "expiresIn": 28800,
  "userId": "6a0f1f9d20a4a3f5efdd7cb1",
  "userEmail": "<e-mail>",
  "role": "TEACHER",
  "name": "Marina Ferreira"
}
```

E-mail ou senha errados: `401` com `{"message": "Invalid email or password"}`. Professor com cadastro ainda não
aprovado: `403` com a mensagem de aprovação pendente.

### 2. Chamar uma rota protegida

```bash
curl -s http://127.0.0.1:8080/api/classrooms -H "Authorization: Bearer <accessToken>"
```

### 3. Renovar a sessão

```bash
curl -s -X POST http://127.0.0.1:8080/api/auth/refresh \\
  -H "Content-Type: application/json" \\
  -d '{"refreshToken": "<refreshToken>"}'
```

A resposta tem o mesmo formato do login, com um novo par de tokens.

### 4. Criar uma turma

```bash
curl -s -X POST http://127.0.0.1:8080/api/classrooms \\
  -H "Authorization: Bearer <accessToken>" -H "Content-Type: application/json" \\
  -d '{"name": "7º Ano do Ensino Fundamental E", "year": 2026, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": "<id do professor>"}'
```

`201` com a turma criada. `409` se já existir turma com o mesmo nome e ano; `400` se o professor não existir,
estiver inativo ou já tiver 5 turmas ativas. As matérias são preenchidas conforme a série (BNCC).

### 5. Lançar uma nota

```bash
curl -s -X POST http://127.0.0.1:8080/api/grades \\
  -H "Authorization: Bearer <accessToken>" -H "Content-Type: application/json" \\
  -d '{"studentId": "<id do aluno>", "classroomId": "<id da turma>", "grade": 8.5, "attendance": true, "subject": "Matemática", "activityType": "EXAM", "date": "2026-11-10T12:00:00Z"}'
```

`201` com a nota. `400` se o aluno não estiver matriculado na turma; `422` se a nota estiver fora de 0 a 10 ou a
data estiver no futuro.

### 6. Aluno envia as respostas de uma atividade

```bash
curl -s -X POST http://127.0.0.1:8080/api/student-portal/activities/<id da atividade>/submissions \\
  -H "Authorization: Bearer <accessToken do aluno>" -H "Content-Type: application/json" \\
  -d '{"answers": [{"questionIndex": 0, "selectedAnswer": "B"}, {"questionIndex": 1, "selectedAnswer": "Texto da resposta discursiva"}]}'
```

As questões objetivas voltam corrigidas na resposta; as discursivas ficam aguardando o professor
(`PUT /api/teacher/activity-corrections/{submission_id}/questions/{question_index}`).

### 7. Exportar um relatório

```bash
curl -s -o boletim.xlsx "http://127.0.0.1:8080/api/reports/<tipo>/export?format=xlsx&classroomId=<id da turma>" \\
  -H "Authorization: Bearer <accessToken>"
```

Os tipos de relatório disponíveis vêm de `GET /api/reports`; `format` aceita `csv`, `xlsx` e `pdf`.
""".strip()


def ref_name(schema: dict[str, Any]) -> str | None:
    ref = schema.get("$ref")
    return ref.rsplit("/", 1)[-1] if ref else None


def type_of(schema: dict[str, Any]) -> str:
    """Tipo legível de um campo do esquema (resolve referências, listas e opcionais)."""
    if not schema:
        return "qualquer"
    name = ref_name(schema)
    if name:
        return f"[{name}](#{name.lower()})"
    for key in ("anyOf", "oneOf"):
        if key in schema:
            parts = [type_of(item) for item in schema[key] if item.get("type") != "null"]
            optional = any(item.get("type") == "null" for item in schema[key])
            text = " ou ".join(dict.fromkeys(parts)) or "nulo"
            return text + (" (ou nulo)" if optional else "")
    kind = schema.get("type")
    if kind == "array":
        return f"lista de {type_of(schema.get('items', {}))}"
    if "enum" in schema:
        return " \\| ".join(f"`{value}`" for value in schema["enum"])
    names = {"string": "texto", "integer": "inteiro", "number": "número", "boolean": "booleano", "object": "objeto"}
    text = names.get(str(kind), str(kind or "qualquer"))
    if schema.get("format"):
        text += f" ({schema['format']})"
    return text


def limits_of(schema: dict[str, Any]) -> str:
    labels = (("minLength", "mín. {} caracteres"), ("maxLength", "máx. {} caracteres"), ("minimum", "mín. {}"), ("maximum", "máx. {}"),
              ("exclusiveMinimum", "maior que {}"), ("exclusiveMaximum", "menor que {}"), ("maxItems", "máx. {} itens"), ("minItems", "mín. {} itens"), ("pattern", "formato `{}`"))
    sources = [schema] + [item for key in ("anyOf", "oneOf") for item in schema.get(key, [])]
    found: list[str] = []
    for source in sources:
        for key, text in labels:
            if key in source:
                value = source[key]
                if isinstance(value, float) and value.is_integer():
                    value = int(value)
                found.append(text.format(value))
    if "default" in schema and schema["default"] not in (None, [], {}):
        found.append(f"padrão: `{schema['default']}`")
    return "; ".join(dict.fromkeys(found))


def cell(text: Any) -> str:
    """Texto seguro para uma célula de tabela Markdown (barras verticais escapadas uma única vez)."""
    flat = str(text or "").replace("\n", " ")
    return re.sub(r"(?<!\\)\|", lambda _match: "\\|", flat)


def body_schema(operation: dict[str, Any]) -> str:
    content = operation.get("requestBody", {}).get("content", {})
    for media in content.values():
        schema = media.get("schema", {})
        return type_of(schema)
    return ""


def response_schema(response: dict[str, Any]) -> str:
    for media_type, media in response.get("content", {}).items():
        schema = media.get("schema", {})
        if schema:
            return type_of(schema)
        return media_type
    return ""


def anchor(method: str, path: str) -> str:
    return f"{method.upper()} {path}"


def main() -> int:
    settings = Settings(_env_file=None, jwt_secret="apenas-para-gerar-a-documentacao", mongodb_required=False)
    schema = create_app(settings).openapi()

    api_dir = REPO_ROOT / "docs" / "api"
    api_dir.mkdir(parents=True, exist_ok=True)
    (api_dir / "openapi.json").write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    groups: dict[str, list[tuple[str, str, dict[str, Any]]]] = {tag["name"]: [] for tag in schema.get("tags", [])}
    for path, item in schema["paths"].items():
        for method in METHODS:
            if method in item:
                operation = item[method]
                groups.setdefault(operation.get("tags", ["Outros"])[0], []).append((method.upper(), path, operation))
    total = sum(len(rows) for rows in groups.values())
    descriptions = {tag["name"]: tag.get("description", "") for tag in schema.get("tags", [])}

    out: list[str] = []
    w = out.append
    w(f"# API do PlusEduc — referência (versão {schema['info']['version']})")
    w("")
    w("> Documento gerado por `PlusEduc-BE-Python/scripts/export_api_docs.py` a partir do esquema OpenAPI do backend. "
      "Não edite à mão: altere os routers, os schemas ou `app/api/openapi_docs.py` e gere de novo.")
    w("")
    w("| Onde consultar | Endereço |")
    w("|---|---|")
    w("| Swagger UI (interativo, com o servidor em execução) | `http://127.0.0.1:8080/docs` |")
    w("| ReDoc (leitura) | `http://127.0.0.1:8080/redoc` |")
    w("| Esquema OpenAPI 3.1 | `http://127.0.0.1:8080/openapi.json` e [`docs/api/openapi.json`](api/openapi.json) |")
    w("")
    w(f"São **{total} rotas** em {len([g for g in groups.values() if g])} grupos. Base: `http://127.0.0.1:8080` em desenvolvimento "
      "(o frontend chama `/api` pelo proxy do Vite).")
    w("")
    w("## Visão geral")
    w("")
    w(API_DESCRIPTION)
    w("")
    w(EXAMPLES)
    w("")
    w("## Rotas por grupo")
    w("")
    for tag, rows in groups.items():
        if not rows:
            continue
        w(f"### {tag}")
        w("")
        if descriptions.get(tag):
            w(descriptions[tag])
            w("")
        w("| Método | Rota | Acesso | O que faz |")
        w("|---|---|---|---|")
        for method, path, operation in rows:
            w(f"| `{method}` | `{path}` | {operation.get('x-acesso', '')} | {cell(operation.get('summary'))} |")
        w("")

    w("## Detalhe das rotas")
    w("")
    w("Para cada rota: parâmetros de caminho e de consulta, corpo esperado e respostas. Os nomes em link levam aos campos em [Esquemas](#esquemas).")
    w("")
    for tag, rows in groups.items():
        if not rows:
            continue
        w(f"### {tag} — detalhe")
        w("")
        for method, path, operation in rows:
            w(f"#### `{anchor(method, path)}`")
            w("")
            w(f"{operation.get('summary', '')}. **Acesso:** {operation.get('x-acesso', '')}.")
            extra = (operation.get("description") or "").split("\n\n", 1)
            if len(extra) > 1 and extra[1].strip():
                w("")
                w(extra[1].strip())
            w("")
            parameters = operation.get("parameters", [])
            if parameters:
                w("| Parâmetro | Onde | Tipo | Obrigatório | Limites |")
                w("|---|---|---|---|---|")
                for parameter in parameters:
                    where = {"path": "caminho", "query": "consulta", "header": "cabeçalho"}.get(parameter["in"], parameter["in"])
                    w(f"| `{parameter['name']}` | {where} | {type_of(parameter.get('schema', {}))} | {'sim' if parameter.get('required') else 'não'} | {cell(limits_of(parameter.get('schema', {})))} |")
                w("")
            body = body_schema(operation)
            if body:
                w(f"**Corpo (JSON):** {body}")
                w("")
            lines = []
            for code, response in operation.get("responses", {}).items():
                detail = response_schema(response)
                description = response.get("description", "")
                translated = {"Successful Response": "Sucesso", "Validation Error": "Dados inválidos (campo e motivo em `details`)"}.get(description, description)
                lines.append(f"`{code}` {translated}" + (f" — {detail}" if detail and code.startswith("2") else ""))
            w("**Respostas:** " + "; ".join(lines) + ".")
            w("")

    w("## Esquemas")
    w("")
    w("Campos dos corpos de requisição e de resposta. \"Obrigatório\" vale para requisições; nas respostas, campos nulos podem ser omitidos.")
    w("")
    for name, definition in sorted(schema.get("components", {}).get("schemas", {}).items()):
        if name in {"HTTPValidationError", "ValidationError"}:
            continue
        w(f"### {name}")
        w("")
        if definition.get("description"):
            w(definition["description"].strip().split("\n")[0])
            w("")
        if "enum" in definition:
            w("Valores: " + ", ".join(f"`{value}`" for value in definition["enum"]) + ".")
            w("")
            continue
        properties = definition.get("properties", {})
        if not properties:
            w("Objeto livre.")
            w("")
            continue
        required = set(definition.get("required", []))
        w("| Campo | Tipo | Obrigatório | Limites / observação |")
        w("|---|---|---|---|")
        for field, field_schema in properties.items():
            note = "; ".join(part for part in (limits_of(field_schema), (field_schema.get("description") or "").replace("\n", " ")) if part)
            w(f"| `{field}` | {type_of(field_schema)} | {'sim' if field in required else 'não'} | {cell(note)} |")
        w("")

    (REPO_ROOT / "docs" / "API.md").write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    print(f"docs/API.md e docs/api/openapi.json gerados: {total} rotas, {len(schema.get('components', {}).get('schemas', {}))} esquemas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
