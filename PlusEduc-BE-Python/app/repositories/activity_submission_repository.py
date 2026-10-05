from typing import Any

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.core.database import MongoConnection


class DuplicateSubmissionError(Exception):
    """O aluno já enviou esta atividade (garantido pelo índice único do banco)."""


class ActivitySubmissionRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["activity_submissions"]

    def ensure_indexes(self) -> None:
        # Garante no banco o que o 409 da API só garante "na maioria das vezes": duas requisições
        # simultâneas do mesmo aluno não conseguem gravar duas submissões da mesma atividade.
        self.collection.create_index(
            [("activity_id", 1), ("student_id", 1)],
            name="submissions_activity_student_unique",
            unique=True,
            partialFilterExpression={"activity_id": {"$type": "string"}, "student_id": {"$type": "string"}},
        )

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

    def find_by_activity(self, activity_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({
            "$or": [
                {"activity_id": activity_id},
                {"activityId": activity_id},
            ]
        }).sort("submitted_at", -1))

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
        try:
            result = self.collection.insert_one(document)
        except DuplicateKeyError as error:
            raise DuplicateSubmissionError() from error
        document["_id"] = result.inserted_id
        return document
