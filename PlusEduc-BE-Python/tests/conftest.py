import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


class FakeTeacherRepository:
    def __init__(self, teachers: list[dict]):
        self._teachers = {teacher["email"]: teacher for teacher in teachers}

    def find_active_by_email(self, email: str):
        teacher = self._teachers.get(email)
        if teacher is None or teacher.get("active", True) is False:
            return None
        return teacher

    def update(self, teacher_id: str, updates: dict):
        for teacher in self._teachers.values():
            if str(teacher.get("_id")) == teacher_id:
                teacher.update(updates)
                return teacher
        return None


class FakeUserRepository:
    def __init__(self, users: list[dict]):
        self._users = {user["email"]: user for user in users}

    def find_active_by_email(self, email: str):
        user = self._users.get(email)
        if user is None or user.get("active", True) is False:
            return None
        return user

    def update_profile(self, current_email: str, name: str, email: str):
        user = self._users.pop(current_email)
        user["name"] = name
        user["email"] = email
        self._users[email] = user
        return user


@pytest.fixture
def user_documents() -> list[dict]:
    password_hash = bcrypt.hashpw(b"correct-password", bcrypt.gensalt()).decode()
    return [
        {
            "_id": "teacher-1",
            "email": "teacher@example.com",
            "password": password_hash,
            "role": "TEACHER",
            "active": True,
        },
        {
            "_id": "student-1",
            "email": "student@example.com",
            "password": password_hash,
            "role": "STUDENT",
            "active": True,
            "studentId": "student-profile-1",
            "name": "Aluno Teste",
        },
    ]


@pytest.fixture
def teacher_documents() -> list[dict]:
    return [
        {
            "_id": "teacher-1",
            "email": "teacher@example.com",
            "name": "Professora Teste",
            "active": True,
        }
    ]


@pytest.fixture
def settings() -> Settings:

    return Settings(
        app_env="test",
        jwt_secret="test-only-secret-that-is-not-production",
        mongodb_uri="mongodb://127.0.0.1:27018",
        mongodb_required=False,
        mongodb_server_selection_timeout_ms=50,
        mongodb_connect_timeout_ms=50,
    )


@pytest.fixture
def fake_repository(user_documents):
    return FakeUserRepository(user_documents)


@pytest.fixture
def fake_teacher_repository(teacher_documents):
    return FakeTeacherRepository(teacher_documents)


@pytest.fixture
def client(settings, fake_repository, fake_teacher_repository) -> TestClient:
    with TestClient(
        create_app(
            settings,
            user_repository=fake_repository,
            teacher_repository=fake_teacher_repository,
        )
    ) as test_client:
        yield test_client
