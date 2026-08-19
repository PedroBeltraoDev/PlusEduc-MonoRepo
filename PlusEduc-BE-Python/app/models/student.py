from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class StudentDocument(BaseModel):
    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    id: Any = Field(validation_alias="_id")
    name: str
    email: str
    birth_date: str | None = None
    class_id: str | None = None
    learning_gaps: list[dict[str, Any]] | None = None
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
