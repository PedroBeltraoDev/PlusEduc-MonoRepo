from fastapi import APIRouter, Depends, Query, Request, Response, status

from app.core.auth import UserPrincipal
from app.dependencies import require_roles
from app.schemas.subject_catalog import (
    SortField,
    SortOrder,
    SubjectAssignmentRequest,
    SubjectAssignmentResponse,
    SubjectClassroomResponse,
    SubjectCreateRequest,
    SubjectResponse,
    SubjectStudentPerformanceResponse,
    SubjectUpdateRequest,
)
from app.services.subject_catalog_service import SubjectCatalogService

router = APIRouter(prefix="/api/subjects", tags=["Subjects"])


def service(request: Request) -> SubjectCatalogService:
    return SubjectCatalogService(
        request.app.state.subject_repository,
        request.app.state.classroom_repository,
        request.app.state.grade_repository,
        request.app.state.student_repository,
        request.app.state.teacher_repository,
    )


teacher_user = require_roles("TEACHER", "ADMIN")


@router.get("", response_model=list[SubjectResponse])
def list_subjects(request: Request, current_user: UserPrincipal = Depends(teacher_user)):
    return service(request).list_subjects()


@router.get("/available", response_model=list[SubjectResponse])
def list_available_subjects(
    request: Request,
    classroomId: str = Query(min_length=1),
    current_user: UserPrincipal = Depends(teacher_user),
):
    return service(request).list_available_subjects(classroomId, current_user)


@router.post("/assignments", response_model=SubjectAssignmentResponse, status_code=status.HTTP_201_CREATED)
def assign_subject(
    payload: SubjectAssignmentRequest,
    request: Request,
    current_user: UserPrincipal = Depends(teacher_user),
):
    return service(request).assign_subject(payload, current_user)


@router.post("", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
def create_subject(payload: SubjectCreateRequest, request: Request, current_user: UserPrincipal = Depends(teacher_user)):
    return service(request).create_subject(payload)


@router.patch("/{subject_id}", response_model=SubjectResponse)
def update_subject(subject_id: str, payload: SubjectUpdateRequest, request: Request, current_user: UserPrincipal = Depends(teacher_user)):
    return service(request).update_subject(subject_id, payload)


@router.get("/{subject_id}/classrooms", response_model=list[SubjectClassroomResponse])
def classrooms_by_subject(subject_id: str, request: Request, current_user: UserPrincipal = Depends(teacher_user)):
    return service(request).classrooms_by_subject(subject_id, current_user)


@router.get("/{subject_id}/classrooms/{classroom_id}/performance", response_model=list[SubjectStudentPerformanceResponse])
def student_performance(
    subject_id: str,
    classroom_id: str,
    request: Request,
    sortBy: SortField = Query(default="name"),
    order: SortOrder = Query(default="asc"),
    current_user: UserPrincipal = Depends(teacher_user),
):
    return service(request).student_performance(subject_id, classroom_id, current_user, sortBy, order)


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_subject(subject_id: str, request: Request, current_user: UserPrincipal = Depends(teacher_user)):
    service(request).update_subject(subject_id, SubjectUpdateRequest(active=False))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
