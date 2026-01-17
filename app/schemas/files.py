from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class FileStatus(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_STARTED = "NOT STARTED"
    HALTED = "HALTED"

class FileCreate(BaseModel):
    user_id: str
    filename: str
    size_bytes: int
    total_chunks: Optional[int] = 1
    last_raw_log_chunk_id: Optional[str] = None
    
class FileDB(FileCreate):
    file_id: Optional[str]
    status: FileStatus
    created_at : datetime