import time
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import (
    analytics,
    events,
    incident,
    ingest,
    search,
    system,
    upload,
    user_management,
)
from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.mongo import client as mongo_client
from app.core.mongo import ensure_indexes
from app.core.redis import close_redis, redis_client
from app.core.vector_db import vector_backend_healthy

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await ensure_indexes()
    logger.info("api started", extra={"environment": settings.ENVIRONMENT})
    yield
    await close_redis()
    mongo_client.close()
    logger.info("api stopped")


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Semantic observability and incident-intelligence platform.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            },
        )
        raise

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["x-request-id"] = request_id
    response.headers["x-response-time-ms"] = str(duration_ms)
    logger.info(
        "request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        },
    )
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": f"http_{exc.status_code}"},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Request validation failed", "code": "validation_error", "errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(_: Request, exc: Exception) -> JSONResponse:
    # Internal details stay in the logs; clients get a stable, non-revealing message.
    logger.exception("unhandled error", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error", "code": "internal_error"},
    )


prefix = settings.API_V1_PREFIX
app.include_router(user_management.router, prefix=f"{prefix}/auth", tags=["auth"])
app.include_router(upload.router, prefix=f"{prefix}/files", tags=["files"])
app.include_router(ingest.router, prefix=f"{prefix}/ingest", tags=["ingest"])
app.include_router(events.router, prefix=f"{prefix}/events", tags=["events"])
app.include_router(search.router, prefix=f"{prefix}/search", tags=["search"])
app.include_router(incident.router, prefix=f"{prefix}/incidents", tags=["incidents"])
app.include_router(analytics.router, prefix=f"{prefix}/analytics", tags=["analytics"])
app.include_router(system.router, prefix=f"{prefix}/system", tags=["system"])


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
async def ready() -> JSONResponse:
    checks = {"mongodb": False, "redis": False, "vector": False}
    try:
        await mongo_client.admin.command("ping")
        checks["mongodb"] = True
    except Exception:
        logger.warning("mongodb readiness check failed", exc_info=True)
    try:
        await redis_client.ping()
        checks["redis"] = True
    except Exception:
        logger.warning("redis readiness check failed", exc_info=True)
    checks["vector"] = await vector_backend_healthy()

    healthy = all(checks.values())
    return JSONResponse(
        status_code=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)

