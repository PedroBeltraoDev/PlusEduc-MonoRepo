from fastapi import APIRouter, Depends, Request, Response, status

from app.core.auth import UserPrincipal
from app.dependencies import get_current_user
from app.schemas.teacher import TeacherCreateRequest, TeacherResponse, TeacherUpdateRequest
from app.services.teacher_service import TeacherService

router = APIRouter(prefix="/api/teachers", tags=["Teachers"])


def service(request: Request) -> TeacherService:
    return TeacherService(request.app.state.teacher_repository)


@router.post("", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).create(payload)


@router.get("", response_model=list[TeacherResponse])
def list_teachers(
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).list_active()


@router.get("/email/{email}", response_model=TeacherResponse)
def get_teacher_by_email(
    email: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).by_email(email)


@router.get("/subject/{subject}", response_model=list[TeacherResponse])
def get_teachers_by_subject(
    subject: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).by_subject(subject)


@router.get("/count", response_model=int)
def count_teachers(
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).count()


@router.get("/{teacher_id}", response_model=TeacherResponse)
def get_teacher(
    teacher_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).get(teacher_id)


@router.put("/{teacher_id}", response_model=TeacherResponse)
def update_teacher(
    teacher_id: str,
    payload: TeacherUpdateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).update(teacher_id, payload)


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(
    teacher_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    service(request).delete(teacher_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
