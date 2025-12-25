from fastapi import FastAPI
import uvicorn
from app.api import ingest, events

app = FastAPI(title="Smart API Debugger")

app.include_router(ingest.router, prefix="/api/ingest")
app.include_router(events.router, prefix="/api/events")
# app.include_router(incidents.router, prefix="/api/incidents")

@app.get("/")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="debug", debug=True,
                workers=1, limit_concurrency=1, limit_max_requests=1)
