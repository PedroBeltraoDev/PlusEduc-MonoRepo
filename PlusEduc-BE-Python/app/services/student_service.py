from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
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
        prefix = f"MAT-{datetime.now(timezone.utc).year}-"
        highest = 0
        for item in self.repository.find_active():
            value = str(item.get("matricula", ""))
            if value.startswith(prefix):
                try:
                    highest = max(highest, int(value.removeprefix(prefix)))
                except ValueError:
                    continue
        return f"{prefix}{highest + 1:04d}"

    # ---- coerência aluno, turma e conta de acesso ---------------------------------------
    def _set_membership(self, student_id: str, new_class_id: str | None, old_class_id: str | None) -> None:
        """Atualiza a lista de alunos das turmas quando o class_id do aluno muda."""
        update = getattr(self.classroom_repository, "update", None)
        finder = getattr(self.classroom_repository, "find_by_id", None)
        if update is None or finder is None:
            return
        now = datetime.now(timezone.utc)
        remover = getattr(self.classroom_repository, "remove_student_everywhere", None)
        if remover is not None:
            remover(student_id, keep_classroom_id=new_class_id or None)
        elif old_class_id and old_class_id != new_class_id:
            old = finder(old_class_id)
            if old:
                members = [m for m in old.get("students", []) or [] if str(m) != str(student_id)]
                update(old_class_id, {"students": members, "updated_at": now})
        if new_class_id:
            new = finder(new_class_id)
            if new:
                members = list(new.get("students", []) or [])
                if str(student_id) not in {str(m) for m in members}:
                    members.append(student_id)
                    update(new_class_id, {"students": members, "updated_at": now})

    def _sync_user(self, student: dict[str, Any], values: dict[str, Any], revoke: bool = False) -> None:
        email = str(student.get("email", ""))
        if not email or self.user_repository is None:
            return
        finder = getattr(self.user_repository, "find_by_email", None) or self.user_repository.find_active_by_email
        user = finder(email)
        if not user or user.get("role") != "STUDENT":
            return
        if hasattr(self.user_repository, "update_fields") and values:
            self.user_repository.update_fields(email, values)
        if revoke and hasattr(self.user_repository, "revoke_sessions"):
            self.user_repository.revoke_sessions(values.get("email", email))

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
                created = self.repository.insert(document)
            except DuplicateKeyError:
                continue
            if request.classId:
                # Antes o aluno ganhava class_id, mas não entrava na lista de alunos da turma.
                self._set_membership(str(created.get("_id")), request.classId, None)
            return self.to_response(created)

        raise HTTPException(status_code=409, detail="Não foi possível gerar uma matrícula disponível")

    def list_active(self) -> list[StudentResponse]:
        return [self.to_response(item) for item in self.repository.find_active()]

    def list_unassigned(self) -> list[StudentResponse]:
        return [self.to_response(item) for item in self.repository.find_unassigned_active()]

    def list_scoped(self, scope) -> list[StudentResponse]:
        if scope is None or scope.is_admin:
            return self.list_active()
        finder = getattr(self.repository, "find_active_in_scope", None)
        if finder is not None:
            return [self.to_response(item) for item in finder(scope.classroom_ids, scope.member_ids)]
        return [self.to_response(item) for item in scope.filter_students(self.repository.find_active())]

    def page(self, page: int, size: int, scope=None) -> StudentPageResponse:
        page = max(page, 0)
        size = min(max(size, 1), 100)
        start = page * size
        pager = getattr(self.repository, "find_active_page", None)
        if pager is not None:
            # Paginação no MongoDB (skip/limit + count), sem carregar todos os alunos.
            query: dict[str, Any] = {}
            if scope is not None and not scope.is_admin:
                from app.repositories.base import id_candidates

                ids = list(scope.classroom_ids)
                query = {"$or": [
                    {"class_id": {"$in": ids}},
                    {"classId": {"$in": ids}},
                    {"_id": {"$in": id_candidates(scope.member_ids)}},
                ]}
            content, total = pager(query, start, size)
        else:
            items = self.repository.find_active()
            if scope is not None:
                items = scope.filter_students(items)
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
        if updates.get("class_id") and not self.classroom_repository.exists_by_id(updates["class_id"]):
            raise HTTPException(status_code=400, detail="Turma não encontrada")
        updated = self.repository.update(student_id, updates)
        old_class = str(current.get("class_id", current.get("classId")) or "") or None
        if "class_id" in updates and (updates["class_id"] or None) != old_class:
            self._set_membership(student_id, updates["class_id"] or None, old_class)
        user_values: dict[str, Any] = {}
        if "email" in updates and updates["email"] != current.get("email"):
            user_values["email"] = updates["email"]
        if "name" in updates:
            user_values["name"] = updates["name"]
        if updates.get("active") is False:
            user_values["active"] = False
        elif updates.get("active") is True and current.get("active") is False:
            user_values["active"] = True
        self._sync_user(current, user_values, revoke="email" in user_values or user_values.get("active") is False)
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
        current = self.repository.find_by_id(student_id)
        if not current or not self.repository.soft_delete(student_id, datetime.now(timezone.utc)):
            raise HTTPException(status_code=404, detail=f"Aluno não encontrado: {student_id}")
        # Exclusão lógica coerente: o aluno sai da turma e a conta do portal deixa de entrar.
        self._set_membership(student_id, None, str(current.get("class_id", current.get("classId")) or "") or None)
        self._sync_user(current, {"active": False}, revoke=True)

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
        birth_date = document.get("birth_date", document.get("birthDate"))
        if isinstance(birth_date, datetime):
            birth_date = birth_date.date().isoformat()

        return StudentResponse(
            id=str(raw_id),
            name=document.get("name", ""),
            email=document.get("email", ""),
            matricula=document.get("matricula"),
            birthDate=birth_date,
            learningGaps=gaps,
            classId=document.get("class_id", document.get("classId")),
            className=document.get("class_name", document.get("className", document.get("_class"))),
            active=document.get("active"),
            hasPortalAccess=bool(document.get("user_id")),
            createdAt=document.get("created_at", document.get("createdAt")),
            updatedAt=document.get("updated_at", document.get("updatedAt")),
        )
