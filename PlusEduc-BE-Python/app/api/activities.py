from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.auth import UserPrincipal
from app.core.audit_middleware import set_audit
from app.core.access import AccessScope, build_scope, staff_scope
from app.dependencies import get_current_user
from app.schemas.activity import ActivityCreateRequest, ActivityGenerationRequest, ActivityResponse, ActivityUpdateRequest
from app.schemas.activity_submission import ActivitySubmissionDetailResponse
from app.services.activity_pdf_service import ActivityPdfService
from app.services.activity_service import ActivityService
from app.services.teacher_correction_service import TeacherCorrectionService

router = APIRouter(prefix="/api/activities", tags=["Activities"])


def service(request: Request) -> ActivityService:
    return ActivityService(
        request.app.state.activity_repository,
        request.app.state.student_repository,
        request.app.state.classroom_repository,
        request.app.state.mongo,
        request.app.state.settings,
        request.app.state.activity_submission_repository,
    )


def pdf_service(request: Request) -> ActivityPdfService:
    return ActivityPdfService(
        request.app.state.student_repository,
        request.app.state.classroom_repository,
    )


def _activity_or_404(request: Request, activity_id: str) -> dict:
    activity = request.app.state.activity_repository.find_by_id(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail=f"Atividade não encontrada: {activity_id}")
    return activity


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityCreateRequest, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_classroom(payload.classroomId)
    created = service(request).create(payload, scope.principal)
    set_audit(request, entityId=created.id, summary=f"Atividade “{created.title}” criada", details={"title": created.title, "subject": created.subject, "classroomId": created.classroomId})
    return created


@router.post("/generate", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def generate_activity(payload: ActivityGenerationRequest, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_classroom(payload.classroomId)
    generated = service(request).generate(payload, scope.principal)
    set_audit(request, entityId=generated.id, summary=f"Atividade “{generated.title}” gerada", details={"title": generated.title, "subject": generated.subject})
    return generated


@router.get("", response_model=list[ActivityResponse])
def list_activities(request: Request, scope: AccessScope = Depends(staff_scope)):
    return service(request).list_scoped(scope, include_participation=True)


@router.get("/classroom/{classroom_id}", response_model=list[ActivityResponse])
def activities_by_classroom(classroom_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_classroom(classroom_id)
    return service(request).by_classroom(classroom_id)


@router.get("/student/{student_id}", response_model=list[ActivityResponse])
def activities_by_student(student_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    student = request.app.state.student_repository.find_by_id(student_id)
    scope.require_student(student)
    return [item for item in service(request).by_student(student_id) if scope.can_access_classroom(item.classroomId) or scope.is_admin]


@router.get("/teacher/{teacher_id}", response_model=list[ActivityResponse])
def activities_by_teacher(teacher_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    if not scope.is_admin and teacher_id not in scope.actor_keys:
        raise HTTPException(status_code=403, detail="Você só pode consultar as próprias atividades")
    return service(request).by_teacher(teacher_id)


@router.get("/{activity_id}/submissions", response_model=list[ActivitySubmissionDetailResponse])
def activity_submissions(activity_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    return TeacherCorrectionService(
        request.app.state.activity_repository,
        request.app.state.activity_submission_repository,
        request.app.state.classroom_repository,
        request.app.state.student_repository,
    ).list_activity_submissions(activity_id, scope.principal, scope)


@router.get("/{activity_id}/export-pdf")
def export_activity_pdf(
    activity_id: str,
    request: Request,
    includeAnswers: bool = Query(default=False),
    current_user: UserPrincipal = Depends(get_current_user),
):
    activity = _activity_or_404(request, activity_id)
    # Exportação em PDF: mesma regra das demais rotas (antes, professor sem cadastro passava direto).
    build_scope(request, current_user).require_activity(activity)
    pdf = pdf_service(request).generate(activity, includeAnswers)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="atividade-{activity_id}.pdf"'},
    )


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(activity_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_activity(_activity_or_404(request, activity_id))
    return service(request).get(activity_id, include_participation=True)


@router.put("/{activity_id}", response_model=ActivityResponse)
def update_activity(activity_id: str, payload: ActivityUpdateRequest, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_activity(_activity_or_404(request, activity_id))
    if payload.classroomId:
        scope.require_classroom(payload.classroomId)
    return service(request).update(activity_id, payload, scope.principal)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: str, request: Request, scope: AccessScope = Depends(staff_scope)):
    scope.require_activity(_activity_or_404(request, activity_id))
    before = service(request).get(activity_id)
    service(request).delete(activity_id)
    removed = request.app.state.activity_submission_repository.delete_by_activity(activity_id)  # sem respostas órfãs
    set_audit(request, summary=f"Atividade “{before.title}” excluída", details={"title": before.title, "submissionsRemoved": removed})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
