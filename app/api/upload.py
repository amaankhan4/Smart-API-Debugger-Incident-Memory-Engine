from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services.ingest_service import save_file_to_db, get_all_existing_files_metadata
import aiofiles
from app.core.config import settings
from pathlib import Path

CHUNK_SIZE = 1024 * 1024  # 1MB Chunk Size

router = APIRouter()

ALLOWED_CONTENT_TYPES = {
    'text/plain', 
    'text/x-log',
    'application/octet-stream'
}
ALLOWED_EXTENSIONS = {'.txt', '.log'}

target_dir = Path(settings.UPLOAD_DIR)
target_dir.mkdir(parents=True, exist_ok=True)

@router.post("/")
async def upload_log(file: UploadFile = File(...)):
    
    try:

        fileName = file.filename

        filename_lower = fileName.lower()
        if not any(filename_lower.endswith(ext) for ext in {'.txt', '.log'}):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="Unsupported file extension. Only .txt and .log files are allowed."
            )
        
        file_id = await save_file_to_db(file_size=file.size, fileName=fileName)

        target_path = target_dir / f"{file_id}"

        async with aiofiles.open(target_path, "wb") as out_file:
            while True:
                chunk = await file.read(CHUNK_SIZE)
                if not chunk:
                    break
                await out_file.write(chunk)

            await out_file.close()

        return {"message": "File uploaded successfully", "file_id": file_id}

    
    except Exception as e:
        return {"message": "There was an error uploading the file"}
    
    finally:
        await file.close()


@router.get("/AllFiles")
async def getAllExecutableFiles():
    try:
        result = await get_all_existing_files_metadata(None,target_dir)

        return {"message":"All Executable Files","data":result}
    
    except Exception as e:
        return {"message": "There was an error getting all files metadata"}