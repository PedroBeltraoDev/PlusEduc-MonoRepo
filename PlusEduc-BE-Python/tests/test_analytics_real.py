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
def analytics_real_context():
    settings = Settings(
        app_env="test-real-analytics",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-analytics-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    temporary_student_id = None
    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        grade = db.grades.find_one({"studentId": {"$exists": True}})
        if not grade:
            pytest.fail("Nenhuma nota real está disponível em escola_db.grades")

        student_with_grades = str(grade["studentId"])
        grade_student_ids = {
            str(item["studentId"])
            for item in db.grades.find({"studentId": {"$exists": True}}, {"studentId": 1})
        }
        student_without_grades = next(
            (
                item
                for item in db.students.find({}, {"_id": 1})
                if str(item["_id"]) not in grade_student_ids
            ),
            None,
        )

        if student_without_grades is None:
            classroom = db.classrooms.find_one({}, {"_id": 1})
            if not classroom:
                pytest.fail("Nenhuma classroom real está disponível para a fixture")
            temporary_student_id = ObjectId()
            now = datetime.now(timezone.utc)
            db.students.insert_one(
                {
                    "_id": temporary_student_id,
                    "name": "__TEMP_FASE6_SEM_NOTAS_AUTOMATICO__",
                    "email": f"__temp_fase6_{temporary_student_id}@local.test",
                    "birth_date": "2010-01-01",
                    "class_id": str(classroom["_id"]),
                    "learning_gaps": [],
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            student_without_grades_id = str(temporary_student_id)
        else:
            student_without_grades_id = str(student_without_grades["_id"])

        with TestClient(create_app(settings)) as client:
            client.app.dependency_overrides[get_current_user] = lambda: UserPrincipal(
                user_id="analytics-test-user",
                email="teacher-analytics@local",
                role="TEACHER",
            )
            yield client, student_with_grades, student_without_grades_id
    finally:
        if temporary_student_id is not None:
            deleted = db.students.delete_one(
                {"_id": temporary_student_id, "name": "__TEMP_FASE6_SEM_NOTAS_AUTOMATICO__"}
            )
            assert deleted.deleted_count == 1
        mongo.close()


def test_performance_student_with_real_grades(analytics_real_context):
    client, student_with_grades, _ = analytics_real_context
    response = client.get(f"/api/students/{student_with_grades}/performance")

    assert response.status_code == 200
    payload = response.json()
    assert payload["studentId"] == student_with_grades
    assert payload["totalActivities"] >= 1
    assert payload["completedActivities"] == payload["totalActivities"]
    assert 0 <= payload["averageGrade"] <= 10
    assert payload["subjectPerformance"]


def test_performance_student_without_real_grades(analytics_real_context):
    client, _, student_without_grades = analytics_real_context
    response = client.get(f"/api/students/{student_without_grades}/performance")

    assert response.status_code == 200
    assert response.json() == {
        "studentId": student_without_grades,
        "averageGrade": 0.0,
        "totalActivities": 0,
        "completedActivities": 0,
        "subjectPerformance": [],
    }


def test_average_calculation_matches_real_grade_data(analytics_real_context):
    client, student_with_grades, _ = analytics_real_context
    response = client.get(f"/api/students/{student_with_grades}/performance")
    assert response.status_code == 200
    payload = response.json()
    assert payload["averageGrade"] == 8.5
    assert payload["subjectPerformance"][0]["average"] == 8.5


def test_attendance_with_real_grades(analytics_real_context):
    client, student_with_grades, _ = analytics_real_context
    response = client.get(f"/api/students/{student_with_grades}/attendance")

    assert response.status_code == 200
    payload = response.json()
    assert payload["studentId"] == student_with_grades
    assert payload["totalClasses"] == 1
    assert payload["attendedClasses"] == 1
    assert payload["absences"] == 0
    assert payload["attendanceRate"] == 100


def test_attendance_without_real_grades(analytics_real_context):
    client, _, student_without_grades = analytics_real_context
    response = client.get(f"/api/students/{student_without_grades}/attendance")

    assert response.status_code == 200
    assert response.json() == {
        "studentId": student_without_grades,
        "attendanceRate": 0,
        "totalClasses": 0,
        "attendedClasses": 0,
        "absences": 0,
    }
