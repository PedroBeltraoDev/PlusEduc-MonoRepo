from dataclasses import replace
from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.auth import UserPrincipal, principal_from_document
from app.core.config import Settings
from app.core.jwt import create_access_token, create_refresh_token
from app.core.passwords import verify_password
from app.repositories.teacher_repository import TeacherRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import AuthenticationRequest, AuthenticationResponse, ProfileUpdateRequest

INVALID_CREDENTIALS_MESSAGE = "Invalid email or password"


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        settings: Settings,
        teacher_repository: TeacherRepository | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._teacher_repository = teacher_repository

    def update_profile(self, current_user: UserPrincipal, request: ProfileUpdateRequest) -> AuthenticationResponse:
        current_email = current_user.email
        normalized_email = request.email.lower()
        existing = self._repository.find_active_by_email(normalized_email)
        if existing and str(existing.get("email", "")).lower() != current_email.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")

        teacher = self._find_teacher(current_email)
        updated = self._repository.update_profile(current_email, request.name, normalized_email)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if teacher and self._teacher_repository:
            self._teacher_repository.update(
                str(teacher.get("_id")),
                {
                    "name": request.name,
                    "email": normalized_email,
                    "updated_at": datetime.now(timezone.utc),
                },
            )
            teacher = {**teacher, "name": request.name, "email": normalized_email}
        return self._authentication_response(self._display_principal(updated, teacher_override=teacher))

    def _find_teacher(self, email: str) -> dict | None:
        if not self._teacher_repository:
            return None
        return self._teacher_repository.find_active_by_email(email)

    def _display_principal(
        self,
        document: dict,
        teacher_override: dict | None = None,
    ) -> UserPrincipal:
        principal = principal_from_document(document)
        if principal.role != "TEACHER":
            return principal
        teacher = teacher_override or self._find_teacher(principal.email)
        teacher_name = teacher.get("name") if teacher else None
        if teacher_name:
            return replace(principal, name=str(teacher_name))
        return principal

    def _authentication_response(self, principal: UserPrincipal) -> AuthenticationResponse:
        return AuthenticationResponse(
            accessToken=create_access_token(principal.email, self._settings),
            refreshToken=create_refresh_token(principal.email, self._settings),
            tokenType="Bearer",
            expiresIn=self._settings.jwt_expiration_ms // 1000,
            userId=principal.user_id,
            userEmail=principal.email,
            role=principal.role,
            studentId=principal.student_id,
            name=principal.name,
        )

    def login(self, request: AuthenticationRequest) -> AuthenticationResponse:
        user = self._repository.find_active_by_email(request.email)
        if not user or not verify_password(request.password, user.get("password", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=INVALID_CREDENTIALS_MESSAGE,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._authentication_response(self._display_principal(user))
