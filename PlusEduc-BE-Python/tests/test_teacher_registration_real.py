from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.passwords import verify_password
from app.main import app


def test_public_teacher_registration_creates_profile_and_authenticates():
    email = f"teacher.public.{uuid4().hex[:12]}@professor.local"
    password = "Teacher@123"
    name = "Professor Público Demonstração"
    mongo = MongoClient("mongodb://localhost:27017")
    db = mongo["escola_db"]

    try:
        with TestClient(app) as client:
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
            assert user is not None
            assert teacher is not None
            assert user["role"] == "TEACHER"
            assert user["password"] != password
            assert verify_password(password, user["password"])
            assert teacher["name"] == name
            assert teacher["password"] != password
            assert verify_password(password, teacher["password"])

            login = client.post("/api/auth/login", json={"email": email, "password": password})
            assert login.status_code == 200, login.text
            assert login.json()["role"] == "TEACHER"
            assert login.json()["name"] == name

            duplicate = client.post(
                "/api/auth/register/teacher",
                json={"name": "Outro Nome", "email": email, "password": password},
            )
            assert duplicate.status_code == 409, duplicate.text
    finally:
        db.users.delete_many({"email": email})
        db.teachers.delete_many({"email": email})
        mongo.close()
