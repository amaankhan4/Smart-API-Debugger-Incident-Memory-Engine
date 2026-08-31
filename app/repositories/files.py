from typing import Any

from app.core.mongo import file_col
from app.schemas.enums import FileStatus
from app.utils.datetime_utils import utc_now


async def create_file(
    *, file_id: str, user_id: str, filename: str, stored_name: str, size_bytes: int
) -> dict[str, Any]:
    doc = {
        "file_id": file_id,
        "user_id": user_id,
        "filename": filename,
        "stored_name": stored_name,
        "size_bytes": size_bytes,
        "status": FileStatus.UPLOADED.value,
        "total_events": 0,
        "total_errors": 0,
        "total_chunks": 0,
        "error_message": None,
        "uploaded_at": utc_now(),
        "ingest_started_at": None,
        "ingest_completed_at": None,
        "created_at": utc_now(),
    }
    await file_col.insert_one(doc)
    return doc


async def get_file(file_id: str, user_id: str) -> dict[str, Any] | None:
    return await file_col.find_one({"file_id": file_id, "user_id": user_id})


async def list_files(
    user_id: str, *, status: str | None = None, limit: int = 50, offset: int = 0
) -> tuple[list[dict[str, Any]], int]:
    query: dict[str, Any] = {"user_id": user_id}
    if status:
        query["status"] = status

    total = await file_col.count_documents(query)
    cursor = file_col.find(query).sort("uploaded_at", -1).skip(offset).limit(limit)
    return await cursor.to_list(length=limit), total


async def set_status(file_id: str, user_id: str, status: FileStatus, **fields: Any) -> None:
    update: dict[str, Any] = {"status": status.value, **fields}
    await file_col.update_one({"file_id": file_id, "user_id": user_id}, {"$set": update})


async def mark_ingest_started(file_id: str, user_id: str) -> None:
    await set_status(
        file_id, user_id, FileStatus.PROCESSING, ingest_started_at=utc_now(), error_message=None
    )


async def mark_ingest_failed(file_id: str, user_id: str, message: str) -> None:
    await set_status(file_id, user_id, FileStatus.FAILED, error_message=message[:500])


async def delete_file_record(file_id: str, user_id: str) -> int:
    result = await file_col.delete_one({"file_id": file_id, "user_id": user_id})
    return result.deleted_count


async def count_files(user_id: str) -> int:
    return await file_col.count_documents({"user_id": user_id})


async def status_breakdown(user_id: str) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    return await file_col.aggregate(pipeline).to_list(length=50)
