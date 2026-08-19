from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.auth import UserPrincipal
from app.repositories.subject_topic_repository import SubjectTopicRepository
from app.schemas.subject_topic import (
    SubjectTopicCreateRequest,
    SubjectTopicResponse,
    SubjectTopicUpdateRequest,
)


class SubjectTopicService:
    def __init__(self, repository: SubjectTopicRepository) -> None:
        self.repository = repository

    @staticmethod
    def _owner_key(current_user: UserPrincipal) -> str:
        return str(current_user.user_id or current_user.email).strip().lower()

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.strip().split())

    @classmethod
    def _normalized_key(cls, value: str) -> str:
        return cls._normalize(value).casefold()

    @classmethod
    def _clean_topics(cls, topics: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for topic in topics:
            cleaned = cls._normalize(topic)
            if not cleaned:
                continue
            key = cleaned.casefold()
            if key not in seen:
                seen.add(key)
                result.append(cleaned)
        return result

    @classmethod
    def _response(cls, document: dict[str, Any]) -> SubjectTopicResponse:
        return SubjectTopicResponse(
            id=str(document["_id"]),
            subject=str(document.get("subject", "")),
            topics=cls._clean_topics(document.get("topics", [])),
            createdAt=document.get("created_at", document.get("createdAt")),
            updatedAt=document.get("updated_at", document.get("updatedAt")),
        )

    def list(self, current_user: UserPrincipal) -> list[SubjectTopicResponse]:
        owner_key = self._owner_key(current_user)
        return [self._response(item) for item in self.repository.find_all_by_owner(owner_key)]

    def create(self, payload: SubjectTopicCreateRequest, current_user: UserPrincipal) -> SubjectTopicResponse:
        owner_key = self._owner_key(current_user)
        subject = self._normalize(payload.subject)
        subject_key = self._normalized_key(subject)
        topic = self._normalize(payload.topic) if payload.topic else ""
        now = datetime.now(timezone.utc)
        existing = self.repository.find_by_subject(subject_key, owner_key)

        if existing:
            topics = self._clean_topics([*existing.get("topics", []), topic])
            updated = self.repository.update(
                str(existing["_id"]),
                owner_key,
                {"topics": topics, "updated_at": now},
            )
            return self._response(updated or existing)

        document = {
            "subject": subject,
            "subject_normalized": subject_key,
            "topics": self._clean_topics([topic]),
            "owner_key": owner_key,
            "created_by": current_user.email,
            "created_at": now,
            "updated_at": now,
        }
        return self._response(self.repository.insert(document))

    def update(self, item_id: str, payload: SubjectTopicUpdateRequest, current_user: UserPrincipal) -> SubjectTopicResponse:
        owner_key = self._owner_key(current_user)
        subject = self._normalize(payload.subject)
        subject_key = self._normalized_key(subject)
        existing = self.repository.find_by_id(item_id, owner_key)
        if existing is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matéria não encontrada")

        duplicate = self.repository.find_by_subject(subject_key, owner_key)
        if duplicate is not None and str(duplicate["_id"]) != str(existing["_id"]):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Já existe outra matéria com esse nome")

        updated = self.repository.update(
            item_id,
            owner_key,
            {
                "subject": subject,
                "subject_normalized": subject_key,
                "topics": self._clean_topics(payload.topics),
                "updated_at": datetime.now(timezone.utc),
            },
        )
        if updated is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matéria não encontrada")
        return self._response(updated)

    def delete(self, item_id: str, current_user: UserPrincipal) -> None:
        if not self.repository.delete(item_id, self._owner_key(current_user)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matéria não encontrada")
