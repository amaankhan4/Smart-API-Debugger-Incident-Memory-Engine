import time
from bson import ObjectId
from fastapi import APIRouter

from app.core.redis import redis_client
from app.core.mongo import events_col
from app.core.vector_db import event_collection
from app.services.embedding import generate_embedding
import asyncio

QUEUE_NAME = "embeddings_queue"


async def run_worker():
    print("🔁 Embedding worker started")

    while True:
        print("⏳ Waiting for events to embed...")
        # print(f"Redis connection info: {redis_client.connection_pool.connection_kwargs}")
        _, event_id = redis_client.brpop(QUEUE_NAME)
        
        event = await events_col.find_one({"_id": ObjectId(event_id)})

        print(f"Event data: {event}")

        if not event:
            continue

        text = f"""
        {event.get('service')}
        {event.get('level')}
        {event.get('message')}
        """
        
        embedding = generate_embedding(text)
        vector_id = f"event_{event_id}"

        event_collection.add(
            ids=[vector_id],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{
                "event_id": event_id,
                "file_id": event.get("file_id"),
                "level": event.get("level")
            }]
        )

        print(f"💾 Stored embedding for event {event_id} with vector ID {vector_id}")

        events_col.update_one(
            {"_id": ObjectId(event_id)},
            {"$set": {"embedding_id": vector_id}}
        )

        print(f"✅ Embedded event {event_id}")

        time.sleep(0.1)  # prevent CPU spin

if __name__ == "__main__":
    asyncio.run(run_worker())


# To run the worker, execute this file directly in cmd - python -m app.workers.embedding_workers
