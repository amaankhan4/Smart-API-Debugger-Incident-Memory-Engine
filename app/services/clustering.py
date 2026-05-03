from collections import defaultdict

import numpy as np
from bson import ObjectId
from sklearn.cluster import DBSCAN

from app.core.mongo import events_col, incidents_col


async def run_incident_clustering(eps: float = 0.35, min_samples: int = 3) -> dict:
    docs = await events_col.find({"embedding_id": {"$exists": True, "$ne": None}}).to_list(length=50000)
    if len(docs) < min_samples:
        return {"clusters_created": 0, "events_clustered": 0, "reason": "not_enough_events"}

    vectors: list[list[float]] = []
    mapped_docs: list[dict] = []
    for doc in docs:
        emb = doc.get("embedding")
        if isinstance(emb, list) and emb:
            vectors.append(emb)
            mapped_docs.append(doc)

    if len(vectors) < min_samples:
        return {"clusters_created": 0, "events_clustered": 0, "reason": "not_enough_embeddings"}

    clustering = DBSCAN(eps=eps, min_samples=min_samples, metric="cosine")
    labels = clustering.fit_predict(np.array(vectors))

    grouped = defaultdict(list)
    for i, label in enumerate(labels):
        if label == -1:
            continue
        grouped[int(label)].append(mapped_docs[i])

    created = 0
    clustered_events = 0
    for label, label_docs in grouped.items():
        event_ids = [str(doc["_id"]) for doc in label_docs]
        file_id = label_docs[0].get("file_id")
        cluster_key = f"{file_id}:{label}:{len(event_ids)}"

        existing = await incidents_col.find_one({"cluster_key": cluster_key})
        if existing:
            continue

        summary = "\n".join(doc.get("message", "") for doc in label_docs[:5])
        incident = {
            "title": f"Incident cluster {label}",
            "summary": summary,
            "file_id": file_id,
            "cluster_key": cluster_key,
            "event_ids": event_ids,
            "event_count": len(event_ids),
        }
        incident_result = await incidents_col.insert_one(incident)

        await events_col.update_many(
            {"_id": {"$in": [ObjectId(eid) for eid in event_ids]}},
            {"$set": {"incident_id": str(incident_result.inserted_id)}},
        )
        created += 1
        clustered_events += len(event_ids)

    return {"clusters_created": created, "events_clustered": clustered_events}
