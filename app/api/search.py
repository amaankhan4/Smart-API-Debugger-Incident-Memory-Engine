from datetime import datetime

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.enums import ErrorCategory, Level
from app.schemas.search import SearchFilters, SearchResponse
from app.services.search import search_events

router = APIRouter()


@router.get("", response_model=SearchResponse)
async def search(
    current_user: CurrentUser,
    q: str = Query(min_length=1, max_length=500),
    mode: str = Query("hybrid", pattern="^(semantic|keyword|hybrid)$"),
    file_id: str | None = None,
    service: str | None = None,
    level: Level | None = None,
    error_category: ErrorCategory | None = None,
    incident_id: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = Query(25, ge=1, le=100),
) -> SearchResponse:
    filters = SearchFilters(
        file_id=file_id,
        service=service,
        level=level,
        error_category=error_category,
        incident_id=incident_id,
        start_time=start_time,
        end_time=end_time,
    )
    result = await search_events(
        user_id=current_user.id, query=q, filters=filters, mode=mode, limit=limit
    )
    return SearchResponse(**result)
