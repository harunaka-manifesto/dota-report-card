# Tracker backend runtime

Product meaning: [Tracker SSOTs](../../../../docs/tracker/README.md).
System behavior: [Tracker architecture](../../../../docs/tracker/architecture/README.md).
Implementation status: [ledger](../../../../docs/tracker/architecture/IMPLEMENTATION-LEDGER.md).

This namespace is under implementation. The current slice provides the PostgreSQL schema;
it does not yet provide authentication, the match pipeline, analytical engines or mobile routes.

## Storage boundary

`schema.py` uses SQLAlchemy Core and separate metadata. `tracker_matches` is the single
canonical match table for all tracker users; `tracker_match_players` holds ten canonical
slots (0–4 Radiant, 5–9 Dire). Legacy `matches` and related tables are report-extraction
storage, not the tracker canonical store. No report data is copied or rewritten.
Tracker match IDs are 64-bit; source-to-slot normalization belongs at the adapter boundary.

All tracker tables use the `tracker_` prefix. This keeps the live legacy purge policy intact
and avoids changing the historical migration that creates the legacy ORM metadata.
`migrations/env.py` exposes both metadata sets; the frozen `0006_tracker_foundation` migration
creates only new tables, indexes, constraints and tracker-specific trigger functions.
Runtime must never call `create_all` for these tables.

User analytical state belongs to a Steam profile. Foreign keys retain the account identity,
while the profile boundary prevents an archived profile or a later owner from inheriting
private role assertions, notifications or analytics. Partial unique indexes enforce one active
Steam account per user and one active owner per Steam account. Switching may archive a
profile; deletion cascades user-scoped rows while shared canonical retention remains an
explicit launch-policy gate.

- Summary readiness requires the header and all ten players in the same committed transaction.
- Evidence and per-profile lifecycle remain separate columns; finalized state references an
  analysis for the same profile and match and requires terminal evidence.
- Raw snapshots coexist by provider, operation, operation/schema version, subject and digest.
- Raw snapshots, derived features, analyses, their inputs, metrics, insights, assertions,
  events, share snapshots and parameter sets reject updates. Rebuilds insert new versions.
- Published analysis inputs retain their raw snapshots through restrictive foreign keys.
  Legacy raw-payload cleanup cannot reach tracker snapshots.
- Raw storage starts in PostgreSQL. URI slots permit a later retention-tier migration;
  no object store is provisioned. Such a migration must preserve digest/source identity.
- Profiles carry the active coherent revision. Rebuilt baselines, PBs and claims are staged
  by revision before a later service atomically publishes that revision.
- Ingest work has a unique dedup key, priority, `run_after`, leases and generation fences.
  Redis locks will reduce duplicate effort; the database controls unique observable records.

The schema checks do not prove worker fencing, atomic rebuild publication, canonical
translation, analytical correctness or API isolation. Their service-level tests remain required.

## Local verification

Use an isolated PostgreSQL 16 database that the test role may create schemas in:

```sh
export TEST_POSTGRES_URL='postgresql+psycopg://dota:dota@127.0.0.1:5432/dota_report_card'
make test-tracker
RUN_POSTGRES_MIGRATION_TEST=1 uv run pytest -q tests/integration/test_postgres_migrations.py
```

Each tracker test creates a random schema and drops only that schema. No live provider calls
are made. A missing PostgreSQL URL skips these tests in the general suite; `make test-tracker`
requires it, and the CI migration job supplies a real PostgreSQL 16 service.

The tests cover fresh/repeated migration, schema parity, populated legacy upgrade/downgrade
and persisted report reads, concurrent ownership and job identity, roster completeness,
terminal evidence, immutable sources, retention isolation, finite numbers, missing versus
measured zero, and `FOR UPDATE SKIP LOCKED`. A downgrade removes tracker data and is tested
only in disposable schemas. Applying migrations to production requires separate permission.
