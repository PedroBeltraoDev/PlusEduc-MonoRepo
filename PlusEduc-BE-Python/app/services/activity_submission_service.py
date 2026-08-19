from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.auth import UserPrincipal
from app.repositories.activity_repository import ActivityRepository
from app.repositories.activity_submission_repository import ActivitySubmissionRepository
from app.schemas.activity_submission import (
    ActivitySubmissionRequest,
    QuestionResult,
    StoredSubmissionResult,
    StudentSubmissionResult,
)

from app.services.activity_service import ActivityService


class ActivitySubmissionService:
    def __init__(self, activity_repository: ActivityRepository, submission_repository: ActivitySubmissionRepository, activity_service: ActivityService) -> None:
        self.activity_repository = activity_repository
        self.submission_repository = submission_repository
        self.activity_service = activity_service

    def submit(self, activity_id: str, request: ActivitySubmissionRequest, current_user: UserPrincipal) -> StudentSubmissionResult:
        student_id = getattr(current_user, "student_id", None)
        if not student_id:
            raise HTTPException(status_code=400, detail="Usuário autenticado não está associado a um estudante")
        return self.submit_for_student(activity_id, request, student_id)

    def submit_for_student(
        self,
        activity_id: str,
        request: ActivitySubmissionRequest,
        student_id: str,
        activity: dict[str, Any] | None = None,
    ) -> StudentSubmissionResult:
        activity = activity or self.activity_repository.find_by_id(activity_id)
        if not activity:
            raise HTTPException(status_code=404, detail=f"Atividade não encontrada: {activity_id}")
        if self.submission_repository.find_by_activity_student(activity_id, student_id):
            raise HTTPException(status_code=409, detail="Esta atividade já foi enviada")
        result = self.calculate(activity, request)
        self.submission_repository.insert({
            "activity_id": activity_id,
            "student_id": student_id,
            "content": json.dumps({
                "answers": [item.model_dump() for item in request.answers],
                **result.model_dump(),
            }, ensure_ascii=False),
            "submitted_at": datetime.now(timezone.utc),
        })
        return result

    def get_submission(self, activity_id: str, current_user: UserPrincipal) -> StudentSubmissionResult:
        student_id = getattr(current_user, "student_id", None)
        if not student_id:
            raise HTTPException(status_code=400, detail="Usuário autenticado não está associado a um estudante")
        return self.get_submission_for_student(activity_id, student_id)

    def get_submission_for_student(self, activity_id: str, student_id: str) -> StudentSubmissionResult:
        document = self.submission_repository.find_by_activity_student(activity_id, student_id)
        if not document:
            raise HTTPException(status_code=404, detail="Submissão não encontrada")
        stored = self.parse_stored_result(document.get("content", "{}"))
        return StudentSubmissionResult(
            correctCount=stored.correctCount,
            totalQuestions=stored.totalQuestions,
            scorePercent=stored.scorePercent,
            pendingCount=stored.pendingCount,
            results=stored.results,
        )

    @staticmethod
    def parse_stored_result(content: str | dict[str, Any]) -> StoredSubmissionResult:
        if isinstance(content, dict):
            raw = content
        else:
            try:
                raw = json.loads(content or "{}")
            except (json.JSONDecodeError, TypeError):
                return StoredSubmissionResult(
                    results=[QuestionResult(
                        questionIndex=0,
                        questionText="Resposta enviada",
                        questionType="DISCURSIVA",
                        options=[],
                        selectedAnswer=str(content),
                        correctAnswer="",
                        correct=True,
                    )],
                    correctCount=1,
                    totalQuestions=1,
                    scorePercent=100,
                    pendingCount=1,
                )
        if not isinstance(raw, dict):
            raise HTTPException(status_code=500, detail="Submissão persistida possui formato inválido")
        try:
            return StoredSubmissionResult.from_json_document(raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=500, detail="Submissão persistida possui formato inválido")

    def calculate(self, activity: dict[str, Any], request: ActivitySubmissionRequest) -> StudentSubmissionResult:
        questions = self.activity_service.parse_questions(activity.get("content"))
        if not questions:
            raise HTTPException(status_code=400, detail="Esta atividade não possui questões para responder online")
        self.validate_all_questions_answered(len(questions), request)
        answer_map = {answer.questionIndex: answer.selectedAnswer for answer in request.answers}
        result_rows: list[QuestionResult] = []
        for index, question in enumerate(questions):
            selected = answer_map[index]
            discursive = self.is_discursive_question(question.questionType)
            correct_answer = None if discursive else self.resolve_correct_answer_label(question)
            result_rows.append(QuestionResult(
                questionIndex=index,
                questionText=question.questionText,
                questionType=question.questionType,
                options=question.options or [],
                selectedAnswer=selected,
                correctAnswer=correct_answer,
                correct=False if discursive else self.is_answer_correct(question, selected),
                reviewStatus="PENDING" if discursive else "AUTO_GRADED",
            ))
        correct_count = sum(1 for row in result_rows if row.correct)
        pending_count = sum(1 for row in result_rows if row.reviewStatus == "PENDING")
        total_questions = len(questions)
        score_percent = int((correct_count * 100 / total_questions) + 0.5) if total_questions else 0
        return StudentSubmissionResult(
            correctCount=correct_count,
            totalQuestions=total_questions,
            scorePercent=score_percent,
            pendingCount=pending_count,
            results=result_rows,
        )

    @staticmethod
    def validate_all_questions_answered(total_questions: int, request: ActivitySubmissionRequest) -> None:
        if len(request.answers) != total_questions:
            raise HTTPException(status_code=400, detail="Responda todas as questões antes de enviar")
        indexes: set[int] = set()
        for answer in request.answers:
            if answer.questionIndex < 0 or answer.questionIndex >= total_questions:
                raise HTTPException(status_code=400, detail="Resposta de questão inválida")
            if answer.selectedAnswer is None or not answer.selectedAnswer.strip():
                raise HTTPException(status_code=400, detail="Selecione uma alternativa em cada questão")
            indexes.add(answer.questionIndex)
        if len(indexes) != total_questions:
            raise HTTPException(status_code=400, detail="Responda todas as questões antes de enviar")

    @staticmethod
    def is_discursive_question(question_type: str) -> bool:
        return str(question_type or "").strip().upper() in {"DISCURSIVA", "DISSERTATIVA", "ABERTA", "OPEN_ENDED"}

    @classmethod
    def resolve_correct_answer_label(cls, question) -> str:
        correct = (question.correctAnswer or "").strip()
        options = question.options or []
        if len(correct) == 1 and correct.upper() in "ABCD" and options:
            index = ord(correct.upper()) - ord("A")
            if 0 <= index < len(options):
                return options[index]
        return correct

    @classmethod
    def is_answer_correct(cls, question, selected: str | None) -> bool:
        if selected is None or not selected.strip() or question.correctAnswer is None:
            return False
        selected_normalized = selected.strip()
        correct = question.correctAnswer.strip()
        options = question.options or []
        if len(correct) == 1 and correct.upper() in "ABCD":
            index = ord(correct.upper()) - ord("A")
            if 0 <= index < len(options):
                return options[index].strip().lower() == selected_normalized.lower() or selected_normalized.lower() == correct.lower()
        return selected_normalized.lower() == correct.lower()
