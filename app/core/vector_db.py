import chromadb
from chromadb.config import Settings

client = chromadb.HttpClient(
    host="localhost",
    port=8000
)

event_collection = client.get_or_create_collection("events")
incident_collection = client.get_or_create_collection("incidents")