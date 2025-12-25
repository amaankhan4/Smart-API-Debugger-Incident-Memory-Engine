from fastapi import APIRouter

router = APIRouter()

@router.get("/get_incidents")
async def get_incidents():
    pass