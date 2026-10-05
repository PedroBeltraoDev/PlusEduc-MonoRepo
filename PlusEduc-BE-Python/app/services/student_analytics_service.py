from collections import defaultdict
from typing import Any

from fastapi import HTTPException

from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.grade_repository import GradeRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.analytics import (
    StudentAttendanceResponse,
    StudentPerformanceResponse,
    SubjectPerformance,
)


class StudentAnalyticsService:
    def __init__(
        self,
        student_repository: StudentRepository,
        grade_repository: GradeRepository,
        classroom_repository: ClassroomRepository,
    ) -> None:
        self.student_repository = student_repository
        self.grade_repository = grade_repository
        self.classroom_repository = classroom_repository

    def performance(self, student_id: str) -> StudentPerformanceResponse:
        self.require_student(student_id)
        grades = self.grade_repository.find_by_student(student_id)
        values = [self.grade_value(item) for item in grades]
        subject_values: dict[str, list[float]] = defaultdict(list)
        for item in grades:
            subject = item.get("subject") or "Sem disciplina"
            subject_values[subject].append(self.grade_value(item))
        subject_performance = [
            SubjectPerformance(
                subject=subject,
                average=sum(values_for_subject) / len(values_for_subject),
                count=len(values_for_subject),
            )
            for subject, values_for_subject in sorted(subject_values.items())
        ]
        total = len(values)
        return StudentPerformanceResponse(
            studentId=student_id,
            averageGrade=sum(values) / total if total else 0.0,
            totalActivities=total,
            completedActivities=total,
            subjectPerformance=subject_performance,
        )

    def attendance(self, student_id: str) -> StudentAttendanceResponse:
        self.require_student(student_id)
        grades = self.grade_repository.find_by_student(student_id)
        total_classes, attended, absences, attendance_rate = self.attendance_counts(grades)
        return StudentAttendanceResponse(
            studentId=student_id,
            attendanceRate=attendance_rate,
            totalClasses=total_classes,
            attendedClasses=attended,
            absences=absences,
        )

    def require_student(self, student_id: str) -> dict[str, Any]:
        student = self.student_repository.find_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        return student

    @staticmethod
    def attendance_counts(grades: list[dict[str, Any]]) -> tuple[int, int, int, int]:
        # Só conta como aula o lançamento em que a presença foi registrada: notas vindas
        # de atividades online (attendance ausente) não podem diluir a frequência.
        recorded = [item.get("attendance") for item in grades if item.get("attendance") is not None]
        total_classes = len(recorded)
        attended = sum(1 for value in recorded if value is True)
        absences = total_classes - attended
        attendance_rate = int((attended * 100) / total_classes) if total_classes else 0
        return total_classes, attended, absences, attendance_rate

    @staticmethod
    def grade_value(document: dict[str, Any]) -> float:
        value = document.get("grade", document.get("gradeValue"))
        return float(value or 0)
