# Prompt: adversarial QA of the Dota Tracker backend

You are Opus 5.5, acting as an independent QA engineer. Audit the Dota Tracker backend on branch
`codex/tracker-backend-foundation` (head `6b52ced` or later) in
`/Users/nikanakamanifesto/Documents/GitHub/dota-report-card`. Find real defects, prove each one with a
failing test, fix it, and leave the branch green. Your job is to break things, not to confirm
them. Two earlier agents (Sol, then Opus) built this code and also wrote most of its tests. Assume
some of those tests are tautological, too narrow, or built on helpers that skip the real code
paths.

## Read first

1. `AGENTS.md` (router plus the legacy operating contract; the legacy product is live in production).
2. `docs/tracker/architecture/IMPLEMENTATION-LEDGER.md`: what is claimed verified, owner
   decisions and blockers. Treat every "verified" claim as a hypothesis.
3. `docs/tracker/architecture/README.md` and ADRs 0001–0005, plus the algorithm annexes.
4. The feature SSOTs under `docs/tracker/*/SSOT.md` (product truth), and
   `docs/tracker/architecture/evidence/backend-acceptance-traceability.json`.
5. `services/api/app/tracker/README.md` (module map and the invariants the code relies on).
6. `docs/tracker/operations/README.md` (how to run everything).

## Environment

- PostgreSQL 16 on `localhost:55432` (database `tracker_test`), Redis 7.2 on `localhost:56379`. If
  they are not running, start them locally. Docker is not installed.
- Use these variables:
  ```bash
  export TEST_POSTGRES_URL=postgresql+psycopg://nikanakamanifesto@localhost:55432/tracker_test
  export TEST_REDIS_URL=redis://localhost:56379/0
  ```
- The tracker suite command is
  `.venv/bin/pytest -q -p no:cacheprovider tests/tracker tests/unit/test_migrations.py tests/contract`
  (about 6 minutes).
- Full-suite baseline at handoff: 1772 passed, 0 failed, 2 skipped (both opt-in live smoke tests).
  With `RUN_POSTGRES_MIGRATION_TEST=1` set, the suite takes about 8 minutes.
- There is no `timeout` binary. Run long suites in the background.

## Hard rules

- No deployment, no push, no merge. Do not touch production infrastructure or data.
  Local commits on this branch are fine. End commit messages with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Never delete, move or clean `.local/`, `.env`, `apps/web/.local` or untracked files you did not
  create. Never run `git clean`. Never reset away existing commits. Never print secrets.
- Make zero live provider calls. STRATZ is forbidden: the IP-binding safety check has not been
  established. Use the recorded fixtures under `tests/fixtures/tracker/`.
- Do not change legacy tables, `/v1` routes, persisted reports, retention or frozen V6.1
  artifacts. After your changes, `scripts/generate_api_client.py` must produce no diff.
- Do not invent product values for open owner decisions (Profile §12 claim parameters, trend
  thresholds, Pro depth, context parameter set, and the rest). Fail-closed behaviour is correct
  there. Treat it as a bug only if it is not fail-closed.
- Golden fixtures in `tests/fixtures/tracker/mobile-v1/` are compared, never overwritten to make
  a test pass. If a fixture encodes a bug, explain the contract error and add a new versioned
  fixture set. Alternatively, regenerate the unreleased v1 set with an explicit justification in
  the commit. Never silently re-baseline.
- Recruit Sonnet subagents for mechanical work (running suites, grep sweeps, writing
  straightforward regression tests). Keep reasoning about correctness in the main agent.

## Method

1. Establish the baseline by running the tracker suite and `scripts/tracker_traceability.py --strict`.
2. For each area below, read the code path end to end. Write an adversarial test that drives it
   through the real entry points (jobs, workers, mobile HTTP), not only through
   `tests/tracker/builders.py` shortcuts. Check what the builders skip; any path that only the
   builders exercise is unproven.
3. For each defect: failing test first, then the minimal fix, then rerun the affected tests and
   the full tracker suite.
4. Record each defect in the ledger under a new section *Independent QA — <date>*: symptom, root
   cause, fix commit, test name. Record areas you checked and found sound, with the evidence. Do
   not inflate either list.

## Crucial areas to double-check

Ranked by the damage a hidden bug would do.

### 1. Single finalization point and index recomputation (`finalization.py`, `history.py`)
- Per-bucket ordering by `(provider_started_at, match_id)`: ties, equal timestamps, and a match
  admitted late at an older position (bootstrap refill, backfill, recovery, READMIT).
- `recompute_indexes` runs after the READY flip and rebuilds baselines and PBs from **all
  entitled READY rows**. Check that it cannot read an in-flight non-READY row, a row from the
  other bucket, or an archived profile's rows.
- Live work waits only on earlier LIVE links (`_prior_pending`). Check that this cannot publish a
  live match whose baseline window is missing a settled earlier match, and cannot deadlock.
- NEW_PB is emitted only for LIVE origin and only on a true new PB. Check that no rebuild,
  backfill or readmission can emit a READY or NEW_PB event or push.

### 2. Entitlement above data (`scope.py`, `entitlement.py`, `rebuild.py`)
- Free = BOOTSTRAP plus everything on or after `original_linked_at`; Pro = all. Check boundary
  timestamps (exactly at link time, timezones), relink and Steam switch (which `original_linked_at`
  applies?), and Pro to Free expiry mid-rebuild.
- Every history, baseline, PB, insight comparator, Profile and mobile read must go through
  `scope.entitled`. Grep for any query on `account_matches`, `analyses`, `baselines` or
  `personal_bests` that bypasses it.
- Scope rebuild idempotence: run it twice and confirm identical rows are reused, the revision
  bumps once, and there are zero provider calls.

### 3. Concurrency, leases and fences (`jobs.py`, `account_lifecycle.py`, `worker.py`)
- `authorized_job` lock order user → profile → job, lease expiry and generation checks. Try a late
  worker result after deletion, after a Steam switch, and after lease takeover. It must not commit.
- Duplicate Celery delivery, a crash between the provider response and publication (evidence must
  be persisted first and replayed without refetch), and `SKIP LOCKED` claim fairness.
- Real multi-process races: two workers finalizing the same bucket, and a rebuild racing a live
  finalization.

### 4. Immutability and rebuild determinism (`rebuild.py`, `tracker_reject_mutation` trigger)
- Confirm the trigger covers every table the ledger says it does, and that no code path does
  DELETE+INSERT to get around it where history must be kept.
- Methodology and parameter-set rebuild closure: only stale buckets from their earliest stale
  point; a failure midway keeps the previous coherent state (a single transaction).
- `inputs_digest` must include everything that changes the output (role correction, context
  terms, parameter set version, scope). A missing input means stale rows get reused.

### 5. Data access and bootstrap outcomes (`data_access.py`, `bootstrap.py`, `backfill.py`)
- `observe_history_page` marks BLOCKED on "a page that no longer returns an accepted in-window
  match". Hunt for false positives: pagination edges, a match aging out of the window, provider
  lag, Turbo/unsupported modes, an empty page after the last match. A false BLOCKED is user-facing
  and stops historical work.
- Six bootstrap outcomes (READY, READY_WITH_GAPS, NO_MATCHES_FOUND, NO_ELIGIBLE_MATCHES,
  DATA_ACCESS_BLOCKED, and so on): each is reachable, and none gets stuck in PENDING when coverage
  rows never settle.
- `SUMMARY_404` counts as discovered but not eligible. Check that the consequences are consistent
  across counts, coverage and mobile.

### 6. Provider admission and cost (`provider_control.py`, `provider_transport.py`)
- Capacity comes only from observed headers. Check the probe interval before a window is seen,
  that the processing lane costs 10 rate units and 1 billing unit, and that the P2 reserve works.
- Breaker and disable on 401/403 and IP-binding 403: no retry storm, and the state is shared
  across processes through Redis. Every call is accounted even on exceptions and timeouts.
- STRATZ never on the fresh path, and single-flighted. Verify statically and at runtime with
  fake transports.

### 7. Mobile API contract (`mobile_api.py`)
- Isolation: a foreign `ref`, share, device or operation gives 404, never data. Check opaque refs
  after switch and deletion.
- Idempotency keys: same key with the same body replays, a different body gives 409, keys are
  scoped per account, and concurrent duplicate requests are handled.
- ETag/304 correctness when the body changes but the revision does not, and vice versa.
- `/changes` signed cursor: tampering, a cursor from another profile, the `full_refresh` trigger,
  and microsecond precision across timezones. `/history` cursor bound to filters and revision.
- Readiness per block, closed enums, a measured zero versus N/A, and no provider or pipeline
  vocabulary leaking into responses or problem details.
- Reads never enqueue work and never reach a provider.

### 8. Identity, store and push (`authentication.py`, `steam_identity.py`, `app_store.py`, `store_api.py`, `notifications.py`)
- JWS verifier: alg confusion, a chain that is not three certificates, a wrong root, expired
  intermediates, missing marker OIDs, bundle/environment mismatch, and a notification whose
  nested transaction does not match. Refresh-token rotation and reuse detection.
- Steam OpenID `check_authentication` replay and claimed-id spoofing.
- Notifications: foreground suppression, stale cancellation, invalid-token clearing,
  retry-without-duplicate collapse keys. No push for non-LIVE origins.

### 9. Profile and context (`profile.py`, `context.py`, `population_parameters.py`)
- Profile checkpoints only at coherent points; an importing bucket keeps its prior checkpoint.
  Role-share hysteresis of ±3 pp at n≥30. Claims stay `CALIBRATION_PENDING` (fail-closed).
- Context `h` and `E` per observation. With no APPROVED parameter set, adjustment is exactly zero
  and performance is `NOT_READY`, never a fabricated value.

### 10. Migrations and the legacy boundary
- `0006`–`0015` are additive: upgrade from `0005` with populated legacy data, then check that
  legacy persisted reports still read. `EXPECTED_SCHEMA_REVISION` matches head. Downgrades, if
  defined, do not touch legacy tables.
- No tracker import leaks into legacy `/v1` behaviour, and no legacy retention job can purge raw
  evidence the tracker still references.

### 11. Test and evidence integrity
- Spot-check at least 25 `covered` traceability rules. Does the cited test actually assert the
  rule, or only something adjacent? Downgrade any overstated rule to `partial` with a note.
- Look for tests that monkeypatch the very code under test, tests with no meaningful assertion,
  and golden fixtures that encode wrong behaviour (for example a wrong readiness state or a
  missing PB). The golden fixtures were regenerated once in `5a2d4bd`; review that diff
  critically.

## Deliverable

- Commits on the branch, each fixing one defect with its regression test.
- An updated ledger section with the defects found, the areas verified sound, and any remaining
  doubts.
- Final gates: the full pytest run with both URLs and `RUN_POSTGRES_MIGRATION_TEST=1`, ruff
  (`services/api tests`), mypy, `scripts/check_docs.py`, `scripts/tracker_traceability.py
  --strict`, and the legacy API-client diff check.
- A completion report in the `AGENTS.md` §15 format, plus a ranked list of defects (severity,
  file:line, fixed yes/no) and the live provider call count (must be 0).
