# Progress — SSOT

**Status:** ACTIVE — feature contract
**Scope:** The role progression surface: per-role, per-mode, per-metric observation series, rolling baselines, trend states, Personal Bests in their progression context, and readiness semantics.
**Inherits:** [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) — metric registry, baseline, trend, PB, entitlement, rebuild.

## Architecture dependencies

| Concern | Authoritative source |
|---|---|
| Evidence readiness and the single finalization point | [`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §4A |
| Which metrics need which evidence class | [`../architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md`](../architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md) §3 |
| Rebuild from stored data, never from providers | [`../architecture/DATA-CONTRACTS-AND-VERSIONING.md`](../architecture/DATA-CONTRACTS-AND-VERSIONING.md) §7.2 |

---

## 1. Purpose

Progress answers:

> Is my measured performance in this role, in this mode, actually changing?

It is the deep role analysis that Home's role summaries lead into. It is the **only** surface that shows a metric's history as a series.

The product principle is: **see yourself**. Progress describes change in the player's own role-specific metric history. It does not produce a universal skill score or a causal judgment about any match.

---

## 2. Partitioning

Progress is calculated strictly within:

```text
progression_bucket × effective_role × metric_id × metric_version
```

There are **eight independent tracks**: Standard and Turbo × Carry, Mid, Offlane, Support. Within each, every metric has its own series.

The following are **forbidden**:

- a role-agnostic baseline;
- a Standard/Turbo shared history or count;
- one role reading another role's baseline;
- a shared trend line across roles or metrics;
- cross-role or cross-bucket normalization presented as Progress;
- a fallback from a missing role history to another role or bucket.

A general chronological match list may span roles and modes (see `history/`), but a **Progress calculation may not**. An "All" view MUST show separated tracks or evidence; it MUST NOT silently compute a merged curve.

---

## 3. What Progress shows

For a selected `bucket + role`:

1. **The metric set for that role** (Carry 6, Mid 5, Offlane 4, Support 5 — see foundation §7.2).
2. **Per metric**, some or all of:
   - the chronological series of eligible measured observations (raw/display value and/or the canonical comparison value);
   - the rolling baseline context;
   - the canonical **trend state**: `Improving` · `Stable` · `Declining` · `Insufficient History`;
   - readiness: baseline-building (with its count) or baseline-ready;
   - the current **Personal Best** for that metric, with its source match;
   - N/A points, shown as N/A or omitted from a derived visualization — **never as zero**.
3. **Role-level context that is not a verdict**: number of eligible matches, recency of activity, metric readiness counts.

Navigation from any observation into its `match_detail/` MUST be possible.

---

## 3A. Readiness and recomputation

### 3A.1 When a match enters progression

A match contributes observations **only at the single finalization point** ([`../app_foundation/SSOT.md`](../app_foundation/SSOT.md) §4A.3) — when its evidence is terminal and deterministic analysis has persisted.

| # | Rule |
|---|---|
| PR-1 | Progression recomputation is triggered by finalization, **never** by intermediate readiness. A match at `SUMMARY_READY` with its deep evidence still pending contributes nothing yet. |
| PR-2 | Progression **MUST NOT** present a deep-data-dependent value before its inputs exist. Provisional observations are forbidden: they would produce false baselines, false trends and false PBs that later have to be retracted. |
| PR-3 | Progression **MUST NOT** be unnecessarily delayed when its required inputs already exist. A summary-class metric on a `REPLAY_UNAVAILABLE` match is finalizable and contributes normally. |
| PR-4 | Ordering is unchanged: an older unresolved match in the same bucket still settles first (foundation §4.4). Readiness does not reorder chronology. |

### 3A.2 Metric evidence classes

Six of the twenty metrics are summary-class; the other fourteen are replay-class. The per-metric classification is defined once, in [`../architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md`](../architecture/FEATURE-DATA-DEPENDENCY-MATRIX.md) §3, and is **not** restated here.

The consequence for this surface:

1. A replay-class metric on a `REPLAY_UNAVAILABLE` match is **N/A** (foundation §4A.4) — never zero, never estimated, never substituted.
2. N/A observations do not enter baselines, rolling windows, trend counts or PB history (foundation §8). This is existing law; it is restated because replay unavailability is now a named, expected cause of it.
3. Therefore **a track's readiness depends on the evidence class of its metrics.** Standard Carry hero-damage share may be baseline-ready while Standard Carry CS@10 is still building, purely because some matches lacked replay-derived evidence.
4. This is an **honest, correct outcome**, not a defect and not a degraded state. It is shown with the existing baseline-building and `Insufficient History` states, which are already defined as neutral and explicitly not decline.
5. Progress **MUST NOT** explain such a gap in backend terms. It shows the count and the readiness state, as it already does for a player who simply has not played enough.

### 3A.3 Rebuilds make no provider calls

Recomputation from a role correction, metric-version bump, methodology migration or baseline-definition change reads **stored** data only ([`../architecture/DATA-CONTRACTS-AND-VERSIONING.md`](../architecture/DATA-CONTRACTS-AND-VERSIONING.md) §7.2). A rebuild that needed a provider call would mean the stored derived features were incomplete — that is a storage defect, not an acceptable fallback.

This is what makes the locked rule that **baseline-definition changes apply retroactively** (foundation §14.3) possible at all.

---

## 4. Trend contract

Restated from foundation §11 because it is this surface's central object.

- A **trend point** is a baseline-ready observation paired with the baseline that existed before it.
- The window is the most recent **10 eligible trend points** for that exact identity.
- A state exists **only** with a complete 10-point window; otherwise `Insufficient History`.
- Direction follows the movement of the rolling baseline and respects metric polarity (lower dead-time rate is `Improving`).
- N/A points are skipped, not zeroed. Skipping may leave the window incomplete.
- A single outlier cannot create a state. A calendar gap cannot remove a valid point.
- Exact meaningful-movement thresholds are a **versioned calibration dependency**. Implementations MUST NOT invent a number, use a generic cutoff, or publish a fifth state. The calibration is bound by one measured constraint: the threshold MUST sit above the hero-mix noise floor, so a change of hero pool is not reported as a change in skill.

**Semantic requirements:**

- `Insufficient History` is **not** a claim of decline and MUST NOT be styled as a negative outcome.
- `Stable` means the window did not meet the movement requirement. It does **not** mean nothing happened, and MUST NOT read as stagnation or failure.
- Trend is **metric-level only**. Metrics disagreeing with one another is normal and is the truth.

**Forbidden here:** any role-level trend, any composite of several metrics, any overall progress curve, score, grade, rating or percentage.

```text
Valid:   "CS @10 — Improving"  ·  "Survival — Declining"  ·  "Healing — Insufficient History"
Invalid: "Your Carry is improving"  ·  "Carry Score: 78"  ·  "3 of 4 metrics up, so Carry is trending up"
```

An evidence-bound prose summary that names its metrics is permitted ("Laning and scaling are moving up while survival has slipped"). It MUST preserve polarity and N/A/Insufficient-History status, MUST NOT make causal claims, and MUST NOT turn a missing metric into a favourable or unfavourable judgment.

---

## 5. Baseline in Progress

- The baseline is contextual reference, not a score. It MUST NOT replace or hide the raw observation series.
- Progress uses only the declared comparison value for baseline and trend math, never an ad hoc UI conversion. The raw value remains available for factual display.
- The current match never enters its own baseline; the baseline window is previous-only, capped at 20, gated at 5 priors.
- **Match-level historical comparisons are not recomputed here.** A match's comparison used the baseline that existed before it. Progress shows the *current* baseline context. These are different things and MUST NOT be conflated in wording.

**Progress is not context-adjusted.** Context-adjusted expectations and matchup context are a Match Detail concern (foundation §10; `match_detail/SSOT.md`). The locked 10-match trend runs on the **raw rolling baseline**. Progress MUST NOT display a matchup badge, an adjusted expectation, or a hero/lane adjustment.

---

## 6. Inactivity and calendar

- Progression is **match-based**. There is no time decay, inactivity penalty, hard trend expiry, season reset, or Progress-owned retention cutoff.
- A long break contributes no observation and no penalty. Baseline and trend history are not reset or weakened.
- Recency MAY be shown separately (last activity in a role, time since last match) and MUST NOT be translated into a trend direction or given performance meaning.
- Calendar filters (30D, 90D, All, weekly, monthly) are **presentation windows**. They MUST NOT redefine the 20-observation baseline or the 10-point trend.

---

## 7. Personal Bests in Progress

- Progress shows the **current** canonical PB per eligible role metric within the selected bucket and role.
- Each PB carries enough context to trace it: value, hero, date/time, role, mode, and its source match — openable when accessible under the current entitlement.
- PB history is all known eligible observations for that identity, not the baseline window. A point above the current baseline is frequently not a PB.
- PBs use the **comparison value**; a raw display value may be higher while the comparison value is not a record.
- Ties are not PBs.
- If no qualifying source remains, the PB is **unavailable** — not zero.
- V1 exposes current ownership only; there is no user-facing lineage of every past PB.
- PB **celebrations** are not a Progress concept. Progress shows current truth; delivered celebrations live in the append-only event history.

---

## 8. Entitlement

- Progress has no retention cutoff of its own. It consumes the history exposed by the current entitlement.
- On entitlement **reduction**: rebuild current baseline/trend state from the newly exposed history. Observations are not deleted or fabricated to keep the UI populated. A previously valid trend MAY legitimately become `Insufficient History`.
- This MUST be kept visibly separate from analytical decline. **An entitlement change is not a performance event.**
- On entitlement **expansion or restoration**: re-admit the newly exposed retained history, replay it chronologically under the same methodology, and restore whatever state the evidence supports.
- Hidden or unentitled history MUST NOT be shown as zero, and MUST NOT be implied to be poor performance.

---

## 9. Correction and rebuild effects

After a role correction on match M:

- M's observations leave the old-role histories and enter the new-role histories at M's original chronology position, within the same bucket;
- affected old- and new-role baselines, trend points, trend states and current PB indexes replay **from that position forward**;
- unrelated roles, unrelated metrics and the other bucket are unchanged;
- if the new role lacks telemetry for one of its metrics, that metric is **N/A** under the new role — the old-role value is never copied across;
- delivered celebrations and notifications remain append-only and are not retracted or re-sent.

After a methodology or metric-version migration, Progress displays **one coherent methodology**. Consumers MUST NOT see a series where earlier points use old math and later points use new math. An incomplete migration keeps the previous coherent state or remains unavailable — it never publishes a partial mixed timeline.

A late-recovered historical match is inserted at its true chronology position, never appended.

Rebuilds are deterministic and idempotent, and make no provider calls.

---

## 10. States

| State | Meaning |
|---|---|
| Track has no history | This role has never been played in this bucket. Explicit unstarted state; never zero, never a flat line. |
| Baseline building | Fewer than 5 prior measured observations for this metric+role+mode. Value history may show; no comparison. Countable. |
| Baseline ready, trend insufficient | A baseline exists but fewer than 10 eligible trend points. `Insufficient History`. **Not a decline.** |
| Trend available | One of Improving / Stable / Declining. |
| Metric N/A at a point | Shown as N/A or omitted from a derived chart. **Never zero.** One expected cause is a match whose replay-derived evidence never arrived (§3A.2). |
| Match finalized without deep evidence | Its summary-class metrics contribute normally; its replay-class metrics are N/A. Not a gap in the record, not an error. |
| Metrics within one role at different readiness | Normal and expected. Shown with the existing building / `Insufficient History` states, never explained in backend terms. |
| Metric unsupported | Not in this role's set, or unsupported in V1 (Support Control). Absent — never proxied. |
| Sparse activity | Long gaps in chronology. No penalty, no decay; recency may be shown separately. |
| Entitlement reduced | Fewer observations exposed; state may regress to building/insufficient. Not decline. |
| Rebuilding | After a correction or migration. Honest transitional state; no mixed math displayed. |
| Offline / sync error | Known Progress data remains accurate and usable. |

---

## 11. Hard invariants

- A match contributes observations only at its single finalization point; no provisional or deep-dependent value is shown before its inputs exist.
- A metric whose inputs already exist is never delayed waiting for another metric's evidence.
- Metrics within one role legitimately sit at different readiness; that is shown with the existing neutral states and never explained in backend terms.
- Rebuilds read stored data only and make no provider calls.
- Every calculation is scoped to one bucket, one role, one metric, one metric version.
- No composite: no role trend, player score, grade, rating, percentage, cross-role normalization, or all-role curve.
- Trend requires a complete 10-point window; otherwise `Insufficient History`.
- `Insufficient History` is never styled or worded as decline; `Stable` is never worded as failure.
- Baseline is the previous-20 median after a 5-prior gate; the current match never enters its own baseline.
- N/A never becomes zero and never enters a baseline, trend or PB.
- Progress is never context-adjusted and never shows a matchup badge.
- Calendar filters never redefine canonical math.
- No time decay, inactivity penalty, trend expiry, season reset, or Progress-owned retention cutoff.
- PB uses the comparison value and all known eligible history; ties are not PBs.
- A role correction rebuilds only the affected same-bucket old/new-role closure.
- One canonical methodology is displayed at a time; mixed timelines are never published.
- Entitlement changes never masquerade as performance change.
- Win/loss never appears as a progression signal.

---

## 12. Acceptance rules

- [ ] A match still awaiting deep evidence contributes no observation, no baseline movement and no trend point.
- [ ] A match finalized without deep evidence contributes its summary-class metrics and shows N/A — not zero — for the rest.
- [ ] Two metrics in the same role at different readiness both render correctly, with no backend explanation shown.
- [ ] A baseline-definition change recomputes history from stored data with zero provider calls.
- [ ] Selecting a role and bucket shows only that track's metrics and series.
- [ ] No surface element aggregates metrics into a role-level verdict.
- [ ] A metric with fewer than 10 eligible trend points shows `Insufficient History`, styled neutrally.
- [ ] A lower-is-better metric moving down is `Improving`.
- [ ] N/A points are visibly not zero, and are excluded from baseline and trend counts.
- [ ] A calendar filter changes the view without changing any trend state or baseline.
- [ ] A role never played in the selected bucket shows an unstarted state, not zeros.
- [ ] Each PB shows its value, hero, date, role, mode and a route to its source match.
- [ ] A raw value higher than the PB's raw value does not display as a PB when its comparison value is lower.
- [ ] After a correction, only the affected old/new-role series in that bucket change.
- [ ] After a migration, no series shows mixed methodology.
- [ ] An entitlement reduction that regresses a trend is not presented as decline.
- [ ] No matchup badge, adjusted expectation or hero/lane adjustment appears anywhere on this surface.
