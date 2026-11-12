"""Regressões da revisão geral de segurança e integridade (MongoDB real, dados descartáveis).

Cada teste cria os próprios professores, turmas e alunos e remove tudo ao final.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import Settings
from app.core.passwords import hash_password, verify_password
from app.main import create_app
from tests.database import TEST_DATABASE
from tests.teacher_fixture import temporary_teacher

PASSWORD = "Teste@12345"


def make_settings(**extra) -> Settings:
    values = dict(
        app_env="test-security",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database=TEST_DATABASE,
        mongodb_required=True,
        jwt_secret="test-security-secret-with-enough-length-0123456789",
        jwt_expiration_ms=600_000,
        password_reset_demo_mode=True,
    )
    values.update(extra)
    return Settings(**values)


@pytest.fixture
def db():
    mongo = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)
    mongo.admin.command("ping")
    yield mongo[TEST_DATABASE]
    mongo.close()


@pytest.fixture
def client():
    with TestClient(create_app(make_settings())) as test_client:
        yield test_client


@pytest.fixture
def admin(db):
    email = f"admin.sec.{uuid4().hex[:8]}@pluseduc.local"
    db.users.insert_one({"email": email, "password": hash_password(PASSWORD), "role": "ADMIN", "active": True})
    yield email
    db.users.delete_many({"email": email})
    db.refresh_tokens.delete_many({"email": email})


def login(client, email, password=PASSWORD):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


def bearer(body):
    return {"Authorization": f"Bearer {body['accessToken']}"}


@pytest.fixture
def student_factory(db):
    created: list[ObjectId] = []

    def make(classroom_id: str | None, with_account: bool = False) -> dict:
        token = uuid4().hex[:8]
        email = f"aluno.sec.{token}@aluno.local"
        doc = {"name": f"Aluno Seg {token}", "email": email, "matricula": f"SEC-{token}", "active": True,
               "learning_gaps": [], "class_id": classroom_id, "created_at": datetime.now(timezone.utc)}
        student_id = db.students.insert_one(doc).inserted_id
        created.append(student_id)
        if classroom_id:
            db.classrooms.update_one({"_id": ObjectId(classroom_id)}, {"$addToSet": {"students": str(student_id)}})
        if with_account:
            db.users.insert_one({"email": email, "password": hash_password(PASSWORD), "role": "STUDENT",
                                 "studentId": str(student_id), "active": True})
        return {"id": str(student_id), "email": email}

    yield make
    for student_id in created:
        student = db.students.find_one({"_id": student_id})
        if student:
            db.users.delete_many({"email": student.get("email")})
        db.students.delete_one({"_id": student_id})
        db.grades.delete_many({"studentId": str(student_id)})


# ------------------------------------------------------------------ 1.1 permissões por professor
def test_teacher_only_sees_own_classrooms_students_and_grades(client, db, student_factory):
    with temporary_teacher(db, with_classroom=True) as a, temporary_teacher(db, with_classroom=True) as b:
        own = student_factory(a["classroom_id"])
        other = student_factory(b["classroom_id"])
        headers = bearer(login(client, a["email"]))

        assert {c["id"] for c in client.get("/api/classrooms", headers=headers).json()} == {a["classroom_id"]}
        assert client.get(f"/api/classrooms/{a['classroom_id']}", headers=headers).status_code == 200
        assert client.get(f"/api/classrooms/{b['classroom_id']}", headers=headers).status_code == 403
        assert client.get(f"/api/classrooms/{b['classroom_id']}/performance", headers=headers).status_code == 403

        listed = {s["id"] for s in client.get("/api/students", headers=headers).json()}
        assert own["id"] in listed and other["id"] not in listed
        assert client.get(f"/api/students/{other['id']}", headers=headers).status_code == 403
        assert client.put(f"/api/students/{other['id']}", headers=headers, json={"name": "Invasão"}).status_code == 403
        assert client.delete(f"/api/students/{other['id']}", headers=headers).status_code == 403
        assert client.get(f"/api/students/{other['id']}/performance", headers=headers).status_code == 403

        grade = {"studentId": other["id"], "classroomId": b["classroom_id"], "grade": 7, "attendance": True,
                 "subject": "Matemática", "activityType": "EXAM", "date": "2026-06-01T12:00:00Z"}
        assert client.post("/api/grades", headers=headers, json=grade).status_code == 403
        assert client.get(f"/api/grades/classroom/{b['classroom_id']}", headers=headers).status_code == 403

        own_grade = {**grade, "studentId": own["id"], "classroomId": a["classroom_id"]}
        created = client.post("/api/grades", headers=headers, json=own_grade)
        assert created.status_code == 201, created.text

        # Pesquisa global e dashboard não vazam dados de outra turma.
        name_other = db.students.find_one({"_id": ObjectId(other["id"])})["name"]
        hits = client.get("/api/search", headers=headers, params={"q": name_other}).json()["results"]
        assert all(hit["id"] != other["id"] for hit in hits)
        dashboard = client.get("/api/dashboard/overview", headers=headers)
        assert dashboard.status_code == 200
        assert client.get("/api/dashboard/overview", headers=headers, params={"classroomId": b["classroom_id"]}).status_code == 404


def test_teacher_cannot_move_student_from_another_teachers_classroom(client, db, student_factory):
    with temporary_teacher(db, with_classroom=True) as a, temporary_teacher(db, with_classroom=True) as b:
        other = student_factory(b["classroom_id"])
        headers = bearer(login(client, a["email"]))
        assert client.post(f"/api/classrooms/{a['classroom_id']}/enroll/{other['id']}", headers=headers).status_code == 403
        assert db.students.find_one({"_id": ObjectId(other["id"])})["class_id"] == b["classroom_id"]


def test_teacher_cannot_create_classroom_for_another_teacher(client, db):
    with temporary_teacher(db) as a, temporary_teacher(db) as b:
        headers = bearer(login(client, a["email"]))
        body = {"name": f"Turma {uuid4().hex[:6]}", "year": datetime.now().year, "gradeLevel": "7º Ano do Ensino Fundamental", "teacherId": b["teacher_id"]}
        created = client.post("/api/classrooms", headers=headers, json=body)
        try:
            assert created.status_code == 201, created.text
            assert created.json()["teacherId"] == a["teacher_id"]  # forçado para o próprio professor
        finally:
            if created.status_code == 201:
                db.classrooms.delete_one({"_id": ObjectId(created.json()["id"])})


def test_activity_pdf_export_requires_classroom_access(client, db):
    with temporary_teacher(db, with_classroom=True) as a, temporary_teacher(db, with_classroom=True) as b:
        activity_id = db.activities.insert_one({"title": "Prova B", "subject": "Matemática", "classroom_id": b["classroom_id"],
                                                "content": "[]", "created_by": b["email"], "created_at": datetime.now(timezone.utc)}).inserted_id
        try:
            headers_a = bearer(login(client, a["email"]))
            headers_b = bearer(login(client, b["email"]))
            assert client.get(f"/api/activities/{activity_id}/export-pdf", headers=headers_a).status_code == 403
            assert client.get(f"/api/activities/{activity_id}", headers=headers_a).status_code == 403
            assert client.get(f"/api/activities/{activity_id}/export-pdf", headers=headers_b).status_code == 200
        finally:
            db.activities.delete_one({"_id": activity_id})


def test_teacher_without_active_profile_gets_no_access(client, db):
    email = f"sem.cadastro.{uuid4().hex[:8]}@professor.local"
    db.users.insert_one({"email": email, "password": hash_password(PASSWORD), "role": "TEACHER", "active": True})
    try:
        headers = bearer(login(client, email))
        for path in ("/api/classrooms", "/api/students", "/api/activities", "/api/dashboard/overview"):
            assert client.get(path, headers=headers).status_code == 403, path
    finally:
        db.users.delete_many({"email": email})
        db.refresh_tokens.delete_many({"email": email})


def test_teacher_management_is_admin_only(client, db, admin):
    with temporary_teacher(db) as a:
        teacher_headers = bearer(login(client, a["email"]))
        body = {"name": "Professor Novo", "email": f"novo.{uuid4().hex[:6]}@professor.local", "password": "Senha@123"}
        assert client.post("/api/teachers", headers=teacher_headers, json=body).status_code == 403
        assert client.put(f"/api/teachers/{a['teacher_id']}", headers=teacher_headers, json={"name": "x"}).status_code == 403
        assert client.delete(f"/api/teachers/{a['teacher_id']}", headers=teacher_headers).status_code == 403


# ------------------------------------------------------------------ 1.2 senhas de professores
def test_admin_teacher_crud_hashes_password_and_syncs_account(client, db, admin):
    headers = bearer(login(client, admin))
    email = f"crud.{uuid4().hex[:8]}@professor.local"
    created = client.post("/api/teachers", headers=headers, json={"name": "Professor CRUD", "email": email, "password": "Senha@123"})
    try:
        assert created.status_code == 201, created.text
        teacher_id = created.json()["id"]
        teacher = db.teachers.find_one({"email": email})
        user = db.users.find_one({"email": email})
        assert "password" not in teacher  # nunca mais em teachers
        assert user["role"] == "TEACHER" and verify_password("Senha@123", user["password"])
        assert user["password"] != "Senha@123"

        session = login(client, email, "Senha@123")
        assert client.put(f"/api/teachers/{teacher_id}", headers=headers, json={"password": "Outra@456"}).status_code == 200
        assert "password" not in db.teachers.find_one({"email": email})
        assert verify_password("Outra@456", db.users.find_one({"email": email})["password"])
        assert client.get("/api/classrooms", headers=bearer(session)).status_code == 401  # sessão antiga revogada

        assert client.delete(f"/api/teachers/{teacher_id}", headers=headers).status_code == 204
        assert db.users.find_one({"email": email})["active"] is False
        assert client.post("/api/auth/login", json={"email": email, "password": "Outra@456"}).status_code == 401
    finally:
        db.teachers.delete_many({"email": email})
        db.users.delete_many({"email": email})
        db.refresh_tokens.delete_many({"email": email})


# ------------------------------------------------------------------ 1.3 sessões e tokens
def test_refresh_rotates_and_reuse_revokes_the_whole_session(client, db):
    with temporary_teacher(db) as a:
        first = login(client, a["email"])
        second = client.post("/api/auth/refresh", json={"refreshToken": first["refreshToken"]})
        assert second.status_code == 200, second.text
        assert second.json()["refreshToken"] != first["refreshToken"]
        assert client.get("/api/students", headers=bearer(second.json())).status_code == 200

        reuse = client.post("/api/auth/refresh", json={"refreshToken": first["refreshToken"]})
        assert reuse.status_code == 401  # token já usado: possível roubo
        # A família inteira foi revogada: o token mais novo também deixa de renovar.
        assert client.post("/api/auth/refresh", json={"refreshToken": second.json()["refreshToken"]}).status_code == 401


def test_logout_revokes_refresh_token(client, db):
    with temporary_teacher(db) as a:
        session = login(client, a["email"])
        assert client.post("/api/auth/logout", json={"refreshToken": session["refreshToken"]}).status_code == 204
        assert client.post("/api/auth/refresh", json={"refreshToken": session["refreshToken"]}).status_code == 401


def test_access_token_cannot_be_used_to_refresh(client, db):
    with temporary_teacher(db) as a:
        session = login(client, a["email"])
        assert client.post("/api/auth/refresh", json={"refreshToken": session["accessToken"]}).status_code == 401


def test_change_password_validates_current_and_ends_other_sessions(client, db):
    with temporary_teacher(db) as a:
        other_session = login(client, a["email"])
        current = login(client, a["email"])
        wrong = client.post("/api/auth/change-password", headers=bearer(current), json={"currentPassword": "errada", "newPassword": "Nova@12345"})
        assert wrong.status_code == 400
        changed = client.post("/api/auth/change-password", headers=bearer(current), json={"currentPassword": PASSWORD, "newPassword": "Nova@12345"})
        assert changed.status_code == 200, changed.text
        assert client.get("/api/students", headers=bearer(other_session)).status_code == 401
        assert client.post("/api/auth/refresh", json={"refreshToken": other_session["refreshToken"]}).status_code == 401
        assert client.get("/api/students", headers=bearer(changed.json())).status_code == 200
        assert client.post("/api/auth/login", json={"email": a["email"], "password": "Nova@12345"}).status_code == 200


def test_password_reset_invalidates_existing_sessions(client, db):
    with temporary_teacher(db) as a:
        session = login(client, a["email"])
        code = client.post("/api/auth/forgot-password", json={"email": a["email"]}).json()["demoCode"]
        reset = client.post("/api/auth/reset-password", json={"email": a["email"], "code": code, "newPassword": "Reset@12345"})
        assert reset.status_code == 200, reset.text
        assert client.get("/api/students", headers=bearer(session)).status_code == 401
        assert client.post("/api/auth/refresh", json={"refreshToken": session["refreshToken"]}).status_code == 401


def test_login_is_rate_limited_after_repeated_failures(db):
    with TestClient(create_app(make_settings(login_max_failures=3))) as limited, temporary_teacher(db) as a:
        for _ in range(3):
            assert limited.post("/api/auth/login", json={"email": a["email"], "password": "errada"}).status_code == 401
        blocked = limited.post("/api/auth/login", json={"email": a["email"], "password": PASSWORD})
        assert blocked.status_code == 429
        assert "Retry-After" in blocked.headers


def test_insecure_demo_settings_are_refused_in_production():
    with pytest.raises(RuntimeError):
        create_app(make_settings(app_env="production"))  # modo demo de senha + segredo de teste
    strong = "x" * 48
    assert make_settings(app_env="production", jwt_secret=strong, password_reset_demo_mode=False).insecure_production_settings() == []


# ------------------------------------------------------------------ 1.4 integridade dos dados
def test_enroll_keeps_a_single_membership_and_unenroll_from_other_class_keeps_link(client, db, admin, student_factory):
    with temporary_teacher(db, with_classroom=True) as a, temporary_teacher(db, with_classroom=True) as b:
        student = student_factory(a["classroom_id"])
        # Dado legado inconsistente: o aluno aparece também na lista da turma B.
        db.classrooms.update_one({"_id": ObjectId(b["classroom_id"])}, {"$addToSet": {"students": student["id"]}})
        headers = bearer(login(client, admin))

        # Remover de B (onde ele não está matriculado de fato) não pode apagar o vínculo com A.
        assert client.delete(f"/api/classrooms/{b['classroom_id']}/unenroll/{student['id']}", headers=headers).status_code == 204
        assert db.students.find_one({"_id": ObjectId(student["id"])})["class_id"] == a["classroom_id"]

        assert client.post(f"/api/classrooms/{b['classroom_id']}/enroll/{student['id']}", headers=headers).status_code == 204
        lists = [c for c in db.classrooms.find({"students": student["id"]})]
        assert [str(c["_id"]) for c in lists] == [b["classroom_id"]]
        assert db.students.find_one({"_id": ObjectId(student["id"])})["class_id"] == b["classroom_id"]


def test_student_created_with_class_is_added_to_the_class_list(client, db, admin):
    with temporary_teacher(db, with_classroom=True) as a:
        headers = bearer(login(client, a["email"]))
        email = f"novo.{uuid4().hex[:8]}@aluno.local"
        created = client.post("/api/students", headers=headers, json={"name": "Aluno Lista", "email": email, "birthDate": "2012-01-02", "classId": a["classroom_id"]})
        try:
            assert created.status_code == 201, created.text
            classroom = db.classrooms.find_one({"_id": ObjectId(a["classroom_id"])})
            assert created.json()["id"] in [str(x) for x in classroom["students"]]
            assert created.json()["matricula"].startswith(f"MAT-{datetime.now(timezone.utc).year}-")
        finally:
            db.students.delete_many({"email": email})


def test_deleting_a_student_deactivates_portal_account_and_leaves_the_class(client, db, student_factory):
    with temporary_teacher(db, with_classroom=True) as a:
        student = student_factory(a["classroom_id"], with_account=True)
        portal = login(client, student["email"])
        headers = bearer(login(client, a["email"]))
        assert client.delete(f"/api/students/{student['id']}", headers=headers).status_code == 204
        assert db.users.find_one({"email": student["email"]})["active"] is False
        assert client.get("/api/student-portal/me", headers=bearer(portal)).status_code == 401
        classroom = db.classrooms.find_one({"_id": ObjectId(a["classroom_id"])})
        assert student["id"] not in [str(x) for x in classroom.get("students", [])]


def test_student_email_change_is_synced_to_the_portal_account(client, db, student_factory):
    with temporary_teacher(db, with_classroom=True) as a:
        student = student_factory(a["classroom_id"], with_account=True)
        headers = bearer(login(client, a["email"]))
        new_email = f"trocado.{uuid4().hex[:8]}@aluno.local"
        try:
            assert client.put(f"/api/students/{student['id']}", headers=headers, json={"email": new_email}).status_code == 200
            assert db.users.find_one({"email": new_email}) is not None
            assert client.post("/api/auth/login", json={"email": new_email, "password": PASSWORD}).status_code == 200
        finally:
            db.users.delete_many({"email": new_email})
            db.refresh_tokens.delete_many({"email": new_email})
