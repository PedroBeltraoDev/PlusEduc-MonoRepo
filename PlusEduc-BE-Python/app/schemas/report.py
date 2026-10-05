from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.audit import AuditLogResponse


class ReportColumn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    type: str = "text"  # text | number | percent | date | datetime


class ReportSummaryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    value: str


class ReportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    description: str
    generatedAt: datetime
    filters: dict[str, str] = Field(default_factory=dict)
    columns: list[ReportColumn]
    rows: list[dict[str, Any]]
    summary: list[ReportSummaryItem] = Field(default_factory=list)
    total: int


class ReportCatalogItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    title: str
    description: str
    statusOptions: list[dict[str, str]] = Field(default_factory=list)


class DashboardKpis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    students: int
    classrooms: int
    activities: int
    gradeLaunches: int
    averageGrade: float | None
    attendanceRate: int | None
    submissionRate: int | None
    studentsAtRisk: int


class NamedAverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str | None = None
    name: str
    average: float
    attendanceRate: int | None = None
    launches: int


class MonthlyAverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: str
    average: float
    launches: int


class DistributionBucket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: str
    count: int


class ParticipationTotals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivered: int
    pending: int


class AtRiskStudent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studentId: str
    studentName: str
    classroomName: str
    average: float | None
    attendanceRate: int | None
    reasons: list[str]


class DashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generatedAt: datetime
    filters: dict[str, str]
    kpis: DashboardKpis
    averageByClassroom: list[NamedAverage]
    averageBySubject: list[NamedAverage]
    monthlyAverage: list[MonthlyAverage]
    distribution: list[DistributionBucket]
    participation: ParticipationTotals
    atRisk: list[AtRiskStudent]
    recentOperations: list[AuditLogResponse]


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    id: str
    title: str
    subtitle: str | None = None
    url: str


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    total: int
    results: list[SearchHit]
