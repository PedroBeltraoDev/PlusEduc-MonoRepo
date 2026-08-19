from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TeacherDocument(BaseModel):
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    id: Any = Field(validation_alias="_id")
    name: str
    email: str
    password: str | None = None
    subjects: list[str] | None = None
    classrooms: list[str] | None = None
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
