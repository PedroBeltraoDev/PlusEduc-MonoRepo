from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.activities import router as activities_router
from app.api.auth import router as auth_router
from app.api.classrooms import router as classrooms_router
from app.api.grades import router as grades_router
from app.api.health import router as health_router
from app.api.student_analytics import router as student_analytics_router
from app.api.activity_submissions import router as activity_submissions_router
from app.api.students import router as students_router
from app.api.student_portal import router as student_portal_router
from app.api.teachers import router as teachers_router
from app.core.config import Settings, get_settings
from app.core.database import MongoConnection
from app.core.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.core.logging_config import configure_logging
from app.repositories.activity_repository import ActivityRepository
from app.repositories.activity_submission_repository import ActivitySubmissionRepository
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.grade_repository import GradeRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.repositories.user_repository import UserRepository


def create_app(
    settings: Settings | None = None,
    user_repository=None,
    student_repository=None,
    teacher_repository=None,
    classroom_repository=None,
    grade_repository=None,
    activity_repository=None,
    activity_submission_repository=None,
) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings.log_level)

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        mongo = MongoConnection(resolved_settings)
        mongo.connect()
        application.state.settings = resolved_settings
        application.state.mongo = mongo
        application.state.user_repository = user_repository or UserRepository(mongo)
        application.state.student_repository = student_repository or StudentRepository(mongo)
        application.state.teacher_repository = teacher_repository or TeacherRepository(mongo)
        application.state.classroom_repository = classroom_repository or ClassroomRepository(mongo)
        application.state.grade_repository = grade_repository or GradeRepository(mongo)
        application.state.activity_repository = activity_repository or ActivityRepository(mongo)
        application.state.activity_submission_repository = activity_submission_repository or ActivitySubmissionRepository(mongo)
        try:
            yield
        finally:
            mongo.close()

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        description="Backend FastAPI do PlusEduc em migração incremental.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_allowed_origins,
        allow_credentials=resolved_settings.cors_allow_credentials,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition"],
    )
    application.add_exception_handler(StarletteHTTPException, http_exception_handler)
    application.add_exception_handler(RequestValidationError, validation_exception_handler)
    application.add_exception_handler(Exception, unhandled_exception_handler)
    application.include_router(health_router)
    application.include_router(auth_router)
    application.include_router(students_router)
    application.include_router(student_analytics_router)
    application.include_router(teachers_router)
    application.include_router(classrooms_router)
    application.include_router(grades_router)
    application.include_router(activities_router)
    application.include_router(student_portal_router)
    application.include_router(activity_submissions_router)
    return application


app = create_app()
