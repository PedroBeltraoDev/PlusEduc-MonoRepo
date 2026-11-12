"""Cadastro de professores, sempre sincronizado com a conta de acesso em ``users``.

* A senha nunca é gravada em ``teachers`` (antes era gravada em texto puro). Ela vai, com hash
  bcrypt, apenas para ``users`` — a coleção usada pelo login.
* Criar, alterar e desativar o professor cria/atualiza/desativa a conta de acesso junto.
* Desativar o professor ou trocar a senha encerra as sessões abertas dele.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException

from app.core.passwords import hash_password
from app.repositories.teacher_repository import TeacherRepository
from app.schemas.teacher import TeacherCreateRequest, TeacherResponse, TeacherUpdateRequest

logger = logging.getLogger(__name__)


def normalize_email(value: str) -> str:
    return value.strip().lower()


class TeacherService:
    def __init__(self, repository: TeacherRepository, user_repository=None, refresh_repository=None) -> None:
        self.repository = repository
        self.users = user_repository
        self.refresh_tokens = refresh_repository

    # ---- conta de acesso -------------------------------------------------------------------
    def _find_user(self, email: str) -> dict[str, Any] | None:
        if self.users is None:
            return None
        finder = getattr(self.users, "find_by_email", None) or getattr(self.users, "find_active_by_email", None)
        return finder(email) if finder else None

    def _sync_user(self, email: str, values: dict[str, Any]) -> None:
        if self.users is not None and hasattr(self.users, "update_fields"):
            self.users.update_fields(email, values)

    def _revoke_sessions(self, email: str) -> None:
        if self.users is not None and hasattr(self.users, "revoke_sessions"):
            self.users.revoke_sessions(email)
        if self.refresh_tokens is not None:
            try:
                self.refresh_tokens.revoke_all_for(email)
            except Exception:  # noqa: BLE001
                logger.warning("Não foi possível revogar os refresh tokens do professor")

    # ---- CRUD ------------------------------------------------------------------------------
    def create(self, request: TeacherCreateRequest) -> TeacherResponse:
        email = normalize_email(request.email)
        if self.repository.find_by_email(email) or self._find_user(email):
            raise HTTPException(status_code=409, detail=f"Email já cadastrado: {email}")
        now = datetime.now(timezone.utc)
        active = True if request.active is None else request.active
        document = {
            "name": request.name,
            "email": email,
            "subjects": request.subjects or [],
            "classrooms": request.classroomIds or [],
            "active": active,
            "approvalStatus": "APPROVED",
            "created_at": now,
            "updated_at": now,
        }
        created = self.repository.insert(document)
        if self.users is not None and hasattr(self.users, "insert_teacher_user"):
            try:
                password_hash = hash_password(request.password) if request.password else None
                self.users.insert_teacher_user(email, password_hash, active=active, name=request.name)
            except Exception:
                # Sem conta de acesso o cadastro ficaria órfão: desfaz a inserção do professor.
                if hasattr(self.repository, "delete_by_id"):
                    self.repository.delete_by_id(str(created.get("_id")))
                else:
                    self.repository.soft_delete(str(created.get("_id")), datetime.now(timezone.utc))
                raise
        return self.to_response(created)

    def list_active(self) -> list[TeacherResponse]:
        return [self.to_response(item) for item in self.repository.find_active()]

    def get(self, teacher_id: str) -> TeacherResponse:
        item = self.repository.find_by_id(teacher_id)
        if not item:
            raise HTTPException(status_code=404, detail=f"Professor não encontrado: {teacher_id}")
        return self.to_response(item)

    def by_email(self, email: str) -> TeacherResponse:
        item = self.repository.find_active_by_email(normalize_email(email))
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
        current_email = str(current.get("email", ""))
        new_email = normalize_email(values["email"]) if values.get("email") else current_email
        if new_email != current_email:
            duplicate = self.repository.find_by_email(new_email)
            if (duplicate and str(duplicate.get("_id")) != str(current.get("_id"))) or self._find_user(new_email):
                raise HTTPException(status_code=409, detail=f"Email já cadastrado: {new_email}")

        mapping = {"name": "name", "subjects": "subjects", "classroomIds": "classrooms", "active": "active"}
        updates = {target: values[source] for source, target in mapping.items() if source in values}
        if new_email != current_email:
            updates["email"] = new_email
        updates["updated_at"] = datetime.now(timezone.utc)
        updated = self.repository.update(teacher_id, updates)

        user_updates: dict[str, Any] = {}
        if "name" in values:
            user_updates["name"] = values["name"]
        if new_email != current_email:
            user_updates["email"] = new_email
        if "active" in values and values["active"] is not None:
            user_updates["active"] = bool(values["active"])
        if values.get("password"):
            user_updates["password"] = hash_password(values["password"])
        if user_updates:
            existing_user = self._find_user(current_email)
            if existing_user is None and self.users is not None and hasattr(self.users, "insert_teacher_user"):
                self.users.insert_teacher_user(
                    new_email,
                    user_updates.get("password"),
                    active=bool(updates.get("active", current.get("active", True))),
                    name=updates.get("name", current.get("name")),
                )
            else:
                self._sync_user(current_email, user_updates)
        if "password" in user_updates or user_updates.get("active") is False or "email" in user_updates:
            self._revoke_sessions(new_email)
        return self.to_response(updated)

    def delete(self, teacher_id: str) -> None:
        current = self.repository.find_by_id(teacher_id)
        if not current or not self.repository.soft_delete(teacher_id, datetime.now(timezone.utc)):
            raise HTTPException(status_code=404, detail=f"Professor não encontrado: {teacher_id}")
        email = str(current.get("email", ""))
        # Professor desativado não pode continuar entrando no sistema.
        self._sync_user(email, {"active": False})
        self._revoke_sessions(email)

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
            classroomIds=[str(item) for item in document.get("classrooms", document.get("classroomIds", [])) or []],
            active=document.get("active"),
            approvalStatus=document.get("approvalStatus"),
            createdAt=document.get("created_at", document.get("createdAt")),
            updatedAt=document.get("updated_at", document.get("updatedAt")),
        )
