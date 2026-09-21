# Provider Capabilities and Routing

**Status:** ACTIVE — authoritative
**Last updated:** 2026-09-20
**Scope:** What each provider can supply, the current routing policy, fallback behaviour, provider operational limits, and the provider questions that remain unanswered.
**Depends on:** [`SYSTEM-ARCHITECTURE.md`](SYSTEM-ARCHITECTURE.md) · [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md)
**Evidence date:** 2026-09-20 — all measurements below are from that date. **Re-verify before relying on them for a future commitment.**

---

## 1. Plain-English summary

**What is this?** The list of what each of our two data suppliers can actually do, and who we currently ask for what.

**Why did we choose it?** We measured both on the same day against the same matches. One is much better at *fresh*; the other is much better at *old*. Neither is better at everything, and both have commercial unknowns. So we use each for what it is good at and keep the ability to swap.

**What does it mean for the user?** Nothing directly — and that is the point. Users never see a provider name.

**What should future agents not break?** Do not assume "advanced analysis = STRATZ". Most sophisticated-sounding analysis needs replay-class evidence, not a specific vendor. Check the matrix before adding a provider dependency.

---

## 2. The distinction that matters most

**Provider preference is policy. The canonical internal model is architecture.**

- **Architecture** (locked, changed only by ADR): providers sit behind adapters; the canonical model is provider-independent; the client never calls a provider; `match_id` is the unit of work.
- **Policy** (this document, changeable on evidence): *which* provider we currently ask for *which* capability.

Conflating the two is the specific failure this document exists to prevent. "We use OpenDota for fresh matches" is a sentence about policy. It must never harden into a sentence about architecture.

---

## 3. Current routing policy

| Work | Current provider | Why |
|---|---|---|
| Fresh-match detection | **OpenDota** | Fastest observed appearance; cheap; explicit paid scaling path. |
| Fresh summary-class evidence | **OpenDota** | Arrives with detection; no replay processing required. |
| Fresh replay-class evidence | **OpenDota** | We can *request* processing on demand; measured fast and reliable on fresh matches. |
| Historical summary-class backfill | **OpenDota** | An account's full summary history is a single call. |
| Historical replay-class backfill | **STRATZ** | Already holds parsed matches beyond Valve's replay horizon. OpenDota structurally cannot recreate them. |
| Population / baseline reference data | **STRATZ** | Provides population aggregates by hero and position. Cached and versioned; not a per-match cost. |
| Fresh-path fallback | **STRATZ** | Behind a circuit breaker, at degraded latency, when the primary is unavailable. |

**STRATZ spend per fresh match is zero.** STRATZ is a per-account onboarding/backfill cost plus a small global periodic cost for reference data. It is not a per-match cost, and making it one requires a new ADR.

### 3.1 Provider selection rules (normative)

| # | Rule |
|---|---|
| P-1 | Do **not** spend a call on a provider merely to duplicate evidence another provider has already supplied for the same match. |
| P-2 | Use a provider-specific capability **only** when an enabled feature demonstrably requires it, and only after the requirement is recorded in §4.3. |
| P-3 | Route by **capability + current availability + remaining quota**, never by habit and never by a hard-coded vendor name inside product or analysis code. |
| P-4 | Never use one provider as the *detection* mechanism for another provider's enrichment. Detection and enrichment are separately routed. |
| P-5 | Every stored feature records which provider, operation and version produced it. ([`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) §5.) |
| P-6 | When both providers can supply a capability, prefer the one whose evidence is **already cached**. |

---

## 4. Capability matrix

Two independent investigations produced capability matrices on 2026-09-20. They agree on every material point; where their granularity differs, the more conservative reading is used here. Full matrices: [`evidence/post-match-ingestion-probe-2026-09-20.md`](evidence/post-match-ingestion-probe-2026-09-20.md) §5 and [`../../evidence/provider-post-match-architecture-investigation-2026-09-20.md`](../../evidence/provider-post-match-architecture-investigation-2026-09-20.md) §5.

**Class** answers "what does this cost us architecturally?":

- **A** — summary-class. Available from either provider without replay processing. **No provider is required.**
- **B** — replay-class. Available from either provider's replay-derived layer. **No provider is required**; routing picks one.
- **C** — provider-specific in the tested provider set. Using it creates a real dependency.

### 4.1 Class A — summary-class (no replay, no specific provider)

Result · duration · mode · lobby · side · hero and hero variant · level · K/D/A · GPM · XPM · net worth · gold spent · last hits · denies · final hero damage · final tower damage · final healing · final items including backpack and neutral · ability and talent build order · draft (picks and bans) · tower and barracks end state · first-blood time · all ten players' scoreboard · team scores.

Derivable from the above with our own history: personal records and PBs on summary-class metrics · personal-baseline comparisons on summary-class metrics · role and hero composition over time.

Also class A and worth noting: **hero-population percentile benchmarks** are returned by the current fresh provider on unparsed matches at no extra call (TESTED). That is a genuinely substantive comparison available at Stage 1.

### 4.2 Class B — replay-class (either provider's parsed layer)

Per-minute gold / XP / last-hit / deny / net-worth series · team gold and XP advantage curves · lane assignment and lane metrics · item purchase timings · item usage counts · ward placement and destruction logs · camp stacking · objectives with timestamps · teamfight participation · kill and death logs with context · runes · damage breakdowns by inflictor and target · positional/lane-position data.

**This is where most "sophisticated" analysis lives.** Lane win/loss, "you were X gold behind at 10 minutes", item timing against your own median, smoke-to-kill conversion, stack counts, ward uptime, objective participation, teamfight impact, death-cost analysis, farm-pattern change — all class B. **None of them requires a specific vendor.**

### 4.3 Class C — provider-specific (dependency register)

Adding a row here creates a real provider dependency. Keep it short and justified.

| Capability | Only from | Current V1 status |
|---|---|---|
| Native position/role label (POSITION_1..5) as a first-class field | STRATZ | **Not required.** V1 role resolution is a classifier over class A/B evidence ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §5.2). |
| Vendor impact/award scores | STRATZ | **Forbidden by product.** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §16 bans provider-derived impact/award scores. |
| Per-match rank / bracket | STRATZ (reliably) | **Forbidden by product.** Rank stays fenced ([`../profile/SSOT.md`](../profile/SSOT.md) §10). |
| Population aggregates by hero × position | STRATZ | **Required.** Feeds the context-adjusted expectation model ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §10.1). Cached and versioned; a global periodic cost, never per match. |
| Replay-class evidence for matches beyond the Valve replay horizon | STRATZ | **Required.** Structural: the fresh provider cannot newly create it. |
| Exact assist-event timings | STRATZ | Not required by any V1 metric or card. Recorded so a future feature does not assume it is free. |
| Full ordered replay event stream | neither | **UNKNOWN / unavailable** from the tested endpoints. Any feature needing it is unshipped. |

**Normative:** a new class C entry requires an explicit note of which enabled feature needs it and what happens when that provider is unavailable. "It would be nice to have" is not a justification.

### 4.4 Known semantic differences

| Area | Difference | Handling |
|---|---|---|
| Parse-state flags | On STRATZ, `parsedDateTime` marks basic ingestion, **not** replay-stat availability; `statsDateTime` / `isStats` marks replay stats. They diverged by up to 45+ min in probes (TESTED). | Any STRATZ-sourced replay-class feature gates on the **stats** marker, never the ingestion marker. |
| Turbo visibility | The fresh provider's history endpoint defaults to excluding Turbo, silently. With the default, an account returned 4,107 rows and was missing 14 of its last 20 matches; with Turbo included, 9,493 rows (TESTED). | Turbo is a first-class progression bucket ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §6.1). The adapter **MUST** request Turbo-inclusive history explicitly. A silent Turbo drop is a correctness bug, not a performance detail. |
| Positional data | STRATZ's location report was measured **unusable** (no time field, fixed length); the fresh provider supplies lane-position and death-position data. | Positional capability is routed to the fresh provider's replay layer only. |
| Summary-field agreement | Cross-checked on overlapping matches: duration, start time, winner, hero, K/D/A, LH, GPM/XPM, final damage and healing matched **exactly** (TESTED, small sample). | Good cross-check. **Not** proof that all fields and all matches agree — §6 still applies. |

---

## 5. Operational limits (dated evidence — single source)

**These numbers live here and nowhere else.** They MUST NOT be copied into feature SSOTs. All figures are from 2026-09-20.

### 5.1 OpenDota

| | Free | Premium (what we use) |
|---|---|---|
| Price | free | **$0.0001 per call**, rounded up to the nearest cent (VERIFIED) |
| Daily ceiling | 3,000/day | unlimited per the plan page (VERIFIED) |
| Rate | 60/min | **3,000/min** (VERIFIED; TESTED via response headers) |
| Not billed | — | 404 / 429 / 500 responses (VERIFIED) |

**Replay-processing requests are accounted separately from billing.** A processing request costs **$0.0001 to bill but 10 units against the rate limit** (VERIFIED from the vendor's own spec). At scale this is the binding constraint, not the money:

- 3,000 rate units/min ÷ 10 = **300 processing requests/min** maximum, before any other traffic.
- Therefore processing requests **MUST** pass through a dedicated token bucket, separate from read traffic. See [`SCALING-RELIABILITY-AND-OPERATIONS.md`](SCALING-RELIABILITY-AND-OPERATIONS.md) §3.

**Measured behaviour.** Fresh matches appeared in the per-account history endpoint at a median of ~3.4 min after match end (n=12). The provider does **not** auto-parse the general population (0/40 fresh public matches). When *we* requested processing: 10/10 parsed at 6.2–7.1 min in one cohort, 11/12 at 6.4–7.8 min in another. Once the replay exists, processing itself completed in ~23–25 s. A 60-day-old match parsed successfully; 180 / 365 / 730-day-old matches all failed — **the replay horizon boundary between 60 and 180 days is UNKNOWN**.

### 5.2 STRATZ

**Published tiers (VERIFIED)** and **what our token actually enforces (TESTED)** disagree:

| | Published Default | Published Individual | Published Multi-Token | **Our token, measured** |
|---|---|---|---|---|
| per second | 20 | 20 | 20/user | **8** |
| per minute | 250 | 250 | 20/user | **150** |
| per hour | 2,000 | 4,000 | 50/user | **1,500** |
| per day | 10,000 | 20,000 | 100/user | **15,000** |

**Normative:** plan against **response headers**, never against the published table. Read the remaining-quota headers on every response and treat them as the operational truth.

**Other measured constraints:**

- The token is **bound to one client IP**. A rotating egress address or two concurrent jobs sharing the token produce a 403 naming different IP addresses (TESTED). Server-side use requires a **stable egress IP** and single-flighted jobs.
- Query cost is computed from the **shape of the selection set**, not from the page size. Two probes with different page sizes produced identical cost per player-alias (TESTED). Consequence: **page size is effectively free; selection breadth is what costs.**
- Page size is hard-capped at **100** per request.
- The per-player history field **defaults to a page of 10 when the page size is omitted.**
- A root bulk match-ids field is **admin-only** and unavailable to us.

**Batching, measured.** The two investigations used different field profiles and therefore reached different maxima. Both are correct for their profile; neither contradicts the other:

| Shape | Measured maximum in one request |
|---|---|
| Aliased per-match, minimal fields | ~633 matches (200 confirmed OK) |
| Aliased per-match, mid-depth fields | 77 matches |
| Aliased per-match, heavy fields | ~37 matches |
| Per-player history, mid-depth, aliased pages | **300 matches in one call** |
| Per-player history, our current production deep selection + explicit page size | 89–100 matches (of which 69 were replay-covered in the tested page) |
| Per-player history, id + parse-state only | 3,000 matches in one call |

**Conservative production recommendation:** until an all-replay-covered 100-row page passes memory and timeout gates, treat **50** as the proven all-covered deep batch size and **100** as the proven mixed-state size. Either is an order of magnitude better than the **8** currently shipped — see [`IMPLEMENTATION-GAPS.md`](IMPLEMENTATION-GAPS.md) G-1.

**Historical replay coverage, measured:** 87% / 100% / 97% across three accounts' 300 most-recent matches, one call each. This is the capability OpenDota structurally cannot match.

**Freshness, measured:** STRATZ is **not** a fresh-match source. 1/20 freshly ended public matches were present at T+5–11 min; 0/20 of the freshest cohort at T+12 min; a separate live specimen was still absent after 14 polls through T+20m05s. In one live-player comparison, STRATZ's newest row was ~111 hours old while the fresh provider's was ~2 hours old.

### 5.3 Valve / Steam direct

**UNKNOWN.** No Steam Web API key was configured during either investigation; zero live calls were made. Current public documentation did not establish Dota-specific availability, quotas, commercial suitability or latency. A direct Valve detector remains a **bounded pilot worth running**, not a justified production dependency. A Valve-only rich-analysis architecture would additionally require operating a replay-acquisition and parsing stack — the highest-complexity option available.

---

## 6. Fallback and degradation

Full behaviour table: [`SCALING-RELIABILITY-AND-OPERATIONS.md`](SCALING-RELIABILITY-AND-OPERATIONS.md) §6. The routing rules:

| Condition | Routing response |
|---|---|
| Fresh provider slow | Nothing changes. Retry ladder absorbs it. Already-stored matches unaffected. |
| Fresh provider unavailable | Circuit breaker opens. Detection may fall back to STRATZ history at materially worse freshness, single-flighted from the stable egress IP. Replay-class enrichment degrades: queue and resume, or fall back where the evidence exists. Accept degraded latency; **do not** promise the normal timeline while a breaker is open. |
| Replay processing delayed | Match stays `REPLAY_PENDING`. Stage 1 is unaffected. |
| Replay does not exist / processing permanently fails | `REPLAY_UNAVAILABLE`. Terminal and explained. |
| STRATZ unavailable | **No effect on fresh matches.** Backfill pauses. Population reference data is served from the cached versioned snapshot. |
| STRATZ quota exhausted | Same as above. Backfill resumes next window. |
| STRATZ lacks a fresh match | Expected — STRATZ is not the fresh source. Never treat its absence as evidence the match does not exist. |
| Both histories absent for an account | Distinguish **private/unavailable** from **still syncing**. These are different product states ([`../onboarding/SSOT.md`](../onboarding/SSOT.md) §5.4). A refresh that stays empty for minutes is a privacy signal, not a queue signal. |
| Providers disagree | Keep both raw snapshots. Compare semantically equivalent core fields. **Quarantine the dependent analysis; never silently merge.** |
| Stored provider data is stale | Retain the last successful cursor and source timestamp. **Do not present stale data as current.** |

---

## 7. Open questions and provider-contract risks

Preserved from both investigations. **None of these blocks the architecture** — that is by design; the architecture must be safe before they are answered. Each carries its current mitigation.

### 7.1 OpenDota

| # | Question | Impact | Current mitigation | Launch-blocking? |
|---|---|---|---|---|
| OD-1 | Is Premium explicitly supported for a commercial app at our projected volume? | Commercial/contractual | Volume is low pre-launch. Cost model is observable and controllable. | **No** now. **Yes** before scaling past ~10k DAU. |
| OD-2 | Are "unlimited" daily calls subject to fair-use or anti-abuse ceilings beyond the per-minute rate? | Scale | Token bucket keeps us far under the published rate. Monitor 429s. | No |
| OD-3 | Are replay-processing requests subject to per-account, per-IP, per-match or commercial limits beyond the 10-unit accounting? | **High** — this is our fresh deep path | Dedicated token bucket; deduplicated per `match_id`; scheduled, not burst. Monitor rejection rate. | No, but escalates with DAU |
| OD-4 | What processing queue success rate and latency should a paid integrator expect, by region? | Product copy | Copy stays qualitative (§7 of [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md)). | No |
| OD-5 | Is the ~6-minute replay-availability floor stable, or region-dependent? | Product copy, scheduling | Scheduling uses a floor with a retry ladder, not a fixed assumption. | No |
| OD-6 | May raw responses be retained for reproducibility and derived commercial analytics? | **Legal/contractual** | Raw retention is tiered and bounded ([`DATA-CONTRACTS-AND-VERSIONING.md`](DATA-CONTRACTS-AND-VERSIONING.md) §6). | **Yes** — confirm before public launch. |
| OD-7 | Does Premium include any free monthly call allowance? | Cost modelling only | Cost modelled with zero allowance. | No |
| OD-8 | Is there any bulk match endpoint, or any plan for webhooks? | Efficiency | Polling architecture assumes no webhook. | No |

### 7.2 STRATZ

| # | Question | Impact | Current mitigation | Launch-blocking? |
|---|---|---|---|---|
| SZ-1 | Which limits are authoritative — the published table or our token's headers (they disagree)? What tier is our token on? | Capacity planning | We plan against headers, which are lower. Conservative by construction. | No |
| SZ-2 | Can an iOS consumer app qualify for a Multi-Token, given the "desktop application" framing? | Scale option | Multi-Token is **not** a foundation. A single token covers the architecture's STRATZ needs at six-figure DAU. | No |
| SZ-3 | Is there a documented child-token issuance/revocation API, or only the logged-in page? | Multi-Token feasibility | Not designed for. | No |
| SZ-4 | Must each end user have a STRATZ account or link Steam for a child token? | Multi-Token feasibility | Not designed for. | No |
| SZ-5 | Are child tokens bound to a Steam ID / device / arbitrary id? | Multi-Token feasibility | Not designed for. | No |
| SZ-6 | May child tokens be stored and used **server-side** by our backend? | Multi-Token feasibility | Not designed for. | No |
| SZ-7 | Is there a global ceiling above the per-user Multi-Token quotas? | Multi-Token feasibility | Not designed for. | No |
| SZ-8 | Does the one-IP binding apply per child token? **If yes, server-side Multi-Token use is impossible from a multi-IP backend.** | Kills the Multi-Token option if true | Not designed for. Single-token path assumes stable egress. | No |
| SZ-9 | Is the monthly referral obligation measured in clicks, unique visitors or sessions? What happens in a short month? | Token-tier risk | We are on the tier that needs no referrals. | No |
| SZ-10 | Is commercial use, raw-snapshot retention and derived-result display permitted for this product? | **Legal/contractual** | Raw retention is tiered and bounded. | **Yes** — confirm before public launch. |
| SZ-11 | Is there any freshness or parse SLA, or a webhook/notification path? | Fallback quality | STRATZ is not on the fresh critical path. | No |
| SZ-12 | What causes recent public matches to be absent from player history while older rows remain? | Fallback reliability | Never treat STRATZ absence as proof a match does not exist. | No |
| SZ-13 | Which quota applies to aliases and multi-page requests long-term? Is page-size-independent cost intentional and stable? | **Backfill plan rests on this** | Conservative batch sizes (§5.2); monitor quota headers; degrade to smaller pages on error. | No |
| SZ-14 | Is the admin-only bulk match-ids field permanently unavailable to us? | Efficiency | Per-player history path does not need it. | No |

### 7.3 Still to test ourselves

| # | Test | Why it matters |
|---|---|---|
| T-1 | Direct Valve match-history / sequence endpoints (no key was configured). | Could reduce detection latency at no marginal cost. Would **not** change the analysis timeline, which is replay-bound. |
| T-2 | The exact replay-availability boundary between 60 and 180 days. | Directly determines whether onboarding's 90-day bootstrap window can use the fresh replay route at all. See [`MATCH-INGESTION-AND-LIFECYCLE.md`](MATCH-INGESTION-AND-LIFECYCLE.md) §8. |
| T-3 | An all-replay-covered 100-row deep page, under memory and timeout gates. | Unlocks the larger backfill batch size. |
| T-4 | Real deduplication rate in production. | The modelled shared-match rate is a crude estimate, not a measurement. |
| T-5 | Production P50/P90/P99 for every readiness transition, across regions, modes, durations and times of day. | **Prerequisite for any numeric customer-facing claim.** |

---

## 8. Product/SSOT dependents

| Document | What to re-check when this document changes |
|---|---|
| [`FEATURE-DATA-DEPENDENCY-MATRIX.md`](FEATURE-DATA-DEPENDENCY-MATRIX.md) | Any capability moving between classes A / B / C. |
| [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) | §10.1 population reference data source; §20 parameter-coverage conditions. |
| [`../onboarding/SSOT.md`](../onboarding/SSOT.md) | Bootstrap acquisition feasibility against the replay horizon. |
| [`../settings_account/SSOT.md`](../settings_account/SSOT.md) | Pro backfill acquisition economics. |

No feature SSOT may restate any number from §5. They reference readiness classes only.
