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
| Approved context parameter set | Without one, adjustment is zero and performance states are `NOT_READY`. | Owner/calibration gate. |

## Order

1. Back up the production database. Migrations `0006`–`0015` are additive: they create
   `tracker_*` tables, functions and triggers and do not alter legacy tables or retention.
2. Run `alembic upgrade head` before starting any new process: the API and workers refuse to
   start against an older revision.
3. Start the existing legacy API and report worker unchanged, then the tracker beat and the
   four tracker workers.
4. Configure the environment values above; each unconfigured capability stays fail-closed.
5. Smoke-test with an existing account through `/mobile/v1` read routes only; do not generate
   reports or spend provider budget for presentation checks.

The legacy report product, its persisted reports and the `/v1` API contract are unchanged by
the tracker migrations; this is covered by `tests/tracker/test_schema.py` (populated upgrade
from `0005`, current and historical persisted-report reads) and the contract suite.
