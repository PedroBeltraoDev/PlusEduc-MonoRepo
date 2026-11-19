from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.access import AccessScope, staff_scope
from app.core.audit_middleware import set_audit
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


def _student_or_404(request: Request, student_id: str) -> dict:
    student = request.app.state.student_repository.find_by_id(student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Aluno não encontrado: {student_id}")
    return student


def _visible(items: list[StudentResponse], scope: AccessScope) -> list[StudentResponse]:
    if scope.is_admin:
        return items
    return [item for item in items if item.id in scope.member_ids or (item.classId or "") in scope.classroom_ids]


@router.post("", response_model=StudentResponse, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreateRequest, request: Request, scope: AccessScope = Depends(staff_scope)):
    if payload.classId:
        scope.require_classroom(payload.classId)
    created = service(request).create(payload, scope.principal)
    set_audit(request, entityId=created.id, summary=f"Aluno {created.name} cadastrado", details={"name": created.name})
    return created


@router.get("", response_model=list[StudentResponse])
def list_students(request: Request, scope: AccessScope = Depends(staff_scope)):
    return service(request).list_scoped(scope)


@router.get("/unassigned", response_model=list[StudentResponse])
def list_unassigned_students(request: Request, scope: AccessScope = Depends(staff_scope)):
    # Alunos sem turma ficam visíveis à equipe para poderem ser matriculados.
    return service(request).list_unassigned()


@router.get("/paginated", response_model=StudentPageResponse)
def list_students_paginated(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    sort: str | None = None,
    scope: AccessScope = Depends(staff_scope),
):
    return service(request).page(page, size, scope)


@router.get("/class/{class_id}", response_model=list[StudentResponse])
def list_students_by_class(class_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_classroom(class_id)
    return service(request).by_class(class_id)


@router.get("/learning-gap/{subject}", response_model=list[StudentResponse])
def list_students_by_learning_gap(subject: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    return _visible(service(request).by_learning_gap(subject), scope)


@router.get("/{student_id}", response_model=StudentResponse)
def get_student(student_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_student(_student_or_404(request, student_id), allow_unassigned=True)
    return service(request).get(student_id)


@router.put("/{student_id}", response_model=StudentResponse)
def update_student(
    student_id: str,
    payload: StudentUpdateRequest,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    scope.require_student(_student_or_404(request, student_id), allow_unassigned=True)
    values = payload.model_dump(exclude_unset=True)
    if values.get("classId"):
        scope.require_classroom(values["classId"])
    updated = service(request).update(student_id, payload, scope.principal)
    set_audit(request, summary=f"Aluno {updated.name} alterado", details={"fields": sorted(values)})
    return updated


@router.post("/{student_id}/enable-access", status_code=status.HTTP_204_NO_CONTENT)
def enable_student_access(
    student_id: str,
    payload: EnableStudentAccessRequest,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    scope.require_student(_student_or_404(request, student_id), allow_unassigned=True)
    service(request).enable_access(student_id, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_student(student_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_student(_student_or_404(request, student_id), allow_unassigned=True)
    before = service(request).get(student_id)
    service(request).delete(student_id)
    set_audit(request, summary=f"Aluno {before.name} excluído", details={"name": before.name})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
