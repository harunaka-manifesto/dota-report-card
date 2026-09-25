# Tracker backend runtime

Product meaning: [Tracker SSOTs](../../../../docs/tracker/README.md).
System behavior: [Tracker architecture](../../../../docs/tracker/architecture/README.md).
How to run and verify: [runbook](../../../../docs/tracker/operations/README.md).
Status, decisions and blockers: [ledger](../../../../docs/tracker/architecture/IMPLEMENTATION-LEDGER.md).

This namespace is the Dota Tracker backend. It shares only transport clients
(`app.opendota`, `app.stratz`), configuration and the database engine with the live legacy
report product; legacy tables, routes and retention are untouched.

## Module map

| Layer | Modules |
|---|---|
| Storage contract | `schema.py` (migrations own DDL), `evidence.py` (immutable, content-addressed snapshots) |
| Provider control | `provider_control.py` (shared Redis admission, lanes, breaker), `provider_transport.py` (bounded, accounted HTTP wrapper) |
| Acquisition (P0–P3) | `sync.py`, `acquisition.py`, `replay_acquisition.py`, `historical.py`, `historical_summary.py`, `bootstrap.py`, `backfill.py`, `data_access.py` |
| Canonical translation | `normalization.py`, `replay.py`, `events.py`, `integrity.py`, `role_evidence.py`, `materialization.py` |
| Work model | `jobs.py` (database-owned scheduling, leases, generation fences), `linking.py`, `worker.py` (Celery lanes), `retry.py` |
| Analysis | `roles.py`, `eligibility.py`, `metrics.py`, `history.py`, `context.py`, `population_parameters.py`, `insights.py`, `trend.py`, `finalization.py` (the single publication point) |
| Rebuilds | `role_correction.py`, `rebuild.py` (scope, methodology/parameter set, late re-admission) |
| Entitlement above data | `scope.py` (the only entitled-history filter), `entitlement.py`, `app_store.py`, `store_api.py` |
| Identity and lifecycle | `authentication.py`, `steam_identity.py`, `account_lifecycle.py` |
| Product projections | `profile.py`, `profile_claims.py`, `shares.py`, `coverage.py`, `notifications.py` |
| Boundaries | `mobile_api.py` (`/mobile/v1`), `store_api.py` (`/store`), `operations.py` (`/internal/tracker`) |

## Invariants the code relies on

- Provider I/O happens only inside claimed jobs through `ControlledTransport`, outside the
  publication transaction. A response is persisted before it is used, so an internal failure
  retries from stored evidence without refetching.
- Private effects publish under `jobs.authorized_job` (user → profile → job locks, lease and
  generation checks). Deletion and Steam switching use the same order, so late results cannot
  commit after either.
- `finalization.complete_finalization_job` is the only place a match becomes READY, ordered per
  bucket by `(provider_started_at, match_id)`. Live work waits only on earlier live work and on
  its own mode's bootstrap.
- Analyses are immutable and keyed by `(profile, match, analysis_version, inputs_digest)`;
  rebuilds reuse identical rows, so running any rebuild twice changes nothing.
- Entitlement is read only through `scope.entitled` by history selection, rebuilds and
  projections. Acquisition, features, roles, metrics and insights never read it.
- Mobile reads use persisted state only and never enqueue work.
