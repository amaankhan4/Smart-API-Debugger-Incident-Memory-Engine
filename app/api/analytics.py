from fastapi import APIRouter, Query

from app.api.deps import CurrentUser
from app.schemas.analytics import AnalyticsResponse
from app.services.analytics import build_analytics

router = APIRouter()


@router.get("", response_model=AnalyticsResponse)
async def analytics(
    current_user: CurrentUser, days: int = Query(14, ge=1, le=180)
) -> AnalyticsResponse:
    data = await build_analytics(current_user.id, days=days)
    return AnalyticsResponse(**data)
