from __future__ import annotations

import logging
from typing import Any

from starlette.concurrency import run_in_threadpool
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.jwt import TokenError, decode_token
from app.services.audit_service import AuditService, classify

logger = logging.getLogger(__name__)

MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def set_audit(request: Request, **values: Any) -> None:
    """Permite que um endpoint enriqueça a entrada do histórico (resumo, id da entidade, antes/depois)."""
    current = getattr(request.state, "audit", None) or {}
    current.update(values)
    request.state.audit = current


def audit_enabled(settings) -> bool:
    if settings.audit_enabled is not None:
        return settings.audit_enabled
    return not str(settings.app_env).lower().startswith("test")


class AuditMiddleware(BaseHTTPMiddleware):
    """Registra no histórico toda operação que altera dados (POST, PUT, PATCH, DELETE), com sucesso ou falha."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        try:
            if request.method in MUTATING_METHODS and request.url.path.startswith("/api/") and not request.url.path.startswith("/api/audit-logs"):
                state = getattr(request.app.state, "audit_repository", None)
                if state is not None and audit_enabled(request.app.state.settings):
                    await run_in_threadpool(self._record, request, response.status_code)
        except Exception:  # noqa: BLE001 - o histórico nunca pode derrubar a operação do usuário
            logger.exception("Falha ao registrar operação no histórico")
        return response

    @staticmethod
    def _record(request: Request, status: int) -> None:
        path = request.url.path
        action, entity, entity_id = classify(request.method, path)
        extra: dict[str, Any] = dict(getattr(request.state, "audit", None) or {})
        principal = getattr(request.state, "principal", None)
        actor_email = extra.pop("actorEmail", None)
        if principal is None and not actor_email:
            actor_email = AuditMiddleware._email_from_token(request)
        if action == "LOGIN" and status >= 400:
            action = "LOGIN_FAILED"
        elif status in (401, 403) and action not in {"LOGIN_FAILED"}:
            action = "ACCESS_DENIED"
        AuditService(request.app.state.audit_repository).record(
            action=action,
            entity=entity,
            method=request.method,
            path=path,
            status=status,
            principal=principal,
            actor_email=actor_email,
            actor_role=extra.pop("actorRole", None),
            actor_name=extra.pop("actorName", None),
            entity_id=extra.pop("entityId", None) or entity_id,
            summary=extra.pop("summary", None),
            details=extra.pop("details", None),
            ip=request.client.host if request.client else None,
        )

    @staticmethod
    def _email_from_token(request: Request) -> str | None:
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            return None
        try:
            return decode_token(header[7:], request.app.state.settings).get("sub")
        except (TokenError, RuntimeError):
            return None
