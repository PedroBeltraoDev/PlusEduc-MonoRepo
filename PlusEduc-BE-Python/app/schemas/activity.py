from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GeneratedQuestion(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    questionText: str
    questionType: str
    options: list[str] = Field(default_factory=list)
    correctAnswer: str | None = None
    explanation: str | None = None
    difficultyLevel: str | None = None


class ActivityCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    title: str = Field(min_length=5, max_length=200)
    subject: str | None = None
    topic: str | None = Field(default=None, min_length=3, max_length=100)
    difficultyLevel: str
    questionsCount: int = Field(ge=1, le=100)
    format: str
    classroomId: str = Field(min_length=1)
    studentId: str | None = None
    disabilityAdaptations: list[str] | None = None
    questions: list[GeneratedQuestion] | None = None
    content: str | None = Field(default=None, max_length=10000)
    pdfUrl: str | None = None


class ActivityGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    classroomId: str = Field(min_length=1)
    studentId: str | None = None
    subject: str = Field(min_length=3, max_length=50)
    topic: str = Field(min_length=3, max_length=100)
    difficultyLevel: str
    questionsCount: int = Field(ge=1, le=50)
    format: str
    disabilityAdaptations: list[str] = Field(default_factory=list)
    learningGapId: str | None = None
    additionalInstructions: str | None = Field(default=None, max_length=500)


class ActivityUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    title: str | None = Field(default=None, min_length=5, max_length=200)
    subject: str | None = None
    topic: str | None = Field(default=None, min_length=3, max_length=100)
    difficultyLevel: str | None = None
    questionsCount: int | None = Field(default=None, ge=1, le=100)
    format: str | None = None
    classroomId: str | None = None
    studentId: str | None = None
    disabilityAdaptations: list[str] | None = None
    questions: list[GeneratedQuestion] | None = None
    content: str | None = Field(default=None, max_length=10000)
    pdfUrl: str | None = None


class ActivityParticipant(BaseModel):
    model_config = ConfigDict(extra="forbid")

    studentId: str
    studentName: str
    submittedAt: datetime | None = None


class ActivityParticipation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    totalStudents: int = 0
    completedStudents: int = 0
    pendingStudents: int = 0
    completed: list[ActivityParticipant] = Field(default_factory=list)
    pending: list[ActivityParticipant] = Field(default_factory=list)


class ActivityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    subject: str | None = None
    topic: str | None = None
    difficultyLevel: str | None = None
    questionsCount: int | None = None
    format: str | None = None
    classroomId: str | None = None
    classroomName: str | None = None
    studentId: str | None = None
    studentName: str | None = None
    disabilityAdaptations: list[str] = Field(default_factory=list)
    questions: list[GeneratedQuestion] = Field(default_factory=list)
    content: str | None = None
    pdfUrl: str | None = None
    generatedByAi: bool | None = None
    aiProvider: str | None = None
    createdBy: str | None = None
    creatorName: str | None = None
    createdAt: datetime | None = None
    participation: ActivityParticipation | None = None
