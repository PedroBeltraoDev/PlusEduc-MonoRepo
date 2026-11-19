"""Escopo de acesso por perfil: o que cada usuário da equipe pode ver e alterar.

ADMIN enxerga e altera tudo. TEACHER só atua nas turmas sob sua responsabilidade:

* turmas em que é o professor titular (``teacher_id``);
* turmas em que foi atribuído a uma disciplina (``subjectTeachers``);
* turmas listadas no próprio cadastro (``classrooms``/``classroomIds``, formato legado).

Um TEACHER sem cadastro ativo em ``teachers`` não recebe permissão nenhuma (antes, a ausência
do cadastro liberava o acesso em algumas rotas). A autorização acontece sempre aqui, no backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from fastapi import Depends, HTTPException, Request, status

from app.core.auth import UserPrincipal
from app.dependencies import require_roles

FORBIDDEN_CLASSROOM = "Você não tem acesso a esta turma"
FORBIDDEN_STUDENT = "Você não tem acesso a este aluno"
FORBIDDEN_ACTIVITY = "Você não tem acesso a esta atividade"
TEACHER_PROFILE_MISSING = "Perfil de professor não encontrado ou inativo"


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def classroom_teacher_ids(classroom: dict[str, Any]) -> set[str]:
    """Todos os professores ligados à turma (titular e professores de disciplina)."""
    ids = {_text(classroom.get("teacher_id", classroom.get("teacherId")))}
    for assignment in classroom.get("subjectTeachers", []) or []:
        if isinstance(assignment, dict):
            ids.add(_text(assignment.get("teacherId", assignment.get("teacher_id"))))
    ids.discard("")
    return ids


def classroom_member_ids(classroom: dict[str, Any]) -> set[str]:
    members = classroom.get("students", classroom.get("student_ids", classroom.get("studentIds", []))) or []
    return {_text(member) for member in members}


def student_classroom_id(student: dict[str, Any]) -> str:
    return _text(student.get("class_id", student.get("classId")))


@dataclass
class AccessScope:
    principal: UserPrincipal
    teacher: dict[str, Any] | None = None
    classroom_ids: set[str] = field(default_factory=set)
    member_ids: set[str] = field(default_factory=set)

    @property
    def is_admin(self) -> bool:
        return self.principal.role == "ADMIN"

    @property
    def teacher_id(self) -> str | None:
        return _text(self.teacher.get("_id")) if self.teacher else None

    @property
    def actor_keys(self) -> set[str]:
        """Identificadores com que o usuário aparece em ``created_by`` e afins."""
        keys = {self.principal.user_id, self.principal.email, self.principal.email.lower()}
        if self.teacher_id:
            keys.add(self.teacher_id)
        keys.discard("")
        return keys

    # ---- turmas ------------------------------------------------------------------------
    def can_access_classroom(self, classroom_id: Any) -> bool:
        return self.is_admin or _text(classroom_id) in self.classroom_ids

    def require_classroom(self, classroom_id: Any) -> None:
        if not self.can_access_classroom(classroom_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_CLASSROOM)

    def filter_classrooms(self, classrooms: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        if self.is_admin:
            return list(classrooms)
        return [item for item in classrooms if _text(item.get("_id", item.get("id"))) in self.classroom_ids]

    # ---- alunos ------------------------------------------------------------------------
    def can_access_student(self, student: dict[str, Any] | None, allow_unassigned: bool = False) -> bool:
        if self.is_admin:
            return True
        if not student:
            return False
        student_id = _text(student.get("_id", student.get("id")))
        if student_id in self.member_ids or student_classroom_id(student) in self.classroom_ids:
            return True
        return allow_unassigned and not student_classroom_id(student)

    def require_student(self, student: dict[str, Any] | None, allow_unassigned: bool = False) -> None:
        if not self.can_access_student(student, allow_unassigned):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_STUDENT)

    def filter_students(self, students: Iterable[dict[str, Any]], allow_unassigned: bool = False) -> list[dict[str, Any]]:
        if self.is_admin:
            return list(students)
        return [item for item in students if self.can_access_student(item, allow_unassigned)]

    # ---- atividades --------------------------------------------------------------------
    def can_access_activity(self, activity: dict[str, Any] | None) -> bool:
        if self.is_admin:
            return True
        if not activity:
            return False
        classroom_id = activity.get("classroom_id", activity.get("classroomId"))
        if classroom_id:
            return _text(classroom_id) in self.classroom_ids
        # Atividade sem turma (rascunho/legado): só quem a criou.
        creator = _text(activity.get("created_by", activity.get("createdBy")))
        return bool(creator) and creator in self.actor_keys

    def require_activity(self, activity: dict[str, Any] | None) -> None:
        if not self.can_access_activity(activity):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=FORBIDDEN_ACTIVITY)

def resolve_teacher(request: Request, principal: UserPrincipal) -> dict[str, Any] | None:
    repository = request.app.state.teacher_repository
    teacher = repository.find_active_by_email(principal.email)
    if teacher is None and principal.email.lower() != principal.email:
        teacher = repository.find_active_by_email(principal.email.lower())
    return teacher


def build_scope(request: Request, principal: UserPrincipal) -> AccessScope:
    if principal.role == "ADMIN":
        return AccessScope(principal=principal)
    if principal.role != "TEACHER":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    teacher = resolve_teacher(request, principal)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=TEACHER_PROFILE_MISSING)
    teacher_id = _text(teacher.get("_id"))
    classrooms = _teacher_classrooms(request, teacher)
    classroom_ids = {_text(item.get("_id")) for item in classrooms}
    member_ids: set[str] = set()
    for classroom in classrooms:
        member_ids |= classroom_member_ids(classroom)
    # Turmas legadas ligadas pelo cadastro do professor (sem teacher_id na turma).
    for legacy_id in teacher.get("classrooms", teacher.get("classroomIds", [])) or []:
        classroom_ids.add(_text(legacy_id))
    classroom_ids.discard("")
    request.state.teacher_id = teacher_id
    return AccessScope(principal=principal, teacher=teacher, classroom_ids=classroom_ids, member_ids=member_ids)


def _teacher_classrooms(request: Request, teacher: dict[str, Any]) -> list[dict[str, Any]]:
    repository = request.app.state.classroom_repository
    finder = getattr(repository, "find_active_by_teacher_access", None)
    teacher_id = _text(teacher.get("_id"))
    if finder is not None:
        return list(finder(teacher_id, _text(teacher.get("email"))))
    # Repositórios em memória dos testes: filtra a lista completa (quando existir).
    finder_all = getattr(repository, "find_active", None)
    if finder_all is None:
        return []
    return [
        classroom
        for classroom in finder_all()
        if teacher_id in classroom_teacher_ids(classroom)
    ]


def staff_scope(
    request: Request,
    current_user: UserPrincipal = Depends(require_roles("TEACHER", "ADMIN")),
) -> AccessScope:
    return build_scope(request, current_user)

