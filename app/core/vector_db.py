import chromadb
from chromadb.config import Settings

client = chromadb.Client(
    Settings(
        chroma_api_impl="rest",
        chroma_server_host="localhost",
        chroma_server_http_port=8000
    )
)

event_collection = client.get_or_create_collection("events")
incident_collection = client.get_or_create_collection("incidents")