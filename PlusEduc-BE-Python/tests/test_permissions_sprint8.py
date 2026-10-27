"""Controle de permissões (Sprint 08): matriz de rotas por perfil e regressões das lacunas encontradas.

Os testes usam repositórios em memória (sem MongoDB) para poder rodar em qualquer máquina. As
verificações de ponta a ponta contra o MongoDB real ficam nos demais arquivos *_real.py e no
script de avaliação descrito em docs/sprint-08/README.md.
"""

import re
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.jwt import create_access_token, create_refresh_token
from app.core.passwords import verify_password
from app.main import create_app
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.services.auth_service import DEMO_PASSWORD_RESET_CODE, AuthService
from tests.test_students_teachers import (
    FakeClassroomRepository,
    FakeStudentRepository,
    FakeTeacherRepository,
)

PASSWORD_HASH = bcrypt.hashpw(b"correct-password", bcrypt.gensalt()).decode()


class FakeUsers:
    """Repositório de usuários em memória com os métodos de autenticação e de recuperação de senha."""

    def __init__(self):
        self.users = {
            "teacher@example.com": {"_id": "u-teacher", "email": "teacher@example.com", "password": PASSWORD_HASH, "role": "TEACHER", "active": True},
            "admin@example.com": {"_id": "u-admin", "email": "admin@example.com", "password": PASSWORD_HASH, "role": "ADMIN", "active": True},
            "student@example.com": {"_id": "u-student", "email": "student@example.com", "password": PASSWORD_HASH, "role": "STUDENT", "active": True, "studentId": "student-1"},
        }

    def find_active_by_email(self, email):
        user = self.users.get(email)
        return user if user and user.get("active", True) else None

    def insert_student_user(self, email, password_hash, student_id):
        self.users[email] = {"_id": "u-new", "email": email, "password": password_hash, "role": "STUDENT", "studentId": student_id, "active": True}
        return "u-new"

    def set_password_reset_code(self, email, code_hash, expires_at):
        self.users[email].update(passwordResetCodeHash=code_hash, passwordResetExpiresAt=expires_at, passwordResetAttempts=0)

    def register_password_reset_attempt(self, email):
        self.users[email]["passwordResetAttempts"] = self.users[email].get("passwordResetAttempts", 0) + 1

    def update_password(self, email, password_hash):
        self.users[email]["password"] = password_hash

    def clear_password_reset_code(self, email):
        for key in ("passwordResetCodeHash", "passwordResetExpiresAt", "passwordResetAttempts"):
            self.users[email].pop(key, None)


@pytest.fixture
def users():
    return FakeUsers()


@pytest.fixture
def client(settings, users):
    app = create_app(settings, user_repository=users, student_repository=FakeStudentRepository(),
                     teacher_repository=FakeTeacherRepository(), classroom_repository=FakeClassroomRepository())
    with TestClient(app) as test_client:
        yield test_client


def bearer(settings, email):
    return {"Authorization": f"Bearer {create_access_token(email, settings)}"}


# --------------------------------------------------------------------------------------------
# Matriz de rotas: cada rota da API precisa estar classificada, e as negações precisam funcionar
# --------------------------------------------------------------------------------------------
PUBLIC = {
    ("GET", "/health"),
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/register/student"),
    ("POST", "/api/auth/register/teacher"),
    ("POST", "/api/auth/forgot-password"),
    ("POST", "/api/auth/reset-password"),
}
# Qualquer usuário autenticado; cada rota confere internamente se o registro pertence a quem pede.
OWN_RECORD = re.compile(r"^/api/students/\{student_id\}/(performance|attendance|pedagogical-recommendation)$")
ANY_AUTHENTICATED = {("PUT", "/api/auth/profile"), ("GET", "/api/activities/{activity_id}/export-pdf")}


def policy(method: str, path: str) -> str:
    if (method, path) in PUBLIC:
        return "public"
    if (method, path) in ANY_AUTHENTICATED or (method == "GET" and OWN_RECORD.match(path)):
        return "any"
    if path.startswith("/api/student-portal/"):
        return "student"
    return "staff"  # professor ou administrador


def all_routes(client):
    paths = client.get("/openapi.json").json()["paths"]
    return sorted((method.upper(), path) for path, item in paths.items() for method in item if method in {"get", "post", "put", "patch", "delete"})


def concrete(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "x", path)


def call(client, method, path, headers=None):
    kwargs = {"headers": headers or {}}
    if method in {"POST", "PUT", "PATCH"}:
        kwargs["json"] = {}
    return client.request(method, concrete(path), **kwargs)


def test_openapi_lists_every_route_and_all_are_classified(client):
    routes = all_routes(client)
    assert len(routes) > 80
    assert {policy(m, p) for m, p in routes} == {"public", "any", "student", "staff"}


def test_protected_routes_require_authentication(client):
    for method, path in all_routes(client):
        if policy(method, path) == "public":
            continue
        response = call(client, method, path)
        assert response.status_code == 401, f"{method} {path} sem token respondeu {response.status_code}"


def test_student_is_denied_on_every_staff_route(client, settings):
    headers = bearer(settings, "student@example.com")
    for method, path in all_routes(client):
        if policy(method, path) != "staff":
            continue
        response = call(client, method, path, headers)
        assert response.status_code == 403, f"{method} {path} para ALUNO respondeu {response.status_code}"


@pytest.mark.parametrize("email", ["teacher@example.com", "admin@example.com"])
def test_staff_is_denied_on_every_student_portal_route(client, settings, email):
    headers = bearer(settings, email)
    for method, path in all_routes(client):
        if policy(method, path) != "student":
            continue
        response = call(client, method, path, headers)
        assert response.status_code == 403, f"{method} {path} para {email} respondeu {response.status_code}"


@pytest.mark.parametrize("suffix", ["performance", "attendance", "pedagogical-recommendation"])
def test_student_cannot_read_another_students_analytics(client, settings, suffix):
    headers = bearer(settings, "student@example.com")
    assert client.get(f"/api/students/outro-aluno/{suffix}", headers=headers).status_code == 403


# --------------------------------------------------------------------------------------------
# Tokens: o refresh token não abre a API
# --------------------------------------------------------------------------------------------
def test_refresh_token_cannot_be_used_as_access_token(client, settings):
    refresh = {"Authorization": f"Bearer {create_refresh_token('teacher@example.com', settings)}"}
    assert client.get("/api/students", headers=refresh).status_code == 401


def test_token_without_type_claim_is_rejected(client, settings):
    now = datetime.now(timezone.utc)
    legacy = jwt.encode({"sub": "teacher@example.com", "iat": now, "exp": now + timedelta(hours=1)}, settings.jwt_secret, algorithm="HS256")
    assert client.get("/api/students", headers={"Authorization": f"Bearer {legacy}"}).status_code == 401


def test_login_issues_distinct_access_and_refresh_token_types(client, settings):
    body = client.post("/api/auth/login", json={"email": "teacher@example.com", "password": "correct-password"}).json()
    assert jwt.decode(body["accessToken"], settings.jwt_secret, algorithms=["HS256"])["type"] == "access"
    assert jwt.decode(body["refreshToken"], settings.jwt_secret, algorithms=["HS256"])["type"] == "refresh"
    assert client.get("/api/students", headers={"Authorization": f"Bearer {body['accessToken']}"}).status_code == 200


def test_role_comes_from_the_database_not_from_the_token(client, settings):
    now = datetime.now(timezone.utc)
    forged = jwt.encode({"sub": "student@example.com", "role": "ADMIN", "type": "access", "iat": now, "exp": now + timedelta(hours=1)}, settings.jwt_secret, algorithm="HS256")
    assert client.get("/api/students", headers={"Authorization": f"Bearer {forged}"}).status_code == 403


def test_token_of_a_user_deactivated_after_login_stops_working(client, settings, users):
    headers = bearer(settings, "teacher@example.com")
    assert client.get("/api/students", headers=headers).status_code == 200
    users.users["teacher@example.com"]["active"] = False
    assert client.get("/api/students", headers=headers).status_code == 401


# --------------------------------------------------------------------------------------------
# ADMIN administra alunos como administra turmas, professores e notas
# --------------------------------------------------------------------------------------------
def test_admin_can_manage_students(client, settings):
    headers = bearer(settings, "admin@example.com")
    payload = {"name": "Novo Aluno Admin", "email": "novo.admin@example.com", "birthDate": "2011-02-03", "classId": "class-1", "learningGaps": []}
    created = client.post("/api/students", headers=headers, json=payload)
    assert created.status_code == 201, created.text
    student_id = created.json()["id"]
    assert client.put(f"/api/students/{student_id}", headers=headers, json={"name": "Aluno Editado Admin"}).status_code == 200
    assert client.post(f"/api/students/{student_id}/enable-access", headers=headers, json={"password": "portal-password"}).status_code == 204
    assert client.delete(f"/api/students/{student_id}", headers=headers).status_code == 204


# --------------------------------------------------------------------------------------------
# Recuperação de senha: sem modo de demonstração, o código vai só por e-mail
# --------------------------------------------------------------------------------------------
class FakeEmail:
    def __init__(self):
        self.sent = []

    def send_password_reset_code(self, *, account_email, code):
        self.sent.append((account_email, code))


def reset_service(settings, users, demo_mode):
    email = FakeEmail()
    service = AuthService(users, settings.model_copy(update={"password_reset_demo_mode": demo_mode}), email_service=email)
    return service, email


def test_password_reset_default_is_not_demo_mode(settings):
    assert Settings(jwt_secret="x" * 32).password_reset_demo_mode is False


def test_password_reset_does_not_return_the_code_and_sends_it_by_email(settings, users):
    service, email = reset_service(settings, users, demo_mode=False)
    response = service.request_password_reset(ForgotPasswordRequest(email="student@example.com"))
    assert response.demoCode is None
    [(recipient, code)] = email.sent
    assert recipient == "student@example.com"
    assert re.fullmatch(r"\d{6}", code)
    service.reset_password(ResetPasswordRequest(email="student@example.com", code=code, newPassword="nova-senha-123"))
    assert verify_password("nova-senha-123", users.users["student@example.com"]["password"])


def test_password_reset_response_does_not_reveal_whether_the_account_exists(settings, users):
    service, email = reset_service(settings, users, demo_mode=False)
    known = service.request_password_reset(ForgotPasswordRequest(email="student@example.com"))
    unknown = service.request_password_reset(ForgotPasswordRequest(email="ninguem@example.com"))
    assert known == unknown
    assert [recipient for recipient, _ in email.sent] == ["student@example.com"]


def test_fixed_demo_code_does_not_work_when_demo_mode_is_off(settings, users):
    service, _ = reset_service(settings, users, demo_mode=False)
    service.request_password_reset(ForgotPasswordRequest(email="student@example.com"))
    from fastapi import HTTPException
    code_hash_before = users.users["student@example.com"]["passwordResetCodeHash"]
    with pytest.raises(HTTPException) as error:
        service.reset_password(ResetPasswordRequest(email="student@example.com", code=DEMO_PASSWORD_RESET_CODE, newPassword="invasor-123"))
    assert error.value.status_code == 400
    assert verify_password("correct-password", users.users["student@example.com"]["password"])
    assert users.users["student@example.com"]["passwordResetCodeHash"] == code_hash_before


def test_demo_mode_is_explicit_opt_in_for_presentations(settings, users):
    service, email = reset_service(settings, users, demo_mode=True)
    response = service.request_password_reset(ForgotPasswordRequest(email="student@example.com"))
    assert response.demoCode == DEMO_PASSWORD_RESET_CODE
    assert email.sent == []


# --------------------------------------------------------------------------------------------
# Aluno só envia respostas a atividades da própria turma
# --------------------------------------------------------------------------------------------
class FakeActivities:
    def __init__(self):
        questions = [{"questionText": "1+1?", "questionType": "MULTIPLA_ESCOLHA", "options": ["A) 1", "B) 2"], "correctAnswer": "B"}]
        self.items = [
            {"_id": "act-own", "title": "Da minha turma", "classroom_id": "class-1", "content": questions},
            {"_id": "act-other", "title": "De outra turma", "classroom_id": "class-2", "content": questions},
            {"_id": "act-private", "title": "Atribuída a outro aluno", "classroom_id": "class-1", "student_id": "student-2", "content": questions},
        ]

    def find_by_id(self, activity_id):
        return next((item for item in self.items if item["_id"] == activity_id), None)

    def find_by_student(self, student_id):
        return [item for item in self.items if item.get("student_id") == student_id]

    def find_by_classroom(self, classroom_id):
        return [item for item in self.items if item.get("classroom_id") == classroom_id]


class FakeSubmissions:
    def __init__(self):
        self.items = []

    def find_by_activity_student(self, activity_id, student_id):
        return next((item for item in self.items if item["activity_id"] == activity_id and item["student_id"] == student_id), None)

    def find_by_student(self, student_id):
        return [item for item in self.items if item["student_id"] == student_id]

    def insert(self, document):
        self.items.append(document)
        return document


@pytest.fixture
def submission_context(settings, users):
    students = FakeStudentRepository()  # "student-1" (turma class-1) é o aluno ligado ao usuário student@example.com
    activities, submissions = FakeActivities(), FakeSubmissions()
    app = create_app(settings, user_repository=users, student_repository=students, teacher_repository=FakeTeacherRepository(),
                     classroom_repository=FakeClassroomRepository(), activity_repository=activities,
                     activity_submission_repository=submissions)
    with TestClient(app) as test_client:
        yield test_client, bearer(settings, "student@example.com"), submissions


ANSWER = {"answers": [{"questionIndex": 0, "selectedAnswer": "B"}]}


def test_student_submits_to_activity_of_own_classroom(submission_context):
    client, headers, submissions = submission_context
    response = client.post("/api/student-portal/activities/act-own/submissions", headers=headers, json=ANSWER)
    assert response.status_code == 200, response.text
    assert response.json()["correctCount"] == 1
    assert [item["student_id"] for item in submissions.items] == ["student-1"]


@pytest.mark.parametrize("activity_id", ["act-other", "act-private", "nao-existe"])
def test_student_cannot_submit_to_activity_outside_own_classroom(submission_context, activity_id):
    client, headers, submissions = submission_context
    response = client.post(f"/api/student-portal/activities/{activity_id}/submissions", headers=headers, json=ANSWER)
    assert response.status_code == 404
    assert submissions.items == []


def test_student_cannot_resubmit(submission_context):
    client, headers, submissions = submission_context
    assert client.post("/api/student-portal/activities/act-own/submissions", headers=headers, json=ANSWER).status_code == 200
    assert client.post("/api/student-portal/activities/act-own/submissions", headers=headers, json=ANSWER).status_code == 409
    assert len(submissions.items) == 1
