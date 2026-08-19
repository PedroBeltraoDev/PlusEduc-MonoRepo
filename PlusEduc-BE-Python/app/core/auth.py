from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UserPrincipal:
    user_id: str
    email: str
    role: str
    active: bool = True
    student_id: str | None = None
    name: str | None = None


def _first_value(document: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = document.get(key)
        if value is not None:
            return value
    return None


def principal_from_document(document: dict[str, Any]) -> UserPrincipal:
    raw_id = _first_value(document, "id", "_id")
    student_id = _first_value(document, "studentId", "student_id")
    return UserPrincipal(
        user_id="" if raw_id is None else str(raw_id),
        email=str(document.get("email", "")),
        role=str(document.get("role", "")),
        active=document.get("active", True) is not False,
        student_id=None if student_id is None else str(student_id),
        name=document.get("name"),
    )
