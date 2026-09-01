from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.core import quota
from app.schemas.system import VectorQuota

router = APIRouter()


@router.get("/quota", response_model=VectorQuota)
async def vector_quota(_: CurrentUser) -> VectorQuota:
    return VectorQuota(**await quota.snapshot())  # type: ignore[arg-type]
