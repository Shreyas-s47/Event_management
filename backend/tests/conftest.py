import os
import uuid

import pytest
from alembic import command
from alembic.config import Config
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

os.environ.setdefault("JWT_SECRET", "test-secret-used-only-in-isolated-tests-123456")
os.environ["COOKIE_SECURE"] = "false"
os.environ["ENVIRONMENT"] = "test"

from app.core.config import get_settings  # noqa: E402
from app.core.security import password_hasher  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.modules.auth.models import User  # noqa: E402
from app.modules.auth.service import issue_tokens  # noqa: E402

PASSWORD = "Test-only-password-123!"
PASSWORD_HASH = password_hasher.hash(PASSWORD)
ORIGIN = {"Origin": "http://localhost:5173", "X-CSRF-Protection": "1"}


@pytest.fixture
async def database():
    """Each test migrates a new isolated schema; never truncates existing application data."""
    url = os.environ.get("TEST_DATABASE_URL", get_settings().database_url)
    schema = f"test_{uuid.uuid4().hex}"
    control = create_async_engine(url, poolclass=NullPool)
    async with control.begin() as connection:
        await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    test_engine = create_async_engine(
        url,
        connect_args={"server_settings": {"search_path": schema}},
    )
    try:
        async with test_engine.begin() as connection:

            def migrate(sync_connection):
                config = Config("alembic.ini")
                config.attributes["connection"] = sync_connection
                command.upgrade(config, "head")

            await connection.run_sync(migrate)
        yield async_sessionmaker(test_engine, expire_on_commit=False)
    finally:
        await test_engine.dispose()
        async with control.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await control.dispose()


@pytest.fixture
async def client(database):
    async def override_db():
        async with database.begin() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def accounts(database):
    results = {}
    async with database.begin() as db:
        for name, role in [
            ("admin", "admin"),
            ("client", "client"),
            ("other", "client"),
            ("staff", "employee"),
            ("audience", "audience"),
        ]:
            user = User(
                full_name=name,
                email=f"{name}@example.com",
                role=role,
                password_hash=PASSWORD_HASH,
            )
            db.add(user)
            await db.flush()
            token, _, _ = await issue_tokens(db, user)
            results[name] = {
                "id": str(user.id),
                "headers": {"Authorization": f"Bearer {token.access_token}"},
            }
    return results


@pytest.fixture
def event_payload():
    return {
        "title": "Team event",
        "event_type": "conference",
        "venue": "Hall A",
        "starts_at": "2027-01-02T09:00:00+05:30",
        "ends_at": "2027-01-02T18:00:00+05:30",
        "total_budget": "1000.00",
        "currency": "INR",
    }


@pytest.fixture
async def event(client, accounts, event_payload):
    response = await client.post(
        "/api/v1/events",
        json=event_payload,
        headers=accounts["client"]["headers"],
    )
    assert response.status_code == 201, response.text
    return response.json()
