# ADR 0004: Entitlement is applied above the data and analysis foundation

Date: 2026-09-20
Status: **Accepted**
Binds: [`../SYSTEM-ARCHITECTURE.md`](../SYSTEM-ARCHITECTURE.md) · [`../DATA-CONTRACTS-AND-VERSIONING.md`](../DATA-CONTRACTS-AND-VERSIONING.md)

## Context

Dota Tracker has not launched. We do not know whether a Pro tier will exist in its currently imagined form, what it will cost, what it will contain, or what share of users will pay for it. The product SSOT records the Pro feature catalogue, pricing and packaging as explicitly open ([`../../app_foundation/SSOT.md`](../../app_foundation/SSOT.md) §19).

That uncertainty is a hard constraint on the backend, not a marketing detail.

If fresh-match ingestion is designed so that its economics only work when enough users convert, then a launch where nobody pays is not a slow start — it is an architecture that cannot run. Worse, the failure would arrive at exactly the moment we could least afford a rewrite.

There is also a quieter risk. Once a codebase contains a "paid pipeline" and a "free pipeline", the tiers drift apart: different acquisition depth, different freshness, different field coverage. The product has already locked that **subscription does not change measurement truth** ([`../../app_foundation/SSOT.md`](../../app_foundation/SSOT.md) §2.9, §13.4) and that Pro must never be framed as more accurate. Separate pipelines make that promise unenforceable by construction, no matter what the documentation says. The existing V7 acquisition policy already encodes the same principle in code (`PAID_MAY_ACQUIRE_MORE_THAN_FREE = False`), with tests holding it there.

The cost analysis supports the decision rather than merely permitting it: the fresh path's dominant cost is per-unique-match, it is small per match, and global deduplication makes it smaller as the product grows denser. A free-only launch is affordable.

## Decision

1. **Fresh-match ingestion MUST be viable as a system even if every launched user is free.** Its economics may not depend on conversion.

2. **Free and paid users use the same fundamental ingestion architecture.** The same detection, the same canonical model, the same enrichment path, the same feature extraction, the same deterministic analysis, the same persisted results.

3. **The following MUST NOT be created:** a free ingestion pipeline and a paid ingestion pipeline; a free match model and a paid match model; a paid-only acquisition path for data a free user's match would otherwise get; tier-conditional freshness or tier-conditional field coverage on the fresh path.

4. **The layering is:**

   ```text
   provider acquisition
     → canonical match data
     → feature extraction
     → deterministic analysis
     → persisted result
     → entitlement / presentation decision
   ```

   and explicitly **not**:

   ```text
   subscription tier
     → a different ingestion architecture
   ```

5. **Entitlement decides what an already-computed result is shown to a user, and how much history is exposed.** It never reaches below the persisted-result layer.

6. **Pro MAY legitimately request greater historical depth.** Deeper historical backfill is more *work of the same kind*, at the same priority class as other historical work — not a different pipeline, not a different model, and never a different measurement. It is subject to the same rules: lowest priority, pausable, never delaying a fresh match.

7. **Entitlement changes are rebuilds over stored data**, not re-acquisitions. Activation, expiry and resubscription recompute from retained data and make no provider calls where coverage is already complete.

## Consequences

**Accepted costs**

- We cannot use tier as a cost-control lever on the fresh path. Cost control must come from architecture — deduplication, debouncing, scheduling, not re-fetching — which is where it belongs anyway.
- Free users receive the full-quality fresh pipeline. That is a deliberate expense.
- A future genuinely expensive Pro-only capability needs its own justification against this ADR; it cannot simply assume paid users may be served differently at the acquisition layer.

**Gains**

- A launch with zero paying users is survivable. The product can find out what people will pay for without first betting the backend on the answer.
- The locked product promise — Pro is more depth and synthesis, never more accuracy — becomes structurally true rather than merely documented.
- Monetisation can be redesigned repeatedly without any backend migration, because it lives above persisted results.
- Entitlement transitions are cheap and atomic: they are rebuilds over data we already hold.
- One pipeline to test, monitor, reason about and debug.

**Obligations this creates**

- A future agent optimising the backend around monetisation assumptions is making an architectural error, not a business trade-off. This ADR is the thing to point at.
- Any proposal that introduces tier-conditional behaviour **below** the persisted-result layer requires superseding this ADR.
- Pro historical depth is scheduled as historical work under the normal priority rules. "Pro users paid, so their import should jump the queue" would violate the fresh-work-first rule in [`../SCALING-RELIABILITY-AND-OPERATIONS.md`](../SCALING-RELIABILITY-AND-OPERATIONS.md) §2 and is not permitted.
