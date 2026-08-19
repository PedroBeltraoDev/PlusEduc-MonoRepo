from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubjectTopicCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    subject: str = Field(min_length=2, max_length=80)
    topic: str | None = Field(default=None, min_length=2, max_length=120)


class SubjectTopicUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    subject: str = Field(min_length=2, max_length=80)
    topics: list[str] = Field(default_factory=list, max_length=100)


class SubjectTopicResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    subject: str
    topics: list[str] = Field(default_factory=list)
    createdAt: datetime | None = None
    updatedAt: datetime | None = None
