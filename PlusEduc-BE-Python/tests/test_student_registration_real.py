from copy import deepcopy

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo import MongoClient

from app.core.config import get_settings
from app.core.passwords import hash_password, verify_password
from app.main import create_app

TEST_EMAIL = "cadastro.automatico@aluno.local"
TEST_PASSWORD = "Cadastro@123"
MATRICULA_PREFIX = "MAT-2026-"


def highest_demo_matricula(database) -> int:
    highest = 0
    for document in database.students.find({"matricula": {"$regex": f"^{MATRICULA_PREFIX}\\d+$"}}, {"matricula": 1}):
        value = str(document.get("matricula", ""))
        try:
            highest = max(highest, int(value[len(MATRICULA_PREFIX):]))
        except ValueError:
            continue
    return highest


@pytest.fixture
def registration_context():
    settings = get_settings()
    mongo_client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=3000)
    database = mongo_client[settings.mongodb_database]
    database.users.delete_many({"email": TEST_EMAIL})
    database.students.delete_many({"email": TEST_EMAIL})
    highest_before = highest_demo_matricula(database)

    with TestClient(create_app(settings)) as client:
        yield client, database, highest_before

    temporary_students = list(database.students.find({"email": TEST_EMAIL}, {"_id": 1}))
    temporary_student_ids = [str(student["_id"]) for student in temporary_students]
    if temporary_student_ids:
        database.classrooms.update_many(
            {"students": {"$in": temporary_student_ids}},
            {"$pull": {"students": {"$in": temporary_student_ids}}},
        )
    database.users.delete_many({"email": TEST_EMAIL})
    database.students.delete_many({"email": TEST_EMAIL})
    mongo_client.close()


def test_registration_generates_next_matricula_and_links_user_student(registration_context):
    client, database, highest_before = registration_context

    response = client.post(
        "/api/auth/register/student",
        json={
            "name": "Aluno Cadastro Automático",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "accessToken",
        "refreshToken",
        "tokenType",
        "expiresIn",
        "userId",
        "userEmail",
        "role",
        "studentId",
        "name",
    }
    assert payload["tokenType"] == "Bearer"
    assert payload["role"] == "STUDENT"
    assert payload["userEmail"] == TEST_EMAIL
    assert payload["name"] == "Aluno Cadastro Automático"

    persisted_student = database.students.find_one({"_id": ObjectId(payload["studentId"])})
    assert persisted_student is not None
    assert persisted_student["matricula"] == f"{MATRICULA_PREFIX}{highest_before + 1:04d}"
    assert "class_id" not in persisted_student
    assert "classId" not in persisted_student
    assert persisted_student["user_id"] == payload["userId"]

    persisted_user = database.users.find_one({"email": TEST_EMAIL})
    assert persisted_user is not None
    assert persisted_user["studentId"] == payload["studentId"]
    assert verify_password(TEST_PASSWORD, persisted_user["password"])

    login_response = client.post(
        "/api/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    assert login_response.status_code == 200
    assert login_response.json()["studentId"] == payload["studentId"]


def test_registration_rejects_manual_matricula_field(registration_context):
    client, _, _ = registration_context

    response = client.post(
        "/api/auth/register/student",
        json={
            "matricula": "MAT-2026-9999",
            "name": "Aluno Campo Proibido",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 422


def test_registration_rejects_duplicate_email_without_creating_second_student(registration_context):
    client, database, highest_before = registration_context

    first_response = client.post(
        "/api/auth/register/student",
        json={
            "name": "Primeiro Cadastro",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/api/auth/register/student",
        json={
            "name": "Segundo Cadastro",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )
    assert second_response.status_code == 409
    assert second_response.json()["message"] == "Email já cadastrado"
    assert database.students.count_documents({"email": TEST_EMAIL}) == 1
    student = database.students.find_one({"email": TEST_EMAIL})
    assert student["matricula"] == f"{MATRICULA_PREFIX}{highest_before + 1:04d}"


def test_teacher_can_list_students_without_class(registration_context):
    client, database, _ = registration_context
    teacher_email = "professor.fisica@professor.local"
    teacher_password = "Demo@123"

    register_response = client.post(
        "/api/auth/register/student",
        json={
            "name": "Aluno Sem Turma",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )
    assert register_response.status_code == 200
    created_student_id = register_response.json()["studentId"]

    login_response = client.post(
        "/api/auth/login",
        json={"email": teacher_email, "password": teacher_password},
    )
    assert login_response.status_code == 200

    response = client.get(
        "/api/students/unassigned",
        headers={"Authorization": f"Bearer {login_response.json()['accessToken']}"},
    )
    assert response.status_code == 200
    assert any(student["id"] == created_student_id for student in response.json())
    created_payload = next(student for student in response.json() if student["id"] == created_student_id)
    assert created_payload["matricula"].startswith(MATRICULA_PREFIX)
    assert created_payload["classId"] is None

    classroom = database.classrooms.find_one({"active": True})
    assert classroom is not None
    enroll_response = client.post(
        f"/api/classrooms/{classroom['_id']}/enroll/{created_student_id}",
        headers={"Authorization": f"Bearer {login_response.json()['accessToken']}"},
    )
    assert enroll_response.status_code == 204

    persisted_student = database.students.find_one({"_id": ObjectId(created_student_id)})
    assert persisted_student["class_id"] == str(classroom["_id"])
    after_link_response = client.get(
        "/api/students/unassigned",
        headers={"Authorization": f"Bearer {login_response.json()['accessToken']}"},
    )
    assert after_link_response.status_code == 200
    assert all(student["id"] != created_student_id for student in after_link_response.json())


def test_registration_cleanup_does_not_touch_existing_documents(registration_context):
    client, database, _ = registration_context
    before = deepcopy(database.students.find_one({"matricula": "MAT-2026-0001"}))

    response = client.post(
        "/api/auth/register/student",
        json={
            "name": "Aluno Temporário",
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
    )
    assert response.status_code == 200

    database.users.delete_many({"email": TEST_EMAIL})
    database.students.delete_many({"email": TEST_EMAIL})
    after = database.students.find_one({"matricula": "MAT-2026-0001"})
    assert after == before
