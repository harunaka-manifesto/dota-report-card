# Dota Tracker — Backend Foundation: Autonomous Implementation Goal

> **Audience:** GPT-5.6 Sol, working autonomously in this repository.
> **Audit basis:** every repository fact in this prompt was observed at commit `bd3289e` on branch `main` on 2026-09-21. Facts drift. Re-verify each one before acting on it. If the repository differs from this prompt, the repository wins — record the difference in the ledger (§7.2).

---

## 0. Your role and the shape of this goal

You are the principal backend/infrastructure engineer responsible for completing the backend foundation for the native iOS **Dota Tracker** in this repository.

This is an **implementation goal, not a planning exercise.** Keep working autonomously until the server-side backend described by the active product SSOTs and architecture documents is implemented, migrated, tested, documented and verified end to end, to the extent this repository and your environment allow.

Do not stop after an audit, a plan, a scaffold, a partial implementation or a list of TODOs. Treat those as intermediate steps and keep executing.

Do not wait for the iOS UI. The backend must be independently operable and verifiable.

**Precedence inside this prompt:** (1) the operating and safety rules in §2; (2) the authoritative documents in §1; (3) the phase instructions; (4) your engineering judgment. Where this prompt disagrees with an authoritative document about product meaning or system behaviour, **the document wins** — follow it and record the discrepancy.

This is a multi-day effort. Work in ordered vertical slices (§3), keep the ledger current so you can resume after losing context, and commit after every green slice.

---

## 1. Sources of truth

The active native-iOS documentation lives under `#swiftMigration/`. The folder name starts with `#`, so quote it in every shell command (`"#swiftMigration/README.md"`). §18 R1 moves it to a permanent home early in the work. After that move, read every path below at its new location.

### 1.1 Reading order

1. `#swiftMigration/README.md`: the feature map, the authority ladder and the one exception for the two engine annexes.
2. `architecture/README.md`, all of it. §4 (rules for agents), §5 (the architecture/product conflict rule) and §6 (how decisions change) are binding.
3. In this order: `SYSTEM-ARCHITECTURE.md`, `MATCH-INGESTION-AND-LIFECYCLE.md`, `DATA-CONTRACTS-AND-VERSIONING.md`, `PROVIDER-CAPABILITIES-AND-ROUTING.md`, `FEATURE-DATA-DEPENDENCY-MATRIX.md`, `SCALING-RELIABILITY-AND-OPERATIONS.md`, `IMPLEMENTATION-GAPS.md`.
4. `architecture/decisions/README.md` and ADRs 0001–0005.
5. `architecture/evidence/README.md`, `architecture/evidence/post-match-ingestion-probe-2026-09-20.md` **and** `docs/evidence/provider-post-match-architecture-investigation-2026-09-20.md`. The second report is active evidence even though it lives outside `#swiftMigration`. Treat a report's *recommendations* as superseded by the ADRs. Only its *measurements* count as evidence.
6. All eight feature SSOTs: `app_foundation/`, `onboarding/`, `home/`, `history/`, `match_detail/`, `progress/`, `profile/`, `settings_account/`. Each one ends with an **acceptance-rules checklist**. Those checklists are your primary acceptance criteria (§7.3).
7. All eight `DESIGN-REQUIREMENTS.md` files. Skim them for the states and distinctions the UI must be able to render. They are projections of the SSOTs, and the SSOT wins.
8. The two algorithmically normative annexes, plus what they bind:
   - `_archive/engine_specs/POST-MATCH-INSIGHTS-SSOT.md`, its machine-readable companion `_archive/generated_data/post-match-final-audit-data/final-candidate-contract.json` (the Markdown and the JSON MUST agree, and a disagreement is a defect), and the frozen Tier-B classifier reference `_archive/generated_data/post-match-tier-b-validation-data/research-code/shape.py`, which the annex says engineering MUST implement exactly. Its §17 test vectors become golden tests.
   - `_archive/engine_specs/CONTEXT-ADJUSTED-PERFORMANCE-V1.md`.
9. `_archive/README.md`, which records what replaced what. Use `_archive/research/native-ios-backend-reuse-audit.md` as a **code map only**. It predates ADRs 0001–0005 (for example, it treats STRATZ as the authoritative production path). Where it disagrees with the architecture, the architecture wins.
10. `AGENTS.md`, `docs/agent/production-safety.md` and `docs/agent/analytical-learnings-and-gotchas.md`. They still bind, as reconciled in §2.1.

### 1.2 Authority

- **Product meaning:** owner decisions recorded in an SSOT > `app_foundation/SSOT.md` > the feature SSOT > `DESIGN-REQUIREMENTS.md` > `_archive/`.
- **System behaviour:** the architecture documents.
- **Algorithmic detail:** the two annexes and the JSON contract. When an annex cites a superseded SSOT (for example "Role Metrics V1 §6"), the active SSOT's version of that rule wins. An annex written against STRATZ field names does **not** make STRATZ a runtime dependency (§5.4).
- Nothing else overrides these: not the root `README.md`, `ARCHITECTURE.md`, anything under `docs/**`, `V7 Master Experience Plan v1.md`, `tone_of_voice.md`, older prompts, `graphify-out/`, or code comments.

### 1.3 Competing or stale documents you will meet (as of the audit)

| Document | Why it is dangerous |
|---|---|
| `docs/progression/role-metrics-and-baselines-v1.md`, `docs/progression/role-resolution-and-correction-v1.md` | Headed **"Status: ACTIVE SSOT"** but superseded. Their consolidated successors are in `app_foundation/SSOT.md`, and copies sit in `_archive/superseded_ssots/`. |
| `ARCHITECTURE.md` | States that Free "never hydrates match details or requests replay parsing". That is the old product's rule, and G-2 cites it as a conflict. |
| `README.md` | Says "Forward development is V7 on the staging line". |
| `docs/architecture/**`, `docs/product/**`, `docs/qa/**`, `docs/ui-revamp/**`, `docs/prompts/**`, `V7 Master Experience Plan v1.md`, `tone_of_voice.md` | Report-card-era product and architecture material. |
| `docs/decisions/0001-free-dna-v6.1-additive-generation.md` | A second ADR log whose numbering collides with architecture ADR 0001. |
| `api.json` | **OpenDota's vendor OpenAPI spec**, not ours. |
| `graphify-out/` | A generated knowledge graph from the v6.1 era. Stale. |
| `dota-news-scraper/` | An unrelated tool. |

None of these are authoritative. Fence them during reorganization (§18).

### 1.4 Decisions that are deliberately open — do not fill them by inference

The SSOTs mark these as not decided: `app_foundation/SSOT.md` §19, `home/SSOT.md` §4, §5 and §10, `profile/SSOT.md` §12–13, `onboarding/SSOT.md` §16, `settings_account/SSOT.md` §12, and `progress/SSOT.md` §4. Implementing any of them "because the screen needs something" is inventing product behaviour.

| Open item | What you do instead |
|---|---|
| Trend meaningful-movement thresholds ("MUST NOT invent a number"). The only binding input is the hero-mix noise floor in the context annex §11, and it is a lower bound, not a value. | Build the evaluator against a **versioned calibration artifact**. Tests use clearly labelled test-only calibration fixtures. With no approved artifact, production MUST NOT emit Improving/Stable/Declining for that metric. Represent the gap explicitly in the API (a documented nullable state plus a reason code, never a fifth trend state) and log it as an owner/calibration blocker. |
| Classifier weights, calibration and the low-confidence threshold | Keep them as versioned configuration (`ROLE_CONFIDENCE_THRESHOLD` exists). Record the current values as provisional. |
| Today's Focus content model | Return only an honest neutral or absent slot state. Do not generate prompts. |
| Challenges and missions | Not contracted. Expose an "unavailable / not contracted" slot state and nothing else. |
| Achievement definitions and XP curves (the Free Level-5 cap has nothing to cap yet) | Do not implement achievements. |
| Monthly and periodic report content and cadence | Do not invent report content. At most provide the coverage-statement plumbing. |
| Pro historical depth ceiling (lifetime or capped) | Make it a configuration parameter. Do not choose a product value. |
| Account-recovery verification flow | Implement only the blocked and collision states plus the routing boundary. |
| Email authentication mechanism (password, magic link or OTP) | Build the interface and a fake. Log the decision. |
| Profile provisional parameters (`profile/SSOT.md` §12) | Ship them as the provisional, versioned parameter set exactly as written. Calibration is a pre-release gate, not your call. |
| Default Home bucket | Design may choose. The API must make the selected bucket explicit. |

Record every such item in the ledger's **Owner decisions needed** section with options and a recommendation.

### 1.5 Conflicts and owner decisions while you work autonomously

You cannot get owner sign-off during this run. When a conflict genuinely blocks implementation:

1. Write the ADR with **`Status: Proposed`**. Never mark your own ADR Accepted, and never edit an accepted ADR's decision.
2. Log it under *Owner decisions needed* with the options and your recommendation.
3. Implement the most conservative, **fail-closed** behaviour that does not foreclose the options: N/A, withheld, `UNAVAILABLE`, or the feature switched off.
4. Continue with everything else.

Correcting a **factual error** in an architecture document (for example, a wrong claim about which provider field is summary-class) is allowed in place under `architecture/README.md` §6. Cite the evidence and run the Product/SSOT dependents audit (rule 9).

---

## 2. Operating and safety rules

### 2.1 Reconciling with `AGENTS.md`

`AGENTS.md` was written for the live report-card product and is still in force. This goal is authorized as **BACKEND, DATABASE, ANALYTICAL (the new tracker engines only), DOCUMENTATION, and local-only INFRASTRUCTURE**. It is **not** authorized as RELEASE/DEPLOYMENT.

Therefore:

- These `AGENTS.md` rules still bind: production is live (§2); persisted-report compatibility (§4); the frozen V6.1 analytical invariants for legacy code (§12); OpenDota cost protection (§13); deployment permission (§14); and the STOP conditions for private data, fabricated evidence and production-state mismatch (§16).
- The `AGENTS.md` §3 scope-expansion STOP is **pre-authorized** for the scope above.
- When an `AGENTS.md` STOP condition fires, do not abandon the goal. Isolate the affected item, record it, and continue with unaffected work. Halt entirely only if nothing else can proceed.

### 2.2 Git

- Create a feature branch from current `main`, for example `tracker/backend-foundation`. Make reviewable logical checkpoint commits, not one opaque rewrite.
- **Never** commit to `main`, merge, push, force-push, rewrite history, deploy, or touch production environment variables, feature flags or dashboards (Vercel or Railway).
- Use `git mv` for moves so history survives.

### 2.3 Untracked data is sacred

- `.local/` holds about 14 GB of gitignored research corpora and provider caches. An irreplaceable corpus was lost on 2026-09-07 (`docs/evidence/v7-corpus-loss-incident-2026-09-07.md`).
- **Never** delete, move, rewrite or clean `.local/`, `.env`, `apps/web/.local`, or any untracked file you did not create. No `git clean`. No `rm -rf` outside directories you created in this run.
- Read-only use of `.local/` is allowed. To build fixtures, copy **sanitized** subsets into `tests/fixtures/`.

### 2.4 Secrets and privacy

- Never print, log or commit secret values. Inspect environment variable *names* only.
- As of the audit, `.env` defines `STRATZ_API_KEY` while `core/config.py` reads `STRATZ_API_TOKEN`. Map it explicitly without echoing the value, and fix `.env.example` and the docs so the names agree.
- Sanitize fixtures per `AGENTS.md` §8. Never commit raw account identifiers taken from `.local/` (some local files explicitly say never to copy them).

### 2.5 Live provider calls: budget and ledger

These are the defaults for the whole goal unless the owner changes them:

| Provider | Budget | Rules |
|---|---|---|
| OpenDota | ≤ 200 reads and ≤ 10 replay-processing requests (each costs 10 rate units) | Scheduled, never burst. |
| STRATZ | ≤ 60 smoke calls, plus **at most one** run of the population-parameter job (about 386 calls, context annex §14) | Only if §2.6 is satisfied. |

- Record every live call in the ledger: provider, operation, purpose, rate units and outcome.
- Never run bulk backfills of real accounts.
- Use identifiers that existing tests or evidence already use.
- No live calls just to validate UI or presentation (`AGENTS.md` §13).

### 2.6 The STRATZ token is IP-bound

A request from a second IP, or two concurrent jobs sharing the token, gets a 403 naming different IP addresses. The owner's network rotates IPv4 through CGNAT and mixes IPv4 and IPv6 per connection. If a deployed service uses the same token, calling it from your environment can disrupt that service.

Before any live STRATZ call:

- establish that the token is not in concurrent use by a deployment, or use a dev token;
- single-flight all calls through one keep-alive client pinned to one IP family;
- on a 403 IP-binding response, stop, do not retry-storm, and record it.

If you cannot establish safety, skip live STRATZ calls and record it as an external blocker.

### 2.7 Local dependencies

- Integration verification needs PostgreSQL 16 and Redis 7. `make infra-up` uses docker compose. At audit time the owner's machine had no `docker`, `psql` or `redis-server` on PATH. Provision them by whatever means your environment allows.
- If you cannot, record an environment blocker. **Do not** substitute SQLite for Postgres-specific guarantees (unique constraints under concurrency, `SELECT … FOR UPDATE SKIP LOCKED`, advisory locks, JSONB, partial indexes), and do not report such tests as passing.
- A **skipped test is not a passing test.** Report skip counts separately.

---

## 3. Execution order at a glance

Run tests continuously, not only at the end.

1. **Phase 0.** Baseline, ledger and acceptance traceability (§7).
2. **R1.** Mechanically move the documentation to its permanent home and fence the stale documents (§18). Docs are not runtime dependencies, and doing this early means every later document lands in its final location.
3. **Contract-first draft.** Write the mobile API resource model and state enums from the SSOTs and the dependency matrix. Design only; do not implement yet (§14.1).
4. **Phase A.** Schema and migrations (§8).
5. **Phase C.** Provider adapters: the OpenDota fresh path first, including the Turbo fix, then the STRATZ historical path (§10).
6. **Phase D.** A walking-skeleton fresh pipeline running end to end on fixtures with P0–P3 queues, even while analysis is still a stub (§11, §15).
7. **Phase E.** Role and analysis engines (§12).
8. **Phase F.** Identity, bootstrap, history, coverage, entitlement and account lifecycle (§13).
9. **Phase G.** Finish the mobile API, the fixtures and the local seed (§14).
10. **Phases H and I.** Operations and full verification (§15, §16), plus the E2E acceptance suite (§17).
11. **R2–R4.** Code migration and legacy fencing after parity (§18). Then documentation (§19), then the completion report (§22).

Phase B, the gap burn-down, runs through all of this. Close each gap in the phase that owns it.

---

## 4. Product transition

This repository was built for the deprecated one-shot, Spotify-Wrapped-style **Dota Report Card / Free DNA / Deep Scan** product. The new primary product is the continuous native iOS **Dota Tracker** described in `#swiftMigration/`.

The repository mixes:

- reusable backend, provider and domain code;
- current iOS product documentation;
- old web and report product code, **which is still in production** (§5.1);
- old product documentation;
- production-derived research modules, some **imported by runtime code**;
- offline research and evidence;
- scripts and generated outputs.

Part of this goal is to reorganize the repository so future agents cannot mistake deprecated report-card concepts for current Dota Tracker truth. **Do not do blind cleanup first.** Some old-looking modules are runtime dependencies holding validated provider, normalization, analytical, fixture or artifact code. Before moving or deleting anything, follow §18.

---

## 5. Repository facts and known landmines (audited at `bd3289e`)

### 5.1 Production and deployment coupling

- `AGENTS.md` says production is live: Vercel/Next.js (`apps/web`) → Railway/FastAPI (`services/api`) + PostgreSQL + Redis + Celery. Persisted user reports are production data contracts. Treat production as live unless the owner says otherwise.
- `infra/docker/api.Dockerfile` copies `services/`, `migrations/`, `scripts/verify_v61_runtime_package.py` and `infra/runtime-artifacts/free_dna_v61/6.1.0/`, and runs `uvicorn app.main:app`. `infra/compose.yaml` and CI depend on the same paths. The Vercel and Railway settings (root directory, start command, build path) are **outside this repository and unknown**. Moving any deploy-coupled path breaks production on the next deploy.
- `.github/workflows/qa.yml` runs on pull requests and on pushes to `main` and `staging`. It runs: an Alembic upgrade smoke on Postgres 16; ruff; mypy; `make test`; `make test-v7-stratz`; `make test-contract`; `make test-integration`; `make taxonomy-validate`; `make dna-catalog-check`; `make docs-check`; and `make api-client` followed by `git diff --exit-code -- packages/api-client/src/openapi-meta.ts`, so any change to the main app's OpenAPI must regenerate that file. It also runs web lint, tsc, build and Playwright.
- `scripts/check_docs.py` hardcodes a list of legacy documents. Moving documents means updating it.

### 5.2 Storage

- The Alembic chain is linear, even though two files start with `0001`: `0001_initial` → `0001_version_table_width` → `0002_persist_analysis_job_details` → `0003_analysis_mode` → `0004_raw_payload_metadata` → `0005_v6_interactions_deep` (head). `services/api/app/storage/database.py: EXPECTED_SCHEMA_REVISION` must equal the head. The API and the worker (`check_ready`) refuse to start against any other revision.
- Tables already present include `players`, `matches`, `match_participants`, `match_time_series`, `match_events`, `teamfights`, `ward_events`, `raw_payloads`, `parse_coverage`, `derived_features`, `analysis_jobs`, `reports`, `report_interaction_sessions` and `evidence_objects`. See G-3, G-5, G-7, G-11 and G-13 for what is right and what is missing.
- **Retention purge landmine.** Celery beat runs `dota_report_card.purge_expired` every hour. `SqlAlchemyRepository.purge_expired` deletes **every `raw_payloads` row older than `REPORT_RETENTION_DAYS`** (30 in compose), plus expired reports.
  - Tracker raw snapshots that feed a published analysis must be retained (`DATA-CONTRACTS-AND-VERSIONING.md` §6, rule S-1). Derived features are kept forever (S-5).
  - If you reuse these tables or this job, reconcile it explicitly with a test.
  - Do not silently change the legacy report retention behaviour. It is a privacy behaviour of the live product.
- `tests/integration/test_postgres_migrations.py` is skipped unless `RUN_POSTGRES_MIGRATION_TEST=1` and `TEST_POSTGRES_URL` are set, and most repository tests use SQLite. A green `make test` does not prove Postgres behaviour.

### 5.3 Workers

`services/api/app/workers/tasks.py` has a single Celery app: one beat schedule, no routing, no queues. It runs only legacy `AnalysisService` report jobs. `V7RuntimeService.generate` is wired to neither the routes nor the tasks.

### 5.4 Providers, and the cross-provider translation risk

- **OpenDota:** `opendota/client.py` handles reads and has **no `significant=0`** (G-10 confirmed). `opendota/parse_client.py` is a deliberately separate parse transport. Keep that separation and change *who decides* (G-2).
- `analysis/budget.py`: `CostPolicy.parse_request_units = 5.0`. The vendor documents 10 (G-9).
- **STRATZ:** `stratz/client.py`, `queries.py`, `models.py`, `normalize.py` and `deep.py`. `GetDeepMatchBatch` omits a page size, and `player_analysis_v7/acquisition_policy.py` sets `MATCHES_PER_REQUEST = 8` (G-1).
- `providers/base.py` is the provider-neutral contract. Preserve it.

**Cross-provider translation is the largest analytical risk in this goal.** The insight annex and the context annex were researched and specified on **STRATZ** fields and semantics:

- `POSITION_1…5` for all ten players ("each team has exactly one player at each position" is a global eligibility rule);
- STRATZ `lane` enums;
- STRATZ cell coordinates for vision reconstruction;
- `stats.networthPerMinute`, `stats.level` timestamps, `leaverStatus` enums and `gameVersionId`;
- STRATZ `heroStats` position semantics for the population parameters.

But fresh replay-class evidence is routed to **OpenDota** (ADR 0001), and STRATZ must stay off the fresh path. Therefore:

1. Define the canonical derived features provider-neutrally.
2. Write one explicit **translation rule** per provider per feature (`DATA-CONTRACTS-AND-VERSIONING.md` §5 V-4). Record the semantic differences in `PROVIDER-CAPABILITIES-AND-ROUTING.md` §4.4.
3. Prove each rule with **paired fixtures**: the same matches fetched from both providers, compared within documented tolerances. Look first for existing overlapping payloads in `.local/` (read-only) and in the evidence folders.
4. Where equivalence cannot be established, record **UNKNOWN**, fail closed for the dependent output (N/A, no card, or lane context `UNAVAILABLE`), and log an owner decision. **Never silently assume two fields are equivalent.**
5. The fresh provider has no native position. The engines need a **provider-neutral 1–5 position assignment for all ten players**, derived by our own classifier. That assignment is internal, and the product boundary normalizes it to the four roles. Decide and document how a user role correction affects the internal assignment the engines consume.
6. Smoke→Kills enrichment depends on STRATZ playback. **Do not add a per-fresh-match STRATZ call to get it.** That would violate ADR 0001 and "STRATZ spend per fresh match is zero". On the fresh path the enrichment is simply absent, which the annex permits.

### 5.5 Research code imported by runtime

- `services/api/app/player_analysis_v7/research/` is imported by `player_analysis_v7/runtime.py`, `capability_payload.py`, `display_semantics.py`, `report_contract.py`, `service.py` and `descriptive.py` (all V7 report product), and by **`stratz/deep.py`**, which is the provider layer.
- The top-level `research/` holds evidence documents and specimens. It is not imported.
- `#swiftMigration/_archive/**/research-code/` is **referenced normatively** (the Tier-B `shape.py`). Do not delete it.

### 5.6 Tracker-looking code that contradicts the locked contracts

These are **reference material, not parity targets.**

- **`services/api/app/progression/role_metrics.py`** and its tests. It consumes STRATZ-normalized rows. It derives the role from STRATZ `position_native` and `role_native`, which violates R-2 and is a class-C dependency. Its baseline uses `statistics.fmean`, a **mean**, where the SSOT requires the **median** of the previous 20 with a 5-prior gate. It implements 5 of the 20 metrics. Fix these semantics with regression tests. Do not preserve them for "parity".
- **`services/api/app/features/roles.py`.** It labels the classes 1–5 as "position N" (G-14). Its primary signal, `lane_role`, is tagged `parsed_lane_role` in the code itself, which suggests it is **replay-class on the fresh provider**. That contradicts G-4's statement that lane role is summary-class. Verify against real unparsed and parsed OpenDota payloads before designing the summary-class evidence profile (R-1). If G-4 is factually wrong, correct it in place (§1.5). Its confidences are hardcoded constants.
- **`services/api/app/insights/`** appears to be the legacy report insight registry, not the V1 post-match insight engine described in the annex. Verify before reusing any of it.
- **`player_analysis_v7/data/population-parameters-*.json`** are V7 report artifacts. Do not assume they are the context-adjustment parameter set. `_archive/scripts/lane-difficulty-research-code/pass2/param_stratz.json` is a **one-week** research set. It fails the ≥ 97 % coverage condition, which requires a 4–8-week pool, so it is not a production artifact.

### 5.7 Identity and commerce do not exist yet

There is **no** app-account authentication, no sessions, no Steam OpenID ownership verification, no App Store entitlement handling and no push delivery. `core/security.py` and `identity/steam.py` only parse and resolve Steam identifiers. §13 builds all of it.

### 5.8 Share cards

`services/api/app/share/service.py` renders deterministic, privacy-safe **SVG** share cards for legacy reports. Reuse the pattern for Profile and PB share snapshots. No new rendering infrastructure is needed.

---

## 6. Architecture invariants (non-negotiable)

Preserve what the documents lock. The following is a checklist; the documents hold the exact rules.

1. **Client boundary.** iOS → Dota Tracker API → persisted Dota Tracker state. The iOS app never calls OpenDota, STRATZ, Valve or any provider for product data. Provider calls happen only behind backend adapters and workers. **No product read path may trigger a synchronous provider call anywhere in the stack** (`SYSTEM-ARCHITECTURE.md` §4.1).
2. **Stack.** FastAPI, Python 3.11, PostgreSQL, Redis and Celery, with the existing tooling (uv, ruff, mypy, pytest, Alembic). No new infrastructure technology. New Python libraries are fine when they are standard and justified, for example JOSE/JWT verification. A **hosted** identity, queue, observability or storage platform needs an owner decision.
3. **Routing is policy.** OpenDota handles fresh detection, fresh summary-class evidence and fresh replay-class enrichment. STRATZ handles historical replay-class backfill beyond the replay horizon, cached versioned population reference data, and a circuit-broken fallback. Routing stays swappable behind adapters. **STRATZ on the fresh happy path requires a new ADR.**
4. **Canonical boundary.** Provider concepts end at the adapter. Layers 2–6 are provider-neutral (`DATA-CONTRACTS-AND-VERSIONING.md` L-2). Cross-provider translation follows §5.4.
5. **`match_id` is the unit of work.** One Dota match with five tracked users means: one detected match, one canonical match, ten player rows, one replay-enrichment path, five account links, and user-relative analysis per tracked account. Tracking is a property of the account; follower count never adds fetches.
6. **One pipeline for Free and Pro.** Acquisition, feature extraction, methodology and analysis are shared. Entitlement sits above persisted analysis. Fresh ingestion must be viable if every user is free. Pro history depth is more P3 work of the same kind and never jumps the queue.
7. **No runtime LLM** anywhere in the post-match pipeline, and no model fitted at runtime.
8. **Missing evidence stays missing.** Never zero, default, interpolate, substitute or carry over. N/A carries a reason, and a legitimate zero stays zero.
9. **Two orthogonal axes, one finalization point.** These are **independent** axes, and you must not merge them into one state machine:
   - **Evidence readiness** (global, per match): `DISCOVERED → SUMMARY_READY → REPLAY_PENDING → REPLAY_READY | REPLAY_UNAVAILABLE`. The only backward transition is `REPLAY_UNAVAILABLE → REPLAY_READY`, and only through historical re-admission.
   - **Lifecycle** (per match × tracked account): `WAITING_FOR_PROVIDER | ANALYZING | WAITING_FOR_PRIOR_MATCH | ACTION_REQUIRED | READY | UNAVAILABLE`. `RETRYING` is attempt metadata, never a durable state. There is no partial-READY.
   - **Progression classification:** `STANDARD | TURBO | NONE(reason)`.
   - **Account sync state:** `IDLE | CHECKING | UP_TO_DATE | SYNC_ERROR`.
   - Exactly **one** finalization per match and account produces comparisons, expectations, performance states, matchup context, PB determination and `NEW_PB`, progression observations, insight cards and any READY notification. `REPLAY_UNAVAILABLE` reaches READY with N/A replay metrics. It is **not** lifecycle `UNAVAILABLE` and **not** `ACTION_REQUIRED`.
10. **Discovery triggers.** V1 discovers on app open, app resume or explicit refresh (P0, debounced globally per Dota account), plus server-owned bootstrap, backfill and recovery work. **Do not build always-on background detection polling.** The "hot user" polling in the probe's §9.3 is a non-normative recommendation that `app_foundation/SSOT.md` §4.1 does not adopt. Replay-enrichment polling after detection is bounded and has terminal stop conditions (CB-6).
11. **No provider or pipeline vocabulary in product payloads or copy**: no provider names, "parse", "parser", "queue", "job", "quota", "rate limit", `POSITION_*`, "Position 4" or "Position 5". An internal admin or diagnostic surface may use them. It must be separately authenticated and must not appear in the mobile OpenAPI.

**What may change without a new ADR:** routing policy and configuration, batch sizes, retry ladders, thresholds that are operational configuration, worker counts, evidence updates, and implementation structure. **What needs an ADR:** anything that changes the ADR 0001–0005 decisions, the client boundary, the canonical boundary, `match_id` as the unit of work, the two-stage and single-finalization model, entitlement above data, no runtime LLM, a new infrastructure technology, or STRATZ on the fresh path.

---

## 7. Phase 0 — Baseline, ledger and traceability

### 7.1 Establish the baseline before any structural change

- Record `git status --short --branch` and `git rev-parse HEAD`, then create your branch.
- Inspect the repository tree, runtime import dependencies, the migration history, CI, deployment configuration, the current API and OpenAPI surface, the database models and repository, and the provider clients and adapters. Re-verify every fact in §5.
- Run every applicable test target (`make lint`, `make typecheck`, `make test`, `make test-v7-stratz`, `make test-contract`, `make test-integration`, `make docs-check`, `make dna-catalog-check`, `make taxonomy-validate`), plus the Postgres migration test if you can provision Postgres. Record the **pass, fail and skip counts** and every test that fails before your changes.
- Produce a runtime import graph for `services/api/app`, for example with a small AST script. It is the basis for every later move.

### 7.2 Implementation ledger

Create `architecture/IMPLEMENTATION-LEDGER.md`, which moves with the docs in R1. It is temporary operational documentation, not a second architecture contract. Its sections:

1. **Gap status.** Every item in `IMPLEMENTATION-GAPS.md` (G-1 … G-15), each with: status, code affected, the tests that prove completion, and the commit.
2. **V1 capability work not in the gap list.** The gap list only covers architecture-versus-code gaps. It does not cover authentication, Steam OpenID, entitlement, notifications, bootstrap, the insight engine, Profile claims, the population-parameter job, and so on. Track those here.
3. **Engineering decisions.** Consequential choices, each with its rationale.
4. **Owner decisions needed.** From §1.4 and §1.5, each with options and a recommendation.
5. **External blockers.** Only genuinely external ones, each with the smallest action that would unblock it.
6. **Live provider call ledger** (§2.5).
7. **Baseline test results**, and the pre-existing failures.
8. **Path mapping** for every documentation or code move.

### 7.3 Acceptance traceability

Turn the backend-relevant rules in every SSOT's acceptance checklist into traceable tests: `app_foundation` §18, `onboarding` §17, `settings_account` §11, `match_detail` §11, `progress` §12, `profile` §14, `history` §11 and `home` §11. Also include the SSOTs' hard-invariant lists.

We recommend a pytest marker, for example `@pytest.mark.ssot("app_foundation#18.12")`, plus a script that reports which rules have tests, which do not, and which are client-only. Rules that belong to the client and not the backend are marked as such, not dropped.

---

## 8. Phase A — Data foundation

Implement the canonical entities and invariants from `DATA-CONTRACTS-AND-VERSIONING.md`. Exact table names are your decision, but **the shapes and keys are the contract**. Reuse the existing `matches` and `match_participants` foundation where it is correct (G-5), after dealing with the purge job in §5.2.

The backend needs coherent representations for at least the following.

**Identity and accounts**

- App users.
- Authentication identities (Apple, Google, email), each attached to exactly one user.
- Sessions and refresh tokens, stored hashed.
- Device registrations and push tokens.
- Dota/Steam accounts.
- The verified user ↔ Steam ownership: at most one **active** Steam ID per user and one active user per Steam ID, **enforced by database constraints**. Store the **original Steam-link date**, which is the entitlement anchor.
- Archived Steam profiles.
- Steam-switch history and the cooldown.
- `follows`, at the schema level only. No follow API exists until an SSOT contracts it.

**Match data**

- Global matches keyed by `match_id`, carrying `evidence_state`.
- Ten canonical `match_players` rows per match.
- `account_matches` links carrying the per-account lifecycle state, the progression classification and reason, and the chronology key `(provider_started_at, provider_source_match_id)`.
- `match_acquisition_state`, which holds the per-provider request, retry and terminal-reason state behind `evidence_state`.
- Provider snapshots keyed by (provider, operation, operation_version, subject), carrying digest, size, fetch time and provenance. Unparsed and parsed snapshots of the same match coexist; they never overwrite each other.

**Derived and analytical data**

- `derived_match_features` per (`match_id`, player_slot, `feature_version`), with per-field-group provenance. This is permanent storage.
- The provider-neutral internal position assignment for all ten players.
- Classifier results for each evidence profile, recording which profile produced each one.
- **Append-only role assertions**, recording user corrections with provenance.
- User-relative metric observations per (account, match, metric_id, metric_version), including the **baseline-at-the-time snapshot**, the persisted context terms `h` and `E`, and `parameter_set_version`.
- Baseline and reference metadata, including **versioned population parameter sets** and personal rolling baselines.
- Immutable analysis results per (`match_id`, account_id, `analysis_version`, `inputs_digest`).
- Insight results carrying `contract_version`.
- Current-PB state (rebuildable) and the **append-only** `NEW_PB` event ledger.
- The Profile claim state machine (CANDIDATE, CONFIRMED, FADING, RETIRED) and its change events.
- Share snapshots.

**Sync, jobs and accounting**

- Account sync state: cursors, last check, backoff, failure counters and the privacy/blocked state.
- Historical coverage per account per evidence class, with known gaps.
- Bootstrap state per Steam profile **per mode**.
- Ingest jobs with a **unique constraint on the dedup key**, a `run_after` time for scheduling, attempt metadata and priority class.
- The provider call log: provider, operation, status, latency, **billed units and rate units kept separate**.

**Commerce, notifications and deletion**

- Entitlement and subscription records, bound to the app account and keyed by the store's original transaction ID.
- The append-only event and notification outbox, with stable dedupe keys.
- The deletion-pending state and **job fencing**, so that late results cannot commit after deletion.

**Rules**

- Implement the **three independent version boundaries**, `feature_version`, `analysis_version` and `baseline_version`, on every analysis result, plus an `inputs_digest`. Where a product document names a version (metric version, parameter-set version, insight `contract_version`), the product's name wins.
- Rebuilds must work from stored canonical and derived data with **zero provider calls**.
- Enforce idempotency with **database constraints**, not application discipline alone.
- Legacy tables get additive changes only. Never destroy or rewrite persisted report data to simplify a migration.
- Write proper Alembic migrations, then bump `EXPECTED_SCHEMA_REVISION`. Test all of the following:
  1. a clean database upgraded to head;
  2. an upgrade from `0005_v6_interactions_deep` with a **populated legacy fixture database**, after which the persisted reports must still read correctly through the existing endpoints;
  3. a downgrade, where feasible;
  4. that the CI Alembic smoke still passes.
- Running the migration against production is a release step and **out of scope**.

---

## 9. Phase B — Burn down the implementation gaps

Resolve `IMPLEMENTATION-GAPS.md` systematically. For this goal, implement FOLLOW-UP items too when they are foundational and achievable. None of these may remain structurally unresolved:

- **G-1** STRATZ batching. Add an explicit page size. Use 50 as the proven all-covered batch and 100 as the proven mixed-state batch, as `PROVIDER-CAPABILITIES-AND-ROUTING.md` §5.2 recommends. Delete the arithmetic built on 8. Add memory, timeout and schema tests, and reduce the batch size on error, never increase it on optimism.
- **G-2** Replay enrichment on the shared fresh path for every tracked account, Free and Pro alike. Keep the separate parse transport.
- **G-3** A persisted `evidence_state` and acquisition state. Readiness is derived from persisted state, never by inspecting a payload at read time.
- **G-4** Two explicit classifier evidence profiles, recording which one produced each result. Verify the claim that lane role is summary-class first (§5.6).
- **G-5** Account links and the global-match work model. Key analysis on (`match_id`, account_id, `analysis_version`).
- **G-6** P0–P3 queues (§15).
- **G-7** Ingest job rows with schema-enforced idempotency, plus the Redis locks from `DATA-CONTRACTS-AND-VERSIONING.md` §8. **Locks are an optimization; database constraints are correctness.** Losing a lock must not create duplicates.
- **G-8** Account sync state and historical coverage.
- **G-9** Rate units modelled correctly: a parse request costs 10 rate units and 1 billing unit, and the two are kept separate.
- **G-10** Turbo-inclusive history everywhere account history is read. For the OpenDota history endpoint that means passing `significant=0`. Add a regression test that fails if the parameter is dropped **or** if the provider's default changes, and check every history-reading call site, including detection.
- **G-11** Provider and operation version as first-class columns.
- **G-13** The three version boundaries plus the inputs digest.
- **G-14** An explicit four-role normalization boundary, with a test proving that no product payload carries a five-value role.
- **G-15** The per-match, per-account lifecycle on `account_matches`.
- **G-12** Raw-payload tiering is trigger-based. Implement the storage interface or pointer abstraction if it is cheap. Do not deploy object storage merely so it exists.

When everything is addressed or deliberately trigger-deferred, burn the list down exactly as the document says: it gets burned down and deleted. Keep the ledger as the closure record, filed under evidence.

---

## 10. Phase C — Provider and acquisition layer

Reuse the validated OpenDota and STRATZ transport where it is correct. Do not rewrite working transport.

### 10.1 OpenDota (the fresh path)

| Purpose | Endpoint and notes |
|---|---|
| Detection | `recentMatches` or the history endpoint. The history endpoint **must** pass `significant=0`. |
| Stage-1 summary | The unparsed `GET /matches/{id}`. It carries all ten players' scoreboard, items, ability builds and the draft. The detection payload alone is **not** the full Stage-1 record, per the evidence reconciliation, and `SUMMARY_READY` needs the canonical summary for all ten players. |
| Replay processing | `POST /request/{id}`, through the dedicated processing token bucket. |
| Parsed payload | `GET /matches/{id}`, where `version != null` marks a parsed match. |

The benchmarks and percentile fields the provider returns are **not exposable**, because the product forbids percentiles (`app_foundation/SSOT.md` §2).

### 10.2 STRATZ (the historical path)

- Deep history batches with explicit page sizes.
- Gate replay-class features on the **stats** marker (`statsDateTime` / `isStats`), never on `parsedDateTime`.
- Single-flight every call from one client with a stable egress.
- **Never treat an absence in STRATZ as proof a match does not exist.**
- The population-parameter job (§12.4).

### 10.3 Implement and verify

- Provider-neutral canonical normalization, with the translation rules and paired-fixture parity from §5.4.
- Storage identity of provider + operation + version + subject, with immutable raw snapshots.
- Structured provenance: provider, operation, operation version, fetch time and digest per snapshot, and per field group on derived features.
- **Provider disagreement quarantine.** When two providers supply semantically equivalent fields for the same match, compare them. On disagreement, keep both, quarantine only the dependent findings, and record it. Never silently pick one.
- Account-sync debouncing, keyed per provider and account, globally.
- Global match deduplication and replay-request deduplication (`parse:{provider}:{match_id}`).
- Bounded retries with backoff, circuit breakers per provider, and token buckets **sized from response headers, never from published documentation**, read on every response.
- A **separate replay-processing bucket**, a held-back reserve share, and distributed coordination wherever multiple processes could duplicate provider work.
- A provider call log sufficient to attribute latency, cost and rate usage.
- Credentials never reach client code or logs.

**Egress.** A stable STRATZ egress IP is a **deployment prerequisite**, not something code can provide. The code must single-flight, detect IP-binding 403s, open the breaker instead of retrying, and alert. Document the requirement (for example a static outbound IP) in the deployment notes.

---

## 11. Phase D — Fresh-match pipeline

Implement the sequence in `MATCH-INGESTION-AND-LIFECYCLE.md` §4 and map it onto the lifecycle per §5. The two axes are kept separate here.

```text
EVIDENCE (per match)                          LIFECYCLE (per tracked account in the roster)
match_id observed            → DISCOVERED        WAITING_FOR_PROVIDER
canonical summary persisted  → SUMMARY_READY     WAITING_FOR_PROVIDER   ← Stage 1 readable now
enrichment enqueued          → REPLAY_PENDING    WAITING_FOR_PROVIDER
replay persisted             → REPLAY_READY      ┐
  or ladder exhausted / no replay / horizon      │ ANALYZING
       passed / deadline     → REPLAY_UNAVAILABLE┘   → WAITING_FOR_PRIOR_MATCH (if needed) → READY
                                                   failure branches: ACTION_REQUIRED | UNAVAILABLE
```

### 11.1 Required behaviour

- **Stage 1 never waits** for replay data (F-2). The match is product-readable at `SUMMARY_READY`, and the effective role is available at that point (R-1).
- **Scheduling.** Compute the match end from the summary (start plus duration). Request replay processing **no earlier than the expected replay availability**: a configurable floor, about 6 minutes after match end according to the evidence (F-3, RL-6). Run a bounded ladder with backoff and a deadline. Never request processing for matches outside the replay horizon (H-3).
- **Terminal outcomes.** `REPLAY_UNAVAILABLE` carries an **internal** reason code: no replay, processing permanently failed, horizon passed, or deadline exceeded. It never becomes an endless state.
- **Late recovery.** `REPLAY_UNAVAILABLE → REPLAY_READY` happens only through historical re-admission. Treat it as a late-admitted historical match under the rebuild rules: no celebration, no notification.
- **After READY**, passive provider enrichment is ignored for the finalized snapshot (`app_foundation/SSOT.md` §4.7). Provider checkpoints are monotonic before READY, and a stale response never regresses them (F-8).
- **Ordering.** Analysis may run concurrently, but **finalization is ordered per progression bucket** by the chronology key. A later same-bucket match waits in `WAITING_FOR_PRIOR_MATCH`, and the other bucket never blocks. A **live match that arrives while its mode's bootstrap is unsettled** shows its facts but defers finalization until **that mode's** bootstrap is terminal (`onboarding/SSOT.md` §6.1).
- **Internal failure after provider success** retries internal work only and never refetches source truth (CB-4).
- **Manual Retry** is one action. It resumes from the earliest failed or unresolved stage and reuses completed work. It applies to `ACTION_REQUIRED` and `UNAVAILABLE` only, never to `REPLAY_UNAVAILABLE`.
- Overlapping discovery, workers and retries **merge**. At-least-once internal work has exactly-once observable effects.
- **Notifications** are READY-only, go through the outbox, are coalesced per user (one bundle may span both buckets), dedupe stably across retries, restarts and devices, and are best-effort suppressed while the app is in the foreground. Notification permission and device state **never** gate processing.

### 11.2 Integration tests

- normal replay success;
- replay delayed, then succeeds;
- replay never exists;
- replay processing permanently fails;
- deadline exceeded;
- duplicate discovery;
- concurrent workers on the same match;
- multiple tracked users in one match;
- provider outage with the breaker open;
- internal failure after provider success, asserting zero refetches;
- Turbo;
- missing or null fields;
- provider disagreement;
- ordering: a newer same-bucket match waits, and the other bucket proceeds;
- a live match during an unsettled bootstrap;
- enrichment arriving after READY is ignored;
- late `REPLAY_UNAVAILABLE → REPLAY_READY` recovery without a celebration;
- a stale response does not regress a checkpoint;
- manual Retry resumes from the right stage;
- a remake, abandon or ambiguous-integrity match becomes `NONE(reason)` and fails closed;
- duration 599 s is ineligible and 600 s is eligible;
- rebuild during in-flight enrichment.

---

## 12. Phase E — Role and analysis engines

All analytical truth is computed on the server. The client reconstructs nothing.

### 12.1 Roles

- The **classifier runs from summary-class evidence alone** (R-1) and may be refined on the replay-class profile **before** finalization only (R-3). A rerun before finalization is not a correction (R-4).
- It produces the internal 1–5 assignment for all ten players (§5.4). The public roles are exactly **Carry, Mid, Offlane, Support**, and positions 4 and 5 both become Support at the boundary.
- Confidence is a product bucket, high or low. The low-confidence prompt comes from the **final** run (R-7).
- **The latest user assertion always wins.** Reruns never overwrite it. Win/loss, KDA and outcome never feed classification. Hero identity is a weak prior only.
- **Correction rebuild** (`app_foundation/SSOT.md` §5.6): remove the match from the old-role histories, re-evaluate it under the new role's metric set using frozen source data and the original metric versions, insert it at its original chronology position, and replay forward **within the same bucket only**. Use N/A where retained data cannot support a metric. Delivered events are never retracted. There are no provider calls. Edit Role is available on every retained match while retained data supports a rebuild; otherwise the API says correction is unavailable. Reopen that match's insight result, and mark later affected results for recompute on next display.

### 12.2 Progression and metrics

- **Eligibility** (`app_foundation/SSOT.md` §6): a supported bucket, duration ≥ 600 s, no abandon by the tracked player, an effective role, no evidence of an invalid match (ambiguity fails closed), and the required telemetry for each metric. `MATCH_ELIGIBLE != EVERY_METRIC_AVAILABLE`.
- **All 20 metrics** in the `app_foundation/SSOT.md` §7.2 registry, versioned, with the exact N/A rules. Camps Stacked is the count at **exactly 20:00**. Support Control is unsupported and must never be proxied. Raw and comparison values stay separate. The evidence class per metric comes from the dependency matrix §3.
- **Baseline:** the **median** of the previous ≤ 20 eligible measured observations, once there are ≥ 5 priors, keyed by bucket + role + metric + version. The current match is never included. Baseline-at-the-time is stored with each observation, and the current rolling baseline is a separate thing.
- **Personal Bests:** comparison value, strict inequality (ties keep the earliest), metric polarity, **all** known eligible history (not the 20-window), the 5-prior gate, and a pointer to the source match. `NEW_PB` at most once, only at finalization, never retroactively. Imports, backfills, corrections, entitlement changes and migrations update the current PB silently.
- **Trend:** the complete 10-point window of baseline-ready points; N/A points are skipped; the movement thresholds come from a calibration artifact only (§1.4). No role-level or composite trend exists anywhere.
- Standard and Turbo share nothing: no baselines, trends, PBs, observations or queues.

### 12.3 Context-adjusted expectation and lane context (annex + `app_foundation/SSOT.md` §10)

- Window-relative own-hero and lane-opponent terms, capped. Apply the per-metric **class matrix** exactly (A, B, C, C\*, D, E) and the **floor rule**. `offlane.objective_involvement.v1` is diagnostic only. Lane context applies only to Standard × {Carry, Mid, Offlane}. **Turbo gets no adjustment.**
- `PerformanceState` uses the frozen τ·σ_pop thresholds from the parameter set.
- `LaneContext` is draft-only and fails closed to `UNAVAILABLE`, which renders **nothing**. It is never composed in one claim with the performance state or the result.
- Encode the **forbidden-input list as a test**, not a comment.

### 12.4 Population parameter job (required for V1 by annex §15)

1. Fetch STRATZ `heroStats.stats` and `heroStats.laneOutcome` with a 4–8-week pool.
2. Derive the parameter tables.
3. Validate opponent coverage **≥ 97 %** and csCount-slope drift, with regression tests.
4. Publish a versioned, immutable artifact.

A failed validation **keeps the previous artifact**. With no valid artifact at all, **adjustment degrades to zero**, never to a wrong number. The job runs as offline or periodic P3 work under all the STRATZ rules. Run it live at most once (§2.5, §2.6). If it cannot run, ship the pipeline and validation, and record the missing artifact as a blocker.

### 12.5 Insight cards (annex + JSON contract)

- Global eligibility, then the feeding guard, then shared derivations. The Tier-B classifier must match `shape.py` exactly. Use the **stats-only** vision reconstruction. History comparators use the annex's own raw record window. Then severity, enrichments, the single Match-Lead-Story suppression rule, the fixed sort, and at most three cards.
- Every result is stamped with `contract_version`. The output is `EVALUATED` or `NOT_ELIGIBLE(reason)`. The 0-card state is the **normal majority state**.
- Cards are recap content, not progression and not events. Implement the annex's §17 test vectors as golden tests.
- Provider-field semantics follow §5.4.

### 12.6 Profile

- Profile eligibility is the same as progression eligibility.
- Per-bucket identity and role windows. The claim lifecycle with persistence and hysteresis. An evidence payload on every visible claim.
- Coverage honesty (PC-1 … PC-5). Withhold a claim when its window is under-covered.
- Change events are in-app only. Displayed state changes only at coherent checkpoints.
- Provisional parameters ship exactly as written (§1.4).

### 12.7 Determinism and versioning

- The same inputs with the same versions give **byte-identical** outputs. The inputs digest makes this checkable.
- **Run every rebuild twice** and prove that neither run duplicates observations, PB events, insights, notifications or any other observable state.
- Baseline, metric, analysis and parameter-set changes recompute from stored data with **zero provider calls**, over the **smallest dependency closure**, atomically from the consumer's point of view. A mixed-methodology timeline is never published.

---

## 13. Phase F — Identity, bootstrap, history, coverage, entitlement and account lifecycle

### 13.1 Authentication (`app_foundation/SSOT.md` §3, `onboarding/SSOT.md` §3, `settings_account/SSOT.md` §2)

- Apple, Google and email are methods on one app account. Authentication is mandatory before any product data; there is no guest mode.
- Verify Apple and Google ID tokens against their JWKS behind an interface. Test with locally signed keys.
- Email uses an interface plus a fake sender (§1.4).
- Sessions are backend-issued, with rotating refresh tokens stored hashed.
- Attaching an identity that belongs to another account is **blocked** and routed to the recovery boundary. Accounts are never merged.

### 13.2 Steam linking

- Server-side **Steam OpenID 2.0 assertion verification** (`check_authentication`) behind an interface, with a fake in tests. **Never accept a Steam ID the client asserts without verification.**
- Linking records the original link date and starts the Free bootstrap.
- Steam is optional for exploration, required for tracking, and required before a Pro purchase.

### 13.3 Free bootstrap (`onboarding/SSOT.md` §5)

- Independently **per mode**: up to 30 Standard **and** 30 Turbo eligible matches, searching back from the link date up to 90 days.
- It is server-owned and survives app kill, logout and reinstall.
- It acquires summary-class **and** replay-class evidence. Use the fresh replay route only inside a conservative, configurable horizon (the real boundary between 60 and 180 days is UNKNOWN). Use STRATZ historical data for older matches. A match with no obtainable replay is `REPLAY_UNAVAILABLE` and valid, and it is recorded as a coverage gap, never as "not played".
- **Terminal condition:** both searches finished, and every match processed or terminally failed.
- Six outcomes **per mode**: `NO_STEAM_LINKED`, `DATA_ACCESS_BLOCKED`, `NO_MATCHES_FOUND`, `NO_ELIGIBLE_MATCHES`, `READY`, `READY_WITH_GAPS`.
- **One** idempotent completion event per Steam-profile bootstrap. It is not queued for delivery after a later permission grant.
- There is **no** single `ONBOARDING_COMPLETE` flag.
- Imports never emit per-match notifications, PBs or celebrations. They insert at the true chronology position and update state at coherent checkpoints.

### 13.4 History and coverage

- Resumable imports with persisted cursors, and P3 backfill with pause and resume.
- Coverage per evidence class, recording known gaps.
- The authoritative discovery cursor advances **only after** the durable boundary, and every item gets an accepted, rejected or terminal outcome (`app_foundation/SSOT.md` §4.1).
- No partial historical state leaks into active calculations: Free state stays coherent while an import runs.

### 13.5 Data access blocked (`onboarding/SSOT.md` §8, `settings_account/SSOT.md` §4)

- Distinguish **private or unavailable** from **still syncing**. A refresh that stays empty is a privacy signal.
- Keep the link and keep Pro.
- Recovery re-anchors to the **original** link date, and the Free boundary never shifts forward.

### 13.6 Entitlement (`settings_account/SSOT.md` §5, ADR 0004)

- Entitlement sits above persisted analysis.
- A Pro purchase requires a linked Steam account.
- **Atomic activation** happens at a coherent checkpoint with a deterministic cutoff. First activation also requires a coherent Free foundation.
- Cancelling keeps Pro active until expiry. **Expiry deactivates atomically.** Pro data is retained, never deleted. A scope change is never presented as performance change, and there are no negative celebrations.
- Resubscription rebuilds from retained data and refetches only genuinely missing coverage.
- Entitlement belongs to the app account. Pro history belongs to the Steam profile.
- Store integration: App Store signed transactions and Server Notifications v2 are **verified with JWS signature-chain verification behind an interface**, with a deterministic fake provider for tests. Handle refund and revoke notifications as atomic deactivation. **Do not claim production Apple verification** without real credentials.

### 13.7 Steam switching

- Preconditions: the target authenticates, the target is linkable, and the target is not owned by another account.
- Blocked while an import or rebuild is non-terminal.
- A 90-day cooldown starts on success only; failed attempts never reset it.
- Old state is archived and **never** shown for the new identity. A new bootstrap and a new Pro backfill start, and the Pro entitlement stays with the account.
- Provide a preflight that reports the exact blocking cause and the days remaining.

### 13.8 Deletion

- Deletion-pending takes effect immediately. Jobs are cancelled or **fenced** so late results cannot commit. The Steam link is released. All user-scoped state is removed.
- Two questions must be logged, not resolved in code:
  - What happens to **globally shared canonical match rows** that other tracked accounts may reference. This is a legal-retention question.
  - The App Store gives the server **no way to turn off a user's auto-renewal** (verify this). The product rule "set not to renew" therefore needs an owner/legal decision on mechanism.

---

## 14. Phase G — Mobile API

### 14.1 Principles

- Create a deliberately small, versioned and typed boundary, mounted **separately from the legacy routes**. We recommend a FastAPI sub-application with its own OpenAPI document, for example under `/mobile/v1`. That leaves the legacy `/v1` report endpoints, `packages/api-client` and the CI OpenAPI diff check untouched, and gives Swift code generation a clean schema.
- Never expose provider or canonical database schemas, and never reuse a legacy report payload as the mobile contract.
- Derive every field and state from the feature SSOTs and `FEATURE-DATA-DEPENDENCY-MATRIX.md`.
- **Every block carries its own readiness.** A generic `isLoading` or `processing` flag must not cover capabilities with different evidence classes. The same applies to per-metric N/A with a reason, and to legitimate zeros that must stay distinguishable from N/A.
- Use closed enums, and document a forward-compatibility strategy for Swift decoding. Avoid `dict[str, Any]` wherever a stable schema can exist.
- Use no provider or pipeline vocabulary (§6 item 11). Enforce it with a test that scans the mobile OpenAPI document and every golden fixture for forbidden tokens.
- Insight cards and claims are returned as **template IDs plus typed slots** from the versioned template contract. If you also render text on the server, it must come only from versioned templates. Document the choice.

### 14.2 Conventions to decide once and document

- Authentication with bearer tokens, and account isolation tested against IDOR.
- Idempotency keys on mutating POSTs.
- Cursor pagination. ETag or `updated_since` support for incremental refresh.
- A problem+json error model with stable codes.
- Every timestamp in UTC. A **client time zone parameter** where "today" matters: Home's Today's Matches uses the user's local day.
- A cheap readiness-change mechanism so a foreground client can update additively. Choose the simplest one, for example a "changes since" endpoint. Push stays READY-only.

### 14.3 Endpoint inventory (minimum)

- Authentication, sessions and identity-method attach.
- Steam link start and verify.
- Device and push-token registration.
- Account, sync trigger (P0) and readiness.
- Bootstrap and coverage status per mode.
- Home, with the Today's Focus and Challenge slots in honest, non-fabricated states.
- History with filters and pagination.
- Match Detail, Stage 1 and Stage 2.
- Edit Role, correction availability, and manual Retry.
- Progress: series, rolling baseline, trend state and PBs per bucket, role and metric.
- Profile: claims with evidence payloads, heroes, "Right now", PBs, changes, and the share-snapshot projection.
- Settings: auth methods, switch preflight and execute, subscription and entitlement state, App Store transaction submission, and the notification webhook as a server-to-server endpoint outside the mobile OpenAPI.
- Data-access recovery confirmation, account deletion, and rebuild or import status.

### 14.4 Golden fixtures (sanitized, versioned, never overwritten)

- the common ready state; the cold start, per mode and across all six outcomes;
- a summary-ready / replay-pending match; a fully ready match; a replay-unavailable match;
- `WAITING_FOR_PRIOR_MATCH`; `ACTION_REQUIRED`; `UNAVAILABLE`; a READY-but-ineligible `NONE(reason)` match;
- N/A and zero side by side;
- history gaps; an insufficient baseline; trend `Insufficient History`; a trend that is uncalibrated or absent (§1.4);
- a low-confidence role; a corrected role; correction unavailable;
- lane context `UNAVAILABLE` (renders nothing); objective involvement shown as diagnostic only; Turbo with no adjustment;
- the 0-card normal state; three cards;
- Free; Pro importing; Pro active with partial coverage; Pro expired, showing a scope change;
- switch blocked by cooldown; deletion pending;
- data access blocked; sync error with cached data;
- an empty or new user; no Steam linked.

### 14.5 Developer experience

An iOS engineer must be able to work from only the OpenAPI document, these fixtures and the product and design docs. Provide:

- a **fixture-backed local seed**, for example `make seed-demo`, that creates accounts in each state above with no provider calls;
- an OpenAPI lint or validation step;
- if a Swift generator is available, a dry run of code generation.

---

## 15. Phase H — Jobs, priorities and operations

Implement the P0–P3 contract (`SCALING-RELIABILITY-AND-OPERATIONS.md` §2) on the existing Celery and Redis stack.

| Class | Work |
|---|---|
| P0 | Foreground account sync and latest-match detection. |
| P1 | Fresh-match replay enrichment. |
| P2 | Retries, lower-priority enrichment, followed-but-unowned accounts. |
| P3 | Historical imports, backfills and the parameter job. |

### 15.1 Celery and Redis facts to design around (verify them in the installed version)

- With a Redis broker, one worker consuming several queues does **not** give strict priority. Use **dedicated worker processes per priority class**, at least keeping P0/P1 separate from P3, and prove non-starvation with a test.
- Tasks scheduled with ETA or countdown and held longer than the broker's `visibility_timeout` can be **redelivered and run more than once**. Prefer **database-backed scheduling**: `ingest_jobs.run_after` plus a dispatcher that claims due jobs with `FOR UPDATE SKIP LOCKED`. Avoid long Celery countdowns for the replay schedule.
- Use `acks_late` with idempotent tasks, set prefetch to 1 for long tasks, and keep the P3 pause flag in shared state that is checked before claiming work.

### 15.2 Requirements

- P0 and P1 can never be starved by P2 or P3.
- P3 is pausable and resumable from its cursors. Provider pressure pauses P3 first. P3 hard-pauses when P1 depth, P1 oldest age or budget use crosses a threshold. Thresholds are operational configuration.
- Every job is idempotent. Routing is explicit.
- The oldest job age is observable per class.
- Fresh work keeps flowing during imports.

### 15.3 Observability without a new platform

- Persist per-match and per-account timestamps (match end, discovered, summary ready, replay requested, replay ready or unavailable with a reason, finalized) so the readiness-ladder P50/P90/P99 can be computed with SQL.
- Build on the existing `core/metrics.py`, structured logs and the provider call log.
- Expose operational summaries on an internal, separately authenticated endpoint that is not in the mobile OpenAPI.

### 15.4 What must be measurable

- discovery, summary-ready, replay-ready and analysis-ready latency;
- queue depth and oldest age per class;
- retry and failure rates, and the reasons for `REPLAY_UNAVAILABLE`;
- provider errors, 429s and quota; circuit-breaker state;
- coverage;
- the dedup ratio; provider calls per unique match; rate units by reads versus processing; cost attribution.

---

## 16. Phase I — Testing and verification

"Tests pass" is not enough unless the tests cover the architecture invariants. Build and run:

1. unit tests;
2. schema and model tests;
3. migration tests, both the clean path and the upgrade-from-legacy path;
4. repository tests on **Postgres**;
5. provider adapter and normalization tests, **including cross-provider paired-fixture parity**;
6. deterministic and golden analysis tests, including the annex test vectors;
7. role classification, correction and rebuild tests;
8. lifecycle and evidence-state transition tests;
9. idempotency and concurrency tests with real parallel workers;
10. queue priority and backpressure tests;
11. entitlement-boundary tests, including a static check that nothing below the persisted-result layer reads entitlement;
12. mobile API contract tests;
13. OpenAPI generation and validation tests, plus the forbidden-vocabulary scan;
14. **boundary tests**: product read paths cannot import or reach provider clients (extend the pattern in `tests/unit/test_v7_provider_architecture.py`), and no LLM SDK is importable from runtime packages;
15. integration tests with PostgreSQL, Redis, Celery and FastAPI running;
16. full backend E2E flows: account sync → persisted match → enrichment → analysis → API read;
17. the **legacy regression suite**, so the existing report endpoints and persisted reports still work.

**Rules**

- Use sanitized fixtures for deterministic CI.
- Update CI so Postgres and Redis integration tests actually run in CI. Keep the existing jobs green.
- Run tests throughout, not only at the end.
- When you fix a defect, add the regression test that would have caught it.
- When you move a module, prove that its callers were migrated.

**Live smoke tests.** Run them bounded, within §2.5 and §2.6, only when credentials exist and the rules allow. Their purpose is to confirm assumptions fixtures cannot prove: the fresh-provider Turbo parameter, parse timing and the processing-request response, the STRATZ page size with `take`, and the header-based limits. If they cannot run, **finish everything else** and record precisely which small verification item remains blocked.

---

## 17. Required E2E acceptance scenarios

Before you consider the backend finished, demonstrate each of these with automated tests or reproducible scripts.

**Onboarding and bootstrap**

- A new tracked account bootstraps 30 + 30 per mode and produces persisted history, with the correct per-mode outcomes and coverage gaps.

**Fresh-match pipeline**

- A newly completed match is discovered and becomes `SUMMARY_READY` without replay evidence, and the mobile API returns that Stage-1 match immediately, with an effective role.
- Replay enrichment later advances the same match to `REPLAY_READY` without replacing the canonical match. The final analysis is persisted and returned through the mobile contract.
- A missing replay reaches a terminal, explained state while the match stays usable and READY.
- Two tracked users in one Dota match produce one enrichment path, one match, ten player rows and two account links.
- Duplicate syncs and workers produce no duplicate provider calls and no duplicate product-visible effects.
- Turbo matches are never silently excluded.
- Missing evidence never becomes zero.

**Ordering and rebuilds**

- Same-bucket finalization ordering holds (`WAITING_FOR_PRIOR_MATCH`) and the other bucket is never blocked. A live match during an unsettled bootstrap defers only its own mode.
- A role correction survives classifier reruns and deterministically rebuilds the affected history in the same bucket only.
- A baseline-version change, and a parameter-set change, rebuild from stored data with zero provider calls. Running either twice changes nothing.

**Entitlement and account lifecycle**

- Free and Pro fresh matches traverse the same code path, proven by test and by static check.
- Pro activation, expiry and resubscription are atomic and make no provider refetch when coverage is complete.
- A Steam switch archives the old state, and none of it is ever visible for the new identity.
- Deletion during a running import fences the late results.

**Queues and degradation**

- A historical P3 import cannot starve P0/P1 fresh work.
- An interrupted import resumes from persisted cursors without duplicating work.
- A provider outage leaves stored product data readable.
- Provider disagreement quarantines the dependent findings instead of silently choosing a value.

**Boundary and contract**

- No product read endpoint performs a synchronous provider call.
- No mobile payload leaks provider vocabulary or a five-value role where a canonical concept exists.
- The legacy report endpoints and persisted reports still pass their existing tests.

---

## 18. Repository reorganization

### R1 — Documentation home (right after Phase 0; mechanical and isolated)

- Move `#swiftMigration/` to a permanent home with `git mv`. We recommend `docs/tracker/`, because `docs/product/` already holds legacy v6.1/v7 material. The `#` in the current name breaks relative Markdown links (they are read as URL fragments) and is awkward in shells and tooling.
- Keep `_archive/` intact, including `engine_specs/` (normative) and the research code the annexes reference.
- Rewrite every relative link, including the outward links to `docs/evidence/`, `docs/decisions/` and `AGENTS.md`. Extend `scripts/check_docs.py`, or add a link checker, so it covers the new tree and proves **zero broken links**.
- Leave no duplicate copy. Record the path mapping in the ledger.
- In the same slice, **fence** every competing document from §1.3. Mark `docs/progression/*.md` as superseded with a pointer. Add "legacy — non-authoritative" banners or moves for report-era documentation. Correct `README.md` and `ARCHITECTURE.md` so they point to the tracker. Move legacy documentation into a clearly named legacy area only where no tooling depends on its path, and update `check_docs.py` wherever it does.

### R2 — Fence the live legacy product (do not remove it)

- Do **not** remove or relocate anything production currently builds or serves: `apps/web`, the paths in `api.Dockerfile` and compose, `migrations/`, `infra/runtime-artifacts/`, and the legacy `/v1` endpoints. The one exception is a relocation where you update the Dockerfile, compose, CI and imports in the same change **and** tests prove parity **and** you document the required dashboard changes. Decommissioning the report product is an owner decision and outside this goal.
- Add a README at each legacy boundary that explains why the code exists, that it is non-authoritative for the tracker, and what still depends on it.

### R3 — Code migration, after the new backend works

For each module you touch, in this order:

1. inventory and classify it;
2. inspect its importers;
3. move the active subset to a truthfully named runtime module (for example, move what `stratz/deep.py` needs out of `player_analysis_v7/research/corpus.py`);
4. prove **relocation parity** with tests: identical behaviour for moved code;
5. only then archive the research-only remainder.

- Relocation parity is different from **correction**. Tracker semantics that contradict the SSOT (§5.6) are fixed, not preserved.
- Separate offline research and tooling from runtime.
- Remove dead compatibility paths only when you have proven they are unnecessary.
- Keep the historical evidence that explains architecture decisions.
- Classify `graphify-out/`, `api.json`, `dota-news-scraper/`, `output/` and the root-level legacy documents. Move, label or leave each one with a documented reason. Never touch `.local/`.

### R4 — Final pass

Update the references, imports, build tooling and CI after every move. Run the **entire** applicable suite again: backend, legacy regression, and web build/Playwright where your environment allows.

### Target boundaries

The layout is your choice, but these boundaries must be unmistakable:

1. current product SSOTs;
2. current architecture and ADRs;
3. active backend runtime (tracker);
4. backend tests and fixtures;
5. offline research, evidence and tooling;
6. the deprecated report-card material that is **still live**;
7. the future native iOS client.

---

## 19. Documentation deliverables

Keep product meaning in the SSOTs, architecture behaviour in the architecture docs, and implementation detail next to the code and in runbooks. **One authoritative home per rule.** Add concise READMEs at important boundaries instead of duplicating rules.

**Update or create:**

- the root `README.md`;
- `AGENTS.md`. Restructure it as a short router: which product is current, which rules apply to tracker work, and which production-safety rules still apply to the live legacy product. Keep the legacy rules intact, moved into `docs/agent/` if you split them. Also cover `apps/web/AGENTS.md`;
- the product documentation index and the architecture index;
- the API README (versioning, conventions, codegen);
- the local-development runbook (`make infra-up`, migrations, seed, workers per priority class, environment variables);
- test and verification instructions, including how to run the Postgres, Redis and live tests;
- operational notes on providers and routing (the budgets, IP binding, header-based buckets);
- migration and schema documentation;
- an accurate `.env.example` with consistent variable names;
- deployment notes: prerequisites such as the stable STRATZ egress IP, dedicated worker processes, APNs and App Store credentials, and the migration order. These are notes only; you do not deploy;
- a legacy/archive README.

**A fresh agent must be able to answer immediately:**

- which product is current and which is deprecated but still live;
- which documents are authoritative, and which directories must not be used as product truth;
- where the backend code lives, how to run it, how to run the tests, and how to run the local dependencies;
- how to verify the fresh-match pipeline;
- which provider is responsible for which capability;
- what may change without a new ADR.

If implementation shows an active document is stale, update the authoritative document and every dependent listed in its `## Product/SSOT dependents` section, in the same change. **Never rewrite an accepted ADR to change its decision; supersede it.**

---

## 20. What "backend done" means

It is **not** done merely because the code compiles, the existing unit tests pass, the endpoints exist, one happy path works, the old backend still works, or a TODO document exists.

It is done only when all of the following hold:

1. The active backend materially matches the current SSOTs and architecture, and the §7.3 acceptance traceability shows every backend-relevant rule covered by a test, or explicitly classified as client-only or owner-blocked.
2. Every BLOCKER and REQUIRED gap is closed. Foundational FOLLOW-UP gaps are closed. G-12 is policy-only or trigger-deferred.
3. The fresh-match pipeline works end to end, with both axes, one finalization point, ordering and notifications.
4. Deterministic analysis and rebuild semantics work: roles, metrics, baselines, PBs, trend mechanics, context adjustment, insights and Profile claims.
5. Bootstrap, history and coverage logic works.
6. The Free/Pro split obeys entitlement-above-data, and identity, Steam linking, switching and deletion work against fakes.
7. A typed, separately versioned mobile API exists for every contracted V1 feature, with golden fixtures and a seed.
8. Schema migrations are safe for a clean database and for an upgrade from the legacy head, with persisted reports intact.
9. Queues, idempotency and rate controls satisfy the architecture.
10. Integration and E2E tests verify the core invariants **on Postgres and Redis**.
11. The repository clearly separates the current tracker from the deprecated but live report-card material, and the report product still works.
12. The documentation accurately describes the resulting code, and a clean checkout has reproducible setup and test instructions.
13. The full applicable suite is green. The only exceptions are explicitly documented tests that need genuinely unavailable external credentials or services, with the skip counts reported.

**Release gates, not done-blockers.** These are recorded, not faked: the trend calibration, the Profile parameter calibration, the production parameter-set run, the raw-retention legal terms (OD-6, SZ-10), the Apple and Google production credentials, and the Railway static egress. Do not fabricate external verification. A missing iOS client is never a reason to leave server logic unverified; use contract tests, fakes and backend E2E instead. A missing provider credential blocks only the bounded live smoke tests.

---

## 21. Autonomy and decision-making

- Solve problems yourself instead of repeatedly returning to the owner for decisions the SSOTs and architecture already answer.
- For ordinary engineering ambiguity: inspect the existing code and tests, consult the authoritative documents, follow established repository patterns, choose the simplest implementation that satisfies the contract, and record consequential decisions in the ledger.
- For product ambiguity, follow §1.4 and §1.5. Never invent product behaviour, never add speculative features, and never deploy a scaling mechanism whose documented trigger has not fired.
- Prefer correctness, reproducibility, explicitness and testability over cleverness.
- When you change a schema, prove forward compatibility. When you change provider behaviour, prove your quota and idempotency assumptions.
- Continue until the completion definition is met, or until the only remaining work is blocked by an external dependency that genuinely cannot be simulated or verified locally.

---

## 22. Completion report

Finish with one concise report containing:

- **the `AGENTS.md` §15 fields that apply**: task type, base and new SHA, changed files, backend/analytical files changed, public report contract changed, persisted-report compatibility tested, typecheck, lint and build results, OpenDota QA calls, deployed (must be **NO**), and safe to merge;
- the final architecture and repository layout, with the path mapping;
- the status of every implementation gap;
- the migrations added, and the results of the clean and upgrade tests;
- the mobile endpoints and contracts added, and the fixture list;
- test counts: **passed, failed and skipped per suite**, including the Postgres and Redis integration runs;
- the E2E scenarios verified, with the test that proves each one;
- the acceptance-traceability summary: covered, client-only and owner-blocked;
- the live provider checks actually performed, from the call ledger;
- the infrastructure deliberately deferred because its trigger has not fired;
- the owner decisions needed, and the proposed ADRs;
- the genuine external blockers;
- the remaining work that belongs to the future Swift/iOS client rather than the backend.
