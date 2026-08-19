from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.auth import UserPrincipal
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.grade_repository import GradeRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.grade import (
    GradeAverageResponse,
    GradeCreateRequest,
    GradeResponse,
    GradeUpdateRequest,
)


class GradeService:
    def __init__(
        self,
        repository: GradeRepository,
        student_repository: StudentRepository,
        classroom_repository: ClassroomRepository,
    ) -> None:
        self.repository = repository
        self.student_repository = student_repository
        self.classroom_repository = classroom_repository

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
            createdAt=document.get("createdAt", document.get("created_at")),
        )
