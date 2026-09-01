"""Streaming ingestion.

Files are read in fixed-size chunks and never fully materialised in memory. A
``LineBuffer`` carries an incomplete trailing line across chunk boundaries so a
read boundary can never become a logical log boundary.
"""

import time
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.core.mongo import raw_log_chunks_col
from app.core.redis import redis_client
from app.repositories import events as events_repo
from app.repositories import files as files_repo
from app.schemas.enums import SEVERE_LEVELS, EmbeddingStatus, FileStatus
from app.services.parser import parse_log_line
from app.services.storage import storage
from app.utils.datetime_utils import utc_now

logger = get_logger(__name__)


class IngestError(Exception):
    pass


class LineBuffer:
    """Accumulates chunk text and yields only complete lines."""

    def __init__(self) -> None:
        self._remainder = ""

    def feed(self, chunk: str) -> list[str]:
        data = self._remainder + chunk
        parts = data.split("\n")
        # The final element is always incomplete (empty when the chunk ended on a newline).
        self._remainder = parts.pop()
        return [part.rstrip("\r") for part in parts]

    def flush(self) -> list[str]:
        rest, self._remainder = self._remainder, ""
        return [rest.rstrip("\r")] if rest else []

    @property
    def pending(self) -> str:
        return self._remainder


class _IngestState:
    def __init__(self, file_id: str, user_id: str) -> None:
        self.file_id = file_id
        self.user_id = user_id
        self.sequence_number = 0
        self.line_no = 0
        self.events_created = 0
        self.events_queued = 0
        self.errors_seen = 0
        self.lines_skipped = 0
        self.pending_docs: list[dict[str, Any]] = []


async def _persist_raw_chunk(state: _IngestState, lines: list[str], start_line: int) -> None:
    await raw_log_chunks_col.update_one(
        {"file_id": state.file_id, "sequence_number": state.sequence_number},
        {
            "$set": {
                "file_id": state.file_id,
                "user_id": state.user_id,
                "sequence_number": state.sequence_number,
                "content": "\n".join(lines),
                "start_line_no": start_line,
                "end_line_no": start_line + len(lines) - 1,
                "created_at": utc_now(),
            }
        },
        upsert=True,
    )


async def _flush_events(state: _IngestState) -> None:
    if not state.pending_docs:
        return

    docs = state.pending_docs
    state.pending_docs = []
    inserted_ids = await events_repo.bulk_insert_events(docs)
    state.events_created += len(inserted_ids)

    if not inserted_ids:
        return

    # Quiet lines stay keyword-searchable in Mongo but never spend vector-store budget.
    embeddable = [
        event_id
        for event_id, doc in zip(inserted_ids, docs)
        if doc.get("level") in settings.embeddable_levels
    ]
    if not embeddable:
        await events_repo.mark_embedding_status(inserted_ids, EmbeddingStatus.SKIPPED)
        return

    skipped = [event_id for event_id in inserted_ids if event_id not in set(embeddable)]
    if skipped:
        await events_repo.mark_embedding_status(skipped, EmbeddingStatus.SKIPPED)

    try:
        pipeline = redis_client.pipeline()
        for event_id in embeddable:
            pipeline.lpush(settings.EMBEDDING_QUEUE, event_id)
        await pipeline.execute()
        await events_repo.mark_embedding_status(embeddable, EmbeddingStatus.QUEUED)
        state.events_queued += len(embeddable)
    except Exception:
        # The API must not fail because the queue is down; the worker backfills PENDING rows.
        logger.warning(
            "failed to enqueue embedding jobs", exc_info=True, extra={"file_id": state.file_id}
        )


def _build_event_doc(state: _IngestState, line: str, line_no: int) -> dict[str, Any] | None:
    parsed = parse_log_line(line)
    if parsed is None:
        return None

    return {
        **parsed,
        "user_id": state.user_id,
        "file_id": state.file_id,
        "line_no": line_no,
        "chunk_sequence": state.sequence_number,
        "raw_line": line[:2000],
        "embedding_id": None,
        "embedding_status": EmbeddingStatus.PENDING.value,
        "incident_id": None,
        "created_at": utc_now(),
    }


async def _process_lines(state: _IngestState, lines: list[str]) -> None:
    if not lines:
        return

    start_line = state.line_no + 1
    await _persist_raw_chunk(state, lines, start_line)

    for offset, line in enumerate(lines):
        line_no = start_line + offset
        try:
            doc = _build_event_doc(state, line, line_no)
        except Exception:
            # One malformed line must never abort the file.
            logger.warning(
                "failed to parse line", exc_info=True, extra={"file_id": state.file_id, "line_no": line_no}
            )
            state.lines_skipped += 1
            continue

        if doc is None:
            state.lines_skipped += 1
            continue

        if doc.get("level") in SEVERE_LEVELS:
            state.errors_seen += 1
        state.pending_docs.append(doc)

        if len(state.pending_docs) >= settings.EVENT_BULK_BATCH:
            await _flush_events(state)

    state.line_no = start_line + len(lines) - 1
    state.sequence_number += 1


async def ingest_file(file_id: str, user_id: str, *, force: bool = False) -> dict[str, Any]:
    file_doc = await files_repo.get_file(file_id, user_id)
    if file_doc is None:
        raise IngestError("File not found")

    status = file_doc.get("status")
    if status == FileStatus.COMPLETED.value and not force:
        return {
            "file_id": file_id,
            "status": FileStatus.COMPLETED,
            "chunks_processed": file_doc.get("total_chunks", 0),
            "events_created": file_doc.get("total_events", 0),
            "lines_skipped": 0,
            "duration_ms": 0.0,
        }

    stored_name = file_doc.get("stored_name")
    if not stored_name or not storage.exists(stored_name):
        await files_repo.mark_ingest_failed(file_id, user_id, "Uploaded file is missing from storage")
        raise IngestError("Uploaded file is missing from storage")

    started = time.perf_counter()
    await files_repo.mark_ingest_started(file_id, user_id)
    # Re-ingestion is idempotent: previous derived data for this file is discarded first.
    await events_repo.delete_events_for_file(file_id, user_id)

    state = _IngestState(file_id, user_id)
    buffer = LineBuffer()

    try:
        async with storage.open_text(stored_name) as handle:
            while True:
                chunk = await handle.read(settings.READ_CHUNK_BYTES)
                if not chunk:
                    break
                await _process_lines(state, buffer.feed(chunk))
            await _process_lines(state, buffer.flush())

        await _flush_events(state)
    except Exception as exc:
        # Driver errors can carry an entire rejected batch, so never persist one whole.
        reason = f"{type(exc).__name__}: {exc}"[:500]
        await files_repo.mark_ingest_failed(file_id, user_id, reason)
        logger.exception("ingestion failed", extra={"file_id": file_id, "user_id": user_id})
        raise IngestError("Ingestion failed while reading the log file") from exc

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    # Only the embedding worker can move a file out of EMBEDDING, so a file with
    # nothing to embed has to be completed here.
    final_status = FileStatus.EMBEDDING if state.events_queued else FileStatus.COMPLETED

    await files_repo.set_status(
        file_id,
        user_id,
        final_status,
        total_events=state.events_created,
        total_errors=state.errors_seen,
        total_chunks=state.sequence_number,
        last_line_no=state.line_no,
        ingest_completed_at=utc_now(),
        error_message=None,
    )

    logger.info(
        "ingestion completed",
        extra={
            "operation": "ingest",
            "file_id": file_id,
            "user_id": user_id,
            "events_created": state.events_created,
            "chunks": state.sequence_number,
            "lines_skipped": state.lines_skipped,
            "duration_ms": duration_ms,
        },
    )

    return {
        "file_id": file_id,
        "status": final_status,
        "chunks_processed": state.sequence_number,
        "events_created": state.events_created,
        "lines_skipped": state.lines_skipped,
        "duration_ms": duration_ms,
    }

