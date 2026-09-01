from functools import lru_cache
from urllib.parse import quote, urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.schemas.enums import LEVEL_SEVERITY


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Incident Memory Engine"
    API_V1_PREFIX: str = "/api/v1"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False

    MONGODB_URI: str
    MONGODB_DB: str
    # Either REDIS_URL, or the Upstash REST pair below, must be provided.
    REDIS_URL: str = ""
    UPSTASH_REDIS_REST_URL: str = ""
    UPSTASH_REDIS_REST_TOKEN: str = ""
    UPSTASH_VECTOR_REST_URL: str = ""
    UPSTASH_VECTOR_REST_TOKEN: str = ""
    UPLOAD_DIR: str

    # Auth. JWT_SECRET must be overridden outside development.
    JWT_SECRET: str = "dev-insecure-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    # Ingestion
    READ_CHUNK_BYTES: int = 1024 * 1024
    EVENT_BULK_BATCH: int = 500
    MAX_UPLOAD_BYTES: int = 200 * 1024 * 1024
    ALLOWED_UPLOAD_EXTENSIONS: str = ".log,.txt,.json,.ndjson"

    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    EMBEDDING_BATCH_SIZE: int = 64
    EMBEDDING_QUEUE: str = "embeddings:queue"
    EMBEDDING_PROCESSING_QUEUE: str = "embeddings:processing"
    EMBEDDING_DEAD_LETTER_QUEUE: str = "embeddings:dead"
    EMBEDDING_MAX_RETRIES: int = 3
    # Each idle BLMOVE is a billed command on hosted Redis, so raise this to spend fewer.
    EMBEDDING_BLOCK_SECONDS: int = 2
    # Only events at or above this level are embedded. Quieter lines stay in Mongo and
    # remain keyword-searchable; this is the main lever on daily vector-upsert spend.
    EMBED_MIN_LEVEL: str = "WARN"

    # Upstash Vector free tier: queries and updates are metered separately per UTC day.
    VECTOR_DAILY_QUERY_LIMIT: int = 10_000
    VECTOR_DAILY_UPDATE_LIMIT: int = 10_000
    VECTOR_FETCH_BATCH: int = 1000

    # Clustering
    CLUSTER_INTERVAL_SECONDS: int = 900
    CLUSTER_EPS: float = 0.35
    CLUSTER_MIN_SAMPLES: int = 3
    CLUSTER_MAX_EVENTS: int = 20000
    INCIDENT_REPRESENTATIVE_LIMIT: int = 25

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @field_validator("ENVIRONMENT")
    @classmethod
    def _normalize_environment(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("EMBED_MIN_LEVEL")
    @classmethod
    def _validate_embed_level(cls, value: str) -> str:
        level = value.strip().upper()
        if level not in LEVEL_SEVERITY:
            raise ValueError(f"EMBED_MIN_LEVEL must be one of {sorted(LEVEL_SEVERITY)}")
        return level

    @property
    def embeddable_levels(self) -> set[str]:
        floor = LEVEL_SEVERITY[self.EMBED_MIN_LEVEL]
        return {level for level, rank in LEVEL_SEVERITY.items() if rank >= floor}

    @property
    def redis_url(self) -> str:
        """Upstash serves the same database over TCP; its REST token is the password."""
        if self.REDIS_URL:
            return self.REDIS_URL
        host = urlparse(self.UPSTASH_REDIS_REST_URL).hostname
        if host and self.UPSTASH_REDIS_REST_TOKEN:
            password = quote(self.UPSTASH_REDIS_REST_TOKEN, safe="")
            return f"rediss://default:{password}@{host}:6379"
        raise RuntimeError(
            "Redis is not configured: set REDIS_URL, or both UPSTASH_REDIS_REST_URL "
            "and UPSTASH_REDIS_REST_TOKEN"
        )

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {ext.strip().lower() for ext in self.ALLOWED_UPLOAD_EXTENSIONS.split(",") if ext.strip()}

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    resolved = Settings()  # type: ignore[call-arg]
    if resolved.is_production and resolved.JWT_SECRET == "dev-insecure-secret-change-me":
        raise RuntimeError("JWT_SECRET must be set to a strong value when ENVIRONMENT=production")
    return resolved


settings = get_settings()
