from fastapi import APIRouter, Depends, Request, Response, status

from app.core.auth import UserPrincipal
from app.dependencies import get_current_user, require_roles
from app.schemas.grade import (
    GradeAverageResponse,
    GradeCreateRequest,
    GradeResponse,
    GradeUpdateRequest,
)
from app.services.grade_service import GradeService

router = APIRouter(prefix="/api/grades", tags=["Grades"])


def service(request: Request) -> GradeService:
    return GradeService(
        request.app.state.grade_repository,
        request.app.state.student_repository,
        request.app.state.classroom_repository,
    )


@router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def create_grade(
    payload: GradeCreateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return service(request).create(payload, current_user)


@router.get("", response_model=list[GradeResponse])
def list_grades(
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).list_all()


@router.get("/student/{student_id}/average", response_model=float)
def average_by_student(
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).average_by_student(student_id)


@router.get("/student/{student_id}", response_model=list[GradeResponse])
def grades_by_student(
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).by_student(student_id)


@router.get("/classroom/{classroom_id}", response_model=list[GradeResponse])
def grades_by_classroom(
    classroom_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).by_classroom(classroom_id)


@router.get("/{grade_id}", response_model=GradeResponse)
def get_grade(
    grade_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).get(grade_id)


@router.put("/{grade_id}", response_model=GradeResponse)
def update_grade(
    grade_id: str,
    payload: GradeUpdateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return service(request).update(grade_id, payload, current_user)


@router.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(
    grade_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    service(request).delete(grade_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
