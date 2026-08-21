from fastapi import APIRouter, Depends, Request

from app.dependencies import get_current_user
from app.core.auth import UserPrincipal
from app.schemas.auth import (
    AuthenticationRequest,
    AuthenticationResponse,
    ProfileUpdateRequest,
    StudentRegistrationRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


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
    return service.register_student(payload)


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
    return service.login(payload)
