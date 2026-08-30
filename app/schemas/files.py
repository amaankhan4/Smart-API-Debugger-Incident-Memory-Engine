from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schemas.enums import FileStatus


class FileOut(BaseModel):
    file_id: str
    user_id: str
    filename: str
    size_bytes: int = 0
    status: FileStatus = FileStatus.UPLOADED
    total_events: int = 0
    total_errors: int = 0
    total_chunks: int = 0
    error_message: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    ingest_started_at: Optional[datetime] = None
    ingest_completed_at: Optional[datetime] = None


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    size_bytes: int
    status: FileStatus


class IngestResponse(BaseModel):
    file_id: str
    status: FileStatus
    chunks_processed: int
    events_created: int
    lines_skipped: int
    duration_ms: float