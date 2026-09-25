# Backend foundation implementation ledger

Operational evidence, not a product or architecture contract.

## Baseline and scope

- Base: `bd3289e4602303a7cdb9fccb3ea5bc482413f68f` (local main matched the attached audit).
- Branch: `codex/tracker-backend-foundation`.
- Authorized: BACKEND, DATABASE, ANALYTICAL (new tracker only), DOCUMENTATION, local INFRASTRUCTURE. No release/deployment.
- Existing untracked `docs/prompts/tracker-backend-foundation-goal.md` is user-owned and remains untouched.
- Current step: Phases C–H have verified partial checkpoints. Controlled providers, ordered finalization, Free bootstrap, tracker identity, isolated mobile routes, insight persistence, account lifecycle, entitlement boundary and an operations readout exist. Rebuild/correction, Profile publication, production integrations, full mobile inventory and goal-wide E2E evidence remain pending. Checkpoint entries below govern the exact status; none of these phases is declared complete.

## Gap status

| Gap | Work | Status | Code / verification / commit |
|---|---|---|---|
| G-1 | STRATZ batching | Partial | 50-ID deep batches and size/cost splitting; expanded selection/live ceiling unproven |
| G-2 | Shared fresh replay enrichment | Partial | Shared bounded path, terminal propagation and private finalization; full E2E matrix pending |
| G-3 | Persisted evidence readiness | Partial | Separate summary/replay states, immutable snapshots and private READY path; recovery/rebuild pending |
| G-4 | Classifier evidence profiles | Partial | Summary and replay profiles/refinement implemented; provisional calibration and correction remain |
| G-5 | Global matches and account links | Partial | Shared match/roster and generation-fenced links; full lifecycle pending |
| G-6 | Priority queues | Partial | Dedicated P0–P3 workers and pressure admission; E2E non-starvation gate pending |
| G-7 | Job deduplication and locks | Partial | Leases, source-call recovery and unique jobs; full pipeline duplicate-effect gate pending |
| G-8 | Sync and coverage | Partial | Durable discovery, match coverage and per-mode bootstrap outcome publication; interval/recovery E2E pending |
| G-9 | Rate and billing units | Partial | Separate Redis read/processing lanes and persisted units; live-limit evidence pending |
| G-10 | Turbo-inclusive history | Implemented, E2E pending | Explicit `significant=0` in tracker readers; see Phase C tests |
| G-11 | Snapshot provenance | Partial | Immutable source snapshots and final analysis lineage; rebuild lineage gate pending |
| G-12 | Trigger-based raw tiering | Trigger-deferred; policy review pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-13 | Independent versions and digest | Partial | Source/feature/role/parameter versions and digests exist; complete analysis rebuild gate pending |
| G-14 | Four-role public boundary | Partial | Internal positions map to four mobile roles; correction and full contract tests pending |
| G-15 | Account-match lifecycle | Partial | Private lifecycle, ordered finalizer and retained-evidence Retry; full E2E matrix pending |

## V1 capability work outside the gap list

Pending: production identity/store/push integrations; resumable Pro history; entitlement rebuild; full deletion/legal settlement; notification delivery; population context artifact; complete deterministic insight vectors; Profile claims; rebuild/correction; remaining mobile routes; seed and golden fixtures; PostgreSQL/Redis/Celery E2E; acceptance traceability. All 20 metric formulas are persisted, but calibrated adjustment and the rebuild gate are not complete.

## Engineering decisions

- Preserve deployment-coupled paths and legacy endpoints. Tracker behavior uses a distinct boundary.
- Tracker storage uses separate SQLAlchemy Core metadata and `tracker_` tables. `tracker_matches` is global across tracker accounts; legacy report extraction rows are not canonical tracker inputs. This avoids changing `0001_initial` (which imports live legacy metadata) or legacy raw retention.
- Account-relative analytical rows use the Steam-profile ownership boundary so archived state and a future owner cannot inherit private corrections. Canonical match evidence remains shared.
- Read-only AST import inventory covers 254 runtime modules. `stratz.deep` imports `player_analysis_v7.research.corpus`; research code cannot be blindly archived.
- Legacy purge removes old raw payloads regardless of published tracker use. Tracker storage must prevent that without weakening legacy retention.
- Baseline uses installed `.venv/bin` tools through Make overrides, avoiding dependency/network changes while establishing evidence.

## Owner decisions needed

All remain open; no product choices are inferred from missing UI content.

| Item | Options | Recommended implementation while open |
|---|---|---|
| Trend thresholds | Approve calibration artifact / defer labels | Nullable uncalibrated state with reason, no invented fifth trend |
| Role weights and confidence | Approve existing provisional values / calibrate | Version provisional configuration |
| Today’s Focus | Define content / omit | Honest absent slot |
| Challenges, achievements and XP | Contract mechanics / defer | Unavailable slot; no invented mechanics |
| Periodic reports | Define content and cadence / defer | Coverage plumbing only |
| Pro depth ceiling | Lifetime / approved cap | Unset configuration; no product limit invented |
| Recovery verification | Approve recovery method / defer | Collision and blocked routing boundary only |
| Email authentication | Password / magic link / OTP | Interface and test fake pending decision |
| Profile parameters | Approve calibration / retain provisional | Exact versioned SSOT provisional set |
| Home default bucket | Standard / Turbo / last selected | Require explicit selected bucket |
| Shared canonical rows after deletion | Retain shared evidence / legal removal policy | Record legal gate; remove user scope and fence jobs |
| Subscription renewal at deletion | Store-managed cancellation guidance / approved alternative | Verify platform capabilities; do not claim server cancellation |

## External blockers and environment

- PostgreSQL 16.15 installed locally. Redis 7.2.16 official archive SHA-256 verified and built under `/tmp/tracker-foundation-deps`; isolated services run only on localhost ports 55432/56379; Docker absent. Legacy PostgreSQL migration smoke, tracker concurrency and Redis integration checks pass (latest counts below).
- Web node_modules absent: web checks cannot execute until installed.
- STRATZ concurrent production token use not established: zero live calls permitted until safety is established or a dev token is available.
- Production identity/store/push credentials and approved calibration artifacts require later verification.

## Live provider call ledger

OpenDota reads: 3; replay requests: 1; STRATZ calls: 0. Total: 13 rate units, 4 known billing units. No deployment.

## Baseline test results

Commands: `make <target> PYTHON=.venv/bin/python PYTEST=.venv/bin/pytest RUFF=.venv/bin/ruff MYPY=.venv/bin/mypy`.

| Suite | Passed | Failed | Skipped | Outcome |
|---|---:|---:|---:|---|
| Full pytest | 1419 | 2 sandbox failures | 3 | Both failures are localhost bind denials; affected module rerun outside sandbox: 3 passed |
| STRATZ subset | 27 | 0 | 0 | Pass |
| Contract | 8 | 0 | 0 | Pass |
| Integration baseline | 8 | 0 | 1 | Initially skipped PostgreSQL; see explicit run below |
| PostgreSQL migration | 1 | 0 | 0 | Real PostgreSQL 16.15: clean and repeated upgrade; readiness passes |
| Backend ruff | — | 0 | — | Pass |
| Backend mypy | 254 files | 0 | — | Pass |
| Web lint/typecheck | — | — | — | Commands unavailable: node_modules missing |
| docs-check | — | 2 findings | — | Pre-existing classifier-domain ban flags tracker role doc and user goal |
| DNA catalog | — | 0 | — | Current |
| Taxonomy | 127 heroes | 0 | — | Pass |

Detailed local logs: `/tmp/tracker-foundation-baseline/`. The baseline import graph is checked in beside this ledger under evidence.

## Path mapping

R1: `#swiftMigration/` → `docs/tracker/` with `git mv`, preserving all 186 original files plus the three baseline evidence files. Five outward Markdown destinations repaired. Legacy documentation is fenced in place because tooling and historical references still use those paths.

Baseline checkpoint: `b4bf302`. R1 checkpoint: `ae9aaed`. Verification: documentation check passes, covering 57 tracker Markdown documents and 451 local destinations with zero missing paths; checker regression test and ruff pass. All 189 files from the baseline checkpoint survive relocation. Only seven tracker Markdown files changed (five outward-link fixes, archive README, and this ledger). A first filename audit mishandled Git-quoted Unicode names; rerun with NUL-delimited paths verified every file.

## Resume checkpoint

Baseline full suite completed; 305 acceptance/invariant rules inventoried as pending in `evidence/backend-acceptance-traceability.json`. R1 docs move/link audit is green. Mobile resource/state design is in `MOBILE-API-DRAFT.md`. Phase A has a frozen additive migration and 36 tracker tables. Next: Phase C providers (OpenDota history inclusion and canonical normalization first), then fixture pipeline. All application-level gap closures remain pending. Revisit algorithm companion sections before engine implementation.

Progress board: [Dota Tracker — Backend Foundation](https://app.asana.com/1/1218421734064975/project/1218700923418699). Two Luna agents created phase cards, 13 decision/blocker cards and seven E2E subtasks; no task is claimed implemented by creating its card.

## Phase A verification — 2026-09-22

- Migration `0006_tracker_foundation` is additive. Legacy table definitions, routes and retention code are unchanged. Application readiness expects the new head; deployment must migrate before starting this code. No deployment performed.
- Real PostgreSQL 16: **9 tracker checks passed, 0 failed, 0 skipped**. They cover schema parity; populated upgrade from 0005; repeated upgrade; downgrade/re-upgrade; both current and sanitized historical-production report reads through `/v1/reports`; parallel Steam ownership and work deduplication; complete roster requirement; immutable snapshots/assertions; source retention; independent readiness axes; terminal finalization; finite/null/zero values; SKIP LOCKED.
- Combined tracker + contract + integration + migration + legacy SQL repository/release checks: **38 passed, 0 failed, 0 skipped**. Database URL checks: **6 passed**. Ruff passes; mypy passes on 256 modules. Existing deprecation warnings remain.
- CI migration job now runs the real PostgreSQL tests; `make test-tracker` requires a PostgreSQL URL rather than silently using SQLite.
- No analytical algorithm, report JSON contract, frozen artifact, holdout or calibration changed. No claim that schema constraints alone prove the pipeline, identity services, deletion races, atomic rebuilds, or API isolation.
- API metadata generation exposed a baseline omission: `/v1/v7/reports/{report_id}` already exists at `bd3289e` (`api/routes.py:941`) but is absent from checked-in generated path metadata. Routes, main app and generator are unchanged. Refreshing that generated artifact is a separate maintenance checkpoint; it does not add an endpoint.
- Local dependencies: PostgreSQL 16.15 isolated data directory `/tmp/tracker-foundation-deps/pgdata`, localhost 55432; Redis 7.2.16 localhost 56379, built from the official SHA-256-verified archive. No production services used.

## Phase C checkpoint — acquisition transport

- Added `OpenDotaClient.get_history_page`: explicitly `significant=0`, bounded one-page reads, no legacy Free cap, no cached history, strict response validation. Detection and bootstrap will share this method. A malformed response is an acquisition failure, never empty coverage.
- Added `refresh_match`: one physical read independent of the immutable legacy match cache; rejects mismatched IDs. Tracker jobs will own scheduling/retries and immutable snapshot persistence. This does not yet provide distributed deduplication or quota admission.
- G-10 applies to all new tracker history readers. Audited existing history callers in legacy API/analysis and offline V6/V6.1 calibration tools; their frozen annual input contract is intentionally unchanged under goal §2.1. They are not tracker acquisition paths. Changing that legacy corpus is outside this goal's analytical authorization.
- `tests/tracker/test_opendota_acquisition.py` plus existing client suite: **18 passed, 0 failed, 0 skipped**; lint and client typecheck pass. Mock provider default deliberately excludes Turbo unless explicitly requested; replay refresh test proves stale legacy cache cannot hide new evidence. Live calls remain zero.
- Phase C remains in progress: normalization, paired evidence, persistence, historical batches, distributed accounting and circuit breakers still required.

### Immutable evidence persistence

`tracker/evidence.py` inserts content-addressed snapshots in the caller's transaction, separating provider, operation/schema version, subject and digest. Identical concurrent writes return the existing snapshot ID without mutating fetch time or provenance; changed content creates a new snapshot. Strict JSON rejects nonfinite and unsupported values instead of coercing them. PostgreSQL concurrency plus acquisition/client checks: **20 passed, 0 failed, 0 skipped**; lint/typecheck pass.

Environment correction on continuation: the previous `/tmp/tracker-foundation-deps` directory no longer exists, so its PostgreSQL/Redis processes are unavailable. The first evidence run reported **19 passed, 1 setup error** (connection refused). Recreated isolated PostgreSQL 16 at `/tmp/tracker-foundation-pg-current`, localhost 55432, UTF-8 database `tracker_test`; the rerun above passed. Redis must be reprovisioned before its integration gates; Asana availability card reopened accordingly. Prior test outcomes remain historical evidence, not claims about currently running services.

Read-only corpus inventory: the retained OpenDota architecture investigation contains six full OpenDota matches and 110 STRATZ match records, with no full-match ID overlap. The reported 13 summary-row overlaps are not full ten-player replay parity evidence. Continue searching other retained probe subsets; do not manufacture paired evidence or call providers to replace unavailable evidence without the budget/safety gate.

### Summary translation evidence

- Added `tracker/normalization.py` scoreboard translation, full-roster validation, canonical slots 0–9 and mode mapping; missing/malformed values retain reason codes, zero remains zero. Vendor roles, percentiles and unrelated identity blocks cannot cross the allowlist. This is the scoreboard subset, not yet the complete Stage-1 projection (items, draft, abilities and integrity inputs remain to add).
- Added immutable version-1 sanitized specimens in `tests/fixtures/tracker/provider-summary-v1`: 13 real same-match/same-slot/same-hero pairs and one real unparsed ten-player match shape. Raw private identifiers are removed; the full match ID is synthetic. Thirteen pairs prove exact jointly observed K/D/A, last hits, denies, GPM and XPM; this is not proof of net-worth series, event, coordinate or other replay equivalence.
- Reconciled G-4 factual error: read-only scan of retained investigation payloads found lane fields absent in 60/60 unparsed player rows (six snapshots), present/non-null in 50/50 parsed rows (five snapshots). Summary classification cannot use lane role. The provider capability doc §4.2 already classifies lane assignment as replay-class; lifecycle §6, dependency matrix §6 and foundation §5 still require an immediate role from available summary evidence. Dependent-document audit found no product rule requiring a change; accepted ADRs untouched.
- Four normalization tests pass, including paired agreement, ten-player/duplicate guards, null versus zero, Turbo routing and stats-versus-ingestion readiness. Ruff and tracker typecheck pass. Full replay normalization/parity and classifier remain pending. Live calls: zero.

### Stage-1 detail translation checkpoint

Extended the OpenDota summary allowlist with item/backpack/neutral slots, ordered ability IDs, validated draft picks/bans, hero variant, raw leave-status evidence, party size, team scores, first blood and end-state structures. Unknown optional evidence remains null; empty slots and empty arrays remain distinct. No role/eligibility verdict is inferred here. Five normalization tests pass. Before this extension, combined tracker PostgreSQL/acquisition/normalization, legacy OpenDota client and report-contract checks passed **41 tests, 0 failed, 0 skipped**; full backend ruff and mypy (258 modules) passed.

Current next steps: finish provider-neutral historical/replay translation and disagreement quarantine; add distributed admission/accounting and acquisition persistence, then fixture pipeline. Complete raw summary specimen coverage beyond the initial scoreboard subset. Redis reprovision/integration still pending. Asana Phase C remains In Progress. The complete backend goal is not yet satisfied.

### Historical transport checkpoint

Added versioned `GetTrackerMatchBatch` and `StratzClient.get_tracker_match_batch`: explicit `take`, 50 all-covered / 100 explicitly mixed ceilings, one uncached physical attempt, all ten players selected, raw response retained for snapshot persistence. Null/private history differs from an empty source page; unexpected/duplicate IDs and malformed pages fail closed. The frozen V7 deep query, eight-row collector and report analytical inputs remain unchanged. Their old cost arithmetic is legacy-only and will be fenced during R2–R4, not reused by tracker planning.

Tracker + legacy STRATZ client tests: **22 passed, 0 failed, 0 skipped**. Ruff and STRATZ mypy pass. New query expands the historical all-player evidence selection beyond the old measured own-player selection: the 50/100 values are conservative ceilings, not new live sizing evidence. Expanded-selection schema/memory/timeout verification and durable batch reduction remain required; do not call G-1 closed yet. STRATZ live safety remains unestablished, so no network calls were made.

### Shared provider control and real Redis integration

- Restored Redis 7.2.16 from the official release archive, verified against the official SHA-256 list, and built under `/tmp/tracker-foundation-redis`. Test-only server binds localhost 56379; no persistence or production service changes.
- `provider_control.py`: Redis WATCH/transaction admission shared across processes, header-sized named windows, separate read/processing capacity, held reserve, 10-unit processing accounting and globally paced processing requests. With unknown headers, only one bounded shared discovery read is admitted; processing waits. Remaining-only headers tighten learned limits. Repeated failures open a shared breaker; credential/IP failures disable acquisition pending operational intervention.
- `provider_transport.py`: wraps existing clients rather than replacing transport behavior. Whitelisted operations, pinned IPv4 family, distributed STRATZ single-flight, whole-attempt deadline and response-size bound. Raw successful object/array payloads and call accounting persist together in PostgreSQL before the caller receives a response. Invalid/oversized/timed-out evidence never becomes a success snapshot. No raw URL, credentials or response body enters logs.
- **8 real Redis/PostgreSQL tests passed, 0 failed, 0 skipped**: parallel initial probe, independent processing budget/reserve and pacing, remaining-only headers, shared circuits, existing-client integration, immutable raw persistence, correct `(10 rate, 1 known billing)` processing units, STRATZ concurrency/IP-binding, timeout and size bounds. Full backend ruff and mypy pass (260 modules).
- CI now provisions Redis 7 beside PostgreSQL 16 for tracker tests. `make test-tracker` requires both test URLs. Runtime docs describe shared credential namespaces and fail-closed unknown quotas.
- Not yet closed: durable job retry/claim fencing, crash-recovery from stored responses, batch-size reduction, all replay feature parity, and product API/pipeline wiring. The limiter's generic-header-only mode intentionally withholds processing rather than inventing a capacity; bounded live header verification remains outstanding. G-1, G-6/G-7 and full Phase C are not marked complete.

### Durable job scheduling checkpoint

- `tracker/jobs.py` adds transaction-owned idempotent enqueue, priority-specific `FOR UPDATE SKIP LOCKED` claims, expiring lease tokens, persisted cursor/retry checkpoints and bounded failure termination. Quota deferrals do not consume the failure-attempt budget. Reusing a dedup key for different work is rejected.
- Private publication must use `authorized_job`: user/profile generation, active ownership and current unexpired lease are checked while holding locks in user → profile → job order. Effects and completion/checkpoint commit together. Provider I/O remains outside this transaction. Deletion/switch services must use the same lock order when implemented.
- **4 real PostgreSQL tests passed, 0 failed, 0 skipped**: parallel enqueue and non-overlapping claims; priority isolation/paused claims; expired-lease takeover rejecting the old token; deletion generation rejecting late effects; persisted cursor resumption and bounded failures. Module lint/typecheck pass.
- Previous combined tracker + legacy provider + report-contract run: **72 passed, 0 failed, 0 skipped**, one existing deprecation warning. No live provider calls or deployment.
- This is scheduler storage, not a claim of finished Celery routing, P3 pressure policy or end-to-end pipeline. Those remain required next integration work, alongside remaining provider normalization and batch recovery.

### Bounded live OpenDota verification

One authorized history read using the existing test/evidence account, `significant=0`, limit 20 and 90-day window returned HTTP 200: **13 Turbo and 7 Standard rows**. Purpose: verify actual Turbo inclusion and quota-header format, not presentation QA. Cost: **1 read / 1 rate unit / 1 known billing unit**, zero replay requests. No payload identifiers, credentials or raw account data committed.

Observed quota header: `x-rate-limit-remaining-minute: 2999`; **no limit/capacity header**. The limiter initially required a capacity header and would have indefinitely withheld processing. Corrected initialization to use the observed named-window remainder as a conservative capacity lower bound. It does not infer a published plan ceiling. A regression test uses the exact header shape; **5 real Redis tests passed, 0 failed, 0 skipped**. STRATZ safety gate remains closed; no STRATZ live call.


### Paired replay checkpoints

- The bounded provider total is now **3 OpenDota reads + 1 processing request**
  (**13 rate units, 4 known billing units**), with **zero live STRATZ calls**. The
  paired OpenDota match was first unparsed, accepted processing, and had replay
  statistics at a later check. The observation does not establish exact processing
  latency. No further calls were needed for the offline normalization work.
- Added a sanitized real ten-player pair at `tests/fixtures/tracker/paired-replay-v1/`.
  Known summary facts agree, including the retained NONE/no-abandon translation.
  The STRATZ capture has `isStats=false` with positive `statsDateTime` and replay
  arrays, exposing and correcting the earlier overly strict AND gate. Either stats
  marker now permits field-level validation; ingestion time alone never does.
- `tracker/replay.py` normalizes exact net-worth, cumulative last-hit and stacked-camp
  checkpoints with source paths and a translation version. STRATZ last hits are
  interval deltas; campStack is cumulative and index 19 means 20:00. OpenDota uses
  explicit sample times and networth_t, never gold_t as a substitute.
- All ten players agree at 10:00 and 20:00 for these three series. Other real point
  differences remain in the fixtures; reconciliation withholds only conflicting
  known points and preserves both inputs. Missing deltas invalidate the subsequent
  cumulative prefix. Missing samples, malformed data and out-of-duration points
  never become zero or interpolated values.
- This is translation and in-memory conflict quarantine, not finished acquisition
  orchestration or persisted dependency quarantine. Event translation, remaining
  replay features, source binding, pipeline and all later phases remain required.
- Verification: **84 passed, 0 failed, 0 skipped** across tracker (real PostgreSQL
  and Redis), legacy provider clients and report contracts; one existing Starlette
  deprecation warning. Tracker lint/typecheck and documentation links pass.


### Canonical source materialization checkpoint

- `tracker/materialization.py` consumes registered inline snapshots rather than making
  provider calls. It validates the operation/schema identity and requested match, then
  serializes publication on the global match row. First summary materialization creates
  all ten players and the header in one transaction. It only advances to SUMMARY_READY;
  replay terminal state and private finalization belong to the still-pending pipeline.
- Every source produces immutable per-player summary/header/checkpoint projections, with
  source snapshot, provider/operation/schema, content digest and translation versions.
  Reprocessing the same source is idempotent. A later parsed source creates new feature
  rows without changing earlier missing values, first-ready time or source evidence.
- Cross-provider summary conflicts are persisted on the match as dependency paths while
  both source projections survive. No last-writer-wins scoreboard replacement. This
  alone does not close dependent analytical suppression: the analysis consumer and
  persisted multi-source replay reconciliation still need wiring.
- Four real PostgreSQL checks cover concurrent materialization (one match, ten players,
  ten features), immutable replay enrichment, persisted provider disagreement, and
  rejection of partial/mismatched/duplicate-batch evidence without partial match rows.
  Remaining: account links, durable acquisition job handlers, replay transitions,
  ordering, analysis and mobile API integration. No new live calls or deployment.
- Final combined check for this slice: **88 passed, 0 failed, 0 skipped** across
  tracker/PostgreSQL/Redis, legacy provider clients and report contracts. Tracker
  lint and mypy (9 modules), docs-check (474 links) and diff whitespace checks pass.
  Task-base scope audit shows no changes to the web app, legacy analytical runtime
  or frozen runtime artifacts. The complete backend goal remains unfinished.


### Profile links and shared fresh replay scheduling

- `tracker/linking.py` fans the stored ten-player roster out to active owned
  profiles as generation-bound LINK_MATCH jobs. It performs no provider calls
  and does not read entitlement. Publication uses the existing user/profile/lease
  fence, then locks the shared match and inserts the private link idempotently.
- A live link enqueues one global P1 REPLAY job by match ID and advances evidence
  to REPLAY_PENDING. The availability delay is explicit operational policy from
  match end, persisted in run_after. Neither per-user links nor Free/Pro duplicate
  the acquisition job. Historical links use their own acquisition route and do
  not enqueue fresh processing; terminal evidence never passively reopens.
- Existing links keep origin, role and analysis state. Missing or contradictory
  roster account identity cannot authorize a link. Four real PostgreSQL tests
  pass: concurrent Free/Pro users share one replay job; deletion and switch fence
  late publication; historical/terminal attachment preserves role state; absent
  and quarantined account identities cannot attach.
- This is storage/scheduling integration, not a completed Stage-1 API: effective
  role classification is still pending. Replay handlers, stored-evidence reuse
  before network requests, Celery dispatch, finalization/order, notifications and
  mobile consumers remain required. No additional live calls or deployment.
- Combined verification: **92 passed, 0 failed, 0 skipped** (tracker with real
  PostgreSQL/Redis, legacy provider clients, report contracts); one existing
  Starlette warning. Tracker lint/mypy (10 modules), docs links and whitespace
  checks pass. Full goal remains in progress, with no deployment/push/merge.


### Fresh summary acquisition handler

- `tracker/acquisition.py` creates global deduplicated P0 SUMMARY jobs. A claimed
  job uses the existing fresh OpenDota client inside ControlledTransport, so shared
  admission, bounded HTTP, raw persistence and call accounting cannot be bypassed
  by the normal execution path. No entitlement branch or STRATZ fresh fallback.
- Before network work, the handler reuses valid stored summary evidence. After
  provider success, canonical materialization, link-job fanout, acquisition source
  pointer and job completion commit together under the lease fence. An internal
  publication failure retries from the stored response, without source refetch.
- Quota deferrals persist run_after without burning failure attempts. Malformed
  summaries and internal failures have bounded retries. Duplicate execution of
  the same claimed job leaves the active worker's lease intact; it neither makes
  another request nor reschedules that active worker out from under publication.
- Six real PostgreSQL/Redis tests passed: fake HTTP through controlled transport
  to summary, link and shared replay scheduling; internal-failure recovery without
  refetch; quota deferral; malformed roster bounded failure; lease takeover with
  preserved raw but fenced publication; concurrent duplicate delivery.
- These tests use fake provider HTTP and real local storage. Live totals remain
  **3 OpenDota reads + 1 processing request, 0 STRATZ calls**. Exactly-once external
  network effects are not claimed across the unavoidable request/response-loss
  boundary. The stored-success/internal-failure boundary is now tested.
- Still required: replay handler and full telemetry extraction, detection/sync,
  historical batch recovery, Celery dispatch/priority policy, immediate roles,
  finalization/order, notification and mobile integration. This does not complete
  Phase C/D or the full backend goal.
- Combined regression: **98 passed, 0 failed, 0 skipped** across tracker with
  real PostgreSQL/Redis, legacy provider clients and report contracts. Tracker
  lint/mypy (11 modules), docs (474 links) and whitespace pass; one existing
  Starlette deprecation warning. No push, merge or deployment.


### Bounded replay acquisition checkpoint

- `tracker/replay_acquisition.py` implements the claimed P1 replay handler through
  the existing separate processing client and ControlledTransport. It checks
  stored valid parsed evidence before any call, including after internal failure.
  It persists terminal evidence and acquisition provenance without writing private
  READY, finalization, PBs or notifications.
- Policy is explicit/configurable: minimum age 360 seconds, conservative processing
  window 60 days, poll delays 60/120/300/600/1200 seconds, at most five failures and
  a 7200-second elapsed bound. The window is policy, not a discovered exact Valve
  horizon. Processing is submitted once unless a known 429 rejection permits a
  retry. An uncertain submission is reconciled by polling, never blind re-POST.
- ControlledTransport now has a guarded pre-send hook after quota admission. The
  worker commits a step claim/cursor before physical I/O. PostgreSQL cursor/lease
  checks prevent duplicate steps if the Redis lock disappears; the same guard is
  applied to summary reads. Quota denial does not create submission intent.
- The replay cursor preserves submission intent, poll count and next allowed time
  across crashes. Known 429 responses preserve poll budget; the elapsed bound
  stops indefinite quota waiting. Actual attempted request time comes from the
  provider call ledger, not merely from intent. Acquisition attempt counts use
  recorded physical calls. Terminal reasons distinguish exhausted checks, elapsed
  wait, out-of-policy age and source failure.
- Fourteen real PostgreSQL/Redis replay tests passed before the final combined run:
  submission/poll success; cached replay; missing replay terminality; ambiguous
  submission; quota-before-intent; young/old processing bounds; recovery after
  internal publication failure; GET/POST 429; elapsed limit; duplicate delivery
  with/without Redis lock; lease takeover between admission and HTTP.
- The initial integration attempt was not executed because automatic approval
  review hit an account usage limit. After the user's continuation, review
  succeeded and the real integration checks ran. This was an infrastructure
  review failure, not a safety rejection and not a passing test.
- No new live provider calls: cumulative totals remain 3 OpenDota reads plus one
  processing request, zero STRATZ calls. Still required: detection, historical
  recovery, Celery/pressure policy, roles, remaining telemetry/engines, private
  finalization/order, notifications and mobile API. Full goal remains unfinished.
- Final combined verification: **113 passed, 0 failed, 0 skipped** across tracker
  with real PostgreSQL/Redis, legacy provider clients and report contracts; one
  existing Starlette warning. This includes summary-read and replay-submission
  duplicate tests after deliberate Redis lock loss. Tracker lint/mypy (12 modules),
  docs-check (474 links) and whitespace pass. No deployment, push or merge.


### Foreground account discovery checkpoint

- `tracker/sync.py` implements explicit account-global debounced triggers, shared P0
  jobs and one Turbo-inclusive history page per claim. Concurrent triggers reuse the
  active job. It has no polling timer and no entitlement branch. Authenticated mobile
  entry points and queue delivery are still pending.
- Each page journals accepted/rejected items with its immutable source snapshot.
  Invalid IDs and out-of-window chronology get explicit reasons; absent chronology
  stays null and needs the full summary. Accepted matches share global summary jobs;
  existing canonical matches enqueue generation-fenced owner links.
- Journal, enqueue effects and next offset commit together. Only an empty page
  advances completed coverage; short pages continue. A page limit or source/internal
  failure preserves the last completed boundary. The explicit scope is widened at
  the provider during long interruptions, then filtered against the frozen job window.
- Migration `0007_tracker_discovery_journal` adds an account discovery table and
  nullable call account/job/snapshot/request correlation plus a lookup index. Calls
  and saved responses commit atomically. Existing 0006 call rows keep their original
  accounting with null new provenance. No legacy table is altered.
- A DB step claim before HTTP prevents duplicate delivery; a retry uses the exact
  job/request response even when snapshot content was deduplicated. This does not
  claim exactly-once network I/O if a process dies between HTTP and durable recording.
- Verification includes concurrent triggers, Turbo pagination through an empty page,
  invalid/missing chronology, atomic rollback recovery without refetch, duplicate
  delivery, bounded malformed/page-limit failure, shared matches across accounts,
  outage preservation, and populated 0006 upgrade/downgrade/re-upgrade.
- No new live calls: cumulative 3 OpenDota reads, 1 processing request, 0 STRATZ.
  No push, merge or deployment. Full goal remains active and unfinished.
- Combined verification: **124 passed, 0 failed, 0 skipped** across tracker, legacy
  provider clients, migration unit checks and report contracts on real PostgreSQL/Redis.
  Two existing deprecation warnings (Starlette, Alembic). Ruff, mypy (14 modules),
  docs-check (474 local links) and whitespace pass.

### Dedicated priority-worker checkpoint

- `tracker/worker.py` adds a separate Celery app for tracker jobs. Existing report
  worker startup and deployment commands are unchanged. Four named queues require
  separate worker processes; Make targets and `.env.example` document local setup.
- Beat sends expiring five-second wake signals, not provider-polling jobs. Each wake
  claims one due job in its priority from PostgreSQL. Existing SYNC, SUMMARY,
  LINK_MATCH and REPLAY handlers run through their existing fences. Long replay waits
  remain database timestamps. Late acks, worker-loss redelivery, prefetch 1 and
  soft/hard limits complement the 120-second database lease.
- P3 admission checks shared manual pause, due P1 depth/age and observed provider
  quota utilization before claiming. Both total and separate read/processing lanes
  matter: spare total capacity cannot hide a nearly exhausted read lane. Unknown
  quotas pause P3. P2 receives a reduced admission rate under the same pressure;
  P0/P1 have dedicated workers and bypass this backpressure gate, while their actual
  provider requests still require rate admission.
- Queue metrics exclude scheduled future work from latency; worker logs expose
  priority/outcome. Full telemetry export/alarms, retry demotion and historical/
  analytical handlers remain pending; G-6 and the full goal are not closed.
- Tests exercise P1 depth/age pressure, provider lane pressure, P3 pause/resume
  without losing stored work, handler routing and an actual Redis-backed Celery
  worker consuming duplicate wake messages. Initial four tests passed. The initial
  combined-run process handle disappeared before its result was retrieved; it is
  not counted as passing. A replacement combined run was launched.
- No new live provider calls, push, merge or deployment.
- Replacement combined run: **130 passed, 0 failed, 0 skipped**, two existing
  deprecation warnings. This includes real PostgreSQL, Redis and Celery delivery,
  legacy provider clients, migration unit tests and report contracts.
- Follow-up correction: completing a step now immediately wakes its lane when more
  work is due, avoiding a fixed one-job-per-five-seconds throughput ceiling. The
  periodic sweep remains the lost-message recovery path. Expanded Celery test
  requires two stored jobs to finish and the duplicate wake to become idle.
- Final affected worker rerun after that correction: **6 passed, 0 failed, 0 skipped**.
  Ruff, mypy (15 runtime/storage modules), docs-check (474 links) and whitespace pass.


### Retry-lane and quota-reserve checkpoint

- The shared `jobs.reschedule` now moves actual P0/P1 failures to P2. Existing P2
  stays P2 and historical P3 never gets promoted. Quota waits, replay schedules and
  page continuation preserve priority and do not spend the failure-attempt budget.
- ControlledTransport forwards an internal recovery flag to the existing provider
  gate. Summary, replay and sync handlers derive it from persisted P2 priority and
  a subsequent attempt. Recovery can use the reserve share but cannot bypass a
  provider window, empty read/processing lane, pacing, circuit or credential block.
- Regression coverage spans every priority and failure/wait combination, retained
  cursors and attempt counts, plus an actual failed summary retry that completes
  with protected quota while ordinary admission is denied. All acquisition/worker
  and legacy compatibility checks are rerun against local PostgreSQL and Redis.
- No schema or public report contract changes; no live calls, push, merge or deployment.
- Combined verification: **139 passed, 0 failed, 0 skipped** across tracker (real
  PostgreSQL/Redis/Celery), legacy provider clients, migration units and report
  contracts; two existing deprecation warnings. Ruff, mypy (14 tracker modules),
  docs-check (474 links) and whitespace pass.


### Summary role-classification checkpoint

- Tracker-only ANALYTICAL/BACKEND change: `roles.py` provides joint within-team
  position assignments and four-role projection. It does not import or change the
  legacy classifier. Summary farm midranks use only commonly observed fields and
  exclude KDA, result, opponent economy, hero identity and native position labels.
- Versioned provisional weights (farm 1, lane 6, support 1, threshold 0.60) are
  stored in immutable parameter sets. Same-version parameter drift is rejected.
  Summary-only classification is always low confidence; assignment margin is not a
  calibrated probability. Owner calibration gate remains open.
- Materialization persists ten summary-profile assignments before committing
  SUMMARY_READY. Account linking sets effective role or an explicit unavailable
  classification failure. Null/missing farm is never zero; tied observed zeroes
  remain evidence with deterministic low-confidence assignments.
- Disputed farm fields are withheld. Identity conflicts still block private linking.
  Re-linking cannot overwrite existing user assertions/effective role/revision.
  Internal assignments stay global; private role corrections must not mutate another
  player's assignment. Full correction/rebuild APIs are still pending.
- The pure scorer has an explicit REPLAY profile for canonical lane/ward behavior;
  provider adapters and pre-finalization replay rerun wiring are not yet implemented.
- Initial roles/link/materialization run: **14 passed**. Expanded suite includes
  actual stored user assertions and per-team quarantine. No live provider calls,
  legacy analytical changes, holdout/recalibration, push, merge or deployment.
- Combined verification: **146 passed, 0 failed, 0 skipped** on real
  PostgreSQL/Redis/Celery plus legacy provider clients, migration units and report
  contracts. Two existing deprecation warnings. Ruff, mypy (16 runtime/storage
  modules), docs-check (474 links) and whitespace pass. No calibration is claimed.


### Replay-role refinement checkpoint

- Replay-only role evidence adapter maps OD lane/observer/sentry facts and STRATZ
  ward events into canonical role inputs. All ten ward counts agree in the retained
  pair. STRATZ has no retained lane input; no location/position proxy is invented.
  OD lane codes verified against its official web language source; roaming/unknown
  remains absent. Unparsed payloads never supply these replay observations.
- Feature version now includes `role-evidence-1`; old projections remain immutable.
  REPLAY assignments bind their digest to the source feature digest and persist
  separately from SUMMARY assignments. Existing provisional classifier parameters
  remain uncalibrated; no native position or performance outcome becomes a role.
- P1 ROLE_REFRESH jobs use generation/lease guards, exact assignment identity and
  latest user assertion precedence. Finalized/active-analysis rows are unchanged.
  Missing replay classification keeps the prior usable assignment. No READY,
  history, PB, rebuild or notification effect is introduced.
- Migration 0008 adds nullable selected global/private role assignment references.
  Terminal replay selects one reference; late account links schedule that same
  refinement, closing the replay-before-link ordering gap. Existing private roles
  survive upgrade/downgrade/re-upgrade with null provenance rather than invented refs.
- Initial combined verification: **153 passed, 0 failed, 0 skipped** with real
  PostgreSQL/Redis/Celery, legacy clients, migrations and report contracts. Subsequent
  late-link and populated migration regressions run separately before commit.
- No live provider calls, holdout/recalibration, legacy analytical changes, push,
  merge or deployment. Corrections/rebuilds and remaining backend engines still pending.
- After the late-link fix: **36 passed, 0 failed, 0 skipped**, including populated
  0007→0008 upgrade/downgrade/re-upgrade, schema parity, old/current report reads,
  replay acquisition and refinement. Added a final publication guard for team farm
  disagreements discovered after the refinement was queued.
- Final refinement suite after that guard: **10 passed, 0 failed, 0 skipped**.
  Ruff, mypy (17 runtime/storage modules), docs (474 links) and whitespace pass.

### Metric formulas and replay event projection

- Implemented the 20 pure V1 metric calculators, keeping raw and normalized values
  separate and returning reasons for absent, malformed or zero-denominator inputs.
  Exact 10/20-minute checkpoints, cumulative series validation, unique opponent
  positions, inclusive early-kill and tower-credit windows are tested.
- Added immutable `replay-events-1` projections and source provenance to feature
  materialization; older feature versions remain immutable. Retained fixtures
  revealed valid negative level-one times, incomplete death durations and small
  provider death-duration disagreements. No gaps or disagreements are fabricated
  away. Canonical dead intervals must be complete and inside match time.
- OpenDota assists, exact level times and attributed ward destruction are not
  inferred. STRATZ operation 1.1.0 adds realized death duration and tower reports,
  verified by retained evidence; older 1.0.0 snapshots remain readable with absent
  inputs unavailable. No live verification is claimed for the expanded operation.
- Pure formula/adapter verification: **35 passed, 0 failed, 0 skipped**. Broader
  PostgreSQL/Redis/contract regression is recorded below after completion.
- Pipeline eligibility, conflict reconciliation, persisted analysis, baseline/PB,
  correction/rebuild, finalization and remaining goal phases are still pending.
  No live provider calls, legacy analytical changes, recalibration or deployment.
- Broader local regression: **191 passed, 0 failed, 0 skipped** (tracker,
  PostgreSQL/Redis/Celery, provider clients, migrations and legacy report contracts).
  After the additive query revision: **62 passed, 0 failed, 0 skipped**, including
  older-operation materialization, provenance, event formulas and STRATZ clients.
  Ruff, mypy (19 runtime/storage modules), docs (474 links) and whitespace pass.

### Progression history mechanics

- Added deterministic previous-only baseline and Personal Best calculations.
  Baseline selects the last 20 eligible measured priors in the exact bucket,
  role and metric identity; median needs five. PB searches the entire supplied
  eligible measured history, retains the earliest source on ties, honours the
  lower-is-better metrics and only marks a strict live improvement when the
  caller explicitly enables celebration.
- Focused tests cover the sixth-observation gate, chronology and match identity,
  Standard/Turbo and role separation, 20-vs-all-history distinction, N/A,
  ties, invalid values and silent rebuild. A PostgreSQL reader includes only
  READY active-analysis rows of the matching methodology, with Free bootstrap
  and post-link scope or Pro retained history. **6 passed, 0 failed, 0 skipped**
  including real PostgreSQL. Ordered publication, notifications and atomic
  entitlement revision switching remain open.

### Match-level eligibility boundary

- Added a fail-closed progression classifier for Standard and Turbo, exact
  600-second duration boundary, tracked-player leaver status, effective role,
  and explicit competitive-integrity verdict. Missing integrity proof produces
  `NONE(INTEGRITY_UNKNOWN)` rather than a fabricated normal-match decision.
- The current canonical summary exposes mode, duration, roster and leaver
  status but lacks source-backed remake/safe-to-leave verification. A verifier
  and source evidence must be established before calling this gate with VALID.
  Replay availability and individual metric availability are separate axes.
- Focused eligibility test: **1 passed, 0 failed, 0 skipped**. No finalization
  or public API claim rests on this classifier yet.

### Retained historical batch materialization

- Added a consumer for recorded STRATZ deep batches. It validates operation
  identity, requested match IDs and tracked roster membership before global
  materialization and profile link scheduling. Parsed historical evidence can
  make a shared match REPLAY_READY. Absent IDs record SOURCE_MISSING for that
  source only; later retained evidence can recover them.
- PostgreSQL verification: **2 passed, 0 failed, 0 skipped**. Tests cover
  duplicate delivery, one omitted ID, later recovery, link deduplication and
  rejection of duplicate/unrequested rows or unproven roster membership.
- The P3 worker now performs one controlled STRATZ read for at most 50 IDs,
  with generation/lease checks, provider accounting, stored-response recovery
  and rate-limit deferral that preserves attempt budget. Mocked HTTP plus real
  PostgreSQL/Redis worker verification: **11 passed, 0 failed, 0 skipped**
  across historical and worker tests. Batch-size fallback, account history
  enumeration, source-gap settlement and bootstrap completion remain pending. No live STRATZ calls were made.
- Each returned row now uses a PostgreSQL savepoint. One malformed source row
  records INVALID_SOURCE and leaves valid siblings materialized; neither
  malformed evidence nor a roster mismatch creates a private link. Retained
  batch checks: **3 passed, 0 failed, 0 skipped**.

### Durable Free-bootstrap search

- Added one profile-generation-fenced P3 `BOOTSTRAP_SEARCH` job with independent
  Standard/Turbo ledgers. The job scans Turbo-inclusive OpenDota history once,
  anchored to the original link date and its preceding 90 days. Each source row
  is durably journaled as a candidate or a reasoned rejection; unsupported modes,
  post-link rows and pre-window rows cannot become bootstrap candidates. The
  search cursor advances in the same transaction as the page journal. A retained
  page is reused after publication rollback rather than fetched again.
- Bootstrap, worker, sync and migration tests: **21 passed**; full tracker suite:
  **170 passed** on PostgreSQL/Redis. Ruff, mypy and docs checks pass. No live
  provider call. `search_finished` here means enumeration only:
  30-eligible-per-mode selection, source-backed integrity classification,
  summary/replay settlement and product outcomes are not yet implemented.

### Historical batch size fallback

- Explicit HTTP 413, response-size, timeout and GraphQL complexity/cost errors
  split a multi-ID historical batch into two deduplicated P3 children under the
  same profile generation. The parent completes only with both child jobs
  enqueued. Singleton and unrelated failures retain bounded retry behavior.
  Retained HTTP-200 error payloads are excluded from successful response
  recovery; malformed null `data` fails as invalid evidence.
- Historical/worker PostgreSQL/Redis checks: **15 passed**; ruff and mypy pass.
  No live provider calls. Provider-specific threshold behavior remains unproven
  until controlled live validation.

### Source-backed integrity projection

- `integrity-1` requires a normal/ranked lobby, ten humans, explicit no-leaver
  status for all ten players, and complete K/D/A rows. Nonzero leaver status
  (including OpenDota's "Left Safely" status 1), noncompetitive lobby or fewer
  humans is invalid; missing values remain unknown. This is a conservative
  inference from the [OpenDota status labels](https://github.com/odota/web/blob/master/src/lang/en-US.json)
  and retained paired OpenDota/STRATZ fixtures, not a claim that the providers
  expose a dedicated remake flag. The verdict and reason are immutable
  versioned features; progression still applies its independent duration,
  mode, role and tracked-player gates.
- Focused integrity/materialization/historical tests: **16 passed**; full tracker
  suite: **175 passed**. Ruff, mypy and docs checks pass. No frozen V6.1
  analytical source, artifacts or public report
  contract changed.

### Independent initial bootstrap acquisition

- Added a selected marker on source search items and an atomic first-wave
  selector after the 90-day scan. It takes at most 30 newest candidates per
  mode, increments each mode's discovered count independently and enqueues
  one P3 STRATZ deep batch per nonempty bucket. The selected rows and jobs
  commit with the search cursor; no match is counted eligible yet.
- Bootstrap/migration focused suite: **9 passed**; full tracker suite:
  **176 passed**. Ruff and mypy pass. Filling
  vacancies left by ineligible or unavailable first-wave candidates and
  settling the per-mode outcomes are the next dependent work.

### Historical summary fallback

- Every requested historical ID now gets a shared match stub before STRATZ
  acquisition, so omitted rows can retain SOURCE_MISSING evidence. Missing or
  invalid deep rows and a private STRATZ history response enqueue a generation-
  fenced P3 OpenDota summary job. The job reuses valid stored summary evidence,
  records its own provider attempt, and only queues a private bootstrap link
  after canonical roster membership is proved. An OpenDota 404 remains a
  source-specific gap, not proof the player never played the match.
- Mock-provider tests on PostgreSQL/Redis: **18 passed** across historical,
  fallback and bootstrap modules; full tracker suite: **180 passed**. No live
  calls. Per-mode eligibility/refill,
  replay-unavailable state and outcome settlement remain pending.

### 2026-09-24 continuation audit

- Reconstructed branch `codex/tracker-backend-foundation` at `2131027` (17 commits ahead of its remote tracking ref), with only the pre-existing, user-owned untracked goal copy. The separate `docs/evidence/v7-backend-completion-ledger.md` describes an older report-card effort; this ledger governs the tracker goal. The top status and gap matrix above were corrected from their Phase C snapshot to the verified checkpoints below.
- Existing disposable PostgreSQL 16 and Redis 7 test services still run on localhost 55432/56379. Socket access requires execution outside the workspace sandbox; no service data was removed or recreated. Current HEAD tracker suite: **180 passed, 0 failed, 0 skipped**, one existing Starlette deprecation warning, against both real services. This is the baseline for subsequent slices, not final goal verification.
- Asana project [Dota Tracker — Backend Foundation](https://app.asana.com/1/1218421734064975/project/1218700923418699): 5 tasks complete, 4 in progress, 29 incomplete total. Its phase task statuses agree with verified checkpoint evidence; a project-level note still describes the original Phase 0 state and should be refreshed with the next verified checkpoint.
- Next dependencies: per-mode bootstrap candidate refill and evidence/coverage settlement; persisted analysis and ordered finalization from existing pure metric/history modules; then identity/account services, mobile API, E2E, and release-independent documentation. Provider safety still prohibits live STRATZ calls. No deployment, push, merge, holdout, recalibration, or new provider call occurred during this audit.

### Trend evaluator checkpoint

- Added a pure ten-baseline-point, metric-level trend evaluator with polarity and N/A exclusion. It emits `INSUFFICIENT_HISTORY` before ten points and a nullable state with `UNCALIBRATED` when the approved, versioned per-metric threshold is absent. A test-only fixture exercises direction; production has no approved calibration artifact and therefore cannot publish Improving/Stable/Declining. The measured 1.25 CS floor applies to the current Carry CS@10 metric; the annex's other named floor metrics do not map directly to the V1 registry, so no substitute mapping was invented.
- Focused tests: **3 passed, 0 failed, 0 skipped**; ruff and mypy pass. Persisted history loading, artifact publication and mobile projection remain pending. No provider calls or legacy analytical changes.

### Paired checkpoint disagreement persistence

- Materializing a second source now compares its exact replay checkpoints with the immutable first source and adds observed point disagreements to the match's persisted quarantine paths. Neither raw snapshot nor derived feature record is overwritten; a missing point does not become a disagreement. The existing retained ten-player pair proves a non-checkpoint 420-second disagreement is recorded while agreed 600/1200-second values remain usable. Event-stream dependency comparison and downstream per-metric/insight quarantine remain pending.
- Real PostgreSQL materialization suite: **5 passed, 0 failed, 0 skipped**; ruff and mypy pass. No provider calls or legacy behavior changed.

### Pure context-adjusted expectation checkpoint

- Added the exact named 20-metric A/B/C/C*/D/E matrix, a draft-only lane score, window-relative hero/lane terms and caps, the floor and support gates, polarity-aware performance states, and fail-closed unavailable outputs. The paired hero for C* is derived from the validated opposing lane/position in the draft; callers cannot assert a different counterpart. Turbo receives zero adjustments and no lane label. No provider call or production parameter artifact was introduced.
- The annex §6 aggregate sentence says 9 B and 6 A, which sums to 22 metrics with its other classes. Its named rows and the active SSOT's named rows sum to 20 (8 B, 5 A); code and tests follow the row-level authority. This is a factual documentation discrepancy, not a new product classification.
- Focused tests: **9 passed, 0 failed, 0 skipped**; ruff and mypy pass. Population-parameter acquisition/validation/publication, stored prior-term projection and persisted analysis wiring remain pending.

### Per-mode bootstrap refill and tracker authentication primitives

- Selected Free bootstrap candidates now settle once after a source-backed private link is classified, or after the summary fallback reaches terminal unavailability. An ineligible/unavailable selection opens only its own mode's next newest candidate, preserving the 30-eligible target and profile-generation fence. This is candidate/eligibility refill, not overall bootstrap completion: replay coverage, final analysis, six outcomes and the single completion event are still pending.
- Tracker-only authentication primitives now verify fixed-issuer Apple/Google RS256 ID token signatures against their JWKS with PyJWT/cryptography, block identity collisions, issue hashed opaque sessions and rotate refresh tokens with reuse-family revocation. Email has only a sender interface and fake, per the open mechanism decision. The login path's explicit verification time now reaches the verifier. Steam OpenID, a full login challenge/nonce boundary, mobile routes and production credential/configuration validation remain pending; do not call the identity phase complete.
- Integrated affected suites (bootstrap, historical summary, linking, materialization, context, trend, authentication) against real PostgreSQL/Redis: **36 passed, 0 failed, 0 skipped**, one existing Starlette deprecation warning. Ruff and mypy pass on the changed modules. No live provider calls, legacy report contract changes or deployment.
- Broader pre-checkpoint regression on tracker, legacy provider clients, report contracts and migration units: **236 passed, 0 failed, 0 skipped**; two existing deprecation warnings. Full backend ruff and mypy pass (281 source files), docs-check passes (58 tracker documents, 474 links), and `git diff --check` passes. This is a regression gate for the current working tree, not final goal E2E evidence.
- Follow-up guard: context evaluation rejects a metric under another role. The PyJWT verifier and role guard together pass **14 focused tests** with real PostgreSQL, ruff and mypy. Asana Phase E/F notes and a yellow project status update were published from verified evidence; tasks remain in progress.

### Ordered tracker finalization and terminal historical evidence

- Added one profile-generation-fenced `FINALIZE` job. Shared replay terminality enqueues private work; the private transaction selects one immutable feature projection, applies the final replay role or latest assertion, evaluates progression and all metrics for that role, stores baseline-at-the-time/PB state, source lineage and an inputs digest, and moves the account match to READY once. Live work waits for that mode's bootstrap and for earlier unresolved same-mode links. Repeated work finds READY and produces no duplicate analysis or PB event. Terminal replay absence produces reasoned N/A metrics, not an unavailable match. A finalization failure that exhausts retries moves to ACTION_REQUIRED.
- Link lifecycle now remains WAITING_FOR_PROVIDER until evidence terminality. Coverage checkpoints store per-profile, per-mode SUMMARY/REPLAY KNOWN/PENDING/GAP at the source match timestamp and cannot regress KNOWN to PENDING. An unparsed historical deep row or terminal OpenDota fallback records REPLAY_UNAVAILABLE, enabling summary-only finalization. A terminal 404 candidate can settle without a fabricated account link. Free bootstrap outcomes wait for selected eligible analyses and coverage, and the finalizer calls settlement inside the publication transaction.
- Affected PostgreSQL/Redis suites: **50 passed, 0 failed, 0 skipped** across finalization, bootstrap, linking, replay, historical and worker checks. Ruff and mypy pass on affected modules. No provider calls. This is a first persisted pipeline checkpoint, **not** Phase D/E/F closure: complete insight cards, profile claims, notification outbox/delivery, complete coverage intervals, role correction/rebuild, and the end-to-end matrix remain required. The current READY path lacks those effects and must be completed before release.
- Independently verified Steam OpenID service/challenge/Redis nonce and atomic first-profile bootstrap enqueue are committed at `1c551c2` and `a7420a4` (10 focused PostgreSQL/Redis tests, no provider calls). Authenticated mobile routes and production callback configuration remain pending. Bootstrap per-mode outcome settlement is committed at `80445dc` (8 focused tests); root added the terminal-summary-absence regression and finalizer call described above.

### Isolated mobile boundary checkpoint

- Added an additive, separate `/mobile/v1` FastAPI application with its own typed OpenAPI document. Its first contract covers bearer sessions, account and identity methods, Steam challenge/verification, sync and readiness, device registration, per-mode bootstrap/coverage, Home in a client-supplied time zone, opaque match-detail references, scoped history cursors, and metric progress. Legacy `/v1` report routes and payload schemas are untouched. A public UUID match reference is introduced by additive migration `0011`; canonical/provider match IDs are not exposed in these mobile responses.
- Idempotency rows back Steam link start/completion, identity attach, and sync. Free/Pro read scope is applied above persisted match data. Absent Focus/Challenge and uncalibrated trends stay explicitly unavailable. This is a **partial Phase G checkpoint**: Profile, correction/retry, entitlement, switch/deletion, incremental changes, full Stage-2 insight projection, golden fixtures, local seed and mobile E2E remain open. The exact authentication POST idempotency convention also remains to be settled.
- Focused mobile/Steam/auth integration tests against local PostgreSQL and Redis: **21 passed, 0 failed, 0 skipped**. Migration tests including clean/repeated PostgreSQL smoke: **11 passed**. Ruff and mypy pass on the changed mobile/identity modules. No provider calls, deployment, push or merge.

### App Store entitlement boundary checkpoint

- Added a tracker-only signed transaction/Server Notifications verifier protocol,
  deterministic fake verifier, immutable transaction-to-account binding,
  linked-Steam purchase gate, stale-update protection, expiry/refund/revoke
  state, and a revision-scoped entitlement rebuild request. Pro activation is
  withheld until both Free mode bootstraps are terminal. `complete_scope_rebuild`
  publishes scope and revision together only after the caller's stored-data
  rebuild is coherent; a refund/expiry cancels pending activation and requests
  a Free-scope rebuild. Cached subscription rows and retained history are not
  deleted. `reconcile_entitlement_scope` is the hook for bootstrap settlement
  and transaction refresh.
- PostgreSQL purchase/foundation gating, atomic scope publication, refund,
  expiry fencing, cached subscription retention and account-link checks: **4
  passed**. Ruff and mypy pass. Production Apple JWS signature-chain
  verification, the operation worker that rebuilds derived state, mobile
  transaction/webhook routes and notifications remain unimplemented; this is
  not production App Store verification or entitlement completion. No provider
  calls, deployment, push or merge.

### READY event and outbox checkpoint

- The single finalization transaction now records one deduplicated `MATCH_READY` event for a live match. Imported/bootstrap matches do not emit it. Device permission and account notification choice gate only push-outbox creation, never finalization or the in-app event. Pending READY events for an account/profile coalesce into one outbox bundle; Steam switching cancels its old pending bundle. A delivery adapter rechecks active account/profile generation and permission before sending with the stable outbox dedupe key; revoked permission suppresses the bundle without changing the match.
- Real PostgreSQL tests for live/import distinction, no retroactive enqueue, duplicate finalization, coalescing, delivery and revocation: **10 passed, 0 failed, 0 skipped** across notifications, finalization and lifecycle. Ruff and mypy pass on the affected modules. This is not notification completion: a production APNs transport, worker dispatch, foreground signal/suppression and cross-device failure handling remain to be implemented and verified. No live push or provider call occurred.

### Profile claim lifecycle foundation

- Added `tracker_profile_claim_checkpoints` as an additive migration and advanced the application schema readiness head. Each account/bucket/scope/claim/version has a generation-fenced latest state, prior evidence snapshot, lifecycle checkpoint and bounded input digest. It is separate from existing Profile report rows and leaves legacy reports untouched.
- Added a deterministic CANDIDATE → CONFIRMED → FADING → RETIRED state machine with explicit versioned persistence-gap input, monotonic checkpoint enforcement, silent candidate discard, evidence-window/sample validation (≤200 match references), and fail-closed eligibility/coverage checks. Current evidence requires its actual window, sample references/count, aggregates, threshold crossings and player-facing coverage state. The repository does not publish claim candidates yet: deriving claim-specific enter/exit signals, evaluating these checkpoints in finalization, reconstructing coherent visible claim history, and serving Profile remain integration work.
- Goal SSOT §12 says Profile numeric parameters are provisional and need development-corpus calibration. Its active claim lifecycle specifies a persistence gap but no numeric value; the superseded archived profile document is not promoted to authority. Therefore policy gap stays explicit and versioned, test values are test-only, and calibration remains a pre-release gate.
- Focused pure/PostgreSQL tests plus migration contract: **9 passed, 0 failed, 0 skipped**; ruff and mypy pass. Migration used an isolated clean PostgreSQL schema. No provider calls or legacy report changes.

### Persisted insight checkpoint and migration parity repair

- The ordered finalizer now derives the versioned insight result from its selected immutable provider snapshot and all ten retained positions inside the publication transaction. It stores contract version, status and at most three cards under the active analysis. The isolated mobile match DTO exposes readiness, reason, template ID and JSON slots without generated copy. A progression-ineligible match and any source disagreement withhold cards; missing source inputs fail closed. The latter currently suppresses all cards rather than only dependent ones until a card-level source dependency map is verified.
- This is a partial §12.5 integration: history comparators are not yet supplied from retained prior insight evidence, several annex golden vectors lack end-to-end candidate fixtures, and the mobile slot schema is still generic JSON rather than candidate-specific typed slots. No claim of complete insight semantics or calibrated parameters is made.
- The first full tracker suite after migration `0012` found one schema metadata mismatch (249 passed, 1 failed). Adding the additive checkpoint table to `tracker.schema.metadata` repaired it; focused metadata/Profile and finalizer/mobile tests then passed (**6** and **10** respectively), followed by **6** finalizer disagreement tests. The full tracker suite must be rerun after all integration edits. No provider calls, push, merge or deployment.

### Archived Steam relink isolation

- Migration `0013` removes only the obsolete per-user/Steam pair uniqueness. Existing partial unique indexes still allow at most one active profile per user and Steam account. After the 90-day cooldown and completion of current bootstrap/history work, a verified switch back to a previously used Steam ID creates a new profile and Free bootstrap; the archived profile and its prior history stay isolated. An unsettled mode bootstrap now blocks switching even if a search job is no longer running. Pending old-profile notification bundles are cancelled by the earlier lifecycle checkpoint.
- Real PostgreSQL switch, migration-head, clean/repeated migration and metadata checks: **9 passed, 0 failed, 0 skipped**; ruff and mypy pass. The mobile verified-switch route and subsequent Pro backfill remain required. Downgrading after a relink with duplicate archived `(user_id, account_id)` pairs requires resolving those duplicates before reinstating the old unique constraint. No provider calls, push, merge or deployment.

### Verified mobile Steam switch boundary

- A switch-specific Redis challenge namespace now prevents a normal first-link assertion from authorizing a switch. The mobile API exposes account-wide cooldown/import preflight plus idempotent Steam switch start/completion; completion verifies the exact callback and one-use nonce through the server-side assertion verifier before the account lifecycle transaction archives the old profile and starts a new bootstrap. Replaying the same idempotency key returns the same result without another switch. Target ownership and same-account checks remain inside the locked transaction.
- Focused mobile/Steam/lifecycle PostgreSQL/Redis tests: **21 passed, 0 failed, 0 skipped**. Ruff and mypy pass. A production Steam callback configuration is still required; tests used a fake verifier and made no live Steam call. Pro backfill after the new Free foundation and full mobile/E2E verification remain open.

### Isolated operations readout

- Added a separately mounted `/internal/tracker` FastAPI application requiring a configured operations token. Without a token it returns 503; invalid tokens return 401. It reads database-backed P0–P3 due depth/age and failures, provider calls/errors/429s/rate units, coverage intervals and summary/detailed/analysis P50/P90/P99 readiness spans. Its schema is separate from both mobile and legacy `/v1`, and it performs no provider call.
- Local PostgreSQL operations plus legacy API contract tests: **5 passed, 0 failed, 0 skipped**. Ruff and mypy pass. This is partial Phase H observability: retry-reason distributions, breaker state, cost attribution and a controlled worker deployment/non-starvation proof remain to be completed.

### Retained-evidence manual Retry checkpoint

- The isolated mobile API now accepts an idempotent, account-scoped Retry for ACTION_REQUIRED and UNAVAILABLE matches. It reopens the existing private finalization job and, when a live match has unresolved evidence, reopens failed shared replay work in the P2 recovery lane. The request itself performs no provider I/O; finalization reuses retained snapshots. READY and other non-retryable states reject the action, and another account receives 404. Retry status is cleared on READY, role-unavailable and exhausted finalization outcomes.
- Focused real-PostgreSQL tests cover failed-job revival, finished UNAVAILABLE recovery after stored role evidence changes, mobile idempotency/IDOR, replay-first recovery and zero provider calls during request: **4 passed**. Finalization regression: **6 passed**. Ruff and mypy pass. The full tracker, migration and legacy API contract suites passed **270 tests** with no failures after this edit. This is partial Phase D Retry: historical acquisition failures, interrupted in-flight recovery and the full §11.2 matrix still need integration evidence.

### Bootstrap-to-entitlement reconciliation and stale-operation fence

- Overall Free-bootstrap settlement now reconciles an already verified, account-bound Pro purchase in the same profile-locked transaction. A purchase made during bootstrap requests one pending Pro rebuild when both modes become terminal; duplicate settlement does not create another operation. An opposite store update cancels a pending scope operation even when the newly desired scope equals the currently published scope.
- Scope publication now locks user → active profile → operation, refuses a deleted account or operation from an archived profile, and checks the current signed entitlement for both Pro and Free targets. An expired operation is committed as CANCELLED before the error returns, so it cannot block later lifecycle work or publish a stale scope. This fixes a prior rollback of cancellation on error.
- Real PostgreSQL and Redis entitlement/bootstrap suites: **15 passed, 0 failed, 0 skipped**. Ruff and mypy pass. The full tracker/migration/legacy contract regression passed **270** before this edit; it must be rerun after the next integration checkpoint. The actual retained-data scope rebuild worker, App Store production verifier and mobile/webhook routes remain pending; no scope activation is claimed from this handoff alone. No provider calls, push, merge or deployment.

### Mobile deletion boundary

- The isolated mobile API now exposes `DELETE /account`. It invokes the existing immediate deletion fence, removes private profile and session state, and returns only the deletion-pending state; subsequent use of the revoked bearer token fails authentication. The existing legal/store policy gates remain internal and unresolved rather than being promised to the client.
- Real PostgreSQL mobile/account-lifecycle tests: **11 passed, 0 failed, 0 skipped**, including an in-flight private job that cannot publish after deletion and an unaffected second account. Ruff and mypy pass. This does not resolve shared canonical-row retention or App Store auto-renewal policy; both remain owner/legal decisions.

### Shared provider-control operations visibility

- The authenticated internal summary now reads Redis provider circuit state and the P3 pause flag alongside its database metrics. It distinguishes unknown, open, disabled, closed and Redis-unavailable states and reports the bounded remaining open time and non-secret failure code. This read performs no quota admission or provider call.
- Real PostgreSQL/Redis operations and legacy API contract checks: **6 passed, 0 failed, 0 skipped**. Ruff and mypy pass. Remaining Phase H gaps include retry-reason distribution, cost attribution, controlled Celery priority/non-starvation proof and production worker wiring; this card stays in progress.

### Retained retry and replay failure visibility

- The isolated operations summary groups current job `last_error` values by job type, replay-unavailable terminal reasons, and attempted versus retried job counts by type. These are retained current-state counts, not a lifetime failure history. It makes no provider call and does not change mobile or legacy APIs.
- Real PostgreSQL operations and legacy API contract checks: **11 passed, 0 failed, 0 skipped**. Ruff and mypy pass. The first test fixture violated the existing ten-player roster constraint; the fixture was corrected and rerun. Cost attribution, failure-rate time windows, controlled Celery priority/non-starvation proof and production worker wiring remain open.

### Provider usage attribution

- The internal operations summary now groups persisted provider calls and billed/rate units by provider operation and the owning job's type/priority. Calls whose job no longer exists are explicitly unattributed. This is unit accounting; no price or currency conversion is invented.
- Real PostgreSQL operations and legacy contract checks: **11 passed, 0 failed, 0 skipped**. Ruff and mypy pass. The broad tracker/migration/legacy contract regression at the previous checkpoint passed **275 tests**. A proposed two-consumer Celery in-process test failed because Kombu's test hub cannot poll concurrently (`RuntimeError: concurrent poll() invocation`); that invalid test was removed without claiming non-starvation. A separate-process proof remains required. No provider calls, push, merge or deployment.

### Separate-process priority proof

- A local integration test launches distinct real Celery P3 and P0 processes on Redis queues backed by the same PostgreSQL schema. It holds a P3 profile row lock after the P3 job is claimed, then verifies that the independent P0 worker completes its fresh link job while P3 remains running. Queue names are isolated and subprocesses are terminated after the check. This proves local process separation under contention, beyond an admission-policy unit assertion.
- Local PostgreSQL/Redis worker suite plus legacy contract checks: **15 passed, 0 failed, 0 skipped**; ruff and whitespace checks pass. No provider calls. Production worker process configuration and deployment behavior remain unverified; no deployment, push or merge.
