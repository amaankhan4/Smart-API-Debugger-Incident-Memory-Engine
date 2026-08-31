from datetime import datetime
from typing import Any

from app.core.mongo import incidents_col
from app.schemas.enums import IncidentSeverity, IncidentStatus
from app.utils.datetime_utils import utc_now
from app.utils.serialization import to_object_id


async def upsert_incident(user_id: str, cluster_key: str, payload: dict[str, Any]) -> tuple[str, bool]:
    """Upsert on (user_id, cluster_key); returns (incident_id, created)."""
    existing = await incidents_col.find_one({"user_id": user_id, "cluster_key": cluster_key})
    now = utc_now()

    if existing:
        # Never overwrite human-owned fields (status, severity override, resolution notes).
        await incidents_col.update_one(
            {"_id": existing["_id"]},
            {"$set": {**payload, "updated_at": now}},
        )
        return str(existing["_id"]), False

    doc = {
        "user_id": user_id,
        "cluster_key": cluster_key,
        "status": IncidentStatus.OPEN.value,
        "created_at": now,
        "updated_at": now,
        **payload,
    }
    result = await incidents_col.insert_one(doc)
    return str(result.inserted_id), True


async def get_incident(incident_id: str, user_id: str) -> dict[str, Any] | None:
    object_id = to_object_id(incident_id)
    if object_id is None:
        return None
    return await incidents_col.find_one({"_id": object_id, "user_id": user_id})


async def list_incidents(
    user_id: str,
    *,
    status: str | None = None,
    severity: str | None = None,
    service: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_field: str = "last_seen",
    sort_dir: int = -1,
) -> tuple[list[dict[str, Any]], int]:
    query: dict[str, Any] = {"user_id": user_id}
    if status:
        query["status"] = status
    if severity:
        query["severity"] = severity
    if service:
        query["services"] = service
    if search:
        query["title"] = {"$regex": search, "$options": "i"}

    total = await incidents_col.count_documents(query)
    cursor = incidents_col.find(query).sort(sort_field, sort_dir).skip(offset).limit(limit)
    return await cursor.to_list(length=limit), total


async def update_status(
    incident_id: str,
    user_id: str,
    status: IncidentStatus,
    severity: IncidentSeverity | None = None,
) -> dict[str, Any] | None:
    object_id = to_object_id(incident_id)
    if object_id is None:
        return None

    update: dict[str, Any] = {"status": status.value, "updated_at": utc_now()}
    if severity is not None:
        update["severity"] = severity.value
    update["resolved_at"] = utc_now() if status is IncidentStatus.RESOLVED else None

    return await incidents_col.find_one_and_update(
        {"_id": object_id, "user_id": user_id},
        {"$set": update},
        return_document=True,
    )


async def count_by_status(user_id: str, status: IncidentStatus) -> int:
    return await incidents_col.count_documents({"user_id": user_id, "status": status.value})


async def count_incidents(user_id: str) -> int:
    return await incidents_col.count_documents({"user_id": user_id})


async def incidents_over_time(user_id: str, since: datetime) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {"user_id": user_id, "created_at": {"$gte": since}}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    return await incidents_col.aggregate(pipeline).to_list(length=400)
