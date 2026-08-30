from datetime import datetime

from pydantic import BaseModel


class CountPoint(BaseModel):
    key: str
    count: int


class TimePoint(BaseModel):
    bucket: datetime
    total: int
    errors: int


class ProcessingStatusCount(BaseModel):
    status: str
    count: int


class OverviewStats(BaseModel):
    total_files: int
    total_events: int
    total_errors: int
    error_rate: float
    open_incidents: int
    resolved_incidents: int
    total_incidents: int
    events_pending_embedding: int


class RecurringError(BaseModel):
    signature: str
    message: str
    service: str
    count: int
    error_category: str
    incident_id: str | None = None


class AnalyticsResponse(BaseModel):
    overview: OverviewStats
    error_trend: list[TimePoint]
    incidents_over_time: list[CountPoint]
    errors_by_service: list[CountPoint]
    errors_by_category: list[CountPoint]
    top_recurring_errors: list[RecurringError]
    most_affected_endpoints: list[CountPoint]
    processing_status: list[ProcessingStatusCount]
