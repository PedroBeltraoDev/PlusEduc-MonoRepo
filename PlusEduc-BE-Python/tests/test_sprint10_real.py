"""Sprint 10 (release candidate): pendências de autenticação fechadas, verificadas contra o MongoDB real.

* RF01 — renovação da sessão com o refresh token (``POST /api/auth/refresh``);
* RF03 — troca de senha pelo próprio usuário autenticado (``POST /api/auth/change-password``);
* RF04 — cadastro público de professor fica pendente até um ADMIN aprovar
  (``GET /api/teachers/pending``, ``POST /api/teachers/{id}/approve`` e ``/reject``).

Os registros criados aqui usam e-mails aleatórios e são apagados no final de cada teste.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import get_settings
from app.core.jwt import create_access_token
from app.core.passwords import hash_password, verify_password
from app.main import create_app
from tests.database import TEST_DATABASE

PASSWORD = "Senha@123"


def _settings(**overrides):
    return get_settings().model_copy(update={"mongodb_database": TEST_DATABASE, **overrides})


@pytest.fixture
def db():
    mongo = MongoClient("mongodb://localhost:27017")
    database = mongo[TEST_DATABASE]
    created: list[str] = []
    yield database, created
    for email in created:
        database.users.delete_many({"email": email})
        database.teachers.delete_many({"email": email})
        database.audit_logs.delete_many({"actorEmail": email})
    mongo.close()


@pytest.fixture
def client():
    with TestClient(create_app(_settings())) as test_client:
        yield test_client


def _email(prefix: str, created: list[str]) -> str:
    email = f"{prefix}.{uuid4().hex[:10]}@sprint10.local"
    created.append(email)
    return email


def _make_user(database, email: str, role: str, **extra) -> None:
    database.users.insert_one(
        {
            "email": email,
            "password": hash_password(PASSWORD),
            "role": role,
            "active": True,
            "createdAt": datetime.now(timezone.utc),
            **extra,
        }
    )


def _bearer(email: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(email, _settings())}"}


# ------------------------------------------------------------------ RF01: refresh token
def test_refresh_token_renews_the_session(client, db):
    database, created = db
    email = _email("admin.refresh", created)
    _make_user(database, email, "ADMIN", name="Admin Refresh")

    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()
    renewed = client.post("/api/auth/refresh", json={"refreshToken": login["refreshToken"]})
    assert renewed.status_code == 200, renewed.text
    body = renewed.json()
    assert body["userEmail"] == email and body["role"] == "ADMIN"
    assert body["accessToken"] and body["refreshToken"]
    assert client.get("/api/teachers", headers={"Authorization": f"Bearer {body['accessToken']}"}).status_code == 200


def test_refresh_rejects_access_token_and_garbage(client, db):
    database, created = db
    email = _email("admin.refresh.bad", created)
    _make_user(database, email, "ADMIN")
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()

    assert client.post("/api/auth/refresh", json={"refreshToken": login["accessToken"]}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refreshToken": "nao-e-um-token"}).status_code == 401
    assert client.post("/api/auth/refresh", json={}).status_code == 422


def test_refresh_stops_working_after_the_account_is_deactivated(client, db):
    database, created = db
    email = _email("admin.refresh.off", created)
    _make_user(database, email, "ADMIN")
    login = client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).json()

    database.users.update_one({"email": email}, {"$set": {"active": False}})
    assert client.post("/api/auth/refresh", json={"refreshToken": login["refreshToken"]}).status_code == 401


# ------------------------------------------------------------------ RF03: troca de senha logado
def test_user_changes_own_password(client, db):
    database, created = db
    email = _email("prof.senha", created)
    _make_user(database, email, "TEACHER")
    database.teachers.insert_one(
        {"name": "Prof Senha", "email": email, "password": hash_password(PASSWORD), "active": True, "subjects": []}
    )
    headers = _bearer(email)

    wrong = client.post("/api/auth/change-password", json={"currentPassword": "errada", "newPassword": "Nova@123"}, headers=headers)
    assert wrong.status_code == 400 and wrong.json()["message"] == "Senha atual incorreta"

    same = client.post("/api/auth/change-password", json={"currentPassword": PASSWORD, "newPassword": PASSWORD}, headers=headers)
    assert same.status_code == 400

    short = client.post("/api/auth/change-password", json={"currentPassword": PASSWORD, "newPassword": "123"}, headers=headers)
    assert short.status_code == 422

    ok = client.post("/api/auth/change-password", json={"currentPassword": PASSWORD, "newPassword": "Nova@123"}, headers=headers)
    assert ok.status_code == 200, ok.text

    assert client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 401
    assert client.post("/api/auth/login", json={"email": email, "password": "Nova@123"}).status_code == 200
    # a cópia do hash no cadastro do professor acompanha a troca
    assert verify_password("Nova@123", database.teachers.find_one({"email": email})["password"])


def test_change_password_requires_authentication(client):
    response = client.post("/api/auth/change-password", json={"currentPassword": "x", "newPassword": "Nova@123"})
    assert response.status_code == 401


# ------------------------------------------------------------------ RF04: aprovação do professor
def test_public_teacher_registration_waits_for_admin_approval(client, db):
    database, created = db
    admin = _email("admin.aprova", created)
    _make_user(database, admin, "ADMIN")
    teacher_email = _email("prof.pendente", created)
    other_teacher = _email("prof.ativo", created)
    _make_user(database, other_teacher, "TEACHER")

    registration = client.post(
        "/api/auth/register/teacher",
        json={"name": "Professora Pendente", "email": teacher_email, "password": PASSWORD},
    )
    assert registration.status_code == 202, registration.text
    body = registration.json()
    assert body["status"] == "PENDING_APPROVAL"
    assert "accessToken" not in body

    # senha certa: avisa que está pendente; senha errada: resposta genérica (não revela o cadastro)
    pending_login = client.post("/api/auth/login", json={"email": teacher_email, "password": PASSWORD})
    assert pending_login.status_code == 403
    assert "aprovação" in pending_login.json()["message"]
    assert client.post("/api/auth/login", json={"email": teacher_email, "password": "errada"}).status_code == 401

    # fora das listas de professores enquanto pendente
    listed = client.get("/api/teachers", headers=_bearer(admin)).json()
    assert teacher_email not in {item["email"] for item in listed}

    # só o ADMIN vê e decide os pendentes
    assert client.get("/api/teachers/pending", headers=_bearer(other_teacher)).status_code == 403
    pending = client.get("/api/teachers/pending", headers=_bearer(admin))
    assert pending.status_code == 200
    match = [item for item in pending.json() if item["email"] == teacher_email]
    assert len(match) == 1
    teacher_id = match[0]["id"]
    assert client.post(f"/api/teachers/{teacher_id}/approve", headers=_bearer(other_teacher)).status_code == 403

    approved = client.post(f"/api/teachers/{teacher_id}/approve", headers=_bearer(admin))
    assert approved.status_code == 200, approved.text
    assert approved.json()["active"] is True

    login = client.post("/api/auth/login", json={"email": teacher_email, "password": PASSWORD})
    assert login.status_code == 200, login.text
    assert login.json()["role"] == "TEACHER" and login.json()["name"] == "Professora Pendente"
    teacher = database.teachers.find_one({"email": teacher_email})
    assert teacher["approval_status"] == "APPROVED" and teacher["approved_by"] == admin
    # aprovado não volta a aparecer como pendente nem pode ser aprovado de novo
    assert client.post(f"/api/teachers/{teacher_id}/approve", headers=_bearer(admin)).status_code == 404


def test_admin_rejects_registration_and_email_becomes_available(client, db):
    database, created = db
    admin = _email("admin.recusa", created)
    _make_user(database, admin, "ADMIN")
    teacher_email = _email("prof.recusado", created)

    client.post("/api/auth/register/teacher", json={"name": "Cadastro Recusado", "email": teacher_email, "password": PASSWORD})
    teacher_id = str(database.teachers.find_one({"email": teacher_email})["_id"])

    rejected = client.post(f"/api/teachers/{teacher_id}/reject", headers=_bearer(admin))
    assert rejected.status_code == 204
    assert database.teachers.find_one({"email": teacher_email}) is None
    assert database.users.find_one({"email": teacher_email}) is None
    assert client.post("/api/auth/login", json={"email": teacher_email, "password": PASSWORD}).status_code == 401

    again = client.post("/api/auth/register/teacher", json={"name": "Cadastro Novo", "email": teacher_email, "password": PASSWORD})
    assert again.status_code == 202


def test_registration_without_approval_keeps_immediate_access(db):
    database, created = db
    email = _email("prof.imediato", created)
    with TestClient(create_app(_settings(teacher_registration_requires_approval=False))) as client:
        response = client.post("/api/auth/register/teacher", json={"name": "Acesso Imediato", "email": email, "password": PASSWORD})
        assert response.status_code == 200, response.text
        assert response.json()["accessToken"]
        assert client.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200


# ------------------------------------------------------------------ turma exige professor ativo
def test_classroom_requires_an_active_teacher(client, db):
    database, created = db
    admin = _email("admin.turma", created)
    _make_user(database, admin, "ADMIN")
    inactive_email = _email("prof.inativo", created)
    active_email = _email("prof.ativo.turma", created)
    inactive_id = str(database.teachers.insert_one({"name": "Prof Inativo", "email": inactive_email, "active": False, "subjects": []}).inserted_id)
    active_id = str(database.teachers.insert_one({"name": "Prof Ativo", "email": active_email, "active": True, "subjects": []}).inserted_id)
    name = f"Turma Professor Inativo {uuid4().hex[:6]}"
    body = {"name": name, "year": 2026, "gradeLevel": "6º Ano do Ensino Fundamental", "studentIds": []}
    try:
        refused = client.post("/api/classrooms", headers=_bearer(admin), json={**body, "teacherId": inactive_id})
        assert refused.status_code == 400 and "inativo" in refused.json()["message"]

        created_classroom = client.post("/api/classrooms", headers=_bearer(admin), json={**body, "teacherId": active_id})
        assert created_classroom.status_code == 201, created_classroom.text
        classroom_id = created_classroom.json()["id"]

        moved = client.put(f"/api/classrooms/{classroom_id}", headers=_bearer(admin), json={"teacherId": inactive_id})
        assert moved.status_code == 400
        missing = client.put(f"/api/classrooms/{classroom_id}", headers=_bearer(admin), json={"teacherId": "000000000000000000000000"})
        assert missing.status_code == 400
        # sem trocar o professor, a edição continua funcionando
        assert client.put(f"/api/classrooms/{classroom_id}", headers=_bearer(admin), json={"teacherId": active_id, "year": 2026}).status_code == 200
    finally:
        database.classrooms.delete_many({"name": name})


# ------------------------------------------------------------------ matrícula nos dois lados ao criar aluno
def test_student_created_with_classroom_is_listed_in_the_classroom(client, db):
    database, created = db
    admin = _email("admin.matricula", created)
    _make_user(database, admin, "ADMIN")
    classroom = database.classrooms.find_one({"active": True})
    classroom_id = str(classroom["_id"])
    email = _email("aluno.matricula", created)
    student_id = None
    try:
        response = client.post(
            "/api/students",
            headers=_bearer(admin),
            json={"name": "Aluno Matricula Sprint Dez", "email": email, "birthDate": "2012-03-04", "classId": classroom_id, "learningGaps": []},
        )
        assert response.status_code == 201, response.text
        student_id = response.json()["id"]
        assert student_id in [str(value) for value in database.classrooms.find_one({"_id": classroom["_id"]})["students"]]
        assert database.students.find_one({"email": email})["class_id"] == classroom_id
    finally:
        database.students.delete_many({"email": email})
        if student_id:
            database.classrooms.update_one({"_id": classroom["_id"]}, {"$pull": {"students": student_id}})
