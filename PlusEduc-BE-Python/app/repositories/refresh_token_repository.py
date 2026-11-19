"""Refresh tokens emitidos: permite rotação, revogação e detecção de reuso.

Só o hash SHA-256 do ``jti`` é gravado (o token em si nunca vai para o banco). Cada login abre
uma "família"; a cada renovação o token anterior é marcado como usado. Se um token já usado for
apresentado de novo (sinal de roubo), a família inteira é revogada.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from pymongo.errors import OperationFailure

from app.core.database import MongoConnection


def hash_jti(jti: str) -> str:
    return hashlib.sha256(jti.encode("utf-8")).hexdigest()


class RefreshTokenRepository:
    def __init__(self, mongo: MongoConnection) -> None:
        self._mongo = mongo

    @property
    def collection(self):
        return self._mongo.database["refresh_tokens"]

    def ensure_indexes(self) -> None:
        try:
            self.collection.create_index("jtiHash", unique=True, name="refresh_tokens_jti_unique")
            self.collection.create_index("family", name="refresh_tokens_family")
            self.collection.create_index("email", name="refresh_tokens_email")
            # O próprio MongoDB apaga os registros vencidos.
            self.collection.create_index("expiresAt", expireAfterSeconds=0, name="refresh_tokens_ttl")
        except OperationFailure:
            pass

    def register(self, jti: str, email: str, family: str, expires_at: datetime) -> None:
        self.collection.insert_one(
            {
                "jtiHash": hash_jti(jti),
                "email": email,
                "family": family,
                "expiresAt": expires_at,
                "createdAt": datetime.now(timezone.utc),
                "usedAt": None,
                "revokedAt": None,
            }
        )

    def consume(self, jti: str) -> dict[str, Any] | None:
        """Marca o token como usado de forma atômica; devolve o registro só se ainda estava válido.

        Duas renovações simultâneas com o mesmo token: apenas uma vence.
        """
        return self.collection.find_one_and_update(
            {"jtiHash": hash_jti(jti), "usedAt": None, "revokedAt": None},
            {"$set": {"usedAt": datetime.now(timezone.utc)}},
        )

    def find(self, jti: str) -> dict[str, Any] | None:
        return self.collection.find_one({"jtiHash": hash_jti(jti)})

    def revoke_family(self, family: str) -> None:
        self.collection.update_many(
            {"family": family, "revokedAt": None},
            {"$set": {"revokedAt": datetime.now(timezone.utc)}},
        )

    def revoke_all_for(self, email: str) -> None:
        self.collection.update_many(
            {"email": email, "revokedAt": None},
            {"$set": {"revokedAt": datetime.now(timezone.utc)}},
        )
