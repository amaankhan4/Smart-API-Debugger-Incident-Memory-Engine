"""Surrounding-log retrieval for a single event.

Strategies are tried in priority order: same trace, then same file within a
timestamp window, then a line-number window, then the raw chunk as a last resort.
"""

from datetime import timedelta
from typing import Any

from app.repositories import events as events_repo
from app.utils.datetime_utils import as_utc
from app.utils.serialization import serialize_doc, serialize_docs


async def build_event_context(
    *, user_id: str, event: dict[str, Any], line_window: int = 20, time_window_seconds: int = 120
) -> dict[str, Any]:
    file_id = event.get("file_id", "")
    line_no = int(event.get("line_no") or 0)
    event_id = str(event["_id"])

    trace_docs: list[dict[str, Any]] = []
    if event.get("trace_id"):
        trace_docs = await events_repo.trace_events(user_id, str(event["trace_id"]))

    neighbours: list[dict[str, Any]] = []
    strategy = "line_window"

    if len(trace_docs) > 1:
        strategy = "trace_id"
        neighbours = trace_docs
    else:
        timestamp = as_utc(event.get("timestamp"))
        if timestamp is not None:
            query = events_repo.build_event_query(
                user_id,
                file_id=file_id,
                start_time=timestamp - timedelta(seconds=time_window_seconds),
                end_time=timestamp + timedelta(seconds=time_window_seconds),
            )
            window_docs, _ = await events_repo.list_events(
                query, limit=(line_window * 2) + 1, offset=0, sort_field="line_no", sort_dir=1
            )
            if len(window_docs) > 1:
                strategy = "time_window"
                neighbours = window_docs

        if not neighbours:
            neighbours = await events_repo.context_window(user_id, file_id, line_no, line_window)

    before: list[dict[str, Any]] = []
    after: list[dict[str, Any]] = []
    for doc in neighbours:
        if str(doc["_id"]) == event_id:
            continue
        if int(doc.get("line_no") or 0) < line_no:
            before.append(doc)
        else:
            after.append(doc)

    before = before[-line_window:]
    after = after[:line_window]

    chunk = await events_repo.raw_chunk_for_line(file_id, line_no)
    if not neighbours and chunk is None:
        strategy = "unavailable"
    elif not neighbours:
        strategy = "raw_chunk"

    return {
        "event": serialize_doc(event),
        "strategy": strategy,
        "before": serialize_docs(before),
        "after": serialize_docs(after),
        "trace_events": serialize_docs(trace_docs) if strategy != "trace_id" else [],
        "raw_chunk": (chunk or {}).get("content"),
        "raw_chunk_sequence": (chunk or {}).get("sequence_number"),
    }
