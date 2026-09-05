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

**Corrected 2026-09-05, after running the model end to end.** The first version
of this table mixed two estimators: it took `tau` from the tournament's
Paule-Mandel pooling, which subtracts only `SE^2`, and combined it with a
dependence-inflated `SE^2 * D` in the denominator. That is inconsistent — if
measurement variance is inflated for the reliability, the same inflated variance
must be removed when estimating the between-player spread, or the spread is
credited with noise it does not own. The effect was to **overstate reliability**,
by up to 27 points on the post-loss families.

The figures below come from running the real pipeline over DISCOVERY: per-player
estimates from the validated inference layer, `D` measured per family from its
own variance-ratio curve, and `tau` estimated consistently as
`max(0, var(delta_hat) - mean(SE^2 * D))`.

| family | players | `tau` (consistent) | **reliability (median)** | share scoring > 0.25 |
|---|---:|---:|---:|---:|
| duration_tempo | 538 | 0.1126 | **0.976** | 46.3% |
| purchase_tempo | 116 | 0.0566 | **0.919** | 75.9% |
| position_flexibility | 114 | 0.1077 | **0.828** | 78.1% |
| fight_timing_centroid | 116 | 0.0116 | **0.808** | 75.0% |
| hero_novelty | 525 | 0.1187 | **0.736** | 74.3% |
| post_loss_session_continuation | 536 | 0.0679 | **0.537** | 70.5% |
| lead_retention | 109 | 0.0546 | **0.537** | 71.6% |
| post_loss_hero_switch | 527 | 0.0704 | **0.463** | 56.2% |
| post_loss_requeue_latency | 527 | 0.1305 | **0.380** | 60.9% |
| transfer_risk | 501 | 0.0000 | 0.000 | 0.0% |
| transfer_activity | 501 | 0.0000 | 0.000 | 0.0% |
| lane_recovery_participation | 113 | 0.0000 | 0.000 | 0.0% |
| **side_sensitivity (negative control)** | 536 | **0.0000** | **0.000** | **0.0%** |

**Nine families carry real between-player signal.** Four go to exactly zero,
and that is the more interesting half of the result: under a consistent
estimator their entire observed spread is explained by dependence-inflated
measurement error. There is no between-player signal left to rank. The old model
graded three of them D by a completely different route — a failed confirmation
pass — and the two methods agree.

The negative control is the proof the metric is not generous. A Finding built on
which side of the map a player was assigned — something nobody controls —
returns `tau` of exactly zero, so reliability is zero, so no player receives a
score at all. The estimator refuses to manufacture a Finding from noise, and it
does so without any rule that mentions the control by name.

Between 46% and 78% of measurable players score above 0.25 on the surviving
families, which is what makes a ranked list possible for ordinary players rather
than only for outliers.

## 4. Reach

Under this model, a player receives a ranked Finding list whenever their
matches support the underlying estimands at all. From the capability atlas, the
support thresholds are met by **84–90% of sampled accounts** at a 100-match bar,
and the median account has 526 product-context matches.

So the design target — most sufficiently active players receiving several
genuine Findings — is met by construction, and the 15.4% figure does not carry
forward. **That number was a property of the discarded rule, not of the data.**

This is a claim about *coverage*, not about strength. Every measurable player
gets a ranked list; how much that list is worth depends on their own scores, and
section 5 is what keeps the presentation honest about it.

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
