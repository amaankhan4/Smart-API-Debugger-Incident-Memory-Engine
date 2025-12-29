from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGODB_URI)
db = client[settings.MONGODB_DB]

raw_log_chunks_col = db.raw_logs
events_col = db.events
incidents_col = db.incidents
user_col = db.users
file_col = db.files
