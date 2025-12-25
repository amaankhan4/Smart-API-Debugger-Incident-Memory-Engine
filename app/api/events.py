from fastapi import APIRouter

router = APIRouter()

@router.get("/get_events")
async def get_events():
    pass