from datetime import datetime
from pathlib import Path

import aiofiles
from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.core.mongo import events_col, file_col, raw_log_chunks_col
from app.core.redis import redis_client
from app.services.parser import parse_log_line

router = APIRouter()

target_dir = Path(settings.UPLOAD_DIR)
CHUNK_SIZE = 1024 * 1024
QUEUE_NAME = "embeddings_queue"


@router.post("/{file_id}")
async def ingest_file(file_id: str):
    file_doc = await file_col.find_one({"file_id": file_id})
    if not file_doc:
        raise HTTPException(status_code=404, detail="File not found")

    if file_doc.get("status") == "INGESTED":
        return {
            "file_id": file_id,
            "chunks_processed": file_doc.get("total_chunks", 0),
            "events_created": file_doc.get("event_count", 0),
            "status": "already_ingested",
        }

    file_path = target_dir / f"{file_id}{file_doc.get('filename')}"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Uploaded file not found on disk")

    await events_col.delete_many({"file_id": file_id})
    await raw_log_chunks_col.delete_many({"file_id": file_id})

    sequence_number = 0
    total_events = 0
    line_no = 0
    remainder = ""

    async with aiofiles.open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        while True:
            chunk = await f.read(CHUNK_SIZE)
            if not chunk:
                break

            full_chunk = remainder + chunk
            lines = full_chunk.splitlines(keepends=True)

            if lines and not lines[-1].endswith("\n"):
                remainder = lines.pop()
            else:
                remainder = ""

            normalized_lines: list[str] = []
            for raw_line in lines:
                normalized_lines.append(raw_line.rstrip("\r\n"))

            await raw_log_chunks_col.insert_one(
                {
                    "file_id": file_id,
                    "sequence_number": sequence_number,
                    "content": "\n".join(normalized_lines),
                    "start_line_no": line_no + 1,
                    "end_line_no": line_no + len(normalized_lines),
                    "created_at": datetime.utcnow(),
                }
            )

            for line in normalized_lines:
                line_no += 1
                parsed = parse_log_line(line)
                if not parsed:
                    continue

                event_doc = {
                    **parsed,
                    "file_id": file_id,
                    "line_no": line_no,
                    "chunk_sequence": sequence_number,
                    "timestamp": parsed.get("timestamp") or datetime.utcnow(),
                    "created_at": datetime.utcnow(),
                }

                result = await events_col.insert_one(event_doc)
                if result.inserted_id:
                    redis_client.lpush(QUEUE_NAME, str(result.inserted_id))
                    total_events += 1

            sequence_number += 1

        if remainder:
            line_no += 1
            await raw_log_chunks_col.insert_one(
                {
                    "file_id": file_id,
                    "sequence_number": sequence_number,
                    "content": remainder,
                    "start_line_no": line_no,
                    "end_line_no": line_no,
                    "created_at": datetime.utcnow(),
                }
            )
            parsed = parse_log_line(remainder)
            if parsed:
                result = await events_col.insert_one(
                    {
                        **parsed,
                        "file_id": file_id,
                        "line_no": line_no,
                        "chunk_sequence": sequence_number,
                        "timestamp": parsed.get("timestamp") or datetime.utcnow(),
                        "created_at": datetime.utcnow(),
                    }
                )
                if result.inserted_id:
                    redis_client.lpush(QUEUE_NAME, str(result.inserted_id))
                    total_events += 1
            sequence_number += 1

    await file_col.update_one(
        {"file_id": file_id},
        {
            "$set": {
                "status": "INGESTED",
                "ingested_at": datetime.utcnow(),
                "total_chunks": sequence_number,
                "event_count": total_events,
                "last_line_no": line_no,
            }
        },
    )

    return {
        "file_id": file_id,
        "chunks_processed": sequence_number,
        "events_created": total_events,
        "status": "ingestion_completed",
    }
