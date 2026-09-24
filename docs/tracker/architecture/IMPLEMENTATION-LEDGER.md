# Backend foundation implementation ledger

Operational evidence, not a product or architecture contract.

## Baseline and scope

- Base: `bd3289e4602303a7cdb9fccb3ea5bc482413f68f` (local main matched the attached audit).
- Branch: `codex/tracker-backend-foundation`.
- Authorized: BACKEND, DATABASE, ANALYTICAL (new tracker only), DOCUMENTATION, local INFRASTRUCTURE. No release/deployment.
- Existing untracked `docs/prompts/tracker-backend-foundation-goal.md` is user-owned and remains untouched.
- Current step: Phases C/D in progress: controlled providers, summary/replay handlers and foreground account discovery. Phase A schema, baseline, R1 and API design are committed. Full pipeline, analysis and mobile wiring remain pending; no implementation gap is claimed closed.

## Gap status

| Gap | Work | Status | Code / verification / commit |
|---|---|---|---|
| G-1 | STRATZ batching | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-2 | Shared fresh replay enrichment | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-3 | Persisted evidence readiness | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-4 | Classifier evidence profiles | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-5 | Global matches and account links | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-6 | Priority queues | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-7 | Job deduplication and locks | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-8 | Sync and coverage | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-9 | Rate and billing units | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-10 | Turbo-inclusive history | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-11 | Snapshot provenance | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-12 | Trigger-based raw tiering | Trigger-deferred; policy review pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-13 | Independent versions and digest | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-14 | Four-role public boundary | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |
| G-15 | Account-match lifecycle | Pending | See IMPLEMENTATION-GAPS.md; no closure evidence yet |

## V1 capability work outside the gap list

Pending: app authentication and sessions; verified Steam linking; bootstrap per mode; resumable history; entitlement; switching/deletion fencing; notification outbox; all 20 metrics; context parameters; deterministic insight engine; Profile claims; isolated mobile API; seed and golden fixtures; PostgreSQL/Redis/Celery E2E; acceptance traceability.

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
