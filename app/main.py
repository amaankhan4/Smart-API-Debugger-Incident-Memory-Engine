from fastapi import FastAPI
import uvicorn

from app.api import events, incident, ingest, upload
from app.core.mongo import events_col, file_col, incidents_col, raw_log_chunks_col

app = FastAPI(title="Smart API Debugger")

app.include_router(upload.router, prefix="/api/upload", tags=["upload"])
app.include_router(ingest.router, prefix="/api/ingest", tags=["ingest"])
app.include_router(events.router, prefix="/api/events", tags=["events"])
app.include_router(incident.router, prefix="/api/incidents", tags=["incidents"])


@app.on_event("startup")
async def startup_indexes():
    await file_col.create_index("file_id", unique=True)
    await raw_log_chunks_col.create_index([("file_id", 1), ("sequence_number", 1)], unique=True)
    await events_col.create_index([("file_id", 1), ("line_no", 1)], unique=True)
    await events_col.create_index([("trace_id", 1), ("timestamp", 1)])
    await incidents_col.create_index("cluster_key", unique=True)


@app.get("/")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, log_level="debug")
