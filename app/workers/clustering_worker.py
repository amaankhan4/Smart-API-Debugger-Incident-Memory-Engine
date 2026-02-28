import asyncio
import os

from app.services.clustering import run_incident_clustering

INTERVAL_SECONDS = int(os.getenv("CLUSTER_INTERVAL_SECONDS", "300"))


async def run_worker():
    while True:
        result = await run_incident_clustering()
        print(f"clustering cycle: {result}")
        await asyncio.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_worker())
