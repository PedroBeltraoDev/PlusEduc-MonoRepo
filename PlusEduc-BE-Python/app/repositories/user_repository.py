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

    def insert_teacher_user(
        self,
        email: str,
        password_hash: str | None,
        pending_approval: bool = False,
        active: bool = True,
        name: str | None = None,
    ) -> str:
        document: dict[str, Any] = {
            "email": email,
            "role": "TEACHER",
            "active": active and not pending_approval,
            "tokenVersion": 0,
            "createdAt": datetime.now(timezone.utc),
        }
        if password_hash:
            document["password"] = password_hash
        if name:
            document["name"] = name
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
                "tokenVersion": 0,
                "createdAt": datetime.now(timezone.utc),
            }
        )
        return str(result.inserted_id)

    # ---- consultas sem filtro de ativo (cadastro pendente, sincronização) -----------------
    def find_by_email(self, email: str) -> dict[str, Any] | None:
        return self._mongo.database["users"].find_one({"email": email})

    def find_by_id(self, user_id: str) -> dict[str, Any] | None:
        candidates: list[Any] = [user_id]
        if ObjectId.is_valid(user_id):
            candidates.append(ObjectId(user_id))
        return self._mongo.database["users"].find_one({"_id": {"$in": candidates}})

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

    def update_fields(self, email: str, values: dict[str, Any]) -> bool:
        result = self._mongo.database["users"].update_one(
            {"email": email},
            {"$set": {**values, "updatedAt": datetime.now(timezone.utc)}},
        )
        return result.matched_count == 1

    def unset_fields(self, email: str, *fields: str) -> None:
        self._mongo.database["users"].update_one({"email": email}, {"$unset": {field: "" for field in fields}})

    def revoke_sessions(self, email: str) -> None:
        """Invalida todos os tokens já emitidos para a conta (access e refresh)."""
        self._mongo.database["users"].update_one(
            {"email": email},
            {"$inc": {"tokenVersion": 1}, "$set": {"updatedAt": datetime.now(timezone.utc)}},
        )

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
        """Desativa o login de quem foi excluído (exclusão lógica): os tokens já emitidos deixam de valer."""
        result = self._mongo.database["users"].update_many(
            {"email": email, "active": {"$ne": False}},
            {"$set": {"active": False, "updatedAt": datetime.now(timezone.utc)}, "$inc": {"tokenVersion": 1}},
        )
        return result.modified_count

    def update_password(self, email: str, password_hash: str) -> bool:
        """Troca a senha e encerra as sessões abertas (tokens antigos deixam de valer)."""
        result = self._mongo.database["users"].update_one(
            {"email": email, "active": {"$ne": False}},
            {
                "$set": {"password": password_hash, "updatedAt": datetime.now(timezone.utc)},
                "$inc": {"tokenVersion": 1},
            },
        )
        return result.matched_count == 1
