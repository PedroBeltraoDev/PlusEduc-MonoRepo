from fastapi import APIRouter, Depends, Request

from app.core.access import AccessScope, staff_scope
from app.schemas.activity_submission import (
    PendingCorrectionResponse,
    ReviewQuestionRequest,
    StudentSubmissionResult,
)
from app.services.teacher_correction_service import TeacherCorrectionService

router = APIRouter(prefix="/api/teacher/activity-corrections", tags=["Teacher Activity Corrections"])
legacy_router = APIRouter(prefix="/api/teacher/activity_corrections", tags=["Teacher Activity Corrections (legacy)"])


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
    scope: AccessScope = Depends(staff_scope),
):
    return service(request).list_pending(scope.principal, scope)


@router.put("/{submission_id}/questions/{question_index}", response_model=StudentSubmissionResult)
def review_question(
    submission_id: str,
    question_index: int,
    payload: ReviewQuestionRequest,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    return service(request).review_question(submission_id, question_index, payload, scope.principal, scope)


@legacy_router.get("/pending", response_model=list[PendingCorrectionResponse])
def list_pending_legacy(
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    return service(request).list_pending(scope.principal, scope)


@legacy_router.put("/{submission_id}/questions/{question_index}", response_model=StudentSubmissionResult)
def review_question_legacy(
    submission_id: str,
    question_index: int,
    payload: ReviewQuestionRequest,
    request: Request,
    scope: AccessScope = Depends(staff_scope),
):
    return service(request).review_question(submission_id, question_index, payload, scope.principal, scope)
