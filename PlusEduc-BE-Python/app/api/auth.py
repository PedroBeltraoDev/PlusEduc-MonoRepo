from fastapi import APIRouter, Depends, Request, Response, status

from app.core.audit_middleware import set_audit
from app.core.auth import UserPrincipal
from app.core.rate_limit import client_ip, limiter_of, too_many
from app.dependencies import get_current_user
from app.schemas.auth import (
    AuthenticationRequest,
    AuthenticationResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LogoutRequest,
    ProfileUpdateRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    StudentRegistrationRequest,
    TeacherRegistrationRequest,
    TeacherRegistrationResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def auth_service(request: Request) -> AuthService:
    return AuthService(
        request.app.state.user_repository,
        request.app.state.settings,
        request.app.state.teacher_repository,
        request.app.state.student_repository,
        refresh_repository=getattr(request.app.state, "refresh_token_repository", None),
    )


def _limit(request: Request, scope: str, identity: str, limit: int, window: int) -> None:
    limiter = limiter_of(request)
    if limiter is not None:
        limiter.check_and_hit(f"{scope}:{client_ip(request)}:{identity.strip().lower()}", limit, window)


@router.put(
    "/profile",
    response_model=AuthenticationResponse,
    response_model_exclude_none=True,
    summary="Atualizar perfil do usuário autenticado",
)
def update_profile(
    request: Request,
    payload: ProfileUpdateRequest,
    current_user: UserPrincipal = Depends(get_current_user),
) -> AuthenticationResponse:
    return auth_service(request).update_profile(current_user, payload)


@router.post(
    "/register/student",
    response_model=AuthenticationResponse,
    response_model_exclude_none=True,
    summary="Cadastrar aluno com matrícula automática e emitir tokens",
)
def register_student(request: Request, payload: StudentRegistrationRequest) -> AuthenticationResponse:
    settings = request.app.state.settings
    _limit(request, "register", "any", settings.registration_max_requests, settings.registration_window_seconds)
    set_audit(request, actorEmail=payload.email)
    return auth_service(request).register_student(payload)


@router.post(
    "/register/teacher",
    response_model=TeacherRegistrationResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Solicitar cadastro de professor (fica pendente até aprovação de um administrador)",
)
def register_teacher(request: Request, payload: TeacherRegistrationRequest) -> TeacherRegistrationResponse:
    settings = request.app.state.settings
    _limit(request, "register", "any", settings.registration_max_requests, settings.registration_window_seconds)
    set_audit(request, actorEmail=payload.email, summary=f"Pedido de cadastro de professor: {payload.email}")
    return auth_service(request).register_teacher(payload)


@router.post(
    "/login",
    response_model=AuthenticationResponse,
    response_model_exclude_none=True,
    summary="Autenticar usuário e emitir tokens",
)
def login(request: Request, payload: AuthenticationRequest) -> AuthenticationResponse:
    settings = request.app.state.settings
    limiter = limiter_of(request)
    key = f"login:{client_ip(request)}:{payload.email.strip().lower()}"
    if limiter is not None:
        retry = limiter.is_blocked(key, settings.login_max_failures, settings.login_window_seconds)
        if retry:
            raise too_many(retry)
    set_audit(request, actorEmail=payload.email)  # fica registrado mesmo se o login falhar
    try:
        response = auth_service(request).login(payload)
    except Exception:
        # Só as falhas contam para o bloqueio; quem acerta a senha não é penalizado.
        if limiter is not None:
            limiter.hit(key, settings.login_window_seconds)
        raise
    if limiter is not None:
        limiter.reset(key)
    set_audit(request, actorName=response.name, actorRole=response.role, summary=f"Login de {payload.email}")
    return response


@router.post(
    "/refresh",
    response_model=AuthenticationResponse,
    response_model_exclude_none=True,
    summary="Renovar o access token (o refresh token é rotacionado a cada uso)",
)
def refresh(request: Request, payload: RefreshTokenRequest) -> AuthenticationResponse:
    return auth_service(request).refresh(payload.refreshToken)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Encerrar a sessão (revoga o refresh token)")
def logout(request: Request, payload: LogoutRequest) -> Response:
    auth_service(request).logout(payload.refreshToken)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/change-password",
    response_model=AuthenticationResponse,
    response_model_exclude_none=True,
    summary="Trocar a senha do usuário autenticado (encerra as outras sessões)",
)
def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    current_user: UserPrincipal = Depends(get_current_user),
) -> AuthenticationResponse:
    settings = request.app.state.settings
    _limit(request, "change-password", current_user.email, settings.login_max_failures, settings.login_window_seconds)
    response = auth_service(request).change_password(current_user, payload)
    set_audit(request, summary="Senha alterada pelo próprio usuário")
    return response


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Solicitar código de verificação para redefinição de senha",
)
def forgot_password(request: Request, payload: ForgotPasswordRequest) -> ForgotPasswordResponse:
    settings = request.app.state.settings
    _limit(request, "forgot", payload.email, settings.password_reset_max_requests, settings.password_reset_window_seconds)
    set_audit(request, actorEmail=payload.email)
    return auth_service(request).request_password_reset(payload)


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Redefinir senha a partir do código de verificação",
)
def reset_password(request: Request, payload: ResetPasswordRequest) -> ResetPasswordResponse:
    settings = request.app.state.settings
    _limit(request, "reset", payload.email, settings.password_reset_max_requests * 2, settings.password_reset_window_seconds)
    set_audit(request, actorEmail=payload.email)
    return auth_service(request).reset_password(payload)
