# Tracker backend runbook

Implementation guide for the Dota Tracker backend. Product meaning lives in the
[feature SSOTs](../README.md); system behaviour lives in the
[architecture](../architecture/README.md). This page only says how to run and verify
the code. Progress and open decisions are in the
[implementation ledger](../architecture/IMPLEMENTATION-LEDGER.md).

Related pages: [provider operations](providers.md) · [deployment notes](deployment-notes.md) ·
[mobile API](../api/README.md).

## Where things live

| Boundary | Path |
|---|---|
| Tracker runtime (schema, pipeline, engines, mobile API, workers) | `services/api/app/tracker/` — see its [module map](../../../services/api/app/tracker/README.md) |
| Tracker migrations | `migrations/versions/0006_…` to `0015_…` (additive; legacy tables untouched) |
| Tracker tests | `tests/tracker/` (PostgreSQL + Redis required), `tests/unit/test_migrations.py` |
| Sanitized fixtures | `tests/fixtures/tracker/` (provider specimens, golden mobile responses) |
| Local seed, OpenAPI export, traceability | `scripts/tracker_seed_demo.py`, `scripts/tracker_export_openapi.py`, `scripts/tracker_traceability.py` |
| Live legacy report product (still in production) | `legacy/apps/web/`, legacy `/v1` routes, `legacy/services/api/report_card/` — see [legacy boundaries](../../../legacy/README.md) |

## Local dependencies

The tracker needs PostgreSQL 16 and Redis 7. SQLite cannot prove its guarantees
(`SKIP LOCKED`, partial unique indexes, JSONB, deferred constraint triggers) and the
tracker tests refuse to run without both URLs.

```bash
make infra-up            # docker compose: postgres + redis
make db-migrate          # alembic upgrade head (legacy + tracker revisions)
```

Without Docker, any local PostgreSQL 16 and Redis 7 work; point `DATABASE_URL`,
`TEST_POSTGRES_URL` and `TEST_REDIS_URL` at them. The API and every worker refuse to start
unless the database is at `EXPECTED_SCHEMA_REVISION` (`services/api/app/storage/database.py`).

## Running

```bash
make dev                              # FastAPI: legacy /v1, /mobile/v1, /store, /internal/tracker
make tracker-worker PRIORITY=0        # one terminal per priority class: 0, 1, 2, 3
make tracker-beat                     # wake signals only; PostgreSQL owns scheduling
DATABASE_URL=… make seed-demo         # thirteen fixture-backed personas, prints bearer tokens
```

Run each priority in its own process (compose profile `tracker` does this). A single
worker consuming several queues on Redis gives no strict priority. P3 can be paused by
setting the Redis key `<TRACKER_NAMESPACE>:pause:p3`; it resumes from stored cursors.

Environment variables are listed with comments in [`.env.example`](../../../.env.example).
Empty identity/store/operations values keep their routes fail-closed (503), never open.

## Verifying

```bash
TEST_POSTGRES_URL=postgresql+psycopg://…/tracker_test TEST_REDIS_URL=redis://localhost:6379/0 make test-tracker
uv run pytest -q tests/unit/test_migrations.py tests/contract          # migration units, legacy contracts
RUN_POSTGRES_MIGRATION_TEST=1 TEST_POSTGRES_URL=… uv run pytest -q tests/integration/test_postgres_migrations.py
uv run python -m scripts.tracker_traceability --strict                 # SSOT acceptance coverage
make lint typecheck docs-check                                         # repository gates
```

What the tracker suite proves, by file:

| Concern | Tests |
|---|---|
| Fresh chain end to end (sync → summary → links → one replay path → ordered finalization → mobile) | `test_e2e_matrix.py`, `test_pipeline_e2e.py` |
| Replay ladder, terminal outcomes, duplicate delivery, crash recovery | `test_replay_acquisition.py`, `test_acquisition.py`, `test_sync.py` |
| Priority lanes, backpressure, separate-process non-starvation (real Celery) | `test_worker.py` |
| Bootstrap, backfill, historical batches, data-access recovery | `test_bootstrap.py`, `test_backfill.py`, `test_historical*.py`, `test_mobile_inventory.py` |
| Roles, metrics, baselines, PBs, context, insights, trend | `test_roles.py`, `test_metrics.py`, `test_history.py`, `test_context.py`, `test_insights.py`, `test_trend.py` |
| Corrections and deterministic rebuilds (run twice, zero provider calls) | `test_role_correction.py`, `test_rebuild.py` |
| Identity, Steam, App Store, entitlement, switching, deletion | `test_authentication.py`, `test_steam_identity.py`, `test_app_store.py`, `test_entitlement.py`, `test_account_lifecycle.py` |
| Mobile contract, golden fixtures, vocabulary scan, provider-free reads | `test_mobile_*.py`, `test_architecture_boundaries.py`, `test_contract_rules*.py` |
| Schema, migrations, legacy report reads after upgrade | `test_schema.py`, `tests/unit/test_migrations.py` |

A skipped test is not a passing test. The tracker fixtures skip only when the
PostgreSQL/Redis URLs are absent; CI provides both.

### Live provider smoke checks

Live calls are never part of the test suite. The goal's budgets (OpenDota ≤ 200 reads and
≤ 10 processing requests; STRATZ ≤ 60 smoke calls plus one parameter-job run) and every call
actually made are recorded in the ledger. STRATZ calls additionally require the IP-binding
safety check in [provider operations](providers.md).

## Rebuilds and version bumps

A change to `ANALYSIS_VERSION`, `BASELINE_VERSION`, `FEATURE_VERSION` or the approved context
parameter set is replayed from stored data by `rebuild.enqueue_methodology_rebuilds` (one P3
job per affected profile). Each bucket replays from its earliest stale chronology point in one
transaction; a failure keeps the previous coherent state. Entitlement changes run as
`SCOPE_REBUILD` jobs. None of these paths can reach a provider.
