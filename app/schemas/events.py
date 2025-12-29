from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum

class Level(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"


class EventCreate(BaseModel):
    user_id: str
    file_id: str

    timestamp: datetime
    service: str
    level: Level
    message: str

    http_method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    embedding_id: Optional[str] = None  # Chroma reference

class EventDB(EventCreate):
    id: Optional[str]
    created_at: datetime
