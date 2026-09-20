# Match Detail — SSOT

**Status:** ACTIVE — feature contract
**Scope:** The single-match review surface: match identity and result, personal performance against a reasonable expectation, matchup context, role metrics, Personal Best state, deterministic post-match insight cards, role correction, and unavailability semantics.
**Inherits:** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) — lifecycle, roles, metrics, baselines, context adjustment, PB, entitlement, rebuild.
**Engineering annex:** the insight-card algorithms, thresholds, ladders, classifier constants and frozen reference tables live in [`../_archive/engine_specs/POST-MATCH-INSIGHTS-SSOT.md`](../_archive/engine_specs/POST-MATCH-INSIGHTS-SSOT.md) and its machine-readable contract. That annex is **engineering-normative for algorithms** and **subordinate to this document for product meaning**.

---

## 1. Purpose

Match Detail answers:

> What happened in this match, how did I personally perform relative to a reasonable expectation, and what noteworthy patterns are worth seeing?

It is a **factual, metric-level review of one processed match**. It is not an overall evaluation of the player or the game.

---

## 2. The hard separation

Match Detail hosts **two systems that share only a match ID**. They MUST NOT be merged into one judgment.

| | **Personal Performance** | **Match Diagnosis (Insights)** |
|---|---|---|
| Question | How did you perform relative to a reasonable expectation? | What notable patterns occurred in this match? |
| Unit | Per metric | Per card (0–3 per match) |
| History system | Rolling 20-match median, ≥ 5 priors | Record window ≤ 50, N ≥ 20 |
| Context-adjusted? | Yes, selectively per metric | **No** — records stay raw and comparable |
| May mention matchup context? | Yes, as a badge | **No** |
| May mention the match result? | **No** | Yes, factually |
| May mention another player? | **No** | Only as a neutral named fact |

**Normative:** insight cards MUST NOT read lane context, the hero or lane adjustment, or the adjusted expectation. The personal-performance layer MUST NOT read insight card output.

---

## 3. Minimum semantic contract

For a retained processed match, Match Detail MUST be able to express, where applicable:

1. match context (hero, result, mode, date/time, duration);
2. the **effective role**;
3. the applicable fixed role metric set;
4. each achieved value, **including legitimate zeroes**;
5. baseline-at-the-time comparison for eligible metrics where a valid prior baseline exists;
6. an explicit **baseline-not-established** state when comparison history is insufficient;
7. the context-adjusted expectation and performance state for metrics that carry them;
8. matchup context, where applicable, or nothing;
9. current PB ownership, and any relevant one-time `NEW_PB` distinction;
10. progression eligibility, with a clear reason when the match does not count;
11. a persistent **Edit Role** action while correction is supported;
12. explicit unavailable/N/A states for individual facts or metrics;
13. 0–3 insight cards, or the normal no-special-insight state.

This is a **minimum semantic contract, not an exhaustive schema**. Additional factual context MAY be added later if it violates nothing here.

---

## 4. Personal performance layer

### 4.1 Per-metric output

For each metric in the effective role's set:

- the **achieved value** (raw/display form as defined in foundation §7.2);
- its comparison reference:
  - the **context-adjusted expectation** for class B / C / C\* metrics in Standard, or
  - the **raw personal baseline** ("your usual") for class A / D metrics and for all Turbo metrics;
- a **performance state**: `ABOVE` · `IN_LINE` · `BELOW` · `NOT_READY`;
- or an explicit **N/A** with its reason.

`offlane.objective_involvement.v1` is **diagnostic only**: display the value and the personal median, emit **no** performance state.

### 4.2 Baseline-at-the-time

Every comparison uses the same-role, same-mode baseline that existed **immediately before this match**. Wording MUST make the time-relative meaning clear ("baseline at the time", "your usual before this match"). "Current baseline" is reserved for present-day Progress and Home contexts and MUST NOT be used ambiguously here.

Later matches MUST NOT change a finalized historical comparison. Only an authorized role correction, methodology migration or parameter-set rebuild may recompute it.

### 4.3 Matchup context

```text
DIFFICULT | TYPICAL | FAVOURABLE | UNAVAILABLE
```

- **One badge per match**, attached to the lane-metric group — never per metric, never repeated.
- Applies to **Standard × {Carry, Mid, Offlane}** only. Turbo and Support receive no badge.
- Computed from the draft alone. It never reads the residual, the result, or anything realised in the match.
- MAY render when the baseline is not ready — it needs no history.
- `UNAVAILABLE` renders **nothing**. It MUST NEVER be drawn as "Typical".
- User-facing terminology: **Difficult / Typical / Favourable matchup** (or lane). It describes **on-paper opponent context**, not what happened in the lane.

**Forbidden:** any sentence containing both the matchup label and the match result; any use of the label as a reason, cause or excuse; any softening of `BELOW` because the matchup was `DIFFICULT`; "not your fault", "you lost because", "unwinnable", any teammate claim.

The four "contradictory" combinations (DIFFICULT+ABOVE+LOSS, FAVOURABLE+BELOW+WIN, DIFFICULT+BELOW+WIN, FAVOURABLE+ABOVE+LOSS) are **correct output**.

### 4.4 Never composed

`PerformanceState`, `LaneContext` and `TrendState` MUST NOT be composed into one sentence. Trend does not appear on Match Detail at all — it belongs to `progress/` (different time horizon, different contract).

### 4.5 Personal Best

- Show whether the match **currently owns** the canonical PB for a metric.
- Distinguish the one-time `NEW_PB` event from ongoing current ownership.
- On later visits, labelling reflects only **current** ownership. V1 has no "PB at the time" label.
- A PB that has since been superseded simply no longer shows as a PB here. No retraction, no notice.
- PB uses the comparison value and all known eligible history — not the 20-observation window. A value above the recent baseline is frequently not a PB.

---

## 5. Match diagnosis: insight cards

### 5.1 Product contract

- **0 to 3 cards.** Three is a ceiling, never a target. Empty slots MUST NOT be filled.
- **Deterministic.** Every card comes from provider fields, deterministic derivations, eligibility rules, guards, history comparators, severity ladders, a fixed ranking rule and predefined semantic templates. **No LLM analyses any production match.**
- **Quality over coverage.** A high score MUST NOT rescue a boring or misleading card type. Thresholds and guards MUST NOT be loosened for coverage, and removed card types MUST NOT return, without a new owner decision backed by new evidence.
- **Standard and Turbo never mix.** Thresholds, distributions and history cohorts are per bucket.
- **Playback is optional.** No card depends on it; it can only add one optional enrichment line.
- Cards are **derived, ephemeral recap content** attached to a match. They are **not** progression: they never feed baselines, trends or PBs, and never create celebration or notification events.

### 5.2 Coverage expectation (locked)

**About 57–61% of eligible viewpoints show no card at all.** Two or more cards occur in roughly 7–9% of recaps; three in 1–2%. Supports see no card about 66% of the time; Turbo is sparser than Standard.

**Sparse coverage is not an engine failure.** It is the direct result of deliberately removing statistically valid but boring candidates and of player-context guards.

The post-match surface MUST therefore support **two first-class states**:

- **special-insight state:** 1–3 cards;
- **normal / no-special-insight state:** 0 cards. **This is the majority experience** and deserves real design attention.

### 5.3 Card families and the V1 registry

17 card types and 2 enrichments ship in V1.

| Family | What it is about | Count |
|---|---|---|
| **Match Lead Story** | How the net-worth story of the match went: comebacks, losses from ahead, lead flips, close games, separations, erosions, recoveries, late reversals. | 8 (3 Tier A + 5 Tier B) |
| **Lane Story** | How this lane compared with the lanes this player normally has, or normally faces. | 2 |
| **Hidden Enemy Activity** | Enemy work the player could not see: stacking, vision clearing, smoke usage, an unusually early-rich hero. | 5 (+ Smoke→Kills enrichment) |
| **Power Spikes & Item Timings** | An unusually fast own item, or an unusually early enemy core item. | 2 |
| **Structure contradiction** | Enrichment on a lead-story card: a long lead with no structures taken. | enrichment only |

Tier A (anomaly/exceptional/hidden/history-personal) and Tier B (match shape) are **taxonomy, not priority**. There is no Tier A bonus and no Tier B penalty.

The canonical card IDs, eligibility thresholds, severity ladders, guards and frozen reference tables are in the engineering annex. They are not restated here and MUST NOT be re-derived elsewhere.

### 5.4 Selection

- Exactly **one** combination rule exists: at most one card is kept from the Match Lead Story group. It is a targeted, empirically justified suppression rule.
- There is **no** generic diversity engine: no one-card-per-family rule, no redundancy groups, no merge logic, no composite cards, no diversity quotas, no balancing of own/enemy, positive/negative, or win/loss.
- Cards are ordered by a fixed deterministic rule (ranking class, then severity band, then level, then a fixed tie order). Display order is the engine's output order.
- **Display order is semantically meaningful** — the first card is the engine's most significant. Design MAY vary treatment by position but MUST NOT reorder.

### 5.5 Semantic safety contract

**Allowed:** was, reached, bought, used, destroyed, stacked; followed by, within, after, before, while, during, until, from…to; led by, trailed by, cut…to; "across your last N {mode} {role} matches"; "at least N" (mandatory for vision counts); "for most of"; the match result stated factually.

**Prohibited:**

| Category | Forbidden |
|---|---|
| Causality | because, caused, resulted in, led to, cost you, won them the game, punished, that's why, decided the game, momentum |
| Judgement | threw / throw, outplayed, clutch, should have, failed to, wasted, bad wards, "your supports didn't…" |
| Intent | counter-built, rushed to counter you, "successful" in a causal sense, ganked you |
| Visibility | they saw you, you had no vision, blinded, map control, any visibility percentage |
| History overreach | ever, all-time, personal record, PB, exact percentiles, any history wording below the sample gates, population data presented as "your usual" |
| Purchase semantics | finished, completed (a purchase is what is observed — use "bought") |
| Shape overreach | throughout, "even the entire time", "anyone's game", "comeback" in a loss |

**Rules:**

1. Every card states only observed facts: values, times, counts, the result, and scoped history.
2. Lead-story and match-shape cards MUST state the match result where their specification requires it.
3. Enemy-side cards MUST NOT imply the player's team failed.
4. Copy MUST use actual values, never smoothed intermediates, for displayed numbers.
5. **Sequence, never cause.**

### 5.6 History claims in cards

Card history is a **separate system** from progression baselines. Claim strength is gated by sample size N (the count of comparable prior values, window ≤ 50):

| N | Allowed |
|---|---|
| < 10 | No historical claim of any kind. |
| 10–19 | A median-only secondary line on an already-eligible card. History MUST NOT create a card. |
| ≥ 20 | Record wording ("fastest / best / worst / most across your last N {mode} {role} matches"). History-required cards become eligible. |
| ≥ 30 | Rarity wording, continuous metrics only ("one of your 3 fastest", "top 10% of your last N", "unusually early for you"). |
| never | "ever", "all-time", "personal record", "PB", exact percentiles, fake precision beyond the sample. |

The stated **N is mandatory** in any history wording. "Your usual" means the window median and is used only for the player's own metrics.

A freshly bootstrapped account (30 matches per bucket) reaches N ≥ 20 for role cohorts in only a minority of evaluations. History-required cards are simply **absent** below the gate; the recap is not padded.

### 5.7 Card unavailability

A match may produce zero cards because it is globally ineligible for the engine (not because processing failed). Global ineligibility includes: unsupported bucket, fewer than 10 human players, duration under 600 s, missing required series, a leaver, malformed position data, or the feeding guard (one player with an extreme early-death count distorts every economy fact).

`EVALUATED with 0 cards` and `NOT_ELIGIBLE` both render the **normal post-match state**. The distinction exists for diagnostics only and is not user-facing.

---

## 6. Role correction

- A persistent **Edit Role** action is available on every retained match while source telemetry supports recalculation. Not limited by age, recency or confidence.
- A **low-confidence prompt**, when present, is a shortcut into the same flow — not a second system, and never a prerequisite for finalization.
- Edit Role accepts only Carry, Mid, Offlane, Support.
- If telemetry no longer supports recalculation, the product MUST explain that correction is unavailable rather than fabricate a rebuild.
- A confirmed change triggers the deterministic rebuild in foundation §5.6. On this surface, that means: the metric set changes to the new role's set; values, baselines, adjusted expectations, performance states, matchup context and PB state recompute; metrics the new role cannot compute from retained data become **N/A**, never fabricated or substituted.
- The match's **insight result is reopened and recomputed**. Later matches whose history windows included this match SHOULD be recomputed when next displayed. This never triggers notifications.
- Delivered celebrations and notifications are never retracted or re-sent.
- Effective role is the user-facing role. Raw detected role and classifier confidence are **not** required Match Detail content in V1.

---

## 7. Ineligible and unavailable matches

### 7.1 READY but progression-ineligible

Remains viewable as a factual match record with whatever trustworthy data exists. It MUST clearly indicate that it **does not count** and **why**. It receives no baseline comparison, no performance state, no PB evaluation and no progression observation. Unavailable values use explicit N/A.

Insight cards are independent of progression eligibility but have their own eligibility gate (§5.7); many ineligible matches will also produce no cards.

### 7.2 Non-READY states

| State | What Match Detail shows |
|---|---|
| `WAITING_FOR_PROVIDER` | Waiting on source data. Any already-known identity facts may show. |
| `ANALYZING` | Processing. |
| `WAITING_FOR_PRIOR_MATCH` | Computation is done; an older same-bucket match must settle first. **Not an error.** |
| `ACTION_REQUIRED` | Automatic attempts exhausted. One Retry action. |
| `UNAVAILABLE` | Trustworthy data never arrived. Visible, explained, still manually retryable. |

There is no partial-READY state: the personal-performance layer and insight cards are final together, or not yet present.

### 7.3 N/A

N/A is a **concluded state with a reason**, not a retry failure and not a zero. A legitimate measured zero stays zero. Both MUST be distinguishable on this surface.

---

## 8. Prohibited interpretation

Match Detail MUST NOT introduce:

- an overall match score, letter grade, composite performance score, or opaque AI verdict;
- an arbitrary good/bad judgment of the player;
- any causal explanation of the match result;
- any claim about a teammate, or any teammate-quality estimate;
- any visibility claim derived from ward data;
- any percentile, rank, MMR or bracket claim;
- any composition of performance state with matchup context or with the result;
- any softening of a below-expectation verdict because of context.

---

## 9. Versioning

- The insight result is computed when the match becomes READY, from the frozen source checkpoint and the ordered prior history available then. Later passive provider data never changes it.
- A recap MUST NOT mix cards from different contract versions. A stored result whose version is not current MUST be either recomputed deterministically under the current version or not displayed.
- Recomputation is deterministic and idempotent, and sends no notifications.
- Entitlement changes do not rewrite already-computed results for display.
- The personal-performance layer follows the foundation's rebuild rules: role correction, metric-version bump, or parameter-set bump, each a deterministic replay with no provider calls.

---

## 10. Hard invariants

- Personal performance and match diagnosis are never merged into one judgment.
- Insight cards never read lane context, adjustments or the adjusted expectation.
- At most 3 cards; slots are never filled; 0 cards is the majority, expected state.
- Cards claim sequence, never cause.
- History wording always states N and never exceeds its sample gate.
- One matchup badge per match, on the lane-metric group; `UNAVAILABLE` renders nothing.
- A below-expectation state is never softened by matchup context.
- The matchup label and the match result never appear in the same claim.
- Comparisons use the baseline at the time, never today's baseline.
- N/A is never rendered as zero.
- `objective_involvement` emits no performance state.
- Trend states do not appear on this surface.
- Edit Role is available on every retained match with sufficient telemetry.
- A correction rebuilds this match's metrics, comparisons, adjustments, PB state and insight result, deterministically, with no provider calls.
- A READY but ineligible match is visible, says it doesn't count, and gives the reason.
- No score, grade, causal result explanation, teammate claim or visibility claim appears.

---

## 11. Acceptance rules

- [ ] Every applicable metric shows a value, a legitimate zero, or an explicit N/A with a reason.
- [ ] A metric without a ready baseline shows baseline-not-established, never a synthetic comparison.
- [ ] Class A/D and Turbo metrics compare against "your usual"; class B/C/C\* Standard metrics compare against the adjusted expectation.
- [ ] `offlane.objective_involvement.v1` shows value + personal median only.
- [ ] Exactly one matchup badge appears, on the lane-metric group, for Standard cores only; `UNAVAILABLE` shows nothing.
- [ ] `DIFFICULT + BELOW` renders identically to `TYPICAL + BELOW`.
- [ ] No string contains both the matchup label and the match result.
- [ ] A match with 0 insight cards renders a designed normal state, not an error or an empty container.
- [ ] Cards render in engine order; no client reordering, merging or padding.
- [ ] Every history claim states N and respects its sample gate.
- [ ] Current PB ownership is distinguishable from the one-time NEW_PB event.
- [ ] Edit Role is present on old, recent, high-confidence and low-confidence matches alike.
- [ ] After a correction, the metric set, comparisons, adjustments, PB state and insight result all reflect the new role, with unsupported metrics as N/A.
- [ ] A READY ineligible match is fully viewable with its reason and no comparisons.
- [ ] `ACTION_REQUIRED` exposes exactly one Retry; `UNAVAILABLE` remains manually retryable.
- [ ] `WAITING_FOR_PRIOR_MATCH` does not read as an error.
