from typing import Any

from bson import ObjectId

from app.core.database import MongoConnection


class SubjectTopicRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["subject_topics"]

    def find_all_by_owner(self, owner_key: str) -> list[dict[str, Any]]:
        return list(self.collection.find({"owner_key": owner_key}).sort("subject_normalized", 1))

    def find_by_id(self, item_id: str, owner_key: str) -> dict[str, Any] | None:
        candidates: list[Any] = [item_id]
        if ObjectId.is_valid(item_id):
            candidates.append(ObjectId(item_id))
        return self.collection.find_one({"_id": {"$in": candidates}, "owner_key": owner_key})

    def find_by_subject(self, subject_normalized: str, owner_key: str) -> dict[str, Any] | None:
        return self.collection.find_one({"owner_key": owner_key, "subject_normalized": subject_normalized})

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update(self, item_id: str, owner_key: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        current = self.find_by_id(item_id, owner_key)
        if current is None:
            return None
        self.collection.update_one({"_id": current["_id"]}, {"$set": updates})
        current.update(updates)
        return current

    def delete(self, item_id: str, owner_key: str) -> bool:
        current = self.find_by_id(item_id, owner_key)
        if current is None:
            return False
        return self.collection.delete_one({"_id": current["_id"]}).deleted_count == 1
