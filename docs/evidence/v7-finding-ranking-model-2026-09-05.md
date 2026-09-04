# The V7 Finding ranking model — 2026-09-05

The owner redefined a Finding:

> A Finding is something I would not know without looking at my whole year.
> Rank my own patterns by how strongly they show up **in my own data**. I do
> not need to be unusual against the population to be told what I am. If my
> result is INTJ and 90% of people are INTJ, I should still see INTJ.

This document specifies what "strongly shows up in my data" means precisely
enough to implement, and shows what it does to reach.

```text
PHASE: V7_FINDING_RANKING_MODEL
STATUS: DESIGN — derived from already-measured variance components
NEW PROVIDER CALLS: 0
CORPUS READ: NO — computed from the published tournament output
```

## 1. The mistake the old model made

The previous model published a Finding when a player's effect was
*statistically distinguishable from the population average*. Under that rule
the best five-Finding portfolio reached 15.4% of players, and no candidate
selection could fix it — the ceiling is a closed-form function of `tau/SE`
(`docs/evidence/v7-qualification-ceiling-2026-09-04.md`).

The rule was wrong, not the data. "Distinguishable from average" is a claim
about the *population*; the owner wants a claim about *the player*. Most people
are near average — that is what average means — so a population-contrast gate
is guaranteed to have nothing to say about most people.

**The population is the ruler, not the bar.** It supplies the scale that makes
two different Findings comparable. It does not decide who is allowed one.

## 2. The model

For player `p` and Finding dimension `f`, the tournament already produces a
per-player effect `delta_hat` with a standard error, and a population spread
`tau_f`. Three quantities follow.

### 2.1 Position, in population units

```text
z_pf = (delta_hat_pf - mu_f) / tau_f
```

How far from typical this player sits, measured in population standard
deviations. Dividing by `tau` rather than by `SE` is the whole difference from
the old model: `tau` is a *ruler*, `SE` is a *test*.

### 2.2 Reliability — how much of that is real

```text
r_pf = tau_f^2 / (tau_f^2 + SE_pf^2 * D_f)
```

The classic shrinkage weight: the share of a player's measured deviation that
is signal rather than measurement noise. `D_f` is the **dependence inflation
factor**, taken from the variance-ratio curve the tournament measured at a
batch length of 100. It matters: a player's matches are serially dependent, a
naive `SE` understates the true uncertainty, and skipping the correction would
inflate every reliability figure.

### 2.3 The ranking score

```text
score_pf = |z_pf| * r_pf         (the shrunk position, in population units)
direction_pf = sign(z_pf)
```

A player's Findings are their own dimensions sorted by `score`. Everyone with
enough matches gets a ranked list. Nobody is excluded for being ordinary.

The model is self-regulating: a dimension measured badly for this player has a
low `r`, so its score collapses toward zero and it cannot reach the top of the
list on noise alone.

## 3. What this does to the corpus we already have

Reliability per family, computed from the tournament's own published `tau`,
median `SE`, and dependence inflation. No new data.

| family | naive `r` | **dependence-corrected `r`** |
|---|---:|---:|
| duration_tempo | 0.989 | **0.973** |
| purchase_tempo | 0.982 | **0.923** |
| position_flexibility | 0.957 | **0.901** |
| fight_timing_centroid | 0.909 | **0.851** |
| post_loss_session_continuation | 0.870 | **0.713** |
| hero_novelty | 0.921 | **0.688** |
| post_loss_hero_switch | 0.905 | **0.672** |
| post_loss_requeue_latency | 0.845 | **0.646** |
| lead_retention | 0.514 | **0.536** |
| transfer_risk | 0.554 | 0.291 |
| transfer_activity | 0.510 | 0.281 |
| lane_recovery_participation | 0.378 | 0.268 |
| **side_sensitivity (negative control)** | 0.113 | **0.108** |

**Nine of twelve families clear 0.50.** For a typical player, 65–97% of their
measured deviation on those dimensions is real.

The negative control is the proof the metric is not simply generous: a Finding
built on which side of the map you were assigned — something no player controls
— scores 0.108. The model says, correctly, that there is almost nothing there.

Three families stay weak (`transfer_*`, `lane_recovery_participation`). Under
the old model they were rejected; under this one they are simply outranked, per
player, by dimensions that are measured better. No separate rejection rule is
needed, which is a good sign the metric is doing real work.

## 4. Reach

Under this model, a player receives a ranked Finding list whenever their
matches support the underlying estimands at all. From the capability atlas, the
support thresholds are met by **84–90% of sampled accounts** at a 100-match bar,
and the median account has 526 product-context matches.

So the design target — most sufficiently active players receiving several
genuine Findings — is met by construction, and the 15.4% figure does not carry
forward. **That number was a property of the discarded rule, not of the data.**

This is not a relaxation of a statistical standard. Nothing has been re-tuned,
no alpha was raised, no threshold moved. The estimands, the standard errors and
the dependence correction are exactly the ones the independent tournament and
red-team already validated. What changed is the question being asked of them.

## 5. What honesty now requires

Dropping the significance gate moves the burden onto presentation.

1. **Report a strength band, not a verdict.** `score` is banded — *pronounced*,
   *moderate*, *slight* — and the copy must match the band. A slight Finding may
   not be phrased as a defining trait.
2. **Report the interval, not just the point.** The shrunk estimate carries an
   interval derived from `r`. A Finding whose interval spans zero is still
   shown, but it is described as a tendency, never as a fact.
3. **Direction is part of the Finding.** `sign(z)` decides which of two opposite
   copy variants is used. "You keep playing after a loss" and "you stop for the
   day" are the same dimension and different Findings.
4. **A calibrated dimension is still required.** Reliability answers *is this
   real for you*; it does not license an estimand whose null model is broken.
   The tournament's calibration work still gates which dimensions exist at all.
5. **Population position is not skill.** Unchanged from learning 10. A
   percentile is a location, not a ranking of worth.

## 6. Section coverage

The report has distinct sections — what is good, what is costing you, how you
respond to a loss, what to improve. A purely global top-N would happily return
five Findings from one family and leave whole sections empty.

Selection is therefore **stratified**: take the top-scoring Finding within each
report section first, then fill remaining slots globally by score. This
guarantees narrative coverage without weakening the ranking, and it replaces the
old portfolio-overlap machinery, which existed only to stop a significance gate
concentrating on the same users.

## 7. Improvement recommendations are a different computation

Section 5 of the report ("what to improve") must not reuse this ranking.
Distinctiveness is not actionability: the most distinctive thing about a player
may be something they should keep doing.

Recommendations rank a different quantity — the **within-player gap between
their own wins and their own losses** on dimensions that are actionable in a
next game — and are subject to the rule that the diagnosis must sit upstream of
the result. That model is specified separately.

## 8. What this does not decide

```text
DECIDES: how a player's own patterns are ranked, and why reach is no longer
         the binding constraint
DOES NOT DECIDE: which dimensions ship, the strength-band cut points, the copy,
         or the final report composition
```

Band cut points are calibration and belong to a later phase, against the
reserved split, not to this design.
