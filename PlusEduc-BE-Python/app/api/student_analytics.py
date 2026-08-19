from fastapi import APIRouter, Depends, Request

from app.core.auth import UserPrincipal
from app.dependencies import get_current_user
from app.schemas.analytics import StudentAttendanceResponse, StudentPerformanceResponse
from app.services.student_analytics_service import StudentAnalyticsService

router = APIRouter(prefix="/api/students", tags=["Student Analytics"])


def service(request: Request) -> StudentAnalyticsService:
    return StudentAnalyticsService(
        request.app.state.student_repository,
        request.app.state.grade_repository,
        request.app.state.classroom_repository,
    )


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
