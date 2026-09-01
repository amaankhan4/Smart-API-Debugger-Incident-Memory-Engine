from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING, TEXT

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

client = AsyncIOMotorClient(settings.MONGODB_URI, uuidRepresentation="standard")
db = client[settings.MONGODB_DB]

raw_log_chunks_col = db.raw_logs
events_col = db.events
incidents_col = db.incidents
user_col = db.users
file_col = db.files
incident_notes_col = db.incident_notes

_MESSAGE_TEXT_INDEX = "event_message_text"
# A text index reads each document's language from a field named "language" by default,
# which is also a field the parser emits. Pointing the override at a name no document
# carries makes Mongo always use the default language instead of rejecting the write.
_TEXT_LANGUAGE_OVERRIDE = "_text_language"


async def _ensure_message_text_index() -> None:
    existing = (await events_col.index_information()).get(_MESSAGE_TEXT_INDEX)
    if existing and existing.get("language_override") != _TEXT_LANGUAGE_OVERRIDE:
        await events_col.drop_index(_MESSAGE_TEXT_INDEX)
    await events_col.create_index(
        [("message", TEXT)],
        name=_MESSAGE_TEXT_INDEX,
        language_override=_TEXT_LANGUAGE_OVERRIDE,
    )


async def ensure_indexes() -> None:
    """Indexes are ownership-first: every hot query is scoped by user_id."""
    await user_col.create_index([("email", ASCENDING)], unique=True)

    # Mongo treats every missing field as the same null, so a plain unique index here
    # collides on legacy rows. Scoping it to well-formed documents keeps the guarantee
    # for real records without letting one malformed row block startup.
    await file_col.create_index(
        [("file_id", ASCENDING)],
        unique=True,
        partialFilterExpression={"file_id": {"$type": "string"}},
    )
    await file_col.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    await file_col.create_index([("user_id", ASCENDING), ("status", ASCENDING)])

    await raw_log_chunks_col.create_index(
        [("file_id", ASCENDING), ("sequence_number", ASCENDING)], unique=True
    )
    await raw_log_chunks_col.create_index(
        [("file_id", ASCENDING), ("start_line_no", ASCENDING), ("end_line_no", ASCENDING)]
    )

    await events_col.create_index(
        [("file_id", ASCENDING), ("line_no", ASCENDING)],
        unique=True,
        partialFilterExpression={"file_id": {"$type": "string"}, "line_no": {"$type": "number"}},
    )
    await events_col.create_index([("user_id", ASCENDING), ("timestamp", DESCENDING)])
    await events_col.create_index([("user_id", ASCENDING), ("level", ASCENDING), ("timestamp", DESCENDING)])
    await events_col.create_index([("user_id", ASCENDING), ("service", ASCENDING), ("timestamp", DESCENDING)])
    await events_col.create_index([("user_id", ASCENDING), ("error_category", ASCENDING)])
    await events_col.create_index([("user_id", ASCENDING), ("incident_id", ASCENDING)])
    await events_col.create_index([("trace_id", ASCENDING), ("timestamp", ASCENDING)])
    await events_col.create_index([("embedding_status", ASCENDING)])
    await _ensure_message_text_index()

    await incidents_col.create_index([("user_id", ASCENDING), ("cluster_key", ASCENDING)], unique=True)
    await incidents_col.create_index([("user_id", ASCENDING), ("status", ASCENDING), ("last_seen", DESCENDING)])
    await incidents_col.create_index([("user_id", ASCENDING), ("severity", ASCENDING)])

    await incident_notes_col.create_index([("incident_id", ASCENDING), ("created_at", DESCENDING)])
    await incident_notes_col.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])

    logger.info("mongo indexes ensured", extra={"database": settings.MONGODB_DB})

