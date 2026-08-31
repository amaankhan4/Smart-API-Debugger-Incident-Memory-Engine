from typing import Any

from app.core.mongo import incident_notes_col
from app.schemas.enums import NoteType
from app.utils.datetime_utils import utc_now
from app.utils.serialization import to_object_id


async def create_note(
    *,
    incident_id: str,
    user_id: str,
    author_name: str,
    note: str,
    note_type: NoteType,
    event_id: str | None = None,
) -> dict[str, Any]:
    doc = {
        "incident_id": incident_id,
        "user_id": user_id,
        "author_name": author_name,
        "event_id": event_id,
        "note": note,
        "type": note_type.value,
        "created_at": utc_now(),
    }
    result = await incident_notes_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_notes(
    incident_id: str, user_id: str, *, limit: int = 100, offset: int = 0
) -> tuple[list[dict[str, Any]], int]:
    query = {"incident_id": incident_id, "user_id": user_id}
    total = await incident_notes_col.count_documents(query)
    cursor = incident_notes_col.find(query).sort("created_at", -1).skip(offset).limit(limit)
    return await cursor.to_list(length=limit), total


async def delete_note(note_id: str, user_id: str) -> int:
    object_id = to_object_id(note_id)
    if object_id is None:
        return 0
    result = await incident_notes_col.delete_one({"_id": object_id, "user_id": user_id})
    return result.deleted_count
