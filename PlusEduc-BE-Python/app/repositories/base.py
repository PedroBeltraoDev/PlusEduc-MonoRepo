from collections.abc import Iterable
from typing import Any

from bson import ObjectId


def id_candidates(values: Iterable[Any]) -> list[Any]:
    """Um mesmo id pode estar gravado como texto ou como ObjectId; devolve as duas formas."""
    candidates: list[Any] = []
    for value in values:
        text = str(value)
        candidates.append(text)
        if ObjectId.is_valid(text):
            candidates.append(ObjectId(text))
    return candidates


def find_by_ids(collection, ids: Iterable[Any]) -> dict[str, dict[str, Any]]:
    """Resolve vários ids numa única consulta (evita N+1). A chave do resultado é ``str(_id)``."""
    unique = {str(value) for value in ids if value}
    if not unique:
        return {}
    return {str(document["_id"]): document for document in collection.find({"_id": {"$in": id_candidates(unique)}})}
