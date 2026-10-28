from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from app.core.auth import UserPrincipal
from app.dependencies import require_roles
from app.schemas.audit import AuditLogPage
from app.services.audit_service import AuditService

router = APIRouter(prefix="/api/audit-logs", tags=["Audit"])


@router.get("", response_model=AuditLogPage, summary="Histórico de operações (professor: as próprias; admin: todas)")
def list_audit_logs(
    request: Request,
    entity: str | None = None,
    action: str | None = None,
    success: bool | None = None,
    actor: str | None = None,
    q: str | None = Query(default=None, max_length=100),
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    page: int = Query(default=0, ge=0),
    size: int = Query(default=20, ge=1, le=100),
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
):
    return AuditService(request.app.state.audit_repository).search(
        current_user, page, size,
        entity=entity, action=action, success=success, actor=actor, q=q, date_from=date_from, date_to=date_to,
    )
