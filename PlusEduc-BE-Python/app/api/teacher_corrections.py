from fastapi import APIRouter, Depends, Request

from app.core.auth import UserPrincipal
from app.dependencies import require_roles
from app.schemas.activity_submission import (
    PendingCorrectionResponse,
    ReviewQuestionRequest,
    StudentSubmissionResult,
)
from app.services.teacher_correction_service import TeacherCorrectionService

router = APIRouter(prefix="/api/teacher/activity-corrections", tags=["Teacher Activity Corrections"])


def service(request: Request) -> TeacherCorrectionService:
    return TeacherCorrectionService(
        request.app.state.activity_repository,
        request.app.state.activity_submission_repository,
        request.app.state.classroom_repository,
        request.app.state.student_repository,
    )


@router.get("/pending", response_model=list[PendingCorrectionResponse])
def list_pending(
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return service(request).list_pending(current_user)


@router.put("/{submission_id}/questions/{question_index}", response_model=StudentSubmissionResult)
def review_question(
    submission_id: str,
    question_index: int,
    payload: ReviewQuestionRequest,
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return service(request).review_question(submission_id, question_index, payload, current_user)
