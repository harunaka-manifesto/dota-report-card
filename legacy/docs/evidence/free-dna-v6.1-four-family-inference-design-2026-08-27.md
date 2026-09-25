# V6.1 Four-Family Inference Design

## Status

**PASS WITH LIMITATIONS — all four candidate family methods passed the
predeclared Type-I gates.** The next status is
`READY_FOR_MARGIN_STABILITY_AND_MULTIPLICITY_CALIBRATION`. Production
implementation remains blocked.

## Integrity

| item | value |
| --- | --- |
| task type | ANALYTICAL RESEARCH + STATISTICAL METHOD DESIGN + DOCUMENTATION |
| base SHA | `fc3a728787e978c3e1ad9589e20806686f95ef28` |
| branch | `research/v61-four-family-inference-design` |
| origin/main observed at start | `e523d855e307f1e0202377b5269142c0e009b65a` |
| external collection calls | 0 |
| tuning profiles loaded | 0 |
| holdout reruns | 0 |
| thresholds or margins derived | 0 |
| production changes | 0 |

The run was socket-blocked and used synthetic known-truth data only. It did not
inspect the tuning partition, revealed holdout, production reports, or frozen
runtime artifacts.

## Binding method decision

The retained research candidate is **session signed-prevalence randomization**.
For every supported component, first compute one signed effect per independent
session. The inferential estimand is:

```text
theta = P(session effect > 0) - P(session effect < 0)
```

The null is sign balance, `theta = 0`; it is not a zero-mean null. Zero effects
are ties, are reported, and do not enter the sign denominator. The two-sided
p-value uses 2,000 Monte Carlo sign-randomization draws with an add-one
correction. An unsupported component receives `p=1`, and a family with no
supported component abstains.

Transfer and Post-Loss each retain exactly three fixed components or contrasts.
Their family p-value is `min(1, 3 * min(component p))`, with unsupported rows
still occupying their fixed slot at `p=1`. This Bonferroni union bound controls
the internal family error under arbitrary component dependence. Presence &
Exposure and Session Drift each have one predeclared statistic.

This method deliberately trades magnitude efficiency for a bounded question:
is the direction repeated across independent sessions? Magnitude remains
descriptive until new practical margins are calibrated for this new estimand.

## Frozen family contracts

### Transfer

| field | contract |
| --- | --- |
| question | What survives when the hero changes? |
| raw unit | Eligible match in a fixed cross-fitted core or reliable-stretch band. |
| session effect | Reliable-stretch session mean minus core session mean. A session must contain both bands for that component. |
| components | Outcome, context-adjusted activity, survival-oriented negative death exposure. |
| minimum support | At least 12 informative paired sessions, at least 30 component-complete matches in each band, at least 80% context coverage; band assignment fixed before inference. |
| family test | Three fixed two-sided sign-randomization tests plus Bonferroni. |
| evidence required | Core/stretch counts, paired-session count, component theta/interval/p-value, fixed frontier status, coverage, ties, and sensitivity diagnostics. |
| forbidden claim | Hero-choice causality, skill, mastery, or a mean-magnitude claim from theta. |

At least one component may be supported. Unsupported components fail closed at
`p=1` and cannot supply branch evidence. A future compatibility or “clean
transfer” statement requires a separately validated equivalence design; it is
not licensed by a nonsignificant direction test.

### Post-Loss Response

| field | contract |
| --- | --- |
| question | How does the next same-session hero choice move after supported result states? |
| raw unit | Chronological adjacent transition wholly within one session. |
| states | `win`, `one_loss`, `two_plus_losses`, `win_streak`. |
| contrasts | Each of `one_loss`, `two_plus_losses`, and `win_streak` versus the fixed `win` reference. |
| session effect | Target-state session mean movement minus win-state session mean movement. |
| minimum support | At least 12 informative paired sessions and 30 transitions across each compared state pair, with at least 80% required coverage. |
| family test | Three fixed two-sided sign-randomization tests plus Bonferroni. |
| evidence required | State and paired-session counts, theta/interval/p-value for the selected contrast, same-hero and next-result guardrails, ties, and coverage. |
| forbidden claim | Psychology, tilt, intent, causality, or any cross-session transition. |

Overlapping transitions remain clustered inside their session. A nonsignificant
contrast is abstention, not evidence of invariance.

### Presence & Exposure

| field | contract |
| --- | --- |
| question | When your scoreboard involvement rises, what happens to your death exposure? |
| raw unit | Paired context-adjusted involvement-per-minute and death-exposure-per-ten-minute observation. |
| session effect | Sign of the within-session centered least-squares slope. |
| minimum support | At least 12 qualifying sessions, 30 paired observations, 3 paired observations per qualifying session, 80% context coverage, and within-session involvement variation. |
| family test | One two-sided sign-randomization test. |
| evidence required | Theta/interval/p-value, paired observations, sessions, ties, coverage, duration audit, and hero/function/role sensitivity. |
| forbidden claim | Aggression, positioning, good or bad deaths, efficiency, skill, intent, causality, or a complete combat model. |

Within-session centering removes purely between-session level association from
the estimand. It does not remove unobserved hero, role, draft, opponent, team
tempo, or match-state confounding. Positive and inverse are the only possible
qualified directions; neutral is abstention.

### Session Drift

| field | contract |
| --- | --- |
| question | Within completed sessions, what changes from early to late? |
| raw unit | Eligible match in a boundary-safe completed session. |
| session effect | Late-half win rate minus early-half win rate; omit the middle match when session length is odd. |
| minimum support | At least 12 informative completed sessions, at least 4 matches per session, and at least 50% qualifying-session coverage. |
| censor rule | Exclude left-censored, right-censored, and corrupt sessions. |
| family test | One two-sided sign-randomization test. |
| evidence required | Theta/interval/p-value, session and match counts, ties, length distribution, boundary flags, and coverage. |
| forbidden claim | Fatigue, learning, tilt, causality, or a duration claim. |

The current helper's broad `completed_sessions` view does not exclude
left-censored sessions. A later research implementation must use the existing
explicit censor metadata rather than that convenience view alone.

## Source-mapping audit

| family | current inputs sufficient? | required research mapping |
| --- | --- | --- |
| Transfer | Yes | Rebuild fixed-band component means inside each session, rather than reusing the annual frontier scalar. |
| Post-Loss | Yes | Reuse the V6.1 state vocabulary and adjacent same-session transitions, then form paired session contrasts. |
| Presence & Exposure | Yes, with bounded wording | Pair context-adjusted per-match rates and compute the centered slope inside each qualifying session. |
| Session Drift | Yes | Reuse early/late bucketing but restrict to explicit boundary-safe sessions and result only. |

No production estimator currently implements these inferential contracts. This
task validates research methods; it does not silently reinterpret current
runtime p-values.

## Predeclared validation

Each scenario used 1,000 independent synthetic datasets and each dataset used
exactly 2,000 null draws. The family method passed a scenario only when:

```text
estimated Type-I error <= 0.065
and the 95% Wilson lower bound <= 0.05
```

The 67 scenarios included exact zero, symmetric Gaussian, skewed magnitude,
heavy tails, unequal session sizes, 12- and 60-session boundaries, low/high
opportunity counts, strong component correlation, heteroskedastic sessions, a
dominant session, partial component support, and fail-closed structural
ineligibility. Family-specific screens added band imbalance, session sign
reversal, unequal state frequency, overlapping transition dependence, pure
between-session confounding, nonlinear symmetric association, isolated
single-session signals, session-length selection, and censor exclusion.

These simulations start at the predeclared per-session effect boundary. They
validate the inference rule under known sign-generating processes; they do not
replace later end-to-end estimator parity tests on authorized tuning data.

## Type-I results

| family | null scenarios | worst estimated Type-I | verdict |
| --- | ---: | ---: | --- |
| Transfer | 16 | 0.045 | `METHOD_VALIDATED_WITH_LIMITATIONS` |
| Post-Loss Response | 16 | 0.037 | `METHOD_VALIDATED_WITH_LIMITATIONS` |
| Presence & Exposure | 17 | 0.044 | `METHOD_VALIDATED_WITH_LIMITATIONS` |
| Session Drift | 18 | 0.040 | `METHOD_VALIDATED_WITH_LIMITATIONS` |

All exact-zero and below-support datasets returned `p=1`. Missing support for
one component did not shrink the fixed three-component multiplicity universe.

## Power and interval behavior

Power was run only after all Type-I gates passed. Each power cell used 1,000
datasets, 60 informative sessions, and true signed prevalence effects
`theta={0.05, 0.15, 0.30, 0.50}`.

| family | power at theta .05 / .15 / .30 / .50 | max absolute theta bias | Wilson coverage range |
| --- | --- | ---: | --- |
| Transfer | .038 / .103 / .435 / .937 | .0043 | .937–.978 |
| Post-Loss Response | .040 / .117 / .425 / .948 | .0078 | .960–.969 |
| Presence & Exposure | .043 / .159 / .581 / .979 | .0042 | .962–.970 |
| Session Drift | .045 / .160 / .598 / .982 | .0043 | .949–.970 |

Power was monotone in every family. Small effects are intentionally difficult
to publish, and the three-component Bonferroni families pay a visible power
cost. No method or support rule was tuned to improve publication yield.

## Practical margins and tuning

All inherited magnitude margins are **not transferable** because the estimand
changed to signed session prevalence. No margin was derived and no tuning
profile was inspected. The next authorized analytical pass must derive
tuning-only practical margins, predeclare stability/robustness gates, and
measure how often structural support is actually available without optimizing
for publication count.

## Four-family multiplicity readiness

Pool is absent from the candidate hypothesis universe. If all four retained
families are structurally present, the candidate universe is `m=4`; unsupported
families must remain `p=1` rather than disappearing from the denominator.

A preliminary 1,000-dataset synthetic screen exercised all four p-values under
a correlated latent null. Observed pairwise p-value correlations were between
-0.007 and 0.092. This is only a code-path and dependence-readiness screen. It
does not establish the dependence structure on player data and does not choose
or approve BH. Status is `READY_FOR_FOUR_FAMILY_DEPENDENCY_VALIDATION`.

## Decision

| item | decision |
| --- | --- |
| Transfer method | `METHOD_VALIDATED_WITH_LIMITATIONS` |
| Post-Loss Response method | `METHOD_VALIDATED_WITH_LIMITATIONS` |
| Presence & Exposure method | `METHOD_VALIDATED_WITH_LIMITATIONS` |
| Session Drift method | `METHOD_VALIDATED_WITH_LIMITATIONS` |
| Pool family test | `NONE — DEMOTED_TO_ELEMENTS` |
| practical margins | `NOT DERIVED` |
| stability/robustness gates | `NOT FROZEN` |
| external four-family correction | `NOT CHOSEN` |
| production implementation | `BLOCKED` |
| next status | `READY_FOR_MARGIN_STABILITY_AND_MULTIPLICITY_CALIBRATION` |

## Required local artifacts

The complete machine-readable record is local-only under
`.local/diagnostics/v61-four-family-inference-design/`:

- `family_contracts.json`
- `candidate_methods.json`
- `null_simulation_results.csv`
- `type1_summary.csv`
- `power_results.csv`
- `family_method_verdicts.json`
- `tuning_method_behavior.csv`
- `margin_transferability.csv`
- `multiplicity_readiness.json`
- `aggregate_summary.json`

## What must not change yet

- production family IDs, estimators, thresholds, semantic outcomes, copy,
  Elements, or report contracts;
- the frozen V6.1 source binding or artifact package;
- tuning/holdout membership or the revealed holdout;
- multiplicity rules or the three-Finding display cap; and
- provider collection, deployment, flags, database, Redis, or infrastructure.
