# Provider evidence

**Status:** ACTIVE — evidence, **not** product or architecture truth
**Last updated:** 2026-09-20
**Evidence date:** 2026-09-20 for everything referenced here
**Scope:** The investigations behind the architecture decisions, how they were reconciled, and the rules for using and refreshing them.

---

## What this is

Two **independent** provider investigations were run on 2026-09-20 against live matches and live APIs. They are **evidence reports**, not competing sources of truth.

| Report | Location | Emphasis |
|---|---|---|
| **Post-match ingestion probe** | [`post-match-ingestion-probe-2026-09-20.md`](post-match-ingestion-probe-2026-09-20.md) | Latency-forward. Larger measured latency cohorts; batching and complexity mechanics; scale and cost simulation. |
| **Provider architecture investigation** | [`../../../docs/evidence/provider-post-match-architecture-investigation-2026-09-20.md`](../../../docs/evidence/provider-post-match-architecture-investigation-2026-09-20.md) | Structure-forward. Provider-independence discipline; entity model; immutable snapshots; explicit refusal to convert probes into promises. |

The second report lives under the repository-wide `docs/evidence/` tree with the rest of the evidence archive. It is **linked, not copied** — duplicating it would create two versions of the same evidence.

---

## How to use them

| Question | Read |
|---|---|
| What must the system do? | The architecture documents in [`../`](../). |
| Why was that decided? | [`../decisions/`](../decisions/). |
| What was actually measured, and how confidently? | These reports. |

**Normative:**

1. These reports are **superseded on the architecture question** by [`../decisions/0001-provider-independent-hybrid-ingestion.md`](../decisions/0001-provider-independent-hybrid-ingestion.md). Where a report recommends an architecture, the ADR is what the system does.
2. Evidence tags **MUST NOT** be upgraded when a finding is restated. An INFERRED number does not become a fact by being repeated confidently. An UNKNOWN does not become known because a design would be simpler if it were.
3. These are **measurements on a date**, not guarantees. Re-verify before relying on any of them for a future commitment.
4. New probes update **evidence**. Evidence updates change routing **policy** by default. Changing architecture requires a new ADR ([`../README.md`](../README.md) §6).
5. **Do not copy probe logs or tables into feature SSOTs.** Provider numbers have exactly one operational home: [`../PROVIDER-CAPABILITIES-AND-ROUTING.md`](../PROVIDER-CAPABILITIES-AND-ROUTING.md) §5.

---

## Evidence tags

Used consistently across both reports and preserved in the architecture documents:

| Tag | Means |
|---|---|
| **TESTED** | Measured by a live request on 2026-09-20. |
| **VERIFIED** | Read from the vendor's own documentation or source on 2026-09-20. |
| **INFERRED** | Derived from tested behaviour or arithmetic. Not measured directly. |
| **UNKNOWN** | Public evidence and these probes do not answer it. |

---

## Reconciliation

The two investigations were compared point by point. **No factual contradiction was found that would make the locked architecture technically impossible.** Where they differ, it is in scope, sample size or field profile — and in both cases the more conservative reading is what the architecture documents carry.

| Topic | Report A (ingestion probe) | Report B (architecture investigation) | Resolution |
|---|---|---|---|
| **Fresh-match appearance latency** | Median ~3.4 min, min 2.9, max 4.0 (n=12), plus min 2.4 min across 100 public matches. | Did not measure first appearance; its first check was made at T+12m36s, an explicit **upper bound**, censored by an earlier decision to watch the live feed. | **Not a contradiction.** A censored upper bound does not refute a measured distribution. Report A's measurement is carried, always with n and date. |
| **Replay-processing latency** | 21/22 fresh matches processed at 6.2–7.8 min after match end (median 7.1) across two cohorts; ~23–25 s once the replay exists. | Two specimens: 31.3 s and 64.2 s from request to processed. | **Consistent.** Both describe "fast once the replay exists". Report A additionally establishes that the ~6-minute floor is Valve's replay publication, not a provider queue. |
| **Turning latency into a promise** | Proposes concrete safe copy. | Explicitly refuses numeric copy until production P50/P90/P99 over 50–100 matches across regions, modes, durations and times of day. | **Report B's discipline wins.** Copy stays qualitative. The four-way distinction — measured latency / product copy / operational SLO / contractual SLA — is normative ([`../MATCH-INGESTION-AND-LIFECYCLE.md`](../MATCH-INGESTION-AND-LIFECYCLE.md) §7). |
| **STRATZ deep batch size** | Up to 300 matches in one call via aliased pages at a mid-depth field profile; 77 via aliased per-match at the same depth. | 50 fully replay-covered rows and 100 mixed-state rows with the exact current production selection; 100 is the hard page cap. | **Different field profiles, both correct.** Selection breadth drives cost, not page size. Production guidance is the conservative number: **50 proven all-covered, 100 proven mixed**. Either destroys the shipped 8. |
| **Why the shipped batch size is 8** | Frames it as a wrong assumption plus a missing page-size argument. | Identifies the same root cause: the operation omits an explicit page size, so the provider's default page of 10 applies. | **Agreement.** Recorded as gap [G-1](../IMPLEMENTATION-GAPS.md). |
| **STRATZ freshness** | 1/20 present at T+5–11 min; 0/20 at T+12 min. | One live specimen absent through 14 polls to T+20m05s; a player whose newest STRATZ row was ~111 h old while the fresh provider's was ~2 h. | **Agreement.** STRATZ is not a fresh-match source. Both note their samples are small; the conclusion does not depend on precision. |
| **STRATZ parse-state semantics** | `parsedDateTime` marks ingestion; `statsDateTime` / `isStats` marks replay stats; they diverged by 45+ min. | Notes parsed coverage is selected by what STRATZ retained and parsed, and that missingness must be measured rather than conditioned on. | **Complementary.** Both are carried: gate on the stats marker, and measure coverage rather than assume it. |
| **Detection payload contents** | Uses the recent-matches endpoint for detection. | Notes that endpoint returns no items, and that the projectable history endpoint is the better instant-card request. | **Report B's detail is carried.** The detection payload is **not** automatically the full Stage-1 card. Which endpoint serves Stage 1 is an adapter-level routing detail, recorded in [`../PROVIDER-CAPABILITIES-AND-ROUTING.md`](../PROVIDER-CAPABILITIES-AND-ROUTING.md). |
| **Turbo exclusion** | The fresh provider's history endpoint silently drops Turbo by default: 4,107 rows vs 9,493, missing 14 of the last 20 matches. | Not covered. | **Report A only, and important.** Turbo is a first-class progression bucket. Carried as risk [OR-6](../SCALING-RELIABILITY-AND-OPERATIONS.md). |
| **Empty history vs private account** | Covers the public-match-data setting as an onboarding concern. | Adds a failure specimen: a refresh accepted, then 29 polls over five minutes still empty. "Private or unavailable" must be a separate state from "still syncing". | **Report B's detail is carried** into the degradation contract. |
| **Architecture recommendation** | OpenDota-first fresh, STRATZ-first historical. | Provider-independent hybrid orchestrator; provider order must remain a measured policy. | **Both are adopted, at different levels.** The provider-independent canonical model is architecture (Report B's framing). OpenDota-first fresh routing is current policy (Report A's recommendation). [ADR 0001](../decisions/0001-provider-independent-hybrid-ingestion.md) keeps these deliberately separate. |
| **Valve direct acquisition** | Untested — no key configured. Worth a bounded look. | Untested — no key configured. A worthwhile bounded pilot, not a justified production dependency. | **Agreement.** Recorded as open test T-1. |

---

## Sample-size honesty

Both reports state their own limits, and those limits are carried forward rather than smoothed away:

- The latency cohorts are tens of matches, not thousands, and were collected on one day.
- The cross-provider agreement check covers a small number of overlapping matches. It is a useful cross-check, **not** proof that all fields and all matches agree.
- The deduplication rate used in the scale simulation is an **estimate**, not a measurement (open test T-4).
- The exact replay-availability boundary between 60 and 180 days is **UNKNOWN** (open test T-2) — and it overlaps onboarding's 90-day bootstrap window, which makes it the most product-relevant unknown on the list.
- No all-replay-covered 100-row deep page has been verified under memory and timeout gates (open test T-3).

---

## Refreshing this evidence

1. Run the probe. Record it under `docs/evidence/` with its date, exactly as these two were.
2. Update the operational numbers in [`../PROVIDER-CAPABILITIES-AND-ROUTING.md`](../PROVIDER-CAPABILITIES-AND-ROUTING.md) §5 and bump its `Evidence date`.
3. Update this reconciliation if the new evidence changes a resolution.
4. **Only if the architecture must change:** write a new ADR, supersede the affected one, then run the SSOT propagation audit.
