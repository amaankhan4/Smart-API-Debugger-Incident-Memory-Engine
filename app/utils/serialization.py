from typing import Any

from bson import ObjectId


def to_object_id(value: str) -> ObjectId | None:
    return ObjectId(value) if ObjectId.is_valid(value) else None


def serialize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """Convert a Mongo document into a JSON-safe dict without leaking internal vectors."""
    if doc is None:
        return None

    result = dict(doc)
    raw_id = result.pop("_id", None)
    if raw_id is not None:
        result["id"] = str(raw_id)
    result.pop("embedding", None)
    result.pop("password_hash", None)
    return result


def serialize_docs(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [serialized for doc in docs if (serialized := serialize_doc(doc)) is not None]
