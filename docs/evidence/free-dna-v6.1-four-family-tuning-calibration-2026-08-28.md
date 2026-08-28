# V6.1 Four-Family Tuning Calibration

## Status

**PARTIAL — Transfer and Post-Loss calibrated with limitations; Session Drift
and Presence & Exposure remain blocked.** The next status is
`BLOCKED_PENDING_SESSION_MARGIN_AND_PRESENCE_CONFOUNDER_REVIEW`. Production
implementation and fresh holdout selection are not authorized.

## Integrity

| item | value |
| --- | --- |
| task type | ANALYTICAL RESEARCH + CALIBRATION + DOCUMENTATION |
| base SHA | `31a48b0b0b2ab524126b8ebfed9e76f6d47b020f` |
| branch | `research/v61-margin-stability-multiplicity` |
| origin/main observed at start | `6d088f76e3c0ca39a3649a6c80ee2cfb1db93d95` |
| external collection calls | 0 |
| tuning profiles evaluated | 791 |
| holdout profiles evaluated | 0 |
| holdout outputs loaded | no |
| frozen artifacts changed | 0 |
| production changes | 0 |

The pass ran from the prior analytical commit rather than rebasing onto the
concurrent UI merge on `main`. It did not touch the owner's staged presentation
work.

## Bound inputs

| input | binding |
| --- | --- |
| replacement canonical corpus | `5b80bd29d6ecd04c92e4ba37051b7a71f23775007614b9f6a110d9efa2090216` |
| frozen split manifest | `2aa3b4292c0a24d9ca209c5f885ebd1590e3032323362f111befae678d816231` |
| train profile digest | `2d961edcde679a529751c78b9129cf6d8cf0e56d32d17a226a12dd24a0c09461` |
| train / excluded holdout | 791 / 339 |
| analytical source binding | `7df38e6d234ae9c4ee425490bc40b8cc92685f85` |
| frozen artifact package | `8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0` |

The corpus loader validated the full bound corpus and split, then the evaluator
constructed analytical rows only for the 791 frozen train profiles. It did not
open either revealed holdout evaluation output.

## Rules frozen before tuning outcomes

The candidate method remains session signed-prevalence randomization from the
four-family inference design.

### Practical margin

For every supported profile and family:

1. divide independent sessions into chronological odd and even halves;
2. compute each fixed component's signed-prevalence estimate in both halves;
3. retain the maximum absolute component disagreement for that profile; and
4. set the family margin to half the P90 disagreement.

At least 100 usable profile-level disagreements were required. Publication
yield was not an input.

### Stability and robustness

A profile-level candidate requires:

- at least six informative sessions in each odd/even half;
- both half-estimate directions to match the full selected-component direction;
- at least 80% leave-one-session-out direction agreement; and
- support and direction to survive exclusion of the profile's most-used hero.

Dominant-hero exclusion is a bounded robustness screen, not proof that hero,
role, draft, opponent, team tempo, or match state has been controlled.

### Multiplicity

The candidate family universe is fixed at four. Pool has no family test.
Unsupported families remain present at `p=1`.

The selected correction is Benjamini–Yekutieli at `q=.05`, `m=4`. BY was
chosen before tuning outcomes because it controls FDR under arbitrary
dependence. Ordinary BH was retained only as a diagnostic comparator.

## Calibration results

Counts labeled “qualified” are tuning-only mechanical diagnostics before the
post-run safety review. They are not publication estimates or product targets.

| family | supported | margin observations | theta margin | split pass | LOO pass | dominant-hero pass | BY q≤.05 | mechanically qualified | verdict |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Transfer | 484 | 462 | 0.4115 | 343 | 476 | 326 | 49 | 20 | `CALIBRATED_WITH_LIMITATIONS` |
| Post-Loss Response | 537 | 517 | 0.3889 | 302 | 510 | 342 | 10 | 4 | `CALIBRATED_WITH_LIMITATIONS` |
| Presence & Exposure | 629 | 593 | 0.2072 | 549 | 621 | 543 | 376 | 362 | `BLOCKED_COMMON_DIRECTION_CONFOUNDER_REVIEW` |
| Session Drift | 63 | 62 | not derived | 33 | 55 | 28 | 3 | 0 | `BLOCKED_INSUFFICIENT_MARGIN_EVIDENCE` |

The margins are large because they estimate repeatability noise on a bounded
`[-1, 1]` signed-prevalence scale. They are new research values and do not
modify any checked-in runtime artifact.

## Session Drift stop

Session Drift produced only 62 usable odd/even margin observations, below the
predeclared minimum of 100. The strict contract requires boundary-safe completed
sessions, at least four matches per session, at least 50% qualifying-session
coverage, and at least 12 informative non-tie session effects. Although 394
profiles had at least 12 nonzero early/late result effects, only 63 passed the
complete structural contract.

The pass did not lower the 50% coverage rule, reduce the margin sample minimum,
reuse tied sessions as neutral signs, or substitute activity/exposure for the
frozen result-only construct. Any of those would be a post-outcome method
change and would require a new registered design plus Type-I revalidation.

## Presence & Exposure stop

Among 629 supported profiles, 617 were inverse, 9 positive, and 3 tied. The
dominant direction therefore covered 98.1% of supported profiles. After the
predeclared margin, stability, robustness, and BY gates, 362 profiles still
mechanically qualified.

This concentration was not used to change the margin. Instead, a conservative
post-run safety stop was added: a direction present in at least 90% of supported
profiles requires explicit confounder and product review. The stop can only
prevent approval; it cannot increase yield.

The observed inverse link may reflect a population-common result or match-state
relationship—winning/team-tempo contexts can simultaneously increase credited
involvement and reduce death exposure—rather than a distinctive personal
pattern. Current summary-only inputs cannot observe fight participation,
positioning, detailed role, draft state, objectives, or within-match state.
Dominant-hero exclusion does not resolve that problem.

Presence & Exposure must therefore be redesigned with a credible negative
control or richer conditioning, or deferred/demoted. It must not enter a fresh
holdout as currently specified.

## Dependency and multiplicity evidence

On profiles where both families were supported, pairwise raw-p correlations
were modest:

| pair | paired profiles | Pearson | Spearman |
| --- | ---: | ---: | ---: |
| Transfer / Post-Loss | 462 | 0.079 | 0.105 |
| Transfer / Presence | 482 | 0.073 | 0.164 |
| Transfer / Session | 59 | -0.093 | -0.049 |
| Post-Loss / Presence | 537 | 0.036 | 0.197 |
| Post-Loss / Session | 63 | 0.028 | 0.050 |
| Presence / Session | 63 | 0.225 | 0.205 |

Empirical correlations cannot prove the dependence conditions required by BH.
The BY selection therefore rests on its arbitrary-dependence guarantee, not
these estimates.

The 10,000-dataset-per-cell stress grid covered global null and one-moderate-
alternative settings at latent correlations `-0.25`, `0`, `0.50`, and `0.90`.
All BY cells passed the predeclared estimated-FDR limit of 0.055. BY's worst
estimated FDR was 0.0148. BH also passed this bounded synthetic grid but remains
diagnostic-only because the grid does not establish player-data PRDS.

## Decision

| item | decision |
| --- | --- |
| Transfer | `CALIBRATED_WITH_LIMITATIONS` |
| Post-Loss Response | `CALIBRATED_WITH_LIMITATIONS` |
| Presence & Exposure | `BLOCKED_COMMON_DIRECTION_CONFOUNDER_REVIEW` |
| Session Drift | `BLOCKED_INSUFFICIENT_MARGIN_EVIDENCE` |
| four-family correction | candidate BY, fixed `m=4`, `q=.05`; simulation pass |
| fresh holdout selection | `NOT AUTHORIZED` |
| candidate implementation | `BLOCKED` |
| next status | `BLOCKED_PENDING_SESSION_MARGIN_AND_PRESENCE_CONFOUNDER_REVIEW` |

The next analytical decision is product-level, not parameter tuning:

1. redesign, defer, or demote Presence & Exposure after a confounder/negative-
   control review; and
2. retain the Session Drift contract and obtain adequate authorized evidence,
   or register a new construct and rerun method validation from Type-I onward.

## Local machine-readable evidence

The complete private record is under
`.local/diagnostics/v61-four-family-tuning-calibration/`:

- `predeclared_rules.json`
- `provenance.json`
- `profile_family_results.jsonl`
- `margin_derivation.csv`
- `stability_robustness_summary.csv`
- `multiplicity_dependency.csv`
- `multiplicity_simulation.csv`
- `tuning_behavior.csv`
- `family_verdicts.json`
- `aggregate_summary.json`

Profile output uses a second research-only digest. No raw profile ID, match ID,
account ID, Steam ID, or holdout result is written.

## What must not change yet

- production family IDs, estimators, thresholds, semantic outcomes, copy,
  Elements, or report contracts;
- frozen V6.1 source binding or runtime artifacts;
- tuning/holdout membership or any revealed holdout output;
- the three-Finding display cap; and
- provider collection, deployment, flags, database, Redis, or infrastructure.
