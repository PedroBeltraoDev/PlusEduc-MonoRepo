from typing import Any

from bson import ObjectId

from app.core.database import MongoConnection


class ClassroomRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["classrooms"]

    def find_by_id(self, classroom_id: str) -> dict[str, Any] | None:
        candidates: list[Any] = [classroom_id]
        if ObjectId.is_valid(classroom_id):
            candidates.append(ObjectId(classroom_id))
        return self.collection.find_one({"_id": {"$in": candidates}})

    def exists_by_id(self, classroom_id: str) -> bool:
        return self.find_by_id(classroom_id) is not None

    def find_active(self) -> list[dict[str, Any]]:
        return list(self.collection.find({"active": True}))

    def find_active_by_teacher(self, teacher_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({"teacher_id": teacher_id, "active": True}))

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

    def soft_delete(self, classroom_id: str, updated_at) -> bool:
        current = self.find_by_id(classroom_id)
        if current is None:
            return False
        self.collection.update_one(
            {"_id": current.get("_id")},
            {"$set": {"active": False, "updated_at": updated_at}},
        )
        return True
