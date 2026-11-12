from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.validators import validate_email_format


class TeacherCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=3, max_length=120)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=6, max_length=100)
    subjects: list[str] | None = None
    classroomIds: list[str] | None = None
    active: bool | None = True

    _check_email = field_validator("email")(validate_email_format)


class TeacherUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, min_length=3, max_length=120)
    email: str | None = Field(default=None, min_length=3, max_length=254)
    password: str | None = Field(default=None, min_length=6, max_length=100)
    subjects: list[str] | None = None
    classroomIds: list[str] | None = None
    active: bool | None = None

    _check_email = field_validator("email")(validate_email_format)


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


class PendingTeacherResponse(BaseModel):
    """Cadastro público de professor aguardando aprovação do ADMIN."""

    id: str
    name: str
    email: str
    subjects: list[str] = []
    createdAt: datetime | None = None
