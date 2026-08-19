from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.auth import UserPrincipal
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.teacher import TeacherCreateRequest, TeacherResponse, TeacherUpdateRequest


class TeacherService:
    def __init__(self, repository: TeacherRepository) -> None:
        self.repository = repository

    def create(self, request: TeacherCreateRequest) -> TeacherResponse:
        if self.repository.find_by_email(request.email):
            raise HTTPException(status_code=409, detail=f"Email já cadastrado: {request.email}")
        now = datetime.now(timezone.utc)
        document = {
            "name": request.name,
            "email": request.email,
            "password": request.password,
            "subjects": request.subjects or [],
            "classrooms": request.classroomIds or [],
            "active": True if request.active is None else request.active,
            "created_at": now,
            "updated_at": now,
        }
        return self.to_response(self.repository.insert(document))

    def list_active(self) -> list[TeacherResponse]:
        return [self.to_response(item) for item in self.repository.find_active()]

    def get(self, teacher_id: str) -> TeacherResponse:
        item = self.repository.find_by_id(teacher_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Professor não encontrado: {teacher_id}")
        return self.to_response(item)

    def by_email(self, email: str) -> TeacherResponse:
        item = self.repository.find_active_by_email(email)
        if not item:
            raise HTTPException(status_code=404, detail=f"Professor não encontrado: {email}")
        return self.to_response(item)

    def by_subject(self, subject: str) -> list[TeacherResponse]:
        return [self.to_response(item) for item in self.repository.find_active_by_subject(subject)]

    def update(self, teacher_id: str, request: TeacherUpdateRequest) -> TeacherResponse:
        current = self.repository.find_by_id(teacher_id)
        if not current:
            raise HTTPException(status_code=404, detail=f"Professor não encontrado: {teacher_id}")
        values = request.model_dump(exclude_unset=True)
        if "email" in values and values["email"] != current.get("email"):
            duplicate = self.repository.find_by_email(values["email"])
            if duplicate and str(duplicate.get("_id")) != str(current.get("_id")):
                raise HTTPException(status_code=409, detail=f"Email já cadastrado: {values['email']}")
        mapping = {
            "name": "name",
            "email": "email",
            "password": "password",
            "subjects": "subjects",
            "classroomIds": "classrooms",
            "active": "active",
        }
        updates = {target: values[source] for source, target in mapping.items() if source in values}
        updates["updated_at"] = datetime.now(timezone.utc)
        return self.to_response(self.repository.update(teacher_id, updates))

    def delete(self, teacher_id: str) -> None:
        if not self.repository.soft_delete(teacher_id, datetime.now(timezone.utc)):
            raise HTTPException(status_code=404, detail=f"Professor não encontrado: {teacher_id}")

    def count(self) -> int:
        return self.repository.count_all()

    @staticmethod
    def to_response(document: dict[str, Any]) -> TeacherResponse:
        raw_id = document.get("_id", document.get("id"))
        return TeacherResponse(
            id=str(raw_id),
            name=document.get("name", ""),
            email=document.get("email", ""),
            subjects=document.get("subjects", []),
            classroomIds=document.get("classrooms", document.get("classroomIds", [])),
            active=document.get("active"),
            createdAt=document.get("created_at", document.get("createdAt")),
            updatedAt=document.get("updated_at", document.get("updatedAt")),
        )
