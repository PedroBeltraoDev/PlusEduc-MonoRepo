from typing import Any

from app.core.database import MongoConnection


class ActivitySubmissionRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["activity_submissions"]

    def find_by_activity_student(self, activity_id: str, student_id: str) -> dict[str, Any] | None:
        return self.collection.find_one({
            "$or": [
                {"activity_id": activity_id, "student_id": student_id},
                {"activityId": activity_id, "studentId": student_id},
            ]
        })

    def find_by_student(self, student_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({
            "$or": [
                {"student_id": student_id},
                {"studentId": student_id},
            ]
        }))

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document
