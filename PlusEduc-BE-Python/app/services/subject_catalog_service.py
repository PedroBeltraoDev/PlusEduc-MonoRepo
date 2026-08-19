from datetime import datetime, timezone
import unicodedata
from typing import Any

from fastapi import HTTPException, status

from app.core.auth import UserPrincipal
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.grade_repository import GradeRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.subject_repository import SubjectRepository
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.subject_catalog import (
    SortField,
    SortOrder,
    SubjectClassroomResponse,
    SubjectCreateRequest,
    SubjectResponse,
    SubjectStudentPerformanceResponse,
    SubjectUpdateRequest,
)


class SubjectCatalogService:
    def __init__(
        self,
        subject_repository: SubjectRepository,
        classroom_repository: ClassroomRepository,
        grade_repository: GradeRepository,
        student_repository: StudentRepository,
        teacher_repository: TeacherRepository,
    ) -> None:
        self.subject_repository = subject_repository
        self.classroom_repository = classroom_repository
        self.grade_repository = grade_repository
        self.student_repository = student_repository
        self.teacher_repository = teacher_repository

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.strip().split())

    @classmethod
    def _key(cls, value: str) -> str:
        folded = cls._normalize(value).casefold()
        return "".join(
            character
            for character in unicodedata.normalize("NFKD", folded)
            if not unicodedata.combining(character)
        )

    @classmethod
    def _subject_response(cls, document: dict[str, Any]) -> SubjectResponse:
        return SubjectResponse(
            id=str(document["_id"]),
            name=str(document.get("name", document.get("subject", ""))),
            active=document.get("active", True) is not False,
            createdAt=document.get("created_at", document.get("createdAt")),
            updatedAt=document.get("updated_at", document.get("updatedAt")),
        )

    def list_subjects(self) -> list[SubjectResponse]:
        return [self._subject_response(item) for item in self.subject_repository.find_all_active()]

    def create_subject(self, payload: SubjectCreateRequest) -> SubjectResponse:
        name = self._normalize(payload.name)
        existing = next(
            (
                item
                for item in self.subject_repository.find_all_active()
                if self._key(str(item.get("name", item.get("subject", "")))) == self._key(name)
            ),
            None,
        )
        now = datetime.now(timezone.utc)
        if existing:
            updated = self.subject_repository.update(
                str(existing["_id"]),
                {"name": name, "name_normalized": self._key(name), "active": True, "updated_at": now},
            )
            return self._subject_response(updated or existing)

        document = {
            "name": name,
            "name_normalized": self._key(name),
            "active": True,
            "created_at": now,
            "updated_at": now,
        }
        return self._subject_response(self.subject_repository.insert(document))

    def update_subject(self, subject_id: str, payload: SubjectUpdateRequest) -> SubjectResponse:
        updates: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        if payload.active is not None:
            updates["active"] = payload.active
        updated = self.subject_repository.update(subject_id, updates)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matéria não encontrada")
        return self._subject_response(updated)

    def _subject(self, subject_id: str) -> dict[str, Any]:
        subject = self.subject_repository.find_by_id(subject_id)
        if subject is None or subject.get("active", True) is False:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matéria não encontrada")
        return subject

    def _teacher(self, current_user: UserPrincipal) -> dict[str, Any] | None:
        teacher = self.teacher_repository.find_by_id(current_user.user_id)
        if teacher is None:
            teacher = self.teacher_repository.find_by_email(current_user.email)
        return teacher

    def classrooms_by_subject(self, subject_id: str, current_user: UserPrincipal) -> list[SubjectClassroomResponse]:
        subject = self._subject(subject_id)
        subject_key = self._key(str(subject.get("name", "")))
        teacher = self._teacher(current_user)
        teacher_id = str((teacher or {}).get("_id", current_user.user_id))
        classrooms = self.classroom_repository.find_active_by_teacher(teacher_id)
        if not classrooms and teacher:
            teacher_classrooms = teacher.get("classrooms", teacher.get("classroomIds", [])) or []
            classrooms = [item for item in (self.classroom_repository.find_by_id(str(classroom_id)) for classroom_id in teacher_classrooms) if item and item.get("active", True) is not False]

        result: list[SubjectClassroomResponse] = []
        for classroom in classrooms:
            subjects = classroom.get("subjects", []) or []
            if not any(self._key(str(value)) == subject_key for value in subjects):
                continue
            student_ids = [str(value) for value in (classroom.get("students", classroom.get("studentIds", [])) or [])]
            performance = self._performance_rows(str(classroom["_id"]), subject_key, student_ids)
            grades = [row.averageGrade for row in performance if row.gradeCount > 0]
            result.append(SubjectClassroomResponse(
                id=str(classroom["_id"]),
                name=str(classroom.get("name", "")),
                year=classroom.get("year"),
                gradeLevel=classroom.get("grade_level", classroom.get("gradeLevel")),
                studentCount=len(student_ids),
                averageGrade=round(sum(grades) / len(grades), 2) if grades else 0,
            ))
        return result

    def _performance_rows(self, classroom_id: str, subject_key: str, student_ids: list[str]) -> list[SubjectStudentPerformanceResponse]:
        grades = self.grade_repository.find_by_classroom(classroom_id)
        grouped: dict[str, list[dict[str, Any]]] = {}
        for grade in grades:
            subject = grade.get("subject", "")
            if self._key(str(subject)) != subject_key:
                continue
            student_id = str(grade.get("studentId", grade.get("student_id", "")))
            if student_id:
                grouped.setdefault(student_id, []).append(grade)

        ids = student_ids or list(grouped.keys())
        rows: list[SubjectStudentPerformanceResponse] = []
        for student_id in ids:
            student = self.student_repository.find_by_id(student_id) or {}
            student_grades = grouped.get(student_id, [])
            values: list[float] = []
            for grade in student_grades:
                value = grade.get("grade", grade.get("gradeValue", grade.get("grade_value")))
                try:
                    values.append(float(value))
                except (TypeError, ValueError):
                    continue
            rows.append(SubjectStudentPerformanceResponse(
                studentId=student_id,
                studentName=str(student.get("name", "Aluno")),
                studentEmail=student.get("email"),
                averageGrade=round(sum(values) / len(values), 2) if values else 0,
                gradeCount=len(values),
                lastGrade=values[-1] if values else None,
            ))
        return rows

    def student_performance(
        self,
        subject_id: str,
        classroom_id: str,
        current_user: UserPrincipal,
        sort_by: SortField = "name",
        order: SortOrder = "asc",
    ) -> list[SubjectStudentPerformanceResponse]:
        classrooms = self.classrooms_by_subject(subject_id, current_user)
        classroom = next((item for item in classrooms if item.id == classroom_id), None)
        if classroom is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada para esta matéria")
        subject = self._subject(subject_id)
        raw_classroom = self.classroom_repository.find_by_id(classroom_id)
        student_ids = [str(value) for value in (raw_classroom or {}).get("students", (raw_classroom or {}).get("studentIds", [])) or []]
        rows = self._performance_rows(classroom_id, self._key(str(subject.get("name", ""))), student_ids)
        reverse = order == "desc"
        if sort_by == "grade":
            rows.sort(key=lambda row: (row.averageGrade, row.studentName.casefold()), reverse=reverse)
        else:
            rows.sort(key=lambda row: row.studentName.casefold(), reverse=reverse)
        return rows
