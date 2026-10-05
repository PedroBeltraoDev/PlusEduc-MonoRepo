"""Testes do módulo Notas e Frequência (Sprint 6) contra o MongoDB real (escola_db)."""
import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.auth import UserPrincipal
from app.core.config import Settings
from app.dependencies import get_current_user
from app.main import create_app

TEACHER = UserPrincipal(user_id="grades-module-teacher", email="teacher-grades-module@local", role="TEACHER")


@pytest.fixture
def module_context():
    settings = Settings(
        app_env="test-grades-module",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_database="escola_db",
        mongodb_required=True,
        mongodb_server_selection_timeout_ms=3000,
        mongodb_connect_timeout_ms=3000,
        jwt_secret="test-grades-module-secret",
    )
    mongo = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000, connectTimeoutMS=3000)
    try:
        mongo.admin.command("ping")
        db = mongo[settings.mongodb_database]
        students = list(db.students.find({
            "active": {"$ne": False},
            "$or": [{"class_id": {"$nin": [None, ""]}}, {"classId": {"$nin": [None, ""]}}],
        }).limit(2))
        if len(students) < 2:
            pytest.fail("São necessários ao menos 2 alunos ativos matriculados em escola_db")
        student = students[0]
        student_id = str(student["_id"])
        classroom_id = str(student.get("class_id") or student.get("classId"))
        other_student_id = str(students[1]["_id"])
        app = create_app(settings)
        app.dependency_overrides[get_current_user] = lambda: TEACHER
        with TestClient(app) as client:
            yield client, db, student_id, classroom_id, other_student_id
    finally:
        mongo.close()


def as_student(client, student_id):
    user = UserPrincipal(user_id=student_id, email="student-grades-module@local", role="STUDENT", student_id=student_id)
    client.app.dependency_overrides[get_current_user] = lambda: user


def as_teacher(client):
    client.app.dependency_overrides[get_current_user] = lambda: TEACHER


def test_classroom_summary_matches_real_grades(module_context):
    client, db, student_id, classroom_id, _ = module_context
    created = client.post("/api/grades", json={
        "studentId": student_id, "classroomId": classroom_id, "grade": 6.5, "attendance": False,
        "subject": "Disciplina Resumo Teste", "activityType": "EXAM", "date": "2026-06-02T10:00:00Z",
    })
    assert created.status_code == 201
    grade_id = created.json()["id"]
    try:
        filtered = client.get(f"/api/grades/classroom/{classroom_id}/summary", params={"subject": "disciplina resumo teste"})
        assert filtered.status_code == 200
        payload = filtered.json()
        assert payload["classroomId"] == classroom_id
        assert payload["totalLaunches"] == 1
        assert payload["averageGrade"] == 6.5
        assert payload["attendanceRate"] == 0
        row = next(item for item in payload["students"] if item["studentId"] == student_id)
        assert (row["launches"], row["absences"], row["attendedClasses"], row["totalClasses"]) == (1, 1, 0, 1)

        full = client.get(f"/api/grades/classroom/{classroom_id}/summary").json()
        real = list(db.grades.find({"classroomId": classroom_id, "studentId": student_id}))
        full_row = next(item for item in full["students"] if item["studentId"] == student_id)
        assert full_row["launches"] == len(real)
        expected_average = sum(float(g.get("grade", g.get("gradeValue")) or 0) for g in real) / len(real)
        assert full_row["average"] == pytest.approx(expected_average, abs=0.01)
    finally:
        assert client.delete(f"/api/grades/{grade_id}").status_code == 204
    assert client.get("/api/grades/classroom/turma-inexistente/summary").status_code in (400, 404)


def test_attendance_ignores_launches_without_recorded_presence(module_context):
    client, _, student_id, classroom_id, _ = module_context
    before = client.get(f"/api/students/{student_id}/attendance").json()
    created = client.post("/api/grades", json={
        "studentId": student_id, "classroomId": classroom_id, "grade": 9, "subject": "Sem presença",
        "activityType": "ASSIGNMENT", "date": "2026-06-03T10:00:00Z",
    })
    assert created.status_code == 201
    try:
        assert client.get(f"/api/students/{student_id}/attendance").json() == before
    finally:
        assert client.delete(f"/api/grades/{created.json()['id']}").status_code == 204


def test_students_cannot_read_or_write_grades_outside_the_portal(module_context):
    client, _, student_id, classroom_id, other_id = module_context
    as_student(client, student_id)
    for path in (
        "/api/grades",
        f"/api/grades/student/{student_id}",
        f"/api/grades/student/{student_id}/average",
        f"/api/grades/classroom/{classroom_id}",
        f"/api/grades/classroom/{classroom_id}/summary",
    ):
        assert client.get(path).status_code == 403, path
    body = {"studentId": student_id, "classroomId": classroom_id, "grade": 10, "date": "2026-06-01T10:00:00Z"}
    assert client.post("/api/grades", json=body).status_code == 403
    assert client.post("/api/grades/from-activity/qualquer").status_code == 403
    # Dados analíticos: o aluno só enxerga os próprios.
    assert client.get(f"/api/students/{student_id}/attendance").status_code == 200
    assert client.get(f"/api/students/{student_id}/performance").status_code == 200
    assert client.get(f"/api/students/{other_id}/attendance").status_code == 403
    assert client.get(f"/api/students/{other_id}/performance").status_code == 403


def test_launch_grades_from_activity_submissions(module_context):
    client, db, student_id, classroom_id, _ = module_context
    activity = client.post("/api/activities", json={
        "title": "Atividade Temporária Lançamento de Notas", "subject": "Matemática", "topic": "Somas",
        "difficultyLevel": "MEDIO", "questionsCount": 2, "format": "MULTIPLA_ESCOLHA",
        "classroomId": classroom_id, "studentId": student_id, "disabilityAdaptations": [],
        "questions": [
            {"questionText": "2 + 2?", "questionType": "MULTIPLA_ESCOLHA", "options": ["3", "4"], "correctAnswer": "4", "explanation": "x"},
            {"questionText": "3 + 3?", "questionType": "MULTIPLA_ESCOLHA", "options": ["5", "6"], "correctAnswer": "6", "explanation": "x"},
        ],
    })
    assert activity.status_code == 201
    activity_id = activity.json()["id"]
    try:
        first = client.post(f"/api/grades/from-activity/{activity_id}")
        assert first.status_code == 200
        assert first.json()["launched"] == 0 and first.json()["notSubmitted"] == 1

        as_student(client, student_id)
        submitted = client.post(f"/api/student-portal/activities/{activity_id}/submissions", json={
            "answers": [{"questionIndex": 0, "selectedAnswer": "4"}, {"questionIndex": 1, "selectedAnswer": "5"}],
        })
        assert submitted.status_code == 200 and submitted.json()["scorePercent"] == 50
        as_teacher(client)

        launched = client.post(f"/api/grades/from-activity/{activity_id}").json()
        assert launched["launched"] == 1 and launched["alreadyLaunched"] == 0

        grade = db.grades.find_one({"activityId": activity_id, "studentId": student_id})
        assert grade is not None and grade["grade"] == 5.0 and grade["subject"] == "Matemática"
        assert "attendance" not in grade  # lançamento por atividade não altera a frequência

        again = client.post(f"/api/grades/from-activity/{activity_id}").json()
        assert again["launched"] == 0 and again["alreadyLaunched"] == 1
        assert db.grades.count_documents({"activityId": activity_id}) == 1

        as_student(client, student_id)
        portal = client.get("/api/student-portal/grades").json()
        assert any(item.get("activityId") == activity_id and item["grade"] == 5.0 for item in portal)
    finally:
        as_teacher(client)
        db.grades.delete_many({"activityId": activity_id})
        db.activity_submissions.delete_many({"activity_id": activity_id})
        client.delete(f"/api/activities/{activity_id}")
    assert client.post(f"/api/grades/from-activity/{ObjectId()}").status_code == 404
