from fastapi import APIRouter, Depends, Request, Response, status

from app.core.audit_middleware import set_audit
from app.dependencies import get_current_user
from app.core.auth import UserPrincipal
from app.schemas.auth import (
    AuthenticationRequest,
    AuthenticationResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    ProfileUpdateRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    StudentRegistrationRequest,
    TeacherRegistrationPendingResponse,
    TeacherRegistrationRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])


def _service(request: Request) -> AuthService:
    return AuthService(
        request.app.state.user_repository,
        request.app.state.settings,
        request.app.state.teacher_repository,
        request.app.state.student_repository,
    )


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
    service = AuthService(
        request.app.state.user_repository,
        request.app.state.settings,
        request.app.state.teacher_repository,
        request.app.state.student_repository,
    )
    return service.update_profile(current_user, payload)


@router.post(
    "/register/student",
    response_model=AuthenticationResponse,
    response_model_exclude_none=True,
    summary="Cadastrar aluno com matrícula automática e emitir tokens",
)
def register_student(request: Request, payload: StudentRegistrationRequest) -> AuthenticationResponse:
    service = AuthService(
        request.app.state.user_repository,
        request.app.state.settings,
        request.app.state.teacher_repository,
        request.app.state.student_repository,
    )
    set_audit(request, actorEmail=payload.email)
    return service.register_student(payload)


@router.post(
    "/register/teacher",
    response_model=AuthenticationResponse | TeacherRegistrationPendingResponse,
    response_model_exclude_none=True,
    summary="Cadastro público de professor (fica pendente até um ADMIN aprovar)",
    description=(
        "Com `TEACHER_REGISTRATION_REQUIRES_APPROVAL=true` (padrão) a conta nasce pendente: a resposta é "
        "**202** com `status=PENDING_APPROVAL` e nenhum token; o login devolve 403 até um ADMIN aprovar em "
        "`POST /api/teachers/{id}/approve`. Com a opção desligada, a resposta é 200 com os tokens."
    ),
    responses={202: {"model": TeacherRegistrationPendingResponse, "description": "Cadastro aguardando aprovação"}},
)
def register_teacher(
    request: Request, response: Response, payload: TeacherRegistrationRequest
) -> AuthenticationResponse | TeacherRegistrationPendingResponse:
    set_audit(request, actorEmail=payload.email)
    result = _service(request).register_teacher(payload)
    if isinstance(result, TeacherRegistrationPendingResponse):
        response.status_code = status.HTTP_202_ACCEPTED
    return result


@router.post(
    "/refresh",
    response_model=AuthenticationResponse,
    response_model_exclude_none=True,
    summary="Renovar a sessão com o refresh token",
    description=(
        "Recebe o `refreshToken` do login e devolve um novo par de tokens. O token de acesso (8 h) não serve aqui, "
        "e o refresh token não abre as demais rotas. Conta excluída ou desativada recebe 401."
    ),
)
def refresh_session(request: Request, payload: RefreshTokenRequest) -> AuthenticationResponse:
    return _service(request).refresh(payload.refreshToken)


@router.post(
    "/change-password",
    response_model=ChangePasswordResponse,
    summary="Trocar a própria senha (usuário autenticado)",
    description="Exige a senha atual. A nova senha precisa ter de 6 a 100 caracteres e ser diferente da atual.",
)
def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    current_user: UserPrincipal = Depends(get_current_user),
) -> ChangePasswordResponse:
    set_audit(request, summary=f"Troca de senha de {current_user.email}")
    return _service(request).change_password(current_user, payload)


@router.post(
    "/login",
    response_model=AuthenticationResponse,
    response_model_exclude_none=True,
    summary="Autenticar usuário e emitir tokens",
)
def login(request: Request, payload: AuthenticationRequest) -> AuthenticationResponse:
    service = AuthService(
        request.app.state.user_repository,
        request.app.state.settings,
        request.app.state.teacher_repository,
        request.app.state.student_repository,
    )
    set_audit(request, actorEmail=payload.email)  # fica registrado mesmo se o login falhar
    response = service.login(payload)
    set_audit(request, actorName=response.name, actorRole=response.role, summary=f"Login de {payload.email}")
    return response


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Solicitar código de verificação para redefinição de senha",
)
def forgot_password(request: Request, payload: ForgotPasswordRequest) -> ForgotPasswordResponse:
    service = AuthService(
        request.app.state.user_repository,
        request.app.state.settings,
        request.app.state.teacher_repository,
        request.app.state.student_repository,
    )
    set_audit(request, actorEmail=payload.email)
    return service.request_password_reset(payload)


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Redefinir senha a partir do código de verificação",
)
def reset_password(request: Request, payload: ResetPasswordRequest) -> ResetPasswordResponse:
    service = AuthService(
        request.app.state.user_repository,
        request.app.state.settings,
        request.app.state.teacher_repository,
        request.app.state.student_repository,
    )
    set_audit(request, actorEmail=payload.email)
    return service.reset_password(payload)
