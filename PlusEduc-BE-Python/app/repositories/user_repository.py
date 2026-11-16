from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

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

    def delete_by_id(self, user_id: str) -> bool:
        candidates: list[Any] = [user_id]
        if ObjectId.is_valid(user_id):
            candidates.append(ObjectId(user_id))
        result = self._mongo.database["users"].delete_one({"_id": {"$in": candidates}})
        return result.deleted_count == 1

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

    def insert_teacher_user(self, email: str, password_hash: str, pending_approval: bool = False) -> str:
        document: dict[str, Any] = {
            "email": email,
            "password": password_hash,
            "role": "TEACHER",
            "active": not pending_approval,
            "createdAt": datetime.now(timezone.utc),
        }
        if pending_approval:
            # Conta criada pelo cadastro público: só passa a entrar depois da aprovação do ADMIN.
            document["pendingApproval"] = True
        result = self._mongo.database["users"].insert_one(document)
        return str(result.inserted_id)

    def insert_admin_user(self, email: str, password_hash: str, name: str) -> str:
        result = self._mongo.database["users"].insert_one(
            {
                "email": email,
                "password": password_hash,
                "role": "ADMIN",
                "name": name,
                "active": True,
                "createdAt": datetime.now(timezone.utc),
            }
        )
        return str(result.inserted_id)

    def find_pending_by_email(self, email: str) -> dict[str, Any] | None:
        return self._mongo.database["users"].find_one({"email": email, "pendingApproval": True})

    def approve_pending(self, email: str) -> bool:
        result = self._mongo.database["users"].update_one(
            {"email": email, "pendingApproval": True},
            {
                "$set": {"active": True, "updatedAt": datetime.now(timezone.utc)},
                "$unset": {"pendingApproval": ""},
            },
        )
        return result.modified_count == 1

    def delete_pending(self, email: str) -> int:
        return self._mongo.database["users"].delete_many({"email": email, "pendingApproval": True}).deleted_count

    def set_password_reset_code(self, email: str, code_hash: str, expires_at: datetime) -> bool:
        result = self._mongo.database["users"].update_one(
            {"email": email, "active": {"$ne": False}},
            {
                "$set": {
                    "passwordResetCodeHash": code_hash,
                    "passwordResetExpiresAt": expires_at,
                    "passwordResetAttempts": 0,
                }
            },
        )
        return result.matched_count == 1

    def register_password_reset_attempt(self, email: str) -> None:
        self._mongo.database["users"].update_one(
            {"email": email},
            {"$inc": {"passwordResetAttempts": 1}},
        )

    def clear_password_reset_code(self, email: str) -> None:
        self._mongo.database["users"].update_one(
            {"email": email},
            {
                "$unset": {
                    "passwordResetCodeHash": "",
                    "passwordResetExpiresAt": "",
                    "passwordResetAttempts": "",
                }
            },
        )

    def deactivate_by_email(self, email: str) -> int:
        """Desativa o login de quem foi excluído (exclusão lógica): o token e a senha deixam de valer."""
        result = self._mongo.database["users"].update_many(
            {"email": email, "active": {"$ne": False}},
            {"$set": {"active": False, "updatedAt": datetime.now(timezone.utc)}},
        )
        return result.modified_count

    def update_password(self, email: str, password_hash: str) -> bool:
        result = self._mongo.database["users"].update_one(
            {"email": email, "active": {"$ne": False}},
            {"$set": {"password": password_hash, "updatedAt": datetime.now(timezone.utc)}},
        )
        return result.matched_count == 1
