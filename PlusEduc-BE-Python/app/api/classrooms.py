from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core.auth import UserPrincipal
from app.dependencies import get_current_user
from app.schemas.analytics import ClassroomPerformanceResponse
from app.schemas.classroom import (
    ClassroomCreateRequest,
    ClassroomPageResponse,
    ClassroomResponse,
    ClassroomUpdateRequest,
)
from app.services.classroom_service import ClassroomService

router = APIRouter(prefix="/api/classrooms", tags=["Classrooms"])


def service(request: Request) -> ClassroomService:
    return ClassroomService(
        request.app.state.classroom_repository,
        request.app.state.student_repository,
        request.app.state.teacher_repository,
        request.app.state.grade_repository,
    )


@router.post("", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
def create_classroom(
    payload: ClassroomCreateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).create(payload)


@router.get("", response_model=list[ClassroomResponse])
def list_classrooms(
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).list_active()


@router.get("/paginated", response_model=ClassroomPageResponse)
def list_classrooms_paginated(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    sort: str | None = None,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).page(page, size)


@router.get("/teacher/{teacher_id}", response_model=list[ClassroomResponse])
def classrooms_by_teacher(
    teacher_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).by_teacher(teacher_id)


@router.get("/student/{student_id}", response_model=list[ClassroomResponse])
def classrooms_by_student(
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).by_student(student_id)


@router.get("/year/{year}", response_model=list[ClassroomResponse])
def classrooms_by_year(
    year: int,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).by_year(year)


@router.get("/{classroom_id}/performance", response_model=ClassroomPerformanceResponse)
def classroom_performance(
    classroom_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).performance(classroom_id)


@router.get("/{classroom_id}", response_model=ClassroomResponse)
def get_classroom(
    classroom_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).get(classroom_id)


@router.put("/{classroom_id}", response_model=ClassroomResponse)
def update_classroom(
    classroom_id: str,
    payload: ClassroomUpdateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).update(classroom_id, payload)


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(
    classroom_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    service(request).delete(classroom_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{classroom_id}/enroll/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def enroll_student(
    classroom_id: str,
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    service(request).enroll(classroom_id, student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{classroom_id}/unenroll/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def unenroll_student(
    classroom_id: str,
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    service(request).unenroll(classroom_id, student_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
