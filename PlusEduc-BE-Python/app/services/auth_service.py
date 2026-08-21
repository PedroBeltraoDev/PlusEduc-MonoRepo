from dataclasses import replace
from datetime import datetime, timezone

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.auth import UserPrincipal, principal_from_document
from app.core.config import Settings
from app.core.jwt import create_access_token, create_refresh_token
from app.core.passwords import hash_password, verify_password
from app.repositories.student_repository import StudentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AuthenticationRequest,
    AuthenticationResponse,
    ProfileUpdateRequest,
    StudentRegistrationRequest,
    TeacherRegistrationRequest,
)

INVALID_CREDENTIALS_MESSAGE = "Invalid email or password"


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        settings: Settings,
        teacher_repository: TeacherRepository | None = None,
        student_repository: StudentRepository | None = None,
    ) -> None:
        self._repository = repository
        self._settings = settings
        self._teacher_repository = teacher_repository
        self._student_repository = student_repository

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

    def _find_student(self, principal: UserPrincipal) -> dict | None:
        if not self._student_repository:
            return None
        if principal.student_id:
            student = self._student_repository.find_by_id(principal.student_id)
            if student:
                return student
        return self._student_repository.find_by_user_id_and_active(principal.user_id)

    def _display_principal(
        self,
        document: dict,
        teacher_override: dict | None = None,
    ) -> UserPrincipal:
        principal = principal_from_document(document)
        if principal.role == "STUDENT":
            if principal.name:
                return principal
            student = self._find_student(principal)
            if student:
                student_id = principal.student_id or str(student.get("_id", ""))
                student_name = student.get("name") or student.get("studentName")
                return replace(
                    principal,
                    student_id=student_id or principal.student_id,
                    name=str(student_name) if student_name else principal.name,
                )
            return principal
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

    def register_student(self, request: StudentRegistrationRequest) -> AuthenticationResponse:
        if not self._student_repository:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Student repository is not configured",
            )

        normalized_email = request.email.lower()
        if self._repository.find_active_by_email(normalized_email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já cadastrado",
            )

        student = None
        student_id = ""
        for _ in range(10):
            matricula = self._student_repository.next_matricula()
            try:
                student = self._student_repository.insert(
                    {
                        "name": request.name,
                        "email": normalized_email,
                        "matricula": matricula,
                        "active": True,
                        "learning_gaps": [],
                        "created_at": datetime.now(timezone.utc),
                        "updated_at": datetime.now(timezone.utc),
                        "created_by": "public-registration",
                        "updated_by": "public-registration",
                    }
                )
                student_id = str(student.get("_id", ""))
                break
            except DuplicateKeyError:
                continue

        if not student or not student_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Não foi possível gerar uma matrícula disponível",
            )

        try:
            user_id = self._repository.insert_student_user(
                normalized_email,
                hash_password(request.password),
                student_id,
            )
        except DuplicateKeyError as error:
            self._student_repository.delete_by_id(student_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já cadastrado",
            ) from error

        updated_student = self._student_repository.update(
            student_id,
            {"user_id": user_id, "updated_at": datetime.now(timezone.utc)},
        )
        if not updated_student:
            self._repository.delete_by_id(user_id)
            self._student_repository.delete_by_id(student_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Não foi possível vincular o usuário ao aluno",
            )

        user = self._repository.find_active_by_email(normalized_email)
        if not user:
            self._repository.delete_by_id(user_id)
            self._student_repository.delete_by_id(student_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Usuário criado, mas não pôde ser recuperado",
            )
        return self._authentication_response(self._display_principal(user))

    def register_teacher(self, request: TeacherRegistrationRequest) -> AuthenticationResponse:
        if not self._teacher_repository:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Teacher repository is not configured",
            )

        normalized_email = request.email.lower()
        if self._repository.find_active_by_email(normalized_email) or self._teacher_repository.find_by_email(normalized_email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já cadastrado",
            )

        now = datetime.now(timezone.utc)
        password_hash = hash_password(request.password)
        teacher = None
        user_id = ""
        try:
            user_id = self._repository.insert_teacher_user(normalized_email, password_hash)
            teacher = self._teacher_repository.insert(
                {
                    "name": request.name,
                    "email": normalized_email,
                    "password": password_hash,
                    "subjects": request.subjects,
                    "classrooms": [],
                    "active": True,
                    "created_at": now,
                    "updated_at": now,
                    "created_by": "public-registration",
                    "updated_by": "public-registration",
                }
            )
        except DuplicateKeyError as error:
            if user_id:
                self._repository.delete_by_id(user_id)
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email já cadastrado") from error
        except Exception:
            if user_id:
                self._repository.delete_by_id(user_id)
            raise

        user = self._repository.find_active_by_email(normalized_email)
        if not user or not teacher:
            if user_id:
                self._repository.delete_by_id(user_id)
            if teacher and teacher.get("_id"):
                self._teacher_repository.soft_delete(str(teacher["_id"]), datetime.now(timezone.utc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Professor criado, mas não pôde ser recuperado",
            )
        return self._authentication_response(self._display_principal(user, teacher_override=teacher))

    def login(self, request: AuthenticationRequest) -> AuthenticationResponse:
        user = self._repository.find_active_by_email(request.email)
        if not user or not verify_password(request.password, user.get("password", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=INVALID_CREDENTIALS_MESSAGE,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._authentication_response(self._display_principal(user))
