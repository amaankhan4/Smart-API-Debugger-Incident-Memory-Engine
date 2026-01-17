import os
from fastapi import APIRouter, UploadFile,File, HTTPException, status 
from app.models.files import update_total_chunks
from app.core.config import settings
from pathlib import Path
from app.core.mongo import file_col, raw_log_chunks_col, events_col
import aiofiles
from app.services.parser import parse_log_line
from datetime import datetime
from app.core.redis import redis_client

target_dir = Path(settings.UPLOAD_DIR)

router = APIRouter()

CHUNK_SIZE = 1024 * 1024  # 1 MB

@router.get("/{file_id}")
async def ingest_file(file_id: str):
    file_doc = await file_col.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")

    file_path = file_id + file_doc.get("filename")

    sequence_number = 0
    total_events = 0

    file_path = target_dir / f"{file_path}"

    async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        while True:
            chunk = await f.read(CHUNK_SIZE)
            if not chunk:
                break

            # 1️⃣ store raw log chunk
            await raw_log_chunks_col.insert_one({
                "file_id": file_id,
                "sequence_number": sequence_number,
                "content": chunk,
                "created_at": datetime.now()
            })

            # 2️⃣ parse events from chunk
            for line in chunk.splitlines():
                event = parse_log_line(line)
                if event:
                    event_doc = {
                        **event,
                        "file_id": file_id,
                        "created_at": datetime.now()
                    }
                    result = await events_col.insert_one(event_doc)

                    if result.inserted_id:
                        redis_client.lpush("embeddings_queue", str(result.inserted_id))
                        print(f"Queued event {result.inserted_id} for embedding")

                    total_events += 1

            sequence_number += 1

    # 3️⃣ mark file as ingested
    await file_col.update_one(
        {"file_id": file_id},
        {"$set": {"status": "ingested", "ingested_at": datetime.now()}}
    )

    return {
        "file_id": file_id,
        "chunks_processed": sequence_number,
        "events_created": total_events,
        "status": "ingestion_completed"
    }

    
