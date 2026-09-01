"""Embedding provider abstraction.

The model is loaded lazily so importing this module (which the API does, transitively)
never pays the model-load cost. Only the worker actually encodes text.
"""

from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Sequence

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = settings.EMBEDDING_MODEL) -> None:
        self.model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            logger.info("loading embedding model", extra={"model": self.model_name})
            self._model = SentenceTransformer(self.model_name)
        return self._model

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIM

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._load()
        # Normalised vectors keep cosine distance in [0, 2], which the search layer
        # relies on when converting distance into a 0-1 similarity score.
        vectors = model.encode(
            list(texts),
            batch_size=settings.EMBEDDING_BATCH_SIZE,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    return SentenceTransformerProvider()


def build_embedding_text(event: dict) -> str:
    """Compact, field-aware representation so similar failures embed close together."""
    parts = [
        event.get("service") or "unknown",
        event.get("level") or "INFO",
        event.get("exception") or "",
        f"{event.get('http_method') or ''} {event.get('path') or ''}".strip(),
        str(event.get("status_code") or ""),
        event.get("error_category") or "",
        event.get("message") or "",
    ]
    return " | ".join(part for part in parts if part).strip()


def generate_embedding(text: str) -> list[float]:
    return get_embedding_provider().embed_one(text)

