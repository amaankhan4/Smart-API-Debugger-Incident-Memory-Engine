from fastapi import APIRouter, UploadFile # type: ignore
from app.services.log_parser import parse_logs
from app.core.mongo import raw_logs_col, events_col

router = APIRouter()

@router.post("/upload")
async def upload_log(file: UploadFile):
    content = await file.read()
    events = parse_logs(content)

    await raw_logs_col.insert_one({
        "filename": file.filename,
        "raw": content.decode(),
    })

    if events:
        await events_col.insert_many(events)

    return {"events_extracted": len(events)}
