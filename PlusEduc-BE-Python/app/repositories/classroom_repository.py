from collections.abc import Iterable
from typing import Any

from app.core.database import MongoConnection
from app.repositories.base import find_by_ids, id_candidates


class ClassroomRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["classrooms"]

    def find_by_id(self, classroom_id: str) -> dict[str, Any] | None:
        return self.collection.find_one({"_id": {"$in": id_candidates([classroom_id])}})

    def find_by_ids(self, ids: Iterable[Any]) -> dict[str, dict[str, Any]]:
        return find_by_ids(self.collection, ids)

    def exists_by_id(self, classroom_id: str) -> bool:
        return self.find_by_id(classroom_id) is not None

    def find_active(self) -> list[dict[str, Any]]:
        return list(self.collection.find({"active": True}))

    def find_active_by_teacher(self, teacher_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({"teacher_id": teacher_id, "active": True}))

    def find_active_by_teacher_access(self, teacher_id: str, teacher_email: str = "") -> list[dict[str, Any]]:
        """Turmas ativas em que o professor é titular ou leciona alguma disciplina."""
        keys = [value for value in {teacher_id, teacher_email, teacher_email.lower()} if value]
        return list(self.collection.find({
            "active": True,
            "$or": [
                {"teacher_id": {"$in": keys}},
                {"teacherId": {"$in": keys}},
                {"subjectTeachers.teacherId": {"$in": keys}},
            ],
        }))

    def find_active_page(self, query: dict[str, Any], skip: int, limit: int) -> tuple[list[dict[str, Any]], int]:
        """Paginação feita no MongoDB (skip/limit), sem carregar a coleção inteira."""
        criteria = {"active": True, **query}
        total = self.collection.count_documents(criteria)
        items = list(self.collection.find(criteria).sort([("name", 1), ("_id", 1)]).skip(skip).limit(limit))
        return items, total

    def remove_student_everywhere(self, student_id: str, keep_classroom_id: str | None = None) -> None:
        """Garante que o aluno fique em no máximo uma turma (a ``keep_classroom_id``)."""
        query: dict[str, Any] = {"students": {"$in": id_candidates([student_id])}}
        if keep_classroom_id:
            keep = self.find_by_id(keep_classroom_id)
            if keep is not None:
                query["_id"] = {"$ne": keep.get("_id")}
        self.collection.update_many(query, {"$pull": {"students": {"$in": id_candidates([student_id])}}})

    def find_active_by_student(self, student_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({"students": student_id, "active": True}))

    def find_active_by_year(self, year: int) -> list[dict[str, Any]]:
        return list(self.collection.find({"year": year, "active": True}))

    def exists_by_name_and_year(self, name: str, year: int, exclude_id: str | None = None) -> bool:
        query: dict[str, Any] = {"name": name, "year": year}
        if exclude_id:
            current = self.find_by_id(exclude_id)
            if current is not None:
                query["_id"] = {"$ne": current.get("_id")}
        return self.collection.find_one(query, {"_id": 1}) is not None

    def count_active_by_teacher(self, teacher_id: str, exclude_id: str | None = None) -> int:
        query: dict[str, Any] = {"teacher_id": teacher_id, "active": True}
        if exclude_id:
            current = self.find_by_id(exclude_id)
            if current is not None:
                query["_id"] = {"$ne": current.get("_id")}
        return self.collection.count_documents(query)

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update(self, classroom_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        current = self.find_by_id(classroom_id)
        if current is None:
            return None
        self.collection.update_one({"_id": current.get("_id")}, {"$set": updates})
        current.update(updates)
        return current

    def add_subject_teacher(self, classroom_id: str, assignment: dict[str, Any]) -> dict[str, Any] | None:
        current = self.find_by_id(classroom_id)
        if current is None:
            return None

        assignments = list(current.get("subjectTeachers", []) or [])
        subject_key = str(assignment.get("subjectKey", ""))
        if any(str(item.get("subjectKey", "")) == subject_key for item in assignments if isinstance(item, dict)):
            return None

        assignments.append(assignment)
        result = self.collection.update_one(
            {
                "_id": current.get("_id"),
                "subjectTeachers": {
                    "$not": {"$elemMatch": {"subjectKey": subject_key}},
                },
            },
            {"$set": {"subjectTeachers": assignments}},
        )
        if result.matched_count != 1:
            return None
        current["subjectTeachers"] = assignments
        return current

    def soft_delete(self, classroom_id: str, updated_at) -> bool:
        current = self.find_by_id(classroom_id)
        if current is None:
            return False
        self.collection.update_one(
            {"_id": current.get("_id")},
            {"$set": {"active": False, "updated_at": updated_at}},
        )
        return True
