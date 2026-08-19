from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core.auth import UserPrincipal
from app.dependencies import get_current_user, require_roles
from app.schemas.student import (
    EnableStudentAccessRequest,
    StudentCreateRequest,
    StudentPageResponse,
    StudentResponse,
    StudentUpdateRequest,
)
from app.services.student_service import StudentService

router = APIRouter(prefix="/api/students", tags=["Students"])


def service(request: Request) -> StudentService:
    return StudentService(
        request.app.state.student_repository,
        request.app.state.classroom_repository,
        request.app.state.user_repository,
    )


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(
    payload: StudentCreateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER")),
):
    return service(request).create(payload, current_user)


@router.get("", response_model=list[StudentResponse])
def list_students(
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).list_active()


@router.get("/paginated", response_model=StudentPageResponse)
def list_students_paginated(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    sort: str | None = None,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).page(page, size)


@router.get("/class/{class_id}", response_model=list[StudentResponse])
def list_students_by_class(
    class_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).by_class(class_id)


@router.get("/learning-gap/{subject}", response_model=list[StudentResponse])
def list_students_by_learning_gap(
    subject: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).by_learning_gap(subject)


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).get(student_id)


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: str,
    payload: StudentUpdateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER")),
):
    return service(request).update(student_id, payload, current_user)


@router.post("/{student_id}/enable-access", status_code=status.HTTP_204_NO_CONTENT)
def enable_student_access(
    student_id: str,
    payload: EnableStudentAccessRequest,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER")),
):
    service(request).enable_access(student_id, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER")),
):
    service(request).delete(student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
