from datetime import datetime
from app.core.mongo import raw_log_chunks_col

async def create_raw_log_chunk(data: dict):
    doc = {
        "file_id": data["file_id"],
        "user_id": data["user_id"],
        "sequence_number": data["sequence_number"],
        "content": data["content"],
        "created_at": datetime.now()
    }
    result = await raw_log_chunks_col.insert_one(doc)
    return result.inserted_id