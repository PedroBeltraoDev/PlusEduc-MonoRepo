from typing import Any

from bson import ObjectId

from app.core.database import MongoConnection


class GradeRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["grades"]

    def find_by_id(self, grade_id: str) -> dict[str, Any] | None:
        candidates: list[Any] = [grade_id]
        if ObjectId.is_valid(grade_id):
            candidates.append(ObjectId(grade_id))
        return self.collection.find_one({"_id": {"$in": candidates}})

    def find_all(self) -> list[dict[str, Any]]:
        return list(self.collection.find({}).sort("date", -1))

    def find_by_student(self, student_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({"studentId": student_id}).sort("date", -1))

    def find_by_classroom(self, classroom_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({"classroomId": classroom_id}).sort("date", -1))

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update(self, grade_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        current = self.find_by_id(grade_id)
        if current is None:
            return None
        self.collection.update_one({"_id": current.get("_id")}, {"$set": updates})
        current.update(updates)
        return current

    def delete(self, grade_id: str) -> bool:
        current = self.find_by_id(grade_id)
        if current is None:
            return False
        return self.collection.delete_one({"_id": current.get("_id")}).deleted_count == 1
