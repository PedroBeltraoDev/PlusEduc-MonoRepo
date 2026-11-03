from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.auth import UserPrincipal
from app.core.passwords import hash_password
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.teacher import TeacherCreateRequest, TeacherResponse, TeacherUpdateRequest


class TeacherService:
    def __init__(self, repository: TeacherRepository, user_repository=None) -> None:
        self.repository = repository
        self.user_repository = user_repository

    def create(self, request: TeacherCreateRequest) -> TeacherResponse:
        if self.repository.find_by_email(request.email):
            raise HTTPException(status_code=409, detail=f"Email já cadastrado: {request.email}")
        if self.user_repository is not None and self.user_repository.find_active_by_email(request.email):
            raise HTTPException(status_code=409, detail=f"Email já cadastrado: {request.email}")
        now = datetime.now(timezone.utc)
        password_hash = hash_password(request.password)  # nunca em texto puro (RNF01)
        document = {
            "name": request.name,
            "email": request.email,
            "password": password_hash,
            "subjects": request.subjects or [],
            "classrooms": request.classroomIds or [],
            "active": True if request.active is None else request.active,
            "created_at": now,
            "updated_at": now,
        }
        created = self.repository.insert(document)
        if self.user_repository is not None:
            self.user_repository.insert_teacher_user(request.email, password_hash)  # sem o login o professor não entraria
        return self.to_response(created)

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
        if updates.get("password"):
            updates["password"] = hash_password(updates["password"])
            if self.user_repository is not None:
                self.user_repository.update_password(current.get("email", ""), updates["password"])
        updates["updated_at"] = datetime.now(timezone.utc)
        return self.to_response(self.repository.update(teacher_id, updates))

    def delete(self, teacher_id: str) -> None:
        current = self.repository.find_by_id(teacher_id)
        if not self.repository.soft_delete(teacher_id, datetime.now(timezone.utc)):
            raise HTTPException(status_code=404, detail=f"Professor não encontrado: {teacher_id}")
        deactivate = getattr(self.user_repository, "deactivate_by_email", None)
        if callable(deactivate) and current:
            deactivate(current.get("email", ""))

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
