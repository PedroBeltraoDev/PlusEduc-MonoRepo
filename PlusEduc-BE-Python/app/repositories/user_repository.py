from datetime import datetime, timezone
from typing import Any

from app.core.database import MongoConnection


class UserRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    def find_active_by_email(self, email: str) -> dict[str, Any] | None:
        return self._mongo.database["users"].find_one(
            {"email": email, "active": {"$ne": False}}
        )

    def update_profile(self, current_email: str, name: str, email: str) -> dict[str, Any] | None:
        collection = self._mongo.database["users"]
        result = collection.update_one(
            {"email": current_email, "active": {"$ne": False}},
            {"$set": {"name": name, "email": email, "updatedAt": datetime.now(timezone.utc)}},
        )
        if result.matched_count == 0:
            return None
        return collection.find_one({"email": email, "active": {"$ne": False}})

    def insert_student_user(self, email: str, password_hash: str, student_id: str) -> str:
        result = self._mongo.database["users"].insert_one(
            {
                "email": email,
                "password": password_hash,
                "role": "STUDENT",
                "studentId": student_id,
                "active": True,
                "createdAt": datetime.now(timezone.utc),
            }
        )
        return str(result.inserted_id)
