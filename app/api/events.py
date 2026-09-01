from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser
from app.repositories import events as events_repo
from app.schemas.common import Page
from app.schemas.enums import ErrorCategory, Level
from app.schemas.events import EventContextResponse, EventOut, SimilarEventMatch
from app.services.context import build_event_context
from app.services.search import escape_regex, similar_to_event
from app.utils.serialization import serialize_docs

router = APIRouter()


@router.get("", response_model=Page[EventOut])
async def list_events(
    current_user: CurrentUser,
    file_id: str | None = None,
    service: str | None = None,
    level: Level | None = None,
    error_category: ErrorCategory | None = None,
    incident_id: str | None = None,
    trace_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    search: str | None = Query(None, max_length=200),
    only_errors: bool = False,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Page[EventOut]:
    query = events_repo.build_event_query(
        current_user.id,
        file_id=file_id,
        service=service,
        level=level.value if level else None,
        error_category=error_category.value if error_category else None,
        incident_id=incident_id,
        trace_id=trace_id,
        start_time=start_time,
        end_time=end_time,
        search=escape_regex(search) if search else None,
        only_errors=only_errors,
    )
    docs, total = await events_repo.list_events(query, limit=limit, offset=offset)
    items = [EventOut(**doc) for doc in serialize_docs(docs)]
    return Page[EventOut].build(items, total, limit, offset)


@router.get("/{event_id}", response_model=EventOut)
async def get_event(event_id: str, current_user: CurrentUser) -> EventOut:
    doc = await events_repo.get_event(event_id, current_user.id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    return EventOut(**serialize_docs([doc])[0])


@router.get("/{event_id}/context", response_model=EventContextResponse)
async def event_context(
    event_id: str,
    current_user: CurrentUser,
    line_window: int = Query(20, ge=1, le=200),
    time_window_seconds: int = Query(120, ge=1, le=86400),
) -> EventContextResponse:
    doc = await events_repo.get_event(event_id, current_user.id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    context = await build_event_context(
        user_id=current_user.id,
        event=doc,
        line_window=line_window,
        time_window_seconds=time_window_seconds,
    )
    return EventContextResponse(**context)


@router.get("/{event_id}/similar", response_model=list[SimilarEventMatch])
async def similar_events(
    event_id: str, current_user: CurrentUser, limit: int = Query(10, ge=1, le=50)
) -> list[SimilarEventMatch]:
    doc = await events_repo.get_event(event_id, current_user.id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

    matches = await similar_to_event(current_user.id, doc, limit)
    return [SimilarEventMatch(**match) for match in matches]

