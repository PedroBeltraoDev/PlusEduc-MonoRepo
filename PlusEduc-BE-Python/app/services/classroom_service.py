from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.auth import UserPrincipal
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.grade_repository import GradeRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.classroom import (
    ClassroomCreateRequest,
    ClassroomPageResponse,
    ClassroomResponse,
    ClassroomUpdateRequest,
    StudentSummary,
    SubjectTeacherSummary,
)
from app.schemas.analytics import ClassroomPerformanceResponse, ClassroomSubjectPerformance
from app.services.curriculum import curriculum_subjects_for_grade, normalize_curriculum_key
from app.services.student_service import StudentService


class ClassroomService:
    def __init__(
        self,
        repository: ClassroomRepository,
        student_repository: StudentRepository,
        teacher_repository: TeacherRepository,
        grade_repository: GradeRepository | None = None,
    ) -> None:
        self.repository = repository
        self.student_repository = student_repository
        self.teacher_repository = teacher_repository
        self.grade_repository = grade_repository

    def create(
        self,
        request: ClassroomCreateRequest,
        current_user: UserPrincipal | None = None,
    ) -> ClassroomResponse:
        self.validate_year(request.year)
        teacher_id = request.teacherId
        if current_user is not None and teacher_id == "current-teacher-id":
            teacher = self.teacher_repository.find_by_id(current_user.user_id) or self.teacher_repository.find_by_email(current_user.email)
            if teacher is None:
                raise HTTPException(status_code=400, detail="Perfil de professor não encontrado para criar a turma")
            teacher_id = str(teacher.get("_id"))
        if self.repository.exists_by_name_and_year(request.name, request.year):
            raise HTTPException(status_code=409, detail="Já existe uma turma com este nome e ano")
        if self.repository.count_active_by_teacher(teacher_id) >= 5:
            raise HTTPException(status_code=400, detail="Limite máximo de 5 turmas ativas por professor")
        student_ids = request.studentIds or []
        self.validate_students_exist(student_ids)
        requested_subjects = request.subjects or []
        if not requested_subjects or (
            len(requested_subjects) == 1
            and normalize_curriculum_key(str(requested_subjects[0])) == normalize_curriculum_key(request.gradeLevel)
        ):
            requested_subjects = curriculum_subjects_for_grade(request.gradeLevel)
        now = datetime.now(timezone.utc)
        document = {
            "name": request.name,
            "year": request.year,
            "grade_level": request.gradeLevel,
            "teacher_id": teacher_id,
            "students": student_ids,
            "subjects": requested_subjects,
            "subjectTeachers": [],
            "active": True if request.active is None else request.active,
            "created_at": now,
            "updated_at": now,
        }
        return self.to_response(self.repository.insert(document))

    def list_active(self) -> list[ClassroomResponse]:
        return [self.to_response(item) for item in self.repository.find_active()]

    def page(self, page: int, size: int) -> ClassroomPageResponse:
        page = max(page, 0)
        size = min(max(size, 1), 100)
        items = self.repository.find_active()
        start = page * size
        content = items[start : start + size]
        total = len(items)
        total_pages = (total + size - 1) // size if total else 0
        return ClassroomPageResponse(
            content=[self.to_response(item) for item in content],
            totalPages=total_pages,
            totalElements=total,
            size=size,
            number=page,
            first=page == 0,
            last=page >= max(total_pages - 1, 0),
        )

    def performance(self, classroom_id: str) -> ClassroomPerformanceResponse:
        classroom = self.repository.find_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")

        grades = self.grade_repository.find_by_classroom(classroom_id) if self.grade_repository else []
        values = [self.grade_value(grade) for grade in grades]
        subject_values: dict[str, list[float]] = {}
        subject_students: dict[str, set[str]] = {}
        for grade, value in zip(grades, values):
            subject = str(grade.get("subject") or "Sem disciplina")
            subject_values.setdefault(subject, []).append(value)
            student_id = grade.get("studentId", grade.get("student_id"))
            if student_id:
                subject_students.setdefault(subject, set()).add(str(student_id))

        subject_performance = [
            ClassroomSubjectPerformance(
                subject=subject,
                average=sum(subject_values[subject]) / len(subject_values[subject]),
                studentsCount=len(subject_students.get(subject, set())),
            )
            for subject in sorted(subject_values)
        ]
        student_ids = classroom.get("students", classroom.get("student_ids", classroom.get("studentIds", []))) or []
        return ClassroomPerformanceResponse(
            classroomId=classroom_id,
            averageGrade=sum(values) / len(values) if values else 0.0,
            studentsCount=len(set(str(student_id) for student_id in student_ids)),
            subjectPerformance=subject_performance,
        )

    @staticmethod
    def grade_value(document: dict[str, Any]) -> float:
        value = document.get("grade", document.get("gradeValue"))
        return float(value or 0)

    def get(self, classroom_id: str) -> ClassroomResponse:
        item = self.repository.find_by_id(classroom_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")
        return self.to_response(item)

    def by_teacher(self, teacher_id: str) -> list[ClassroomResponse]:
        return [self.to_response(item) for item in self.repository.find_active_by_teacher(teacher_id)]

    def by_student(self, student_id: str) -> list[ClassroomResponse]:
        return [self.to_response(item) for item in self.repository.find_active_by_student(student_id)]

    def by_year(self, year: int) -> list[ClassroomResponse]:
        return [self.to_response(item) for item in self.repository.find_active_by_year(year)]

    def update(self, classroom_id: str, request: ClassroomUpdateRequest) -> ClassroomResponse:
        current = self.repository.find_by_id(classroom_id)
        if not current:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")
        values = request.model_dump(exclude_unset=True)
        target_name = values.get("name", current.get("name"))
        target_year = values.get("year", current.get("year"))
        self.validate_year(target_year)
        if self.repository.exists_by_name_and_year(target_name, target_year, classroom_id):
            raise HTTPException(status_code=409, detail="Já existe uma turma com este nome e ano")
        if "studentIds" in values:
            self.validate_students_exist(values["studentIds"] or [])
        if "gradeLevel" in values and (
            "subjects" not in values
            or not values.get("subjects")
            or (
                len(values.get("subjects") or []) == 1
                and normalize_curriculum_key(str(values["subjects"][0])) == normalize_curriculum_key(str(values["gradeLevel"]))
            )
        ):
            values["subjects"] = curriculum_subjects_for_grade(str(values["gradeLevel"]))
        if "teacherId" in values and self.repository.count_active_by_teacher(values["teacherId"], classroom_id) >= 5:
            raise HTTPException(status_code=400, detail="Limite máximo de 5 turmas ativas por professor")
        mapping = {
            "name": "name",
            "year": "year",
            "gradeLevel": "grade_level",
            "teacherId": "teacher_id",
            "studentIds": "students",
            "subjects": "subjects",
            "active": "active",
        }
        updates = {target: values[source] for source, target in mapping.items() if source in values}
        updates["updated_at"] = datetime.now(timezone.utc)
        updated = self.repository.update(classroom_id, updates)
        return self.to_response(updated)

    def delete(self, classroom_id: str) -> None:
        current = self.repository.find_by_id(classroom_id)
        if not current:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")
        if current.get("students", current.get("student_ids", current.get("studentIds", []))):
            raise HTTPException(status_code=400, detail="Não é possível excluir turma com alunos matriculados")
        if not self.repository.soft_delete(classroom_id, datetime.now(timezone.utc)):
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")

    def enroll(self, classroom_id: str, student_id: str) -> None:
        classroom = self.repository.find_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")
        student = self.student_repository.find_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        student_ids = list(classroom.get("students", classroom.get("student_ids", classroom.get("studentIds", []))) or [])
        if student_id not in student_ids:
            student_ids.append(student_id)
        updated = self.repository.update(classroom_id, {"students": student_ids, "updated_at": datetime.now(timezone.utc)})
        self.student_repository.update(student_id, {"class_id": classroom_id, "updated_at": datetime.now(timezone.utc)})

    def unenroll(self, classroom_id: str, student_id: str) -> None:
        classroom = self.repository.find_by_id(classroom_id)
        if not classroom:
            raise HTTPException(status_code=404, detail=f"Turma não encontrada: {classroom_id}")
        student = self.student_repository.find_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        student_ids = [item for item in (classroom.get("students", classroom.get("student_ids", classroom.get("studentIds", []))) or []) if item != student_id]
        self.repository.update(classroom_id, {"students": student_ids, "updated_at": datetime.now(timezone.utc)})
        self.student_repository.update(student_id, {"class_id": None, "updated_at": datetime.now(timezone.utc)})

    def validate_students_exist(self, student_ids: list[str]) -> None:
        missing = [student_id for student_id in student_ids if self.student_repository.find_by_id(student_id) is None]
        if missing:
            raise HTTPException(status_code=400, detail=f"Alunos não encontrados: {', '.join(missing)}")

    @staticmethod
    def validate_year(year: int) -> None:
        current_year = datetime.now(timezone.utc).year
        if year < 2020 or year > current_year + 2:
            raise HTTPException(status_code=400, detail="Ano da turma fora do intervalo permitido")

    def to_response(self, document: dict[str, Any]) -> ClassroomResponse:
        raw_id = document.get("_id", document.get("id"))
        student_ids = list(document.get("students", document.get("student_ids", document.get("studentIds", []))) or [])
        teacher_id = document.get("teacher_id", document.get("teacherId", ""))
        teacher = self.teacher_repository.find_by_id(teacher_id)
        students = []
        for student_id in student_ids:
            student = self.student_repository.find_by_id(student_id)
            if student:
                students.append(
                    StudentSummary(
                        id=str(student.get("_id", student.get("id"))),
                        name=student.get("name", ""),
                        learningGaps=StudentService.to_response(student).learningGaps,
                    )
                )
        subject_teachers = []
        for assignment in document.get("subjectTeachers", []) or []:
            if not isinstance(assignment, dict):
                continue
            assigned_teacher_id = str(assignment.get("teacherId", assignment.get("teacher_id", "")))
            assigned_teacher = self.teacher_repository.find_by_id(assigned_teacher_id)
            subject_teachers.append(
                SubjectTeacherSummary(
                    subjectId=str(assignment.get("subjectId", assignment.get("subject_id", ""))),
                    subjectName=str(assignment.get("subjectName", assignment.get("subject_name", ""))),
                    teacherId=assigned_teacher_id,
                    teacherName=assigned_teacher.get("name") if assigned_teacher else None,
                )
            )

        return ClassroomResponse(
            id=str(raw_id),
            name=document.get("name", ""),
            year=int(document.get("year", 0)),
            gradeLevel=document.get("grade_level", document.get("gradeLevel", "")),
            teacherId=teacher_id,
            teacherName=teacher.get("name") if teacher else None,
            studentIds=student_ids,
            students=students,
            subjects=list(document.get("subjects", []) or []),
            subjectTeachers=subject_teachers,
            active=document.get("active"),
            createdAt=document.get("created_at", document.get("createdAt")),
            updatedAt=document.get("updated_at", document.get("updatedAt")),
        )
