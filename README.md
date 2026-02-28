# Smart-API-Debugger-Incident-Memory-Engine

Production-ready MVP for AI-driven log intelligence:

`Upload -> Ingest -> Parse -> Store -> Embed -> Cluster -> Search -> Incident Management`

## Implemented capabilities
- Chunk-wise upload and ingestion.
- Line-buffered parsing with carry-over between chunks.
- Structured event extraction (`timestamp`, `level`, `service`, `message`, `trace_id`) with `file_id` and `line_no`.
- Separate storage for `files`, `raw_log_chunks`, `events`, `incidents`, `incident_notes`.
- Async embedding worker that writes vectors to Chroma and links vectors to events.
- Similarity search endpoint (`query -> embedding -> vector search -> event metadata`).
- DBSCAN incident clustering and event-to-incident linkage.
- Context retrieval supports same `trace_id`, time window, line window, and raw chunk fallback.
- Idempotent ingest behavior for already-ingested files.

## API surface
- `POST /api/upload/` upload file
- `GET /api/upload/all-files` list known uploaded files
- `POST /api/ingest/{file_id}` trigger ingestion
- `GET /api/events/` list/query events
- `GET /api/events/similar?query=...` similar event search
- `GET /api/events/{event_id}/context` context retrieval
- `POST /api/incidents/cluster` run clustering
- `GET /api/incidents/` list incidents
- `GET /api/incidents/{incident_id}` incident detail
- `POST /api/incidents/{incident_id}/notes?note=...` add note

## Run instructions
1. Create `.env`:

```env
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=incident_memory
REDIS_URL=redis://localhost:6379/0
CHROMA_HOST=localhost
CHROMA_PORT=8001
UPLOAD_DIR=./uploads
CLUSTER_INTERVAL_SECONDS=300
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start API:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

4. Start workers (separate terminals):

```bash
python -m app.workers.embedding_workers
python -m app.workers.clustering_worker
```

## Notes
- API and workers are independent processes.
- Chroma is expected to be reachable at `CHROMA_HOST:CHROMA_PORT`.
- Startup creates indexes for ingestion safety and duplicate prevention.
