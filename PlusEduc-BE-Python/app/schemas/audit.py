from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    timestamp: datetime
    actorEmail: str | None = None
    actorName: str | None = None
    actorRole: str | None = None
    action: str
    actionLabel: str
    entity: str
    entityLabel: str
    entityId: str | None = None
    method: str
    path: str
    status: int
    success: bool
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


class AuditLogPage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[AuditLogResponse]
    total: int
    page: int
    size: int
    totalPages: int
