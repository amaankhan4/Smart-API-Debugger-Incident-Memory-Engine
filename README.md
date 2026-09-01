# Incident Memory Engine

A semantic observability and incident-intelligence platform. It turns raw application
logs into structured events, semantic embeddings, clustered incident candidates,
searchable history, and durable human debugging knowledge.

```
Upload logs → Ingest & parse → Structured events → Embeddings → Semantic search
     → Incident clustering → Investigation → Human notes / resolution knowledge
```

The AI layer assists engineers with retrieval and grouping. It deliberately does **not**
claim to know root causes — clusters are labelled *incident candidates*, and the
authoritative explanation is the one a human writes down.

---

## Architecture

```
                       ┌───────────────┐
   Browser  ──────────▶│  React + Vite │
                       └───────┬───────┘
                               │ JWT / REST
                       ┌───────▼────────┐        ┌──────────────┐
                       │  FastAPI API   │───────▶│   MongoDB    │  source of truth
                       └───┬────────┬───┘        └──────────────┘
                           │        │
              enqueue jobs │        │ vector query
                       ┌───▼───┐    │            ┌──────────────┐
                       │ Redis │    └───────────▶│ Upstash Vec. │  semantic layer
                       └───┬───┘                 └──────▲───────┘
                           │                            │
        ┌──────────────────▼─────────┐   ┌──────────────┴────────────┐
        │     embedding-worker       │   │    clustering-worker      │
        │  MiniLM → vectors → Upstash│   │  DBSCAN → incidents       │
        └────────────────────────────┘   └───────────────────────────┘
```

**MongoDB** is the source of truth for structured data. **Upstash Vector** is the
retrieval layer only. **Redis** is the asynchronous job layer. Embedding never happens
inside an HTTP request.

### Repository layout

```
app/
├── main.py              # app wiring, CORS, error handlers, request timing
├── api/                 # HTTP routes only — no business logic
│   ├── deps.py          # get_current_user (identity from token, never from the body)
│   └── ...              # auth, files, ingest, events, search, incidents, analytics
├── core/                # config, security, logging, mongo, redis, vector_db
├── repositories/        # all database access, every query scoped by user_id
├── services/            # parser, ingestion, embedding, search, context, clustering, analytics
├── schemas/             # Pydantic request/response contracts + shared enums
├── utils/               # datetime, serialization, path safety
└── workers/             # embedding + clustering background processes
tests/                   # parser, chunking, auth, ownership, clustering, security
ui/                      # React + TypeScript frontend
```

---

## Prerequisites

- Python 3.11+
- Node.js 20+
- MongoDB and Redis (or Docker, which provides both)
- An [Upstash Vector](https://console.upstash.com) index: **Dense, 384 dimensions,
  COSINE, no hosted embedding model**. The app sends its own vectors, and the
  dimension and metric cannot be changed after the index is created.

---

## Quick start with Docker

```bash
cp .env.example .env
# Generate a real secret before starting:
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste into JWT_SECRET
docker compose up --build
```

| Service  | URL                         |
| -------- | --------------------------- |
| Frontend | http://localhost:5173       |
| API      | http://localhost:8000       |
| API docs | http://localhost:8000/docs  |

`docker compose` starts the frontend, API, both workers, MongoDB and Redis. The vector
store is hosted, so set `UPSTASH_VECTOR_REST_URL` and `UPSTASH_VECTOR_REST_TOKEN` in
`.env` first. To use MongoDB Atlas instead of the local container, point `MONGODB_URI`
at your SRV connection string and remove the `mongodb` service.

---

## One-command startup (local development)

`start.py` supervises the whole stack — API, both workers and the frontend — as a
single process group. It verifies the datastores first and reports what is wrong
instead of failing with a traceback.

```bash
python start.py           # everything
python start.py --check   # preflight checks only, start nothing
```

On Windows you can also **double-click `start.bat`**. It finds your interpreter
(preferring `.venv`), runs the launcher, and keeps the window open if startup fails.
macOS and Linux have `./start.sh`.

In VS Code: **Run Task → Start dev stack**, or **F5 → Dev stack (all services)**. The
launch configs also let you put breakpoints in the API or either worker on its own.

On first run it creates `.env` from `.env.example`, generates a real `JWT_SECRET`, and
writes `ui/.env` pointing at the local API. If a datastore is unreachable and Docker is
available, it starts those containers for you.

Useful flags: `--no-frontend`, `--no-workers`, `--no-docker`, `--no-reload`.

Ctrl+C stops every service, sending the signal the workers handle so they shut down
cleanly instead of being killed mid-batch.

---

## Manual setup

### 1. Datastores

```bash
docker run -d -p 27017:27017 --name ime-mongo mongo:7
docker run -d -p 6379:6379   --name ime-redis redis:7-alpine
```

No manual schema step is required. Collections are created on first write and all
indexes are built automatically at API startup by `ensure_indexes()`.

### 2. Backend

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

### 3. Workers

Each worker is a separate process. Run them in their own terminals.

```bash
python -m app.workers.embedding_workers    # events → vectors → Upstash Vector
python -m app.workers.clustering_worker    # vectors → DBSCAN → incidents
```

The API stays fully functional if the workers are down: events are stored with
`embedding_status: pending` and the embedding worker backfills them when it starts.

### 4. Frontend

```bash
cd ui
npm install
echo "VITE_API_BASE_URL=http://localhost:8000/api/v1" > .env
npm run dev
```

### 5. Tests

```bash
python -m pytest          # backend: 65 tests
cd ui && npm test         # frontend: 24 tests
```

---

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `MONGODB_URI` | — | Mongo connection string (**required**) |
| `MONGODB_DB` | — | Database name (**required**) |
| `REDIS_URL` | — | Redis connection URL. Required **unless** the Upstash pair below is set |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | — | Upstash credentials. The REST token doubles as the database password, so a `rediss://` TCP URL is derived from them |
| `UPSTASH_VECTOR_REST_URL` / `UPSTASH_VECTOR_REST_TOKEN` | — | Upstash Vector index (**required**) |
| `UPLOAD_DIR` | — | Local log storage directory (**required**) |
| `JWT_SECRET` | dev placeholder | Token signing key. Startup **fails** if left at the default when `ENVIRONMENT=production` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `720` | Access-token lifetime |
| `MAX_UPLOAD_BYTES` | `209715200` | Upload size ceiling (200 MB) |
| `ALLOWED_UPLOAD_EXTENSIONS` | `.log,.txt,.json,.ndjson` | Accepted file types |
| `READ_CHUNK_BYTES` | `1048576` | Ingestion read size (1 MB) |
| `EVENT_BULK_BATCH` | `500` | Events per bulk insert |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | 384-dim local embedding model |
| `EMBEDDING_MAX_RETRIES` | `3` | Attempts before a job is dead-lettered |
| `EMBEDDING_BLOCK_SECONDS` | `2` | Idle queue-poll length. Raise it on metered Redis (Upstash) so an idle worker burns fewer commands |
| `EMBED_MIN_LEVEL` | `WARN` | Only events at or above this level are embedded. Quieter lines stay keyword-searchable in Mongo |
| `VECTOR_DAILY_QUERY_LIMIT` / `VECTOR_DAILY_UPDATE_LIMIT` | `10000` | Daily vector budget. Matches the Upstash Vector free tier |
| `CLUSTER_EPS` / `CLUSTER_MIN_SAMPLES` | `0.35` / `3` | DBSCAN sensitivity |
| `CLUSTER_INTERVAL_SECONDS` | `900` | Clustering cycle period |
| `CORS_ORIGINS` | localhost:5173 | Comma-separated allowed origins |
| `LOG_JSON` | `false` | Structured JSON logs (recommended in production) |

Never commit a real `.env`. Only `.env.example` is tracked.

---

## Staying inside the Upstash Vector free tier

The free tier allows **10,000 updates and 10,000 queries per UTC day**, counted
separately. The app budgets against those numbers rather than discovering the limit
by being rejected:

- **Only `WARN` and above are embedded** (`EMBED_MIN_LEVEL`). Everything else is still
  stored and keyword-searchable in MongoDB. This is the largest lever, because one
  embedded event costs one update.
- **Clustering skips users whose embedded-event count has not changed**, so an idle
  stack spends nothing. Re-reading every vector every cycle was the biggest waste.
- **Counters live in Redis** and are incremented once per API call, not once per
  vector, so tracking a full day costs a few hundred Redis commands.
- **Degradation is graceful.** When the budget is spent, queued events stay queued and
  are retried after the reset instead of being dead-lettered, search falls back to
  keyword matching, and the UI shows a banner. `GET /api/v1/system/quota` returns the
  current usage.

### How large a log file can I upload per day?

One embedded line costs one update, so with a daily budget of 10,000:

```
max lines = 10,000 / (share of lines at WARN or above)
```

At a typical 150–170 bytes per line:

| Share of lines at WARN+ | Lines per day | Approx. file size |
| --- | --- | --- |
| 5% (healthy service) | 200,000 | ~32 MB |
| 10% | 100,000 | ~16 MB |
| 20% (noisy) | 50,000 | ~8 MB |
| 100% (pure error dump) | 10,000 | ~1.6 MB |

**A practical daily ceiling is ~8 MB / 50,000 lines**, which holds even if a fifth of
your log is warnings or errors. If you are uploading a filtered error-only extract,
keep it under **~1.5 MB**.

`examples/checkout-api.log` is a small demo file covering eight recurring failure
patterns across nine services. It is deliberately error-heavy (67% WARN+) so
clustering produces incidents immediately, which makes it a poor guide to sizing.

---

## API overview

All routes are versioned under `/api/v1`. Every route except registration and login
requires `Authorization: Bearer <token>`, and every query is scoped to the
authenticated user.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/auth/register` | Create an account, returns a token |
| `POST` | `/auth/login` | Authenticate |
| `GET` | `/auth/me` | Current identity |
| `POST` | `/files` | Upload a log file |
| `GET` | `/files` | List files (paginated, filter by status) |
| `GET` | `/files/{file_id}` | File metadata + processing counters |
| `DELETE` | `/files/{file_id}` | Delete a file and its derived data |
| `POST` | `/ingest/{file_id}` | Parse a file into events (`?force=true` to re-ingest) |
| `GET` | `/events` | Filter events by file, service, level, category, incident, trace, time |
| `GET` | `/events/{id}` | Single event |
| `GET` | `/events/{id}/context` | Surrounding logs (trace → time → line → raw chunk) |
| `GET` | `/events/{id}/similar` | Similar historical events with similarity scores |
| `GET` | `/search?q=` | Semantic / keyword / hybrid search |
| `POST` | `/incidents/cluster` | Run clustering on demand |
| `GET` | `/incidents` | Incident console list (sort + filter) |
| `GET` | `/incidents/{id}` | Summary, representative events, timeline, similar incidents |
| `GET` | `/incidents/{id}/events` | All events in an incident (paginated) |
| `PATCH` | `/incidents/{id}/status` | Set status / severity |
| `GET`/`POST` | `/incidents/{id}/notes` | Investigation knowledge |
| `DELETE` | `/incidents/{id}/notes/{note_id}` | Remove a note |
| `GET` | `/analytics` | Dashboard aggregations |
| `GET` | `/health`, `/ready` | Liveness and dependency readiness |

Interactive documentation is served at `/docs`.

---

## Example workflow

1. Register at http://localhost:5173, which signs you straight in.
2. Drag one or more `.log` files onto **Files**. Each upload gets a UUID `file_id`;
   the original name is sanitized and never used as an identifier.
3. Press **Ingest**. The file is streamed in 1 MB chunks with a line buffer, so a log
   line split across a chunk boundary is still parsed as one event.
4. Watch the status move `uploaded → processing → embedding → completed` as the
   embedding worker drains the queue.
5. The clustering worker groups recurring failures into incidents.
6. Open **Log Explorer**, filter by level or service, and select an event to see its
   surrounding context, similar historical events, and its incident.
7. Search semantically: `database connection timeout after deployment`.
8. Open the incident, set it to **Investigating**, and record a **Root cause** note:
   *"Retry storm exhausted the DB connection pool."*
9. Mark it **Resolved**. The note stays attached, so the next engineer who hits the
   same signature finds the answer through *Similar incidents*.

---

## Design notes

**Chunk boundaries are never logical boundaries.** `LineBuffer` holds an incomplete
trailing line until the next read completes it. This is covered by a test that splits
the same input at every possible byte offset.

**Ownership is enforced server-side.** `user_id` is always derived from the verified
token. Vector-search hits are re-checked against MongoDB with the owner filter, so a
stale vector cannot leak another tenant's event.

**Incident keys are stable.** A cluster's key is a hash of its dominant symptom
(service, category, exception, normalized message template) rather than its size, so
re-running clustering updates an existing incident instead of duplicating it. Human
fields — status, notes — are never overwritten by a clustering pass.

**Incidents stay bounded.** Only centroid-nearest representative events are stored on
the incident document; full membership lives on the events themselves.

**Failures are contained.** A malformed line is skipped and counted, never fatal to a
file. If Redis is unavailable during ingest, events persist as `pending` and are
backfilled later.

---

## Known limitations

- Ingestion runs inside the request that triggers it. Very large files hold the
  connection open; moving `POST /ingest` onto the Redis queue is the natural next step.
- Clustering re-clusters a rolling window of recent error events rather than
  incrementally assigning new ones.
- `similar_incidents` compares stored centroids, so it is only as current as the last
  clustering cycle.
- Local disk storage is dev-oriented; `LogStorage` is the seam for S3.
- The command palette covers navigation and search, not every mutation.
- Single-node workers only — there is no distributed lock, so run one clustering worker.

## Recommended next steps

- Move ingestion fully onto the job queue with progress streamed over SSE/WebSocket.
- Add refresh tokens and rotation; access tokens are currently long-lived.
- Export Prometheus metrics from the timings already recorded in structured logs.
- Add saved searches and alerting on recurring incident signatures.
- Introduce incremental clustering so new events join incidents without a full re-run.

