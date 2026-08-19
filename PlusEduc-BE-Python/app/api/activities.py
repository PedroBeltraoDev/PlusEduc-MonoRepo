from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from app.core.auth import UserPrincipal
from app.dependencies import get_current_user, require_roles
from app.schemas.activity import ActivityCreateRequest, ActivityGenerationRequest, ActivityResponse, ActivityUpdateRequest
from app.services.activity_pdf_service import ActivityPdfService
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/api/activities", tags=["Activities"])


def service(request: Request) -> ActivityService:
    return ActivityService(
        request.app.state.activity_repository,
        request.app.state.student_repository,
        request.app.state.classroom_repository,
        request.app.state.mongo,
        request.app.state.settings,
    )


def pdf_service(request: Request) -> ActivityPdfService:
    return ActivityPdfService(
        request.app.state.student_repository,
        request.app.state.classroom_repository,
    )


def require_pdf_access(request: Request, activity: dict, current_user: UserPrincipal) -> None:
    if current_user.role.upper() == "ADMIN":
        return
    classroom_id = activity.get("classroom_id", activity.get("classroomId"))
    if not classroom_id:
        raise HTTPException(status_code=400, detail="Atividade sem turma associada para validação de acesso")
    classroom = request.app.state.classroom_repository.find_by_id(str(classroom_id))
    if not classroom:
        raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")
    teacher_id = classroom.get("teacher_id", classroom.get("teacherId"))
    created_by = activity.get("created_by", activity.get("createdBy"))
    if teacher_id and (str(teacher_id) == current_user.user_id or str(teacher_id).lower() == current_user.email.lower()):
        return
    if created_by and (str(created_by) == current_user.user_id or str(created_by).lower() == current_user.email.lower()):
        return
    teacher = request.app.state.mongo.database.teachers.find_one({
        "$or": [{"email": current_user.email}, {"_id": current_user.user_id}]
    })
    classroom_ids = (teacher or {}).get("classroomIds", (teacher or {}).get("classroom_ids", [])) or []
    if str(classroom_id) in {str(value) for value in classroom_ids}:
        return
    if current_user.role.upper() == "TEACHER" and teacher is None:
        return
    raise HTTPException(status_code=403, detail="A atividade não pertence a uma turma do usuário autenticado")


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(payload: ActivityCreateRequest, request: Request, current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN"))):
    return service(request).create(payload, current_user)


@router.post("/generate", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def generate_activity(payload: ActivityGenerationRequest, request: Request, current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN"))):
    return service(request).generate(payload, current_user)


@router.get("", response_model=list[ActivityResponse])
def list_activities(request: Request, current_user: UserPrincipal = Depends(get_current_user)):
    return service(request).list_all()


@router.get("/classroom/{classroom_id}", response_model=list[ActivityResponse])
def activities_by_classroom(classroom_id: str, request: Request, current_user: UserPrincipal = Depends(get_current_user)):
    return service(request).by_classroom(classroom_id)


@router.get("/student/{student_id}", response_model=list[ActivityResponse])
def activities_by_student(student_id: str, request: Request, current_user: UserPrincipal = Depends(get_current_user)):
    return service(request).by_student(student_id)


@router.get("/teacher/{teacher_id}", response_model=list[ActivityResponse])
def activities_by_teacher(teacher_id: str, request: Request, current_user: UserPrincipal = Depends(get_current_user)):
    return service(request).by_teacher(teacher_id)


@router.get("/{activity_id}/export-pdf")
def export_activity_pdf(
    activity_id: str,
    request: Request,
    includeAnswers: bool = Query(default=False),
    current_user: UserPrincipal = Depends(get_current_user),
):
    activity = request.app.state.activity_repository.find_by_id(activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail=f"Atividade não encontrada: {activity_id}")
    require_pdf_access(request, activity, current_user)
    pdf = pdf_service(request).generate(activity, includeAnswers)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="atividade-{activity_id}.pdf"'},
    )


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(activity_id: str, request: Request, current_user: UserPrincipal = Depends(get_current_user)):
    return service(request).get(activity_id)


@router.put("/{activity_id}", response_model=ActivityResponse)
def update_activity(activity_id: str, payload: ActivityUpdateRequest, request: Request, current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN"))):
    return service(request).update(activity_id, payload, current_user)


@router.delete("/{activity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_activity(activity_id: str, request: Request, current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN"))):
    service(request).delete(activity_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
