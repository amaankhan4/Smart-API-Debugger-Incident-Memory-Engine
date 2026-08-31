from fastapi import APIRouter, HTTPException, status
from pymongo.errors import DuplicateKeyError

from app.api.deps import CurrentUser
from app.core.security import create_access_token, hash_password, verify_password
from app.repositories import users as users_repo
from app.schemas.auth import TokenResponse, UserLogin, UserOut, UserRegister

router = APIRouter()


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegister) -> TokenResponse:
    if await users_repo.get_user_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists"
        )

    try:
        user = await users_repo.create_user(
            email=payload.email, name=payload.name, password_hash=hash_password(payload.password)
        )
    except DuplicateKeyError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists"
        ) from None

    user_out = users_repo.to_user_out(user)
    token, expires_in = create_access_token(user_out.id, {"email": user_out.email})
    return TokenResponse(access_token=token, expires_in=expires_in, user=user_out)


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin) -> TokenResponse:
    user = await users_repo.get_user_by_email(payload.email)
    # Identical response for unknown email and wrong password so accounts cannot be enumerated.
    if user is None or not verify_password(payload.password, user.get("password_hash", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password"
        )

    user_out = users_repo.to_user_out(user)
    token, expires_in = create_access_token(user_out.id, {"email": user_out.email})
    return TokenResponse(access_token=token, expires_in=expires_in, user=user_out)


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUser) -> UserOut:
    user = await users_repo.get_user_by_id(current_user.id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return users_repo.to_user_out(user)
