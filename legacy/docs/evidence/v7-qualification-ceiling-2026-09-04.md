# What a significance-gated Finding can reach, at best — 2026-09-04

**This is a diagnostic, not a threshold choice.** It sets no alpha, selects no
publication rule, freezes no multiplicity family, and reads no corpus data. It
takes the variance components the tournament already measured and asks a
structural question the owner needs answered before choosing five Findings:

> Under a rule of the form *"publish when this player's effect is
> distinguishable from the population average"*, what share of players **can**
> qualify — for any candidate, at best?

```text
PHASE: V7_QUALIFICATION_CEILING_DIAGNOSTIC
STATUS: COMPLETE
PUBLICATION THRESHOLDS CHOSEN: NO
MULTIPLICITY FAMILY FROZEN: NO
CORPUS READ: NO — derived from the tournament's published variance components
NEW STRATZ CALLS: 0
CALIBRATION_RESERVED / SEALED_VALIDATION TOUCHED: NO
```

Source: `docs/evidence/v7-statistical-tournament-discovery-2026-09-03.json`
(code SHA `e0230b3165b101e51c84529084f575d887e00d37`, design digest
`4b702dc29f7cd60caecd74ec2bdba3ff5775038fed664e1eb0fa9ffedc4573f3`).
Reproduce with `scripts/v7_qualification_ceiling.py`; the maths is unit-tested
in `tests/unit/test_v7_qualification_ceiling.py`.

## The closed form

Under the tournament's own model,

```text
delta_p            ~ N(mu, tau^2)          true player effects
delta_hat_p | ...  ~ N(delta_p, SE_p^2)    what can be measured
```

the observed deviation `delta_hat_p - mu` is marginally `N(0, tau^2 + SE_p^2)`.
A two-sided test at critical value `z` therefore rejects with probability

```text
q(z, r) = 2 * Phi( -z / sqrt(1 + r^2) ),     r = tau / SE_p
```

which depends on the data **only** through the signal-to-noise ratio `r`. Reach
is not a property of how clever the candidate is. It is a property of how large
between-player variation is relative to per-player measurement error.

This is a ceiling in the strict sense: it assumes a perfectly calibrated test,
no multiplicity correction, no effect-size requirement, and no stability gate.
Adding any of those lowers it.

## What ratio the product target demands

For a five-Finding portfolio, `P(at least 3 of 5)` under the convenient
assumption of independent candidates — convenient, because correlated
candidates do worse:

| P(≥3 of 5) target | per-candidate share needed | needed `tau/SE` at 0.05 | needed `tau/SE` at 0.01 |
|---|---:|---:|---:|
| 60% | 0.554 | 3.16 | 4.23 |
| 70% | 0.610 | 3.71 | 4.95 |
| **80%** | **0.673** | **4.54** | **6.03** |
| 85% | 0.710 | 5.18 | 6.86 |
| 90% | 0.753 | 6.16 | 8.14 |

Single-candidate reach, for reference:

| single-candidate share | needed `tau/SE` at 0.05 | needed `tau/SE` at 0.01 |
|---|---:|---:|
| 60% | 3.60 | 4.81 |
| 75% | 6.07 | 8.02 |
| 80% | 7.67 | 10.12 |
| 90% | 15.57 | 20.47 |

## What ratio the corpus actually delivers

`tau` and the standard-error quantiles are the tournament's measured values on
DISCOVERY. `predicted` is the closed form at the median standard error;
`observed` is the share that actually qualified at the provisional 0.01 level.

| family | grade | tau | SE median | **tau/SE** | predicted 0.05 | predicted 0.01 | observed 0.01 |
|---|:--:|---:|---:|---:|---:|---:|---:|
| duration_tempo | C | 0.0944 | 0.0097 | **9.69** | 0.841 | 0.791 | 0.323 |
| purchase_tempo | B | 0.0619 | 0.0083 | **7.46** | 0.795 | 0.732 | 0.515 |
| position_flexibility | C | 0.1059 | 0.0225 | 4.70 | 0.684 | 0.592 | 0.351 |
| hero_novelty | C | 0.1020 | 0.0300 | 3.41 | 0.581 | 0.468 | 0.307 |
| fight_timing_centroid | C | 0.0127 | 0.0040 | 3.15 | 0.554 | 0.436 | 0.239 |
| post_loss_hero_switch | **A** | 0.1068 | 0.0347 | 3.08 | 0.545 | 0.427 | 0.202 |
| post_loss_session_continuation | **A** | 0.0977 | 0.0377 | 2.59 | 0.480 | 0.354 | 0.275 |
| post_loss_requeue_latency | B | 0.2193 | 0.0941 | 2.33 | 0.440 | 0.310 | 0.223 |
| transfer_risk | B | 0.1311 | 0.1177 | 1.11 | 0.190 | 0.085 | 0.079 |
| lead_retention | D | 0.0546 | 0.0531 | 1.03 | 0.172 | 0.072 | 0.046 |
| transfer_activity | D | 0.3076 | 0.3013 | 1.02 | 0.170 | 0.071 | 0.061 |
| lane_recovery_participation | D | 0.3444 | 0.4422 | 0.78 | 0.122 | 0.042 | 0.035 |
| **side_sensitivity (control)** | — | 0.0145 | 0.0407 | 0.36 | 0.065 | 0.015 | 0.009 |

## Three readings, in order of importance

### 1. The binding constraint is the qualification concept, not the candidate set

Every **calibrated** candidate — the contrast families, the only ones whose
p-values the tournament could certify — sits between `tau/SE` 0.78 and 3.08.
Three-of-five for 80% of players needs about **6**. Standard error falls as
`1/sqrt(n)`, so closing that gap by volume alone would need roughly a
**fourfold increase in matches per player**, on a population whose median
account already supplies 378–553 opportunities in a 365-day window. It is not
available, and no amount of candidate cleverness substitutes for it.

So: under a significance gate against the population average, an 80–90%
three-of-five portfolio is **not reachable from this corpus**. Reporting that
is the correct response. The alternative — reaching it by raising alpha,
dropping the stability requirement, or picking each user's best three p-values —
is exactly what the binding product principle forbids.

### 2. The families with enough signal are the ones whose p-values are not trustworthy

`duration_tempo` at 9.69 and `purchase_tempo` at 7.46 clear the required ratio
comfortably. They are graded C and B precisely because they are **level**
estimands, and the tournament measured every level family as anticonservative:
their standard errors cannot absorb the within-player drift that a 365-day
window carries, and no block length the corpus supports fixes it.

That is a much sharper research direction than "find better candidates". The
open question is not *is there signal* — there is, and more of it than the
target needs. It is **can a level estimand over a drifting year be given an
honest uncertainty model**. Restricting the window, modelling the drift as a
context term, or reformulating a level family as a within-player contrast are
all live options, and all belong after the owner has chosen a direction.

### 3. Even the closed form is optimistic

Predicted reach exceeds observed reach for every family, badly for the level
ones: `duration_tempo` predicts 0.791 and delivers 0.323. The Gaussian
model overstates because real effects are not normal, standard errors are
heterogeneous and heavy-tailed, and the level families' errors are inflated by
dependence the model does not carry. So the numbers in the ceiling table are an
upper bound on an upper bound.

The negative control behaves exactly as it should: `tau/SE` 0.36, predicted
0.015, observed 0.009 at nominal 0.01. The diagnostic does not manufacture
reach any more than the tournament manufactures individuality.

## What this does and does not decide

```text
DECIDES: that a significance-gated portfolio cannot reach the 80-90% target
         from this corpus, and why, in terms the owner can act on
DOES NOT DECIDE: the publication rule, the alpha, the effect requirement,
         the multiplicity family, or which five Findings ship
```

The owner packet carries the consequences as explicit options. None of them is
enacted here.
