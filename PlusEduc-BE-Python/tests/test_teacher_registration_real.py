from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pymongo import MongoClient

from tests.database import TEST_DATABASE
from app.core.config import get_settings
from app.core.passwords import hash_password, verify_password
from app.main import create_app


def make_app(requires_approval: bool):
    return create_app(
        get_settings().model_copy(
            update={"mongodb_database": TEST_DATABASE, "teacher_registration_requires_approval": requires_approval}
        )
    )


def test_public_teacher_registration_requires_admin_approval():
    """Cadastro público de professor não dá acesso imediato: fica pendente até o ADMIN aprovar."""
    token = uuid4().hex[:12]
    email = f"teacher.public.{token}@professor.local"
    admin_email = f"admin.aprovacao.{token}@pluseduc.local"
    password = "Teacher@123"
    name = "Professor Público Demonstração"
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo[TEST_DATABASE]

    try:
        db.users.insert_one({"email": admin_email, "password": hash_password(password), "role": "ADMIN", "active": True})
        with TestClient(make_app(requires_approval=True)) as client:
            registration = client.post(
                "/api/auth/register/teacher",
                json={"name": name, "email": email, "password": password},
            )
            assert registration.status_code == 202, registration.text
            body = registration.json()
            assert body["status"] == "PENDING_APPROVAL"
            assert "accessToken" not in body

            user = db.users.find_one({"email": email})
            teacher = db.teachers.find_one({"email": email})
            assert user is not None and teacher is not None
            assert user["role"] == "TEACHER"
            assert user["active"] is False and user["pendingApproval"] is True
            assert user["password"] != password
            assert verify_password(password, user["password"])
            assert teacher["active"] is False and teacher["approval_status"] == "PENDING"
            assert "password" not in teacher  # senha só em users, com hash

            pending_login = client.post("/api/auth/login", json={"email": email, "password": password})
            assert pending_login.status_code == 403, pending_login.text
            assert "aguarda a aprovação" in pending_login.json()["message"]
            wrong_password = client.post("/api/auth/login", json={"email": email, "password": "senha-errada"})
            assert wrong_password.status_code == 401  # o status do cadastro só aparece para quem sabe a senha

            admin_token = client.post("/api/auth/login", json={"email": admin_email, "password": password}).json()["accessToken"]
            admin = {"Authorization": f"Bearer {admin_token}"}
            pending = client.get("/api/teachers/pending", headers=admin)
            assert pending.status_code == 200
            teacher_id = next(item["id"] for item in pending.json() if item["email"] == email)

            approve = client.post(f"/api/teachers/{teacher_id}/approve", headers=admin)
            assert approve.status_code == 200, approve.text

            login = client.post("/api/auth/login", json={"email": email, "password": password})
            assert login.status_code == 200, login.text
            assert login.json()["role"] == "TEACHER"
            assert login.json()["name"] == name

            teacher_headers = {"Authorization": f"Bearer {login.json()['accessToken']}"}
            assert client.get("/api/teachers/pending", headers=teacher_headers).status_code == 403

            duplicate = client.post(
                "/api/auth/register/teacher",
                json={"name": "Outro Nome", "email": email, "password": password},
            )
            assert duplicate.status_code == 409, duplicate.text
    finally:
        db.users.delete_many({"email": {"$in": [email, admin_email]}})
        db.teachers.delete_many({"email": email})
        db.refresh_tokens.delete_many({"email": {"$in": [email, admin_email]}})
        mongo.close()


def test_public_teacher_registration_without_approval_authenticates():
    """Modo sem aprovação (TEACHER_REGISTRATION_REQUIRES_APPROVAL=false), ainda disponível fora de produção."""
    email = f"teacher.public.{uuid4().hex[:12]}@professor.local"
    password = "Teacher@123"
    name = "Professor Público Demonstração"
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo[TEST_DATABASE]

    try:
        with TestClient(make_app(requires_approval=False)) as client:
            registration = client.post(
                "/api/auth/register/teacher",
                json={"name": name, "email": email, "password": password},
            )
            assert registration.status_code == 200, registration.text
            body = registration.json()
            assert body["role"] == "TEACHER"
            assert body["userEmail"] == email
            assert body["name"] == name
            assert "studentId" not in body
            assert body["accessToken"]

            user = db.users.find_one({"email": email})
            teacher = db.teachers.find_one({"email": email})
            assert user is not None and teacher is not None
            assert user["role"] == "TEACHER"
            assert verify_password(password, user["password"])
            assert teacher["name"] == name
            assert "password" not in teacher

            login = client.post("/api/auth/login", json={"email": email, "password": password})
            assert login.status_code == 200, login.text
            assert login.json()["name"] == name
    finally:
        db.users.delete_many({"email": email})
        db.teachers.delete_many({"email": email})
        db.refresh_tokens.delete_many({"email": email})
        mongo.close()
