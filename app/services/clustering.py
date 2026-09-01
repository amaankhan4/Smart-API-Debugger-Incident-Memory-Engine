"""Incident clustering.

DBSCAN groups semantically similar failures without being told how many clusters
exist. The output is explicitly a set of *incident candidates* — co-occurrence in
embedding space is evidence of a shared symptom, not proof of a shared root cause.
"""

import hashlib
import re
import time
from collections import Counter, defaultdict
from typing import Any, Iterable

import numpy as np
from sklearn.cluster import DBSCAN

from app.core.config import settings
from app.core.logging import get_logger
from app.core.vector_db import (
    EVENT_NAMESPACE,
    INCIDENT_NAMESPACE,
    VectorQuotaExceeded,
    VectorUnavailable,
    build_filter,
    fetch_vectors,
    query_vectors,
    similarity_from_score,
    upsert_vectors,
)
from app.repositories import events as events_repo
from app.repositories import incidents as incidents_repo
from app.schemas.enums import IncidentSeverity, Level
from app.utils.datetime_utils import as_utc

logger = get_logger(__name__)

_NUMBER_RE = re.compile(r"\d+")
_UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
_HEX_RE = re.compile(r"\b[0-9a-f]{12,}\b", re.I)
_QUOTED_RE = re.compile(r"'[^']*'|\"[^\"]*\"")


def normalize_message(message: str) -> str:
    """Collapse volatile tokens so the same failure yields the same signature."""
    text = _UUID_RE.sub("<uuid>", message or "")
    text = _HEX_RE.sub("<hex>", text)
    text = _QUOTED_RE.sub("<str>", text)
    text = _NUMBER_RE.sub("<n>", text)
    return " ".join(text.split()).lower()[:200]


def cluster_signature(docs: list[dict[str, Any]]) -> str:
    """Stable key derived from the cluster's dominant symptom, not its size."""
    service = Counter(doc.get("service") or "unknown" for doc in docs).most_common(1)[0][0]
    category = Counter(doc.get("error_category") or "unknown" for doc in docs).most_common(1)[0][0]
    exceptions = [doc.get("exception") for doc in docs if doc.get("exception")]
    exception = Counter(exceptions).most_common(1)[0][0] if exceptions else "none"
    template = Counter(normalize_message(doc.get("message", "")) for doc in docs).most_common(1)[0][0]

    raw = f"{service}|{category}|{exception}|{template}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:32]


def derive_severity(docs: list[dict[str, Any]]) -> IncidentSeverity:
    levels = Counter(doc.get("level") for doc in docs)
    statuses = [doc.get("status_code") for doc in docs if doc.get("status_code")]
    server_errors = sum(1 for status in statuses if int(status) >= 500)

    if levels.get(Level.CRITICAL.value):
        return IncidentSeverity.CRITICAL
    if len(docs) >= 50 or server_errors >= 20:
        return IncidentSeverity.HIGH
    if levels.get(Level.ERROR.value, 0) >= 10 or server_errors:
        return IncidentSeverity.MEDIUM
    return IncidentSeverity.LOW


def build_title(docs: list[dict[str, Any]]) -> str:
    exceptions = [doc.get("exception") for doc in docs if doc.get("exception")]
    service = Counter(doc.get("service") or "unknown" for doc in docs).most_common(1)[0][0]
    if exceptions:
        headline = Counter(exceptions).most_common(1)[0][0]
    else:
        headline = Counter(doc.get("message", "").strip() for doc in docs).most_common(1)[0][0]
    headline = " ".join(str(headline).split())[:110] or "Recurring failure"
    return f"{headline} in {service}"


async def _fetch_vectors(embedding_ids: list[str]) -> dict[str, list[float]]:
    try:
        return await fetch_vectors(EVENT_NAMESPACE, embedding_ids)
    except VectorUnavailable:
        logger.warning("failed to fetch vectors from the vector store", exc_info=True)
        return {}


def _distinct(values: Iterable[Any], limit: int = 20) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and str(value) not in seen:
            seen.append(str(value))
        if len(seen) >= limit:
            break
    return seen


def _representative_ids(docs: list[dict[str, Any]], vectors: dict[str, list[float]]) -> list[str]:
    """Pick the events closest to the cluster centroid — the most typical examples."""
    limit = settings.INCIDENT_REPRESENTATIVE_LIMIT
    usable = [(doc, vectors.get(str(doc.get("embedding_id")))) for doc in docs]
    usable = [(doc, vector) for doc, vector in usable if vector]
    if not usable:
        return [str(doc["_id"]) for doc in docs[:limit]]

    matrix = np.array([vector for _, vector in usable], dtype=np.float32)
    centroid = matrix.mean(axis=0)
    norm = np.linalg.norm(centroid)
    if norm:
        centroid = centroid / norm
    scores = matrix @ centroid
    order = np.argsort(-scores)[:limit]
    return [str(usable[int(index)][0]["_id"]) for index in order]


async def _index_incident_vector(
    incident_id: str, user_id: str, title: str, vectors: list[list[float]], metadata: dict[str, Any]
) -> None:
    if not vectors:
        return
    matrix = np.array(vectors, dtype=np.float32)
    centroid = matrix.mean(axis=0)
    norm = np.linalg.norm(centroid)
    if norm:
        centroid = centroid / norm
    try:
        await upsert_vectors(
            INCIDENT_NAMESPACE,
            [
                (
                    f"incident_{incident_id}",
                    centroid.tolist(),
                    {
                        "incident_id": incident_id,
                        "user_id": user_id,
                        "title": title,
                        **metadata,
                    },
                )
            ],
        )
    except (VectorQuotaExceeded, VectorUnavailable):
        logger.warning("failed to index incident vector", exc_info=True, extra={"incident_id": incident_id})


async def run_incident_clustering(
    user_id: str,
    *,
    eps: float | None = None,
    min_samples: int | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    eps = settings.CLUSTER_EPS if eps is None else eps
    min_samples = settings.CLUSTER_MIN_SAMPLES if min_samples is None else min_samples

    docs = await events_repo.events_for_clustering(user_id, settings.CLUSTER_MAX_EVENTS)
    if len(docs) < min_samples:
        return _empty_result(started, "not_enough_events")

    try:
        vectors = await _fetch_vectors(
            [str(doc["embedding_id"]) for doc in docs if doc.get("embedding_id")]
        )
    except VectorQuotaExceeded:
        logger.warning("clustering skipped: daily vector quota spent")
        return _empty_result(started, "vector_quota_exceeded")
    usable = [(doc, vectors[str(doc["embedding_id"])]) for doc in docs if str(doc.get("embedding_id")) in vectors]
    if len(usable) < min_samples:
        return _empty_result(started, "not_enough_embeddings")

    matrix = np.array([vector for _, vector in usable], dtype=np.float32)
    labels = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine").fit_predict(matrix)

    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for index, label in enumerate(labels):
        if label == -1:
            continue  # noise: not enough neighbours to call it a recurring incident
        grouped[int(label)].append(usable[index][0])

    created = 0
    updated = 0
    clustered_events = 0

    for label, label_docs in grouped.items():
        signature = cluster_signature(label_docs)
        timestamps = [ts for doc in label_docs if (ts := as_utc(doc.get("timestamp")))]
        representative_ids = _representative_ids(label_docs, vectors)

        payload = {
            "title": build_title(label_docs),
            "summary": "\n".join(doc.get("message", "") for doc in label_docs[:5])[:2000],
            "severity": derive_severity(label_docs).value,
            "cluster_label": label,
            "event_count": len(label_docs),
            "error_category": Counter(
                doc.get("error_category") or "unknown" for doc in label_docs
            ).most_common(1)[0][0],
            "services": _distinct(doc.get("service") for doc in label_docs),
            "endpoints": _distinct(doc.get("path") for doc in label_docs),
            "file_ids": _distinct(doc.get("file_id") for doc in label_docs),
            # Bounded: the full membership lives on the events, not inside the incident.
            "representative_event_ids": representative_ids,
            "first_seen": min(timestamps) if timestamps else None,
            "last_seen": max(timestamps) if timestamps else None,
        }

        incident_id, was_created = await incidents_repo.upsert_incident(user_id, signature, payload)
        created += int(was_created)
        updated += int(not was_created)
        clustered_events += len(label_docs)

        await events_repo.assign_incident([str(doc["_id"]) for doc in label_docs], incident_id)
        await _index_incident_vector(
            incident_id,
            user_id,
            payload["title"],
            [vectors[str(doc["embedding_id"])] for doc in label_docs if str(doc.get("embedding_id")) in vectors],
            {"severity": payload["severity"], "error_category": payload["error_category"]},
        )

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    logger.info(
        "clustering completed",
        extra={
            "operation": "clustering",
            "user_id": user_id,
            "clusters_created": created,
            "clusters_updated": updated,
            "events_clustered": clustered_events,
            "duration_ms": duration_ms,
        },
    )
    return {
        "clusters_created": created,
        "clusters_updated": updated,
        "events_clustered": clustered_events,
        "duration_ms": duration_ms,
        "reason": None,
    }


def _empty_result(started: float, reason: str) -> dict[str, Any]:
    return {
        "clusters_created": 0,
        "clusters_updated": 0,
        "events_clustered": 0,
        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
        "reason": reason,
    }


async def find_similar_incidents(user_id: str, incident: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
    incident_id = str(incident["_id"])
    try:
        current = await fetch_vectors(INCIDENT_NAMESPACE, [f"incident_{incident_id}"])
        centroid = current.get(f"incident_{incident_id}")
        if not centroid:
            return []

        matches = await query_vectors(
            INCIDENT_NAMESPACE,
            centroid,
            top_k=limit + 1,
            metadata_filter=build_filter({"user_id": user_id}),
        )
    except (VectorQuotaExceeded, VectorUnavailable):
        logger.warning("similar incident lookup failed", exc_info=True)
        return []

    results: list[dict[str, Any]] = []
    for match in matches:
        candidate_id = (match.metadata or {}).get("incident_id")
        if not candidate_id or candidate_id == incident_id:
            continue
        candidate = await incidents_repo.get_incident(str(candidate_id), user_id)
        if candidate is None:
            continue
        results.append({"incident": candidate, "score": similarity_from_score(match.score)})
        if len(results) >= limit:
            break
    return results

