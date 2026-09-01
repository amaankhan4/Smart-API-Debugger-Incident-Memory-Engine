from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser
from app.repositories import events as events_repo
from app.repositories import incidents as incidents_repo
from app.repositories import notes as notes_repo
from app.schemas.common import MessageResponse, Page
from app.schemas.enums import IncidentSeverity, IncidentStatus
from app.schemas.events import EventOut
from app.schemas.incident import (
    ClusterRunResponse,
    IncidentDetailResponse,
    IncidentOut,
    IncidentStatusUpdate,
    NoteCreate,
    NoteOut,
    SimilarIncident,
)
from app.services.clustering import find_similar_incidents, run_incident_clustering
from app.utils.serialization import serialize_docs

router = APIRouter()


def _to_incident_out(doc: dict) -> IncidentOut:
    return IncidentOut(**serialize_docs([doc])[0])


async def _load_incident(incident_id: str, user_id: str) -> dict:
    incident = await incidents_repo.get_incident(incident_id, user_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return incident


async def _timeline(user_id: str, incident_id: str) -> list[dict]:
    pipeline = [
        {"$match": {"user_id": user_id, "incident_id": incident_id}},
        {"$group": {"_id": {"$dateTrunc": {"date": "$timestamp", "unit": "hour"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    rows = await events_repo.aggregate(pipeline, length=500)
    return [{"bucket": row["_id"], "count": row["count"]} for row in rows if row.get("_id")]


@router.post("/cluster", response_model=ClusterRunResponse)
async def cluster_incidents(current_user: CurrentUser) -> ClusterRunResponse:
    result = await run_incident_clustering(current_user.id)
    return ClusterRunResponse(**result)


@router.get("", response_model=Page[IncidentOut])
async def list_incidents(
    current_user: CurrentUser,
    incident_status: IncidentStatus | None = Query(None, alias="status"),
    severity: IncidentSeverity | None = None,
    service: str | None = None,
    search: str | None = Query(None, max_length=200),
    sort: str = Query("last_seen", pattern="^(last_seen|first_seen|event_count|created_at|severity)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[IncidentOut]:
    docs, total = await incidents_repo.list_incidents(
        current_user.id,
        status=incident_status.value if incident_status else None,
        severity=severity.value if severity else None,
        service=service,
        search=search,
        limit=limit,
        offset=offset,
        sort_field=sort,
        sort_dir=-1 if order == "desc" else 1,
    )
    return Page[IncidentOut].build([_to_incident_out(doc) for doc in docs], total, limit, offset)


@router.get("/{incident_id}", response_model=IncidentDetailResponse)
async def incident_detail(incident_id: str, current_user: CurrentUser) -> IncidentDetailResponse:
    incident = await _load_incident(incident_id, current_user.id)

    representative_docs = await events_repo.get_events_by_ids(
        incident.get("representative_event_ids", []), current_user.id
    )
    similar = await find_similar_incidents(current_user.id, incident)

    return IncidentDetailResponse(
        incident=_to_incident_out(incident),
        representative_events=[EventOut(**doc) for doc in serialize_docs(representative_docs)],
        timeline=await _timeline(current_user.id, incident_id),
        similar_incidents=[
            SimilarIncident(incident=_to_incident_out(match["incident"]), score=match["score"])
            for match in similar
        ],
    )


@router.get("/{incident_id}/events", response_model=Page[EventOut])
async def incident_events(
    incident_id: str,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[EventOut]:
    await _load_incident(incident_id, current_user.id)
    query = events_repo.build_event_query(current_user.id, incident_id=incident_id)
    docs, total = await events_repo.list_events(query, limit=limit, offset=offset)
    return Page[EventOut].build(
        [EventOut(**doc) for doc in serialize_docs(docs)], total, limit, offset
    )


@router.patch("/{incident_id}/status", response_model=IncidentOut)
async def update_incident_status(
    incident_id: str, payload: IncidentStatusUpdate, current_user: CurrentUser
) -> IncidentOut:
    updated = await incidents_repo.update_status(
        incident_id, current_user.id, payload.status, payload.severity
    )
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    return _to_incident_out(updated)


@router.get("/{incident_id}/notes", response_model=Page[NoteOut])
async def list_notes(
    incident_id: str,
    current_user: CurrentUser,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> Page[NoteOut]:
    await _load_incident(incident_id, current_user.id)
    docs, total = await notes_repo.list_notes(
        incident_id, current_user.id, limit=limit, offset=offset
    )
    return Page[NoteOut].build(
        [NoteOut(**doc) for doc in serialize_docs(docs)], total, limit, offset
    )


@router.post("/{incident_id}/notes", response_model=NoteOut, status_code=status.HTTP_201_CREATED)
async def add_incident_note(
    incident_id: str, payload: NoteCreate, current_user: CurrentUser
) -> NoteOut:
    await _load_incident(incident_id, current_user.id)

    if payload.event_id:
        referenced = await events_repo.get_event(payload.event_id, current_user.id)
        if referenced is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Referenced event not found"
            )

    note = await notes_repo.create_note(
        incident_id=incident_id,
        user_id=current_user.id,
        author_name=current_user.name,
        note=payload.note,
        note_type=payload.type,
        event_id=payload.event_id,
    )
    return NoteOut(**serialize_docs([note])[0])


@router.delete("/{incident_id}/notes/{note_id}", response_model=MessageResponse)
async def delete_incident_note(
    incident_id: str, note_id: str, current_user: CurrentUser
) -> MessageResponse:
    await _load_incident(incident_id, current_user.id)
    if not await notes_repo.delete_note(note_id, current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return MessageResponse(message="Note deleted")

