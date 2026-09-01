"""Daily budget tracking for the Upstash Vector free tier.

Upstash meters queries and updates separately and resets both at UTC midnight.
The counters live in Redis so the API and both workers share one view, which
lets the app stop spending *before* Upstash starts rejecting calls, and lets the
UI show how much of the day's allowance is left.

Counters are incremented once per API call rather than once per vector, so
tracking a full day of vector traffic costs only a few hundred Redis commands.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal

from app.core.config import settings
from app.core.redis import redis_client

Kind = Literal["query", "update"]

QUERY: Kind = "query"
UPDATE: Kind = "update"

_PREFIX = "vector:usage"


def limit_for(kind: Kind) -> int:
    return (
        settings.VECTOR_DAILY_QUERY_LIMIT
        if kind == QUERY
        else settings.VECTOR_DAILY_UPDATE_LIMIT
    )


def resets_at(now: datetime | None = None) -> datetime:
    moment = now or datetime.now(timezone.utc)
    return (moment + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def _key(kind: Kind, now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    return f"{_PREFIX}:{kind}:{moment:%Y-%m-%d}"


def _ttl_seconds(now: datetime | None = None) -> int:
    moment = now or datetime.now(timezone.utc)
    return max(60, int((resets_at(moment) - moment).total_seconds()))


async def used(kind: Kind) -> int:
    raw = await redis_client.get(_key(kind))
    return int(raw or 0)


async def has_budget(kind: Kind, amount: int = 1) -> bool:
    return await used(kind) + amount <= limit_for(kind)


async def consume(kind: Kind, amount: int = 1) -> None:
    key = _key(kind)
    pipeline = redis_client.pipeline()
    pipeline.incrby(key, amount)
    pipeline.expire(key, _ttl_seconds())
    await pipeline.execute()


async def exhaust(kind: Kind) -> None:
    """Upstash refused the call, so trust it over the local count for the rest of the day."""
    key = _key(kind)
    pipeline = redis_client.pipeline()
    pipeline.set(key, limit_for(kind))
    pipeline.expire(key, _ttl_seconds())
    await pipeline.execute()


async def snapshot() -> dict[str, object]:
    queries = await used(QUERY)
    updates = await used(UPDATE)
    query_limit = limit_for(QUERY)
    update_limit = limit_for(UPDATE)
    return {
        "queries_used": queries,
        "queries_limit": query_limit,
        "updates_used": updates,
        "updates_limit": update_limit,
        "queries_exhausted": queries >= query_limit,
        "updates_exhausted": updates >= update_limit,
        "resets_at": resets_at(),
    }
