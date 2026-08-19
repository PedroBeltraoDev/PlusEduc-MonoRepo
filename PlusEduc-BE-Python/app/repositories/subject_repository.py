from typing import Any

from bson import ObjectId

from app.core.database import MongoConnection


class SubjectRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["subjects"]

    def find_all_active(self) -> list[dict[str, Any]]:
        return list(self.collection.find({"active": {"$ne": False}}).sort("name", 1))

    def find_by_id(self, subject_id: str) -> dict[str, Any] | None:
        candidates: list[Any] = [subject_id]
        if ObjectId.is_valid(subject_id):
            candidates.append(ObjectId(subject_id))
        return self.collection.find_one({"_id": {"$in": candidates}})

    def find_by_name_normalized(self, normalized_name: str) -> dict[str, Any] | None:
        return self.collection.find_one({"name_normalized": normalized_name})

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update(self, subject_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        current = self.find_by_id(subject_id)
        if current is None:
            return None
        self.collection.update_one({"_id": current["_id"]}, {"$set": updates})
        current.update(updates)
        return current
