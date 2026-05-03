from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import settings
from app.services.ingest_service import get_all_existing_files_metadata, save_file_to_db

CHUNK_SIZE = 1024 * 1024
router = APIRouter()

target_dir = Path(settings.UPLOAD_DIR)
target_dir.mkdir(parents=True, exist_ok=True)


@router.post("/")
async def upload_log(file: UploadFile = File(...)):
    file_name = file.filename or ""
    if not any(file_name.lower().endswith(ext) for ext in {".txt", ".log"}):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file extension. Only .txt and .log files are allowed.",
        )

    file_id = await save_file_to_db(file_size=file.size or 0, file_name=file_name)
    target_path = target_dir / f"{file_id}{file_name}"

    try:
        async with aiofiles.open(target_path, "wb") as out_file:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                await out_file.write(chunk)
    finally:
        await file.close()

    return {"message": "File uploaded successfully", "file_id": file_id}


@router.get("/all-files")
async def get_all_executable_files():
    result = await get_all_existing_files_metadata(None, target_dir)
    return {"message": "All executable files", "data": result}
