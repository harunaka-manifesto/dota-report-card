# V6.1 Findings Statistical Hardening

## Status

**PARTIAL — the proposed inference method is rejected; implementation is
blocked pending a new family-specific statistical method.**

## Integrity

| item | value |
| --- | --- |
| base SHA | `55d4f2f7d3ed1d3cde462a2cf32f84ee06067fba` |
| branch | `research/v61-findings-statistical-hardening` |
| origin/main observed at start | `e523d855e307f1e0202377b5269142c0e009b65a` |
| task type | ANALYTICAL + DOCUMENTATION, research-only |
| external collection calls | 0 |
| holdout reruns | 0 |
| production changes | 0 |

The work ran in an isolated worktree based on the completed recovery commit.
The later `origin/main` is a sibling line and was not merged, rebased, reset, or
modified.

## Inputs consumed

- the completed statistical recovery evidence and downstream draft;
- the completed suppression autopsy;
- the statistics, evidence-contract, calibration, feature-graph, release-gate,
  production-safety, and analytical-release-invariant documents;
- synthetic known-truth session-cluster data only.

No corpus, protected holdout, provider, production database, Redis instance,
or frozen runtime artifact was opened by the simulation command.

## What remained unresolved from the recovery spec

The recovery proposal treated
`abs(draw - point) >= abs(point - null)` as a common scalar bootstrap test for
both signed scalar and selected maximum statistics. It had not shown that
centering a selected maximum preserves the joint component null, had only 80
Monte Carlo repetitions at 250 draws, carried forward practical margins across
changed estimands, and did not supply executable robustness gates.

## Null-centered bootstrap validity

The proposed construction is rejected for every family.

For a signed scalar, the nonparametric cluster bootstrap approximates the
sampling distribution around the empirical distribution, not an exact null
pivot. Basic centering is only asymptotically defensible under regularity and
was anti-conservative with the tested cluster counts, skew, unequal cluster
sizes, low support, and heteroskedasticity. Studentization or another validated
null-imposed pivot is required.

For a maximum, the defect is structural. If component estimates are
`T=(T1,...,Tk)`, the family null concerns their joint distribution. Computing
`M*=max(T*)` and then centering only `M* - M` does not equal recomputing
`max(T* - T)` under the joint null. Selection and dependence are lost after the
maximum is taken. This produced severe Type-I inflation.

The vector-level null-recomputation screen was materially better for Gaussian
max statistics (alpha 0.059–0.062), but it is diagnostic only. It was not
studentized, did not validate each exact nonlinear family estimand, and did not
pass all scalar/scenario cells. It is a next-method candidate, not a final
method.

## Full Type-I error simulation

Configuration: seed `20260827`; 1,000 repetitions per null scenario; exactly
2,000 session-cluster bootstrap draws per repetition; Wilson 95% Monte Carlo
intervals. A cell passed only when estimated alpha was at most 0.065 and the
interval's lower bound did not exceed 0.05. This tolerance separates Monte
Carlo noise from material inflation; it does not redefine nominal alpha.

| family | statistic class | Gaussian alpha (95% MC CI) | worst alpha | worst scenario | verdict |
| --- | --- | --- | --- | --- | --- |
| Pool Shape | signed scalar | 0.077 (0.062–0.095) | 0.120 | low sessions | FAIL |
| Transfer | max absolute, 3 components | 0.245 (0.219–0.273) | 0.311 | low sessions | FAIL |
| Post-Loss Response | max range, 4 states | 0.272 (0.245–0.300) | 0.304 | low opportunity | FAIL |
| Combat Expression | max absolute, 3 components | 0.245 (0.219–0.273) | 0.311 | low sessions | FAIL |
| Session Drift | max range, 5 positions | 0.321 (0.293–0.351) | 0.360 | low sessions | FAIL |

The complete 168-cell result, including exact-zero, skewed, heavy-tailed,
clustered, unequal-size, low/high-session, low/high-opportunity,
autocorrelated, heteroskedastic, dominant-session, and missing-draw scenarios,
is local in `type1_error_simulation.csv`. The proposed method failed 57 cells.
These family mappings test the proposed scalar/max statistic classes. They do
not claim to validate the still-unfrozen nonlinear family estimands; the shared
method already failed before that later validation could begin.

## Power/sensitivity simulation

**NOT RUN — STOP CONDITION.** Type-I error remained materially above nominal.
Power under a rejected null procedure would not establish implementation
readiness and could encourage selection of an invalid test.

## Family-specific method verdicts

| family | proposed test valid? | verdict | required next method work |
| --- | --- | --- | --- |
| Pool Shape | NO | MODIFY/REPLACE | Validate a studentized scalar or other null-imposed test on the exact JSD contrast. |
| Transfer | NO | REPLACE | Preserve the three-component vector and use a jointly null-imposed max pivot. |
| Post-Loss Response | NO | REPLACE | Freeze supported state contrasts before testing and use a joint max-contrast pivot. |
| Combat Expression | NO | REPLACE | First define the exact components, scales, and null; then validate a joint omnibus pivot. |
| Session Drift | NO | REPLACE | Freeze supported positions independently of outcomes and validate a joint position-contrast pivot with censoring qualification. |

## Practical-effect margin re-derivation

**NOT RUN — STOP CONDITION.** The old margins are not approved for the changed
estimands. Margin derivation must follow, not precede, a valid frozen estimator
and pivot. No margin was selected from publication yield.

## Stability gate specification

**NOT RUN — STOP CONDITION.** Split-half, leave-one-session-out, sign agreement,
dominant-session, and minimum-successful-replicate thresholds remain unresolved
and must not be implemented from the recovery draft.

## Confounder/robustness gate specification

**NOT RUN — STOP CONDITION.** No executable `CONFOUNDED` boolean is approved.
The next method pass must separate hard publication gates from limitation-only
and diagnostic-only checks for each family.

## BH dependency/multiplicity check

**NOT RUN — STOP CONDITION.** Fixed five-family BH at nominal `q=.05` remains
the architectural candidate, and branch labels remain interpretation-only, but
BH cannot be validated with anti-conservative family p-values. No switch to BY
or another correction is recommended before valid marginal p-values exist.

## Tuning-corpus hardened results

**NOT RUN — STOP CONDITION.** The 791-profile tuning partition was not loaded.
Running it under a rejected method would create misleading p/q values and
descriptive yield.

## Final analytical architecture

No final architecture is approved. Retain five family roots, one family-level
discovery per root, no correction for deterministic interpretation labels,
and a post-qualification cap of three as design constraints only. Replace the
common scalar-centering helper with exact family-specific, jointly null-imposed
pivots; freeze estimands, support selection, studentization, invalid-draw rules,
and stability/robustness gates before repeating this hardening sequence.

## Implementation readiness

**NOT READY — `BLOCKED_PENDING_STATISTICAL_METHOD`.** The downstream prompt is
marked accordingly and its numeric rules are preserved only as a rejected
recovery proposal.

## Fresh validation requirements

After a replacement method passes full Type-I, power, coverage, stability,
confounder, tuning-only margin, and five-p-value dependency checks, freeze the
candidate artifacts and predeclare a new sealed holdout. The revealed 339
profiles cannot validate the replacement. No new holdout should be selected or
run until the full implementation specification contains no statistical choice
for the worker.

## What must NOT change yet

- production analytical behavior, config, flags, or release metadata;
- frozen V6.1 artifacts, thresholds, estimators, or source binding;
- the protected/revealed holdout or tuning/holdout membership;
- public report contracts, database, Redis, frontend, or deployment;
- fixed BH or practical margins based on this failed method; and
- provider collection or the 365-day production request contract.

## Files created

Tracked:

- `scripts/v61_findings_statistical_hardening.py`
- `docs/evidence/free-dna-v6.1-findings-statistical-hardening-2026-08-27.md`
- updated `docs/prompts/v61-findings-recovery-implementation.md`

Local-only, mode `0600`, under
`.local/diagnostics/v61-findings-statistical-hardening/`:

- `method_validity_summary.json`
- `type1_error_simulation.csv`
- `power_simulation.csv`
- `family_method_verdicts.json`
- `margin_rederivation.csv`
- `stability_gate_spec.json`
- `confounder_gate_spec.json`
- `bh_dependency_check.csv`
- `tuning_hardened_results.csv`
- `aggregate_summary.json`

## Integrity verification

- external collection calls: **0**;
- holdout reruns: **0**;
- frozen artifacts changed: **no**;
- production changed: **no**;
- owner worktree modified: **no**;
- deployment or merge: **none**.
