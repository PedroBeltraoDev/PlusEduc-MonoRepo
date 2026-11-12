from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.access import AccessScope, staff_scope
from app.core.audit_middleware import set_audit
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


def _student_name(request: Request, student_id: str) -> str:
    return (request.app.state.student_repository.find_by_id(student_id) or {}).get("name", "Aluno")


def _classroom_name(request: Request, classroom_id: str) -> str:
    return (request.app.state.classroom_repository.find_by_id(classroom_id) or {}).get("name", classroom_id)


def _visible(items: list[ClassroomResponse], scope: AccessScope) -> list[ClassroomResponse]:
    return items if scope.is_admin else [item for item in items if scope.can_access_classroom(item.id)]


def _require_titular(request: Request, classroom_id: str, scope: AccessScope) -> None:
    """Excluir a turma ou trocar o titular: só o professor titular (ou o ADMIN)."""
    scope.require_classroom(classroom_id)
    if scope.is_admin:
        return
    classroom = request.app.state.classroom_repository.find_by_id(classroom_id) or {}
    if str(classroom.get("teacher_id", classroom.get("teacherId", ""))) != scope.teacher_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Apenas o professor titular pode realizar esta ação")


@router.post("", response_model=ClassroomResponse, status_code=status.HTTP_201_CREATED)
def create_classroom(payload: ClassroomCreateRequest, request: Request, scope: AccessScope = Depends(staff_scope)):
    if not scope.is_admin:
        # Professor cria turma somente para si mesmo.
        payload = payload.model_copy(update={"teacherId": scope.teacher_id})
    created = service(request).create(payload, scope.principal)
    set_audit(request, entityId=created.id, summary=f"Turma “{created.name}” criada", details={"name": created.name, "year": created.year})
    return created


@router.get("", response_model=list[ClassroomResponse])
def list_classrooms(request: Request, scope: AccessScope = Depends(staff_scope)):
    return service(request).list_scoped(scope)


@router.get("/paginated", response_model=ClassroomPageResponse)
def list_classrooms_paginated(
    request: Request,
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    sort: str | None = None,
    scope: AccessScope = Depends(staff_scope),
):
    return service(request).page(page, size, scope)


@router.get("/teacher/{teacher_id}", response_model=list[ClassroomResponse])
def classrooms_by_teacher(teacher_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    if not scope.is_admin and teacher_id != scope.teacher_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Você só pode consultar as próprias turmas")
    return service(request).by_teacher(teacher_id)


@router.get("/student/{student_id}", response_model=list[ClassroomResponse])
def classrooms_by_student(student_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    return _visible(service(request).by_student(student_id), scope)


@router.get("/year/{year}", response_model=list[ClassroomResponse])
def classrooms_by_year(year: int, request: Request, scope: AccessScope = Depends(staff_scope)):
    return _visible(service(request).by_year(year), scope)


@router.get("/{classroom_id}/performance", response_model=ClassroomPerformanceResponse)
def classroom_performance(classroom_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_classroom(classroom_id)
    return service(request).performance(classroom_id)


@router.get("/{classroom_id}", response_model=ClassroomResponse)
def get_classroom(classroom_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_classroom(classroom_id)
    return service(request).get(classroom_id)


@router.put("/{classroom_id}", response_model=ClassroomResponse)
def update_classroom(
    classroom_id: str,
    payload: ClassroomUpdateRequest,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    scope.require_classroom(classroom_id)
    values = payload.model_dump(exclude_unset=True)
    if "teacherId" in values and not scope.is_admin:
        current = request.app.state.classroom_repository.find_by_id(classroom_id) or {}
        if str(values["teacherId"]) != str(current.get("teacher_id", current.get("teacherId", ""))):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Somente o administrador pode trocar o professor titular")
    if "studentIds" in values and not scope.is_admin:
        _require_students_movable(request, scope, values["studentIds"] or [], classroom_id)
    updated = service(request).update(classroom_id, payload)
    set_audit(request, summary=f"Turma “{updated.name}” alterada", details={"fields": sorted(values)})
    return updated


@router.delete("/{classroom_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_classroom(classroom_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    _require_titular(request, classroom_id, scope)
    before = service(request).get(classroom_id)
    service(request).delete(classroom_id)
    set_audit(request, summary=f"Turma “{before.name}” excluída", details={"name": before.name})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _require_students_movable(request: Request, scope: AccessScope, student_ids: list[str], classroom_id: str) -> None:
    """Professor só traz para a turma alunos sem turma ou que já estão nas turmas dele."""
    found = request.app.state.student_repository.find_by_ids(student_ids)
    for student_id in student_ids:
        student = found.get(str(student_id))
        if student is None:
            continue  # o serviço responde 400 para alunos inexistentes
        if not scope.can_access_student(student, allow_unassigned=True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Aluno matriculado em turma de outro professor; a transferência deve ser feita pelo administrador",
            )


@router.post("/{classroom_id}/enroll/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def enroll_student(classroom_id: str, student_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_classroom(classroom_id)
    if not scope.is_admin:
        _require_students_movable(request, scope, [student_id], classroom_id)
    service(request).enroll(classroom_id, student_id)
    set_audit(request, summary=f"{_student_name(request, student_id)} matriculado(a) na turma {_classroom_name(request, classroom_id)}", details={"studentId": student_id, "classroomId": classroom_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{classroom_id}/unenroll/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
def unenroll_student(classroom_id: str, student_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_classroom(classroom_id)
    service(request).unenroll(classroom_id, student_id)
    set_audit(request, summary=f"{_student_name(request, student_id)} removido(a) da turma {_classroom_name(request, classroom_id)}", details={"studentId": student_id, "classroomId": classroom_id})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
