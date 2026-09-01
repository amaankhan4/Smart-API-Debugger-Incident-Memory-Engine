from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser
from app.schemas.files import IngestResponse
from app.services.ingest_service import IngestError, ingest_file

router = APIRouter()


@router.post("/{file_id}", response_model=IngestResponse)
async def trigger_ingestion(
    file_id: str,
    current_user: CurrentUser,
    force: bool = Query(False, description="Re-ingest a file that has already completed"),
) -> IngestResponse:
    try:
        result = await ingest_file(file_id, current_user.id, force=force)
    except IngestError as exc:
        message = str(exc)
        code = status.HTTP_404_NOT_FOUND if "not found" in message.lower() or "missing" in message.lower() else status.HTTP_422_UNPROCESSABLE_ENTITY
        raise HTTPException(status_code=code, detail=message) from exc

    return IngestResponse(**result)

