# ADR 0002: `match_id` is the global unit of ingestion and enrichment work

Date: 2026-09-20
Status: **Accepted**
Binds: [`../DATA-CONTRACTS-AND-VERSIONING.md`](../DATA-CONTRACTS-AND-VERSIONING.md) · [`../MATCH-INGESTION-AND-LIFECYCLE.md`](../MATCH-INGESTION-AND-LIFECYCLE.md) · [`../SCALING-RELIABILITY-AND-OPERATIONS.md`](../SCALING-RELIABILITY-AND-OPERATIONS.md)

## Context

A Dota match contains ten players. As Dota Tracker grows, some of those players will be our users — sometimes several in the same match, especially once friends invite each other, and especially in parties.

The naive design keys ingestion on `(user, match)`: each user's sync discovers "their" match and fetches it. That design has three compounding problems.

1. **Upstream work multiplies by roster overlap.** Five of our users in one match means five fetches, five replay-processing requests and five stored copies of identical data — for zero additional information. Replay-processing requests are the scarcest provider budget we have (10 rate units each against the fresh provider's per-minute limit, VERIFIED 2026-09-20), so this multiplies exactly the resource we can least afford to waste.

2. **It makes social features structurally expensive.** Following is the natural growth mechanic for this product. Under `(user, match)` keying, 100 followers of one Dota account create 100 independent ingestion pipelines for that account. Cost would then scale with the *follow graph* rather than with the data — which is the wrong curve, and one that gets worse exactly as the product succeeds.

3. **It corrupts the data model.** Per-user copies of the same match drift, disagree, and make provenance and reproducibility incoherent. There would be no single answer to "what do we know about match X?".

Both investigations independently reached the same structural conclusion. The cost model that follows from it — work scaling with *unique tracked matches and accounts* rather than with users, views or edges — is the difference between a viable and an unviable product at scale.

## Decision

1. **A Dota match is stored once, globally, keyed on `match_id`.** Not on `(user, match)`.

2. **Detection, provider fetches, replay-processing requests, raw snapshots and enrichment jobs are all deduplicated on `match_id`.** Where a match can be detected once, it is detected once.

3. **All ten player rows are stored with the match**, whether or not those players are tracked by us.

4. **Tracked accounts attach as links.** Adding the fifth tracked account to a match adds one link and zero provider work.

5. **User-relative analysis is computed per `(match_id, account_id)` from the shared match evidence.** Analyses stay separate; the evidence underneath them does not.

6. **Tracking is a property of the account, not of its follower count.** An account is tracked if any user owns it or at least one user follows it. One hundred followers cost what one follower costs.

7. **Follower fan-out is a read-side fan-out.** Never a fetch fan-out.

8. **Account sync is debounced globally per Dota account** — not per user, not per screen, not per follower.

9. **Deduplication applies at every layer**, not only at the fetch: sync, fetch, processing request, match storage, raw snapshot, analysis job, followed accounts. Each layer's dedup key is specified in [`../DATA-CONTRACTS-AND-VERSIONING.md`](../DATA-CONTRACTS-AND-VERSIONING.md) §8, and queue rows carry a database-level unique constraint so idempotency is enforced by the schema rather than by worker discipline.

## Consequences

**Accepted costs**

- Slightly more schema: a match table, a player table, and an explicit link table, rather than one denormalised per-user table.
- Every job needs a dedup key and a unique constraint. Idempotency is a design requirement from day one, not something to add later.
- Jobs must be written to serve "every tracked account in this match", not "this one user".

**Gains**

- Upstream provider work is independent of how many of our users are in a match.
- Social and friend-timeline features are cheap by construction: a timeline is a read against stored links, not a fetch fan-out. This is the single decision that makes the product's most likely growth mechanic affordable.
- One coherent answer to "what do we know about match X?", which is a precondition for provenance and reproducibility.
- The efficiency of the whole system becomes measurable in one number — provider calls per unique match — and one ratio — unique matches ÷ account-match links.
- Deduplication directly reduces pressure on the scarcest provider budget, and does so more as the product grows denser.

**Obligations this creates**

- Any feature that appears to require per-user provider acquisition is a design error until proven otherwise. Check whether the requirement is actually per-user *analysis* over shared evidence.
- The deduplication ratio must be measured in production ([`../SCALING-RELIABILITY-AND-OPERATIONS.md`](../SCALING-RELIABILITY-AND-OPERATIONS.md) §7.5). The modelled shared-match rate is an estimate, not a measurement.
- A social feature must never be shipped with a fetch fan-out, however convenient, without superseding this ADR.
