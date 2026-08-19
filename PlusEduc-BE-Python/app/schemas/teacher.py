from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TeacherCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1)
    email: str = Field(min_length=1)
    password: str | None = None
    subjects: list[str] | None = None
    classroomIds: list[str] | None = None
    active: bool | None = True


class TeacherUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = None
    email: str | None = None
    password: str | None = None
    subjects: list[str] | None = None
    classroomIds: list[str] | None = None
    active: bool | None = None


class TeacherResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    email: str
    subjects: list[str] | None = None
    classroomIds: list[str] | None = None
    active: bool | None = None
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
