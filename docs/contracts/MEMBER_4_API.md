# Member 4 API contract — first implementation

Base URL: http://localhost:8000/api/v1. Machine-readable contract: member4.openapi.json in this directory. The generated OpenAPI document is authoritative for fields and response schemas.

## Identity and browser sessions

| Method | Path | Permission / behavior |
| --- | --- | --- |
| POST | /auth/register | Public; creates client only; minimum 12-character password |
| POST | /auth/login | JSON email/password; returns access_token, token_type, expires_in, user; sets refresh cookie |
| POST | /auth/refresh | Rotates refresh cookie and returns new access token |
| POST | /auth/logout | Revokes the cookie's entire session; clears cookie; 204 |
| GET | /auth/me | Current authenticated account |
| POST | /users | Admin provisions a user with a role |
| GET | /users | Admin paginated user list |

Login, refresh, and logout require Origin: http://localhost:5173 and X-CSRF-Protection: 1. These requirements also apply when trying the endpoints through Swagger or a CLI. Swagger is hosted at the backend origin, so use the React dev origin or a CLI that explicitly sets Origin for these three endpoints. CORS preflight permits the custom header from configured frontend origins only.

Frontend request example (login):

```javascript
const response = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json', 'X-CSRF-Protection': '1' },
  body: JSON.stringify({ email, password }),
});
// The browser supplies Origin. Keep the returned access token in memory.
```

Protected APIs use Authorization: Bearer <access_token>. Refresh/logout use credentials: 'include'. The HttpOnly SameSite=Strict cookie is restricted to /api/v1/auth. Coordinate refresh calls across tabs/requests: reusing a rotated token revokes the session family and requires login again. Production requires HTTPS and a same-site frontend/backend deployment under this cookie policy. Cross-site deployments need a separate cookie/CSRF review.

Roles: admin, client, employee, audience. Audience accounts cannot use event operations; guest QR routes are Member 6's separate scoped capability flow. Role cannot be specified in public registration. Account listing never exposes password hashes.

## Events

| Method | Path | Permission / behavior |
| --- | --- | --- |
| POST | /events | Client creates an owned draft |
| GET | /events | Admin: all; client: owned; employee: membership-scoped; audience: empty |
| GET | /events/{id} | Admin, owner, or member employee |
| PUT | /events/{id} | Admin or owner replaces draft planning details |
| PATCH | /events/{id}/status | Explicit lifecycle transition |
| POST | /events/{id}/members | Admin adds an active employee |
| GET | /events/{id}/members | Admin or owner lists membership records |
| DELETE | /events/{id}/members/{user_id} | Admin removes event access |
| POST | /events/{id}/agenda | Admin or owner creates an agenda item within event times |
| GET | /events/{id}/agenda | Event readers; paginated |

Example POST /events input:

```json
{
  "title": "Annual gathering",
  "event_type": "conference",
  "requirements": "Stage and vegetarian catering",
  "venue": "Main hall",
  "venue_map": {},
  "starts_at": "2027-01-02T09:00:00+05:30",
  "ends_at": "2027-01-02T18:00:00+05:30",
  "total_budget": "100000.00",
  "currency": "INR"
}
```

Response adds id, client_id, status, created_at. Times must carry an offset and are stored in PostgreSQL timezone-aware columns. Monetary inputs must be decimal strings with at most two fractional digits. Supported currencies in this slice: INR, USD, EUR, GBP. Child finance entries inherit the event currency.

venue_map currently stores metadata only, such as an object key and description. It does not grant upload or media access. Treat it as untrusted display data; Member 6 must authorize object access independently.

Lifecycle:

- Owner or admin: draft → submitted or cancelled.
- Admin: submitted → approved, draft (request changes), or cancelled.
- Admin: approved → in_progress or cancelled.
- Admin: in_progress → completed or cancelled.
- completed/cancelled are terminal. Only drafts permit full replacement. Event dates cannot invalidate existing agenda; budget/currency edits cannot invalidate existing finance entries.

Unauthorized event IDs return 404; an event member attempting a manager-only action returns 403.

## Finance

| Method | Path under /events/{id} | Permission / behavior |
| --- | --- | --- |
| POST | /budget-lines | Owner/admin; title, amount; prevents allocation beyond total budget |
| GET | /budget-lines | Owner/admin; paginated |
| POST | /expenses | Event reader (staff included); description, amount; pending review |
| GET | /expenses | Owner/admin sees event expenses; staff sees own submissions only |
| PATCH | /expenses/{expense_id} | Admin reviews pending expense as approved/rejected; no self-approval |
| GET | /settlements/summary | Owner/admin; live allocation and expense totals |
| POST | /settlements | Admin finalizes approved-expense snapshot after event completion; no pending expenses |

POST budget-lines, expenses, settlements require Idempotency-Key (1–128 characters). Reusing the key for the same actor/operation/payload returns the same response without duplicating the record. Reusing it with different data returns 409. Retries still return 201. Failed operations roll back their keys so corrected requests can retry. Other POST APIs do not yet provide this retry guarantee.

Example expense input: { "description": "Catering deposit", "amount": "2500.00" }.

Expense amounts may exceed the planned budget; the summary exposes a negative remaining budget rather than silently preventing the recording of actual costs. Budget allocation cannot exceed the planned budget. Reviews can finish after an event completes, but new expenses cannot be submitted to closed events. After settlement, finance mutations are rejected. Claim adjustments/payments are outside this slice; do not present the snapshot as a payable invoice.

## Shared response behavior

- List shape: { items, total, page, page_size }; page starts at 1, page_size defaults to 20, maximum 100.
- Error shape: { error: { code, message, field_errors: [{field, message}] }, request_id }.
- X-Request-ID is returned for correlation. Rejected field values are not echoed.
- Missing/expired/revoked authentication: 401. Wrong role/action: 403. Unknown/concealed resource: 404. Conflict or invalid transition: 409. Invalid input: 422.
- No credentials, QR secrets, or request bodies should be added to logs.
