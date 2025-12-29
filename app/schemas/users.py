from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"

class UserCreate(BaseModel):
    email: str 
    name: str
    role: Role

class UserDB(UserCreate):
    id: Optional[str]
    created_at: datetime


# Create index on email field for uniqueness
# user_col.create_index(
#     [("email", 1)],
#     unique=True
# )




