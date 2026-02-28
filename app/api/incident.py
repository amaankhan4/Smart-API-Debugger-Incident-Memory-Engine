from bson import ObjectId
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.core.mongo import events_col, incident_notes_col, incidents_col
from app.services.clustering import run_incident_clustering

router = APIRouter()


def _serialize(doc: dict) -> dict:
    doc["id"] = str(doc.pop("_id"))
    return doc


@router.post("/cluster")
async def cluster_incidents():
    return await run_incident_clustering()


@router.get("/")
async def list_incidents(limit: int = 100):
    docs = await incidents_col.find({}).sort("created_at", -1).limit(limit).to_list(length=limit)
    return {"items": [_serialize(doc) for doc in docs], "count": len(docs)}


@router.get("/{incident_id}")
async def incident_detail(incident_id: str):
    incident = await incidents_col.find_one({"_id": ObjectId(incident_id)})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    event_ids = incident.get("event_ids", [])
    object_ids = [ObjectId(eid) for eid in event_ids if ObjectId.is_valid(eid)]
    events = await events_col.find({"_id": {"$in": object_ids}}).sort("line_no", 1).to_list(length=1000)

    return {"incident": _serialize(incident), "events": [_serialize(event) for event in events]}

@router.post("/{incident_id}/notes")
async def add_incident_note(incident_id: str, note: str):
    incident = await incidents_col.find_one({"_id": ObjectId(incident_id)})
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    result = await incident_notes_col.insert_one(
        {
            "incident_id": incident_id,
            "note": note,
            "created_at": datetime.utcnow(),
        }
    )
    return {"note_id": str(result.inserted_id), "incident_id": incident_id}
