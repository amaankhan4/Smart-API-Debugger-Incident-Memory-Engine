from datetime import datetime, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.core.mongo import events_col, raw_log_chunks_col
from app.core.vector_db import event_collection
from app.services.embedding import generate_embedding

router = APIRouter()


def _serialize_event(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.get("/")
async def list_events(
    file_id: Optional[str] = None,
    service: Optional[str] = None,
    level: Optional[str] = None,
    trace_id: Optional[str] = None,
    limit: int = Query(100, le=1000),
):
    query = {}
    if file_id:
        query["file_id"] = file_id
    if service:
        query["service"] = service
    if level:
        query["level"] = level.upper()
    if trace_id:
        query["trace_id"] = trace_id

    docs = await events_col.find(query).sort("timestamp", -1).limit(limit).to_list(length=limit)
    return {"items": [_serialize_event(doc) for doc in docs], "count": len(docs)}


@router.get("/similar")
async def similar_events(query: str, limit: int = Query(10, ge=1, le=100)):
    embedding = generate_embedding(query)
    result = event_collection.query(query_embeddings=[embedding], n_results=limit)

    matches = []
    ids = result.get("ids", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for idx, vector_id in enumerate(ids):
        metadata = metadatas[idx] if idx < len(metadatas) else {}
        event_id = metadata.get("event_id")
        if not event_id:
            continue
        event = await events_col.find_one({"_id": ObjectId(event_id)})
        if not event:
            continue
        matches.append(
            {
                "vector_id": vector_id,
                "distance": distances[idx] if idx < len(distances) else None,
                "event": _serialize_event(event),
            }
        )

    return {"query": query, "matches": matches}


@router.get("/{event_id}/context")
async def event_context(
    event_id: str,
    line_window: int = Query(5, ge=0, le=500),
    time_window_seconds: int = Query(300, ge=0, le=86400),
):
    event = await events_col.find_one({"_id": ObjectId(event_id)})
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    file_id = event.get("file_id")
    line_no = event.get("line_no", 0)
    timestamp = event.get("timestamp")

    trace_query = {
        "file_id": file_id,
        "trace_id": event.get("trace_id"),
    }
    same_trace = []
    if event.get("trace_id"):
        same_trace_docs = await events_col.find(trace_query).sort("line_no", 1).limit(200).to_list(length=200)
        same_trace = [_serialize_event(doc) for doc in same_trace_docs]

    line_docs = await events_col.find(
        {
            "file_id": file_id,
            "line_no": {"$gte": max(1, line_no - line_window), "$lte": line_no + line_window},
        }
    ).sort("line_no", 1).to_list(length=(2 * line_window) + 1)

    window_docs = []
    if timestamp:
        start = timestamp - timedelta(seconds=time_window_seconds)
        end = timestamp + timedelta(seconds=time_window_seconds)
        window_docs = await events_col.find(
            {"file_id": file_id, "timestamp": {"$gte": start, "$lte": end}}
        ).sort("timestamp", 1).limit(500).to_list(length=500)

    chunk = await raw_log_chunks_col.find_one(
        {
            "file_id": file_id,
            "start_line_no": {"$lte": line_no},
            "end_line_no": {"$gte": line_no},
        }
    )

    return {
        "event": _serialize_event(event),
        "same_trace_id": same_trace,
        "time_window": [_serialize_event(doc) for doc in window_docs],
        "line_window": [_serialize_event(doc) for doc in line_docs],
        "chunk_fallback": {
            "sequence_number": chunk.get("sequence_number") if chunk else None,
            "content": chunk.get("content") if chunk else None,
        },
    }
