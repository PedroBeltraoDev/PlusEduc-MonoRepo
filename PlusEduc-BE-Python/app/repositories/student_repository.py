from collections.abc import Iterable
from typing import Any

from app.core.database import MongoConnection
from app.repositories.base import find_by_ids, id_candidates


class StudentRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["students"]

    def find_by_email(self, email: str) -> dict[str, Any] | None:
        return self.collection.find_one({"email": email})

    def find_active_by_email(self, email: str) -> dict[str, Any] | None:
        return self.collection.find_one({"email": email, "active": True})

    def find_by_matricula(self, matricula: str) -> dict[str, Any] | None:
        return self.collection.find_one({"matricula": matricula, "active": True})

    def find_unassigned_active(self) -> list[dict[str, Any]]:
        return list(
            self.collection.find(
                {
                    "active": True,
                    "$and": [
                        {
                            "$or": [
                                {"class_id": {"$exists": False}},
                                {"class_id": None},
                                {"class_id": ""},
                            ]
                        },
                        {
                            "$or": [
                                {"classId": {"$exists": False}},
                                {"classId": None},
                                {"classId": ""},
                            ]
                        },
                    ],
                }
            ).sort("name", 1)
        )

    def next_matricula(self, prefix: str | None = None) -> str:
        """Próxima matrícula do ano corrente (ex.: MAT-2027-0001); antes o ano era fixo em 2026."""
        if prefix is None:
            from datetime import datetime, timezone

            prefix = f"MAT-{datetime.now(timezone.utc).year}-"
        highest = 0
        for document in self.collection.find({"matricula": {"$regex": f"^{prefix}\\d+$"}}, {"matricula": 1}):
            value = str(document.get("matricula", ""))
            try:
                highest = max(highest, int(value[len(prefix):]))
            except ValueError:
                continue
        return f"{prefix}{highest + 1:04d}"

    def find_by_user_id_and_active(self, user_id: str) -> dict[str, Any] | None:
        return self.collection.find_one({
            "$or": [{"userId": user_id}, {"user_id": user_id}],
            "active": True,
        })

    def find_by_id(self, student_id: str) -> dict[str, Any] | None:
        return self.collection.find_one({"_id": {"$in": id_candidates([student_id])}})

    def find_by_ids(self, ids: Iterable[Any]) -> dict[str, dict[str, Any]]:
        return find_by_ids(self.collection, ids)

    def find_active(self) -> list[dict[str, Any]]:
        return list(self.collection.find({"active": True}))

    def find_active_by_class(self, class_id: str) -> list[dict[str, Any]]:
        return self.find_active_by_class_flexible(class_id)

    def find_active_by_class_flexible(self, class_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({
            "$or": [{"class_id": class_id}, {"classId": class_id}],
            "active": True,
        }))

    def find_active_by_learning_gap_subject(self, subject: str) -> list[dict[str, Any]]:
        return list(
            self.collection.find(
                {"learning_gaps.subject": {"$regex": subject, "$options": "i"}, "active": True}
            )
        )

    def find_active_page(self, query: dict[str, Any], skip: int, limit: int) -> tuple[list[dict[str, Any]], int]:
        """Paginação feita no MongoDB (skip/limit), sem carregar a coleção inteira."""
        criteria = {"active": True, **query}
        total = self.collection.count_documents(criteria)
        items = list(self.collection.find(criteria).sort([("name", 1), ("_id", 1)]).skip(skip).limit(limit))
        return items, total

    def find_active_in_scope(self, classroom_ids: Iterable[str], member_ids: Iterable[str], include_unassigned: bool = False) -> list[dict[str, Any]]:
        """Alunos ativos das turmas informadas (pelo class_id ou pela lista de membros da turma)."""
        conditions: list[dict[str, Any]] = [
            {"class_id": {"$in": list(classroom_ids)}},
            {"classId": {"$in": list(classroom_ids)}},
            {"_id": {"$in": id_candidates(member_ids)}},
        ]
        if include_unassigned:
            conditions.extend([{"class_id": {"$in": [None, ""]}}, {"class_id": {"$exists": False}, "classId": {"$in": [None, ""]}}, {"class_id": {"$exists": False}, "classId": {"$exists": False}}])
        return list(self.collection.find({"active": True, "$or": conditions}).sort("name", 1))

    def count_active(self) -> int:
        return self.collection.count_documents({"active": True})

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update(self, student_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        current = self.find_by_id(student_id)
        if current is None:
            return None
        identifier = current.get("_id")
        self.collection.update_one({"_id": identifier}, {"$set": updates})
        current.update(updates)
        return current

    def delete_by_id(self, student_id: str) -> bool:
        current = self.find_by_id(student_id)
        if current is None:
            return False
        result = self.collection.delete_one({"_id": current.get("_id")})
        return result.deleted_count == 1

    def soft_delete(self, student_id: str, updated_at) -> bool:
        current = self.find_by_id(student_id)
        if current is None:
            return False
        self.collection.update_one(
            {"_id": current.get("_id")},
            {"$set": {"active": False, "updated_at": updated_at}},
        )
        return True
