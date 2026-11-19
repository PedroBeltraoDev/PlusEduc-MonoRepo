import hmac
import logging
import secrets
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.auth import UserPrincipal, principal_from_document
from app.core.config import Settings
from app.core.jwt import REFRESH_TOKEN, TokenError, create_access_token, create_refresh_token, decode_token
from app.core.passwords import hash_password, verify_password
from app.repositories.student_repository import StudentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AuthenticationRequest,
    AuthenticationResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ProfileUpdateRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    StudentRegistrationRequest,
    TeacherRegistrationPendingResponse,
    TeacherRegistrationRequest,
)
from app.services.email_service import EmailDeliveryError, EmailService

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS_MESSAGE = "Invalid email or password"
PENDING_APPROVAL_MESSAGE = "Seu cadastro de professor aguarda a aprovação de um administrador."
INVALID_REFRESH_MESSAGE = "Sessão expirada. Entre novamente."
STUDENT_ALREADY_REGISTERED_MESSAGE = (
    "Este e-mail já pertence a um aluno cadastrado pela escola. Peça ao professor para liberar seu acesso ao portal."
)
TEACHER_PENDING_REGISTRATION_MESSAGE = (
    "Cadastro recebido. Um administrador precisa aprovar seu acesso antes do primeiro login."
)
GENERIC_RESET_REQUEST_MESSAGE = "Se o e-mail informado existir, um código de verificação foi enviado."
INVALID_RESET_CODE_MESSAGE = "Código inválido ou expirado"
MAX_PASSWORD_RESET_ATTEMPTS = 5

# Modo de demonstração local (PASSWORD_RESET_DEMO_MODE=true): nenhum e-mail é enviado, o código
# é fixo e devolvido na própria resposta para a equipe apresentar o fluxo completo (inclusive a
# troca real de senha no banco) sem SMTP. Desligado por padrão: ver Settings.password_reset_demo_mode.
DEMO_PASSWORD_RESET_CODE = "123456"


class AuthService:
    def __init__(
        self,
        repository: UserRepository,
        settings: Settings,
        teacher_repository: TeacherRepository | None = None,
        student_repository: StudentRepository | None = None,
        email_service: EmailService | None = None,
        refresh_repository=None,
    ) -> None:
        self._refresh_repository = refresh_repository
        self._repository = repository
        self._settings = settings
        self._teacher_repository = teacher_repository
        self._student_repository = student_repository
        self._email_service = email_service or EmailService(settings)

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
        if current_user.role == "STUDENT" and self._student_repository and current_user.student_id:
            # E-mail e nome do aluno ficam iguais nas coleções users e students.
            self._student_repository.update(
                current_user.student_id,
                {"name": request.name, "email": normalized_email, "updated_at": datetime.now(timezone.utc)},
            )
        return self._authentication_response(self._display_principal(updated, teacher_override=teacher), updated)

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

    def _authentication_response(
        self,
        principal: UserPrincipal,
        user: dict | None = None,
        family: str | None = None,
    ) -> AuthenticationResponse:
        version = int((user or {}).get("tokenVersion", 0) or 0)
        refresh_token = create_refresh_token(principal.email, self._settings, version, family)
        self._register_refresh(refresh_token)
        return AuthenticationResponse(
            accessToken=create_access_token(principal.email, self._settings, version),
            refreshToken=refresh_token,
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
        # Aluno já cadastrado pela escola (sem login): o autocadastro criaria um segundo registro, fora da turma.
        # O acesso desse aluno é liberado pelo professor (POST /api/students/{id}/enable-access).
        existing = self._student_repository.find_by_email(normalized_email)
        if existing and existing.get("active") is not False and not existing.get("user_id"):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=STUDENT_ALREADY_REGISTERED_MESSAGE)

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
        return self._authentication_response(self._display_principal(user), user)

    def register_teacher(
        self, request: TeacherRegistrationRequest
    ) -> AuthenticationResponse | TeacherRegistrationPendingResponse:
        if not self._teacher_repository:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Teacher repository is not configured",
            )

        normalized_email = request.email.lower()
        find_any = getattr(self._repository, "find_by_email", self._repository.find_active_by_email)
        if find_any(normalized_email) or self._teacher_repository.find_by_email(normalized_email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email já cadastrado",
            )

        now = datetime.now(timezone.utc)
        password_hash = hash_password(request.password)
        requires_approval = self._settings.teacher_registration_requires_approval
        teacher = None
        user_id = ""
        try:
            # A senha fica só em users (com bcrypt); o cadastro em teachers não guarda senha.
            user_id = self._repository.insert_teacher_user(
                normalized_email, password_hash, pending_approval=requires_approval, name=request.name
            )
            teacher = self._teacher_repository.insert(
                {
                    "name": request.name,
                    "email": normalized_email,
                    "subjects": request.subjects,
                    "classrooms": [],
                    # Pendente: fica fora das listas e não entra até o ADMIN aprovar (RF04).
                    "active": not requires_approval,
                    "approval_status": "PENDING" if requires_approval else "APPROVED",
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

        if requires_approval and teacher:
            return TeacherRegistrationPendingResponse(
                status="PENDING_APPROVAL",
                message=TEACHER_PENDING_REGISTRATION_MESSAGE,
                userEmail=normalized_email,
                name=request.name,
            )

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
        return self._authentication_response(self._display_principal(user, teacher_override=teacher), user)

    def login(self, request: AuthenticationRequest) -> AuthenticationResponse:
        email = request.email.strip().lower()
        user = self._repository.find_active_by_email(email) or self._repository.find_active_by_email(request.email)
        if not user or not verify_password(request.password, user.get("password", "")):
            self._raise_if_pending_approval(email, request.password)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=INVALID_CREDENTIALS_MESSAGE,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return self._authentication_response(self._display_principal(user), user)

    # ---- sessão: refresh rotativo, logout e troca de senha ---------------------------------
    def _register_refresh(self, refresh_token: str) -> None:
        if self._refresh_repository is None:
            return
        try:
            payload = decode_token(refresh_token, self._settings, REFRESH_TOKEN)
            self._refresh_repository.register(
                payload["jti"],
                str(payload["sub"]),
                str(payload["fam"]),
                datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc),
            )
        except Exception:  # noqa: BLE001 - sem registro, o refresh só não poderá ser usado
            logger.warning("Não foi possível registrar o refresh token emitido")

    def refresh(self, refresh_token: str) -> AuthenticationResponse:
        def invalid() -> HTTPException:
            return HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=INVALID_REFRESH_MESSAGE,
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            payload = decode_token(refresh_token, self._settings, REFRESH_TOKEN)
        except (TokenError, RuntimeError) as error:
            raise invalid() from error
        jti, family, subject = payload.get("jti"), payload.get("fam"), payload.get("sub")
        if not jti or not family or not subject or self._refresh_repository is None:
            raise invalid()

        record = self._refresh_repository.consume(str(jti))
        if record is None:
            # Token já usado ou revogado: possível roubo. Derruba toda a cadeia desse login.
            if self._refresh_repository.find(str(jti)) is not None:
                self._refresh_repository.revoke_family(str(family))
                logger.warning("Reuso de refresh token detectado; sessão revogada")
            raise invalid()

        user = self._repository.find_active_by_email(str(subject))
        if not user or int(payload.get("ver", 0) or 0) != int(user.get("tokenVersion", 0) or 0):
            self._refresh_repository.revoke_family(str(family))
            raise invalid()
        return self._authentication_response(self._display_principal(user), user, family=str(family))

    def logout(self, refresh_token: str | None) -> None:
        if not refresh_token or self._refresh_repository is None:
            return
        try:
            payload = decode_token(refresh_token, self._settings, REFRESH_TOKEN)
        except (TokenError, RuntimeError):
            return
        if payload.get("fam"):
            self._refresh_repository.revoke_family(str(payload["fam"]))

    def change_password(self, current_user: UserPrincipal, request: ChangePasswordRequest) -> AuthenticationResponse:
        """Troca de senha pelo próprio usuário autenticado (RF03): exige a senha atual."""
        user = self._repository.find_active_by_email(current_user.email)
        if not user or not verify_password(request.currentPassword, user.get("password", "")):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")
        if verify_password(request.newPassword, user.get("password", "")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A nova senha deve ser diferente da senha atual",
            )
        # update_password incrementa tokenVersion: todos os tokens já emitidos deixam de valer.
        self._repository.update_password(current_user.email, hash_password(request.newPassword))
        self._repository.clear_password_reset_code(current_user.email)
        self._revoke_refresh_tokens(current_user.email)
        updated = self._repository.find_active_by_email(current_user.email) or user
        # As outras sessões caem; esta recebe tokens novos e continua aberta.
        return self._authentication_response(self._display_principal(updated), updated)

    def _revoke_refresh_tokens(self, email: str) -> None:
        if self._refresh_repository is None:
            return
        try:
            self._refresh_repository.revoke_all_for(email)
        except Exception:  # noqa: BLE001
            logger.warning("Não foi possível revogar os refresh tokens da conta")

    def _raise_if_pending_approval(self, email: str, password: str) -> None:
        """Conta de professor ainda não aprovada: avisa, mas só para quem acertou a senha.

        Assim a mensagem não serve para descobrir quais e-mails têm cadastro pendente.
        """
        find_pending = getattr(self._repository, "find_pending_by_email", None)
        if not callable(find_pending):
            return
        pending = find_pending(email.lower())
        if pending and verify_password(password, pending.get("password", "")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=PENDING_APPROVAL_MESSAGE)

    def request_password_reset(self, request: ForgotPasswordRequest) -> ForgotPasswordResponse:
        normalized_email = request.email.lower()
        user = self._repository.find_active_by_email(normalized_email)
        demo_code = None
        if user:
            demo_mode = self._settings.password_reset_demo_mode
            code = DEMO_PASSWORD_RESET_CODE if demo_mode else f"{secrets.randbelow(1_000_000):06d}"
            expires_at = datetime.now(timezone.utc) + timedelta(
                minutes=self._settings.password_reset_code_ttl_minutes
            )
            self._repository.set_password_reset_code(
                normalized_email,
                self._hash_reset_code(normalized_email, code),
                expires_at,
            )
            if demo_mode:
                demo_code = code
            else:
                try:
                    self._email_service.send_password_reset_code(account_email=normalized_email, code=code)
                except EmailDeliveryError:
                    # A resposta continua genérica: não revela se a conta existe nem se o envio falhou.
                    logger.warning("Código de recuperação gerado, mas o e-mail não pôde ser enviado")
        return ForgotPasswordResponse(message=GENERIC_RESET_REQUEST_MESSAGE, demoCode=demo_code)

    def reset_password(self, request: ResetPasswordRequest) -> ResetPasswordResponse:
        normalized_email = request.email.lower()
        user = self._repository.find_active_by_email(normalized_email)
        code_hash = user.get("passwordResetCodeHash") if user else None
        expires_at = user.get("passwordResetExpiresAt") if user else None
        attempts = int(user.get("passwordResetAttempts", 0)) if user else 0

        if not user or not code_hash or not expires_at or attempts >= MAX_PASSWORD_RESET_ATTEMPTS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_RESET_CODE_MESSAGE)

        expected_hash = self._hash_reset_code(normalized_email, request.code)
        if self._is_expired(expires_at) or not hmac.compare_digest(expected_hash, code_hash):
            self._repository.register_password_reset_attempt(normalized_email)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=INVALID_RESET_CODE_MESSAGE)

        self._repository.update_password(normalized_email, hash_password(request.newPassword))
        self._repository.clear_password_reset_code(normalized_email)
        # Senha redefinida: todas as sessões abertas (inclusive de quem roubou a conta) são encerradas.
        self._revoke_refresh_tokens(normalized_email)
        return ResetPasswordResponse(message="Senha redefinida com sucesso")

    def _hash_reset_code(self, email: str, code: str) -> str:
        key = self._settings.jwt_secret.encode("utf-8")
        message = f"{email}:{code}".encode("utf-8")
        return hmac.new(key, message, "sha256").hexdigest()

    @staticmethod
    def _is_expired(expires_at: datetime) -> bool:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) >= expires_at
