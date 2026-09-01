import uuid
from pathlib import PurePosixPath

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from app.api.deps import CurrentUser
from app.core.config import settings
from app.repositories import events as events_repo
from app.repositories import files as files_repo
from app.schemas.common import MessageResponse, Page
from app.schemas.enums import FileStatus
from app.schemas.files import FileOut, UploadResponse
from app.services.storage import FileTooLargeError, storage
from app.utils.paths import sanitize_filename
from app.utils.serialization import serialize_docs

router = APIRouter()


def _validate_extension(filename: str) -> None:
    suffix = PurePosixPath(sanitize_filename(filename)).suffix.lower()
    if suffix not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(settings.allowed_extensions))}",
        )


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_log_file(current_user: CurrentUser, file: UploadFile = File(...)) -> UploadResponse:
    original_name = file.filename or "upload.log"
    _validate_extension(original_name)

    file_id = str(uuid.uuid4())
    try:
        stored_name, size_bytes = await storage.save(
            file_id=file_id, filename=original_name, stream=file
        )
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc
    finally:
        await file.close()

    if size_bytes == 0:
        await storage.delete(stored_name)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty")

    await files_repo.create_file(
        file_id=file_id,
        user_id=current_user.id,
        filename=sanitize_filename(original_name),
        stored_name=stored_name,
        size_bytes=size_bytes,
    )

    return UploadResponse(
        file_id=file_id,
        filename=sanitize_filename(original_name),
        size_bytes=size_bytes,
        status=FileStatus.UPLOADED,
    )


@router.get("", response_model=Page[FileOut])
async def list_files(
    current_user: CurrentUser,
    file_status: FileStatus | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[FileOut]:
    docs, total = await files_repo.list_files(
        current_user.id,
        status=file_status.value if file_status else None,
        limit=limit,
        offset=offset,
    )
    items = [FileOut(**doc) for doc in serialize_docs(docs)]
    return Page[FileOut].build(items, total, limit, offset)


@router.get("/{file_id}", response_model=FileOut)
async def get_file(file_id: str, current_user: CurrentUser) -> FileOut:
    doc = await files_repo.get_file(file_id, current_user.id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileOut(**serialize_docs([doc])[0])


@router.delete("/{file_id}", response_model=MessageResponse)
async def delete_file(file_id: str, current_user: CurrentUser) -> MessageResponse:
    doc = await files_repo.get_file(file_id, current_user.id)
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    await events_repo.delete_events_for_file(file_id, current_user.id)
    await files_repo.delete_file_record(file_id, current_user.id)
    if stored_name := doc.get("stored_name"):
        await storage.delete(stored_name)

    return MessageResponse(message="File and derived events deleted")

