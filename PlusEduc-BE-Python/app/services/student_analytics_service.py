from typing import Any

from fastapi import HTTPException

from app.compute import GroupStats, stats_by
from app.core.parallel import run_parallel
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
        return self._performance(student_id, self._subject_stats(student_id))

    def attendance(self, student_id: str) -> StudentAttendanceResponse:
        return self._attendance(student_id, self._subject_stats(student_id))

    def overview(self, student_id: str) -> tuple[StudentPerformanceResponse, StudentAttendanceResponse]:
        """Desempenho e frequência com uma única leitura do aluno e das notas."""
        stats = self._subject_stats(student_id)
        return self._performance(student_id, stats), self._attendance(student_id, stats)

    def _subject_stats(self, student_id: str) -> dict[str, GroupStats]:
        _, grades = run_parallel(
            lambda: self.require_student(student_id),
            lambda: self.grade_repository.find_by_student(student_id),
        )
        return stats_by(grades, lambda item: item.get("subject") or "Sem disciplina")

    @staticmethod
    def _performance(student_id: str, stats: dict[str, GroupStats]) -> StudentPerformanceResponse:
        overall = GroupStats.combine(stats.values())
        return StudentPerformanceResponse(
            studentId=student_id,
            averageGrade=overall.average,
            totalActivities=overall.count,
            completedActivities=overall.count,
            subjectPerformance=[
                SubjectPerformance(subject=subject, average=item.average, count=item.count)
                for subject, item in sorted(stats.items())
            ],
        )

    @staticmethod
    def _attendance(student_id: str, stats: dict[str, GroupStats]) -> StudentAttendanceResponse:
        # Só conta como aula o lançamento em que a presença foi registrada: notas vindas
        # de atividades online (attendance ausente) não podem diluir a frequência.
        overall = GroupStats.combine(stats.values())
        return StudentAttendanceResponse(
            studentId=student_id,
            attendanceRate=overall.attendance_rate,
            totalClasses=overall.recorded,
            attendedClasses=overall.attended,
            absences=overall.absences,
        )

    def require_student(self, student_id: str) -> dict[str, Any]:
        student = self.student_repository.find_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        return student
