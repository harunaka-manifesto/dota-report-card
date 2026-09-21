# Scaling, Reliability and Operations

**Status:** ACTIVE — authoritative
**Last updated:** 2026-09-20
**Scope:** Queue priorities, rate limiting, backpressure, circuit breakers, caching, storage policy, the failure/degradation contract, the observability contract, the cost model, scaling stages with trigger points, and known operational risks.
**Depends on:** [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) · [`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) · [`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md)
**Evidence date:** 2026-09-20

---

## 1. Plain-English summary

**What is this?** The rules that stop the system from starving the important work, and the list of what has to keep working when something breaks.

**Why did we choose it?** Because the most expensive thing we can do — importing somebody's thousand-match history — is also the least urgent, and the most urgent thing — one person's match that just ended — is also the cheapest. If those two share a queue without priorities, the cheap urgent thing waits behind the expensive patient one.

**What does it mean for the user?** Your just-finished match is always first in line. Somebody else's history import never makes you wait.

**What should future agents not break?** The priority order, the pausability of historical work, and the rule that a degradation costs a *capability*, never the whole app.

---

## 2. Queue priorities and backpressure

Four strict priority classes on the existing Celery/Redis stack. **No new queue technology.**

| Class | Contents | Notes |
|---|---|---|
| **P0** | Foreground account sync / latest-match detection for a user with the app open. | Cheap, one call, debounced per account. Effectively unbounded. |
| **P1** | Fresh-match enrichment: replay-processing request and replay-payload fetch for recent matches. | The majority of the enrichment budget. |
| **P2** | Retries, and lower-priority enrichment of not-quite-fresh matches; followed-but-unowned accounts. | A controlled share, so retries cannot starve fresh work or be starved by it. |
| **P3** | Historical imports and backfills, both providers. | **Must be pausable.** Smallest share. Hard-paused under load. |

### 2.1 Rules (normative)

| # | Rule |
|---|---|
| Q-1 | **Fresh user experience always wins.** P0 and P1 are never delayed by P2 or P3. |
| Q-2 | **P3 MUST be pausable mid-import** and resumable from its cursor without duplicating work or losing coverage. |
| Q-3 | A new user's large history import **MUST NOT** delay another user's newly completed match. This is the specific failure this section prevents. |
| Q-4 | When provider quota or worker capacity is constrained, degrade in this order: **P3 slows or pauses → P2 gets a reduced share → P1 continues → P0 continues.** |
| Q-5 | P3 is hard-paused whenever P1 queue depth or oldest-P1-job-age exceeds its threshold, or when a provider's rate budget is above its utilisation threshold. |
| Q-6 | Thresholds are **operational configuration**, tuned from the metrics in §7. They are not product meaning and not in any SSOT. |
| Q-7 | Every job is idempotent and uniquely constrained ([`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) §8). Backpressure that drops and re-enqueues must be safe by construction. |
| Q-8 | Ordering constraints from the product are respected **within** a priority class, not across it: progression finalisation is ordered per progression bucket, and the other bucket never blocks ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §4.4). |

---

## 3. Rate limiting and provider budgets

### 3.1 Token buckets (normative)

| # | Rule |
|---|---|
| RL-1 | Every provider has a **token bucket** in front of it, sized from that provider's **response headers**, never from its published documentation. |
| RL-2 | **Replay-processing requests get their own bucket**, separate from reads. They cost 10 rate units each against the fresh provider's budget while costing one unit of billing — so a shared bucket mis-measures the binding constraint by 10×. ([`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) §5.1.) |
| RL-3 | Remaining-quota headers are read on **every** response and drive the bucket. A provider that reports less headroom than we assumed wins. |
| RL-4 | A reserve share of each provider's budget is **held back** for retries and incident recovery. Steady-state work never consumes 100%. |
| RL-5 | STRATZ jobs are **single-flighted from a stable egress IP**. The token is IP-bound; concurrent jobs from different addresses produce hard failures. |
| RL-6 | Processing requests are **scheduled and spread**, never issued in a burst. They are naturally spread by the replay-availability delay; the scheduler must not undo that. |

### 3.2 The binding constraint

Money is not the constraint; **rate units are**. At the modelled high end, replay-processing requests alone can exceed the fresh provider's per-minute rate budget well before the monthly bill becomes interesting. Consequences:

- The processing bucket is the thing to monitor and the thing to alarm on.
- Spreading and deduplication are load-bearing, not optimisations.
- Global `match_id` deduplication directly reduces this constraint in proportion to how many of our users share matches.

---

## 4. Batching, caching and storage

| Concern | Policy |
|---|---|
| **Batching** | Historical reads batch aggressively where the provider supports it. Batch sizes come from [`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) §5 and are reduced on error, never increased on optimism. Fresh-path work does **not** batch across users — it is already deduplicated per match. |
| **Read cache** | The database **is** the cache for product reads. A screen always reads persisted state. Redis holds the account-sync debounce, rate-limit buckets and job locks — not product data. |
| **Provider response cache** | Keyed by provider + operation + version + subject ([`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) §5). |
| **Population reference data** | Cached and **versioned as a snapshot**. Refreshed on a schedule measured in days, not per match, not per user. A refresh failure keeps the previous snapshot; it never degrades to a wrong number ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §20). |
| **Raw snapshot storage** | Tiered per [`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) §6: hot for recent, compressed object storage for older, deleted when no longer a report input. |
| **Derived features** | Permanent, in the database. Small. Never tiered out. |

---

## 5. Circuit breakers, retries and idempotency

| # | Rule |
|---|---|
| CB-1 | Each provider sits behind a **circuit breaker**. Repeated failures open it; work reroutes or queues rather than hammering. |
| CB-2 | An open breaker is an **operational** state. It changes routing and may change latency. It **MUST NOT** change what the product claims, and **MUST NOT** turn stored data into an empty or zeroed state. |
| CB-3 | Retries are **bounded with backoff**. Exact ladders are implementation policy ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §4.5). |
| CB-4 | A provider success followed by an internal failure retries **internal work only**. It never refetches source truth. |
| CB-5 | Retry and reroute are safe because every job is idempotent and uniquely keyed. |
| CB-6 | Polling stops on terminal conditions: private/unavailable account, replay horizon passed, terminal processing failure, or a configured deadline. **Unbounded polling is forbidden.** |
| CB-7 | Neither provider offers a webhook (VERIFIED by absence from both API surfaces, 2026-09-20). The architecture is pull-only by necessity, and the polling policy above is what keeps that affordable. |

---

## 6. Failure and degradation contract (normative)

**The governing principle: degrade by capability, never by product.**

```text
replay enrichment unavailable   ≠  Match Detail unavailable
STRATZ unavailable              ≠  fresh matches unavailable
historical import incomplete    ≠  Home unavailable
one provider down               ≠  the app is down
```

| Failure | System behaviour | What the user sees |
|---|---|---|
| Fresh detection slow | Retry ladder absorbs it. Stored matches unaffected. | Nothing unusual; the match appears slightly later. |
| Fresh provider unavailable | Breaker opens. Detection may fall back at worse freshness. Enrichment queues. | Known history fully usable. Never "you have no matches". Sync state reflects the problem honestly. |
| Replay processing delayed | Match stays `REPLAY_PENDING`; bounded retry ladder. | Stage 1 complete. Deep sections show an honest processing affordance — **not** an endless spinner. |
| Replay does not exist (abandon, custom lobby, missing) | `REPLAY_UNAVAILABLE` immediately. Analysis runs on summary-class evidence. | Stage 1 complete and self-sufficient. Deep sections state, once, that the detailed breakdown isn't available. |
| Replay processing permanently fails | Ladder exhausts → `REPLAY_UNAVAILABLE`. | Same as above. Not an error, not a Retry prompt. |
| STRATZ unavailable | Fresh path untouched. Backfill pauses. Reference data served from cached snapshot. | Historical depth may be incomplete and is stated as such. Nothing else changes. |
| STRATZ quota exhausted | Backfill pauses until the window resets. | An in-progress import continues later. Coverage is reported honestly, never claimed complete. |
| STRATZ lacks a fresh match | Expected. Not an error. | Nothing. Never treat STRATZ absence as proof a match does not exist. |
| Historical backfill incomplete | Recorded as a coverage gap ([`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §3.4). | Long-horizon surfaces state what their claims are based on. They **MUST NOT** imply complete lifetime evidence. |
| Providers disagree | Both raw snapshots kept. Dependent analysis **quarantined**, not merged. | The affected finding is absent, not wrong. |
| Account match data private/unavailable | Distinguished from "still syncing" — these are different states ([`../onboarding/SSOT.md`](../onboarding/SSOT.md) §5.4). | `DATA_ACCESS_BLOCKED` recovery guidance. Link retained, Pro untouched. |
| Upstream quota reached | Token bucket throttles. Reserve protects retries. P3 pauses first. | Fresh matches keep working. |
| Queue backlog grows | P3 pauses, P2 share reduces, P1/P0 continue. Alarm on oldest-job age by priority. | Deep analysis may take longer. Stage 1 unaffected. |
| Stored provider data stale | Last successful cursor and source timestamp retained. | Freshness is in doubt, **never presented as current**. Known data stays usable and truthful. |

**Two cross-cutting rules:**

1. A degraded state **MUST NOT** be rendered as zero, as a neutral default, or as an empty account ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §2).
2. A degraded state **MUST NOT** be described to the user in provider or pipeline vocabulary ([`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §9).

---

## 7. Observability contract

**What must be measurable.** This defines the contract, not an implementation. Do not build a metrics platform from this document; do make sure nothing here is unmeasurable by construction.

### 7.1 Latency — the readiness ladder

Each as **P50 / P90 / P99**, sliced at minimum by region, game mode, match duration band and time of day:

- match discovery latency (match end → `match_id` known);
- summary-ready latency (match end → `SUMMARY_READY`);
- processing-request latency (eligible → request accepted);
- replay-ready latency (match end → `REPLAY_READY`);
- analysis-ready latency (match end → persisted analysis / lifecycle `READY`).

### 7.2 Pipeline health

- replay-processing success and failure rate; `REPLAY_UNAVAILABLE` rate and its reasons;
- retry rate by job type;
- queue depth **by priority class**;
- **oldest job age by priority class** — the single best early warning for starvation;
- P3 pause events, duration and cause.

### 7.3 Providers

- error rate by provider and operation;
- 429 / quota events;
- remaining quota, where the provider exposes it;
- circuit-breaker open/close events;
- **provider disagreement rate** on semantically equivalent fields;
- stale-history rate (accounts whose last successful sync is older than its target).

### 7.4 Coverage

- historical-backfill coverage per account and in aggregate;
- replay-class coverage of historical matches (the property that determines whether long-horizon analysis is honest);
- per-bucket, per-role baseline-readiness distribution — the real measure of whether onboarding is working.

### 7.5 Efficiency and cost

- **dedup ratio**: unique matches ÷ account-match links;
- **provider calls per unique match** — the headline efficiency number;
- provider cost per day, per DAU, and per processed match;
- rate units consumed per minute, per provider, split reads vs processing requests.

### 7.6 The four-way distinction (normative)

Restated here because it is an operations concern, not only a copy concern. See [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §7.

| | Measured latency | Product copy | Operational SLO | Contractual SLA |
|---|---|---|---|---|
| Source | probe or production metric, dated, with n | product decision | engineering target | commercial commitment |
| Binds us? | no | yes, to users | yes, internally | yes, legally |
| Exists today? | yes (2026-09-20) | qualitative only | **not yet** | **none — do not create one** |

An SLO may be set **only** from production P50/P90/P99 over a representative sample. A single probe is never an SLO and never a promise.

---

## 8. Cost model

| Dimension | Scales with | Does **not** scale with |
|---|---|---|
| Fresh provider calls | unique matches involving tracked accounts | number of our users in a match; screen views; follower edges |
| Replay-processing requests | unique matches needing enrichment | users per match |
| STRATZ calls | new-account onboarding + Pro backfill depth + periodic reference refresh | matches played; DAU |
| Storage — raw | unique matches × retention tier | users |
| Storage — derived features | unique match-players, permanently | analyses run |
| Analysis compute | tracked account × match × analysis version | provider calls |

**Cost-control mechanisms, in order of leverage:** global `match_id` deduplication → account-sync debouncing → not spending a call to duplicate evidence we hold → scheduling processing requests instead of bursting → batching historical reads → not re-calling providers to recompute.

**The monetary model is predictable and observable, which is the point.** Per-call pricing on the fresh provider means cost per processed match is a number we can watch daily (§7.5) and act on, rather than a surprise. Modelled projections are in [`evidence/`](evidence/); they are **models, not guarantees**, and their deduplication assumption is explicitly an estimate awaiting production measurement (T-4 in [`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) §7.3).

---

## 9. Scaling stages and trigger points

**Correct now** vs **scale later**. Deploying the right-hand column before its trigger fires is waste, not prudence.

| # | Mechanism | Must be correct **now** | Deploy when |
|---|---|---|---|
| 1 | Global `match_id` dedup | ✅ — it is the data model | — |
| 2 | Account-sync debouncing | ✅ | — |
| 3 | Idempotent, uniquely-keyed jobs | ✅ | — |
| 4 | Priority classes P0–P3 | ✅ | — |
| 5 | Provider token buckets, incl. a separate processing bucket | ✅ | — |
| 6 | Circuit breakers | ✅ | — |
| 7 | Versioned derived features | ✅ | — |
| 8 | Evidence-readiness semantics | ✅ | — |
| 9 | Backpressure thresholds (P3 pause) | mechanism yes, tuning no | tune from observed oldest-job-age |
| 10 | Horizontal worker scaling | — | P1 oldest-job age exceeds target under normal load |
| 11 | Raw payload → object storage tiering | policy yes | raw storage growth becomes a material cost line |
| 12 | Database partitioning / read replicas | — | match or read volume makes single-instance latency the bottleneck |
| 13 | Multiple provider tokens / egress strategy | — | a provider's per-token budget becomes the binding constraint |
| 14 | Materialised social feed | — | measured read load on the fan-out-on-read query requires it |
| 15 | Dedicated queue infrastructure | — | Celery/Redis measurably fails the priority contract |
| 16 | Direct Valve acquisition path | — | after the bounded pilot (T-1) shows it is worth the complexity |

**Normative:** a scaling mechanism is deployed when its trigger fires and the metric that fired it is recorded. "We might need it eventually" is not a trigger.

---

## 10. Known operational risks

| # | Risk | Why it matters | Current mitigation |
|---|---|---|---|
| OR-1 | Replay-processing requests are the scarcest budget and scale directly with unique matches. | The fresh deep path stops at the ceiling. | Dedicated bucket, dedup, scheduling, spread. Monitor as the primary capacity metric. |
| OR-2 | The fresh provider is a single point of failure for detection. | An outage stops new matches being discovered. | Fallback detection behind a breaker, at worse freshness. Stored data unaffected. |
| OR-3 | STRATZ's token is IP-bound. | A multi-IP backend produces hard failures. | Stable egress IP; single-flighted jobs. Verify before any infrastructure change to egress. |
| OR-4 | Published provider limits disagree with measured limits. | Planning against docs over-commits capacity. | Plan against headers; read remaining quota on every response. |
| OR-5 | The replay horizon boundary is **UNKNOWN** between 60 and 180 days, and onboarding's bootstrap window is 90 days. | Part of the bootstrap window may be unreachable by the fresh replay route. | Historical replay acquisition is treated as a functional requirement, not an optimisation. Test T-2 is open. |
| OR-6 | A silent Turbo drop in the fresh provider's default history parameters. | Turbo is a first-class progression bucket. Silent loss is a correctness bug affecting a whole progression world. | Adapter must request Turbo-inclusive history explicitly. Verify with a test that fails on drift. |
| OR-7 | Provider commercial terms for volume and raw retention are unresolved. | Legal exposure at public launch. | OD-1, OD-6, SZ-10 flagged launch-blocking. See [`PROVIDER-CAPABILITIES-AND-ROUTING.md`](PROVIDER-CAPABILITIES-AND-ROUTING.md) §7. |
| OR-8 | The modelled deduplication rate is an estimate. | Cost projections inherit its error. | Measure in production (§7.5). Cost model degrades gracefully if dedup is lower than modelled. |
| OR-9 | No provider webhook exists. | Everything is polling; polling has a floor and a cost. | Bounded, activity-aware polling with terminal stop conditions (CB-6). |

---

## 11. Product/SSOT dependents

| Document | What to re-check when this document changes |
|---|---|
| [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) | §4.2 sync states, §4.5 retry semantics, §19 implementation-policy deferrals. |
| [`../match_detail/SSOT.md`](../match_detail/SSOT.md) | Degraded and terminal states on the surface most affected. |
| [`../home/SSOT.md`](../home/SSOT.md) | §8 Home-level states under degradation. |
| [`../history/SSOT.md`](../history/SSOT.md) | §9 states under sync error and offline. |
| [`../onboarding/SSOT.md`](../onboarding/SSOT.md) | §5.4 bootstrap outcomes; private-vs-syncing distinction. |
| [`../settings_account/SSOT.md`](../settings_account/SSOT.md) | §4 data-access recovery. |
