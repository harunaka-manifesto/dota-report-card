# ADR 0003: Progressive post-match readiness with a single finalisation point

Date: 2026-09-20
Status: **Accepted**
Binds: [`../MATCH-INGESTION-AND-LIFECYCLE.md`](../MATCH-INGESTION-AND-LIFECYCLE.md) · [`../FEATURE-DATA-DEPENDENCY-MATRIX.md`](../FEATURE-DATA-DEPENDENCY-MATRIX.md)

## Context

A Dota match's data does not arrive in one piece.

**Summary-class evidence** — the final scoreboard and match header — is available within a few minutes of the match ending, from either provider, with no replay processing. It is substantially richer than "a result": all ten players' K/D/A, farm, GPM/XPM, net worth, final damage and healing, final items, ability build, the draft, tower and barracks state, and — at no extra cost on the current fresh provider — hero-population percentile benchmarks (TESTED 2026-09-20).

**Replay-class evidence** — everything derived from the match timeline — depends on Valve publishing a replay and someone processing it. Measured floor: about six minutes after match end, and that floor is Valve's, not a provider's. Sometimes the replay never exists at all (abandons, custom lobbies, missing replays), and sometimes processing permanently fails.

Fourteen of the twenty V1 role metrics, and every one of the seventeen insight card types, are replay-class ([`../FEATURE-DATA-DEPENDENCY-MATRIX.md`](../FEATURE-DATA-DEPENDENCY-MATRIX.md) §3). So the heavy analysis genuinely does have to wait.

Treating a match as a binary "loaded / not loaded" leaves only bad options: block the match for several minutes and lose the emotional moment entirely; or show it and lie about what is missing; or spin forever on matches whose replay will never arrive.

Meanwhile the product has already locked contracts that this must not break:

- **There is no partial-READY state.** The personal-performance layer and the insight cards are final together ([`../../match_detail/SSOT.md`](../../match_detail/SSOT.md) §7.2).
- **A `NEW_PB` event is emitted at most once** and never retroactively ([`../../app_foundation/SSOT.md`](../../app_foundation/SSOT.md) §12.2).
- **Passive provider enrichment after READY is ignored** ([`../../app_foundation/SSOT.md`](../../app_foundation/SSOT.md) §4.7).
- **Missing evidence is N/A, never zero** ([`../../app_foundation/SSOT.md`](../../app_foundation/SSOT.md) §2, §8).

And the product has already solved a structurally identical problem once: a live match arriving during an unsettled bootstrap shows its facts immediately and defers its history-dependent finalisation ([`../../onboarding/SSOT.md`](../../onboarding/SSOT.md) §6.1). That precedent is the shape of the answer.

## Decision

1. **Post-match delivery is two-stage.**
   - **Stage 1** begins at `SUMMARY_READY`: the match is present, openable and useful. It shows **non-history-dependent facts** — match identity, result, hero, duration, the full ten-player scoreboard, draft, items, effective role, and raw achieved values for any metric whose evidence already exists.
   - **Stage 2** is the heavy analysis, unlocked when replay-class evidence arrives.

2. **Stage 1 MUST NOT depend on replay-class evidence, on any provider's processing queue, or on any provider-specific enrichment.**

3. **Evidence readiness is a separate, orthogonal axis** from the product's locked per-match lifecycle state. Readiness describes what we know about the *match* (global). Lifecycle describes how far our processing has got for one *player*. States: `DISCOVERED` → `SUMMARY_READY` → `REPLAY_PENDING` → `REPLAY_READY` | `REPLAY_UNAVAILABLE`. **This is not a second lifecycle state machine and must not be turned into one.**

4. **There remains exactly ONE finalisation point per match.** It is reached when evidence is terminal — `REPLAY_READY` **or** `REPLAY_UNAVAILABLE` — and deterministic analysis has run and persisted. Only at finalisation does the product produce baseline comparisons, adjusted expectations, performance states, matchup context, PB determination and `NEW_PB` events, progression observations, insight cards, and any READY notification.

5. **`REPLAY_UNAVAILABLE` is terminal and explainable, not a failure.** Analysis still runs, on summary-class evidence. Replay-class metrics become **N/A with a reason**. The match still reaches `READY` and may still be progression-eligible — `MATCH_ELIGIBLE != EVERY_METRIC_AVAILABLE` is already locked. It is **not** lifecycle `UNAVAILABLE`, which is reserved for matches whose summary-class truth never arrived at all.

6. **The UI adds and unlocks; it does not replace.** When readiness advances while a screen is open, deep sections become available additively. Stage-1 content already rendered is not swapped out or invalidated.

7. **No endless spinners.** Every pending deep section has a bounded, terminal outcome. A terminal unavailable section reads as a settled fact, stated once — not as an error and not as an apology.

8. **The user is notified when readiness advances**, subject to the existing READY-only notification rules.

9. **No numeric latency promise ships** until production P50/P90/P99 monitoring backs it. Measured latency, product copy, operational SLO and contractual SLA are four different things ([`../MATCH-INGESTION-AND-LIFECYCLE.md`](../MATCH-INGESTION-AND-LIFECYCLE.md) §7). "Instant analysis" is forbidden copy.

## Consequences

**Accepted costs**

- Two rendering paths on Match Detail and a defined transition between them. More design work than one state, and it must be designed rather than left to a loading spinner.
- The dependency matrix must be maintained: every new block needs an evidence classification.
- An explicit terminal state has to be designed, written and tested, for a case that is a minority of matches but must never look broken.
- The product must resist the very natural pull toward showing a comparison or a PB at Stage 1. It cannot, because that would create a second finalisation point and therefore a path to double celebration.

**Gains**

- The emotional post-match moment is preserved. A match that just ended is present and genuinely substantive within minutes.
- The deep analysis is not rushed and not faked. It arrives when the evidence does.
- A match with no replay is still a complete, honest record rather than a broken one.
- The product's locked contracts survive intact: no partial-READY, one celebration, no retroactive events, no zero-filling.
- Provider latency variation becomes a *delivery* concern, not a correctness concern.

**Obligations this creates**

- Stage 1 must never grow a replay dependency by accident. Any new Stage-1 block is checked against §3 of the dependency matrix.
- Product copy stays capability-based. A user must never need to know what a replay parse is.
- Progression, PBs, achievements and challenges are classified by their *own* evidence requirement. A single generic "match processing" flag gating everything is explicitly forbidden — it would make a scoreboard-only challenge wait for a replay, and an achievement needing a replay event look failed.
