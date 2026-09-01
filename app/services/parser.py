"""Extensible log parsing.

A line is run through an ordered chain of format parsers (JSON, logfmt, bracketed,
plain). The first one that recognises the line wins; whatever it could not determine
is left as ``None`` rather than guessed. A separate enrichment pass then extracts
transport/exception facts that are format-independent.
"""

import json
import re
from datetime import datetime, timezone
from typing import Any, Callable

from app.schemas.enums import ErrorCategory, Level

MAX_MESSAGE_LENGTH = 8000

# Every parsed event carries this exact key set so stored documents have a uniform
# shape and "field was absent" is always expressed as None rather than a missing key.
OPTIONAL_FIELDS = (
    "timestamp",
    "trace_id",
    "span_id",
    "correlation_id",
    "http_method",
    "path",
    "status_code",
    "exception",
    "stack_trace",
    "language",
    "framework",
)

_LEVEL_ALIASES = {
    "TRACE": Level.TRACE,
    "DEBUG": Level.DEBUG,
    "FINE": Level.DEBUG,
    "INFO": Level.INFO,
    "INFORMATION": Level.INFO,
    "NOTICE": Level.INFO,
    "WARN": Level.WARN,
    "WARNING": Level.WARN,
    "ERROR": Level.ERROR,
    "ERR": Level.ERROR,
    "SEVERE": Level.ERROR,
    "CRITICAL": Level.CRITICAL,
    "FATAL": Level.CRITICAL,
    "PANIC": Level.CRITICAL,
}

_TIMESTAMP_RE = (
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,9})?(?:Z|[+-]\d{2}:?\d{2})?"
)

# [2024-01-01 10:00:00] ERROR [service=api] message
BRACKETED_RE = re.compile(
    rf"^\s*\[(?P<timestamp>{_TIMESTAMP_RE})\]\s*"
    rf"(?:\[?(?P<level>[A-Za-z]+)\]?)?\s*"
    rf"(?P<rest>.*)$"
)

# 2024-01-01T10:00:00Z ERROR auth-service message
PLAIN_RE = re.compile(
    rf"^\s*(?P<timestamp>{_TIMESTAMP_RE})\s+"
    rf"(?P<level>[A-Za-z]+)\s+"
    rf"(?P<rest>.*)$"
)

# Python logging's default and its common variants:
#   2024-01-01 10:00:00,123 - ERROR - message
#   2024-01-01 10:00:00,123 - my.module - ERROR - message
#   2024-01-01 10:00:00 | ERROR | message
# The delimiter must be surrounded by spaces so an ISO date is never split.
DELIMITED_RE = re.compile(
    rf"^\s*(?P<timestamp>{_TIMESTAMP_RE})\s+(?P<delimiter>[-|])\s+(?P<rest>.+)$"
)

_TRACE_RE = re.compile(r"\b(?:trace[_-]?id|traceId)\s*[=:]\s*\"?([A-Za-z0-9._\-]+)\"?", re.I)
_SPAN_RE = re.compile(r"\b(?:span[_-]?id|spanId)\s*[=:]\s*\"?([A-Za-z0-9._\-]+)\"?", re.I)
_CORRELATION_RE = re.compile(
    r"\b(?:correlation[_-]?id|correlationId|request[_-]?id|requestId)\s*[=:]\s*\"?([A-Za-z0-9._\-]+)\"?", re.I
)
_SERVICE_RE = re.compile(r"\b(?:service|svc|logger|component|app)\s*[=:]\s*\"?([A-Za-z0-9._\-]+)\"?", re.I)
_HTTP_RE = re.compile(
    r"\b(?P<method>GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\b\s+(?P<path>/[^\s\"'\]]*)"
)
_STATUS_KV_RE = re.compile(r"\b(?:status(?:[_-]?code)?|http_status)\s*[=:]\s*(\d{3})\b", re.I)
_STATUS_INLINE_RE = re.compile(r"\b(?P<status>[1-5]\d{2})\b(?=\s|$)")
_EXCEPTION_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9_]*(?:Exception|Error|Timeout|Failure|Fault|Denied|Refused))\b"
)
_DOTTED_EXCEPTION_RE = re.compile(r"\b((?:[a-z][A-Za-z0-9_]*\.){1,}[A-Z][A-Za-z0-9_]*(?:Exception|Error))\b")
_STACK_HINT_RE = re.compile(r"(?:\bat\s+[\w.$<>]+\(|Traceback \(most recent call last\)|^\s+File \")", re.M)

_CATEGORY_RULES: list[tuple[ErrorCategory, re.Pattern[str]]] = [
    (ErrorCategory.TIMEOUT, re.compile(r"\btime(?:d)?\s?out|timeout|deadline exceeded\b", re.I)),
    (
        ErrorCategory.DATABASE,
        re.compile(
            r"\b(database|db |sql|postgres|mysql|mongo|redis|connection pool|deadlock|"
            r"psycopg|sqlalchemy|queryfailed|duplicate key)\b",
            re.I,
        ),
    ),
    (ErrorCategory.RATE_LIMIT, re.compile(r"\brate.?limit|too many requests|throttl", re.I)),
    (
        ErrorCategory.AUTHENTICATION,
        re.compile(r"\b(unauthenticated|unauthorized|invalid credentials|invalid token|jwt|login failed|401)\b", re.I),
    ),
    (ErrorCategory.AUTHORIZATION, re.compile(r"\b(forbidden|access denied|permission denied|not allowed|403)\b", re.I)),
    (ErrorCategory.VALIDATION, re.compile(r"\b(validation|invalid (?:input|payload|request|field)|schema|malformed|422)\b", re.I)),
    (
        ErrorCategory.NETWORK,
        re.compile(r"\b(connection (?:refused|reset|aborted)|econnrefused|dns|socket|unreachable|tls|ssl handshake)\b", re.I),
    ),
    (ErrorCategory.CONFIGURATION, re.compile(r"\b(config|missing env|environment variable|not configured|misconfigur)\b", re.I)),
    (
        ErrorCategory.DEPENDENCY,
        re.compile(r"\b(upstream|downstream|third.?party|external service|gateway|service unavailable|502|503|504)\b", re.I),
    ),
]

_FRAMEWORK_HINTS: list[tuple[str, str, re.Pattern[str]]] = [
    ("python", "django", re.compile(r"\bdjango\b", re.I)),
    ("python", "fastapi", re.compile(r"\bfastapi|uvicorn\b", re.I)),
    ("python", "flask", re.compile(r"\bflask|werkzeug\b", re.I)),
    ("python", None, re.compile(r"Traceback \(most recent call last\)|\.py\b", re.I)),  # type: ignore[list-item]
    ("java", "spring", re.compile(r"\bspring(?:framework|boot)?\b", re.I)),
    ("java", None, re.compile(r"\bjava\.[a-z]+\.|\.java:\d+", re.I)),  # type: ignore[list-item]
    ("javascript", "express", re.compile(r"\bexpress\b", re.I)),
    ("javascript", "nestjs", re.compile(r"\bnestjs|nest\b", re.I)),
    ("javascript", None, re.compile(r"\bnode_modules\b|\.js:\d+|at Object\.", re.I)),  # type: ignore[list-item]
    ("go", None, re.compile(r"\bgoroutine \d+|\.go:\d+", re.I)),  # type: ignore[list-item]
]


def _normalize_level(raw: str | None) -> Level | None:
    if not raw:
        return None
    return _LEVEL_ALIASES.get(raw.strip().strip("[]():").upper())


def parse_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        # Heuristic: values past year ~2001 in ms are too large to be seconds.
        seconds = value / 1000 if value > 1_000_000_000_000 else value
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    text = str(value).strip().strip("[]")
    if not text:
        return None
    normalized = text.replace(",", ".")
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%d/%b/%Y:%H:%M:%S %z"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_json(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not (stripped.startswith("{") and stripped.endswith("}")):
        return None
    try:
        payload = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(payload, dict):
        return None

    def pick(*keys: str) -> Any:
        for key in keys:
            if payload.get(key) not in (None, ""):
                return payload[key]
        return None

    message = pick("message", "msg", "event", "log", "text")
    return {
        "timestamp": parse_timestamp(pick("timestamp", "time", "ts", "@timestamp", "eventTime")),
        "level": _normalize_level(str(pick("level", "severity", "levelname", "lvl") or "") or None),
        "service": pick("service", "service_name", "app", "logger", "component", "kubernetes.container_name"),
        "message": str(message) if message is not None else stripped,
        "trace_id": pick("trace_id", "traceId", "traceID", "dd.trace_id"),
        "span_id": pick("span_id", "spanId", "spanID"),
        "correlation_id": pick("correlation_id", "correlationId", "request_id", "requestId"),
        "http_method": pick("method", "http_method", "httpMethod", "http.method"),
        "path": pick("path", "route", "url", "http_path", "http.target"),
        "status_code": pick("status", "status_code", "statusCode", "http_status", "http.status_code"),
        "exception": pick("exception", "error_type", "exception_class", "errorType"),
        "stack_trace": pick("stack", "stack_trace", "stacktrace", "exception_stacktrace"),
    }


def _parse_bracketed(line: str) -> dict[str, Any] | None:
    match = BRACKETED_RE.match(line)
    if not match:
        return None
    level = _normalize_level(match.group("level"))
    rest = match.group("rest") or ""
    # A non-level word in the level slot is really part of the message.
    if level is None and match.group("level"):
        rest = f"{match.group('level')} {rest}".strip()
    return {
        "timestamp": parse_timestamp(match.group("timestamp")),
        "level": level,
        "service": None,
        "message": rest.strip() or line.strip(),
    }


def _looks_like_service(token: str) -> bool:
    """Distinguish a logger/service name from the first word of prose."""
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._\-]{1,63}", token) or token.endswith((":", ",")):
        return False
    return bool(re.search(r"[.\-_]", token)) or token.islower()


def _parse_delimited(line: str) -> dict[str, Any] | None:
    match = DELIMITED_RE.match(line)
    if not match:
        return None

    separator = f" {match.group('delimiter')} "
    parts = [part.strip() for part in match.group("rest").split(separator)]

    level = _normalize_level(parts[0])
    service: str | None = None
    if level is not None:
        remainder = parts[1:]
        # The logger name sits either side of the level depending on the format string.
        if len(remainder) >= 2 and _looks_like_service(remainder[0]):
            service, remainder = remainder[0], remainder[1:]
    elif len(parts) >= 2 and (level := _normalize_level(parts[1])) is not None:
        service, remainder = parts[0], parts[2:]
    else:
        # No level in the slot, but the timestamp is still worth keeping.
        remainder = parts

    return {
        "timestamp": parse_timestamp(match.group("timestamp")),
        "level": level,
        "service": service,
        "message": separator.join(remainder).strip() or line.strip(),
    }


def _parse_plain(line: str) -> dict[str, Any] | None:
    match = PLAIN_RE.match(line)
    if not match:
        return None
    level = _normalize_level(match.group("level"))
    if level is None:
        return None

    rest = (match.group("rest") or "").strip()
    service: str | None = None
    # "<level> <service> <message>" only when the token looks like an identifier, not prose.
    parts = rest.split(maxsplit=1)
    if len(parts) == 2 and _looks_like_service(parts[0]):
        service, rest = parts[0], parts[1]

    return {
        "timestamp": parse_timestamp(match.group("timestamp")),
        "level": level,
        "service": service,
        "message": rest or line.strip(),
    }


def _parse_fallback(line: str) -> dict[str, Any]:
    inline_level = None
    for token in re.findall(r"\b[A-Z]{3,8}\b", line[:80]):
        inline_level = _normalize_level(token)
        if inline_level:
            break
    return {
        "timestamp": None,
        "level": inline_level,
        "service": None,
        "message": line.strip(),
    }


_FORMAT_PARSERS: list[Callable[[str], dict[str, Any] | None]] = [
    _parse_json,
    _parse_bracketed,
    _parse_delimited,
    _parse_plain,
]


def classify_error(text: str, exception: str | None, status_code: int | None) -> ErrorCategory:
    haystack = f"{exception or ''} {text}"
    for category, pattern in _CATEGORY_RULES:
        if pattern.search(haystack):
            return category
    if status_code is not None:
        if status_code == 401:
            return ErrorCategory.AUTHENTICATION
        if status_code == 403:
            return ErrorCategory.AUTHORIZATION
        if status_code == 408:
            return ErrorCategory.TIMEOUT
        if status_code == 429:
            return ErrorCategory.RATE_LIMIT
        if status_code == 422:
            return ErrorCategory.VALIDATION
        if status_code in {502, 503, 504}:
            return ErrorCategory.DEPENDENCY
    return ErrorCategory.UNKNOWN


def _detect_runtime(text: str) -> tuple[str | None, str | None]:
    language: str | None = None
    framework: str | None = None
    for lang, fw, pattern in _FRAMEWORK_HINTS:
        if pattern.search(text):
            language = language or lang
            if fw and framework is None:
                framework = fw
            if language and framework:
                break
    return language, framework


def _coerce_status(value: Any) -> int | None:
    try:
        status = int(value)
    except (TypeError, ValueError):
        return None
    return status if 100 <= status <= 599 else None


def enrich(parsed: dict[str, Any], original: str) -> dict[str, Any]:
    """Fill transport/exception facts that are independent of the surface format."""
    message = parsed.get("message") or original

    if not parsed.get("trace_id") and (m := _TRACE_RE.search(original)):
        parsed["trace_id"] = m.group(1)
    if not parsed.get("span_id") and (m := _SPAN_RE.search(original)):
        parsed["span_id"] = m.group(1)
    if not parsed.get("correlation_id") and (m := _CORRELATION_RE.search(original)):
        parsed["correlation_id"] = m.group(1)
    if not parsed.get("service") and (m := _SERVICE_RE.search(original)):
        parsed["service"] = m.group(1)

    if not parsed.get("http_method") or not parsed.get("path"):
        if m := _HTTP_RE.search(original):
            parsed["http_method"] = parsed.get("http_method") or m.group("method")
            parsed["path"] = parsed.get("path") or m.group("path")

    status = _coerce_status(parsed.get("status_code"))
    if status is None and (m := _STATUS_KV_RE.search(original)):
        status = _coerce_status(m.group(1))
    if status is None and parsed.get("http_method"):
        # Only trust a bare 3-digit number when the line is clearly an HTTP access log.
        tail = original[-40:]
        if m := _STATUS_INLINE_RE.search(tail):
            status = _coerce_status(m.group("status"))
    parsed["status_code"] = status

    exception = parsed.get("exception")
    if not exception:
        if m := _DOTTED_EXCEPTION_RE.search(original):
            exception = m.group(1)
        elif m := _EXCEPTION_RE.search(original):
            exception = m.group(1)
    parsed["exception"] = exception

    if not parsed.get("stack_trace") and _STACK_HINT_RE.search(original):
        parsed["stack_trace"] = original[:MAX_MESSAGE_LENGTH]

    language, framework = _detect_runtime(original)
    parsed["language"] = parsed.get("language") or language
    parsed["framework"] = parsed.get("framework") or framework

    level: Level = parsed.get("level") or Level.INFO
    if level in (Level.ERROR, Level.CRITICAL) or exception or (status and status >= 500):
        parsed["error_category"] = classify_error(message, exception, status).value
    else:
        parsed["error_category"] = ErrorCategory.UNKNOWN.value

    parsed["level"] = level.value if isinstance(level, Level) else str(level)
    parsed["service"] = (parsed.get("service") or "unknown").strip() or "unknown"
    parsed["message"] = (message or "").strip()[:MAX_MESSAGE_LENGTH]
    for field in OPTIONAL_FIELDS:
        parsed.setdefault(field, None)
    return parsed


def parse_log_line(line: str) -> dict[str, Any] | None:
    """Parse one raw line. Returns ``None`` for blank lines; never raises."""
    original = (line or "").rstrip("\r\n")
    if not original.strip():
        return None

    parsed: dict[str, Any] | None = None
    for parser in _FORMAT_PARSERS:
        try:
            parsed = parser(original)
        except Exception:
            parsed = None
        if parsed:
            break
    if parsed is None:
        parsed = _parse_fallback(original)

    try:
        return enrich(parsed, original)
    except Exception:
        # Enrichment is best-effort: a bad line must never abort file ingestion.
        return {
            "level": Level.INFO.value,
            "service": "unknown",
            "message": original.strip()[:MAX_MESSAGE_LENGTH],
            "error_category": ErrorCategory.UNKNOWN.value,
            **{field: None for field in OPTIONAL_FIELDS},
        }

