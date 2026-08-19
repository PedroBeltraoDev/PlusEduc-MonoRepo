from fastapi import APIRouter, Depends, Request, Response

from app.core.auth import UserPrincipal
from app.dependencies import require_roles
from app.schemas.student_portal_schema import (
    Classmate,
    StudentActivity,
    StudentActivityDetail,
    StudentClassroom,
    StudentPortalGrade,
    StudentPortalPerformance,
    StudentPortalProfile,
    TeacherSummary,
)
from app.services.student_portal_service import StudentPortalService

router = APIRouter(prefix="/api/student-portal", tags=["Student Portal"])


def service(request: Request) -> StudentPortalService:
    return StudentPortalService(
        request.app.state.student_repository,
        request.app.state.classroom_repository,
        request.app.state.teacher_repository,
        request.app.state.activity_repository,
        request.app.state.activity_submission_repository,
        request.app.state.grade_repository,
        request.app.state.mongo,
    )


def student_user(current_user: UserPrincipal = Depends(require_roles("STUDENT"))) -> UserPrincipal:
    return current_user


@router.get("/me", response_model=StudentPortalProfile)
def get_profile(request: Request, current_user: UserPrincipal = Depends(student_user)):
    return service(request).profile(current_user)


@router.get("/classroom", response_model=StudentClassroom)
def get_classroom(request: Request, current_user: UserPrincipal = Depends(student_user)):
    return service(request).classroom(current_user)


@router.get("/classmates", response_model=list[Classmate])
def get_classmates(request: Request, current_user: UserPrincipal = Depends(student_user)):
    return service(request).classmates(current_user)


@router.get("/teachers", response_model=list[TeacherSummary])
def get_teachers(request: Request, current_user: UserPrincipal = Depends(student_user)):
    return service(request).teachers(current_user)


@router.get("/activities", response_model=list[StudentActivity])
def get_activities(request: Request, current_user: UserPrincipal = Depends(student_user)):
    return service(request).activities(current_user)


@router.get("/activities/{activity_id}", response_model=StudentActivityDetail)
def get_activity_detail(activity_id: str, request: Request, current_user: UserPrincipal = Depends(student_user)):
    return service(request).activity_detail(activity_id, current_user)


@router.get("/activities/{activity_id}/export-pdf")
def export_activity_pdf(activity_id: str, request: Request, current_user: UserPrincipal = Depends(student_user)):
    pdf = service(request).export_pdf(activity_id, current_user)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="atividade-{activity_id}.pdf"'},
    )


@router.get("/grades", response_model=list[StudentPortalGrade])
def get_grades(request: Request, current_user: UserPrincipal = Depends(student_user)):
    return service(request).grades(current_user)


@router.get("/performance", response_model=StudentPortalPerformance)
def get_performance(request: Request, current_user: UserPrincipal = Depends(student_user)):
    return service(request).performance(current_user)
