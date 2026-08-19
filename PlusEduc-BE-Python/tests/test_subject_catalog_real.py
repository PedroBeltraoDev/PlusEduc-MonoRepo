from datetime import datetime, timezone
import unicodedata

from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import Settings
from app.core.jwt import create_access_token
from app.main import create_app


class FakeUserRepository:
    def __init__(self, users: list[dict]):
        self.users = {item["email"]: item for item in users}

    def find_active_by_email(self, email: str):
        user = self.users.get(email)
        if user is None or user.get("active", True) is False:
            return None
        return user


def subject_key(value: str) -> str:
    folded = value.strip().casefold()
    return "".join(character for character in unicodedata.normalize("NFKD", folded) if not unicodedata.combining(character))


def test_subject_catalog_and_performance_on_real_mongodb():
    settings = Settings(
        app_env="test-subject-catalog",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-subject-catalog-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    inserted_id = None
    db = None

    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        teacher = db.teachers.find_one({"active": True})
        assert teacher, "É necessário um professor real"
        teacher_id = str(teacher["_id"])
        teacher_email = str(teacher["email"])
        classroom = db.classrooms.find_one({"teacher_id": teacher_id, "active": True})
        assert classroom, "É necessário uma turma real do professor"
        subject_name = "Matemática"
        assert subject_name, "É necessário uma matéria real na turma"

        existing = next((item for item in db.subjects.find({}) if subject_key(str(item.get("name", ""))) == subject_key(subject_name)), None)
        if existing:
            subject_id = str(existing["_id"])
        else:
            inserted_id = db.subjects.insert_one({
                "name": subject_name,
                "name_normalized": subject_key(subject_name),
                "active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }).inserted_id
            subject_id = str(inserted_id)

        user = {"_id": teacher_id, "email": teacher_email, "role": "TEACHER", "active": True}
        token = create_access_token(teacher_email, settings)
        app = create_app(settings, user_repository=FakeUserRepository([user]))

        with TestClient(app) as client:
            headers = {"Authorization": f"Bearer {token}"}
            listed = client.get("/api/subjects", headers=headers)
            assert listed.status_code == 200, listed.text
            assert any(item["id"] == subject_id for item in listed.json())

            classrooms = client.get(f"/api/subjects/{subject_id}/classrooms", headers=headers)
            assert classrooms.status_code == 200, classrooms.text
            assert any(item["id"] == str(classroom["_id"]) for item in classrooms.json())

            performance = client.get(
                f"/api/subjects/{subject_id}/classrooms/{classroom['_id']}/performance",
                params={"sortBy": "grade", "order": "desc"},
                headers=headers,
            )
            assert performance.status_code == 200, performance.text
            rows = performance.json()
            assert rows
            assert {"studentId", "studentName", "averageGrade", "gradeCount"}.issubset(rows[0])
    finally:
        if db is not None and inserted_id is not None:
            db.subjects.delete_one({"_id": inserted_id})
        mongo.close()
