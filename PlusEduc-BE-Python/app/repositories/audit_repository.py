from typing import Any

from bson import ObjectId

from app.core.database import MongoConnection


class AuditRepository:
    """Histórico de operações (coleção audit_logs): somente inserção e consulta, nunca edição."""

    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["audit_logs"]

    def ensure_indexes(self) -> None:
        self.collection.create_index([("timestamp", -1)], name="audit_timestamp_desc")
        self.collection.create_index([("actorId", 1), ("timestamp", -1)], name="audit_actor_timestamp")
        self.collection.create_index([("entity", 1), ("action", 1)], name="audit_entity_action")

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def search(self, query: dict[str, Any], skip: int, limit: int) -> list[dict[str, Any]]:
        return list(self.collection.find(query).sort("timestamp", -1).skip(skip).limit(limit))

    def count(self, query: dict[str, Any]) -> int:
        return self.collection.count_documents(query)

    def find_by_id(self, log_id: str) -> dict[str, Any] | None:
        if not ObjectId.is_valid(log_id):
            return None
        return self.collection.find_one({"_id": ObjectId(log_id)})
