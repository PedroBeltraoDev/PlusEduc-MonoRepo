"""Documentação da API (OpenAPI): descrição geral, grupos, resumo e perfil de acesso de cada rota.

O FastAPI gera o esquema a partir dos routers; este módulo completa o que os routers não dizem (resumo em
português, quem pode chamar, grupos com descrição) num lugar só. O mesmo esquema alimenta o Swagger (/docs),
o ReDoc (/redoc) e o documento ``docs/API.md`` (``scripts/export_api_docs.py``).
"""

from __future__ import annotations

import re
from typing import Any

from fastapi import FastAPI

API_DESCRIPTION = """
API REST do **PlusEduc**, plataforma de gestão pedagógica da educação básica: turmas, alunos, professores,
atividades, notas, frequência, relatórios e portal do aluno.

### Autenticação

1. `POST /api/auth/login` com e-mail e senha devolve `accessToken` (8 h) e `refreshToken` (7 dias).
2. Envie o token de acesso em todas as rotas protegidas: `Authorization: Bearer <accessToken>`.
3. Quando o token de acesso vencer, troque o refresh token por um novo par em `POST /api/auth/refresh`.

No Swagger, clique em **Authorize** e cole o `accessToken`.

### Perfis

| Perfil | O que acessa |
|---|---|
| `TEACHER` | gestão de turmas, alunos, atividades, notas, relatórios e o próprio histórico |
| `ADMIN` | o mesmo que o professor, mais a aprovação de cadastros de professor e o histórico de todos |
| `STUDENT` | apenas `/api/student-portal/**` e os próprios dados de desempenho |

Cada rota informa o perfil exigido no campo **Acesso**. Sem token a resposta é `401`; com perfil errado, `403`.

### Erros

Todo erro tem o mesmo formato JSON:

```json
{"timestamp": "2026-11-11T18:00:00Z", "status": 400, "error": "Bad Request", "message": "Senha atual incorreta"}
```

Erros de validação (`422`) trazem também `details`, com o campo (`loc`) e o motivo (`msg`) de cada problema.
Datas usam ISO 8601; identificadores são os `_id` do MongoDB em texto (24 caracteres hexadecimais).
""".strip()

# nome usado nos routers -> (nome exibido, descrição)
TAGS: dict[str, tuple[str, str]] = {
    "Infrastructure": ("Infraestrutura", "Verificação de disponibilidade da aplicação e do banco."),
    "Autenticação": ("Autenticação", "Login, renovação de sessão, cadastro público, perfil e senha."),
    "Students": ("Alunos", "Cadastro de alunos, matrícula, lacunas de aprendizagem e acesso ao portal."),
    "Student Analytics": ("Desempenho do aluno", "Desempenho, frequência e recomendação pedagógica de um aluno."),
    "Professores": ("Professores", "Cadastro de professores e aprovação dos cadastros públicos."),
    "Classrooms": ("Turmas", "Turmas, matrícula de alunos e desempenho por turma."),
    "Grades": ("Notas e frequência", "Lançamento e consulta de notas e presença; resumo por turma."),
    "Activities": ("Atividades", "Atividades objetivas e discursivas, geração assistida e exportação em PDF."),
    "Subjects": ("Matérias", "Catálogo de componentes curriculares (BNCC) e atribuição de professor por turma."),
    "Subject Topics": ("Tópicos das matérias", "Tópicos de conteúdo usados na criação de atividades."),
    "Student Portal": ("Portal do aluno", "Dados que o aluno vê sobre si: turma, professores, atividades, notas e desempenho."),
    "Activity Submissions": ("Portal do aluno — respostas", "Envio e consulta das respostas do aluno a uma atividade."),
    "Teacher Activity Corrections": ("Correção de atividades", "Correção manual das questões discursivas pelo professor."),
    "Teacher Activity Corrections (legacy)": (
        "Correção de atividades (rota antiga)",
        "Mesmo comportamento de **Correção de atividades**, no endereço antigo com sublinhado. Mantida por compatibilidade.",
    ),
    "Reports": ("Relatórios", "Relatórios com filtros e exportação em CSV, Excel e PDF."),
    "Dashboard": ("Dashboard", "Indicadores e séries dos gráficos do painel inicial."),
    "Search": ("Pesquisa", "Pesquisa global em alunos, turmas e atividades."),
    "Audit": ("Histórico de operações", "Registro das operações que alteram dados (quem, quando, o quê e o resultado)."),
}

# (método, caminho) -> resumo, para as rotas cujo router não define um
SUMMARIES: dict[tuple[str, str], str] = {
    ("GET", "/api/students"): "Listar alunos ativos",
    ("POST", "/api/students"): "Cadastrar aluno",
    ("GET", "/api/students/unassigned"): "Listar alunos sem turma",
    ("GET", "/api/students/paginated"): "Listar alunos com paginação",
    ("GET", "/api/students/class/{class_id}"): "Listar alunos de uma turma",
    ("GET", "/api/students/learning-gap/{subject}"): "Listar alunos com lacuna de aprendizagem em uma matéria",
    ("GET", "/api/students/{student_id}"): "Consultar aluno",
    ("PUT", "/api/students/{student_id}"): "Editar aluno",
    ("DELETE", "/api/students/{student_id}"): "Excluir aluno (exclusão lógica; o login deixa de valer)",
    ("POST", "/api/students/{student_id}/enable-access"): "Criar o login do portal para um aluno já cadastrado",
    ("GET", "/api/students/{student_id}/performance"): "Desempenho do aluno por disciplina",
    ("GET", "/api/students/{student_id}/attendance"): "Frequência do aluno",
    ("GET", "/api/students/{student_id}/pedagogical-recommendation"): "Recomendação pedagógica priorizada, com as evidências",
    ("GET", "/api/teachers"): "Listar professores ativos",
    ("POST", "/api/teachers"): "Cadastrar professor (já ativo, com login)",
    ("GET", "/api/teachers/email/{email}"): "Consultar professor pelo e-mail",
    ("GET", "/api/teachers/subject/{subject}"): "Listar professores de uma matéria",
    ("GET", "/api/teachers/count"): "Quantidade de professores cadastrados",
    ("GET", "/api/teachers/{teacher_id}"): "Consultar professor",
    ("PUT", "/api/teachers/{teacher_id}"): "Editar professor",
    ("DELETE", "/api/teachers/{teacher_id}"): "Excluir professor (exclusão lógica; o login deixa de valer)",
    ("GET", "/api/classrooms"): "Listar turmas ativas",
    ("POST", "/api/classrooms"): "Criar turma",
    ("GET", "/api/classrooms/paginated"): "Listar turmas com paginação",
    ("GET", "/api/classrooms/teacher/{teacher_id}"): "Listar turmas de um professor",
    ("GET", "/api/classrooms/student/{student_id}"): "Listar turmas de um aluno",
    ("GET", "/api/classrooms/year/{year}"): "Listar turmas de um ano letivo",
    ("GET", "/api/classrooms/{classroom_id}/performance"): "Desempenho dos alunos da turma",
    ("GET", "/api/classrooms/{classroom_id}"): "Consultar turma",
    ("PUT", "/api/classrooms/{classroom_id}"): "Editar turma",
    ("DELETE", "/api/classrooms/{classroom_id}"): "Excluir turma (só sem alunos matriculados)",
    ("POST", "/api/classrooms/{classroom_id}/enroll/{student_id}"): "Matricular aluno na turma (sai da turma anterior)",
    ("DELETE", "/api/classrooms/{classroom_id}/unenroll/{student_id}"): "Remover aluno da turma",
    ("GET", "/api/grades"): "Listar notas",
    ("POST", "/api/grades"): "Lançar nota e presença",
    ("GET", "/api/grades/student/{student_id}/average"): "Média geral de um aluno",
    ("GET", "/api/grades/student/{student_id}"): "Listar notas de um aluno",
    ("GET", "/api/grades/classroom/{classroom_id}"): "Listar notas de uma turma",
    ("GET", "/api/grades/classroom/{classroom_id}/summary"): "Boletim da turma: média e frequência por aluno",
    ("POST", "/api/grades/from-activity/{activity_id}"): "Lançar no boletim as notas de uma atividade respondida",
    ("GET", "/api/grades/{grade_id}"): "Consultar nota",
    ("PUT", "/api/grades/{grade_id}"): "Editar nota",
    ("DELETE", "/api/grades/{grade_id}"): "Excluir nota",
    ("GET", "/api/activities"): "Listar atividades",
    ("POST", "/api/activities"): "Criar atividade",
    ("POST", "/api/activities/generate"): "Gerar atividade a partir de um tópico (IA, com alternativa determinística)",
    ("GET", "/api/activities/classroom/{classroom_id}"): "Listar atividades de uma turma",
    ("GET", "/api/activities/student/{student_id}"): "Listar atividades atribuídas a um aluno",
    ("GET", "/api/activities/teacher/{teacher_id}"): "Listar atividades criadas por um professor",
    ("GET", "/api/activities/{activity_id}/submissions"): "Participação e respostas da turma em uma atividade",
    ("GET", "/api/activities/{activity_id}/export-pdf"): "Exportar atividade em PDF (gabarito só para professor)",
    ("GET", "/api/activities/{activity_id}"): "Consultar atividade (com gabarito)",
    ("PUT", "/api/activities/{activity_id}"): "Editar atividade",
    ("DELETE", "/api/activities/{activity_id}"): "Excluir atividade e as respostas dela",
    ("GET", "/api/student-portal/me"): "Perfil do aluno autenticado",
    ("GET", "/api/student-portal/classroom"): "Turma do aluno",
    ("GET", "/api/student-portal/classmates"): "Colegas de turma (somente nome)",
    ("GET", "/api/student-portal/teachers"): "Professores da turma do aluno",
    ("GET", "/api/student-portal/activities"): "Atividades da turma do aluno ou atribuídas a ele",
    ("GET", "/api/student-portal/activities/{activity_id}"): "Atividade para responder (sem gabarito)",
    ("GET", "/api/student-portal/activities/{activity_id}/export-pdf"): "Exportar a atividade em PDF (sem gabarito)",
    ("GET", "/api/student-portal/grades"): "Notas do aluno",
    ("GET", "/api/student-portal/performance"): "Desempenho do aluno por disciplina",
    ("POST", "/api/student-portal/activities/{activity_id}/submissions"): "Enviar respostas (objetivas são corrigidas na hora)",
    ("GET", "/api/student-portal/activities/{activity_id}/submissions"): "Consultar as próprias respostas e a correção",
    ("GET", "/api/subject-topics"): "Listar tópicos",
    ("POST", "/api/subject-topics"): "Criar tópico",
    ("PUT", "/api/subject-topics/{item_id}"): "Editar tópico",
    ("DELETE", "/api/subject-topics/{item_id}"): "Excluir tópico",
    ("GET", "/api/subjects"): "Listar matérias do catálogo",
    ("POST", "/api/subjects"): "Criar matéria",
    ("GET", "/api/subjects/available"): "Matérias compatíveis com a série de uma turma",
    ("POST", "/api/subjects/assignments"): "Assumir uma matéria em uma turma (um professor por matéria)",
    ("PATCH", "/api/subjects/{subject_id}"): "Editar ou desativar matéria",
    ("DELETE", "/api/subjects/{subject_id}"): "Desativar matéria",
    ("GET", "/api/subjects/{subject_id}/classrooms"): "Turmas do professor que têm a matéria",
    ("GET", "/api/subjects/{subject_id}/classrooms/{classroom_id}/performance"): "Desempenho dos alunos na matéria",
    ("GET", "/api/teacher/activity-corrections/pending"): "Listar respostas discursivas aguardando correção",
    ("PUT", "/api/teacher/activity-corrections/{submission_id}/questions/{question_index}"): "Corrigir uma questão discursiva (nota e comentário)",
    ("GET", "/api/teacher/activity_corrections/pending"): "Listar respostas discursivas aguardando correção (rota antiga)",
    ("PUT", "/api/teacher/activity_corrections/{submission_id}/questions/{question_index}"): "Corrigir uma questão discursiva (rota antiga)",
}

PUBLIC = {
    ("GET", "/health"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/refresh"),
    ("POST", "/api/auth/register/student"),
    ("POST", "/api/auth/register/teacher"),
    ("POST", "/api/auth/forgot-password"),
    ("POST", "/api/auth/reset-password"),
}
ANY_AUTHENTICATED = {
    ("PUT", "/api/auth/profile"),
    ("POST", "/api/auth/change-password"),
    ("GET", "/api/activities/{activity_id}/export-pdf"),
}
ADMIN_ONLY = {
    ("GET", "/api/teachers/pending"),
    ("POST", "/api/teachers/{teacher_id}/approve"),
    ("POST", "/api/teachers/{teacher_id}/reject"),
}
_OWN_RECORD = re.compile(r"^/api/students/\{student_id\}/(performance|attendance|pedagogical-recommendation)$")


def access_of(method: str, path: str) -> str:
    """Quem pode chamar a rota (a mesma classificação conferida por tests/test_permissions_sprint8.py)."""
    key = (method.upper(), path)
    if key in PUBLIC:
        return "público"
    if key in ADMIN_ONLY:
        return "ADMIN"
    if key in ANY_AUTHENTICATED:
        return "qualquer usuário autenticado"
    if key[0] == "GET" and _OWN_RECORD.match(path):
        return "TEACHER ou ADMIN; STUDENT apenas para o próprio registro"
    if path.startswith("/api/student-portal/"):
        return "STUDENT"
    return "TEACHER ou ADMIN"


def _customize(schema: dict[str, Any]) -> dict[str, Any]:
    used: list[str] = []
    for path, item in schema.get("paths", {}).items():
        for method, operation in item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            key = (method.upper(), path)
            if key in SUMMARIES:
                operation["summary"] = SUMMARIES[key]
            access = access_of(method, path)
            operation["x-acesso"] = access
            note = f"**Acesso:** {access}."
            description = operation.get("description")
            operation["description"] = f"{note}\n\n{description}" if description else note
            if access == "público":
                operation["security"] = []
            else:
                responses = operation.setdefault("responses", {})
                responses.setdefault("401", {"description": "Token ausente, inválido ou expirado"})
                if access != "qualquer usuário autenticado":
                    responses.setdefault("403", {"description": "Perfil sem permissão para esta rota"})
            tags = [TAGS.get(tag, (tag, ""))[0] for tag in operation.get("tags", [])]
            operation["tags"] = tags
            for tag in tags:
                if tag not in used:
                    used.append(tag)
    descriptions = {name: description for name, description in TAGS.values()}
    schema["tags"] = [{"name": tag, "description": descriptions.get(tag, "")} for tag in used]
    return schema


def install(application: FastAPI) -> None:
    """Faz o ``/openapi.json`` (e, por consequência, /docs e /redoc) sair com a documentação completa."""
    original = application.openapi

    def openapi() -> dict[str, Any]:
        if application.openapi_schema is None:
            application.openapi_schema = _customize(original())
        return application.openapi_schema

    application.openapi = openapi  # type: ignore[method-assign]
