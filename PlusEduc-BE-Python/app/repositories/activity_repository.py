from typing import Any

from bson import ObjectId

from app.core.database import MongoConnection


class ActivityRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["activities"]

    def find_by_id(self, activity_id: str) -> dict[str, Any] | None:
        candidates: list[Any] = [activity_id]
        if ObjectId.is_valid(activity_id):
            candidates.append(ObjectId(activity_id))
        return self.collection.find_one({"_id": {"$in": candidates}})

    def find_all(self) -> list[dict[str, Any]]:
        return list(self.collection.find({}).sort("created_at", -1))

    def find_by_classroom(self, classroom_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({"$or": [{"classroom_id": classroom_id}, {"classroomId": classroom_id}]}).sort("created_at", -1))

    def find_by_student(self, student_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({"$or": [{"student_id": student_id}, {"studentId": student_id}]}).sort("created_at", -1))

    def find_by_classrooms(self, classroom_ids: list[str]) -> list[dict[str, Any]]:
        if not classroom_ids:
            return []
        return list(self.collection.find({"$or": [{"classroom_id": {"$in": classroom_ids}}, {"classroomId": {"$in": classroom_ids}}]}).sort("created_at", -1))

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update(self, activity_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        current = self.find_by_id(activity_id)
        if current is None:
            return None
        self.collection.update_one({"_id": current["_id"]}, {"$set": updates})
        current.update(updates)
        return current

    def delete(self, activity_id: str) -> bool:
        current = self.find_by_id(activity_id)
        if current is None:
            return False
        return self.collection.delete_one({"_id": current["_id"]}).deleted_count == 1
