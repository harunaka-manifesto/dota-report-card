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
| Migrations | `migrations/versions/` — `0001`–`0005` built the removed report-card schema, `0006`–`0018` the tracker, `0019` drops the report-card tables (frozen schema in `migrations/historical_schema.py`) |
| Tracker tests | `tests/tracker/` (PostgreSQL + Redis required), `tests/unit/test_migrations.py` |
| Sanitized fixtures | `tests/fixtures/tracker/` (provider specimens, golden mobile responses) |
| Local seed, OpenAPI export, traceability | `scripts/tracker_seed_demo.py`, `scripts/tracker_export_openapi.py`, `scripts/tracker_traceability.py` |

## Local dependencies

The tracker needs PostgreSQL 16 and Redis 7. SQLite cannot prove its guarantees
(`SKIP LOCKED`, partial unique indexes, JSONB, deferred constraint triggers) and the
tracker tests refuse to run without both URLs.

```bash
make infra-up            # docker compose: postgres + redis
make db-migrate          # alembic upgrade head
```

Without Docker, any local PostgreSQL 16 and Redis 7 work; point `DATABASE_URL`,
`TEST_POSTGRES_URL` and `TEST_REDIS_URL` at them. The API and every worker refuse to start
unless the database is at `EXPECTED_SCHEMA_REVISION` (`services/api/app/storage/database.py`).

## Running

```bash
make dev                              # FastAPI: /health*, /mobile/v1, /store, /internal/tracker
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
uv run pytest -q tests/unit                                             # migration units, transports, composition root
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
| Schema, migrations, report-card table drop | `test_schema.py`, `tests/unit/test_migrations.py` |

A skipped test is not a passing test. The tracker fixtures skip only when the
PostgreSQL/Redis URLs are absent; CI provides both.

### Live provider smoke checks

Live calls are never part of the test suite. The goal's budgets (OpenDota ≤ 200 reads and
≤ 10 processing requests; STRATZ ≤ 60 smoke calls plus one parameter-job run) and every call
actually made are recorded in the ledger. STRATZ calls additionally require the IP-binding
safety check in [provider operations](providers.md).

## Rebuilds and version bumps

A change to `ANALYSIS_VERSION`, `BASELINE_VERSION` or `FEATURE_VERSION` is replayed from stored
data by `rebuild.enqueue_methodology_rebuilds` (one P3 job per affected profile). A replayed
match is re-graded with the context parameter set it was first graded with. A **new** parameter
set replays nothing except matches that were never graded (foundation §10.8). Each bucket replays from its earliest stale chronology point in one
transaction; a failure keeps the previous coherent state. Entitlement changes run as
`SCOPE_REBUILD` jobs. None of these paths can reach a provider.

## Context parameter refresh (each major patch)

The hero averages, metric spreads and badge lane data behind performance states and Role
Mastery live in one immutable approved set (current: `context-2026-09-v1`, file
`migrations/data/context-2026-09-v1.json`, registered by migration `0017`). Refresh after each
major Dota patch; past matches and XP are never touched.

1. Collect a fresh 4–8 week STRATZ `heroStats.stats` + `heroStats.laneOutcome` pool through the
   audited provider gate (about 160 calls for 8 weeks; 0 OpenDota). Keep raw responses in
   ignored `.local/`, never in Git.
2. Build with `population_parameters.build_artifact` (reference builder:
   `.local/tracker-context-calibration-2026-09-27/scripts/tracker_mastery_candidate_v3.py`),
   using a new version name such as `context-2026-12-v1`. Keep `tau = 0.35`, the 5%-of-spread
   floor tolerance, the matchup multipliers 0.748 / 0.778 / 0.722 and `maximum_slope_drift = 0.10`
   unless the owner changes them. Metric spreads may be re-measured from retained ten-player
   matches.
3. Check: `validation.passed`, all 16 metrics present, hero-level coverage for the six
   farm metrics, `lane_model_passed` (if false, only the badge hides), and no player or match
   identifiers in the file.
4. Get owner sign-off on that exact file and digest.
5. Commit it under `migrations/data/` and add a new migration modelled on `0017` that verifies
   the digest and inserts it with status `APPROVED`. Bump `EXPECTED_SCHEMA_REVISION`.
6. Deploy the migration. New matches use the new set immediately; nothing is replayed, so
   no award, verdict or PB changes. Never edit or delete a registered set.

## Item timing artifact refresh and rebuild

The item timing algorithm, hero × core-role × mode × item cohort gates and the
`ENEMY_HERO_ITEM` / `OWN_HERO_ITEM` card rules are specified in the [Match Detail annex](../match_detail/ITEM-TIMINGS-V1.md). This is the final item design — item-only baseline, order is descriptive only. The complete timeline and comparison snapshot live in immutable `tracker_analyses.result` JSONB; this feature adds no table or migration. The analysis version, checked-in reference artifact, backend contract and OpenAPI export advance together.

For each lettered patch:

1. Update the patch-date mapping and review patch notes for changed hero/item pairs. Keep affected pairs in `patch_change_pending` until current-letter timing evidence supports them. Pool earlier letter-patch evidence only for pairs the review marks unaffected.
2. Build from the prepared normalized purchase-event corpus, not live provider responses. The existing builder entry point is:

   ```bash
   uv run python scripts/build_item_references.py --source <normalized-corpus> --patch <lettered-patch>
   ```

   `--patch` may be repeated to build more than one lettered patch's shard in one run.
3. Commit the updated shards and `item_references.json`. Verify the deterministic digest, all 762 hero × core-role × mode coverage cells, explicit `sparse` / `patch_change_pending` / `no_qualified_item` outcomes, the purchase-count/purchase-rate thresholds, and the absence of player identifiers. Re-run the 50-card relevance review against the refreshed artifact.
4. If the schema or algorithm changed, bump `ANALYSIS_VERSION`, regenerate the mobile schema with `make tracker-openapi`, and add Match Detail response fixtures under `tests/fixtures/tracker/mobile-v1-item-timings-v1/`. Never overwrite prior versioned goldens.
5. Rebuild retained analyses through `rebuild.enqueue_methodology_rebuilds`. This is the only rebuild path for a refreshed artifact — it uses persisted evidence and is provider-free; role correction also recomputes the timeline and card snapshot from retained purchase events. Repeating a rebuild must remain deterministic and idempotent.

Use stored fixtures and recorded provider responses for parity and API QA. Item-timing QA makes **0 OpenDota calls and 0 STRATZ calls**. Missing or sparse evidence remains unavailable or factual-only; do not fill a cohort or backfill a match with a live fetch.
