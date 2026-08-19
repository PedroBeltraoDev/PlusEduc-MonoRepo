from typing import Any

from bson import ObjectId

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

    def find_all(self) -> list[dict[str, Any]]:
        return list(self.collection.find({}).sort("submitted_at", -1))

    def find_by_id(self, submission_id: str) -> dict[str, Any] | None:
        candidates: list[Any] = [submission_id]
        if ObjectId.is_valid(submission_id):
            candidates.append(ObjectId(submission_id))
        return self.collection.find_one({"_id": {"$in": candidates}})

    def update_content(self, submission_id: str, content: dict[str, Any]) -> dict[str, Any] | None:
        current = self.find_by_id(submission_id)
        if current is None:
            return None
        self.collection.update_one(
            {"_id": current["_id"]},
            {"$set": {"content": content}},
        )
        current["content"] = content
        return current

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document
