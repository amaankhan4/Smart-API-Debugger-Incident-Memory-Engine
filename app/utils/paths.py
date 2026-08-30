import re
import unicodedata
from pathlib import Path

_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")
MAX_NAME_LENGTH = 120


def sanitize_filename(filename: str) -> str:
    """Reduce an untrusted upload name to a flat, path-traversal-safe token."""
    candidate = unicodedata.normalize("NFKD", filename or "")
    # PurePath handles both POSIX and Windows separators before we strip anything else.
    candidate = candidate.replace("\\", "/").split("/")[-1]
    candidate = _UNSAFE.sub("_", candidate).strip("._-")

    if not candidate:
        return "upload.log"
    if len(candidate) > MAX_NAME_LENGTH:
        stem, dot, suffix = candidate.rpartition(".")
        if dot and len(suffix) <= 10:
            candidate = stem[: MAX_NAME_LENGTH - len(suffix) - 1] + "." + suffix
        else:
            candidate = candidate[:MAX_NAME_LENGTH]
    return candidate


def resolve_within(base_dir: Path, *parts: str) -> Path:
    """Join under base_dir and fail closed if the result escapes it."""
    base = base_dir.resolve()
    candidate = (base.joinpath(*parts)).resolve()
    if candidate != base and base not in candidate.parents:
        raise ValueError("Resolved path escapes the storage directory")
    return candidate
