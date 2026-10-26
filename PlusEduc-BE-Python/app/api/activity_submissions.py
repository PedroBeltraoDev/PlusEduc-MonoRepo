from fastapi import APIRouter, Depends, Request

from app.api.student_portal import service as portal_service
from app.core.auth import UserPrincipal
from app.dependencies import require_roles
from app.schemas.activity_submission import ActivitySubmissionRequest, StudentSubmissionResult
from app.services.activity_service import ActivityService
from app.services.activity_submission_service import ActivitySubmissionService

router = APIRouter(prefix="/api/student-portal", tags=["Activity Submissions"])


def service(request: Request) -> ActivitySubmissionService:
    activity_service = ActivityService(
        request.app.state.activity_repository,
        request.app.state.student_repository,
        request.app.state.classroom_repository,
        request.app.state.mongo,
    )
    return ActivitySubmissionService(
        request.app.state.activity_repository,
        request.app.state.activity_submission_repository,
        activity_service,
    )


@router.post("/activities/{activity_id}/submissions", response_model=StudentSubmissionResult)
def submit_activity(activity_id: str, payload: ActivitySubmissionRequest, request: Request, current_user: UserPrincipal = Depends(require_roles("STUDENT"))):
    # O serviço do portal só aceita atividades da turma do aluno (ou atribuídas a ele); sem essa
    # checagem, qualquer aluno poderia enviar respostas a atividades de outras turmas.
    return portal_service(request).submit_activity(activity_id, payload, current_user)


@router.get("/activities/{activity_id}/submissions", response_model=StudentSubmissionResult)
def get_activity_submission(activity_id: str, request: Request, current_user: UserPrincipal = Depends(require_roles("STUDENT"))):
    return service(request).get_submission(activity_id, current_user)
