from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class GradeCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    studentId: str = Field(min_length=1)
    classroomId: str = Field(min_length=1)
    grade: float = Field(
        ge=0,
        le=10,
        validation_alias=AliasChoices("grade", "gradeValue"),
    )
    attendance: bool | None = None
    subject: str | None = None
    activityType: str | None = None
    observations: str | None = Field(default=None, max_length=500)
    date: datetime


class GradeUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    studentId: str | None = None
    classroomId: str | None = None
    grade: float | None = Field(
        default=None,
        ge=0,
        le=10,
        validation_alias=AliasChoices("grade", "gradeValue"),
    )
    attendance: bool | None = None
    subject: str | None = None
    activityType: str | None = None
    observations: str | None = Field(default=None, max_length=500)
    date: datetime | None = None


class GradeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    studentId: str
    classroomId: str
    subject: str | None = None
    grade: float
    gradeValue: float
    attendance: bool | None = None
    date: datetime
    activityType: str | None = None
    observations: str | None = None
    createdAt: datetime | None = None


class GradeAverageResponse(BaseModel):
    average: float
