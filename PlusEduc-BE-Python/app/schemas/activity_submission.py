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


class StudentSubmissionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    correctCount: int
    totalQuestions: int
    scorePercent: int
    results: list[QuestionResult]


class StoredSubmissionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    answers: list[QuestionAnswer] = Field(default_factory=list)
    correctCount: int = 0
    totalQuestions: int = 0
    scorePercent: int = 0
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
            results=document.get("results", []),
        )
