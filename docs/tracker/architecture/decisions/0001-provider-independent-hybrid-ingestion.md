# ADR 0001: Provider-independent hybrid ingestion

Date: 2026-09-20
Status: **Accepted**
Binds: [`../SYSTEM-ARCHITECTURE.md`](../SYSTEM-ARCHITECTURE.md) · [`../PROVIDER-CAPABILITIES-AND-ROUTING.md`](../PROVIDER-CAPABILITIES-AND-ROUTING.md) · [`../MATCH-INGESTION-AND-LIFECYCLE.md`](../MATCH-INGESTION-AND-LIFECYCLE.md)
Evidence: [`../evidence/`](../evidence/) — two independent investigations, 2026-09-20

## Context

Dota Tracker's core product moment is post-match: a player finishes a game and wants an honest, useful review of it quickly. Everything that moment depends on is data we neither own nor control.

Two community providers were investigated independently on 2026-09-20, against live matches, with an explicit evidence-tagging discipline.

1. **Fresh post-match UX requires low-latency detection and low-latency replay-derived enrichment.** OpenDota detected freshly-ended matches within a few minutes (median ~3.4 min, n=12, TESTED) and, when we requested replay processing ourselves, produced fully processed matches for 21 of 22 fresh matches across two cohorts between 6.2 and 7.8 min after match end (TESTED). The ~6-minute floor is Valve's replay publication, not a provider queue.

2. **STRATZ freshness is variable and sometimes very poor.** 1 of 20 freshly-ended matches was present at T+5–11 min; 0 of 20 of the freshest cohort at T+12 min; a separate live specimen was still absent after 14 successful polls through T+20m05s (TESTED, both investigations). Its replay-stat marker landed at +11 min in one case, +61 min in another, and was still null 45 min after match end in a third (TESTED).

3. **OpenDota cannot produce replay-derived data once Valve's replay expires.** A 60-day-old match processed successfully; 180-, 365- and 730-day-old matches all failed (TESTED). The exact boundary between 60 and 180 days is **UNKNOWN**.

4. **STRATZ already holds parsed history well beyond that horizon** — replay-stat coverage of 87% / 100% / 97% across three accounts' 300 most-recent matches, one call each (TESTED). It is also extremely batch-efficient, and its query cost is driven by selection breadth rather than page size (TESTED).

5. **Both providers carry unresolved commercial and operational unknowns** — token tiers, quotas that contradict published tables, IP binding, Multi-Token eligibility, fair-use ceilings on replay-processing requests, raw-retention and commercial-use terms. See [`../PROVIDER-CAPABILITIES-AND-ROUTING.md`](../PROVIDER-CAPABILITIES-AND-ROUTING.md) §7.

6. **Future scale and monetisation are both uncertain.** The product has not launched. We cannot know DAU, and we cannot assume paying users will exist.

7. **Direct Valve acquisition was not testable** — no Steam key was configured — and a Valve-only rich-analysis architecture would additionally require operating a replay acquisition and parsing stack, the highest-complexity option available.

The two investigations differ in emphasis. One is latency-forward and recommends committing to an OpenDota-first fresh path on the strength of its larger measured samples. The other is caution-forward and stresses that provider order must remain a measured policy rather than a fixed architectural assumption. **They do not contradict each other factually**, and both independently reject single-provider designs. This decision takes the operational recommendation of the first and the structural discipline of the second.

## Decision

1. **The canonical architecture is provider-independent.** Providers sit behind acquisition adapters. The persisted model, the analysis engine, the client model and the feature SSOTs are Dota Tracker-shaped, never OpenDota-shaped or STRATZ-shaped.

2. **The iOS client MUST communicate only with the Dota Tracker backend.** It MUST NOT depend on any provider for a product screen. Screens read persisted or cached Dota Tracker state. Provider synchronisation happens behind the backend boundary.

3. **Current routing policy — OpenDota-first for everything fresh:** detection, fresh summary-class evidence, and fresh replay-class enrichment. **STRATZ is not on the critical fresh-match path**, and no STRATZ call is spent merely to duplicate fresh evidence OpenDota already supplies.

4. **STRATZ's role is historical enrichment, population reference data, selected STRATZ-specific capabilities, and fallback.** Specifically: replay-class evidence for matches beyond the replay horizon; cached, versioned population aggregates for the context-adjustment model; and a circuit-broken fresh-path fallback at degraded latency.

5. **Provider preference is policy; the canonical model is architecture.** Routing may change on measured evidence without a rewrite. That is the point of the design. Changing *which* provider serves a capability is a policy change plus an ADR. Changing *whether* the system is provider-independent is not on the table.

6. **Making STRATZ mandatory on the fresh-match happy path requires a new accepted ADR.**

7. **Valve direct acquisition remains a bounded pilot**, not a production dependency, until it is tested (T-1).

## Consequences

**Accepted costs**

- Two integrations to build and maintain, each with its own auth, limits, failure modes and commercial terms.
- Provider provenance must be recorded on every stored feature, which is real schema and real discipline.
- An adapter layer exists that a single-provider design would not need.
- Two sets of unresolved provider-contract questions to chase, two of which (raw retention and commercial terms, one per vendor) are flagged launch-blocking for public launch.

**Gains**

- A predictable, measured fresh path built on the provider that actually performs on fresh matches.
- Historical depth that no single provider can supply alone — the one thing that makes long-horizon Profile and reporting features possible at all.
- Graceful degradation: either provider can fail and the product loses capabilities rather than collapsing.
- Routing can evolve on evidence without touching the client, the domain model or any feature SSOT — and specifically without an App Store release.
- A third source (direct Valve, or a future provider) is an adapter, not a migration.

**Obligations this creates**

- Provider quotas, prices and latencies are dated evidence with a single home ([`../PROVIDER-CAPABILITIES-AND-ROUTING.md`](../PROVIDER-CAPABILITIES-AND-ROUTING.md) §5). They MUST NOT be scattered into feature documents, and MUST be re-verified before being relied on for a future commitment.
- No feature may quietly become provider-dependent. A new class C capability requires an explicit register entry naming the feature that needs it and what happens when that provider is unavailable.
- The degradation contract ([`../SCALING-RELIABILITY-AND-OPERATIONS.md`](../SCALING-RELIABILITY-AND-OPERATIONS.md) §6) is part of the decision, not an afterthought to it.
