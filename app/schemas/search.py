from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.schemas.enums import ErrorCategory, Level
from app.schemas.events import EventOut

SearchMode = Literal["semantic", "keyword", "hybrid"]


class SearchFilters(BaseModel):
    file_id: Optional[str] = None
    service: Optional[str] = None
    level: Optional[Level] = None
    error_category: Optional[ErrorCategory] = None
    incident_id: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class SearchResult(BaseModel):
    event: EventOut
    score: float = Field(ge=0.0, le=1.0)
    source: SearchMode
    matched_on: list[str] = []


class SearchResponse(BaseModel):
    query: str
    mode: SearchMode
    took_ms: float
    results: list[SearchResult]
    total: int
    # Set when semantic ranking was skipped, so the UI can say why results look thin.
    degraded_reason: Optional[Literal["vector_quota_exceeded", "vector_unavailable"]] = None
