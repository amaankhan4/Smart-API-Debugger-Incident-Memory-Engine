import pytest

from app.core.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("Str0ngPassw0rd!")
    second = hash_password("Str0ngPassw0rd!")

    assert first != second  # unique salt per hash
    assert verify_password("Str0ngPassw0rd!", first)
    assert not verify_password("wrong-password", first)


def test_verify_password_rejects_malformed_hash():
    assert not verify_password("anything", "")
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_access_token_roundtrip():
    token, expires_in = create_access_token("user-123", {"email": "a@b.com"})
    payload = decode_access_token(token)

    assert payload["sub"] == "user-123"
    assert payload["email"] == "a@b.com"
    assert expires_in > 0


def test_tampered_token_is_rejected():
    token, _ = create_access_token("user-123")
    with pytest.raises(TokenError):
        decode_access_token(token + "tampered")


def test_garbage_token_is_rejected():
    with pytest.raises(TokenError):
        decode_access_token("not.a.jwt")


async def test_register_returns_token_and_user(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "New.User@Example.com", "name": "New User", "password": "Str0ngPassw0rd!"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == "new.user@example.com"
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]


async def test_duplicate_registration_is_rejected(client, make_user):
    await make_user("dup@example.com")
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "dup@example.com", "name": "Dup", "password": "Str0ngPassw0rd!"},
    )
    assert response.status_code == 409


async def test_weak_password_is_rejected(client):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "name": "Weak", "password": "short"},
    )
    assert response.status_code == 422


async def test_login_succeeds_and_wrong_password_fails(client, make_user):
    await make_user("login@example.com", "Str0ngPassw0rd!")

    ok = await client.post(
        "/api/v1/auth/login", json={"email": "login@example.com", "password": "Str0ngPassw0rd!"}
    )
    assert ok.status_code == 200

    bad = await client.post(
        "/api/v1/auth/login", json={"email": "login@example.com", "password": "nope"}
    )
    assert bad.status_code == 401


async def test_unknown_email_and_wrong_password_are_indistinguishable(client, make_user):
    await make_user("known@example.com", "Str0ngPassw0rd!")

    unknown = await client.post(
        "/api/v1/auth/login", json={"email": "ghost@example.com", "password": "Str0ngPassw0rd!"}
    )
    wrong = await client.post(
        "/api/v1/auth/login", json={"email": "known@example.com", "password": "incorrect"}
    )

    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


async def test_me_requires_authentication(client):
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    assert (
        await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nonsense"})
    ).status_code == 401


async def test_me_returns_current_identity(client, make_user):
    user = await make_user("me@example.com")
    response = await client.get("/api/v1/auth/me", headers=user["headers"])

    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/files",
        "/api/v1/events",
        "/api/v1/incidents",
        "/api/v1/analytics",
        "/api/v1/search?q=test",
    ],
)
async def test_all_data_endpoints_require_authentication(client, path):
    assert (await client.get(path)).status_code == 401
