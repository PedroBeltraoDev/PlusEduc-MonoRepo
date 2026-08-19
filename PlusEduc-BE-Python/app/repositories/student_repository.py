from typing import Any

from bson import ObjectId

from app.core.database import MongoConnection


class StudentRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["students"]

    def find_by_email(self, email: str) -> dict[str, Any] | None:
        return self.collection.find_one({"email": email})

    def find_active_by_email(self, email: str) -> dict[str, Any] | None:
        return self.collection.find_one({"email": email, "active": True})

    def find_by_user_id_and_active(self, user_id: str) -> dict[str, Any] | None:
        return self.collection.find_one({
            "$or": [{"userId": user_id}, {"user_id": user_id}],
            "active": True,
        })

    def find_by_id(self, student_id: str) -> dict[str, Any] | None:
        candidates: list[Any] = [student_id]
        if ObjectId.is_valid(student_id):
            candidates.append(ObjectId(student_id))
        return self.collection.find_one({"_id": {"$in": candidates}})

    def find_active(self) -> list[dict[str, Any]]:
        return list(self.collection.find({"active": True}))

    def find_active_by_class(self, class_id: str) -> list[dict[str, Any]]:
        return self.find_active_by_class_flexible(class_id)

    def find_active_by_class_flexible(self, class_id: str) -> list[dict[str, Any]]:
        return list(self.collection.find({
            "$or": [{"class_id": class_id}, {"classId": class_id}],
            "active": True,
        }))

    def find_active_by_learning_gap_subject(self, subject: str) -> list[dict[str, Any]]:
        return list(
            self.collection.find(
                {"learning_gaps.subject": {"$regex": subject, "$options": "i"}, "active": True}
            )
        )

    def count_active(self) -> int:
        return self.collection.count_documents({"active": True})

    def insert(self, document: dict[str, Any]) -> dict[str, Any]:
        result = self.collection.insert_one(document)
        document["_id"] = result.inserted_id
        return document

    def update(self, student_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        current = self.find_by_id(student_id)
        if current is None:
            return None
        identifier = current.get("_id")
        self.collection.update_one({"_id": identifier}, {"$set": updates})
        current.update(updates)
        return current

    def soft_delete(self, student_id: str, updated_at) -> bool:
        current = self.find_by_id(student_id)
        if current is None:
            return False
        self.collection.update_one(
            {"_id": current.get("_id")},
            {"$set": {"active": False, "updated_at": updated_at}},
        )
        return True
