from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import EmbeddingStatus, ErrorCategory, Level


class EventOut(BaseModel):
    id: str
    user_id: str
    file_id: str
    line_no: int
    timestamp: Optional[datetime] = None
    service: str = "unknown"
    level: Level = Level.INFO
    message: str = ""

    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    correlation_id: Optional[str] = None
    http_method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    exception: Optional[str] = None
    language: Optional[str] = None
    framework: Optional[str] = None
    stack_trace: Optional[str] = None
    error_category: ErrorCategory = ErrorCategory.UNKNOWN

    embedding_id: Optional[str] = None
    embedding_status: EmbeddingStatus = EmbeddingStatus.PENDING
    incident_id: Optional[str] = None
    chunk_sequence: Optional[int] = None
    created_at: Optional[datetime] = None


class EventContextResponse(BaseModel):
    event: EventOut
    strategy: str = Field(description="Which context strategy produced the surrounding lines")
    before: list[EventOut] = []
    after: list[EventOut] = []
    trace_events: list[EventOut] = []
    raw_chunk: Optional[str] = None
    raw_chunk_sequence: Optional[int] = None


class SimilarEventMatch(BaseModel):
    event: EventOut
    score: float = Field(ge=0.0, le=1.0, description="Cosine similarity normalised to 0-1")
    distance: float
    matched_on: list[str] = []


class SimilarEventsResponse(BaseModel):
    query: str
    matches: list[SimilarEventMatch]
