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
    SubjectAssignmentRequest,
    SubjectAssignmentResponse,
    SubjectClassroomResponse,
    SubjectCreateRequest,
    SubjectResponse,
    SubjectStudentPerformanceResponse,
    SubjectUpdateRequest,
)
from app.services.curriculum import (
    all_curriculum_subjects,
    curriculum_subjects_for_grade,
    normalize_curriculum_key,
    subject_area,
)


def classroom_id_not_in(classroom_id: Any, classroom_ids: list[Any]) -> bool:
    return str(classroom_id) not in {str(value) for value in classroom_ids}


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
            area=document.get("area"),
            gradeLevels=document.get("grade_levels", document.get("gradeLevels")),
            curriculumKey=document.get("curriculum_key", document.get("curriculumKey")),
        )

    def list_subjects(self) -> list[SubjectResponse]:
        result: list[SubjectResponse] = []
        seen: set[str] = set()
        for item in self.subject_repository.find_all_active():
            key = self._key(str(item.get("name", item.get("subject", ""))))
            if key in seen:
                continue
            seen.add(key)
            result.append(self._subject_response(item))
        return result

    def _catalog_subject_for_name(self, name: str) -> dict[str, Any] | None:
        normalized = self._key(name)
        return next(
            (
                item
                for item in self.subject_repository.find_all_active()
                if self._key(str(item.get("name", item.get("subject", "")))) == normalized
            ),
            None,
        )

    def create_subject(self, payload: SubjectCreateRequest) -> SubjectResponse:
        name = self._normalize(payload.name)
        matches = [
            item
            for item in self.subject_repository.find_all()
            if self._key(str(item.get("name", item.get("subject", "")))) == self._key(name)
        ]
        existing = next((item for item in matches if item.get("active", True) is not False), None)
        if existing is None and matches:
            existing = matches[-1]
        now = datetime.now(timezone.utc)
        if existing:
            for duplicate in matches:
                if str(duplicate["_id"]) != str(existing["_id"]):
                    self.subject_repository.update(str(duplicate["_id"]), {"active": False, "updated_at": now})
            updated = self.subject_repository.update(
                str(existing["_id"]),
                {"name": name, "name_normalized": self._key(name), "active": True, "updated_at": now},
            )
            return self._subject_response(updated or existing)

        document = {
            "name": name,
            "name_normalized": self._key(name),
            "active": True,
            "area": payload.area or subject_area(name),
            "grade_levels": payload.gradeLevels,
            "curriculum_key": normalize_curriculum_key(name),
            "created_at": now,
            "updated_at": now,
        }
        return self._subject_response(self.subject_repository.insert(document))

    def update_subject(self, subject_id: str, payload: SubjectUpdateRequest) -> SubjectResponse:
        current = self.subject_repository.find_by_id(subject_id)
        if current is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matéria não encontrada")

        updates: dict[str, Any] = {"updated_at": datetime.now(timezone.utc)}
        if payload.active is not None:
            updates["active"] = payload.active

        if payload.active is False:
            subject_key = self._key(str(current.get("name", current.get("subject", ""))))
            matching = [
                item
                for item in self.subject_repository.find_all()
                if self._key(str(item.get("name", item.get("subject", "")))) == subject_key
            ]
            for item in matching:
                self.subject_repository.update(str(item["_id"]), updates)
            updated = self.subject_repository.find_by_id(subject_id)
        else:
            updated = self.subject_repository.update(subject_id, updates)

        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matéria não encontrada")
        return self._subject_response(updated)

    def list_available_subjects(self, classroom_id: str, current_user: UserPrincipal) -> list[SubjectResponse]:
        classroom = self.classroom_repository.find_by_id(classroom_id)
        if classroom is None or classroom.get("active", True) is False:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")
        self._assert_teacher_profile(current_user)

        curriculum = curriculum_subjects_for_grade(str(classroom.get("grade_level", classroom.get("gradeLevel", ""))))
        if not curriculum:
            curriculum = all_curriculum_subjects()
        assigned_keys = {
            str(item.get("subjectKey", ""))
            for item in (classroom.get("subjectTeachers", []) or [])
            if isinstance(item, dict)
        }

        available: list[SubjectResponse] = []
        for name in curriculum:
            if self._key(name) in assigned_keys:
                continue
            subject = self._catalog_subject_for_name(name)
            if subject is not None:
                available.append(self._subject_response(subject))
        return available

    def _assert_teacher_profile(self, current_user: UserPrincipal) -> None:
        if current_user.role == "ADMIN":
            return
        if self._teacher(current_user) is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perfil de professor não encontrado")

    def assign_subject(self, payload: SubjectAssignmentRequest, current_user: UserPrincipal) -> SubjectAssignmentResponse:
        classroom = self.classroom_repository.find_by_id(payload.classroomId)
        if classroom is None or classroom.get("active", True) is False:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")
        self._assert_teacher_profile(current_user)
        subject = self._subject(payload.subjectId)
        subject_name = str(subject.get("name", subject.get("subject", "")))
        curriculum = curriculum_subjects_for_grade(str(classroom.get("grade_level", classroom.get("gradeLevel", ""))))
        if curriculum and self._key(subject_name) not in {self._key(value) for value in curriculum}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Matéria não pertence ao currículo desta série")

        teacher = self._teacher(current_user)
        if teacher is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Perfil de professor não encontrado")
        teacher_id = str(teacher.get("_id"))
        now = datetime.now(timezone.utc)
        assignment = {
            "subjectId": str(subject.get("_id")),
            "subjectKey": self._key(subject_name),
            "subjectName": subject_name,
            "teacherId": teacher_id,
            "assignedAt": now,
        }
        updated = self.classroom_repository.add_subject_teacher(payload.classroomId, assignment)
        if updated is None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Esta matéria já possui professor nesta turma")

        subjects = list(updated.get("subjects", []) or [])
        if not any(self._key(str(value)) == self._key(subject_name) for value in subjects):
            subjects.append(subject_name)
        else:
            subjects = [subject_name if self._key(str(value)) == self._key(subject_name) else value for value in subjects]
        self.classroom_repository.update(payload.classroomId, {"subjects": subjects, "updated_at": now})

        teacher_subjects = list(teacher.get("subjects", []) or [])
        if not any(self._key(str(value)) == self._key(subject_name) for value in teacher_subjects):
            teacher_subjects.append(subject_name)
        else:
            teacher_subjects = [subject_name if self._key(str(value)) == self._key(subject_name) else value for value in teacher_subjects]
        teacher_classrooms = list(teacher.get("classrooms", teacher.get("classroomIds", [])) or [])
        if payload.classroomId not in [str(value) for value in teacher_classrooms]:
            teacher_classrooms.append(payload.classroomId)
        self.teacher_repository.update(
            teacher_id,
            {"subjects": teacher_subjects, "classrooms": teacher_classrooms, "updated_at": now},
        )
        return SubjectAssignmentResponse(
            classroomId=payload.classroomId,
            subjectId=str(subject.get("_id")),
            subjectName=subject_name,
            teacherId=teacher_id,
            teacherName=teacher.get("name"),
        )

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
