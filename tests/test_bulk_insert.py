"""Partial bulk-write handling during ingestion."""

from bson import ObjectId
from pymongo.errors import BulkWriteError

from app.repositories import events as events_repo


class _FakeCollection:
    """Mimics insert_many(ordered=False): assigns _id, then reports per-index failures."""

    def __init__(self, failing_indexes: set[int]) -> None:
        self.failing_indexes = failing_indexes

    async def insert_many(self, docs, ordered=True):
        for doc in docs:
            doc.setdefault("_id", ObjectId())
        raise BulkWriteError(
            {
                "writeErrors": [
                    {
                        "index": index,
                        "code": 17261,
                        "errmsg": "found language override field in document with non-string type",
                    }
                    for index in sorted(self.failing_indexes)
                ],
                "nInserted": len(docs) - len(self.failing_indexes),
            }
        )


async def test_rejected_documents_do_not_void_the_whole_batch(monkeypatch):
    monkeypatch.setattr(events_repo, "events_col", _FakeCollection({1, 3}))
    docs = [{"line_no": n} for n in range(5)]

    inserted = await events_repo.bulk_insert_events(docs)

    assert len(inserted) == 3
    assert inserted == [str(docs[0]["_id"]), str(docs[2]["_id"]), str(docs[4]["_id"])]


async def test_write_errors_are_logged_as_a_digest_not_a_document_dump(monkeypatch, caplog):
    monkeypatch.setattr(events_repo, "events_col", _FakeCollection({0, 1}))

    with caplog.at_level("ERROR"):
        assert await events_repo.bulk_insert_events([{"line_no": 0}, {"line_no": 1}]) == []

    record = next(r for r in caplog.records if r.message == "event bulk insert rejected documents")
    assert record.attempted == 2
    assert record.rejected == 2
    # One digest entry, not one line per rejected document.
    assert record.reasons == [
        {
            "code": 17261,
            "errmsg": "found language override field in document with non-string type",
            "count": 2,
        }
    ]
