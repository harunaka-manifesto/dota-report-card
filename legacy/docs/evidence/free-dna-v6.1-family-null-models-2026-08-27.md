# V6.1 Family Null-Model & Inference Design

## Status

**PARTIAL — the family audit reached a pre-simulation stop condition.**

## Integrity

| item | value |
| --- | --- |
| base SHA | `c28c5bc1f83375e73f5782dd67232b66189daa8f` |
| branch | `research/v61-family-null-models` |
| task type | ANALYTICAL + DOCUMENTATION, research-only |
| external collection calls | 0 |
| holdout reruns | 0 |
| production changes | 0 |

This continuation ran in the existing isolated worktree. It read the runtime
estimators, report assembly, family/branch statistics, semantic catalog,
training-only calibration builder, and prior hardening evidence. It did not
load the 791-profile tuning partition, the revealed 339-profile holdout, a
provider, or a frozen runtime artifact.

## Prior method failure

The shared scalar-centered bootstrap was rejected because it did not impose
the null represented by each family. It was anti-conservative even for the
Pool scalar (worst null alpha 0.120) and severely inflated for selected maxima
(worst alpha 0.311–0.360). Centering a maximum after component selection loses
the joint component null. The replacement therefore has to begin with an exact
family question and jointly null-generated component evidence.

## Design standard

For a retained family, the estimand, structural support, contrast set, scaling,
null, statistic, null generator, invalid-draw rule, and uncertainty method must
be fixed before simulation. Max statistics must be rebuilt from the complete
joint component vector in every null draw. Equivalence is a separate claim and
must not be inferred from failure to reject a difference null. Tuning data,
practical margins, and publication yield cannot choose the method.

## Pool Shape

### Estimand

**Not frozen.** The current public root contains at least three questions:
static concentration (`hidden_center`), hero-versus-job breadth, and
chronological hero-versus-job migration. The proposed scalar
`hero_JSD - job_JSD` answers only the third. Runtime production evidence instead
uses `breadth - toolkit`. Those are not interchangeable estimands, and job
labels are a deterministic coarsening of hero identities.

### Null

No single Pool null is approved. A retained migration-only question could use
`H0: JSD_hero(first,last) - JSD_job(first,last) = 0`, but that null does not
cover concentration or static breadth branches.

### Statistic

No family statistic is approved. A migration-only candidate would be a
studentized signed JSD contrast, with the nonlinear JSD and chronological thirds
recomputed for every valid draw.

### Null-generation method

Not selected. Hero/job-label exchange is invalid; matches are not exchangeable
across chronology; and centering a resampled scalar already failed. A
constrained session-cluster or influence-function/bootstrap-t construction
would need its own known-truth validation after the family question is reduced.

### Type-I results

**NOT RUN — specification stop.** Prior shared-method worst alpha: 0.120.

### Power results

**NOT RUN.**

### Verdict

`FAMILY_SPECIFICATION_GAP`.

## Transfer

### Estimand

Candidate vector
`Delta_k = mean(k | reliable_stretch) - mean(k | core)` for outcome,
context-adjusted involvement, and negative context-adjusted death exposure.
Cross-fitted band assignments and calibration bytes remain fixed. Each
component retains its native unit; practical margins are not statistical
standardizers.

### Null

`H0: Delta_outcome = Delta_activity = Delta_survival = 0` for the structurally
eligible core/reliable-stretch population. Compatibility inside ROPEs is a
separate intersection-union/equivalence question.

### Statistic

Candidate `max_k |Delta_k / SE_cluster,k|`, with component cluster-robust
studentization and the component vector recomputed jointly. Structural support
is decided before looking at the statistic: both bands and all tested
components must meet fixed match, session, and coverage minima.

### Null-generation method

Candidate joint wild session-cluster bootstrap on null-restricted estimating
equations, preserving within-session rows and fixed cross-fit bands. Every draw
must recompute all component pivots and their maximum. This is a proposal, not a
validated method.

### Type-I results

**NOT RUN — global specification stop.** Prior shared-method worst alpha: 0.311.

### Power results

**NOT RUN.**

### Verdict

`METHOD_REQUIRES_REPLACEMENT`.

## Post-Loss Response

### Estimand

Candidate vector of predeclared pairwise differences among same-session
transition-state mean distance movements for `win`, `one_loss`,
`two_plus_losses`, and `win_streak`. The supported contrast set must be selected
only from outcome-blind state/session counts; unsupported states remain absent.

### Null

`H0`: all structurally supported result-state movement means are equal in the
predeclared contrast space. This preserves the actual repeated-measures target
and does not equate a centered bootstrap mean with the null.

### Statistic

Candidate maximum absolute cluster-studentized supported state contrast. State
means retain the runtime equal-session weighting. Overlapping transitions and
shared controls remain in the same session cluster.

### Null-generation method

Candidate null-restricted repeated-measures wild session-cluster bootstrap.
Each draw preserves session chronology and transition overlap, rebuilds every
supported contrast, and then recomputes the maximum. The exact missing-state
estimating equations still require specification and validation.

### Type-I results

**NOT RUN — global specification stop.** Prior shared-method worst alpha: 0.304.

### Power results

**NOT RUN.**

### Verdict

`METHOD_REQUIRES_REPLACEMENT`.

## Combat Expression

### Estimand

**No coherent single family estimand exists in the current catalog.** The
branches combine involvement equivalence, exposure equivalence, result versus
expression relationships, and localized variance. Some result branches have no
corresponding outcome measurement in the current family statistic.

### Null

No single null can simultaneously mean component equivalence, result-expression
association, and variance localization. Defining one would change the public
question rather than repair inference.

### Statistic

None. The fixture statistic maximizes separately scaled involvement/exposure
departures, while production subtracts adjusted involvement and adjusted death
exposure in incompatible units. Production then copies the same family sample
to every branch. Neither operation represents the catalog's heterogeneous
hypotheses.

### Null-generation method

Not applicable until the branches are split, reduced to supporting signals, or
retired.

### Type-I results

**NOT RUN — mandatory Combat stop.** Prior shared-method worst alpha: 0.311.

### Power results

**NOT RUN.**

### Verdict

`FAMILY_REDESIGN_REQUIRED`. Combat decision:
`MULTIPLE_HYPOTHESES_REQUIRED`.

## Session Drift

### Estimand

A simpler candidate is the mean within-session late-minus-early result contrast
among completed sessions that meet a predeclared minimum length. This targets
the selected completed-long-session population explicitly; it does not claim
to generalize G4/G5+ behavior to short or incomplete sessions. It replaces the
current unequal G1–G5+ maximum, where G5+ pools multiple matches per session.

### Null

`H0: E(session-level late result - early result) = 0` in the eligible completed
session population.

### Statistic

Candidate absolute cluster-studentized mean of one paired difference per
session. The early/late windows, minimum session length, completion rule, and
missing-value handling must be fixed before outcomes are inspected.

### Null-generation method

Candidate null-restricted wild bootstrap of paired session differences. A
sign-flip randomization is not assumed valid without a defensible symmetry
condition. Completed-session censoring is held fixed, and inference is limited
to that selected population.

### Type-I results

**NOT RUN — global specification stop.** Prior shared-method worst alpha: 0.360.

### Power results

**NOT RUN.**

### Verdict

`METHOD_REQUIRES_REPLACEMENT`.

## Cross-family method comparison

| family | final candidate | null-generation candidate | current disposition |
| --- | --- | --- | --- |
| Pool | unresolved among concentration, breadth, migration | unresolved | specification gap |
| Transfer | 3-component studentized max | joint null-restricted wild cluster | unvalidated replacement |
| Post-Loss | supported state-contrast studentized max | repeated-measures wild cluster | unvalidated replacement |
| Combat | none | none | redesign required |
| Session | paired completed-session early/late scalar | paired wild cluster | unvalidated replacement |

The candidate wild-bootstrap descriptions are research directions only. No
method received a validation verdict because the mandatory family-definition
stop occurred before simulation.

## Margin transferability

No prior practical margin is approved for transfer. Pool and Session candidates
change estimands; Transfer would studentize without using margins as scales;
Post-Loss changes the contrast space; Combat has no retained statistic.

## BH readiness

**NOT READY.** Marginal p-values are not calibrated for any retained method,
and two family roots are not defined. Fixed `m=5` BH remains only a candidate
architecture.

## Implementation readiness

**`BLOCKED_PENDING_STATISTICAL_METHOD`.** Exact unresolved families: Pool Shape,
Transfer, Post-Loss Response, Combat Expression, and Session Drift.

## Recommended next step

Run one **family-specification redesign phase**: select one public Pool question
and split, demote, or retire Combat's distinct hypotheses before any new null
simulation.

## What must NOT change yet

- production analytical behavior, public contracts, config, or release metadata;
- frozen V6.1 artifacts, estimators, thresholds, or source binding;
- the tuning/holdout split or the revealed holdout;
- practical margins, robustness/stability gates, or BH procedure; and
- frontend, backend runtime, database, infrastructure, or deployment.

## Files created

Tracked:

- `docs/evidence/free-dna-v6.1-family-null-models-2026-08-27.md`
- updated `docs/prompts/v61-findings-recovery-implementation.md`

Local-only under `.local/diagnostics/v61-family-null-models/`:

- `family_null_specifications.json`
- `candidate_methods.json`
- `null_simulation_results.csv`
- `type1_summary.csv`
- `power_results.csv`
- `family_method_verdicts.json`
- `tuning_method_behavior.csv`
- `margin_transferability.csv`
- `aggregate_summary.json`

## Integrity verification

- external collection calls: **0**;
- holdout reruns: **0**;
- frozen artifacts changed: **no**;
- production changed: **no**;
- owner worktree modified: **no**;
- deployment or merge: **none**.
