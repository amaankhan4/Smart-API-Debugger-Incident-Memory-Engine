from fastapi import APIRouter, UploadFile,File, HTTPException, status 
from app.services.ingest_service import process_uploaded_file_chunk
from app.models.files import update_total_chunks
from app.core.config import settings
from pathlib import Path

router = APIRouter()

@router.post("/ingest")
async def upload_log(request: dict):

    try:
        pass
    
    except Exception as e:
        return {"message": "There was an error uploading the file"}
    
