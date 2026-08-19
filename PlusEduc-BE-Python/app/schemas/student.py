from datetime import datetime
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class LearningGapInput(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    id: str | None = None
    subject: str = Field(min_length=1)
    topic: str = Field(min_length=1)
    severityLevel: str | None = Field(
        default=None,
        validation_alias=AliasChoices("severityLevel", "severity"),
    )
    description: str | None = None
    identifiedAt: datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("identifiedAt", "identifiedDate"),
    )
    lastAssessedAt: datetime | None = None
    improved: bool | None = None
    improvementStatus: str | None = None

    def to_document(self) -> dict[str, Any]:
        data = {
            "id": self.id,
            "subject": self.subject,
            "topic": self.topic,
            "severity_level": self.severityLevel,
            "description": self.description,
            "identifiedAt": self.identifiedAt,
            "lastAssessedAt": self.lastAssessedAt,
            "improved": self.improved,
        }
        if data["improved"] is None and self.improvementStatus is not None:
            data["improved"] = self.improvementStatus in {"IMPROVED", "RESOLVED"}
        return {key: value for key, value in data.items() if value is not None}


class LearningGapResponse(BaseModel):
    id: str | None = None
    subject: str
    topic: str
    severityLevel: str | None = None
    description: str | None = None
    identifiedAt: datetime | None = None
    lastAssessedAt: datetime | None = None
    improved: bool | None = None


class StudentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = Field(min_length=3, max_length=100)
    email: str = Field(min_length=1)
    birthDate: str = Field(min_length=1)
    classId: str = Field(min_length=1)
    learningGaps: list[LearningGapInput] | None = None
    active: bool | None = True


class StudentUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str | None = Field(default=None, min_length=3, max_length=100)
    email: str | None = None
    birthDate: str | None = None
    classId: str | None = None
    learningGaps: list[LearningGapInput] | None = None
    active: bool | None = None


class EnableStudentAccessRequest(BaseModel):
    password: str = Field(min_length=6, max_length=100)


class StudentResponse(BaseModel):
    id: str
    name: str
    email: str
    birthDate: str | None = None
    learningGaps: list[LearningGapResponse] | None = None
    classId: str | None = None
    className: str | None = None
    active: bool | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class StudentPageResponse(BaseModel):
    content: list[StudentResponse]
    totalPages: int
    totalElements: int
    size: int
    number: int
    first: bool
    last: bool

