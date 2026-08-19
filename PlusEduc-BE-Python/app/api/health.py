from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.schemas.health import HealthResponse

router = APIRouter(tags=["Infrastructure"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Verificar a disponibilidade da aplicação",
)
def health_check(request: Request) -> HealthResponse:
    settings = request.app.state.settings
    database_status = request.app.state.mongo.health()
    application_status = "ok" if database_status == "ok" else "degraded"
    return HealthResponse(
        status=application_status,
        service=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        database=database_status,
        timestamp=datetime.now(timezone.utc),
    )
