from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.core.auth import UserPrincipal
from app.core.passwords import hash_password
from app.repositories.classroom_reference import ClassroomReferenceRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.user_repository import UserRepository
from app.schemas.student import (
    EnableStudentAccessRequest,
    LearningGapResponse,
    StudentCreateRequest,
    StudentPageResponse,
    StudentResponse,
    StudentUpdateRequest,
)


class StudentService:
    def __init__(
        self,
        repository: StudentRepository,
        classroom_repository: ClassroomReferenceRepository,
        user_repository: UserRepository,
    ) -> None:
        self.repository = repository
        self.classroom_repository = classroom_repository
        self.user_repository = user_repository

    def _next_matricula(self) -> str:
        generator = getattr(self.repository, "next_matricula", None)
        if callable(generator):
            return generator()
        highest = 0
        for item in self.repository.find_active():
            value = str(item.get("matricula", ""))
            if value.startswith("MAT-2026-"):
                try:
                    highest = max(highest, int(value.removeprefix("MAT-2026-")))
                except ValueError:
                    continue
        return f"MAT-2026-{highest + 1:04d}"

    def create(self, request: StudentCreateRequest, current_user: UserPrincipal) -> StudentResponse:
        if self.repository.find_by_email(request.email):
            raise HTTPException(status_code=409, detail=f"Email já cadastrado: {request.email}")
        if request.classId and not self.classroom_repository.exists_by_id(request.classId):
            raise HTTPException(status_code=400, detail="Turma não encontrada")

        now = datetime.now(timezone.utc)
        for _ in range(10):
            document = {
                "name": request.name,
                "email": request.email,
                "matricula": self._next_matricula(),
                "learning_gaps": [gap.to_document() for gap in (request.learningGaps or [])],
                "active": True if request.active is None else request.active,
                "created_at": now,
                "updated_at": now,
                "created_by": current_user.email,
                "updated_by": current_user.email,
            }
            if request.birthDate:
                document["birth_date"] = request.birthDate
            if request.classId:
                document["class_id"] = request.classId
            try:
                return self.to_response(self.repository.insert(document))
            except DuplicateKeyError:
                continue

        raise HTTPException(status_code=409, detail="Não foi possível gerar uma matrícula disponível")

    def list_active(self) -> list[StudentResponse]:
        return [self.to_response(item) for item in self.repository.find_active()]

    def list_unassigned(self) -> list[StudentResponse]:
        return [self.to_response(item) for item in self.repository.find_unassigned_active()]

    def page(self, page: int, size: int) -> StudentPageResponse:
        page = max(page, 0)
        size = min(max(size, 1), 100)
        items = self.repository.find_active()
        start = page * size
        content = items[start : start + size]
        total = len(items)
        total_pages = (total + size - 1) // size if total else 0
        return StudentPageResponse(
            content=[self.to_response(item) for item in content],
            totalPages=total_pages,
            totalElements=total,
            size=size,
            number=page,
            first=page == 0,
            last=page >= max(total_pages - 1, 0),
        )

    def get(self, student_id: str) -> StudentResponse:
        item = self.repository.find_by_id(student_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        return self.to_response(item)

    def by_class(self, class_id: str) -> list[StudentResponse]:
        return [self.to_response(item) for item in self.repository.find_active_by_class(class_id)]

    def by_learning_gap(self, subject: str) -> list[StudentResponse]:
        return [
            self.to_response(item)
            for item in self.repository.find_active_by_learning_gap_subject(subject)
        ]

    def update(self, student_id: str, request: StudentUpdateRequest, current_user: UserPrincipal) -> StudentResponse:
        current = self.repository.find_by_id(student_id)
        if not current:
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        updates: dict[str, Any] = {}
        values = request.model_dump(exclude_unset=True)
        if "email" in values and values["email"] != current.get("email"):
            duplicate = self.repository.find_by_email(values["email"])
            if duplicate and str(duplicate.get("_id")) != str(current.get("_id")):
                raise HTTPException(status_code=409, detail=f"Email já cadastrado: {values['email']}")
        mapping = {
            "name": "name",
            "email": "email",
            "birthDate": "birth_date",
            "classId": "class_id",
            "active": "active",
        }
        for source, target in mapping.items():
            if source in values:
                updates[target] = values[source]
        if "learningGaps" in values:
            updates["learning_gaps"] = [gap.to_document() for gap in (request.learningGaps or [])]
        updates["updated_at"] = datetime.now(timezone.utc)
        updates["updated_by"] = current_user.email
        updated = self.repository.update(student_id, updates)
        return self.to_response(updated)

    def enable_access(self, student_id: str, request: EnableStudentAccessRequest) -> None:
        student = self.repository.find_by_id(student_id)
        if not student:
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        if student.get("user_id"):
            raise HTTPException(status_code=400, detail="Aluno já possui acesso ao portal")
        if self.user_repository.find_active_by_email(student.get("email", "")):
            raise HTTPException(status_code=409, detail="Usuário já cadastrado")
        user_id = self.user_repository.insert_student_user(
            student.get("email", ""),
            hash_password(request.password),
            str(student.get("_id")),
        )
        self.repository.update(
            student_id,
            {"user_id": user_id, "updated_at": datetime.now(timezone.utc)},
        )

    def delete(self, student_id: str) -> None:
        if not self.repository.soft_delete(student_id, datetime.now(timezone.utc)):
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")

    @staticmethod
    def to_response(document: dict[str, Any] | None) -> StudentResponse:
        if document is None:
            raise HTTPException(status_code=404, detail="Aluno não encontrado")
        raw_id = document.get("_id", document.get("id"))
        gaps = []
        for gap in document.get("learning_gaps", document.get("learningGaps", [])) or []:
            gaps.append(
                LearningGapResponse(
                    id=None if gap.get("id") is None else str(gap.get("id")),
                    subject=gap.get("subject", ""),
                    topic=gap.get("topic", ""),
                    severityLevel=gap.get("severity_level", gap.get("severityLevel")),
                    description=gap.get("description"),
                    identifiedAt=gap.get("identified_at", gap.get("identifiedAt")),
                    lastAssessedAt=gap.get("last_assessed_at", gap.get("lastAssessedAt")),
                    improved=gap.get("improved"),
                )
            )
        return StudentResponse(
            id=str(raw_id),
            name=document.get("name", ""),
            email=document.get("email", ""),
            matricula=document.get("matricula"),
            birthDate=document.get("birth_date", document.get("birthDate")),
            learningGaps=gaps,
            classId=document.get("class_id", document.get("classId")),
            className=document.get("class_name", document.get("className", document.get("_class"))),
            active=document.get("active"),
            createdAt=document.get("created_at", document.get("createdAt")),
            updatedAt=document.get("updated_at", document.get("updatedAt")),
        )
