from collections import Counter
from datetime import datetime
from typing import Any, Iterable

from pymongo import UpdateOne
from pymongo.errors import BulkWriteError

from app.core.logging import get_logger
from app.core.mongo import events_col, raw_log_chunks_col
from app.schemas.enums import SEVERE_LEVELS, EmbeddingStatus
from app.utils.serialization import to_object_id

logger = get_logger(__name__)


def build_event_query(
    user_id: str,
    *,
    file_id: str | None = None,
    service: str | None = None,
    level: str | None = None,
    error_category: str | None = None,
    incident_id: str | None = None,
    trace_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    search: str | None = None,
    only_errors: bool = False,
) -> dict[str, Any]:
    query: dict[str, Any] = {"user_id": user_id}
    if file_id:
        query["file_id"] = file_id
    if service:
        query["service"] = service
    if level:
        query["level"] = level.upper()
    if error_category:
        query["error_category"] = error_category
    if incident_id:
        query["incident_id"] = incident_id
    if trace_id:
        query["trace_id"] = trace_id
    if only_errors:
        query["level"] = {"$in": sorted(SEVERE_LEVELS)}

    if start_time or end_time:
        window: dict[str, Any] = {}
        if start_time:
            window["$gte"] = start_time
        if end_time:
            window["$lte"] = end_time
        query["timestamp"] = window

    if search:
        # Escaped by the caller; $regex on an untrusted string is a ReDoS/injection risk otherwise.
        query["message"] = {"$regex": search, "$options": "i"}
    return query


async def list_events(
    query: dict[str, Any], *, limit: int, offset: int, sort_field: str = "timestamp", sort_dir: int = -1
) -> tuple[list[dict[str, Any]], int]:
    total = await events_col.count_documents(query)
    cursor = events_col.find(query, {"embedding": 0}).sort(sort_field, sort_dir).skip(offset).limit(limit)
    return await cursor.to_list(length=limit), total


async def get_event(event_id: str, user_id: str) -> dict[str, Any] | None:
    object_id = to_object_id(event_id)
    if object_id is None:
        return None
    return await events_col.find_one({"_id": object_id, "user_id": user_id}, {"embedding": 0})


async def get_events_by_ids(event_ids: Iterable[str], user_id: str) -> list[dict[str, Any]]:
    object_ids = [oid for eid in event_ids if (oid := to_object_id(eid)) is not None]
    if not object_ids:
        return []
    cursor = events_col.find({"_id": {"$in": object_ids}, "user_id": user_id}, {"embedding": 0})
    return await cursor.to_list(length=len(object_ids))


async def bulk_insert_events(docs: list[dict[str, Any]]) -> list[str]:
    if not docs:
        return []
    try:
        result = await events_col.insert_many(docs, ordered=False)
        return [str(inserted_id) for inserted_id in result.inserted_ids]
    except BulkWriteError as exc:
        # Keep the writes that landed; one rejected line must not void the whole batch.
        write_errors = exc.details.get("writeErrors", []) if exc.details else []
        rejected = {error.get("index") for error in write_errors}
        _log_write_errors(write_errors, attempted=len(docs))
        return [
            str(doc["_id"])
            for index, doc in enumerate(docs)
            if index not in rejected and doc.get("_id") is not None
        ]


def _log_write_errors(write_errors: list[dict[str, Any]], *, attempted: int) -> None:
    """The driver's own message embeds every rejected document, so log a digest instead."""
    reasons = Counter(
        (error.get("code"), str(error.get("errmsg", ""))[:200]) for error in write_errors
    )
    logger.error(
        "event bulk insert rejected documents",
        extra={
            "operation": "ingest",
            "attempted": attempted,
            "rejected": len(write_errors),
            "reasons": [
                {"code": code, "errmsg": errmsg, "count": count}
                for (code, errmsg), count in reasons.most_common(5)
            ],
        },
    )


async def mark_embedding_status(event_ids: list[str], status: EmbeddingStatus) -> None:
    object_ids = [oid for eid in event_ids if (oid := to_object_id(eid)) is not None]
    if not object_ids:
        return
    await events_col.update_many(
        {"_id": {"$in": object_ids}}, {"$set": {"embedding_status": status.value}}
    )


async def apply_embedding_results(results: list[tuple[str, str]]) -> None:
    """results is a list of (event_id, vector_id) pairs."""
    operations = []
    for event_id, vector_id in results:
        object_id = to_object_id(event_id)
        if object_id is None:
            continue
        operations.append(
            UpdateOne(
                {"_id": object_id},
                {"$set": {"embedding_id": vector_id, "embedding_status": EmbeddingStatus.COMPLETED.value}},
            )
        )
    if operations:
        await events_col.bulk_write(operations, ordered=False)


async def assign_incident(event_ids: list[str], incident_id: str | None) -> None:
    object_ids = [oid for eid in event_ids if (oid := to_object_id(eid)) is not None]
    if not object_ids:
        return
    await events_col.update_many({"_id": {"$in": object_ids}}, {"$set": {"incident_id": incident_id}})


async def events_for_clustering(user_id: str, limit: int) -> list[dict[str, Any]]:
    cursor = (
        events_col.find(
            {
                "user_id": user_id,
                "level": {"$in": sorted(SEVERE_LEVELS)},
                "embedding_status": EmbeddingStatus.COMPLETED.value,
                "embedding_id": {"$ne": None},
            }
        )
        .sort("timestamp", -1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def context_window(
    user_id: str, file_id: str, center_line: int, window: int
) -> list[dict[str, Any]]:
    cursor = events_col.find(
        {
            "user_id": user_id,
            "file_id": file_id,
            "line_no": {"$gte": max(1, center_line - window), "$lte": center_line + window},
        },
        {"embedding": 0},
    ).sort("line_no", 1)
    return await cursor.to_list(length=(2 * window) + 1)


async def trace_events(user_id: str, trace_id: str, limit: int = 200) -> list[dict[str, Any]]:
    cursor = (
        events_col.find({"user_id": user_id, "trace_id": trace_id}, {"embedding": 0})
        .sort("line_no", 1)
        .limit(limit)
    )
    return await cursor.to_list(length=limit)


async def raw_chunk_for_line(file_id: str, line_no: int) -> dict[str, Any] | None:
    return await raw_log_chunks_col.find_one(
        {"file_id": file_id, "start_line_no": {"$lte": line_no}, "end_line_no": {"$gte": line_no}}
    )


async def delete_events_for_file(file_id: str, user_id: str) -> None:
    await events_col.delete_many({"file_id": file_id, "user_id": user_id})
    await raw_log_chunks_col.delete_many({"file_id": file_id, "user_id": user_id})


async def count_events(user_id: str, *, only_errors: bool = False) -> int:
    query: dict[str, Any] = {"user_id": user_id}
    if only_errors:
        query["level"] = {"$in": sorted(SEVERE_LEVELS)}
    return await events_col.count_documents(query)


async def count_pending_embeddings(user_id: str) -> int:
    return await events_col.count_documents(
        {
            "user_id": user_id,
            "embedding_status": {"$in": [EmbeddingStatus.PENDING.value, EmbeddingStatus.QUEUED.value]},
        }
    )


async def aggregate(pipeline: list[dict[str, Any]], length: int = 100) -> list[dict[str, Any]]:
    return await events_col.aggregate(pipeline).to_list(length=length)
