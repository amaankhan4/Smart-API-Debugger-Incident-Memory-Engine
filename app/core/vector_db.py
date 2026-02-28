import chromadb

from app.core.config import settings

client = chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)

event_collection = client.get_or_create_collection("events")
incident_collection = client.get_or_create_collection("incidents")
