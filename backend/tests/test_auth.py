from datetime import timedelta
from uuid import UUID

import jwt
from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import utcnow
from app.modules.auth.models import User
from tests.conftest import ORIGIN, PASSWORD


async def test_registration_cannot_escalate_role_and_password_is_hashed(client, database):
    data = {"full_name": "Client", "email": "New@EXAMPLE.com", "password": PASSWORD}
    escalated = await client.post("/api/v1/auth/register", json={**data, "role": "admin"})
    assert escalated.status_code == 422
    response = await client.post("/api/v1/auth/register", json=data)
    assert response.status_code == 201
    assert response.json()["role"] == "client"
    assert "password" not in response.text
    async with database() as db:
        user = await db.scalar(select(User).where(User.email == "new@example.com"))
        assert user.password_hash != PASSWORD
    duplicate = await client.post("/api/v1/auth/register", json=data)
    assert duplicate.status_code == 409


async def test_login_refresh_logout_and_replay_revoke_access(client, accounts):
    data = {"email": "client@example.com", "password": PASSWORD}
    assert (await client.post("/api/v1/auth/login", json=data)).status_code == 403
    invalid = await client.post(
        "/api/v1/auth/login",
        json={**data, "password": "wrong"},
        headers=ORIGIN,
    )
    assert invalid.status_code == 401
    login = await client.post("/api/v1/auth/login", json=data, headers=ORIGIN)
    assert login.status_code == 200, login.text
    cookie = login.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie
    assert "Path=/api/v1/auth" in cookie
    old = client.cookies.get("refresh_token")
    refreshed = await client.post("/api/v1/auth/refresh", headers=ORIGIN)
    assert refreshed.status_code == 200
    assert client.cookies.get("refresh_token") != old
    access = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    assert (await client.get("/api/v1/auth/me", headers=access)).status_code == 200
    client.cookies.clear()
    client.cookies.set("refresh_token", old, domain="testserver.local", path="/api/v1/auth")
    replay = await client.post("/api/v1/auth/refresh", headers=ORIGIN)
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "refresh_reused"
    assert (await client.get("/api/v1/auth/me", headers=access)).status_code == 401
    client.cookies.clear()
    login = await client.post("/api/v1/auth/login", json=data, headers=ORIGIN)
    access = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (await client.post("/api/v1/auth/logout", headers=ORIGIN)).status_code == 204
    assert (await client.get("/api/v1/auth/me", headers=access)).status_code == 401


async def test_token_signature_expiry_and_inactive_user(client, accounts, database):
    assert (await client.get("/api/v1/auth/me")).status_code == 401
    token = accounts["client"]["headers"]["Authorization"].split()[1]
    claims = jwt.decode(
        token, get_settings().jwt_secret, algorithms=["HS256"], audience="event-api"
    )
    claims["exp"] = utcnow() - timedelta(seconds=1)
    expired = jwt.encode(claims, get_settings().jwt_secret, algorithm="HS256")
    for invalid in (expired, "malformed.token.value"):
        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": f"Bearer {invalid}"}
        )
        assert response.status_code == 401
    async with database.begin() as db:
        user = await db.get(User, UUID(accounts["client"]["id"]))
        user.is_active = False
    assert (
        await client.get("/api/v1/auth/me", headers=accounts["client"]["headers"])
    ).status_code == 401


async def test_user_provisioning_is_admin_only(client, accounts):
    data = {
        "full_name": "New staff",
        "email": "new-staff@example.com",
        "password": PASSWORD,
        "role": "employee",
    }
    assert (
        await client.post("/api/v1/users", json=data, headers=accounts["client"]["headers"])
    ).status_code == 403
    created = await client.post("/api/v1/users", json=data, headers=accounts["admin"]["headers"])
    assert created.status_code == 201
    assert created.json()["role"] == "employee"


async def test_csrf_and_error_response_redact_input(client):
    response = await client.post(
        "/api/v1/auth/login",
        headers={"Origin": "https://evil.example", "X-CSRF-Protection": "1"},
        json={"email": "a@example.com", "password": PASSWORD},
    )
    assert response.status_code == 403
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "bad-email", "password": "secret"},
    )
    assert response.status_code == 422
    assert "secret" not in response.text
    assert response.headers["x-request-id"] == response.json()["request_id"]
