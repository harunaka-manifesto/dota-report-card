# Implementation Gaps and Technical Debt

**Status:** ACTIVE — a burn-down list, not a contract
**Last updated:** 2026-09-20
**Scope:** Where the current codebase disagrees with the architecture documents in this folder, classified by urgency. **Nothing here was fixed by the documentation task that produced it.**

---

## 1. Plain-English summary

**What is this?** A list of the places where the code we have today does not match the architecture we just wrote down, so nobody has to rediscover them.

**Why does it exist separately?** Because a gap list has a different lifetime from an architecture document. Architecture documents get maintained; this one gets **burned down and deleted**.

**What should future agents not do?** Do not treat an item here as a decision. The decision is in the architecture documents. This is a to-do list against them.

---

## 2. Important context

The existing backend was built for a **different product**: a one-shot, web-delivered "Free DNA" report, with a paid Deep Scan continuation. The native iOS app is an **ongoing tracker**. Several gaps below are not bugs in the old system — they are places where the old system's shape does not carry over.

Where a gap is genuinely a defect in the current system, it is marked as such.

**Classification:**

| Class | Meaning |
|---|---|
| **BLOCKER** | The V1 iOS product cannot ship correctly without this. The reason is stated — no item is called a blocker without one. |
| **REQUIRED** | Must be done before implementing the architecture, but is not itself a launch gate. |
| **FOLLOW-UP** | Should be done; the architecture works without it. |
| **OPTIONAL** | An optimisation. Do it when a measurement asks for it. |

---

## 3. Gaps

### G-1 — STRATZ deep batch is 8, and the deep operation omits an explicit page size

**Class:** REQUIRED
**Where:** `services/api/app/player_analysis_v7/acquisition_policy.py` (`MATCHES_PER_REQUEST = 8`), `services/api/app/stratz/queries.py` (`GetDeepMatchBatch`), `services/api/app/player_analysis_v7/service.py`
**Conflicts with:** [`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) §5.2

`GET_DEEP_MATCH_BATCH` calls `player.matches(request: { matchIds: $matchIds })` with **no explicit page size**. The provider's default page is 10, so the operation returns at most 10 matches regardless of how many ids are passed. Both investigations independently confirmed this (TESTED: passing 8, 20, 50 and 100 ids each returned 10). The policy constant of 8 was chosen conservatively on top of a behaviour that was never a provider ceiling.

With an explicit page size the **unchanged** field selection returned 50 fully replay-covered rows and 89–100 mixed-state rows in one physical request.

**Impact:** historical backfill is roughly an order of magnitude more expensive in provider calls than it needs to be, and any code that assumes "I asked for N, I got N" is silently wrong. This is a **real defect in current behaviour**, not only a migration issue.

**Fix direction:** add an explicit page size; adopt 50 as the conservative all-covered batch and 100 for mixed-state pages; delete the arithmetic that derives request counts from 8. Needs memory, timeout and schema tests before release.

---

### G-2 — Replay parsing is entitlement-gated

**Class:** BLOCKER
**Where:** `services/api/app/analysis/deep_scan.py` (parse requests occur only inside the deep-scan path, behind `decision.allowed`); `services/api/app/analysis/service.py` (`analysis_mode`, `entitlement_decision`); `services/api/app/opendota/client.py` (docstring: the read client deliberately has *no* parse method, "which keeps the v1 no-auto-parse rule enforceable at the transport boundary"); [`../../../ARCHITECTURE.md`](../../../ARCHITECTURE.md) ("Free … never hydrates match details or requests replay parsing").

**Conflicts with:** [ADR 0004](decisions/0004-entitlement-above-the-data-foundation.md), [ADR 0003](decisions/0003-progressive-post-match-readiness.md), [`FEATURE-DATA-DEPENDENCY-MATRIX.md`](FEATURE-DATA-DEPENDENCY-MATRIX.md) §3

**Why this is a blocker.** Fourteen of the twenty V1 role metrics and all seventeen insight card types require replay-class evidence. If replay enrichment stays behind an entitlement gate, a free user's match produces N/A for most metrics, never builds a baseline (which gates at 5 priors), never reaches a trend (which needs 10 points), and shows no insight cards. That is not a reduced free tier — it is a free tier where the core product does not function. It also directly contradicts the locked product rule that Free and Pro use identical processing and methodology ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §2.9, §13.4).

**Fix direction:** move replay enrichment onto the shared fresh-match path for every tracked account. Entitlement continues to govern **history depth and what is displayed**, above persisted results. The transport-level separation of the parse client is good design and should be **kept** — what changes is *who decides*, not *where the capability lives*.

**Note:** this gap is the old product's shape, not a defect in it. The Free DNA report deliberately had a zero-parse boundary. The tracker cannot.

---

### G-3 — No evidence-readiness state on matches

**Class:** REQUIRED
**Where:** `services/api/app/storage/models.py` (`MatchRecord` has no readiness field); `services/api/app/ingestion/coverage.py`
**Conflicts with:** [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §3

`ParseCoverage` already distinguishes summary families from replay families and exposes `summary_coverage` / `replay_coverage` / `parsed` — **the vocabulary is right and the architecture adopts it**. What is missing is a persisted per-match `evidence_state` and the transitions around it, plus the acquisition/retry state behind it.

**Fix direction:** add `evidence_state` to the match record and a `match_acquisition_state` companion. Derive readiness from persisted state, not from inspecting a payload at read time.

---

### G-4 — The role classifier's support signals are replay-class

**Class:** REQUIRED
**Where:** `services/api/app/features/roles.py`
**Conflicts with:** [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §6 rule R-1

**Good news first:** the classifier is **not** dependent on a provider's proprietary position field. It reads lane role, team-relative economy ranking and ward counts. That satisfies R-2 and means role resolution is not a STRATZ dependency — a genuine strength of the current code.

The gap is readiness, not provider coupling: `obs_placed`, `sen_placed` **and lane role** are replay-class. The summary profile must use the ten-player scoreboard and weak hero priors, without assuming a lane assignment exists. A read-only audit of retained 2026-09-20 OpenDota responses found `lane_role`, `lane`, `is_roaming` and `lane_pos` absent from all 60 player rows across six unparsed snapshots, and present/non-null in all 50 rows across five parsed snapshots. These are snapshot counts, not independent-match sample sizes. See the [implementation evidence](IMPLEMENTATION-LEDGER.md#summary-translation-evidence). This corrects the earlier factual claim that lane role was summary-class; the locked immediate-role requirement remains unchanged.

**Fix direction:** give the classifier two explicit evidence profiles; record which profile produced a result; allow a re-run when evidence advances, under rules R-3 to R-7. Raise the low-confidence prompt from the final run only. **Do not change the locked Role Resolution product contract** — nothing here requires it.

---

### G-5 — No tracked-account link table; work is keyed per account-report, not per match

**Class:** REQUIRED
**Where:** `services/api/app/storage/models.py` — `AnalysisJobRecord` and `ReportRecord` are keyed on `account_id`; there is no `account_matches` link and no `follows`.
**Conflicts with:** [ADR 0002](decisions/0002-match-id-as-global-unit-of-work.md), [`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) §4

`MatchRecord` **is** already keyed on a global `match_id`, and `MatchParticipantRecord` already stores per-slot rows — so the foundation for ADR 0002 is present and correct. What is missing is the explicit tracked-account link, the per-account lifecycle state that hangs off it, and the `follows` relation.

**Fix direction:** add `account_matches` carrying the per-account lifecycle state, and `follows` as a read-side relation. Key analysis results on `(match_id, account_id, analysis_version)` rather than on a per-account report job.

---

### G-6 — No priority queue classes

**Class:** REQUIRED
**Where:** `services/api/app/workers/tasks.py` — a single Celery app with one beat schedule; no task routing, no queue separation, no priority.
**Conflicts with:** [`SCALING-RELIABILITY-AND-OPERATIONS.md`](SCALING-RELIABILITY-AND-OPERATIONS.md) §2

Without P0–P3 separation, the rule that a new user's large history import must not delay another user's newly completed match is unenforceable.

**Fix direction:** route tasks to four queues on the existing Celery/Redis stack with strict priority and a pausable P3. **No new queue technology** ([`README.md`](README.md) §9).

---

### G-7 — No per-match ingestion job table or idempotency constraints

**Class:** REQUIRED
**Where:** `services/api/app/storage/models.py` — `AnalysisJobRecord.active_key` gives per-account single-flighting, but there is no per-`match_id` job row and no per-match unique constraint.
**Conflicts with:** [`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) §8

Deduplication must be enforced by the schema, not by worker discipline. Without a unique constraint on `(match_id, job_type)`, roster overlap and retries multiply the scarcest provider budget.

**Fix direction:** add `ingest_jobs` with the unique constraint, plus the Redis locks listed in §8 of the data contracts document.

---

### G-8 — No account sync state or historical coverage record

**Class:** REQUIRED
**Where:** no `account_sync_state` equivalent exists.
**Conflicts with:** [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §3.4, [`../onboarding/SSOT.md`](../onboarding/SSOT.md) §5.4

Without a coverage record there is no honest way to produce `READY_WITH_GAPS`, no way for Profile to state what its claims are based on, and no cursor to resume a paused import from.

**Fix direction:** add per-account sync cursors, backoff and failure counters, plus historical coverage per evidence class with known gaps.

---

### G-9 — Parse-request cost is modelled at 5 rate units; the vendor documents 10

**Class:** FOLLOW-UP
**Where:** `services/api/app/analysis/budget.py` — `CostPolicy.parse_request_units: float = 5.0`
**Conflicts with:** [`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) §5.1 (VERIFIED from the vendor's own spec)

The docstring correctly calls these "deployment-specific relative units, not a baked-in monetary price", so this is not strictly a bug. But the scarcest real budget is rate units, and modelling the binding constraint at half its true cost will under-estimate exactly the thing most likely to break first.

**Fix direction:** align the parse unit cost with the documented rate accounting, and keep billing units separate from rate units — they genuinely differ (1 vs 10).

---

### G-10 — Turbo can be silently dropped by the fresh provider's default history parameters

**Class:** BLOCKER
**Where:** `services/api/app/opendota/client.py` history calls
**Conflicts with:** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §6.1, risk OR-6 in [`SCALING-RELIABILITY-AND-OPERATIONS.md`](SCALING-RELIABILITY-AND-OPERATIONS.md) §10

**Why this is a blocker.** Turbo is one of two first-class progression buckets, with its own baselines, trends, PBs and histories. The fresh provider's history endpoint defaults to excluding Turbo **silently**. TESTED 2026-09-20: with the default, an account returned 4,107 rows and was **missing 14 of its last 20 matches**; with Turbo included, 9,493 rows. Shipping this would produce a Turbo progression world that is quietly, systematically incomplete — and would look like a product bug, not a parameter bug, for a long time.

**Fix direction:** request Turbo-inclusive history explicitly wherever account history is read. Add a regression test that fails if the parameter is dropped or the provider's default changes.

---

### G-11 — Raw snapshots carry an endpoint string, not structured provider provenance

**Class:** FOLLOW-UP
**Where:** `services/api/app/storage/models.py` — `RawPayloadRecord(endpoint, source_id, payload_hash)`
**Conflicts with:** [`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) §5

Provenance is partially present — a unique constraint on `(endpoint, source_id, payload_hash)` prevents collisions in practice, and `DerivedFeatureRecord` already carries `feature_version` and `provenance_json`, which is the right shape. What is missing is an explicit **provider** and **operation version** as first-class fields, so "which provider produced this stored feature" is queryable rather than parseable out of a string.

**Fix direction:** make provider and operation version explicit columns; keep the existing digest-based dedup.

---

### G-12 — No raw-payload tiering; raw JSON lives only in the database

**Class:** OPTIONAL (until a trigger fires)
**Where:** `RawPayloadRecord.payload_json`
**Conflicts with:** [`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) §6, scaling trigger 11

Replay-derived payloads are large. At current volume this is fine and tiering would be premature. It becomes real when raw storage growth is a material cost line.

**Fix direction:** when the trigger fires, tier to compressed object storage keeping the pointer, digest, size and provenance in the database. **Never tier out `derived_features`.**

---

### G-13 — The three version boundaries are not all first-class

**Class:** FOLLOW-UP
**Where:** `ReportRecord(model_version, template_version)`, `DerivedFeatureRecord.feature_version`, `AnalysisJobRecord.model_version`
**Conflicts with:** [`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) §7

`feature_version` exists and is correct. `analysis_version` and `baseline_version` are folded into `model_version` / `template_version`, which are report-product concepts. Without all three recorded separately, plus an inputs digest, retroactive baseline changes cannot be audited — and retroactive baseline change is a locked product requirement ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §14.3).

**Fix direction:** record all three versions plus an inputs digest on every analysis result.

---

### G-14 — Role values are positions 1–5, not the four V1 roles

**Class:** FOLLOW-UP
**Where:** `services/api/app/features/roles.py` (`ROLE_LABELS` maps 1–5 to "position N")
**Conflicts with:** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §5.1

V1 has exactly four roles; positions 4 and 5 both normalise to Support, and Position 4 / Position 5 MUST NOT exist as product concepts. The classifier may keep a five-position internal representation, but the normalisation to four and the ban on leaking the five-value vocabulary into product surfaces must be explicit and tested.

**Fix direction:** add an explicit normalisation boundary with a test that no product-facing payload carries a five-value role.

---

### G-15 — No product-facing per-match lifecycle state machine

**Class:** REQUIRED
**Where:** `AnalysisJobRecord.status` / `stage` describe a *report job*, not a per-match, per-account lifecycle.
**Conflicts with:** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §4.3, [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §5

The six locked lifecycle states, ordered progression finalisation per bucket, and `WAITING_FOR_PRIOR_MATCH` have no implementation. This is expected — the iOS tracker product has not been built — but it is on the critical path for every surface.

**Fix direction:** implement as per-account state on the `account_matches` link, mapped to evidence readiness per §5.1 of the lifecycle document.

---

## 4. Summary

| Class | Items |
|---|---|
| **BLOCKER** | G-2 (replay parsing entitlement-gated), G-10 (silent Turbo drop) |
| **REQUIRED** | G-1, G-3, G-4, G-5, G-6, G-7, G-8, G-15 |
| **FOLLOW-UP** | G-9, G-11, G-13, G-14 |
| **OPTIONAL** | G-12 |

**Two blockers, and they are blockers for different reasons.** G-2 would make the free product structurally non-functional rather than merely limited. G-10 would silently corrupt an entire progression bucket in a way that looks like a product defect for a long time before anyone traces it to a query parameter.

**What is already right and should be preserved:** the global `match_id` match table; per-slot participant rows; the summary/replay coverage vocabulary; `feature_version` with provenance on derived features; the provider-neutral adapter contract in `providers/base.py`; the deliberate transport-level separation of the parse client; and `PAID_MAY_ACQUIRE_MORE_THAN_FREE = False` with tests holding it — which is [ADR 0004](decisions/0004-entitlement-above-the-data-foundation.md) already expressed in code.
