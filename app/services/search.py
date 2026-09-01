"""Semantic, keyword and hybrid event search.

The vector store supplies candidate ranking; MongoDB remains the source of truth
and applies the ownership filter a second time so a stale or poisoned vector
record can never surface another tenant's event.
"""

import re
import time
from typing import Any

from app.core.logging import get_logger
from app.core.vector_db import (
    EVENT_NAMESPACE,
    VectorQuotaExceeded,
    VectorUnavailable,
    build_filter,
    query_vectors,
    similarity_from_score,
)
from app.repositories import events as events_repo
from app.schemas.search import SearchFilters
from app.services.embedding import get_embedding_provider
from app.utils.serialization import serialize_docs

logger = get_logger(__name__)

OVERSAMPLE = 4
_RRF_K = 60


def escape_regex(term: str) -> str:
    return re.escape(term.strip())


def _event_filter(user_id: str, filters: SearchFilters) -> str:
    return build_filter(
        {
            "user_id": user_id,
            "file_id": filters.file_id,
            "service": filters.service,
            "level": filters.level.value if filters.level else None,
            "error_category": filters.error_category.value if filters.error_category else None,
        }
    )


def explain_match(query: str, event: dict[str, Any]) -> list[str]:
    """Surface the concrete metadata overlap instead of implying causal certainty."""
    reasons: list[str] = []
    lowered = query.lower()
    for field, label in (
        ("service", "service"),
        ("exception", "exception"),
        ("error_category", "category"),
        ("path", "endpoint"),
    ):
        value = event.get(field)
        if value and str(value).lower() in lowered:
            reasons.append(f"{label}:{value}")
    if event.get("status_code") and str(event["status_code"]) in query:
        reasons.append(f"status:{event['status_code']}")
    return reasons


async def _semantic_candidates(
    user_id: str, query: str, filters: SearchFilters, limit: int
) -> tuple[list[tuple[str, float]], str | None]:
    provider = get_embedding_provider()
    vector = provider.embed_one(query)

    try:
        matches = await query_vectors(
            EVENT_NAMESPACE,
            vector,
            top_k=max(limit * OVERSAMPLE, limit),
            metadata_filter=_event_filter(user_id, filters),
        )
    except VectorQuotaExceeded:
        logger.warning("semantic search skipped: daily vector quota spent")
        return [], "vector_quota_exceeded"
    except VectorUnavailable:
        logger.warning("vector search unavailable", exc_info=True)
        return [], "vector_unavailable"

    ranked: list[tuple[str, float]] = []
    for match in matches:
        event_id = (match.metadata or {}).get("event_id")
        if not event_id:
            continue
        ranked.append((str(event_id), similarity_from_score(match.score)))
    return ranked, None


async def _keyword_candidates(
    user_id: str, query: str, filters: SearchFilters, limit: int
) -> list[tuple[str, float]]:
    mongo_query = events_repo.build_event_query(
        user_id,
        file_id=filters.file_id,
        service=filters.service,
        level=filters.level.value if filters.level else None,
        error_category=filters.error_category.value if filters.error_category else None,
        incident_id=filters.incident_id,
        start_time=filters.start_time,
        end_time=filters.end_time,
        search=escape_regex(query),
    )
    docs, _ = await events_repo.list_events(mongo_query, limit=limit * OVERSAMPLE, offset=0)
    total = len(docs) or 1
    return [(str(doc["_id"]), 1.0 - (index / total)) for index, doc in enumerate(docs)]


def _reciprocal_rank_fusion(
    rankings: list[list[tuple[str, float]]]
) -> dict[str, float]:
    fused: dict[str, float] = {}
    for ranking in rankings:
        for rank, (event_id, _score) in enumerate(ranking):
            fused[event_id] = fused.get(event_id, 0.0) + 1.0 / (_RRF_K + rank + 1)
    return fused


async def search_events(
    *,
    user_id: str,
    query: str,
    filters: SearchFilters,
    mode: str = "hybrid",
    limit: int = 25,
) -> dict[str, Any]:
    started = time.perf_counter()
    query = query.strip()
    if not query:
        return {
            "query": query,
            "mode": mode,
            "took_ms": 0.0,
            "results": [],
            "total": 0,
            "degraded_reason": None,
        }

    semantic: list[tuple[str, float]] = []
    keyword: list[tuple[str, float]] = []
    degraded_reason: str | None = None

    if mode in {"semantic", "hybrid"}:
        semantic, degraded_reason = await _semantic_candidates(user_id, query, filters, limit)
    # A semantic-only request still answers with keyword hits rather than nothing.
    if mode in {"keyword", "hybrid"} or degraded_reason:
        keyword = await _keyword_candidates(user_id, query, filters, limit)

    semantic_scores = dict(semantic)
    if mode == "hybrid":
        fused = _reciprocal_rank_fusion([semantic, keyword])
        ordered_ids = sorted(fused, key=lambda key: fused[key], reverse=True)
    elif mode == "semantic":
        ordered_ids = [event_id for event_id, _ in (keyword if degraded_reason else semantic)]
    else:
        ordered_ids = [event_id for event_id, _ in keyword]

    ordered_ids = ordered_ids[: limit * OVERSAMPLE]
    docs = await events_repo.get_events_by_ids(ordered_ids, user_id)
    by_id = {str(doc["_id"]): doc for doc in docs}

    keyword_scores = dict(keyword)
    results: list[dict[str, Any]] = []
    for event_id in ordered_ids:
        doc = by_id.get(event_id)
        if doc is None:
            continue
        if filters.incident_id and doc.get("incident_id") != filters.incident_id:
            continue
        if filters.start_time and doc.get("timestamp") and doc["timestamp"] < filters.start_time:
            continue
        if filters.end_time and doc.get("timestamp") and doc["timestamp"] > filters.end_time:
            continue

        score = semantic_scores.get(event_id, keyword_scores.get(event_id, 0.0))
        source = "semantic" if event_id in semantic_scores else "keyword"
        serialized = serialize_docs([doc])[0]
        results.append(
            {
                "event": serialized,
                "score": round(score, 4),
                "source": source if mode != "hybrid" else mode,
                "matched_on": explain_match(query, doc),
            }
        )
        if len(results) >= limit:
            break

    took_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "search executed",
        extra={"operation": "search", "mode": mode, "duration_ms": took_ms, "results": len(results)},
    )
    return {
        "query": query,
        "mode": mode,
        "took_ms": took_ms,
        "results": results,
        "total": len(results),
        "degraded_reason": degraded_reason,
    }


async def similar_to_event(user_id: str, event: dict[str, Any], limit: int = 10) -> list[dict[str, Any]]:
    """Find historical events resembling a known event, excluding the event itself."""
    from app.services.embedding import build_embedding_text

    text = build_embedding_text(event)
    ranked, _ = await _semantic_candidates(user_id, text, SearchFilters(), limit + 1)

    event_id = str(event["_id"]) if "_id" in event else event.get("id")
    ranked = [(candidate, score) for candidate, score in ranked if candidate != event_id][:limit]
    if not ranked:
        return []

    docs = await events_repo.get_events_by_ids([candidate for candidate, _ in ranked], user_id)
    by_id = {str(doc["_id"]): doc for doc in docs}

    matches: list[dict[str, Any]] = []
    for candidate, score in ranked:
        doc = by_id.get(candidate)
        if doc is None:
            continue
        matches.append(
            {
                "event": serialize_docs([doc])[0],
                "score": round(score, 4),
                "distance": round(1.0 - score, 4),
                "matched_on": explain_match(text, doc),
            }
        )
    return matches
