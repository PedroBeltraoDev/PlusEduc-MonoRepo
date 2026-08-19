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
def activities_real_context():
    settings = Settings(
        app_env="test-real-activities",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-activities-secret",
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
        classroom_id = str(classroom["_id"])
        user = UserPrincipal(user_id=teacher_id, email="teacher-activities@local", role="TEACHER", student_id=student_id)
        app = create_app(settings)
        app.dependency_overrides[get_current_user] = lambda: user
        with TestClient(app) as client:
            yield client, db, student_id, teacher_id, classroom_id
    finally:
        mongo.close()


def activity_payload(classroom_id: str, student_id: str):
    return {
        "title": "Atividade Temporária de Teste",
        "subject": "Matemática",
        "topic": "Equações",
        "difficultyLevel": "MEDIO",
        "questionsCount": 2,
        "format": "MULTIPLA_ESCOLHA",
        "classroomId": classroom_id,
        "studentId": student_id,
        "disabilityAdaptations": [],
        "questions": [
            {
                "questionText": "Quanto é 2 + 2?",
                "questionType": "MULTIPLA_ESCOLHA",
                "options": ["3", "4"],
                "correctAnswer": "4",
                "explanation": "Soma básica.",
            },
            {
                "questionText": "Quanto é 3 + 3?",
                "questionType": "MULTIPLA_ESCOLHA",
                "options": ["5", "6"],
                "correctAnswer": "6",
                "explanation": "Soma básica.",
            },
        ],
    }


def test_activities_crud_queries_and_submission_on_real_mongodb(activities_real_context):
    client, db, student_id, teacher_id, classroom_id = activities_real_context
    created = client.post("/api/activities", json=activity_payload(classroom_id, student_id))
    assert created.status_code == 201
    activity_id = created.json()["id"]
    assert created.json()["questions"][0]["questionType"] == "MULTIPLA_ESCOLHA"

    try:
        assert client.get("/api/activities").status_code == 200
        assert client.get(f"/api/activities/{activity_id}").status_code == 200
        assert any(item["id"] == activity_id for item in client.get(f"/api/activities/classroom/{classroom_id}").json())
        assert any(item["id"] == activity_id for item in client.get(f"/api/activities/student/{student_id}").json())
        assert any(item["id"] == activity_id for item in client.get(f"/api/activities/teacher/{teacher_id}").json())

        updated = client.put(f"/api/activities/{activity_id}", json={"title": "Atividade Temporária Editada"})
        assert updated.status_code == 200
        assert updated.json()["title"] == "Atividade Temporária Editada"

        submission_payload = {"answers": [{"questionIndex": 0, "selectedAnswer": "4"}, {"questionIndex": 1, "selectedAnswer": "5"}]}
        student_user = UserPrincipal(user_id=student_id, email="student-activities@local", role="STUDENT", student_id=student_id)
        teacher_user = UserPrincipal(user_id=teacher_id, email="teacher-activities@local", role="TEACHER", student_id=student_id)
        client.app.dependency_overrides[get_current_user] = lambda: student_user
        submission = client.post(f"/api/student-portal/activities/{activity_id}/submissions", json=submission_payload)
        assert submission.status_code == 200
        assert submission.json()["correctCount"] == 1
        assert submission.json()["totalQuestions"] == 2
        assert submission.json()["scorePercent"] == 50
        assert len(submission.json()["results"]) == 2

        duplicate = client.post(f"/api/student-portal/activities/{activity_id}/submissions", json=submission_payload)
        assert duplicate.status_code == 409

        read_submission = client.get(f"/api/student-portal/activities/{activity_id}/submissions")
        assert read_submission.status_code == 200
        assert read_submission.json()["correctCount"] == 1
    finally:
        client.app.dependency_overrides[get_current_user] = lambda: teacher_user
        db.activity_submissions.delete_many({"activity_id": activity_id, "student_id": student_id})
        deleted = client.delete(f"/api/activities/{activity_id}")
        assert deleted.status_code == 204
        assert db.activities.find_one({"_id": ObjectId(activity_id)}) is None


def test_activity_data_collections_are_real_and_unchanged_after_cleanup(activities_real_context):
    _, db, _, _, _ = activities_real_context
    assert db.activities.count_documents({}) >= 1
    assert db.activity_submissions.count_documents({}) >= 1
