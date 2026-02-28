from datetime import datetime

from app.core.mongo import incidents_col


async def create_incident(data: dict):
    doc = {
        "title": data.get("title", "Detected incident cluster"),
        "summary": data.get("summary", ""),
        "file_id": data.get("file_id"),
        "cluster_key": data.get("cluster_key"),
        "event_ids": data.get("event_ids", []),
        "event_count": len(data.get("event_ids", [])),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    result = await incidents_col.insert_one(doc)
    return result.inserted_id
