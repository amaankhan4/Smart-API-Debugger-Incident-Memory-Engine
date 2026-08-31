from typing import Any

from app.core.mongo import user_col
from app.schemas.auth import UserOut
from app.schemas.enums import Role
from app.utils.datetime_utils import utc_now
from app.utils.serialization import to_object_id


async def create_user(email: str, name: str, password_hash: str) -> dict[str, Any]:
    doc = {
        "email": email.lower(),
        "name": name,
        "password_hash": password_hash,
        "role": Role.USER.value,
        "created_at": utc_now(),
    }
    result = await user_col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def get_user_by_email(email: str) -> dict[str, Any] | None:
    return await user_col.find_one({"email": email.lower()})


async def get_user_by_id(user_id: str) -> dict[str, Any] | None:
    object_id = to_object_id(user_id)
    if object_id is None:
        return None
    return await user_col.find_one({"_id": object_id})


def to_user_out(doc: dict[str, Any]) -> UserOut:
    return UserOut(
        id=str(doc["_id"]),
        email=doc["email"],
        name=doc.get("name", ""),
        role=Role(doc.get("role", Role.USER.value)),
        created_at=doc.get("created_at"),
    )
