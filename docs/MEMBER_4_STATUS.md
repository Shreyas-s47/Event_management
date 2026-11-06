# Member 4 implementation status

## Implemented and ready for local integration

- Python/FastAPI modular application, configuration, request IDs, structured request logs, standard errors, CORS, liveness and DB connectivity probes.
- Async SQLAlchemy/PostgreSQL and initial Alembic migration. Shared session/auth/admin/event permission dependencies are documented for Members 5/6.
- Client-only public registration, admin user provisioning, Argon2 password hashes, short-lived JWT access tokens, hashed rotating refresh tokens, session revocation/replay detection, and cookie-origin protection.
- Client-owned events, server-side role and membership checks, scoped lists, admin membership management, explicit event state transitions, draft editing, agenda creation/listing, and venue map metadata.
- Transactional budget allocations, expense submission/review, idempotent finance creates, audit history, live finance summary, and finalized approved-expense snapshots.
- PostgreSQL integration/concurrency tests, locked Python dependencies, Docker development services, CI checks, run guide, and exported OpenAPI contract.

## Next Member 4 slices

1. Coordinate contract review with frontend members and register Members 5/6 routers/models as their work lands.
2. Add agenda/budget editing, account/password administration, verified-email/recovery workflows, and shared auth throttling.
3. Add financial adjustments/payment records and claim integration before treating a settlement as a final client balance. Add client sign-off and amendment rules.
4. Add complete shared demo data after guest/workforce models exist, production deployment settings, backup/restore automation, operational monitoring, and agreed capacity checks.

This is the first working backend slice. It does not complete all Member 4 release milestones or implement other members' domain features.

## Validation performed

- 14 PostgreSQL API/integration tests passed, covering session replay/logout, roles and event isolation, event transitions, draft invariants, concurrent allocations, idempotent expenses, and settlement rules.
- Focused user-provisioning test passed after the final audit addition.
- Ruff lint and formatting checks passed; Alembic reported no model/migration drift.
- Linux Docker image built successfully; running API returned successful liveness and database-readiness responses.
- GitHub Actions workflow is included; remote CI results must be checked after pushing.
