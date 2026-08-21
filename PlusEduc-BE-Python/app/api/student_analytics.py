from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.auth import UserPrincipal
from app.dependencies import get_current_user
from app.schemas.analytics import (
    PedagogicalRecommendationResponse,
    StudentAttendanceResponse,
    StudentPerformanceResponse,
)
from app.services.pedagogical_recommendation_service import PedagogicalRecommendationService
from app.services.student_analytics_service import StudentAnalyticsService

router = APIRouter(prefix="/api/students", tags=["Student Analytics"])


def service(request: Request) -> StudentAnalyticsService:
    return StudentAnalyticsService(
        request.app.state.student_repository,
        request.app.state.grade_repository,
        request.app.state.classroom_repository,
    )


def recommendation_service(request: Request) -> PedagogicalRecommendationService:
    return PedagogicalRecommendationService(
        request.app.state.student_repository,
        request.app.state.grade_repository,
        request.app.state.classroom_repository,
    )


def ensure_recommendation_access(student_id: str, current_user: UserPrincipal) -> None:
    role = (current_user.role or "").upper()
    if role in {"TEACHER", "ADMIN"}:
        return
    if role == "STUDENT" and current_user.student_id and str(current_user.student_id) == str(student_id):
        return
    raise HTTPException(status_code=403, detail="Você não tem permissão para consultar esta recomendação")


@router.get("/{student_id}/performance", response_model=StudentPerformanceResponse)
def student_performance(
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).performance(student_id)


@router.get("/{student_id}/attendance", response_model=StudentAttendanceResponse)
def student_attendance(
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    return service(request).attendance(student_id)


@router.get("/{student_id}/pedagogical-recommendation", response_model=PedagogicalRecommendationResponse)
def student_pedagogical_recommendation(
    student_id: str,
    request: Request,
    current_user: UserPrincipal = Depends(get_current_user),
):
    ensure_recommendation_access(student_id, current_user)
    return recommendation_service(request).recommend(student_id)
