# Architecture — Dota Tracker V1 (native iOS)

**Status:** ACTIVE — authoritative architecture contract
**Last updated:** 2026-09-20
**Scope:** How match data is acquired, stored, enriched, analysed and delivered to the iOS client — and the rules that keep that shape stable while providers, scale and monetisation change.
**Owner:** Architecture (product owner signs off on the decisions; engineering owns the mechanics)
**Relationship to product:** This area defines **how the system behaves**. [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) and the feature SSOTs define **what the product means**. Neither overrules the other; they answer different questions. See §5.

---

## 1. One-minute summary (no backend knowledge required)

When you finish a Dota match, our backend notices it, saves it, and shows it to you — **in two stages**.

**Stage 1, a few minutes after the match ends.** We learn the basic result: who won, your hero, your K/D/A, farm, GPM/XPM, your items, the draft, all ten players. Your match appears in the app and you can open it. Nothing here needs a replay file.

**Stage 2, usually a few minutes after that.** Valve publishes the match replay. We ask for it to be processed, and that unlocks everything that needs a timeline: laning, gold and XP curves, item timings, wards, stacks, objectives, teamfights, kill and death context. This is where the real analysis — your metrics, your comparisons, your Personal Bests, your insight cards — is produced.

**Three rules make this work and must not be broken:**

1. **The app never calls a data provider.** The iOS app talks only to our backend, and reads what our backend has already stored. If a provider goes down, we acquire less data — the app does not break.
2. **Work is done once per match, not once per user.** If five of our users are in the same Dota match, we fetch and process that match **once** and attach five people to it. This is what makes the system affordable at scale and what makes friends/social features cheap later.
3. **Free and Pro use the same pipeline.** Paying changes how much history you can see and how much we synthesise for you. It never changes how a match is acquired, processed or measured. The backend must be viable even if nobody ever pays.

**Who does what today:** OpenDota is our primary source for *fresh* matches (it is fast, cheap and it lets us request a replay parse on demand). STRATZ is our source for *history* that is older than Valve's replay window, for population reference data, and as a fallback. That split is a **policy** we measured on 2026-09-20 — it can change without rewriting anything, because the system is built provider-independent.

---

## 2. Reading order

Read in this order the first time. After that, jump straight to what you need.

| # | Document | Read it when |
|---|---|---|
| 1 | **this README** | Always first. |
| 2 | [`SYSTEM-ARCHITECTURE.md`](SYSTEM-ARCHITECTURE.md) | You need the system boundary, the components, the quality goals, or a C4 view. |
| 3 | [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) | You are touching detection, enrichment, parse scheduling, retries, or anything about *when* data becomes available. **The evidence-readiness model lives here.** |
| 4 | [`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) | You are touching the data model, storage, provenance, deduplication, idempotency or reproducibility. |
| 5 | [`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) | You need to know which provider can supply a capability, or want to change routing policy. |
| 6 | [`FEATURE-DATA-DEPENDENCY-MATRIX.md`](FEATURE-DATA-DEPENDENCY-MATRIX.md) | You are building or changing a screen and need to know what must exist before it can render. |
| 7 | [`SCALING-RELIABILITY-AND-OPERATIONS.md`](SCALING-RELIABILITY-AND-OPERATIONS.md) | You are touching queues, rate limits, failure handling, cost, observability or scale. |
| 8 | [`IMPLEMENTATION-GAPS.md`](IMPLEMENTATION-GAPS.md) | You are about to implement any of this. It lists where current code disagrees with these documents. |
| 9 | [`decisions/`](decisions/) | You want to know *why*, or you intend to change a locked decision. |
| 10 | [`evidence/`](evidence/) | You need the measurements behind a claim, or you are re-verifying dated provider numbers. |

---

## 3. Authoritative-document map

One home per kind of truth. If you find the same rule stated normatively in two places, that is a defect — fix it by deleting one and linking.

| Kind of truth | Authoritative home |
|---|---|
| What a product concept *means* (role, metric, baseline, PB, trend, entitlement, lifecycle state) | [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) |
| What a screen must contain and how it behaves | that feature's `SSOT.md` |
| System boundary, components, quality goals | [`SYSTEM-ARCHITECTURE.md`](SYSTEM-ARCHITECTURE.md) |
| **Evidence-readiness states** and the fresh-match runtime sequence | [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) |
| Canonical data model, identity, provenance, version boundaries, dedup keys | [`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) |
| Which provider can do what; current routing policy; provider quotas and prices | [`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) |
| Which readiness class a UI block needs | [`FEATURE-DATA-DEPENDENCY-MATRIX.md`](FEATURE-DATA-DEPENDENCY-MATRIX.md) |
| Queues, priorities, backpressure, degradation, observability, cost, scaling triggers | [`SCALING-RELIABILITY-AND-OPERATIONS.md`](SCALING-RELIABILITY-AND-OPERATIONS.md) |
| Why an architectural choice was made | [`decisions/`](decisions/) |
| Measured provider behaviour, with dates | [`evidence/`](evidence/) |
| Insight-card algorithms and context-adjustment parameters | the two engineering annexes named in [`../README.md`](../README.md) |

**Provider quota numbers, prices and latency measurements live in exactly two places:** `PROVIDER-CAPABILITIES-AND-ROUTING.md` (the dated operational summary) and `evidence/` (the raw findings). They MUST NOT be copied into feature SSOTs. A feature SSOT says *"this needs replay-class evidence"*, never *"this needs `GET /matches/{id}` with `version != null`"*.

---

## 4. Rules for future agents

Read these before changing ingestion, analysis, Match Lifecycle, Home, History, Match Detail, Profile, Progress, role resolution, social/following, or subscription behaviour.

1. **Read this index first.** If your change touches any surface listed above, read the relevant architecture document before editing a feature SSOT or writing code.
2. **Never call a provider from iOS UI code.** The client reads Dota Tracker's own API. No OpenDota or STRATZ call may originate from a product screen. ([ADR 0001](decisions/0001-provider-independent-hybrid-ingestion.md))
3. **Never make STRATZ mandatory on the fresh-match happy path** without a new accepted ADR. ([ADR 0001](decisions/0001-provider-independent-hybrid-ingestion.md))
4. **Never build a provider-shaped product or domain model** when a canonical concept exists. Normalise at the adapter boundary; the analysis engine consumes Dota Tracker concepts. ([`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md))
5. **Never duplicate ingestion per user.** `match_id` is the unit of work. Five users in one match is one fetch, one parse, one stored match, five links. ([ADR 0002](decisions/0002-match-id-as-global-unit-of-work.md))
6. **Never block basic Match Detail on replay parsing.** Stage 1 renders from summary-class evidence alone. ([ADR 0003](decisions/0003-progressive-post-match-readiness.md))
7. **Never treat missing deep data as zero.** Missing evidence stays missing — N/A with a reason. This is a foundation invariant ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §2, §8), not a nicety.
8. **Never edit an accepted ADR to change a decision.** Supersede it with a new ADR. See §6.
9. **When architecture changes, run the SSOT dependency audit.** Each normative architecture document ends with a `## Product/SSOT dependents` section. Update every document listed there in the same change.
10. **Provider limits, prices and latencies are dated evidence, not guarantees.** Every one of them carries an evidence date. Re-verify before relying on it for a future commitment, and never turn a probe measurement into a customer-facing promise (§7 of [`SCALING-RELIABILITY-AND-OPERATIONS.md`](SCALING-RELIABILITY-AND-OPERATIONS.md)).
11. **Never architect an LLM into the runtime post-match pipeline.** Analysis is deterministic and reproducible from versioned inputs. ([ADR 0005](decisions/0005-deterministic-analysis-no-runtime-llm.md))
12. **Never split the pipeline by subscription tier.** Entitlement is applied above persisted analysis, never below it. ([ADR 0004](decisions/0004-entitlement-above-the-data-foundation.md))

---

## 5. Architecture versus product: the boundary

These two bodies of documentation answer different questions and MUST NOT absorb each other.

```text
architecture/          answers: HOW does the system behave?
  ├─ what data exists, when, and from where
  ├─ what is stored, keyed and versioned
  ├─ what happens when something fails
  └─ what it costs and how it scales

app_foundation/ + feature SSOTs   answers: WHAT does the product mean?
  ├─ what a role, metric, baseline, trend, PB is
  ├─ what a screen must contain
  ├─ what the product may and may not claim
  └─ which states a user must be able to distinguish
```

**Where they meet** is a single, narrow vocabulary: the **evidence-readiness classes** defined in [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §3. A feature SSOT is allowed to say *"this block requires replay-class evidence"*. It is not allowed to say anything about providers, endpoints, quotas or queues.

**Conflict rule.** If an architecture document and a feature SSOT disagree:

- about **product meaning** (what a thing is, what may be claimed, what the user must be able to tell apart) → the SSOT wins; fix the architecture document.
- about **system behaviour** (when data exists, what is stored, what happens on failure) → the architecture document wins; fix the SSOT.
- if the disagreement is that the architecture makes a locked product rule **technically impossible** → do not silently pick one. Write an ADR, get an owner decision, then propagate.

---

## 6. How architecture decisions change

An accepted ADR is **immutable**. New evidence does not rewrite it.

```text
new evidence
  → write a NEW ADR: state the evidence, the new decision, its consequences
  → mark the affected ADR "Superseded by ADR NNNN"
  → update the affected architecture documents
  → run the SSOT dependency audit (§4 rule 9)
  → record the evidence under evidence/ with its date
```

Provider probes may update *evidence* freely and often. Evidence updates change routing **policy**, not architecture, unless a new ADR says so. The point of the provider-independent design is that a routing change is a configuration-level decision, not a rewrite.

Correcting a typo, a broken link, or a factual error *about what the decision was* is allowed in place. Changing what was decided is not.

---

## 7. Documentation conventions

Kept deliberately light. Only metadata that earns its place.

**Every architecture document carries a header block:**

```text
**Status:**        ACTIVE | DRAFT | SUPERSEDED
**Last updated:**  YYYY-MM-DD
**Scope:**         one sentence
**Depends on:**    links to the documents it builds on
**Evidence date:** only on documents containing provider measurements
```

**Every normative architecture document carries a `## Product/SSOT dependents` section** listing the feature SSOTs that must be re-checked when it changes. This is the propagation mechanism. (`IMPLEMENTATION-GAPS.md` is exempt — it is a burn-down list, not a contract, and nothing depends on it.)

**Every feature SSOT affected by this architecture carries an `## Architecture dependencies` section** linking back to the specific sections it relies on — not restating them.

**Diagrams are Mermaid**, consistent with the rest of the repository (`legacy/docs/architecture/`, `ARCHITECTURE.md`). A diagram exists only where it removes ambiguity that prose leaves. No diagram duplicates a paragraph.

**Evidence tags** are preserved verbatim from the source investigations and MUST NOT be upgraded:

| Tag | Means |
|---|---|
| **TESTED** | Measured by a live request on the stated date. |
| **VERIFIED** | Read from the vendor's own documentation or source on the stated date. |
| **INFERRED** | Derived from tested behaviour or arithmetic. Not measured directly. |
| **UNKNOWN** | Public evidence and our probes do not answer this. |

An INFERRED or UNKNOWN item never becomes a fact because it was restated confidently somewhere else.

**Normative language** follows RFC 2119 (MUST / MUST NOT / SHOULD / MAY), the same as the feature SSOTs.

---

## 8. Product/SSOT dependents

Architecture changes propagate to these documents. Each carries an `## Architecture dependencies` section pointing back here.

| Document | Why it depends on architecture |
|---|---|
| [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) | Match lifecycle, evidence readiness, role classification timing, N/A semantics, rebuild-without-provider-calls. |
| [`../onboarding/SSOT.md`](../onboarding/SSOT.md) | Bootstrap acquisition, historical replay coverage, cold-start readiness, Pro backfill. |
| [`../home/SSOT.md`](../home/SSOT.md) | Today's Matches appearing at summary readiness; update-on-ready behaviour. |
| [`../history/SSOT.md`](../history/SSOT.md) | Rows driven by persisted records; row states across readiness. |
| [`../match_detail/SSOT.md`](../match_detail/SSOT.md) | Two-stage rendering, terminal replay-unavailable state, partial-data rules. |
| [`../progress/SSOT.md`](../progress/SSOT.md) | Which metrics need replay evidence; when progression recomputes. |
| [`../profile/SSOT.md`](../profile/SSOT.md) | Historical coverage, what long-horizon claims may assume, no provider calls on render. |
| [`../settings_account/SSOT.md`](../settings_account/SSOT.md) | Entitlement above the pipeline; Pro backfill acquisition; data-access recovery. |

---

## 9. What is deliberately not here

- **Deployment topology, instance counts, worker counts, DB partitioning.** These are scaling mechanics with documented trigger points in [`SCALING-RELIABILITY-AND-OPERATIONS.md`](SCALING-RELIABILITY-AND-OPERATIONS.md) §9, not pre-launch commitments.
- **A code-level C4 model.** Two levels (System Context, Container) plus runtime sequences is what future agents actually need. Component-level structure lives in code.
- **New queue or storage technology.** The architecture runs on the existing stack (FastAPI, PostgreSQL, Redis, Celery). Introducing new infrastructure for documentation elegance is forbidden.
- **A challenge/achievement contract.** None exists. See [`../home/SSOT.md`](../home/SSOT.md) §5. The dependency matrix records how such a feature *would* classify its data needs, without inventing the feature.
