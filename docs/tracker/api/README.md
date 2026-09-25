# Mobile API (v1)

The iOS client's only backend boundary. It is a separate FastAPI application mounted at
`/mobile/v1` with its own OpenAPI document; the legacy `/v1` report API, its generated client
and its CI diff check are untouched. Resource design and state projections are specified in
[MOBILE-API-DRAFT](../architecture/MOBILE-API-DRAFT.md); product meaning in the
[feature SSOTs](../README.md).

- Contract: [`mobile-openapi-v1.json`](mobile-openapi-v1.json), exported with
  `make tracker-openapi`. `tests/tracker/test_mobile_golden.py` fails when the live schema drifts
  from this file, lints it structurally and scans it for pipeline/provider vocabulary.
- Golden responses: `tests/fixtures/tracker/mobile-v1/` — one file per seeded persona, covering
  every state the goal lists (bootstrap outcomes, Stage 1/2, failures, N/A beside zero, trends,
  roles, Free/Pro, switch cooldown, deletion, data access, sync error). They are compared, never
  overwritten; a contract change adds a new versioned directory.
- Local data: `make seed-demo` creates the same personas without provider calls.

## Conventions

| Concern | Rule |
|---|---|
| Authentication | Bearer access token from `/auth/apple` or `/auth/google`; rotating refresh tokens (`/sessions/refresh`). Email is unavailable until its mechanism is decided. |
| Isolation | Every resource is scoped to the caller's account and active Steam profile; match references are opaque UUIDs. Foreign references return 404. |
| Mutations | Every mutating POST requires `Idempotency-Key`; a replay returns the first result, a different body with the same key returns `409 IDEMPOTENCY_CONFLICT`. |
| Errors | `application/problem+json` with a stable `code` and a `request_id`. No upstream text or private identifiers. |
| Time | UTC RFC 3339. Home takes an IANA `time_zone` for "today" and an explicit `mode`. |
| Pagination | Opaque signed cursors bound to profile, filters and revision (`/history`). |
| Incremental refresh | Body ETags with `If-None-Match` → 304 on every JSON GET; `GET /changes?after=` returns changed match refs or `full_refresh`. Push stays READY-only. |
| Enums | Closed. Swift should keep unknown values and show a neutral unsupported state, never interpret them as success, zero or evidence. |
| Missing values | Nullable with a reason; a measured zero stays zero. Every block carries its own readiness. |
| Text | Insight cards and claims are template IDs plus typed slots. Insight history lines are versioned annex wording and always state N. |

Server-to-server routes (`/store/app-store/notifications`) and the operations readout
(`/internal/tracker`) are separate applications without a mobile OpenAPI entry.

## Swift code generation

No Swift OpenAPI generator is installed in this environment, so a generation dry run has not
been performed. The checked-in document is the intended generator input.
