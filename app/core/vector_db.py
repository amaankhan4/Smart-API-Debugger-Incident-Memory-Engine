"""Upstash Vector adapter.

Events and incidents share one index, separated by namespace, because the index
dimension and metric are fixed at creation and both use the same 384-dim cosine
space. Every call is metered against the daily free-tier budget so the app
degrades predictably instead of collapsing once Upstash starts rejecting calls.
"""

import re
from functools import lru_cache
from typing import Any, Awaitable, Callable, Sequence, TypeVar

from upstash_vector import AsyncIndex
from upstash_vector.errors import UpstashError
from upstash_vector.types import FetchResult, QueryResult

from app.core import quota
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

EVENT_NAMESPACE = "events"
INCIDENT_NAMESPACE = "incidents"

T = TypeVar("T")

# UpstashError carries only a message, so the daily-limit response is matched by text.
_QUOTA_ERROR = re.compile(r"quota|daily limit|limit exceeded|too many requests", re.I)

# Filter values are interpolated into an expression language with no escape syntax,
# so anything outside this set is dropped rather than quoted.
_UNSAFE_IN_LITERAL = re.compile(r"[^A-Za-z0-9 _\-./:@+]")


class VectorQuotaExceeded(RuntimeError):
    """The daily Upstash Vector allowance is spent. It resets at UTC midnight."""


class VectorUnavailable(RuntimeError):
    """The vector backend could not be reached or rejected the request."""


@lru_cache
def get_index() -> AsyncIndex:
    if not (settings.UPSTASH_VECTOR_REST_URL and settings.UPSTASH_VECTOR_REST_TOKEN):
        raise RuntimeError(
            "Vector store is not configured: set UPSTASH_VECTOR_REST_URL and "
            "UPSTASH_VECTOR_REST_TOKEN"
        )
    return AsyncIndex(
        url=settings.UPSTASH_VECTOR_REST_URL,
        token=settings.UPSTASH_VECTOR_REST_TOKEN,
        retries=1,
    )


def similarity_from_score(score: float | None) -> float:
    """Upstash maps cosine onto 0..1 as (1 + cos) / 2; callers want plain cosine."""
    if score is None:
        return 0.0
    return max(0.0, min(1.0, 2.0 * float(score) - 1.0))


def build_filter(equals: dict[str, Any]) -> str:
    """Compose an Upstash metadata filter from code-defined keys and untrusted values."""
    clauses = [
        f"{key} = '{_UNSAFE_IN_LITERAL.sub('', str(value))}'"
        for key, value in equals.items()
        if value is not None and value != ""
    ]
    return " AND ".join(clauses)


async def _spend(kind: quota.Kind, amount: int, call: Callable[[], Awaitable[T]]) -> T:
    if not await quota.has_budget(kind, amount):
        raise VectorQuotaExceeded(f"daily vector {kind} allowance is spent")
    try:
        result = await call()
    except UpstashError as exc:
        if _QUOTA_ERROR.search(str(exc)):
            await quota.exhaust(kind)
            raise VectorQuotaExceeded(str(exc)) from exc
        raise VectorUnavailable(str(exc)) from exc
    await quota.consume(kind, amount)
    return result


async def upsert_vectors(
    namespace: str, vectors: Sequence[tuple[str, list[float], dict[str, Any]]]
) -> None:
    if not vectors:
        return
    await _spend(
        quota.UPDATE,
        len(vectors),
        lambda: get_index().upsert(vectors=list(vectors), namespace=namespace),
    )


async def query_vectors(
    namespace: str,
    vector: list[float],
    *,
    top_k: int,
    metadata_filter: str = "",
) -> list[QueryResult]:
    return await _spend(
        quota.QUERY,
        1,
        lambda: get_index().query(
            vector=vector,
            top_k=top_k,
            filter=metadata_filter,
            include_metadata=True,
            namespace=namespace,
        ),
    )


async def fetch_vectors(namespace: str, ids: list[str]) -> dict[str, list[float]]:
    """Read raw embeddings back, batched to keep each call inside the request size cap."""
    found: dict[str, list[float]] = {}
    batch_size = settings.VECTOR_FETCH_BATCH

    for start in range(0, len(ids), batch_size):
        batch = ids[start : start + batch_size]
        results: list[FetchResult | None] = await _spend(
            quota.QUERY,
            1,
            lambda ids=batch: get_index().fetch(  # type: ignore[misc]
                ids=ids, include_vectors=True, namespace=namespace
            ),
        )
        for item in results:
            if item is not None and item.vector:
                found[str(item.id)] = list(item.vector)
    return found


async def vector_backend_healthy() -> bool:
    try:
        await get_index().info()
        return True
    except Exception:
        logger.warning("upstash vector info failed", exc_info=True)
        return False

