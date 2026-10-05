"""Sprint 6: respostas individuais para o professor e índice único de submissões (MongoDB real)."""
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.auth import UserPrincipal
from app.core.config import Settings
from app.dependencies import get_current_user
from app.main import create_app
from app.repositories.activity_submission_repository import DuplicateSubmissionError


@pytest.fixture
def submissions_context():
    settings = Settings(
        app_env="test-submissions-sprint6",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-submissions-sprint6-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        student = db.students.find_one({
            "active": {"$ne": False},
            "$or": [{"class_id": {"$nin": [None, ""]}}, {"classId": {"$nin": [None, ""]}}],
        })
        if not student:
            pytest.fail("Nenhum aluno ativo matriculado em escola_db")
        student_id = str(student["_id"])
        classroom_id = str(student.get("class_id") or student.get("classId"))
        teacher = UserPrincipal(user_id="sprint6-teacher", email="teacher-sprint6@local", role="TEACHER")
        app = create_app(settings)
        app.dependency_overrides[get_current_user] = lambda: teacher
        with TestClient(app) as client:
            yield client, db, student_id, classroom_id, teacher
    finally:
        mongo.close()


def _create_activity(client, student_id, classroom_id):
    created = client.post("/api/activities", json={
        "title": "Atividade Temporária Respostas Individuais", "subject": "Matemática", "topic": "Somas",
        "difficultyLevel": "MEDIO", "questionsCount": 2, "format": "MULTIPLA_ESCOLHA",
        "classroomId": classroom_id, "studentId": student_id, "disabilityAdaptations": [],
        "questions": [
            {"questionText": "2 + 2?", "questionType": "MULTIPLA_ESCOLHA", "options": ["3", "4"], "correctAnswer": "4", "explanation": "x"},
            {"questionText": "3 + 3?", "questionType": "MULTIPLA_ESCOLHA", "options": ["5", "6"], "correctAnswer": "6", "explanation": "x"},
        ],
    })
    assert created.status_code == 201
    return created.json()["id"]


def test_teacher_sees_individual_answers_and_student_cannot(submissions_context):
    client, db, student_id, classroom_id, teacher = submissions_context
    activity_id = _create_activity(client, student_id, classroom_id)
    student_user = UserPrincipal(user_id=student_id, email="student-sprint6@local", role="STUDENT", student_id=student_id)
    outsider = UserPrincipal(user_id="outro-professor", email="outro@local", role="TEACHER")
    try:
        assert client.get(f"/api/activities/{activity_id}/submissions").json() == []

        client.app.dependency_overrides[get_current_user] = lambda: student_user
        sent = client.post(f"/api/student-portal/activities/{activity_id}/submissions", json={
            "answers": [{"questionIndex": 0, "selectedAnswer": "4"}, {"questionIndex": 1, "selectedAnswer": "5"}],
        })
        assert sent.status_code == 200
        assert client.get(f"/api/activities/{activity_id}/submissions").status_code == 403

        client.app.dependency_overrides[get_current_user] = lambda: outsider
        assert client.get(f"/api/activities/{activity_id}/submissions").status_code == 403

        client.app.dependency_overrides[get_current_user] = lambda: teacher
        rows = client.get(f"/api/activities/{activity_id}/submissions").json()
        assert len(rows) == 1
        row = rows[0]
        assert row["studentId"] == student_id and row["studentName"]
        assert (row["correctCount"], row["totalQuestions"], row["scorePercent"], row["pendingCount"]) == (1, 2, 50, 0)
        assert [item["selectedAnswer"] for item in row["results"]] == ["4", "5"]
        assert [item["correctAnswer"] for item in row["results"]] == ["4", "6"]  # o professor vê o gabarito
        assert client.get(f"/api/activities/{ObjectId()}/submissions").status_code == 404
    finally:
        client.app.dependency_overrides[get_current_user] = lambda: teacher
        db.activity_submissions.delete_many({"activity_id": activity_id})
        client.delete(f"/api/activities/{activity_id}")


def test_database_rejects_a_second_submission_for_the_same_activity_and_student(submissions_context):
    client, db, student_id, _, _ = submissions_context
    repository = client.app.state.activity_submission_repository
    activity_id = f"atividade-indice-{ObjectId()}"
    document = {"activity_id": activity_id, "student_id": student_id, "content": "{}"}
    try:
        repository.insert(dict(document))
        with pytest.raises(DuplicateSubmissionError):
            repository.insert(dict(document))
        assert db.activity_submissions.count_documents({"activity_id": activity_id}) == 1
        assert "submissions_activity_student_unique" in db.activity_submissions.index_information()
    finally:
        db.activity_submissions.delete_many({"activity_id": activity_id})
