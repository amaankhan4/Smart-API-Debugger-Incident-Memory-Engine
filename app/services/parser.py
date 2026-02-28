import re
from datetime import datetime
from typing import Any

# Supports common log formats:
# 2024-01-01T10:00:00Z INFO auth trace_id=abc message
# [2024-01-01 10:00:00] ERROR [service=api] [trace_id=abc] message
LOG_PATTERN = re.compile(
    r"^\s*"
    r"(?P<timestamp>\[?\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?\]?)?\s*"
    r"(?P<level>TRACE|DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL)?\s*"
    r"(?P<service>[a-zA-Z0-9_.-]+)?\s*"
    r"(?P<message>.*)$"
)

TRACE_ID_PATTERN = re.compile(r"(?:trace_id|traceId|trace-id)[=:]\s*([a-zA-Z0-9\-_.]+)")
SERVICE_PATTERN = re.compile(r"(?:service|svc)[=:]\s*([a-zA-Z0-9\-_.]+)")


def _parse_timestamp(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip("[] ")
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    for fmt in (None, "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            if fmt is None:
                return datetime.fromisoformat(cleaned)
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def parse_log_line(line: str) -> dict[str, Any] | None:
    original = line.rstrip("\n")
    if not original.strip():
        return None

    match = LOG_PATTERN.match(original)
    if not match:
        return {
            "timestamp": None,
            "level": "INFO",
            "service": "unknown",
            "message": original,
            "trace_id": None,
        }

    groups = match.groupdict()
    message = (groups.get("message") or "").strip() or original.strip()

    level = (groups.get("level") or "INFO").upper()
    if level == "WARNING":
        level = "WARN"

    trace_match = TRACE_ID_PATTERN.search(original)
    service_match = SERVICE_PATTERN.search(original)

    service = service_match.group(1) if service_match else (groups.get("service") or "unknown")

    return {
        "timestamp": _parse_timestamp(groups.get("timestamp")),
        "level": level,
        "service": service,
        "message": message,
        "trace_id": trace_match.group(1) if trace_match else None,
    }
