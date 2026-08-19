from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.auth import UserPrincipal
from app.repositories.activity_repository import ActivityRepository
from app.repositories.activity_submission_repository import ActivitySubmissionRepository
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.activity_submission import (
    PendingCorrectionResponse,
    PendingQuestionResponse,
    ReviewQuestionRequest,
    StudentSubmissionResult,
)
from app.services.activity_submission_service import ActivitySubmissionService


class TeacherCorrectionService:
    def __init__(
        self,
        activity_repository: ActivityRepository,
        submission_repository: ActivitySubmissionRepository,
        classroom_repository: ClassroomRepository,
        student_repository: StudentRepository,
    ) -> None:
        self.activity_repository = activity_repository
        self.submission_repository = submission_repository
        self.classroom_repository = classroom_repository
        self.student_repository = student_repository

    @staticmethod
    def _id(document: dict[str, Any] | None) -> str:
        if not document:
            return ""
        return str(document.get("_id", document.get("id", "")))

    @staticmethod
    def _value(document: dict[str, Any], *keys: str) -> Any:
        for key in keys:
            if key in document:
                return document[key]
        return None

    @staticmethod
    def _matches_user(value: Any, current_user: UserPrincipal) -> bool:
        return str(value or "") in {str(current_user.user_id), str(current_user.email)}

    def _teacher_can_access(self, activity: dict[str, Any], current_user: UserPrincipal) -> bool:
        creator = self._value(activity, "created_by", "createdBy")
        if creator is not None and self._matches_user(creator, current_user):
            return True

        classroom_id = self._value(activity, "classroom_id", "classroomId")
        classroom = self.classroom_repository.find_by_id(str(classroom_id)) if classroom_id else None
        if not classroom:
            return False
        teacher_id = self._value(classroom, "teacher_id", "teacherId")
        return self._matches_user(teacher_id, current_user)

    @staticmethod
    def _is_discursive(question_type: str) -> bool:
        return str(question_type or "").strip().upper() in {"DISCURSIVA", "DISSERTATIVA", "ABERTA", "OPEN_ENDED"}

    def _pending_results(self, stored) -> list[Any]:
        return [
            result
            for result in stored.results
            if self._is_discursive(result.questionType) and result.reviewStatus != "REVIEWED"
        ]

    def list_pending(self, current_user: UserPrincipal) -> list[PendingCorrectionResponse]:
        pending: list[PendingCorrectionResponse] = []
        for submission in self.submission_repository.find_all():
            activity_id = str(self._value(submission, "activity_id", "activityId") or "")
            activity = self.activity_repository.find_by_id(activity_id)
            if not activity or not self._teacher_can_access(activity, current_user):
                continue

            stored = ActivitySubmissionService.parse_stored_result(submission.get("content", "{}"))
            pending_results = self._pending_results(stored)
            if not pending_results:
                continue

            student_id = str(self._value(submission, "student_id", "studentId") or "")
            student = self.student_repository.find_by_id(student_id) or {}
            classroom_id = self._value(activity, "classroom_id", "classroomId")
            classroom = self.classroom_repository.find_by_id(str(classroom_id)) if classroom_id else None
            pending.append(PendingCorrectionResponse(
                submissionId=self._id(submission),
                activityId=activity_id,
                activityTitle=str(activity.get("title", "Atividade")),
                subject=activity.get("subject"),
                topic=activity.get("topic"),
                classroomName=(classroom or {}).get("name"),
                studentId=student_id,
                studentName=str(student.get("name", "Aluno")),
                submittedAt=self._value(submission, "submitted_at", "submittedAt"),
                questions=[PendingQuestionResponse(
                    questionIndex=result.questionIndex,
                    questionText=result.questionText,
                    selectedAnswer=str(result.selectedAnswer or ""),
                    reviewStatus=result.reviewStatus if result.reviewStatus != "AUTO_GRADED" else "PENDING",
                ) for result in pending_results],
            ))
        return pending

    def review_question(
        self,
        submission_id: str,
        question_index: int,
        request: ReviewQuestionRequest,
        current_user: UserPrincipal,
    ) -> StudentSubmissionResult:
        submission = self.submission_repository.find_by_id(submission_id)
        if not submission:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submissão não encontrada")

        activity_id = str(self._value(submission, "activity_id", "activityId") or "")
        activity = self.activity_repository.find_by_id(activity_id)
        if not activity or not self._teacher_can_access(activity, current_user):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submissão não encontrada")

        stored = ActivitySubmissionService.parse_stored_result(submission.get("content", "{}"))
        result = next((item for item in stored.results if item.questionIndex == question_index), None)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Questão não encontrada na submissão")
        if not self._is_discursive(result.questionType):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Somente questões discursivas precisam de correção manual")

        reviewed_at = datetime.now(timezone.utc)
        result.correct = request.correct
        result.reviewStatus = "REVIEWED"
        result.teacherFeedback = request.feedback.strip() if request.feedback and request.feedback.strip() else None
        result.reviewedBy = str(current_user.email or current_user.user_id)
        result.reviewedAt = reviewed_at

        correct_count = sum(1 for item in stored.results if item.correct)
        pending_count = sum(
            1 for item in stored.results
            if self._is_discursive(item.questionType) and item.reviewStatus != "REVIEWED"
        )
        total_questions = len(stored.results)
        score_percent = int((correct_count * 100 / total_questions) + 0.5) if total_questions else 0
        stored.correctCount = correct_count
        stored.totalQuestions = total_questions
        stored.scorePercent = score_percent
        stored.pendingCount = pending_count

        content = json.loads(stored.model_dump_json())
        updated = self.submission_repository.update_content(submission_id, content)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submissão não encontrada")
        return StudentSubmissionResult(
            correctCount=stored.correctCount,
            totalQuestions=stored.totalQuestions,
            scorePercent=stored.scorePercent,
            pendingCount=stored.pendingCount,
            results=stored.results,
        )
