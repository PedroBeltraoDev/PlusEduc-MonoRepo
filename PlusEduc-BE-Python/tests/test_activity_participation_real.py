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
def activity_participation_context():
    settings = Settings(
        app_env="test-real-activity-participation",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-activity-participation-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        for collection in ["activities", "activity_submissions", "students", "teachers", "classrooms"]:
            if collection not in db.list_collection_names():
                pytest.fail(f"Collection {collection} não existe em escola_db")
        classroom = db.classrooms.find_one({"active": {"$ne": False}})
        teacher = db.teachers.find_one({"active": {"$ne": False}})
        if not classroom or not teacher:
            pytest.fail("Dados reais de turma e professor são necessários")
        member_ids = classroom.get("studentIds", classroom.get("student_ids", classroom.get("students", []))) or []
        if not member_ids:
            pytest.fail("A turma real precisa ter pelo menos um aluno matriculado")
        student_id = str(member_ids[0])
        student = db.students.find_one({"_id": ObjectId(student_id)}) if ObjectId.is_valid(student_id) else db.students.find_one({"_id": student_id})
        if not student:
            pytest.fail("O aluno matriculado na turma real precisa existir")
        classroom_id = str(classroom["_id"])
        teacher_id = str(teacher["_id"])
        teacher_email = str(teacher.get("email", "teacher-participation@local"))
        teacher_user = UserPrincipal(user_id=teacher_id, email=teacher_email, role="TEACHER")
        app = create_app(settings)
        app.dependency_overrides[get_current_user] = lambda: teacher_user
        with TestClient(app) as client:
            yield (
                client,
                db,
                classroom_id,
                student_id,
                str(student.get("name", "Aluno")),
                teacher_id,
                teacher_email,
                len(member_ids),
            )
    finally:
        mongo.close()


def test_activity_participation_summary_is_real_and_updates_after_submission(activity_participation_context):
    (
        client,
        db,
        classroom_id,
        student_id,
        student_name,
        teacher_id,
        teacher_email,
        member_count,
    ) = activity_participation_context
    created = client.post("/api/activities", json={
        "title": "Atividade Temporária de Participação",
        "subject": "Matemática",
        "topic": "Equações",
        "difficultyLevel": "FACIL",
        "questionsCount": 1,
        "format": "MULTIPLA_ESCOLHA",
        "classroomId": classroom_id,
        "questions": [{
            "questionText": "Quanto é 2 + 2?",
            "questionType": "MULTIPLA_ESCOLHA",
            "options": ["3", "4"],
            "correctAnswer": "4",
        }],
    })
    assert created.status_code == 201, created.text
    activity_id = created.json()["id"]

    try:
        initial = client.get(f"/api/activities/{activity_id}")
        assert initial.status_code == 200, initial.text
        initial_participation = initial.json()["participation"]
        assert initial_participation["totalStudents"] == member_count
        assert initial_participation["completedStudents"] == 0
        assert initial_participation["pendingStudents"] == member_count
        assert any(item["studentName"] == student_name for item in initial_participation["pending"])

        student_user = UserPrincipal(user_id=student_id, email="student-participation@local", role="STUDENT", student_id=student_id)
        teacher_user = UserPrincipal(user_id=teacher_id, email=teacher_email, role="TEACHER")
        client.app.dependency_overrides[get_current_user] = lambda: student_user
        submission = client.post(
            f"/api/student-portal/activities/{activity_id}/submissions",
            json={"answers": [{"questionIndex": 0, "selectedAnswer": "4"}]},
        )
        assert submission.status_code == 200, submission.text

        client.app.dependency_overrides[get_current_user] = lambda: teacher_user
        updated = client.get(f"/api/activities/{activity_id}")
        assert updated.status_code == 200, updated.text
        updated_participation = updated.json()["participation"]
        assert updated_participation["totalStudents"] == member_count
        assert updated_participation["completedStudents"] == 1
        assert updated_participation["pendingStudents"] == member_count - 1
        assert updated_participation["completed"][0]["studentName"] == student_name
        assert len(updated_participation["pending"]) == member_count - 1
        assert all(item["studentName"] != student_name for item in updated_participation["pending"])

        listed = client.get("/api/activities")
        assert listed.status_code == 200, listed.text
        listed_item = next(item for item in listed.json() if item["id"] == activity_id)
        assert listed_item["participation"]["completedStudents"] == 1
    finally:
        db.activity_submissions.delete_many({"activity_id": activity_id, "student_id": student_id})
        db.activities.delete_one({"_id": ObjectId(activity_id)})
