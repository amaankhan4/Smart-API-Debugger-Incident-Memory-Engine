import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Settings must exist before app.core.config is imported anywhere.
_UPLOAD_DIR = tempfile.mkdtemp(prefix="ime-uploads-")
os.environ.update(
    {
        "MONGODB_URI": "mongodb://localhost:27017",
        "MONGODB_DB": "incident_memory_test",
        "REDIS_URL": "redis://localhost:6379/15",
        "UPSTASH_VECTOR_REST_URL": "https://vector.test.invalid",
        "UPSTASH_VECTOR_REST_TOKEN": "test-token",
        "UPLOAD_DIR": _UPLOAD_DIR,
        "JWT_SECRET": "test-secret-not-used-in-production",
        "ENVIRONMENT": "test",
        "EVENT_BULK_BATCH": "50",
    }
)

import fakeredis.aioredis  # noqa: E402
import motor.motor_asyncio  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
import redis.asyncio as aioredis  # noqa: E402
from mongomock_motor import AsyncMongoMockClient  # noqa: E402

# Swap the drivers for in-memory doubles before any app module builds a client,
# so the suite runs with no external services.
motor.motor_asyncio.AsyncIOMotorClient = AsyncMongoMockClient  # type: ignore[misc]
aioredis.from_url = lambda *args, **kwargs: fakeredis.aioredis.FakeRedis(decode_responses=True)  # type: ignore[assignment]

from httpx import ASGITransport, AsyncClient  # noqa: E402
from upstash_vector.types import FetchResult, QueryResult  # noqa: E402

from app.core import mongo, vector_db  # noqa: E402
from app.main import app  # noqa: E402


class _FakeIndex:
    """In-memory stand-in for Upstash Vector, keyed by namespace."""

    def __init__(self) -> None:
        self.namespaces: dict[str, dict[str, tuple[list[float], dict]]] = {}

    async def upsert(self, vectors, namespace: str = ""):
        store = self.namespaces.setdefault(namespace, {})
        for vector_id, vector, metadata in vectors:
            store[str(vector_id)] = (list(vector), dict(metadata))
        return "Success"

    async def query(self, vector, top_k=10, filter="", namespace="", **_kwargs):
        store = self.namespaces.get(namespace, {})
        results = []
        for vector_id, (stored, metadata) in store.items():
            dot = sum(a * b for a, b in zip(vector, stored))
            results.append(QueryResult(id=vector_id, score=(1.0 + dot) / 2.0, metadata=metadata))
        results.sort(key=lambda item: item.score, reverse=True)
        return results[:top_k]

    async def fetch(self, ids=None, include_vectors=False, namespace="", **_kwargs):
        store = self.namespaces.get(namespace, {})
        found = []
        for vector_id in ids or []:
            entry = store.get(str(vector_id))
            if entry is None:
                found.append(None)
            else:
                found.append(
                    FetchResult(
                        id=str(vector_id),
                        vector=entry[0] if include_vectors else None,
                        metadata=entry[1],
                    )
                )
        return found

    async def info(self):
        raise AssertionError("info() should not be called in tests")


@pytest.fixture(autouse=True)
def fake_vector_index(monkeypatch):
    index = _FakeIndex()
    monkeypatch.setattr(vector_db, "get_index", lambda: index)
    return index


@pytest.fixture(autouse=True)
async def clean_database():
    for collection in (
        mongo.user_col,
        mongo.file_col,
        mongo.events_col,
        mongo.incidents_col,
        mongo.incident_notes_col,
        mongo.raw_log_chunks_col,
    ):
        await collection.delete_many({})
    yield


@pytest_asyncio.fixture
async def client():
    # ASGITransport skips lifespan, so no real index creation or connection setup runs.
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as async_client:
        yield async_client


@pytest_asyncio.fixture
async def make_user(client):
    async def _make_user(email: str = "engineer@example.com", password: str = "Str0ngPassw0rd!"):
        response = await client.post(
            "/api/v1/auth/register",
            json={"email": email, "name": email.split("@")[0], "password": password},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        return {
            "token": body["access_token"],
            "user": body["user"],
            "headers": {"Authorization": f"Bearer {body['access_token']}"},
        }

    return _make_user


@pytest.fixture
def sample_log() -> bytes:
    return (
        b"2024-05-01T10:00:00Z INFO auth-service User login succeeded trace_id=t-1\n"
        b"2024-05-01T10:00:01Z ERROR auth-service Database connection timeout trace_id=t-1\n"
        b"2024-05-01T10:00:02Z ERROR payment-service POST /api/charge 500 DatabaseTimeout occurred\n"
        b"2024-05-01T10:00:03Z WARN api-gateway Upstream latency high\n"
    )
