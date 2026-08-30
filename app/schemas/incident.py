from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.enums import IncidentSeverity, IncidentStatus, NoteType
from app.schemas.events import EventOut


class IncidentOut(BaseModel):
    id: str
    user_id: str
    title: str
    summary: str = ""
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN
    cluster_key: str
    cluster_label: Optional[int] = None
    event_count: int = 0
    error_category: Optional[str] = None
    services: list[str] = []
    endpoints: list[str] = []
    file_ids: list[str] = []
    representative_event_ids: list[str] = []
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IncidentTimelinePoint(BaseModel):
    bucket: datetime
    count: int


class SimilarIncident(BaseModel):
    incident: IncidentOut
    score: float


class IncidentDetailResponse(BaseModel):
    incident: IncidentOut
    representative_events: list[EventOut] = []
    timeline: list[IncidentTimelinePoint] = []
    similar_incidents: list[SimilarIncident] = []


class IncidentStatusUpdate(BaseModel):
    status: IncidentStatus
    severity: Optional[IncidentSeverity] = None


class NoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=10000)
    type: NoteType = NoteType.GENERAL
    event_id: Optional[str] = None


class NoteOut(BaseModel):
    id: str
    incident_id: str
    user_id: str
    author_name: Optional[str] = None
    event_id: Optional[str] = None
    note: str
    type: NoteType = NoteType.GENERAL
    created_at: Optional[datetime] = None


class ClusterRunResponse(BaseModel):
    clusters_created: int
    clusters_updated: int
    events_clustered: int
    duration_ms: float
    reason: Optional[str] = None
