# Six-member parallel implementation plan

## Confirmed direction

- Team: six people, three frontend and three backend. Replace member numbers with names when assigned.
- Frontend: React.js with JavaScript/JSX, Vite, React Router, Tailwind CSS.
- Backend: Python with FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- Supporting services: Redis, Python Celery workers, private S3-compatible storage.
- One shared frontend and one modular backend. Each person owns feature folders, contracts, and validation for their work.
- This file assigns work; it does not launch agents or implement application code. The overall architecture and scope remain in IMPLEMENTATION_PLAN.md.

Current progress: Member 4's first backend slice is implemented. See [status and remaining work](docs/MEMBER_4_STATUS.md), [run guide](backend/README.md), and [API handoff](docs/contracts/MEMBER_4_API.md).

## Member assignments

| Member | Primary ownership | Screens or backend modules | First independent deliverable |
| --- | --- | --- | --- |
| 1 — Frontend | Shared frontend foundation, authentication, admin operations | App shell, routing, shared UI, login, admin dashboard, event approval, budgets/expenses/settlement, workforce/logistics management, emergency and damage review | Runnable React shell, shared components, login mock, admin event list |
| 2 — Frontend | Client and guest experiences | Client event intake/dashboard, guest import/invitation management, agenda/map editor, client gift ledger, client claim response, albums, guest pass/RSVP/itinerary/room details, feedback | Client event form and guest pass using agreed fixtures |
| 3 — Frontend | Staff PWA and field operations | Staff tasks/status, QR scanner/check-in, incoming gift counter, return-gift inventory/redemption screens, emergency submission, damage evidence upload, staff media upload, later offline queue | Mobile staff task list and scanner input flow using fixtures |
| 4 — Python backend | Shared backend foundation, identity, events, finance | Auth/sessions/event permissions, users, memberships, event lifecycle, requirements, agenda/map metadata, budgets, expenses, settlement; shared DB/config and API conventions | Runnable FastAPI service, health endpoint, event/auth contract, initial migrations |
| 5 — Python backend | Workforce, logistics, incidents | Staff availability, event assignments, tasks/history, transport, rooms/guest room assignments, emergency lifecycle, damage reports/claims | Task and emergency contracts, models, service rules, focused tests |
| 6 — Python backend | Guests, gifts, media, feedback, asynchronous delivery | Guest imports/invites/RSVP, QR token service, check-in, gift logs, inventory/redemptions, media/albums, feedback, invitation workers; shared upload/notification/outbox infrastructure | Guest/QR/gift contracts, transaction rules, fixture responses |

Member 1 owns admin screens across backend domains, so backend members must support multiple frontend consumers. Member 6 has a large domain set: prioritize guests/check-in/gifts, then add albums and feedback. Review capacity at each checkpoint; move whole bounded features with explicit ownership updates if needed.

## Shared files and boundaries

| Area | Maintainer | Collaboration rule |
| --- | --- | --- |
| frontend/package.json, lockfile, main.jsx, App.jsx, routes, shared UI, API client | 1 | Other frontend members request additions; keep their feature changes inside owned folders. Register routes in small integration PRs. |
| frontend/src/features/admin and auth | 1 | Admin presentation only; consume domain APIs. |
| frontend/src/features/client and guest | 2 | Use shared components and API client; avoid a second design system. |
| frontend/src/features/staff and offline | 3 | Build mobile layouts and feature-specific sync behavior. |
| backend/app/main.py, core, db, auth, events, finance; base migration | 4 | Publish stable auth, DB session, permission, and event service interfaces first. |
| backend/app/modules/workforce, logistics, incidents | 5 | Own models, schemas, services, routers, and tests for these modules. |
| backend/app/modules/guests, gifts, media, feedback; workers and notification services | 6 | Expose guest verification, authorized uploads, and durable notification interfaces. |
| backend dependency file, Alembic migration chain, CI, infra | 4 | Each backend owner writes their migrations; member 4 serializes merge order and checks for a single migration head. Member 6 contributes worker/storage configuration. |
| docs/contracts | Respective backend owner | Frontend consumers review before implementation. Member 4 coordinates shared conventions. |

No member edits another member's owned shared file without coordinating the change. This is a merge-conflict convention, not a restriction on code review.

## Contract checkpoint — required before connecting features

All six agree on contracts together. Members 4–6 publish OpenAPI-compatible schemas and example JSON for their modules. Members 1–3 develop against those exact examples and mocked HTTP responses while APIs are being built.

Common conventions:

- REST prefix `/api/v1`; UUID identifiers; UTC ISO-8601 timestamps; explicit display timezone.
- Money is a decimal string plus currency. Never perform accounting with floating-point values.
- Paginated lists return `{ items, total, page, page_size }`.
- Errors return `{ error: { code, message, field_errors }, request_id }`. Define a consistent validation-error adapter.
- Successful creates return 201, asynchronous requests 202, unauthorized access 401, forbidden access 403, and state/duplicate conflicts 409 where appropriate. Define resource concealment rules consistently.
- Auth uses short-lived bearer access tokens held in memory and an HttpOnly refresh cookie, with refresh rotation and explicit logout/revocation. Configure cookie, CSRF/origin checks, and CORS consistently for local and deployed environments; no long-lived tokens in localStorage.
- Every event endpoint checks event membership/ownership and action permissions on the server. Guest tokens have limited capabilities and do not become employee sessions.
- Event states: draft, submitted, approved, in_progress, completed, cancelled. Task states: pending, active, finished. Emergency states: open, acknowledged, in_progress, resolved, rejected. Document allowed actors/transitions and terminal-state behavior.
- Use an idempotency key for retried transactional mutations, scoped to actor and operation. Member 4 defines the shared mechanism; each domain enforces it with domain constraints.
- WebSocket envelope: `{ id, type, event_id, occurred_at, payload }`. Member 6 owns shared notification delivery; member 5 publishes incident notifications and member 6 publishes gift updates. Persist first, authorize subscriptions, and fetch missed state after reconnect.
- Guest QR lookup/check-in/redemption remain distinct actions. Staff privileges and event scope are checked for all operational actions. A QR scan alone does not redeem a gift.

Proposed API families (final payloads belong in the contracts):

| Backend owner | API families | Frontend consumers |
| --- | --- | --- |
| 4 | /auth/*, /users, /events, /events/{id}/members, /events/{id}/agenda, /events/{id}/budget-lines, /events/{id}/expenses, /events/{id}/settlements | 1, 2; shared identity/event context for 3 |
| 5 | /staff/availability, /events/{id}/staff, /events/{id}/tasks, /events/{id}/transport, /events/{id}/accommodation, /events/{id}/emergencies, /events/{id}/damage-reports, /events/{id}/damage-claims | 1, 2, 3 |
| 6 | /events/{id}/guests, guest-imports, invitations, check-ins, gifts, return-gift-items, redemptions, albums, feedback; /guest/*; /uploads/*; notifications and WebSocket channel | 1, 2, 3 |

## Work that begins in parallel

These are dependency checkpoints, not calendar estimates. No one needs to wait for another person's completed feature to start.

### Checkpoint A — setup and contract agreement

1. Member 1 creates the React shell, reusable form/table/status components, API client, mock-response setup, and route placeholders.
2. Member 2 drafts client/guest routes, forms, and fixtures in their feature folders.
3. Member 3 drafts staff mobile screens, scanner/manual token input, and pending/error/success states.
4. Member 4 creates the FastAPI shell, DB/auth interfaces, event schema, base migration, and development service configuration.
5. Member 5 drafts workforce/incident models, contracts, state rules, and domain tests against the agreed interfaces.
6. Member 6 drafts guest/gift models, contracts, QR verification interface, and transaction tests; defines worker/upload/notification interfaces.

Exit: a clean checkout has documented run commands; example responses and shared IDs are agreed; each member has an independently runnable or mockable slice. Shared scaffolding must be merged early in small increments.

### Checkpoint B — first integrated event workflow

| Member | Deliverable |
| --- | --- |
| 1 | Real login, event approval, staff assignment, admin task view |
| 2 | Real client event creation, guest import and invitation view, guest pass/agenda |
| 3 | Real staff task updates and check-in flow |
| 4 | Auth, authorization, event creation/review, agenda and baseline budget APIs |
| 5 | Staff availability/assignment and task APIs |
| 6 | Guest import, QR generation, invitation worker and check-in APIs |

Exit: client creates event → admin approves and assigns staff → guest invitation is generated → staff checks guest in. Run with real APIs and PostgreSQL, including cross-event denial and duplicate check-in tests.

### Checkpoint C — live operations

| Member | Deliverable |
| --- | --- |
| 1 | Emergency acknowledgement dashboard, inventory management, budget/expense views |
| 2 | Live client gift ledger, claim response screen |
| 3 | Gift logging/redemption, emergency and damage reporting |
| 4 | Expense approval APIs, audit/idempotency support, initial settlement calculation |
| 5 | Durable emergency lifecycle, notification publishing, damage/claim review APIs |
| 6 | Gift inventory/redemption transactions, client updates, shared uploads and notification recovery |

Exit: incoming gift appears in the client's ledger; return gift is redeemed once; concurrent attempts cannot overdraw inventory; emergency persists, reaches admin, and can be acknowledged after reconnect. Damage reports create reviewable claims, not automatic charges.

### Checkpoint D — complete scope and release

| Member | Deliverable |
| --- | --- |
| 1 | Admin logistics, settlement views, responsive/accessibility cleanup |
| 2 | Client albums/settlement, guest lodging details and feedback |
| 3 | Staff logistics/media uploads, limited offline task updates and gift drafts |
| 4 | Reconciled settlement, deployment pipeline, backups and restore exercise |
| 5 | Transport/room allocation, incident recovery and assignment-conflict validation |
| 6 | Private albums, feedback, delivery retry validation, gift draft sync integration |

Exit: full demonstration passes on staging. Member 3 defines offline client queue behavior with members 5/6; both server owners validate/reject replayed actions. Keep redemption, financial approvals, and emergency delivery online. Show unsent emergencies clearly with a manual contact fallback.

## Integration and Git workflow

- One repository with frontend/, backend/, infra/, and docs/. One shared main branch that remains runnable.
- Use short-lived feature branches such as feat/m2-client-event-form or feat/m5-emergency-api. Merge complete, small slices; do not wait until the final checkpoint to integrate.
- Each feature PR includes its contract/schema changes, migration if needed, UI states or API examples, and relevant verification. Frontend mocks must be updated alongside contract changes.
- A frontend change gets frontend peer review; a backend change gets backend peer review. The relevant frontend consumer also reviews API changes.
- Backend member 4 coordinates migrations and infrastructure merges; frontend member 1 coordinates shared route/UI changes. These responsibilities do not make them the only reviewers.
- Integrate daily when working daily. Each member reports completed work, the next slice, blockers, and contract changes. Resolve breaking contracts before more dependent code is written.
- Keep a shared seeded scenario: admin, client, two staff members, two events, guests, stock, and an incident. Use the same UUID fixtures in frontend mocks and backend seeds.
- Maintain .env.example with placeholder values; keep credentials and guest QR secrets out of commits/logs.

## Definition of done and shared validation

Every feature needs working API integration, loading/empty/error/success UI states, server-side authorization, database migrations where relevant, and updated contracts. Every member owns validation of their slice.

| Check | Responsible members |
| --- | --- |
| Event ownership, permissions, expired sessions, settlement reconciliation | 4 implements; 1/2 verify user flows |
| Staff booking conflicts, invalid task transitions, emergency acknowledgement/recovery | 5 implements; 1/3 verify flows |
| Wrong-event/revoked QR, repeated check-in, simultaneous redemption, stock exhaustion | 6 implements; 2/3 verify flows |
| Private media access, upload validation, invitation retries | 6 implements; 2/3 verify flows |
| Mobile layout, camera permission denial/manual token fallback, offline pending/conflict states | 3 leads; 5/6 verify sync behavior |
| Full event scenario on staging | All six; 1 coordinates UI integration, 4 coordinates deployment |

The final demonstration must cover: client event submission → admin approval → staff assignment → guest invitation → check-in → gift logging → emergency acknowledgement → return-gift redemption → claim review → settlement. Also demonstrate denial of another event's data and rejection of a duplicate redemption.

## Deferred commitments

Deadline, member names/experience, hosting budget, external delivery providers, concurrency targets, and production versus academic-demo expectations remain unknown. Assign calendar dates after these are known. All six can begin Checkpoint A immediately using the ownership and contract rules above.
