# Deployment guide

Deploy the UI to Vercel and the HTTP API to Render. The repository includes
deployment configuration for both, and neither deployment requires Docker.

## 1. Managed services

Create these first and keep their credentials in the host dashboards only:

- A MongoDB Atlas Free cluster for `MONGODB_URI`.
- An Upstash Redis database for the Redis URL/token pair.
- An Upstash Vector dense index: **384 dimensions**, **COSINE**, with no hosted
  embedding model.

## 2. Deploy the API

Create a Render Blueprint from this repository. `render.yaml` creates the
FastAPI service and prompts for the managed-service credentials. It deliberately
uses `/tmp/incident-memory-uploads`: free web services have ephemeral disks, so
uploaded source files are not durable across a restart.

After Vercel is deployed, set `CORS_ORIGINS` to its exact URL, for example
`https://incident-memory-engine.vercel.app`, then redeploy the API.

## 3. Deploy the UI

Create a Vercel project from this repository with **Root Directory** set to
`ui`. Set this production environment variable before building:

```
VITE_API_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com/api/v1
```

Redeploy the UI any time this value changes; Vite embeds it in the generated
static files.

## 4. Background workers

The API is deployable as-is, but semantic embedding and incident clustering
need the two long-running worker commands below:

```
python -m app.workers.embedding_workers
python -m app.workers.clustering_worker
```

They are intentionally not placed in `render.yaml`, because the free Render
offering supports free web services but not persistent background workers. For
a full demo, run them on a worker-capable host or add a deployment-mode
refactor that turns those jobs into scheduled/serverless work. Until then,
uploads and structured search work; queued semantic enrichment remains pending.

## 5. Verify

- `https://YOUR-RENDER-SERVICE.onrender.com/health` should return a healthy
  response.
- Open the Vercel URL, register an account, upload the included demo log, and
  verify that the file and parsed events appear.
