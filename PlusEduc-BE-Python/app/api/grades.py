from fastapi import APIRouter, Depends, Request, Response, status

from app.core.auth import UserPrincipal
from app.core.audit_middleware import set_audit
from app.dependencies import require_roles
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


@router.post("", response_model=GradeResponse, status_code=status.HTTP_201_CREATED)
def create_grade(
    payload: GradeCreateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    created = service(request).create(payload, current_user)
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
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return service(request).list_all()


@router.get("/student/{student_id}/average", response_model=float)
def average_by_student(
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return service(request).average_by_student(student_id)


@router.get("/student/{student_id}", response_model=list[GradeResponse])
def grades_by_student(
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return service(request).by_student(student_id)


@router.get("/classroom/{classroom_id}", response_model=list[GradeResponse])
def grades_by_classroom(
    classroom_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return service(request).by_classroom(classroom_id)


@router.get("/classroom/{classroom_id}/summary", response_model=GradeClassroomSummaryResponse)
def classroom_summary(
    classroom_id: str,
    request: Request,
    subject: str | None = None,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return service(request).classroom_summary(classroom_id, subject)


@router.post("/from-activity/{activity_id}", response_model=ActivityGradesLaunchResponse)
def launch_grades_from_activity(
    activity_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    result = service(request).launch_from_activity(activity_id, current_user)
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
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return service(request).get(grade_id)


@router.put("/{grade_id}", response_model=GradeResponse)
def update_grade(
    grade_id: str,
    payload: GradeUpdateRequest,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    before = service(request).get(grade_id)
    updated = service(request).update(grade_id, payload, current_user)
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
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    before = service(request).get(grade_id)
    service(request).delete(grade_id)
    set_audit(
        request,
        summary=f"Nota {_fmt(before.grade)} de {_describe(request, before)} excluída",
        details={"before": _snapshot(before), "studentId": before.studentId, "classroomId": before.classroomId},
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
