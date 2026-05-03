import asyncio
from bson import ObjectId

from app.core.mongo import events_col
from app.core.redis import redis_client
from app.core.vector_db import event_collection
from app.services.embedding import generate_embedding

QUEUE_NAME = "embeddings_queue"


async def run_worker():
    print("Embedding worker started")

    while True:
        _, event_id = redis_client.brpop(QUEUE_NAME)
        event = await events_col.find_one({"_id": ObjectId(event_id)})
        if not event:
            continue

        text = f"{event.get('service', '')} {event.get('level', '')} {event.get('message', '')}".strip()
        embedding = generate_embedding(text)
        vector_id = f"event_{event_id}"

        event_collection.upsert(
            ids=[vector_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[
                {
                    "event_id": event_id,
                    "file_id": event.get("file_id"),
                    "level": event.get("level"),
                    "trace_id": event.get("trace_id"),
                }
            ],
        )

        await events_col.update_one(
            {"_id": ObjectId(event_id)},
            {"$set": {"embedding_id": vector_id, "embedding": embedding}},
        )

        await asyncio.sleep(0.01)


if __name__ == "__main__":
    asyncio.run(run_worker())
