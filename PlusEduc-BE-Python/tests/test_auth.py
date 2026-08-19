from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.auth import principal_from_document
from app.core.jwt import create_access_token
from app.dependencies import get_current_user, require_roles


def test_valid_teacher_login_has_exact_base_contract(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "teacher@example.com", "password": "correct-password"},
    )

    assert response.status_code == 200
    assert set(response.json()) == {
        "accessToken",
        "refreshToken",
        "tokenType",
        "expiresIn",
        "userId",
        "userEmail",
        "role",
        "name",
    }
    assert response.json()["tokenType"] == "Bearer"
    assert response.json()["expiresIn"] == 28_800
    assert response.json()["userId"] == "teacher-1"
    assert response.json()["userEmail"] == "teacher@example.com"
    assert response.json()["role"] == "TEACHER"
    assert response.json()["name"] == "Professora Teste"


def test_valid_student_login_includes_optional_student_metadata(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "student@example.com", "password": "correct-password"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["studentId"] == "student-profile-1"
    assert payload["name"] == "Aluno Teste"
    assert payload["role"] == "STUDENT"


def test_wrong_password_is_rejected(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "teacher@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid email or password"


def test_unknown_user_is_rejected(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "unknown@example.com", "password": "correct-password"},
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Invalid email or password"


def test_jwt_is_bearer_compatible_and_subject_is_email(client, settings):
    response = client.post(
        "/api/auth/login",
        json={"email": "teacher@example.com", "password": "correct-password"},
    )
    access_token = response.json()["accessToken"]
    claims = jwt.decode(access_token, settings.jwt_secret, algorithms=["HS256"])

    assert claims["sub"] == "teacher@example.com"
    assert "role" not in claims


def test_valid_jwt_and_role_dependency_return_authenticated_user(settings, fake_repository):
    token = create_access_token("teacher@example.com", settings)
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(settings=settings, user_repository=fake_repository)
        )
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    principal = get_current_user(request, credentials)

    assert principal.email == "teacher@example.com"
    assert principal.role == "TEACHER"
    assert require_roles("TEACHER")(principal) is principal


def test_invalid_jwt_is_rejected(settings, fake_repository):
    request = SimpleNamespace(
        app=SimpleNamespace(
            state=SimpleNamespace(settings=settings, user_repository=fake_repository)
        )
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")

    with pytest.raises(HTTPException) as error:
        get_current_user(request, credentials)

    assert error.value.status_code == 401


def test_principal_preserves_student_metadata():
    principal = principal_from_document(
        {
            "_id": "user-1",
            "email": "student@example.com",
            "role": "STUDENT",
            "student_id": "student-1",
            "name": "Aluno",
        }
    )

    assert principal.student_id == "student-1"
    assert principal.role == "STUDENT"


def test_authenticated_user_can_update_profile(client):
    login_response = client.post(
        "/api/auth/login",
        json={"email": "teacher@example.com", "password": "correct-password"},
    )
    access_token = login_response.json()["accessToken"]

    response = client.put(
        "/api/auth/profile",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": "Professora Atualizada", "email": "professora.atualizada@example.com"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["userEmail"] == "professora.atualizada@example.com"
    assert payload["name"] == "Professora Atualizada"
    assert payload["role"] == "TEACHER"
    assert payload["accessToken"]


def test_profile_update_rejects_email_used_by_another_user(client):
    login_response = client.post(
        "/api/auth/login",
        json={"email": "teacher@example.com", "password": "correct-password"},
    )
    access_token = login_response.json()["accessToken"]

    response = client.put(
        "/api/auth/profile",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"name": "Professora", "email": "student@example.com"},
    )

    assert response.status_code == 409
    assert response.json()["message"] == "Email already in use"


def test_profile_update_requires_authentication(client):
    response = client.put(
        "/api/auth/profile",
        json={"name": "Sem Token", "email": "sem.token@example.com"},
    )

    assert response.status_code == 401
    assert response.json()["message"] == "Authentication required"


def test_teacher_login_uses_name_from_teacher_profile(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "teacher@example.com", "password": "correct-password"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Professora Teste"
