"""Dashboard analytics.

Every number here comes from an aggregation over the caller's own data. Nothing is
synthesised or hard-coded.
"""

from datetime import timedelta
from typing import Any

from app.repositories import events as events_repo
from app.repositories import files as files_repo
from app.repositories import incidents as incidents_repo
from app.schemas.enums import SEVERE_LEVELS, IncidentStatus
from app.utils.datetime_utils import utc_now

_SEVERE = sorted(SEVERE_LEVELS)


def _error_match(user_id: str, since: Any = None) -> dict[str, Any]:
    match: dict[str, Any] = {"user_id": user_id, "level": {"$in": _SEVERE}}
    if since is not None:
        match["timestamp"] = {"$gte": since}
    return match


async def _errors_by_field(user_id: str, field: str, limit: int = 10) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": {**_error_match(user_id), field: {"$nin": [None, ""]}}},
        {"$group": {"_id": f"${field}", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    rows = await events_repo.aggregate(pipeline, length=limit)
    return [{"key": str(row["_id"]), "count": row["count"]} for row in rows]


async def _error_trend(user_id: str, days: int) -> list[dict[str, Any]]:
    since = utc_now() - timedelta(days=days)
    pipeline = [
        {"$match": {"user_id": user_id, "timestamp": {"$gte": since}}},
        {
            "$group": {
                "_id": {"$dateTrunc": {"date": "$timestamp", "unit": "hour" if days <= 2 else "day"}},
                "total": {"$sum": 1},
                "errors": {"$sum": {"$cond": [{"$in": ["$level", _SEVERE]}, 1, 0]}},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    rows = await events_repo.aggregate(pipeline, length=1000)
    return [
        {"bucket": row["_id"], "total": row["total"], "errors": row["errors"]}
        for row in rows
        if row.get("_id") is not None
    ]


async def _top_recurring_errors(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    pipeline = [
        {"$match": _error_match(user_id)},
        {
            "$group": {
                "_id": {
                    "exception": {"$ifNull": ["$exception", "$error_category"]},
                    "service": {"$ifNull": ["$service", "unknown"]},
                },
                "count": {"$sum": 1},
                "message": {"$first": "$message"},
                "error_category": {"$first": "$error_category"},
                "incident_id": {"$first": "$incident_id"},
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    rows = await events_repo.aggregate(pipeline, length=limit)
    return [
        {
            "signature": str(row["_id"].get("exception") or "unknown"),
            "message": (row.get("message") or "")[:200],
            "service": str(row["_id"].get("service") or "unknown"),
            "count": row["count"],
            "error_category": row.get("error_category") or "unknown",
            "incident_id": row.get("incident_id"),
        }
        for row in rows
    ]


async def build_analytics(user_id: str, *, days: int = 14) -> dict[str, Any]:
    total_files = await files_repo.count_files(user_id)
    total_events = await events_repo.count_events(user_id)
    total_errors = await events_repo.count_events(user_id, only_errors=True)
    open_incidents = await incidents_repo.count_by_status(user_id, IncidentStatus.OPEN)
    investigating = await incidents_repo.count_by_status(user_id, IncidentStatus.INVESTIGATING)
    resolved = await incidents_repo.count_by_status(user_id, IncidentStatus.RESOLVED)
    total_incidents = await incidents_repo.count_incidents(user_id)
    pending_embeddings = await events_repo.count_pending_embeddings(user_id)

    incident_rows = await incidents_repo.incidents_over_time(user_id, utc_now() - timedelta(days=days))
    status_rows = await files_repo.status_breakdown(user_id)

    return {
        "overview": {
            "total_files": total_files,
            "total_events": total_events,
            "total_errors": total_errors,
            "error_rate": round(total_errors / total_events, 4) if total_events else 0.0,
            "open_incidents": open_incidents + investigating,
            "resolved_incidents": resolved,
            "total_incidents": total_incidents,
            "events_pending_embedding": pending_embeddings,
        },
        "error_trend": await _error_trend(user_id, days),
        "incidents_over_time": [
            {"key": str(row["_id"]), "count": row["count"]} for row in incident_rows
        ],
        "errors_by_service": await _errors_by_field(user_id, "service"),
        "errors_by_category": await _errors_by_field(user_id, "error_category"),
        "top_recurring_errors": await _top_recurring_errors(user_id),
        "most_affected_endpoints": await _errors_by_field(user_id, "path"),
        "processing_status": [
            {"status": str(row["_id"] or "unknown"), "count": row["count"]} for row in status_rows
        ],
    }
