"""Clustering worker.

Clustering is per-user: incidents are only ever formed from a single owner's events,
so a cluster can never span tenants.
"""

import asyncio
import signal
from typing import Any

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.core.mongo import client as mongo_client
from app.core.mongo import events_col
from app.core.redis import close_redis
from app.schemas.enums import EmbeddingStatus
from app.services.clustering import run_incident_clustering

configure_logging()
logger = get_logger(__name__)

_shutdown = asyncio.Event()

# Re-clustering unchanged data re-reads every vector for no new result, which is the
# single biggest waste of the vector store's daily budget.
_last_embedded_count: dict[str, int] = {}


def _request_shutdown(*_: Any) -> None:
    logger.info("shutdown signal received")
    _shutdown.set()


async def _users_with_embedded_events() -> list[str]:
    user_ids = await events_col.distinct(
        "user_id", {"embedding_status": EmbeddingStatus.COMPLETED.value}
    )
    return [str(user_id) for user_id in user_ids if user_id]


async def run_cycle() -> None:
    for user_id in await _users_with_embedded_events():
        embedded = await events_col.count_documents(
            {"user_id": user_id, "embedding_status": EmbeddingStatus.COMPLETED.value}
        )
        if _last_embedded_count.get(user_id) == embedded:
            continue

        try:
            result = await run_incident_clustering(user_id)
            logger.info("clustering cycle", extra={"user_id": user_id, **result})
        except Exception:
            # One user's failure must not stop clustering for everyone else.
            logger.exception("clustering failed for user", extra={"user_id": user_id})
            continue

        if result.get("reason") != "vector_quota_exceeded":
            _last_embedded_count[user_id] = embedded


async def run_worker() -> None:
    logger.info("clustering worker started", extra={"interval": settings.CLUSTER_INTERVAL_SECONDS})
    while not _shutdown.is_set():
        await run_cycle()
        try:
            await asyncio.wait_for(_shutdown.wait(), timeout=settings.CLUSTER_INTERVAL_SECONDS)
        except asyncio.TimeoutError:
            continue

    await close_redis()
    mongo_client.close()
    logger.info("clustering worker stopped")


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            signal.signal(sig, _request_shutdown)
    try:
        loop.run_until_complete(run_worker())
    finally:
        loop.close()


if __name__ == "__main__":
    main()

