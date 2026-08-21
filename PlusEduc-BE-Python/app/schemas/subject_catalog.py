from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SubjectCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    name: str = Field(min_length=2, max_length=80)
    area: str | None = Field(default=None, max_length=80)
    gradeLevels: list[str] | None = None


class SubjectUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    active: bool | None = None


class SubjectResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    active: bool
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
    area: str | None = None
    gradeLevels: list[str] | None = None
    curriculumKey: str | None = None


class SubjectAssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    classroomId: str = Field(min_length=1)
    subjectId: str = Field(min_length=1)


class SubjectAssignmentResponse(BaseModel):
    classroomId: str
    subjectId: str
    subjectName: str
    teacherId: str
    teacherName: str | None = None


class SubjectClassroomResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    year: int | None = None
    gradeLevel: str | None = None
    studentCount: int = 0
    averageGrade: float = 0


class SubjectStudentPerformanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studentId: str
    studentName: str
    studentEmail: str | None = None
    averageGrade: float = 0
    gradeCount: int = 0
    lastGrade: float | None = None


SortField = Literal["name", "grade"]
SortOrder = Literal["asc", "desc"]
