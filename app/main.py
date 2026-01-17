from fastapi import FastAPI
import uvicorn
from app.api import ingest, incident, events, upload, user_management
# from app.workers import embedding_workers

app = FastAPI(title="Smart API Debugger")

app.include_router(ingest.router, prefix="/api/ingest")
app.include_router(events.router, prefix="/api/events")
app.include_router(incident.router, prefix="/api/incidents")
app.include_router(upload.router, prefix="/api/upload")
# app.include_router(user_management.router, prefix="/api/users")

@app.get("/")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="debug"
    )

# Run command
# uvicorn app.main:app --reload --log-level debug

