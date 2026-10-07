# Deployment notes (not performed)

These are prerequisites and ordering notes for a future owner-approved release. Nothing in
this repository deploys, and the tracker backend has not been deployed.

## Prerequisites

| Item | Why | Status |
|---|---|---|
| Stable static outbound IP for STRATZ | Tokens are IP-bound; rotating egress disables historical acquisition. | External; not configurable in code. |
| Dedicated tracker worker processes per priority (P0, P1, P2, P3) plus one beat | Redis brokers give no strict priority inside one worker. The compose `tracker` profile shows the layout. | Layout proven locally; Railway service configuration unknown. |
| Apple/Google sign-in audiences (`TRACKER_APPLE_AUDIENCE`, `TRACKER_GOOGLE_AUDIENCE`) | ID tokens are verified against fixed issuers' JWKS for these audiences. | Owner credentials required. |
| Steam OpenID callback (`TRACKER_STEAM_CALLBACK_URL`) | Assertions are verified server-side with `check_authentication`. | Owner configuration required. |
| App Store root certificate and bundle id (`TRACKER_APP_STORE_ROOT_CERT_PATH`, `TRACKER_APP_STORE_BUNDLE_ID`) | JWS chains must end in the pinned Apple Root CA G3. The notification endpoint is `/store/app-store/notifications`. | Owner credentials required; revocation (OCSP) checking is a follow-up. |
| APNs credentials and an HTTP/2 push transport | Outbox bundles are delivered through `PushTransport`; no production transport ships. | Not implemented beyond the interface and fake. |
| `TRACKER_INTERNAL_TOKEN` | Operations readout authentication; separate from mobile sessions. | Operator secret. |
| `TRACKER_CURSOR_SECRET` (at least 32 characters, shared by all API replicas) | MAC key for History and Changes cursors. Without it, production `/history` and `/changes` answer 503 while the rest of the API starts. Rotating it invalidates outstanding cursors; clients refetch. | Operator secret. |
| Approved context parameter set | Without one, adjustment is zero and performance states are `NOT_READY`. | Owner/calibration gate. |

## Order

1. Back up the production database. Migrations `0006`–`0018` create `tracker_*` tables,
   functions and triggers. Migration `0019` **drops** the sixteen tables of the removed
   report-card product (never live, no users; owner decision 2026-10-07). Its downgrade
   recreates them empty and cannot restore rows.
2. Run `alembic upgrade head` before starting any new process: the API and workers refuse to
   start against an older revision.
3. Start the API, then the tracker beat and the four tracker workers. A Railway worker started
   with the fixed entrypoint `celery -A app.workers.tasks.celery_app` runs the tracker Celery
   app; give it `-Q tracker-p<n>` per priority lane (see the compose `tracker` profile).
4. Configure the environment values above; each unconfigured capability stays fail-closed.
5. Smoke-test with an existing account through `/mobile/v1` read routes only; do not generate
   reports or spend provider budget for presentation checks.

The drop is covered by `tests/tracker/test_schema.py` (tracker rows survive, the report-card
tables are gone at head and come back empty on downgrade) and `tests/unit/test_migrations.py`.
