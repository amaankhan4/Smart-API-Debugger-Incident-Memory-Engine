from enum import Enum


class Level(str, Enum):
    TRACE = "TRACE"
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


SEVERE_LEVELS = {Level.ERROR.value, Level.CRITICAL.value}

LEVEL_SEVERITY: dict[str, int] = {
    Level.TRACE.value: 0,
    Level.DEBUG.value: 1,
    Level.INFO.value: 2,
    Level.WARN.value: 3,
    Level.ERROR.value: 4,
    Level.CRITICAL.value: 5,
}


class ErrorCategory(str, Enum):
    DATABASE = "database"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


class FileStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    EMBEDDING = "embedding"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class EmbeddingStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class IncidentStatus(str, Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    IGNORED = "ignored"


class IncidentSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class NoteType(str, Enum):
    INVESTIGATION = "investigation"
    ROOT_CAUSE = "root_cause"
    FIX = "fix"
    FOLLOW_UP = "follow_up"
    GENERAL = "general"


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
