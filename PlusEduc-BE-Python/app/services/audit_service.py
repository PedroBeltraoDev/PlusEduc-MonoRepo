from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from typing import Any

from app.core.auth import UserPrincipal
from app.repositories.audit_repository import AuditRepository
from app.schemas.audit import AuditLogPage, AuditLogResponse

# Horário de Brasília (sem horário de verão desde 2019): usado para interpretar os filtros por data.
BRT = timezone(timedelta(hours=-3))

ACTION_LABELS = {
    "LOGIN": "Login",
    "LOGIN_FAILED": "Tentativa de login recusada",
    "REGISTER": "Cadastro de usuário",
    "PASSWORD_RESET_REQUEST": "Pedido de redefinição de senha",
    "PASSWORD_RESET": "Redefinição de senha",
    "PROFILE_UPDATE": "Atualização de perfil",
    "CREATE": "Criação",
    "UPDATE": "Alteração",
    "DELETE": "Exclusão",
    "ENROLL": "Matrícula em turma",
    "UNENROLL": "Remoção de turma",
    "GENERATE": "Geração de atividade",
    "SUBMIT": "Envio de atividade",
    "REVIEW": "Correção de questão",
    "LAUNCH_FROM_ACTIVITY": "Lançamento de notas por atividade",
    "ACCESS_DENIED": "Acesso negado",
}
ENTITY_LABELS = {
    "auth": "autenticação",
    "grade": "nota",
    "classroom": "turma",
    "student": "aluno",
    "teacher": "professor",
    "activity": "atividade",
    "submission": "submissão",
    "correction": "correção",
    "subject": "matéria",
    "topic": "tópico",
}

_CRUD = {"POST": "CREATE", "PUT": "UPDATE", "PATCH": "UPDATE", "DELETE": "DELETE"}
# (padrão do caminho, entidade, ação por método, índice do grupo que contém o id da entidade)
_RULES: list[tuple[re.Pattern[str], str, dict[str, str] | None, int | None]] = [
    (re.compile(r"^/api/auth/login$"), "auth", {"POST": "LOGIN"}, None),
    (re.compile(r"^/api/auth/register/(student|teacher)$"), "auth", {"POST": "REGISTER"}, None),
    (re.compile(r"^/api/auth/forgot-password$"), "auth", {"POST": "PASSWORD_RESET_REQUEST"}, None),
    (re.compile(r"^/api/auth/reset-password$"), "auth", {"POST": "PASSWORD_RESET"}, None),
    (re.compile(r"^/api/auth/profile$"), "auth", {"PUT": "PROFILE_UPDATE"}, None),
    (re.compile(r"^/api/grades/from-activity/([^/]+)$"), "grade", {"POST": "LAUNCH_FROM_ACTIVITY"}, 1),
    (re.compile(r"^/api/grades(?:/([^/]+))?$"), "grade", None, 1),
    (re.compile(r"^/api/classrooms/([^/]+)/enroll/[^/]+$"), "classroom", {"POST": "ENROLL"}, 1),
    (re.compile(r"^/api/classrooms/([^/]+)/unenroll/[^/]+$"), "classroom", {"DELETE": "UNENROLL"}, 1),
    (re.compile(r"^/api/classrooms(?:/([^/]+))?$"), "classroom", None, 1),
    (re.compile(r"^/api/students(?:/([^/]+))?$"), "student", None, 1),
    (re.compile(r"^/api/teachers(?:/([^/]+))?$"), "teacher", None, 1),
    (re.compile(r"^/api/activities/generate$"), "activity", {"POST": "GENERATE"}, None),
    (re.compile(r"^/api/activities(?:/([^/]+))?$"), "activity", None, 1),
    (re.compile(r"^/api/student-portal/activities/([^/]+)/submissions$"), "submission", {"POST": "SUBMIT"}, 1),
    (re.compile(r"^/api/teacher/activity[-_]corrections/([^/]+)/questions/\d+$"), "correction", {"PUT": "REVIEW"}, 1),
    (re.compile(r"^/api/subjects?(?:/([^/]+))?"), "subject", None, 1),
    (re.compile(r"^/api/subject-topics?(?:/([^/]+))?"), "topic", None, 1),
]


def classify(method: str, path: str) -> tuple[str, str, str | None]:
    """Devolve (ação, entidade, id da entidade) a partir do método e do caminho da requisição."""
    for pattern, entity, actions, id_group in _RULES:
        match = pattern.match(path)
        if not match:
            continue
        action = (actions or _CRUD).get(method)
        if action is None:
            continue
        entity_id = match.group(id_group) if id_group and match.lastindex and match.lastindex >= id_group else None
        return action, entity, entity_id
    segments = [part for part in path.split("/") if part]
    return _CRUD.get(method, method), (segments[1] if len(segments) > 1 else "api"), None


def default_summary(action: str, entity: str, entity_id: str | None, status: int, email: str | None) -> str:
    label = ACTION_LABELS.get(action, action.title())
    target = ENTITY_LABELS.get(entity, entity)
    if action in {"LOGIN", "LOGIN_FAILED", "REGISTER", "PASSWORD_RESET_REQUEST", "PASSWORD_RESET", "PROFILE_UPDATE"}:
        text = label + (f" ({email})" if email else "")
    else:
        text = f"{label} de {target}" if action in {"CREATE", "UPDATE", "DELETE"} else f"{label} ({target})"
        if entity_id:
            text += f" {entity_id}"
    if status >= 400:
        text += f" — falhou ({status})"
    return text


def day_start(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=BRT).astimezone(timezone.utc).replace(tzinfo=None)


def day_end(value: date) -> datetime:
    return datetime.combine(value, time.max, tzinfo=BRT).astimezone(timezone.utc).replace(tzinfo=None)


class AuditService:
    def __init__(self, repository: AuditRepository) -> None:
        self.repository = repository

    def record(
        self,
        *,
        action: str,
        entity: str,
        method: str,
        path: str,
        status: int,
        principal: UserPrincipal | None = None,
        actor_email: str | None = None,
        actor_role: str | None = None,
        actor_name: str | None = None,
        entity_id: str | None = None,
        summary: str | None = None,
        details: dict[str, Any] | None = None,
        ip: str | None = None,
    ) -> None:
        email = (principal.email if principal else None) or actor_email
        document = {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None),
            "actorId": principal.user_id if principal else None,
            "actorEmail": email,
            "actorName": (principal.name if principal else None) or actor_name,
            "actorRole": (principal.role if principal else None) or actor_role,
            "action": action,
            "entity": entity,
            "entityId": entity_id,
            "method": method,
            "path": path,
            "status": status,
            "success": status < 400,
            "summary": summary or default_summary(action, entity, entity_id, status, email),
            "details": details or {},
            "ip": ip,
        }
        self.repository.insert(document)

    def build_query(
        self,
        principal: UserPrincipal,
        *,
        entity: str | None = None,
        action: str | None = None,
        success: bool | None = None,
        actor: str | None = None,
        q: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict[str, Any]:
        query: dict[str, Any] = {}
        if principal.role != "ADMIN":
            # Professor só enxerga o que ele mesmo fez; o histórico completo é do administrador.
            query["$or"] = [{"actorId": principal.user_id}, {"actorEmail": principal.email}]
        if entity:
            query["entity"] = entity
        if action:
            query["action"] = action
        if success is not None:
            query["success"] = success
        if actor and principal.role == "ADMIN":
            query["actorEmail"] = {"$regex": re.escape(actor), "$options": "i"}
        if q:
            pattern = {"$regex": re.escape(q), "$options": "i"}
            clause = [{"summary": pattern}, {"actorEmail": pattern}, {"entityId": pattern}]
            query["$and"] = [*query.get("$and", []), {"$or": clause}]
        if date_from or date_to:
            window: dict[str, datetime] = {}
            if date_from:
                window["$gte"] = day_start(date_from)
            if date_to:
                window["$lte"] = day_end(date_to)
            query["timestamp"] = window
        return query

    def search(self, principal: UserPrincipal, page: int, size: int, **filters: Any) -> AuditLogPage:
        query = self.build_query(principal, **filters)
        total = self.repository.count(query)
        items = self.repository.search(query, page * size, size)
        return AuditLogPage(
            items=[self.to_response(item) for item in items],
            total=total,
            page=page,
            size=size,
            totalPages=(total + size - 1) // size if total else 0,
        )

    def recent(self, principal: UserPrincipal, limit: int = 8) -> list[AuditLogResponse]:
        return [self.to_response(item) for item in self.repository.search(self.build_query(principal), 0, limit)]

    @staticmethod
    def to_response(document: dict[str, Any]) -> AuditLogResponse:
        return AuditLogResponse(
            id=str(document["_id"]),
            timestamp=document["timestamp"].replace(tzinfo=timezone.utc),
            actorEmail=document.get("actorEmail"),
            actorName=document.get("actorName"),
            actorRole=document.get("actorRole"),
            action=document.get("action", ""),
            actionLabel=ACTION_LABELS.get(document.get("action", ""), document.get("action", "")),
            entity=document.get("entity", ""),
            entityLabel=ENTITY_LABELS.get(document.get("entity", ""), document.get("entity", "")),
            entityId=document.get("entityId"),
            method=document.get("method", ""),
            path=document.get("path", ""),
            status=document.get("status", 0),
            success=bool(document.get("success", True)),
            summary=document.get("summary", ""),
            details=document.get("details") or {},
        )
