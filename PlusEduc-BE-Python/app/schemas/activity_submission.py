from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class QuestionAnswer(BaseModel):
    model_config = ConfigDict(extra="ignore")

    questionIndex: int = Field(ge=0)
    selectedAnswer: str | None = None


class ActivitySubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    answers: list[QuestionAnswer] = Field(min_length=1)


class QuestionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    questionIndex: int
    questionText: str
    questionType: str
    options: list[str] = Field(default_factory=list)
    selectedAnswer: str | None = None
    correctAnswer: str | None = None
    correct: bool
    reviewStatus: str = "AUTO_GRADED"
    teacherFeedback: str | None = None
    reviewedBy: str | None = None
    reviewedAt: datetime | None = None


class StudentSubmissionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correctCount: int
    totalQuestions: int
    scorePercent: int
    pendingCount: int = 0
    results: list[QuestionResult]


class PendingQuestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questionIndex: int
    questionText: str
    selectedAnswer: str
    reviewStatus: str = "PENDING"


class PendingCorrectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submissionId: str
    activityId: str
    activityTitle: str
    subject: str | None = None
    topic: str | None = None
    classroomName: str | None = None
    studentId: str
    studentName: str
    submittedAt: datetime | None = None
    questions: list[PendingQuestionResponse] = Field(default_factory=list)


class ReviewQuestionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correct: bool
    feedback: str | None = Field(default=None, max_length=2000)


class StoredSubmissionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    answers: list[QuestionAnswer] = Field(default_factory=list)
    correctCount: int = 0
    totalQuestions: int = 0
    scorePercent: int = 0
    pendingCount: int = 0
    results: list[QuestionResult] = Field(default_factory=list)

    @classmethod
    def from_json_document(cls, document: dict[str, Any]) -> "StoredSubmissionResult":
        # Mantém leitura de documentos antigos que ainda não tinham scorePercent.
        correct_count = int(document.get("correctCount", 0))
        total_questions = int(document.get("totalQuestions", 0))
        score_percent = document.get("scorePercent")
        if score_percent is None:
            score_percent = round((correct_count * 100) / total_questions) if total_questions else 0
        return cls(
            answers=document.get("answers", []),
            correctCount=correct_count,
            totalQuestions=total_questions,
            scorePercent=int(score_percent),
            pendingCount=int(document.get("pendingCount", 0)),
            results=document.get("results", []),
        )
