from datetime import datetime, timezone

import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.core.jwt import create_access_token
from app.main import create_app


class FakeStudentRepository:
    def __init__(self):
        self.items = [
            {
                "_id": "student-1",
                "name": "Aluno Um",
                "email": "aluno@example.com",
                "birth_date": "2010-01-01",
                "class_id": "class-1",
                "learning_gaps": [],
                "active": True,
            },
            {
                "_id": "student-inactive",
                "name": "Aluno Inativo",
                "email": "inativo@example.com",
                "birth_date": "2010-01-01",
                "class_id": "class-1",
                "learning_gaps": [],
                "active": False,
            },
        ]

    def find_by_email(self, email):
        return next((item for item in self.items if item.get("email") == email), None)

    def find_by_id(self, student_id):
        return next((item for item in self.items if str(item.get("_id")) == student_id), None)

    def find_active(self):
        return [item for item in self.items if item.get("active") is True]

    def find_active_by_class(self, class_id):
        return [item for item in self.find_active() if item.get("class_id") == class_id]

    def find_active_by_learning_gap_subject(self, subject):
        return [
            item for item in self.find_active()
            if any(subject.lower() in gap.get("subject", "").lower() for gap in item.get("learning_gaps", []))
        ]

    def insert(self, document):
        document["_id"] = "student-created"
        self.items.append(document)
        return document

    def update(self, student_id, updates):
        item = self.find_by_id(student_id)
        if item:
            item.update(updates)
        return item

    def soft_delete(self, student_id, updated_at):
        item = self.find_by_id(student_id)
        if not item:
            return False
        item["active"] = False
        item["updated_at"] = updated_at
        return True


class FakeTeacherRepository:
    def __init__(self):
        self.items = [
            {
                "_id": "teacher-1",
                "name": "Professor Um",
                "email": "prof@example.com",
                "password": "stored-test-password-value",
                "subjects": ["Matemática"],
                "classrooms": ["class-1"],
                "active": True,
            }
        ]

    def find_by_id(self, teacher_id):
        return next((item for item in self.items if str(item.get("_id")) == teacher_id), None)

    def find_by_email(self, email):
        return next((item for item in self.items if item.get("email") == email), None)

    def find_active(self):
        return [item for item in self.items if item.get("active") is True]

    def find_active_by_email(self, email):
        return next((item for item in self.find_active() if item.get("email") == email), None)

    def find_active_by_subject(self, subject):
        return [item for item in self.find_active() if subject in item.get("subjects", [])]

    def count_all(self):
        return len(self.items)

    def insert(self, document):
        document["_id"] = "teacher-created"
        self.items.append(document)
        return document

    def update(self, teacher_id, updates):
        item = self.find_by_id(teacher_id)
        if item:
            item.update(updates)
        return item

    def soft_delete(self, teacher_id, updated_at):
        item = self.find_by_id(teacher_id)
        if not item:
            return False
        item["active"] = False
        item["updated_at"] = updated_at
        return True


class FakeClassroomRepository:
    def exists_by_id(self, classroom_id):
        return classroom_id == "class-1"


class FakeUserRepository:
    def __init__(self):
        password_hash = bcrypt.hashpw(b"correct-password", bcrypt.gensalt()).decode()
        self.users = {
            "teacher@example.com": {
                "_id": "user-teacher",
                "email": "teacher@example.com",
                "password": password_hash,
                "role": "TEACHER",
                "active": True,
            }
        }
        self.created = []

    def find_active_by_email(self, email):
        user = self.users.get(email)
        if user and user.get("active", True):
            return user
        return None

    def insert_student_user(self, email, password_hash, student_id):
        user_id = "student-user-created"
        self.created.append((email, password_hash, student_id))
        self.users[email] = {
            "_id": user_id,
            "email": email,
            "password": password_hash,
            "role": "STUDENT",
            "studentId": student_id,
            "active": True,
        }
        return user_id


@pytest.fixture
def domain_context(settings):
    users = FakeUserRepository()
    students = FakeStudentRepository()
    teachers = FakeTeacherRepository()
    classrooms = FakeClassroomRepository()
    with TestClient(
        create_app(
            settings,
            user_repository=users,
            student_repository=students,
            teacher_repository=teachers,
            classroom_repository=classrooms,
        )
    ) as client:
        token = create_access_token("teacher@example.com", settings)
        yield client, {"Authorization": f"Bearer {token}"}, users, students, teachers


def test_student_create_validates_classroom_existence(domain_context):
    client, headers, _, _, _ = domain_context
    response = client.post(
        "/api/students",
        headers=headers,
        json={
            "name": "Novo Aluno",
            "email": "novo@example.com",
            "birthDate": "2011-02-03",
            "classId": "missing-class",
            "learningGaps": [],
        },
    )

    assert response.status_code == 400
    assert response.json()["message"] == "Turma não encontrada"


def test_student_crud_and_active_list(domain_context):
    client, headers, _, _, _ = domain_context
    response = client.post(
        "/api/students",
        headers=headers,
        json={
            "name": "Novo Aluno",
            "email": "novo@example.com",
            "birthDate": "2011-02-03",
            "classId": "class-1",
            "learningGaps": [
                {
                    "subject": "Matemática",
                    "topic": "Frações",
                    "severity": "HIGH",
                    "description": "Reforço",
                    "identifiedDate": "2024-01-01T00:00:00Z",
                }
            ],
        },
    )
    assert response.status_code == 201
    assert response.json()["id"] == "student-created"
    assert response.json()["classId"] == "class-1"

    listed = client.get("/api/students", headers=headers)
    assert listed.status_code == 200
    assert {item["email"] for item in listed.json()} == {"aluno@example.com", "novo@example.com"}


def test_student_enable_access_uses_bcrypt_and_creates_no_sample_user(domain_context):
    client, headers, users, students, _ = domain_context
    response = client.post(
        "/api/students/student-1/enable-access",
        headers=headers,
        json={"password": "portal-password"},
    )

    assert response.status_code == 204
    assert len(users.created) == 1
    email, password_hash, student_id = users.created[0]
    assert email == "aluno@example.com"
    assert bcrypt.checkpw(b"portal-password", password_hash.encode())
    assert student_id == "student-1"
    assert students.find_by_id("student-1")["user_id"] == "student-user-created"
    assert users.users[email]["studentId"] == "student-1"


def test_teacher_responses_never_serialize_password(domain_context):
    client, headers, _, _, _ = domain_context
    response = client.get("/api/teachers/teacher-1", headers=headers)

    assert response.status_code == 200
    assert "password" not in response.json()
    assert response.json()["email"] == "prof@example.com"


def test_teacher_management_and_count(domain_context):
    client, headers, _, _, _ = domain_context
    created = client.post(
        "/api/teachers",
        headers=headers,
        json={
            "name": "Professor Dois",
            "email": "prof2@example.com",
            "password": "stored-only",
            "subjects": ["História"],
            "classroomIds": [],
        },
    )
    assert created.status_code == 201
    assert "password" not in created.json()

    by_subject = client.get("/api/teachers/subject/Matemática", headers=headers)
    assert by_subject.status_code == 200
    assert all("password" not in item for item in by_subject.json())

    count = client.get("/api/teachers/count", headers=headers)
    assert count.status_code == 200
    assert count.json() == 2


def test_domain_write_requires_teacher_role(domain_context):
    client, _, _, _, _ = domain_context
    response = client.post(
        "/api/students",
        json={
            "name": "Sem Token",
            "email": "sem-token@example.com",
            "birthDate": "2011-02-03",
            "classId": "class-1",
        },
    )

    assert response.status_code == 401
