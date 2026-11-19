from fastapi import APIRouter, Depends, Request, Response, status

from fastapi import HTTPException

from app.core.access import AccessScope, staff_scope
from app.core.audit_middleware import set_audit
from app.schemas.grade import (
    ActivityGradesLaunchResponse,
    GradeAverageResponse,
    GradeClassroomSummaryResponse,
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
        request.app.state.activity_repository,
        request.app.state.activity_submission_repository,
    )


def _fmt(value: float) -> str:
    return f"{value:.1f}".replace(".", ",")


def _snapshot(grade: GradeResponse) -> dict:
    return {
        "grade": grade.grade,
        "attendance": grade.attendance,
        "subject": grade.subject,
        "activityType": grade.activityType,
        "observations": grade.observations,
        "date": grade.date.isoformat() if grade.date else None,
    }


def _describe(request: Request, grade: GradeResponse) -> str:
    student = request.app.state.student_repository.find_by_id(grade.studentId) or {}
    return f"{student.get('name', 'aluno')} ({grade.subject or 'sem disciplina'})"


def _check_student(request: Request, student_id: str, scope: AccessScope) -> None:
    student = request.app.state.student_repository.find_by_id(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
    scope.require_student(student)


def _check_create(request: Request, payload: GradeCreateRequest, scope: AccessScope) -> None:
    """Professor só lança nota em turma dele (o serviço ainda confere a matrícula do aluno)."""
    scope.require_classroom(payload.classroomId)


@router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def create_grade(
    payload: GradeCreateRequest,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    created = _check_create(request, payload, scope) or service(request).create(payload, scope.principal)
    set_audit(
        request,
        entityId=created.id,
        summary=f"Nota {_fmt(created.grade)} lançada para {_describe(request, created)}",
        details={"after": _snapshot(created), "studentId": created.studentId, "classroomId": created.classroomId},
    )
    return created


@router.get("", response_model=list[GradeResponse])
def list_grades(
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    return [item for item in service(request).list_all() if scope.can_access_classroom(item.classroomId)]


@router.get("/student/{student_id}/average", response_model=float)
def average_by_student(
    student_id: str,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    _check_student(request, student_id, scope)
    return service(request).average_by_student(student_id)


@router.get("/student/{student_id}", response_model=list[GradeResponse])
def grades_by_student(
    student_id: str,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    _check_student(request, student_id, scope)
    return [item for item in service(request).by_student(student_id) if scope.can_access_classroom(item.classroomId)]


@router.get("/classroom/{classroom_id}", response_model=list[GradeResponse])
def grades_by_classroom(
    classroom_id: str,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    scope.require_classroom(classroom_id)
    return service(request).by_classroom(classroom_id)


@router.get("/classroom/{classroom_id}/summary", response_model=GradeClassroomSummaryResponse)
def classroom_summary(
    classroom_id: str,
    request: Request,
    subject: str | None = None,
    scope: AccessScope = Depends(staff_scope),
):
    scope.require_classroom(classroom_id)
    return service(request).classroom_summary(classroom_id, subject)


@router.post("/from-activity/{activity_id}", response_model=ActivityGradesLaunchResponse)
def launch_grades_from_activity(
    activity_id: str,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    scope.require_activity(request.app.state.activity_repository.find_by_id(activity_id))
    result = service(request).launch_from_activity(activity_id, scope.principal)
    set_audit(
        request,
        summary=f"Notas lançadas a partir da atividade “{result.activityTitle}”: {result.launched} nova(s), {result.alreadyLaunched} já existente(s)",
        details=result.model_dump(),
    )
    return result


@router.get("/{grade_id}", response_model=GradeResponse)
def get_grade(
    grade_id: str,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    grade = service(request).get(grade_id)
    scope.require_classroom(grade.classroomId)
    return grade


@router.put("/{grade_id}", response_model=GradeResponse)
def update_grade(
    grade_id: str,
    payload: GradeUpdateRequest,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    before = service(request).get(grade_id)
    scope.require_classroom(before.classroomId)
    if payload.classroomId:
        scope.require_classroom(payload.classroomId)
    updated = service(request).update(grade_id, payload, scope.principal)
    set_audit(
        request,
        summary=f"Nota de {_describe(request, updated)} alterada de {_fmt(before.grade)} para {_fmt(updated.grade)}",
        details={"before": _snapshot(before), "after": _snapshot(updated), "studentId": updated.studentId, "classroomId": updated.classroomId},
    )
    return updated


@router.delete("/{grade_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_grade(
    grade_id: str,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    before = service(request).get(grade_id)
    scope.require_classroom(before.classroomId)
    service(request).delete(grade_id)
    set_audit(
        request,
        summary=f"Nota {_fmt(before.grade)} de {_describe(request, before)} excluída",
        details={"before": _snapshot(before), "studentId": before.studentId, "classroomId": before.classroomId},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
