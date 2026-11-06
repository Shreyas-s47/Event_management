# Event Management System — Implementation Plan

## Basis and scope

Reviewed all 10 pages of `C:\Users\Shreyas\Downloads\nasscom project sys.pdf`. The workspace was empty at initial review time. The PDF is a reference architecture, not an implementation-ready specification. This plan preserves its four roles and functional scope while proposing explicit implementation decisions. Member 4's first backend slice is now implemented; see [current status](docs/MEMBER_4_STATUS.md) and [backend setup](backend/README.md).

Working assumption: six members (three frontend and three backend) first deliver a demonstrable single event-management organization's system. See [SIX_MEMBER_WORK_PLAN.md](SIX_MEMBER_WORK_PLAN.md) for parallel ownership and integration checkpoints. Confirm deadline, deployment budget, expected concurrent users, and whether multiple independent organizations must be supported before estimating calendar dates. Production readiness requires separate operational validation.

## Proposed technical decisions

- One React.js frontend using JavaScript, Vite, React Router, and Tailwind CSS, with role-specific routes for admin, client, staff, and guests; staff routes provide the PWA experience. Route visibility is convenience; backend authorization is mandatory.
- One modular FastAPI backend with REST endpoints under `/api/v1` and authenticated event-scoped WebSockets. Keep domains separate within one deployable application rather than starting with microservices.
- PostgreSQL as the source of truth; SQLAlchemy and Alembic for persistence and migrations.
- Celery with Redis as its broker for invitation generation/delivery and media processing. Redis Pub/Sub can distribute live notifications, but is not a durable incident record. The PDF's Redis Streams reference must not be treated as the default Celery transport.
- Private S3-compatible object storage for uploads; local MinIO during development. Authorize downloads and issue short-lived URLs rather than public album URLs.
- Service worker for cached application assets; IndexedDB for a limited staff offline action queue. Do not assume ordinary browser PWAs provide SQLite by default.
- Containerized local services; test PostgreSQL behavior using PostgreSQL. Choose deployment hosting after capacity and budget are known. Run Celery in Linux containers on Windows development machines.
- Pin supported package versions when implementation begins; the version numbers in the PDF are reference baselines.

## Architecture corrections and decisions

| PDF area | Required implementation detail |
| --- | --- |
| Four roles | Add event membership and permissions. An employee sees assigned events; a client sees owned events. Guests receive event-scoped capabilities rather than staff credentials. |
| Guest QR | Use a high-entropy opaque token stored as a hash, with expiry/revocation. QR lookup must not itself authorize gift redemption or staff operations. Staff verifies check-in/redemption. |
| Return gifts | Add a redemption ledger, eligibility policy, inventory movements, and database uniqueness constraints. Decrement stock and create redemption in one transaction. Default proposal: one redemption per guest per event, subject to product confirmation. |
| Emergency notifications | Persist before notifying; support acknowledgement, assignment, resolution, and reconnect catch-up. An offline request must display 'not delivered'; it cannot promise immediate escalation. Provide a visible manual contact fallback. |
| Offline operations | Queue low-risk task updates and draft gift logs with operation IDs and entity versions. Server validates on sync and returns accepted/rejected/conflicted results. Keep approvals, stock redemption, and financial actions online for the first release. |
| Damage claims | Create a reported incident and proposed claim, with evidence, review, client response, and settlement history. Do not automatically deduct money from a deposit on report submission. |
| Budget and settlement | Add budget lines, expenses, approvals, payments/adjustments, and settlement records. Use decimal money values and explicit currency; payment collection is separate scope. |
| Event lifecycle | Use explicit workflow states such as draft, submitted, approved, in_progress, completed, cancelled. Past/present/upcoming are date-based views, not replacement workflow states. |
| Invitations and uploads | Validate guest imports, record delivery attempts, use bounded retries, and restrict file types/sizes. Do not log guest tokens or personal data unnecessarily. |
| Live alerts | Treat WebSockets as delivery hints; clients refetch authoritative state. Event authorization applies to socket subscriptions as well as REST. |

## Domain and data model

Every event-owned row carries an event ID. Enforce same-event relationships in the database where practical and in the service layer. Add created/updated timestamps and audit sensitive mutations.

| Domain | Initial entities |
| --- | --- |
| Identity | users, sessions, event_memberships |
| Planning | events, event_requirements, agenda_items, venue_assets |
| Workforce | availability_slots, event_staff, tasks, task_status_history |
| Guests | guests, invitations, invitation_attempts, guest_access_tokens, check_ins |
| Gifts | gift_logs, return_gift_items, inventory_movements, return_gift_redemptions |
| Incidents | emergency_requests, emergency_status_history, damage_reports, damage_claims |
| Finance | budget_lines, expenses, expense_approvals, settlements, settlement_adjustments |
| Hospitality | transport_bookings, accommodation_bookings, room_assignments |
| Media/feedback | media_assets, albums, album_assets, feedback |
| Reliability | audit_logs, notifications, outbox_events, processed_operations |

Start with the entities needed by the first workflow; add later-domain migrations with their features. Clarify multi-assignee tasks, household versus individual guests, overlapping employee bookings, partial gift allocation, and guest feedback eligibility before implementing their constraints.

## Delivery sequence and completion gates

### 1. Foundation and contracts

Create frontend/backend directories, configuration, container services, migrations, seeded demonstration accounts, authentication, event authorization, API error conventions, CI, and structured logging. Write the permission matrix, initial ERD, API contracts, and lifecycle transition rules.

Done when all four entry experiences work, cross-event access is denied, a clean database migrates successfully, and no secrets are committed.

### 2. Planning and workforce

Build client event intake, admin review/approval, agenda and venue map upload, budget lines, employee roster/availability, task assignment, and task state changes. Begin with an uploaded map image; interactive mapping is a later enhancement.

Done when a client submits an event, an admin approves it and assigns a staff member, and that staff member completes a task with an audit trail. Invalid transitions and conflicting allocations are handled explicitly.

### 3. Invitations and attendance

Implement validated CSV guest import, invitation preview, QR generation, asynchronous email delivery with attempt history, guest itinerary page, staff scanning, and transactional check-in. Use a local mail capture service before configuring an external provider. SMS follows when a provider and budget are selected.

Done when an invited guest opens the correct event page and staff checks them in; a second scan does not create duplicate attendance, and revoked/wrong-event tokens fail.

### 4. Gifts and live incidents — first end-to-end demo

Add incoming gift logging, client ledger, return-gift inventory and redemption, emergency submission, admin acknowledgement/resolution, durable notifications, and WebSocket updates with reconnect recovery.

Done when the demonstration covers event creation → staff assignment → invitation → check-in → gift logging → emergency acknowledgement → one-time return-gift redemption. Concurrent redemption attempts cannot overdraw stock or produce duplicate claims.

### 5. Remaining PDF scope

Add transport and rooms, damage evidence and claim review, private media albums, client/guest feedback, expense approval, and settlement summaries. Add staff offline drafts/task updates with explicit sync conflicts and delivery status.

Done when access is checked for media, claim changes are audited, settlement totals reconcile, and offline retries do not duplicate records. Full offline check-in/redemption requires a separate conflict and reconciliation design.

### 6. Release validation

Run representative load checks against the agreed capacity, restore a database backup, verify worker retry/recovery, exercise socket reconnects and service outages, validate phone layouts, and prepare deployment/rollback instructions and a repeatable demo dataset.

Done when the agreed workflows pass in a deployed staging environment and documented recovery procedures have been exercised. Update the PDF's ERD, sequence, component, and deployment diagrams to match the actual build.

## Suggested repository structure

```text
frontend/                 # Role routes, shared UI, PWA and offline queue
backend/
  app/
    api/                  # REST and WebSocket adapters
    modules/              # auth, events, workforce, guests, gifts, incidents, ...
    core/                 # Configuration, security, shared errors
    db/                   # Database setup
    workers/              # Celery jobs and outbox delivery
  migrations/
  tests/
infra/                    # Containers and deployment configuration
docs/                     # Permission matrix, ERD, contracts and runbooks
```

## Essential verification

- API authorization: role, event ownership, staff assignment, guest scope, and private file access.
- Transaction tests: simultaneous check-in/redemption, stock exhaustion, expense approval, and invalid state transitions.
- Retry tests: repeated operation IDs and worker retries do not duplicate database effects; record provider delivery IDs and account for ambiguous external email delivery.
- Resilience tests: Redis/worker outage leaves committed requests recoverable; notification reconnect retrieves missed records; offline actions show their real delivery status.
- Browser smoke flow: client creates event, admin assigns staff, guest arrives, staff logs gift, admin resolves emergency, guest redeems once.
- Restore and reconciliation: recover a backup and compare financial/inventory totals with source ledgers.

## Open decisions before sprint commitments

1. Is the target an assessed college demo, a pilot at real events, or a production service?
2. What are the deadline, hosting budget, and expected event/guest/concurrency scale? Team size is confirmed as six.
3. Does the first release need every PDF module, and what offline behavior is mandatory?
4. Is this one organization's system or a multi-organization product? Multi-organization support changes authorization and schema scope.
5. Which email/SMS and storage providers are available, and are actual payment collection or deposit deductions required?

## Reference checks

- Source architecture: supplied PDF, pages 1–10.
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/
- Browser offline data: https://developer.mozilla.org/en-US/docs/Web/API/IndexedDB_API/Using_IndexedDB
- Celery Redis transport/retries: https://docs.celeryq.dev/en/latest/getting-started/backends-and-brokers/redis.html
- Celery task idempotency: https://docs.celeryq.dev/en/latest/userguide/tasks.html
