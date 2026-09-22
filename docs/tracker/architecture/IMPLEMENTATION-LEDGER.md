# Backend foundation implementation ledger

Operational evidence, not a product or architecture contract.

## Baseline and scope

- Base: `bd3289e4602303a7cdb9fccb3ea5bc482413f68f` (local main matched the attached audit).
- Branch: `codex/tracker-backend-foundation`.
- Authorized: BACKEND, DATABASE, ANALYTICAL (new tracker only), DOCUMENTATION, local INFRASTRUCTURE. No release/deployment.
- Existing untracked `docs/prompts/tracker-backend-foundation-goal.md` is user-owned and remains untouched.
- Current step: Phase A schema verified; next Phase C provider acquisition. Baseline, R1 and API design are committed. No implementation gap is closed.

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

- PostgreSQL 16.15 installed locally. Redis 7.2.16 official archive SHA-256 verified and built under `/tmp/tracker-foundation-deps`; isolated services run only on localhost ports 55432/56379; Docker absent. Legacy PostgreSQL migration smoke passes; tracker concurrency and Redis integration tests still pending.
- Web node_modules absent: web checks cannot execute until installed.
- STRATZ concurrent production token use not established: zero live calls permitted until safety is established or a dev token is available.
- Production identity/store/push credentials and approved calibration artifacts require later verification.

## Live provider call ledger

OpenDota reads: 0; replay requests: 0; STRATZ calls: 0. No deployment.

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
