from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import TokenError, decode_access_token
from app.repositories import users as users_repo
from app.schemas.auth import AuthenticatedUser
from app.schemas.enums import Role

_bearer = HTTPBearer(auto_error=False)

_UNAUTHENTICATED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    if credentials is None or not credentials.credentials:
        raise _UNAUTHENTICATED

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # The identity is always re-read from the database, never taken from the request body.
    user = await users_repo.get_user_by_id(str(payload["sub"]))
    if user is None:
        raise _UNAUTHENTICATED

    return AuthenticatedUser(
        id=str(user["_id"]),
        email=user["email"],
        name=user.get("name", ""),
        role=Role(user.get("role", Role.USER.value)),
    )


CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
