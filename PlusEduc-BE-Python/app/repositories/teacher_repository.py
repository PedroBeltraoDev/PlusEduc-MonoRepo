from typing import Any

from bson import ObjectId

from app.core.database import MongoConnection


class TeacherRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["teachers"]

    def find_by_id(self, teacher_id: str) -> dict[str, Any] | None:
        candidates: list[Any] = [teacher_id]
        if ObjectId.is_valid(teacher_id):
            candidates.append(ObjectId(teacher_id))
        return self.collection.find_one({"_id": {"$in": candidates}})

    def find_by_email(self, email: str) -> dict[str, Any] | None:
        return self.collection.find_one({"email": email})

    def find_active(self) -> list[dict[str, Any]]:
        return list(self.collection.find({"active": True}))

    def find_active_by_email(self, email: str) -> dict[str, Any] | None:
        return self.collection.find_one({"email": email, "active": True})

    def find_active_by_subject(self, subject: str) -> list[dict[str, Any]]:
        return list(
            self.collection.find(
                {"subjects": subject, "active": True},
                {"password": 0},
            )
        )

    def count_all(self) -> int:
        return self.collection.count_documents({})

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update(self, teacher_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        current = self.find_by_id(teacher_id)
        if current is None:
            return None
        self.collection.update_one({"_id": current.get("_id")}, {"$set": updates})
        current.update(updates)
        return current

    def soft_delete(self, teacher_id: str, updated_at) -> bool:
        current = self.find_by_id(teacher_id)
        if current is None:
            return False
        self.collection.update_one(
            {"_id": current.get("_id")},
            {"$set": {"active": False, "updated_at": updated_at}},
        )
        return True
