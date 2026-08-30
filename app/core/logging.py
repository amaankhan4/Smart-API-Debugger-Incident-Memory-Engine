import json
import logging
import sys
import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.core.config import settings

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__) | {"asctime", "message"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key not in _RESERVED:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    if getattr(root, "_ime_configured", False):
        return

    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-8s %(name)s %(message)s"))

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.LOG_LEVEL.upper())
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    root._ime_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.LoggerAdapter | logging.Logger:
    return logging.getLogger(name)


@contextmanager
def track_duration(logger: logging.Logger, operation: str, **fields: Any) -> Iterator[dict[str, Any]]:
    """Emit a single structured timing record so the platform can observe itself."""
    started = time.perf_counter()
    context: dict[str, Any] = {}
    try:
        yield context
    except Exception:
        logger.exception(
            "%s failed", operation, extra={"operation": operation, "duration_ms": round((time.perf_counter() - started) * 1000, 2), **fields, **context}
        )
        raise
    else:
        logger.info(
            "%s completed",
            operation,
            extra={"operation": operation, "duration_ms": round((time.perf_counter() - started) * 1000, 2), **fields, **context},
        )
