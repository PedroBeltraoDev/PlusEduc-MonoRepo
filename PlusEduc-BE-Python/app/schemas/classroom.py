from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.student import LearningGapResponse


class ClassroomCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=3, max_length=100)
    year: int
    gradeLevel: str = Field(min_length=1)
    teacherId: str = Field(min_length=1)
    studentIds: list[str] | None = None
    subjects: list[str] | None = None
    active: bool | None = True


class ClassroomUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, min_length=3, max_length=100)
    year: int | None = None
    gradeLevel: str | None = None
    teacherId: str | None = None
    studentIds: list[str] | None = None
    subjects: list[str] | None = None
    active: bool | None = None


class StudentSummary(BaseModel):
    id: str
    name: str
    learningGaps: list[LearningGapResponse] | None = None


class ClassroomResponse(BaseModel):
    id: str
    name: str
    year: int
    gradeLevel: str
    teacherId: str
    teacherName: str | None = None
    studentIds: list[str]
    students: list[StudentSummary]
    subjects: list[str]
    active: bool | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class ClassroomPageResponse(BaseModel):
    content: list[ClassroomResponse]
    totalPages: int
    totalElements: int
    size: int
    number: int
    first: bool
    last: bool
