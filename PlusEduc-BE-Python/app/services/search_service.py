from __future__ import annotations

from typing import Any

from app.repositories.activity_repository import ActivityRepository
from app.repositories.classroom_repository import ClassroomRepository
from app.repositories.student_repository import StudentRepository
from app.schemas.report import SearchHit, SearchResponse
from app.services.report_service import norm

TYPES = ("students", "classrooms", "activities")


class SearchService:
    """Pesquisa global (sem acento e sem diferenciar maiúsculas) em alunos, turmas e atividades."""

    def __init__(self, students: StudentRepository, classrooms: ClassroomRepository, activities: ActivityRepository) -> None:
        self.students = students
        self.classrooms = classrooms
        self.activities = activities

    @staticmethod
    def _field_score(token: str, *fields: Any) -> int | None:
        best = None
        for index, field in enumerate(fields):
            text = norm(field)
            if not text:
                continue
            if text == token:
                score = 0
            elif text.startswith(token):
                score = 1
            elif any(word.startswith(token) for word in text.split()):
                score = 2
            elif token in text:
                score = 3
            else:
                continue
            score = score * 10 + index
            best = score if best is None else min(best, score)
        return best

    @classmethod
    def _score(cls, term: str, *fields: Any) -> int | None:
        # Várias palavras: todas precisam aparecer (em qualquer campo e em qualquer ordem).
        total = 0
        for token in term.split():
            score = cls._field_score(token, *fields)
            if score is None:
                return None
            total += score
        return total

    def search(self, query: str, kinds: list[str] | None, limit: int) -> SearchResponse:
        term = norm(query)
        selected = [kind for kind in (kinds or TYPES) if kind in TYPES]
        scored: list[tuple[int, SearchHit]] = []
        class_names: dict[str, str] = {}
        if "students" in selected or "activities" in selected:
            class_names = {str(c["_id"]): str(c.get("name", "")) for c in self.classrooms.find_active()}
        if "students" in selected:
            for student in self.students.find_active():
                score = self._score(term, student.get("name"), student.get("matricula"), student.get("email"))
                if score is None:
                    continue
                class_id = str(student.get("class_id") or student.get("classId") or "")
                subtitle = " • ".join(part for part in [student.get("matricula"), class_names.get(class_id) or "Sem turma"] if part)
                scored.append((score, SearchHit(type="students", id=str(student["_id"]), title=str(student.get("name", "")), subtitle=subtitle, url=f"/notas?turma={class_id}" if class_id else "/turmas")))
        if "classrooms" in selected:
            for classroom in self.classrooms.find_active():
                level = classroom.get("grade_level") or classroom.get("gradeLevel")
                score = self._score(term, classroom.get("name"), level)
                if score is None:
                    continue
                count = len(classroom.get("students") or classroom.get("student_ids") or [])
                subtitle = " • ".join(part for part in [level, f"{count} aluno(s)"] if part)
                scored.append((score, SearchHit(type="classrooms", id=str(classroom["_id"]), title=str(classroom.get("name", "")), subtitle=subtitle, url=f"/notas?turma={classroom['_id']}")))
        if "activities" in selected:
            for activity in self.activities.find_all():
                score = self._score(term, activity.get("title"), activity.get("topic"), activity.get("subject"))
                if score is None:
                    continue
                class_id = str(activity.get("classroom_id") or activity.get("classroomId") or "")
                subtitle = " • ".join(part for part in [activity.get("subject"), activity.get("topic"), class_names.get(class_id)] if part)
                scored.append((score, SearchHit(type="activities", id=str(activity["_id"]), title=str(activity.get("title", "")), subtitle=subtitle, url=f"/atividades/{activity['_id']}")))
        scored.sort(key=lambda pair: (pair[0], pair[1].title.lower()))
        hits = [hit for _, hit in scored]
        return SearchResponse(query=query, total=len(hits), results=hits[:limit])
