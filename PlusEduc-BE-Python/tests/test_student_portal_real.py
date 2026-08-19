import json
from datetime import datetime, timezone

import bcrypt
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import Settings
from app.core.jwt import create_access_token
from app.dependencies import get_current_user
from app.main import create_app


class FakeUserRepository:
    def __init__(self, users: list[dict]):
        self.users = {item["email"]: item for item in users}

    def find_active_by_email(self, email: str):
        user = self.users.get(email)
        if user is None or user.get("active", True) is False:
            return None
        return user


def test_student_login_returns_student_role_and_claim_contract():
    password_hash = bcrypt.hashpw(b"student-password", bcrypt.gensalt()).decode()
    settings = Settings(
        app_env="test-student-login",
        mongodb_uri="mongodb://127.0.0.1:27018",
        mongodb_required=False,
        mongodb_server_selection_timeout_ms=50,
        mongodb_connect_timeout_ms=50,
        jwt_secret="test-student-login-secret",
    )
    fake_users = FakeUserRepository([{
        "_id": "student-login-id",
        "email": "student-login@example.com",
        "password": password_hash,
        "role": "STUDENT",
        "studentId": "student-profile-id",
        "name": "Aluno de Teste",
        "active": True,
    }])
    with TestClient(create_app(settings, user_repository=fake_users)) as client:
        response = client.post("/api/auth/login", json={
            "email": "student-login@example.com",
            "password": "student-password",
        })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["role"] == "STUDENT"
    assert payload["studentId"] == "student-profile-id"
    assert payload["tokenType"] == "Bearer"
    assert payload["accessToken"]


@pytest.fixture
def student_portal_real_context():
    settings = Settings(
        app_env="test-real-student-portal",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-real-student-portal-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    activity_id = None
    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        required = ["users", "students", "teachers", "classrooms", "activities", "activity_submissions", "grades"]
        missing = [name for name in required if name not in db.list_collection_names()]
        assert not missing, f"Collections ausentes em escola_db: {missing}"

        student = db.students.find_one({"active": True})
        assert student, "É necessário um aluno real"
        class_id = student.get("classId", student.get("class_id"))
        assert class_id, "É necessário um aluno real associado a uma turma"
        classroom = db.classrooms.find_one({"_id": ObjectId(str(class_id))}) if ObjectId.is_valid(str(class_id)) else db.classrooms.find_one({"_id": class_id})
        assert classroom and classroom.get("active", True) is not False, "É necessário uma turma real ativa"
        student_id = str(student["_id"])
        classroom_id = str(classroom["_id"])
        auth_user = {
            "_id": "phase9-student-auth",
            "email": "phase9-student-auth@example.com",
            "role": "STUDENT",
            "studentId": student_id,
            "active": True,
        }
        token = create_access_token(auth_user["email"], settings)

        activity = {
            "title": "Atividade Temporária do Portal",
            "subject": "Matemática",
            "topic": "Equações",
            "difficulty_level": "MEDIO",
            "questions_count": 2,
            "format": "MULTIPLA_ESCOLHA",
            "classroom_id": classroom_id,
            "student_id": student_id,
            "content": json.dumps({"questions": [
                {
                    "questionText": "Quanto é 2 + 2?",
                    "questionType": "MULTIPLA_ESCOLHA",
                    "options": ["A) 4", "B) 5"],
                    "correctAnswer": "A",
                    "explanation": "Soma básica.",
                },
                {
                    "questionText": "Quanto é 3 + 3?",
                    "questionType": "MULTIPLA_ESCOLHA",
                    "options": ["A) 5", "B) 6"],
                    "correctAnswer": "B",
                    "explanation": "Soma básica.",
                },
            ]}, ensure_ascii=False),
            "generated_by_ai": False,
            "created_at": datetime.now(timezone.utc),
        }
        activity_id = str(db.activities.insert_one(activity).inserted_id)
        app = create_app(settings, user_repository=FakeUserRepository([auth_user]))
        headers = {"Authorization": f"Bearer {token}"}
        with TestClient(app) as client:
            yield client, db, headers, student_id, classroom_id, activity_id
    finally:
        if activity_id:
            db.activities.delete_one({"_id": ObjectId(activity_id)})
            db.activity_submissions.delete_many({"activity_id": activity_id, "student_id": student_id})
        mongo.close()


def test_student_portal_end_to_end_on_real_mongodb(student_portal_real_context):
    client, db, headers, student_id, classroom_id, activity_id = student_portal_real_context

    profile = client.get("/api/student-portal/me", headers=headers)
    assert profile.status_code == 200, profile.text
    assert profile.json()["studentId"] == student_id
    assert profile.json()["classId"] == classroom_id

    classroom = client.get("/api/student-portal/classroom", headers=headers)
    assert classroom.status_code == 200, classroom.text
    assert classroom.json()["id"] == classroom_id

    classmates = client.get("/api/student-portal/classmates", headers=headers)
    teachers = client.get("/api/student-portal/teachers", headers=headers)
    assert classmates.status_code == 200 and isinstance(classmates.json(), list)
    assert teachers.status_code == 200 and isinstance(teachers.json(), list)

    activities = client.get("/api/student-portal/activities", headers=headers)
    assert activities.status_code == 200, activities.text
    item = next(row for row in activities.json() if row["id"] == activity_id)
    assert item["submitted"] is False

    detail = client.get(f"/api/student-portal/activities/{activity_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["submitted"] is False
    assert len(detail.json()["questions"]) == 2
    assert "correctAnswer" not in detail.json()["questions"][0]

    submission_payload = {"answers": [
        {"questionIndex": 0, "selectedAnswer": "A"},
        {"questionIndex": 1, "selectedAnswer": "B"},
    ]}
    submission = client.post(f"/api/student-portal/activities/{activity_id}/submissions", json=submission_payload, headers=headers)
    assert submission.status_code == 200, submission.text
    assert submission.json()["correctCount"] == 2
    assert submission.json()["totalQuestions"] == 2
    assert submission.json()["scorePercent"] == 100
    assert len(submission.json()["results"]) == 2

    duplicate = client.post(f"/api/student-portal/activities/{activity_id}/submissions", json=submission_payload, headers=headers)
    assert duplicate.status_code == 409

    submitted_detail = client.get(f"/api/student-portal/activities/{activity_id}", headers=headers)
    assert submitted_detail.status_code == 200
    assert submitted_detail.json()["submitted"] is True
    assert submitted_detail.json()["questions"] == []
    assert submitted_detail.json()["scorePercent"] == 100

    grades = client.get("/api/student-portal/grades", headers=headers)
    assert grades.status_code == 200, grades.text
    assert isinstance(grades.json(), list)

    pdf = client.get(f"/api/student-portal/activities/{activity_id}/export-pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.headers["content-disposition"].startswith("attachment;")
    assert pdf.content.startswith(b"%PDF")


def test_student_portal_rejects_teacher_role(student_portal_real_context):
    client, db, _, _, _, _ = student_portal_real_context
    teacher = db.teachers.find_one({"active": {"$ne": False}})
    assert teacher, "É necessário um professor real para validar a autorização"
    settings = Settings(
        app_env="test-real-student-portal-teacher",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        jwt_secret="test-real-student-portal-secret",
    )
    teacher_auth = {
        "_id": str(teacher["_id"]),
        "email": str(teacher.get("email", "phase9-teacher@example.com")),
        "role": "TEACHER",
        "active": True,
    }
    teacher_token = create_access_token(teacher_auth["email"], settings)
    teacher_app = create_app(settings, user_repository=FakeUserRepository([teacher_auth]))
    with TestClient(teacher_app) as teacher_client:
        response = teacher_client.get("/api/student-portal/me", headers={"Authorization": f"Bearer {teacher_token}"})
    assert response.status_code == 403
