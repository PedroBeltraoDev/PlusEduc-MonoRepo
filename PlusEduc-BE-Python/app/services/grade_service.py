from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.auth import UserPrincipal
from app.repositories.activity_repository import ActivityRepository
from app.repositories.activity_submission_repository import ActivitySubmissionRepository
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.grade_repository import GradeRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.grade import (
    ActivityGradesLaunchResponse,
    GradeAverageResponse,
    GradeClassroomSummaryResponse,
    GradeCreateRequest,
    GradeResponse,
    GradeStudentSummary,
    GradeUpdateRequest,
)
from app.services.activity_submission_service import ActivitySubmissionService
from app.services.student_analytics_service import StudentAnalyticsService


def _subject_key(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _as_naive_utc(value: Any) -> datetime | None:
    # Datas antigas (seed) ficam como texto ISO; as novas, como datetime. Normaliza as duas.
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value.tzinfo else value


class GradeService:
    def __init__(
        self,
        repository: GradeRepository,
        student_repository: StudentRepository,
        classroom_repository: ClassroomRepository,
        activity_repository: ActivityRepository | None = None,
        submission_repository: ActivitySubmissionRepository | None = None,
    ) -> None:
        self.repository = repository
        self.student_repository = student_repository
        self.classroom_repository = classroom_repository
        self.activity_repository = activity_repository
        self.submission_repository = submission_repository

    def create(self, request: GradeCreateRequest, current_user: UserPrincipal) -> GradeResponse:
        self.validate_references(request.studentId, request.classroomId)
        document = {
            "studentId": request.studentId,
            "classroomId": request.classroomId,
            "grade": request.grade,
            "attendance": request.attendance,
            "subject": request.subject,
            "activityType": request.activityType,
            "observations": request.observations,
            "activityId": request.activityId,
            "date": request.date,
            "createdAt": datetime.now(timezone.utc),
        }
        document = {key: value for key, value in document.items() if value is not None}
        return self.to_response(self.repository.insert(document))

    def list_all(self) -> list[GradeResponse]:
        return [self.to_response(item) for item in self.repository.find_all()]

    def get(self, grade_id: str) -> GradeResponse:
        item = self.repository.find_by_id(grade_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Nota não encontrada: {grade_id}")
        return self.to_response(item)

    def update(self, grade_id: str, request: GradeUpdateRequest, current_user: UserPrincipal) -> GradeResponse:
        current = self.repository.find_by_id(grade_id)
        if not current:
            raise HTTPException(status_code=404, detail=f"Nota não encontrada: {grade_id}")
        values = request.model_dump(exclude_unset=True)
        student_id = values.get("studentId", current.get("studentId"))
        classroom_id = values.get("classroomId", current.get("classroomId"))
        self.validate_references(student_id, classroom_id)
        updates = {key: value for key, value in values.items() if value is not None}
        updated = self.repository.update(grade_id, updates)
        return self.to_response(updated)

    def delete(self, grade_id: str) -> None:
        if not self.repository.delete(grade_id):
            raise HTTPException(status_code=404, detail=f"Nota não encontrada: {grade_id}")

    def by_student(self, student_id: str) -> list[GradeResponse]:
        if not self.student_repository.find_by_id(student_id):
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        return [self.to_response(item) for item in self.repository.find_by_student(student_id)]

    def by_classroom(self, classroom_id: str) -> list[GradeResponse]:
        if not self.classroom_repository.find_by_id(classroom_id):
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")
        return [self.to_response(item) for item in self.repository.find_by_classroom(classroom_id)]

    def average_by_student(self, student_id: str) -> float:
        if not self.student_repository.find_by_id(student_id):
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        grades = self.repository.find_by_student(student_id)
        if not grades:
            return 0.0
        values = [float(item.get("grade", item.get("gradeValue", 0))) for item in grades]
        return sum(values) / len(values)

    def classroom_summary(self, classroom_id: str, subject: str | None = None) -> GradeClassroomSummaryResponse:
        classroom = self.classroom_repository.find_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")
        grades = self.repository.find_by_classroom(classroom_id)
        if subject:
            grades = [item for item in grades if _subject_key(item.get("subject")) == _subject_key(subject)]

        by_student: dict[str, list[dict[str, Any]]] = {}
        for item in grades:
            by_student.setdefault(str(item.get("studentId", item.get("student_id", ""))), []).append(item)

        rows: list[GradeStudentSummary] = []
        for student in self.student_repository.find_active_by_class(classroom_id):
            student_id = str(student.get("_id", student.get("id")))
            items = by_student.get(student_id, [])
            values = [self.grade_value(item) for item in items]
            total_classes, attended, absences, rate = StudentAnalyticsService.attendance_counts(items)
            dates = [parsed for parsed in (_as_naive_utc(item.get("date")) for item in items) if parsed]
            rows.append(GradeStudentSummary(
                studentId=student_id,
                studentName=str(student.get("name", "")),
                average=round(sum(values) / len(values), 2) if values else 0.0,
                launches=len(items),
                totalClasses=total_classes,
                attendedClasses=attended,
                absences=absences,
                attendanceRate=rate,
                lastLaunchAt=max(dates) if dates else None,
            ))
        rows.sort(key=lambda row: row.studentName.lower())

        enrolled_ids = {row.studentId for row in rows}
        class_items = [item for item in grades if str(item.get("studentId", item.get("student_id", ""))) in enrolled_ids]
        class_values = [self.grade_value(item) for item in class_items]
        _, _, _, class_rate = StudentAnalyticsService.attendance_counts(class_items)
        return GradeClassroomSummaryResponse(
            classroomId=classroom_id,
            classroomName=str(classroom.get("name", "")),
            subject=subject or None,
            studentsCount=len(rows),
            totalLaunches=len(class_items),
            averageGrade=round(sum(class_values) / len(class_values), 2) if class_values else 0.0,
            attendanceRate=class_rate,
            students=rows,
        )

    def launch_from_activity(self, activity_id: str, current_user: UserPrincipal) -> ActivityGradesLaunchResponse:
        if self.activity_repository is None or self.submission_repository is None:
            raise HTTPException(status_code=500, detail="Lançamento por atividade indisponível nesta configuração")
        activity = self.activity_repository.find_by_id(activity_id)
        if not activity:
            raise HTTPException(status_code=404, detail=f"Atividade não encontrada: {activity_id}")

        classroom_id = activity.get("classroom_id", activity.get("classroomId"))
        classroom_id = str(classroom_id) if classroom_id else None
        target_student = activity.get("student_id", activity.get("studentId"))
        if classroom_id:
            recipients = [str(item.get("_id")) for item in self.student_repository.find_active_by_class(classroom_id)]
        elif target_student:
            recipients = [str(target_student)]
        else:
            raise HTTPException(status_code=400, detail="Atividade sem turma ou aluno associado")
        if target_student:
            recipients = [item for item in recipients if item == str(target_student)]

        submissions = {
            str(item.get("student_id", item.get("studentId"))): item
            for item in self.submission_repository.find_by_activity(activity_id)
        }
        already = {
            str(item.get("studentId", item.get("student_id")))
            for item in self.repository.find_by_activity(activity_id)
        }

        launched = already_launched = awaiting = not_submitted = 0
        for student_id in recipients:
            submission = submissions.get(student_id)
            if submission is None:
                not_submitted += 1
                continue
            if student_id in already:
                already_launched += 1
                continue
            stored = ActivitySubmissionService.parse_stored_result(submission.get("content", "{}"))
            if stored.pendingCount > 0:
                awaiting += 1
                continue
            student = self.student_repository.find_by_id(student_id)
            student_classroom = classroom_id or str((student or {}).get("class_id", (student or {}).get("classId", "")) or "")
            if not student or not student_classroom:
                not_submitted += 1
                continue
            self.repository.insert({
                "studentId": student_id,
                "classroomId": student_classroom,
                "grade": round(stored.scorePercent / 10, 1),
                "subject": activity.get("subject"),
                "activityType": "ASSIGNMENT",
                "observations": f"Atividade: {activity.get('title', '')}"[:500],
                "activityId": activity_id,
                "date": submission.get("submitted_at", submission.get("submittedAt")) or datetime.now(timezone.utc),
                "createdAt": datetime.now(timezone.utc),
            })
            launched += 1

        return ActivityGradesLaunchResponse(
            activityId=activity_id,
            activityTitle=str(activity.get("title", "")),
            launched=launched,
            alreadyLaunched=already_launched,
            awaitingCorrection=awaiting,
            notSubmitted=not_submitted,
        )

    @staticmethod
    def grade_value(document: dict[str, Any]) -> float:
        value = document.get("grade", document.get("gradeValue"))
        return float(value or 0)

    def validate_references(self, student_id: str, classroom_id: str) -> None:
        if not self.student_repository.find_by_id(student_id):
            raise HTTPException(status_code=400, detail=f"Aluno não encontrado: {student_id}")
        if not self.classroom_repository.find_by_id(classroom_id):
            raise HTTPException(status_code=400, detail=f"Turma não encontrada: {classroom_id}")

    @staticmethod
    def to_response(document: dict[str, Any]) -> GradeResponse:
        raw_id = document.get("_id", document.get("id"))
        value = document.get("grade", document.get("gradeValue"))
        return GradeResponse(
            id=str(raw_id),
            studentId=str(document.get("studentId", document.get("student_id", ""))),
            classroomId=str(document.get("classroomId", document.get("classroom_id", ""))),
            subject=document.get("subject"),
            grade=float(value),
            gradeValue=float(value),
            attendance=document.get("attendance"),
            date=document.get("date"),
            activityType=document.get("activityType", document.get("activity_type")),
            observations=document.get("observations"),
            activityId=document.get("activityId", document.get("activity_id")),
            createdAt=document.get("createdAt", document.get("created_at")),
        )
