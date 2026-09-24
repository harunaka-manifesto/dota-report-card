# Tracker backend runtime

Product meaning: [Tracker SSOTs](../../../../docs/tracker/README.md).
System behavior: [Tracker architecture](../../../../docs/tracker/architecture/README.md).
Implementation status: [ledger](../../../../docs/tracker/architecture/IMPLEMENTATION-LEDGER.md).

This namespace is under implementation. It provides the PostgreSQL schema, immutable
evidence persistence, summary/replay translation, summary roles, source materialization and controlled
provider transport. Authentication,
the match pipeline, analytical engines and mobile routes remain under implementation.

`ControlledTransport` wraps the existing OpenDota/STRATZ HTTP clients. It enforces shared
Redis admission, replay pacing, bounded response size/time, STRATZ single-flight and
PostgreSQL call/evidence persistence. Its provider key must be shared by every process using
the same credential. Never give replicas separate namespaces. An IPv4 client is used, but
stable public egress is still a deployment prerequisite. IP/credential failures disable the
provider until an operator resolves the cause and resets its shared state.

Quota capacities come only from named response-header windows. Until those are known,
one shared discovery read per probe interval is permitted; processing is withheld. Generic
headers with ambiguous window duration do not authorize guessed capacity. Reserve and
processing shares are operational policy. A Redis outage fails acquisition closed; it must
not affect persisted product reads. Network-ambiguous calls record rate reservations and
zero **known** billing units, not a claim that the provider charged nothing.

`materialize_snapshot` consumes supported stored responses, creates one canonical match
and ten players, and persists immutable per-source feature projections. It does not call
providers, link private profiles or finalize analysis. Canonical summary fields retain the
first accepted facts; later conflicting observations remain separate and add explicit
quarantine paths. Product analysis must apply those dependency paths before publication.
Replay checkpoint reconciliation is currently a pure transformation; worker wiring and
persisted multi-source dependency quarantine remain under implementation.

`enqueue_roster_links` creates generation-bound private link work for active owners.
`complete_link_job` publishes under the lease/identity fence and schedules one shared
P1 replay job for live matches, with an explicit availability delay from match end.
Historical links never schedule fresh processing. These functions do not classify
finalize analysis; those handlers remain pending. Summary role assignment is persisted
with materialization and applied when the account link is first created. Existing
links and user assertions are never overwritten by re-linking.

`enqueue_fresh_summary` deduplicates global P0 work. `acquire_fresh_summary` executes
one claimed job through ControlledTransport, reuses a valid persisted response before
fetching, then atomically materializes evidence, enqueues private link jobs, records the
acquisition pointer and completes the job. Internal publication failures retry from
stored evidence. Quota deferral does not spend the failure-attempt budget. Redis
single-flight guards duplicate delivery; PostgreSQL leases fence late publication.
`acquire_fresh_replay` reuses stored replay evidence, submits processing through the
separate bucket, then polls on a persisted bounded schedule. Submission/poll intent is
committed after admission and before HTTP; PostgreSQL rejects a duplicate step even
if its Redis lock disappears. Unknown submission outcomes poll rather than submit
again. Known 429 rejections preserve the remaining poll budget.

`ReplayPolicy` defaults are operational policy: six-minute minimum age, a conservative
60-day processing window (not a claim about Valve's exact horizon), five polls with
60/120/300/600/1200-second delays, and a two-hour elapsed bound from job creation.
Existing replay evidence is reused regardless of processing age. Terminal evidence
never finalizes private analysis or passively reopens an unavailable match.

`request_account_sync` debounces explicit foreground triggers per account and creates
one shared P0 job. `sync_account_page` reads one Turbo-inclusive page per claim, journals
each accepted/rejected source item, and commits discovery work with the next offset.
Only an empty terminal page advances the completed boundary; errors and page limits
leave the previous boundary intact. Missing source chronology remains null until full
summary acquisition. Successful call rows bind job, request and immutable snapshot,
so a publication retry reuses that exact page without another fetch. Foreground
authenticated routes, complete analysis and mobile integration remain pending.

`request_bootstrap_search` creates one profile-fenced P3 scan and separate Standard/Turbo
search ledgers anchored to the original Steam-link date. Each Turbo-inclusive history
page is retained before its 90-day-window candidates or rejections are journaled;
the cursor moves only with those writes. Search completion does not imply bootstrap
completion. Candidate eligibility, 30-per-mode selection, deep acquisition and
coverage settlement remain separate pending steps.

Historical deep batches split into two profile-fenced P3 jobs after an explicit
size, cost or deadline rejection. A singleton still uses bounded retries, and
unrelated provider failures do not masquerade as size evidence. A retained
HTTP-200 GraphQL error is never replayed as a successful batch.

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
`0007_tracker_discovery_journal` adds the global discovery journal and nullable call
correlation fields; pre-existing call rows retain their accounting without invented provenance.
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
export TEST_REDIS_URL='redis://127.0.0.1:6379/0'
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

## Priority workers

After local migrations, run `make tracker-worker PRIORITY=0` through `PRIORITY=3`
in four separate processes, plus **one** `make tracker-beat`. The tracker Celery
app is separate from the live report worker; do not change the report worker command.
Never put P3 and P0/P1 queues on the same worker. Start with one process per lane;
increase lane concurrency only from observed queue latency.

Beat publishes expiring wake signals every five seconds. Each worker claims one due
PostgreSQL job from its own priority with `SKIP LOCKED`, runs one bounded step and
persists its result. Successful steps wake their lane immediately when more work is
due; the five-second sweep is recovery, not a throughput cap. An omitted/expired delivery is recovered by the next wake;
an interrupted job is recovered after its 120-second lease. Celery has late acks,
worker-loss redelivery, prefetch 1, a 300-second broker visibility timeout and 90/110
second soft/hard limits. Replay waits remain `run_after` timestamps, never long
broker countdowns. Signals may duplicate; the database lease/step fences still apply.

`TRACKER_*` knobs in `.env.example` are operational tuning, not calibrated product
parameters. P3 pauses before claiming when P1 due depth/age crosses its threshold,
when either provider's named quota window or read/processing lane exceeds configured
utilization, or when quota is unknown. Under the same pressure, P2 gets one admission
per configured interval. P0/P1 do not share this pause gate. Provider rate admission
still applies to every physical request. To pause imports manually, set Redis key
`<TRACKER_NAMESPACE>:pause:p3` to `1`; delete that key to resume. Do not reset job
cursors. Never clear provider state as a way to bypass quotas.

`queue_metrics` reports due depth and oldest age per lane; future replay waits do not
inflate queue latency. Worker logs include priority and bounded outcome codes. Complete
metrics export/alarms and historical handlers remain pending.
The current dispatcher executes SYNC, SUMMARY, LINK_MATCH, REPLAY and ROLE_REFRESH; this is not
yet the complete analytical/finalization pipeline.

Failures from P0/P1 move to P2 in the shared rescheduler. Normal page continuation,
quota deferral and scheduled replay waits do not count as failures or change lanes;
P3 retries stay in P3. A subsequent P2 attempt may draw on the reserved quota share,
while all provider windows, lane capacity, pacing and circuit checks still apply.
This recovery permission is derived from persisted job priority/attempt count, not
from a client request.

## Provisional role classifier

`roles.py` assigns all five internal positions jointly within each team and exposes
only Carry, Mid, Offlane and Support. Summary inputs use within-team midranks of
commonly observed net worth, GPM, last hits and gold spent; tied ranks stay tied.
The assignment minimizes farm-rank distance, with canonical slot order as the stable
tiebreaker. Opponent economy, KDA, result, hero identity and native position labels
do not enter the score. Summary-only assignments always have low confidence.

Parameters are immutable `ROLE_CLASSIFIER` sets, initially
`role-assignment-provisional-1`: farm weight 1, lane weight 6, support weight 1,
confidence threshold 0.60. The margin score is not a calibrated probability.
Lane and relative ward behavior are accepted only by the explicit REPLAY scoring
profile; replay adapters and generation-fenced refinement publish this profile before finalization. The fresh
summary path does not consume parsed lane labels. Calibration remains a release gate.

Assignments retain profile, parameter version and a digest of actual classifier
inputs/parameters. Disputed farm measurements are withheld. A team with no common
observed farm field receives an explicit `MISSING_FARM_PRIORITY` failure, not invented
zeroes or an Unknown role; linking exposes this as an unavailable classification.
Measured zero is evidence. Re-linking preserves existing effective roles, revisions
and user assertions. Full correction APIs and deterministic rebuilds remain
under implementation. Shared internal assignments are not user corrections;
a correction must not mutate another tracked player's canonical assignment.

Replay acquisition selects an exact role assignment at evidence terminality.
`ROLE_REFRESH` jobs apply it only under the current user/profile/job fence and before
private finalization; assertions remain authoritative. Global internal positions
never change because one user corrects a role. A late account link schedules the
same selected refinement. Missing replay classification preserves the usable prior
assignment. Migration `0008_tracker_role_assignment` adds nullable global/private
assignment references and preserves pre-existing effective roles.

The replay adapter requires a parsed-evidence marker before accepting lane/wards.
[OpenDota's lane labels](https://github.com/odota/web/blob/master/src/lang/en-US.json)
map lane_role 1/2/3 to Safe/Mid/Off, not positions; roaming/jungle/unknown yields
no lane. OD observer+sentry counts and STRATZ ward-event counts agree for all ten
players in the retained pair. STRATZ's retained operation has no lane evidence.
Empty validated ward lists mean zero; absent, malformed or unsupported events
remain unavailable. Input projections include adapter version and source paths.

## Metric measurements

`metrics.py` calculates all 20 V1 role metrics from canonical facts, retaining raw
and comparison values, ratio components and explicit unavailable reasons. It uses
exact checkpoints, previous-to-current CS differences, team denominators, and
complete dead intervals. Eligibility, source conflict withholding, baseline/PB
selection and analytical publication belong to the pipeline and remain unfinished.

`events.py` translates stored replay events into versioned immutable features with
source paths. A negative level-one timestamp is valid pre-horn evidence; level six
must have a nonnegative timestamp. Missing streams are not empty streams. OpenDota
ward removal logs do not identify the destroyer, so they cannot supply vision
denial. Missing assists or level timing remain unavailable. STRATZ operation 1.1.0 selects realized death durations and tower damage
reports. Stored 1.0.0 snapshots remain readable, with these measurements unavailable
when the fields are absent. Retained raw death durations can disagree across providers or be incomplete;
the adapter preserves these facts without inventing intervals or reconciling values.

`history.py` computes previous-only median baselines and current Personal Best
ownership from explicit eligible observations. It keeps the 20-prior baseline
window separate from the full PB history, honours the five-prior gate and strict
ties, and never selects another role, bucket or metric. The caller supplies
entitled, finalized observations in chronology order and controls whether a
new live PB may celebrate. The PostgreSQL reader selects only finalized observations through active
analysis pointers and applies current Free/Pro history scope. Ordered
finalization, atomic entitlement revision and publication remain required
before this calculation is exposed.

`eligibility.py` is the match-level progression gate. It requires a supported
bucket, at least 600 seconds, a usable effective role, non-abandon evidence and
an explicit positive competitive-integrity verdict. A missing verdict yields
`NONE(INTEGRITY_UNKNOWN)` while factual Match Detail and available measurements
remain possible. A source-backed integrity verifier is still needed; neither
replay absence nor a missing metric is an automatic ineligibility reason.

`historical.py` consumes one retained STRATZ deep-batch snapshot inside a
current profile/job fence. It validates requested IDs and tracked roster
membership, materializes per-match source features, selects parsed replay
readiness, queues profile-specific link work, and records provider-specific
missing IDs without declaring the match nonexistent. A later returned row can
replace that source-missing acquisition. A P3 historical batch worker now runs one controlled STRATZ read for at most
50 IDs and reuses a durably recorded successful response after a crash.
History enumeration, batch-size fallback, coverage settlement and terminal
source resolution are still to be connected.
A malformed returned match is isolated with a database savepoint, leaving
valid sibling matches processable and recording an `INVALID_SOURCE` acquisition
for the affected match. The raw snapshot remains available for diagnosis.
