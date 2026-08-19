from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.auth import UserPrincipal
from app.core.config import Settings
from app.dependencies import get_current_user
from app.main import create_app


@pytest.fixture
def real_grade_context():
    settings = Settings(
        app_env="test-real-mongodb",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-real-mongodb-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        if "grades" not in db.list_collection_names():
            pytest.fail("A collection grades não existe em escola_db")
        sample = db.grades.find_one({"studentId": {"$exists": True}, "classroomId": {"$exists": True}})
        if not sample:
            pytest.fail("A collection grades não possui documento com studentId e classroomId")
        student_id = str(sample["studentId"])
        classroom_id = str(sample["classroomId"])
        student = db.students.find_one({"$or": [{"_id": student_id}, {"_id": _object_id(student_id)}]})
        classroom = db.classrooms.find_one({"$or": [{"_id": classroom_id}, {"_id": _object_id(classroom_id)}]})
        if not student or not classroom:
            pytest.fail("As referências do documento real de grades não existem em students/classrooms")

        app = create_app(settings)
        app.dependency_overrides[get_current_user] = lambda: UserPrincipal(
            user_id="real-test-user",
            email="teacher-test@local",
            role="TEACHER",
        )
        with TestClient(app) as client:
            yield client, student_id, classroom_id
    finally:
        mongo.close()


def _object_id(value: str):
    from bson import ObjectId
    return ObjectId(value) if ObjectId.is_valid(value) else value


def test_grades_real_mongodb_crud_queries_and_average(real_grade_context):
    client, student_id, classroom_id = real_grade_context
    payload = {
        "studentId": student_id,
        "classroomId": classroom_id,
        "gradeValue": 7.25,
        "attendance": True,
        "subject": "Matematica",
        "activityType": "ASSIGNMENT",
        "observations": "Teste real da Fase 5",
        "date": "2026-06-01T10:00:00Z",
    }
    created = client.post("/api/grades", json=payload)
    assert created.status_code == 201
    grade_id = created.json()["id"]
    assert created.json()["grade"] == 7.25
    assert created.json()["gradeValue"] == 7.25
    assert created.json()["studentId"] == student_id
    assert created.json()["classroomId"] == classroom_id
    assert created.json()["date"].startswith("2026-06-01T10:00:00")

    try:
        fetched = client.get(f"/api/grades/{grade_id}")
        assert fetched.status_code == 200

        all_grades = client.get("/api/grades")
        assert all_grades.status_code == 200
        assert any(item["id"] == grade_id for item in all_grades.json())

        by_student = client.get(f"/api/grades/student/{student_id}")
        assert by_student.status_code == 200
        assert any(item["id"] == grade_id for item in by_student.json())

        by_classroom = client.get(f"/api/grades/classroom/{classroom_id}")
        assert by_classroom.status_code == 200
        assert any(item["id"] == grade_id for item in by_classroom.json())

        updated = client.put(
            f"/api/grades/{grade_id}",
            json={"grade": 9.0, "observations": "Nota atualizada no MongoDB real"},
        )
        assert updated.status_code == 200
        assert updated.json()["grade"] == 9.0
        assert updated.json()["gradeValue"] == 9.0

        average = client.get(f"/api/grades/student/{student_id}/average")
        assert average.status_code == 200
        assert isinstance(average.json(), (float, int))
        assert 0 <= average.json() <= 10
    finally:
        deleted = client.delete(f"/api/grades/{grade_id}")
        assert deleted.status_code == 204


def test_grades_reject_invalid_student_and_classroom(real_grade_context):
    client, student_id, classroom_id = real_grade_context
    response = client.post(
        "/api/grades",
        json={
            "studentId": "student-that-does-not-exist",
            "classroomId": classroom_id,
            "grade": 8,
            "date": "2026-06-01T10:00:00Z",
        },
    )
    assert response.status_code == 400

    response = client.post(
        "/api/grades",
        json={
            "studentId": student_id,
            "classroomId": "classroom-that-does-not-exist",
            "grade": 8,
            "date": "2026-06-01T10:00:00Z",
        },
    )
    assert response.status_code == 400
