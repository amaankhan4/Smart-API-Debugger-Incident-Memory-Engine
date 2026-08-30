from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RawLogChunkCreate(BaseModel):
    file_id: str
    user_id: str
    sequence_number: int
    content: str
    start_line_no: int
    end_line_no: int

class RawLogChunkDB(RawLogChunkCreate):
    id: Optional[str]
    created_at: datetime
