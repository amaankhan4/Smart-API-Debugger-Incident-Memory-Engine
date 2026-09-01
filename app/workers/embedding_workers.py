"""Embedding worker.

Runs independently of the API. Jobs are moved onto a processing list before being
worked so a crash cannot silently drop an event, and encoding happens in a thread
so the CPU-bound model never blocks the event loop.
"""

import asyncio
import signal
from typing import Any

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.mongo import events_col, file_col
from app.core.redis import close_redis, redis_client
from app.core.vector_db import EVENT_NAMESPACE, VectorQuotaExceeded, upsert_vectors
from app.repositories import events as events_repo
from app.schemas.enums import EmbeddingStatus, FileStatus
from app.services.embedding import build_embedding_text, get_embedding_provider
from app.utils.serialization import to_object_id

configure_logging()
logger = get_logger(__name__)

IDLE_SLEEP_SECONDS = 1
BACKFILL_INTERVAL_SECONDS = 30
QUOTA_BACKOFF_SECONDS = 300

_shutdown = asyncio.Event()


def _request_shutdown(*_: Any) -> None:
    logger.info("shutdown signal received; finishing in-flight batch")
    _shutdown.set()


async def _claim_batch() -> list[str]:
    """Block for the first job, then drain up to a full batch without blocking."""
    batch: list[str] = []

    first = await redis_client.blmove(
        settings.EMBEDDING_QUEUE,
        settings.EMBEDDING_PROCESSING_QUEUE,
        settings.EMBEDDING_BLOCK_SECONDS,
        "LEFT",
        "RIGHT",
    )
    if first is None:
        return batch
    batch.append(first)

    while len(batch) < settings.EMBEDDING_BATCH_SIZE:
        item = await redis_client.lmove(
            settings.EMBEDDING_QUEUE, settings.EMBEDDING_PROCESSING_QUEUE, "LEFT", "RIGHT"
        )
        if item is None:
            break
        batch.append(item)
    return batch


async def _ack(event_ids: list[str]) -> None:
    if not event_ids:
        return
    pipeline = redis_client.pipeline()
    for event_id in event_ids:
        pipeline.lrem(settings.EMBEDDING_PROCESSING_QUEUE, 1, event_id)
    await pipeline.execute()


async def _requeue(event_ids: list[str]) -> None:
    """Put work back untouched: a spent quota is not the event's fault, so no retry is burned."""
    if not event_ids:
        return
    pipeline = redis_client.pipeline()
    for event_id in event_ids:
        pipeline.lrem(settings.EMBEDDING_PROCESSING_QUEUE, 1, event_id)
        pipeline.rpush(settings.EMBEDDING_QUEUE, event_id)
    await pipeline.execute()


async def _retry_or_dead_letter(event_ids: list[str], reason: str) -> None:
    pipeline = redis_client.pipeline()
    for event_id in event_ids:
        attempts = await redis_client.hincrby("embeddings:attempts", event_id, 1)
        pipeline.lrem(settings.EMBEDDING_PROCESSING_QUEUE, 1, event_id)
        if attempts >= settings.EMBEDDING_MAX_RETRIES:
            pipeline.lpush(settings.EMBEDDING_DEAD_LETTER_QUEUE, event_id)
            pipeline.hdel("embeddings:attempts", event_id)
        else:
            pipeline.rpush(settings.EMBEDDING_QUEUE, event_id)
    await pipeline.execute()

    failed = [
        event_id
        for event_id in event_ids
        if int(await redis_client.hget("embeddings:attempts", event_id) or 0) == 0
    ]
    if failed:
        await events_repo.mark_embedding_status(failed, EmbeddingStatus.FAILED)
    logger.warning("embedding batch requeued", extra={"count": len(event_ids), "reason": reason})


async def _mark_files_completed(file_ids: set[str]) -> None:
    """Flip a file to COMPLETED once nothing is left to embed for it."""
    for file_id in file_ids:
        outstanding = await events_col.count_documents(
            {
                "file_id": file_id,
                "embedding_status": {
                    "$in": [EmbeddingStatus.PENDING.value, EmbeddingStatus.QUEUED.value]
                },
            }
        )
        if outstanding == 0:
            await file_col.update_one(
                {"file_id": file_id, "status": FileStatus.EMBEDDING.value},
                {"$set": {"status": FileStatus.COMPLETED.value}},
            )


async def _process_batch(event_ids: list[str]) -> None:
    object_ids = [oid for eid in event_ids if (oid := to_object_id(eid)) is not None]
    docs = await events_col.find({"_id": {"$in": object_ids}}, {"embedding": 0}).to_list(
        length=len(object_ids)
    )
    found = {str(doc["_id"]): doc for doc in docs}

    # Events deleted between enqueue and processing are acknowledged, not retried.
    missing = [event_id for event_id in event_ids if event_id not in found]
    await _ack(missing)

    workable = [found[event_id] for event_id in event_ids if event_id in found]
    if not workable:
        return

    texts = [build_embedding_text(doc) for doc in workable]
    provider = get_embedding_provider()

    try:
        vectors = await asyncio.to_thread(provider.embed, texts)
        await upsert_vectors(
            EVENT_NAMESPACE,
            [
                (
                    f"event_{doc['_id']}",
                    vector,
                    {
                        "event_id": str(doc["_id"]),
                        "user_id": str(doc.get("user_id") or ""),
                        "file_id": str(doc.get("file_id") or ""),
                        "service": str(doc.get("service") or "unknown"),
                        "level": str(doc.get("level") or "INFO"),
                        "error_category": str(doc.get("error_category") or "unknown"),
                    },
                )
                for doc, vector in zip(workable, vectors)
            ],
        )
    except VectorQuotaExceeded:
        await _requeue([str(doc["_id"]) for doc in workable])
        raise
    except Exception as exc:
        await _retry_or_dead_letter([str(doc["_id"]) for doc in workable], str(exc))
        return

    processed_ids = [str(doc["_id"]) for doc in workable]
    await events_repo.apply_embedding_results(
        [(event_id, f"event_{event_id}") for event_id in processed_ids]
    )
    await _ack(processed_ids)
    await redis_client.hdel("embeddings:attempts", *processed_ids)
    await _mark_files_completed({str(doc.get("file_id")) for doc in workable if doc.get("file_id")})

    logger.info("embedded batch", extra={"operation": "embedding", "count": len(processed_ids)})


async def _backfill_pending() -> None:
    """Recover events whose enqueue failed (for example, Redis was briefly down)."""
    docs = await events_col.find(
        {"embedding_status": EmbeddingStatus.PENDING.value}, {"_id": 1}
    ).limit(settings.EMBEDDING_BATCH_SIZE * 4).to_list(length=settings.EMBEDDING_BATCH_SIZE * 4)
    if not docs:
        return

    event_ids = [str(doc["_id"]) for doc in docs]
    pipeline = redis_client.pipeline()
    for event_id in event_ids:
        pipeline.rpush(settings.EMBEDDING_QUEUE, event_id)
    await pipeline.execute()
    await events_repo.mark_embedding_status(event_ids, EmbeddingStatus.QUEUED)
    logger.info("backfilled pending embeddings", extra={"count": len(event_ids)})


async def _recover_orphaned_jobs() -> None:
    """Return anything stranded on the processing list by a previous crash."""
    stranded = await redis_client.lrange(settings.EMBEDDING_PROCESSING_QUEUE, 0, -1)
    if not stranded:
        return
    pipeline = redis_client.pipeline()
    for event_id in stranded:
        pipeline.rpush(settings.EMBEDDING_QUEUE, event_id)
    pipeline.delete(settings.EMBEDDING_PROCESSING_QUEUE)
    await pipeline.execute()
    logger.info("recovered orphaned embedding jobs", extra={"count": len(stranded)})


async def run_worker() -> None:
    logger.info("embedding worker started", extra={"queue": settings.EMBEDDING_QUEUE})
    await _recover_orphaned_jobs()
    last_backfill = 0.0

    while not _shutdown.is_set():
        try:
            batch = await _claim_batch()
            if batch:
                await _process_batch(batch)
            else:
                now = asyncio.get_running_loop().time()
                if now - last_backfill > BACKFILL_INTERVAL_SECONDS:
                    last_backfill = now
                    await _backfill_pending()
                await asyncio.sleep(IDLE_SLEEP_SECONDS)
        except VectorQuotaExceeded:
            # The batch is already back on the queue; wait rather than spin on a spent quota.
            logger.warning(
                "embedding paused: daily vector quota spent",
                extra={"retry_in_seconds": QUOTA_BACKOFF_SECONDS},
            )
            await asyncio.sleep(QUOTA_BACKOFF_SECONDS)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("embedding worker loop error")
            await asyncio.sleep(IDLE_SLEEP_SECONDS)

    await close_redis()
    logger.info("embedding worker stopped")


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            # Windows ProactorEventLoop does not support add_signal_handler.
            signal.signal(sig, _request_shutdown)
    try:
        loop.run_until_complete(run_worker())
    finally:
        loop.close()


if __name__ == "__main__":
    main()

