from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

client = AsyncIOMotorClient(settings.MONGODB_URI)
db = client[settings.MONGODB_DB]

raw_logs_col = db.raw_logs
events_col = db.events
incidents_col = db.incidents
