from datetime import datetime
from app.core.mongo import events_col

async def create_events(data: dict):
    doc = {
        "user_id": data["user_id"],
        "file_id": data["file_id"],
        "timestamp": data["timestamp"],
        "service": data["service"],
        "level": data["level"],
        "message": data["message"],
        "http_method": data.get("http_method"),
        "path": data.get("path"),
        "status_code": data.get("status_code"),
        "trace_id": data.get("trace_id"),
        "span_id": data.get("span_id"),
        "embedding_id": data.get("embedding_id"),
        "created_at": datetime.now()
    }
    result = await events_col.insert_one(doc)
    return result.inserted_id
