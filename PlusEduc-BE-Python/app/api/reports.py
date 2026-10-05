from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response

from app.core.auth import UserPrincipal
from app.dependencies import require_roles
from app.schemas.report import DashboardResponse, ReportCatalogItem, ReportResponse, SearchResponse
from app.services.report_export import CONTENT_TYPES, EXPORTERS
from app.services.report_service import CATALOG, Filters, ReportService
from app.services.search_service import SearchService

STAFF = ("TEACHER", "ADMIN")
reports_router = APIRouter(prefix="/api/reports", tags=["Reports"])
dashboard_router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
search_router = APIRouter(prefix="/api/search", tags=["Search"])


def report_service(request: Request) -> ReportService:
    state = request.app.state
    return ReportService(
        state.student_repository,
        state.classroom_repository,
        state.grade_repository,
        state.activity_repository,
        state.activity_submission_repository,
        state.audit_repository,
    )


def filters_from(
    classroomId: str | None = Query(default=None),
    subject: str | None = Query(default=None, max_length=80),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    status: str | None = Query(default=None, max_length=30),
    entity: str | None = Query(default=None, max_length=30),
    action: str | None = Query(default=None, max_length=40),
) -> Filters:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=422, detail="A data inicial não pode ser posterior à data final")
    return Filters(
        classroom_id=classroomId or None,
        subject=subject or None,
        date_from=date_from,
        date_to=date_to,
        status=status or None,
        entity=entity or None,
        action=action or None,
    )


@dashboard_router.get("/overview", response_model=DashboardResponse, summary="Indicadores e gráficos do dashboard")
def dashboard_overview(
    request: Request,
    filters: Filters = Depends(filters_from),
    current_user: UserPrincipal = Depends(require_roles(*STAFF)),
):
    return report_service(request).dashboard(current_user, filters)


@reports_router.get("", response_model=list[ReportCatalogItem], summary="Relatórios disponíveis")
def report_catalog(current_user: UserPrincipal = Depends(require_roles(*STAFF))):
    return CATALOG


@reports_router.get("/{report_type}", response_model=ReportResponse, summary="Executa um relatório com filtros")
def run_report(
    report_type: str,
    request: Request,
    filters: Filters = Depends(filters_from),
    current_user: UserPrincipal = Depends(require_roles(*STAFF)),
):
    return report_service(request).report(report_type, current_user, filters)


@reports_router.get("/{report_type}/export", summary="Exporta um relatório em CSV, XLSX ou PDF")
def export_report(
    report_type: str,
    request: Request,
    format: str = Query(default="csv", pattern="^(csv|xlsx|pdf)$"),
    filters: Filters = Depends(filters_from),
    current_user: UserPrincipal = Depends(require_roles(*STAFF)),
):
    report = report_service(request).report(report_type, current_user, filters)
    content = EXPORTERS[format](report)
    filename = f"pluseduc-{report_type}-{datetime.now().strftime('%Y%m%d')}.{format}"
    return Response(
        content=content,
        media_type=CONTENT_TYPES[format],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@search_router.get("", response_model=SearchResponse, summary="Pesquisa global em alunos, turmas e atividades")
def global_search(
    request: Request,
    q: str = Query(min_length=2, max_length=80),
    types: str | None = Query(default=None, description="students,classrooms,activities"),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserPrincipal = Depends(require_roles(*STAFF)),
):
    state = request.app.state
    kinds = [item.strip() for item in types.split(",")] if types else None
    return SearchService(state.student_repository, state.classroom_repository, state.activity_repository).search(q, kinds, limit)
