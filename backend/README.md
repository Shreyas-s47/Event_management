# Member 4 — Python backend

Implemented first slice: FastAPI application, PostgreSQL migrations, identity/session APIs, event membership/lifecycle, agenda, budget allocations, expenses, and an immutable expense settlement snapshot.

## Local setup (PowerShell)

Requires Python 3.12+, uv, and Docker Desktop with Linux containers. Run commands from the repository root unless noted.

```powershell
Copy-Item backend/.env.example backend/.env
# Generate a secret and paste it into JWT_SECRET in backend/.env:
python -c "import secrets; print(secrets.token_urlsafe(48))"
docker compose --env-file backend/.env -f infra/compose.yaml up -d db
Set-Location backend
uv sync --frozen
uv run alembic upgrade head
uv run python -m app.cli admin@example.com --name "Operations Admin" --role admin
uv run uvicorn app.main:app --reload
```

The CLI prompts for the password; no default privileged account is created. Public registration creates clients only. The admin can provision employees through POST /api/v1/users or the CLI. Register a client to create an event, then use an admin session to review it.

Interactive API docs: http://localhost:8000/docs. Liveness: /health/live. Database connectivity: /health/ready. Readiness does not check migration revision; migrations must be run separately before serving traffic.

For a containerized API, run from the repository root after setting the secret:

```powershell
docker compose --env-file backend/.env -f infra/compose.yaml build api
docker compose --env-file backend/.env -f infra/compose.yaml run --rm api .venv/bin/alembic upgrade head
docker compose --env-file backend/.env -f infra/compose.yaml run --rm api .venv/bin/python -m app.cli admin@example.com --name "Operations Admin" --role admin
docker compose --env-file backend/.env -f infra/compose.yaml up -d api
```

Compose exposes the development database only on 127.0.0.1:55432 and API on 127.0.0.1:8000. The development password is not a production credential. Backups and production deployment remain a later milestone.

## Validation

From backend/ with PostgreSQL running:

```powershell
uv run ruff check .
uv run ruff format --check .
uv run alembic check
uv run pytest -q
```

Tests create randomly named isolated PostgreSQL schemas, apply actual migrations, and drop only those schemas. They do not truncate the application schema. Set TEST_DATABASE_URL to a separate PostgreSQL database if desired; the test account must have CREATE SCHEMA permission. Tests require real PostgreSQL and intentionally do not substitute SQLite for transaction/concurrency behavior.

Dependency versions are locked in uv.lock. Regenerate the committed frontend contract after API changes:

```powershell
uv run python -m app.export_openapi
```

## Integration points for Members 5 and 6

- DB dependency: app.core.dependencies.DB. It commits before response transmission, and rolls back failed requests.
- Authentication: CurrentUser, Admin from app.core.dependencies. These check the user and database session on every request, so logout/revocation also invalidates issued access tokens.
- Event permissions: await app.modules.events.service.require_event(db, user, event_id, manage=False, lock=False). Unauthorized event access is concealed as 404. Use manage=True for admin/client-owner operations. Use lock=True for mutations that must serialize with event closing or settlement, and call editable(event) for operations prohibited on closed events.
- EventMembership is the access boundary. Member 5's workforce assignments should use this membership rather than inventing separate event authorization. Removing access and changing workforce assignments must be coordinated in that module.
- Audit: app.modules.events.service.audit adds a record in the current transaction. Do not place secrets or personal guest details in audit payloads.
- Idempotency: await begin_operation(db, actor_id, scope, key, payload). If replay is false, perform the mutation and set operation.response to JSON-safe response data in the same transaction. If replay is true, return the stored response. Authorize event access before reading a stored response.
- Register new routers in app/main.py, and import new models in app/db/models.py:load_models. Member 4 coordinates migrations to preserve one head.
- Keep HTTP handlers thin; module services own rules and transactions use the injected session. Do not independently commit domain changes in feature services.

See ../docs/contracts/MEMBER_4_API.md and ../docs/contracts/member4.openapi.json for frontend handoff.

## Scope still to implement

- Payment collection, deposit accounting, claim adjustments, settlement amendments, and client financial sign-off. Current settlement is an approved-expense snapshot, not a payment ledger or an invoice.
- Edit/delete agenda and budget lines, authenticated account/password administration, email verification and password recovery.
- Shared fixtures across all six modules, durable notification/outbox delivery (Member 6), and production backup/restore automation.
- Production perimeter controls, shared login/registration throttling, capacity testing, and monitoring integration. This is a development foundation, not a public production deployment.
