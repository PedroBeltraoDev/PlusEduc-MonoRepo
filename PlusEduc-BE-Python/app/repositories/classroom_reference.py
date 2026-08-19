from typing import Any

from bson import ObjectId

from app.core.database import MongoConnection


class ClassroomReferenceRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    def exists_by_id(self, classroom_id: str) -> bool:
        collection = self._mongo.database["classrooms"]
        candidates: list[Any] = [classroom_id]
        if ObjectId.is_valid(classroom_id):
            candidates.append(ObjectId(classroom_id))
        return collection.find_one({"_id": {"$in": candidates}}, {"_id": 1}) is not None
