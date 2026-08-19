import json
from datetime import datetime, timezone

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.auth import UserPrincipal
from app.core.config import Settings
from app.dependencies import get_current_user
from app.main import create_app


@pytest.fixture
def teacher_corrections_context():
    settings = Settings(
        app_env="test-real-teacher-corrections",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-teacher-corrections-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        for collection in ["activities", "activity_submissions", "students", "teachers", "classrooms"]:
            if collection not in db.list_collection_names():
                pytest.fail(f"Collection {collection} não existe em escola_db")
        student = db.students.find_one({})
        teacher = db.teachers.find_one({})
        classroom = db.classrooms.find_one({})
        if not student or not teacher or not classroom:
            pytest.fail("Dados reais de student, teacher e classroom são necessários")
        student_id = str(student["_id"])
        teacher_id = str(teacher["_id"])
        teacher_email = str(teacher.get("email", "teacher-corrections@local"))
        teacher_user = UserPrincipal(user_id=teacher_id, email=teacher_email, role="TEACHER")
        app = create_app(settings)
        app.dependency_overrides[get_current_user] = lambda: teacher_user
        with TestClient(app) as client:
            yield client, db, student_id, teacher_id, teacher_email, str(classroom["_id"])
    finally:
        mongo.close()


def test_teacher_can_review_discursive_submission_on_real_mongodb(teacher_corrections_context):
    client, db, student_id, teacher_id, teacher_email, classroom_id = teacher_corrections_context
    activity_payload = {
        "title": "Atividade Temporária de Correção Discursiva",
        "subject": "Matemática",
        "topic": "Equações",
        "difficultyLevel": "MEDIO",
        "questionsCount": 2,
        "format": "MISTA",
        "classroomId": classroom_id,
        "questions": [
            {
                "questionText": "Quanto é 2 + 2?",
                "questionType": "MULTIPLA_ESCOLHA",
                "options": ["3", "4"],
                "correctAnswer": "4",
            },
            {
                "questionText": "Explique como você resolveu a equação.",
                "questionType": "DISCURSIVA",
                "options": [],
                "correctAnswer": None,
            },
        ],
    }
    created = client.post("/api/activities", json=activity_payload)
    assert created.status_code == 201
    activity_id = created.json()["id"]
    submission_id = None

    try:
        student_user = UserPrincipal(user_id=student_id, email="student-corrections@local", role="STUDENT", student_id=student_id)
        teacher_user = UserPrincipal(user_id=teacher_id, email=teacher_email, role="TEACHER")
        client.app.dependency_overrides[get_current_user] = lambda: student_user
        submission = client.post(
            f"/api/student-portal/activities/{activity_id}/submissions",
            json={"answers": [
                {"questionIndex": 0, "selectedAnswer": "4"},
                {"questionIndex": 1, "selectedAnswer": "Isolei a incógnita e substituí o resultado."},
            ]},
        )
        assert submission.status_code == 200
        assert submission.json()["correctCount"] == 1
        assert submission.json()["pendingCount"] == 1
        assert submission.json()["results"][1]["reviewStatus"] == "PENDING"

        stored_submission = db.activity_submissions.find_one({"activity_id": activity_id, "student_id": student_id})
        assert stored_submission is not None
        submission_id = str(stored_submission["_id"])

        client.app.dependency_overrides[get_current_user] = lambda: teacher_user
        pending = client.get("/api/teacher/activity-corrections/pending")
        assert pending.status_code == 200
        pending_item = next(item for item in pending.json() if item["submissionId"] == submission_id)
        assert pending_item["questions"][0]["questionIndex"] == 1

        reviewed = client.put(
            f"/api/teacher/activity-corrections/{submission_id}/questions/1",
            json={"correct": True, "feedback": "Boa explicação."},
        )
        assert reviewed.status_code == 200
        assert reviewed.json()["pendingCount"] == 0
        assert reviewed.json()["correctCount"] == 2
        assert reviewed.json()["results"][1]["reviewStatus"] == "REVIEWED"

        pending_after = client.get("/api/teacher/activity-corrections/pending")
        assert pending_after.status_code == 200
        assert all(item["submissionId"] != submission_id for item in pending_after.json())

        client.app.dependency_overrides[get_current_user] = lambda: student_user
        detail = client.get(f"/api/student-portal/activities/{activity_id}")
        assert detail.status_code == 200
        assert detail.json()["pendingCount"] == 0
        assert detail.json()["results"][1]["teacherFeedback"] == "Boa explicação."
    finally:
        db.activity_submissions.delete_many({"activity_id": activity_id, "student_id": student_id})
        client.app.dependency_overrides[get_current_user] = lambda: UserPrincipal(user_id=teacher_id, email=teacher_email, role="TEACHER")
        deleted = client.delete(f"/api/activities/{activity_id}")
        assert deleted.status_code == 204
        assert db.activities.find_one({"_id": ObjectId(activity_id)}) is None
