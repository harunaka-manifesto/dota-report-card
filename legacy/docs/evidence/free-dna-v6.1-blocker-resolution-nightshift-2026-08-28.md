# V6.1 Blocker Resolution Nightshift

## Status

**PARTIAL — Transfer and Post-Loss are ready for implementation specifications,
Session Drift requires more tuning data under its frozen contract, and Presence
& Exposure requires an owner product decision before its public question can
change.**

## Integrity

```text
TASK TYPE: ANALYTICAL + DOCUMENTATION, research-only
ALLOWED SCOPE: 791 TUNING_ELIGIBLE profiles, synthetic known-truth simulations, local-only diagnostics, research scripts, analytical evidence
FORBIDDEN SCOPE: protected/revealed holdout, providers, production estimators/thresholds/artifacts, public contract changes, database/Redis/config, integration, deployment
STOP CONDITIONS: holdout/provider access; lowered frozen minimum; yield-selected rule; silent family redefinition; production edit; ambiguous analytical base
ANALYTICAL BASE SHA: 44bba6dc44f605916cb113da6feaa10ebe63e0b1
LATEST MAIN SHA: 6d088f76e3c0ca39a3649a6c80ee2cfb1db93d95
ACTIVE OWNER WORKTREE STATUS: codex/v61-case-notes at c4df42df12f7b14bad0cdbc2e32c7bb632ff81f5 with unrelated untracked docs/evidence, docs/prompts, and research/stratz-enrichment
RESEARCH WORKTREE: /tmp/dota-report-card-v61-blocker-resolution-nightshift on research/v61-blocker-resolution-nightshift
```

The runner used the frozen 791-profile train partition only. It opened no
holdout output and made no provider call. A process-level offline guard made
network access fail closed. All profile-level output is pseudonymous and local.

| binding | value |
| --- | --- |
| corpus SHA-256 | `5b80bd29d6ecd04c92e4ba37051b7a71f23775007614b9f6a110d9efa2090216` |
| split SHA-256 | `2aa3b4292c0a24d9ca209c5f885ebd1590e3032323362f111befae678d816231` |
| train profile digest | `2d961edcde679a529751c78b9129cf6d8cf0e56d32d17a226a12dd24a0c09461` |
| analytical source | `7df38e6d234ae9c4ee425490bc40b8cc92685f85` |
| frozen artifact package | `8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0` |

## Starting state

The prior pass calibrated Transfer at `0.4115` from 462 margin profiles and
Post-Loss at `0.3889` from 517. Presence & Exposure calibrated mechanically at
`0.2072` but 617/629 supported profiles shared the inverse direction. Session
Drift supplied only 62 valid margin observations against the registered minimum
of 100. BY with fixed `m=4`, `q=.05` passed the prior bounded stress grid.

No prior stop was treated as a target to optimize around. Practical margins,
support gates, the revealed holdout, and production behavior remained frozen.

## Repository lineage

The analytical and main histories diverge at
`2ce777b84bd936a416dfdc7e8cac5d758c04ae57`. The analytical-only chain is:

```text
3d0e65c suppression autopsy
55d4f2f statistical recovery specification
c28c5bc statistical hardening stop
f1e5961 family null-model stop
fc3a728 Pool + Combat redesign
31a48b0 four-family inference validation
44bba6d margin/stability/multiplicity calibration
```

Main-only commits are `e523d85`, `9853aaf`, `b406e36`, and merge `6d088f7`.
The only path changed on both sides is
`docs/evidence/free-dna-v6.1-suppression-autopsy-2026-08-27-complete.md`, and its
bytes are identical at both heads. Integration therefore appears conceptually
clean, but this task did not merge, rebase, or cherry-pick.

## Session Drift scarcity forensic

### Attrition funnel

| stage | profiles | share of 791 |
| --- | ---: | ---: |
| total / structurally eligible | 791 | 100.0% |
| at least 12 boundary-safe completed sessions | 776 | 98.1% |
| basic early/late support | 481 | 60.8% |
| valid non-tie family estimate under the full contract | 63 | 8.0% |
| valid odd/interleaved half | 63 | 8.0% |
| valid even/interleaved half | 62 | 7.8% |
| finite paired margin statistic | 62 | 7.8% |

The exclusive first-reason distribution is: 15 with fewer than 12
boundary-safe completed sessions; 295 with fewer than 12 sessions of at least
four matches; 412 below 50% qualifying-session coverage; 6 with fewer than 12
informative non-tie effects; 1 with fewer than six informative odd sessions;
and 62 margin-eligible.

Median profile history contains 108 sessions, but the median session contains
only 2 matches. The median profile has 18 sessions of at least four matches,
11 informative non-tie effects, and only 19.4% qualifying-session coverage.
Even P90 qualifying coverage is 49.6%, just below the frozen 50% requirement.
Dominant-hero exclusion is not the source of margin attrition; the scarcity is
already present at the completed-long-session and coverage stages.

### Root cause

`62` is the expected consequence of the frozen family question and the observed
tuning distribution. Most profiles have many sessions, but too few sessions
long enough to support a boundary-safe early/late comparison. The odd/even
calculation loses only one of the 63 inferentially supported profiles. It is not
the primary bottleneck, and there is no implementation defect in that count.

At the observed 7.8% margin-eligible rate, roughly 1,276 similarly distributed
tuning profiles would be needed in expectation to reach 100 observations. That
is an extrapolation, not authorization to collect or to assume the yield will
remain constant.

### Alternative margin methods

Four methods were specified before evaluating their usable counts:

| method | noise target | observed usable | comparable to current margin? |
| --- | --- | ---: | --- |
| alternating complete-session halves | balanced cluster-preserving repeatability | 62 | yes; existing method |
| chronological complete-session halves | repeatability plus temporal drift | 63 | broadly, but adds chronology |
| leave-one-session-out | single-session influence | 63 | no; materially smaller scale |
| paired session bootstrap | conditional sampling uncertainty | 63 | no; different noise target |

All retain the frozen structural contract. None produces the required 100
profiles. LOSO and bootstrap estimates are not interchangeable with half-sample
repeatability, so their smaller numeric noise cannot be used as a replacement
margin.

### Validation

Known-truth stable, moderate, and sign-balanced scenarios verified that stable
and noisy profiles behave in the expected order. The chronological split is
not downward-biased relative to the existing split in the synthetic screen,
but it adds genuine chronology to measurement error. LOSO and paired bootstrap
often have smaller scales precisely because they estimate different objects.
No alternative is both comparable and capable of resolving the sample-size
stop.

### Verdict

`SESSION_REQUIRES_MORE_TUNING_DATA`.

For the V6.1 product path, defer Session Drift from the registered Finding
universe. Do not lower the 100-profile margin minimum, the four-match session
minimum, the 50% coverage gate, or the 12 non-tie-session requirement.

## Presence & Exposure common-direction autopsy

### Formula audit

The exact raw rates are `(kills + assists) / minutes` and `deaths / ten
minutes`. The retained estimator applies the existing context baselines, then
fits a centered least-squares slope inside each session and tests the prevalence
of session-slope signs. Both rates share match duration. They also remain
dependent on result/match state, hero/function, role, draft, opponent, and team
tempo. The frozen summary corpus has no credible team-tempo field.

A common duration denominator creates mathematical coupling, but does not by
itself explain an almost universal inverse direction. Context adjustment also
does not address the relevant unobserved match-state variables.

### Direction decomposition

All four diagnostic formulas produced the same direction counts:

| x | y | supported | inverse | positive | tied | inverse share |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| raw involvement | raw death exposure | 629 | 617 | 9 | 3 | 98.1% |
| adjusted involvement | raw death exposure | 629 | 617 | 9 | 3 | 98.1% |
| raw involvement | adjusted death exposure | 629 | 617 | 9 | 3 | 98.1% |
| adjusted involvement | adjusted death exposure | 629 | 617 | 9 | 3 | 98.1% |

The median supported profile theta is `-0.48`. The common sign is therefore
not created or removed by the current baseline adjustments.

### Outcome/confounder diagnostics

Restricting the calculation within result strata materially attenuates the
common direction: wins are inverse for 244/390 supported profiles (62.6%);
losses are inverse for 260/384 (67.7%). This is not a causal decomposition and
the supported subsets differ, but it strongly supports the outcome/match-state
proxy hypothesis.

The inverse link otherwise remains broad:

| diagnostic | supported | inverse share |
| --- | ---: | ---: |
| dominant hero excluded | 558 | 96.4% |
| within dominant hero | 84 | 95.2% |
| dominant hero function | 177 | 94.4% |
| other hero functions | 512 | 96.9% |
| shorter-duration matches | 388 | 97.2% |
| longer-duration matches | 367 | 84.2% |
| shorter sessions | 547 | 98.0% |
| longer sessions | 354 | 97.7% |
| early chronology | 481 | 97.5% |
| late chronology | 486 | 98.1% |

The direction is not explained by one dominant hero, one mapped function,
chronology, or session length. Duration changes its strength but not the core
diagnosis. Team tempo could not be tested because the input is absent; no proxy
was fabricated.

### Hero dependence

Both within-dominant-hero and dominant-hero-excluded analyses remain above 95%
inverse. The family is not merely measuring dominant-hero choice. Sparse role
hints are insufficient for role-stratified causal claims, and mapped hero
functions are editorial taxonomy rather than observed role.

### Population-common relationship

The pooled within-profile-session adjusted slope is `-1.2984`. Subtracting this
common slope from every session slope yields 629 supported residual profile
thetas: 233 positive, 360 negative, and 36 tied, with median `-0.0476`.
Meaningful personal variation therefore exists around the population-common
relationship, but it answers a different question.

```text
OWNER_PRODUCT_DECISION_REQUIRED

CURRENT QUESTION:
When your scoreboard involvement rises, what happens to your death exposure?

EVIDENCE PROBLEM:
The sign is population-common (98.1%) and materially attenuates within result
strata, so publishing the sign as personal risks repackaging match state.

PROPOSED QUESTION:
How much more or less strongly than the tuning population does your involvement
move with death exposure?

WHY IT IS MORE PERSONAL:
Residual directions are distributed across players instead of nearly universal.

WHAT CHANGES ANALYTICALLY:
Register and validate a population-baseline residual estimand, its uncertainty,
margin, stability, multiplicity, provenance, and fresh validation.

WHAT CHANGES ONSTAGE:
Copy must compare the player's coupling with a bounded population baseline; it
cannot present the raw inverse sign as the player's distinctive pattern.
```

### Personalization verdict

`PRESENCE_EXPOSURE_REQUIRES_POPULATION_BASELINE_REDEFINITION`.

Do not implement or validate the redefinition without owner approval. If the
public question is not changed, defer or demote this family.

## Transfer hardening

### Margin

The registered theta margin `0.4115` reproduces from 462 usable profiles. A
1,000-resample tuning bootstrap places the margin median at `0.4025` and its
95% diagnostic interval at `[0.3809, 0.4442]`, containing the registered value.
The margin is half the P90 maximum odd/even component disagreement on the
bounded signed-prevalence scale; it is not a causal or skill threshold.

### Stability

484 profiles are structurally supported. Component support is 417 outcome,
484 activity, and 484 survival; selected components are 98 outcome, 179
activity, and 207 survival. Forty-nine pass fixed-four-family BY, 326 survive
dominant-hero exclusion, and 20 pass every current mechanical gate.

The predeclared `0.8× / 1.0× / 1.2×` margin sensitivity yields 33 / 20 / 13
mechanical candidates. Those counts describe sensitivity only and did not
select the registered margin. The margin bootstrap and component balance show
no method-level revisit trigger.

### Limitations

- Fixed cross-fitted core/stretch bands remain observational hero-choice
  contexts, not randomized treatment.
- Outcome support is lower than activity/survival support.
- Dominant-hero exclusion does not remove role, draft, opponent, or match-state
  confounding.
- Fresh sealed validation remains required after a candidate is implemented
  and frozen.

### Verdict

`TRANSFER_READY_FOR_IMPLEMENTATION_SPEC`.

Implementation-ready analytical contract: retain three fixed session effects
(stretch minus core for outcome, adjusted activity, and survival-oriented
negative death exposure); require 12 paired sessions, 30 complete matches per
band, 80% context coverage, fixed band assignment, 2,000-draw sign
randomization with add-one p-values, fixed three-component Bonferroni, theta
margin `0.4114976780185762`, both six-session halves matching full direction,
LOO agreement at least 80%, dominant-hero direction/support survival, and the
registered external correction. Unsupported components remain `p=1`. Claims
must not imply hero-choice causality, skill, or mastery.

## Post-Loss hardening

### Margin

The registered theta margin `0.3889` reproduces from 517 profiles. Its
1,000-resample diagnostic median is `0.3889` with 95% interval
`[0.3722, 0.4167]`. The registered value is stable under reasonable tuning
resampling.

### State support

537 profiles support at least one fixed contrast. Component support is 531
one-loss-vs-win, 297 two-plus-losses-vs-win, and 407 win-streak-vs-win; selected
contrasts are 300, 99, and 138 respectively. Sparse two-plus-loss states are
the main balance limitation. Unsupported fixed slots remain `p=1`; missing
states never shrink the internal multiplicity denominator.

Ten profiles pass fixed-four-family BY, 342 survive dominant-hero exclusion,
and 4 pass every mechanical gate. The `0.8× / 1.0× / 1.2×` margin sensitivity
gives 8 / 4 / 3 candidates and did not select the margin. Session effects use
equal-session weighting, same-session chronology, and no cross-session
transitions, which prevents long sessions from becoming independent evidence.

### Limitations

Current V6/V6.1 evidence uses the sparse same-session result-state matcher.
Future STRATZ role+patch inputs may improve matching in V7, but they are not
part of this contract and were not used here. The observational state remains
subject to selection and match-state confounding; no psychology, tilt, intent,
or causality claim is allowed.

### Verdict

`POSTLOSS_READY_FOR_IMPLEMENTATION_SPEC`.

Implementation-ready analytical contract: retain the three fixed state
contrasts against `win`; require 12 informative paired sessions, 30
transitions across each compared pair, 80% required coverage, same-session
chronology only, 2,000-draw sign randomization with add-one p-values, fixed
three-contrast Bonferroni, theta margin `0.38888888888888884`, both six-session
halves matching full direction, LOO agreement at least 80%, dominant-hero
direction/support survival, and the registered external correction.

## Multiplicity audit

The exact prior 10,000-dataset-per-cell grid contains complete null and mixed
truth scenarios at latent correlations `-0.25`, `0`, `0.5`, and `0.9`. BH
passed every bounded cell with worst estimated FDR `0.0322`; BY passed every
cell with worst estimated FDR `0.0148`. The grid does not establish player-data
PRDS, so BH remains diagnostic and BY remains the defensible arbitrary-
dependence correction.

The bounded independent-alternative power diagnostic estimates true-positive
rates of BH/BY at 22.0%/17.0% for `m=4`, 24.5%/19.7% for `m=3`, and
27.8%/24.0% for `m=2`. This quantifies BY's power cost without using tuning
Finding yield.

| registered universe | BY harmonic factor | permitted decision point |
| ---: | ---: | --- |
| 4 | 2.0833 | only if all four questions remain registered before fresh validation |
| 3 | 1.8333 | only after a conceptual family decision, never a tuning-yield dropout |
| 2 | 1.5000 | only after owner approves Transfer + Post-Loss as the complete V6.1 universe |

Verdict: `MULTIPLICITY_CONDITIONAL_PENDING_FINAL_FAMILY_SET`. Use BY, but freeze
and revalidate its denominator only after the owner makes the family-set
decision.

## Tuning-only yield diagnostics

These counts are descriptive and explicitly non-optimizing.

| family | supported | BY significant | practical pass | stability pass | robustness pass | all mechanical gates |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Transfer | 484 | 49 | 80 | 343 | 326 | 20 |
| Post-Loss | 537 | 10 | 69 | 302 | 342 | 4 |
| Presence & Exposure | 629 | 376 | 578 | 549 | 543 | 362 |
| Session Drift | 63 | 3 | 0 | 33 | 28 | 0 |

Presence's unusually broad mechanical yield is a safety warning, not a product
success. Session's sparse result is support-gated. Transfer and Post-Loss are
selective and margin-sensitive but supported by reproducible calibrations.

## Recommended V6.1 family set

| player question | method | margin | personalization | main risk | disposition | next action |
| --- | --- | --- | --- | --- | --- | --- |
| What survives when the hero changes? | validated | calibrated | supported | observational hero/context sensitivity | KEEP | implementation spec + fresh validation |
| How does the next choice move after result states? | validated | calibrated | supported | sparse states and match-state confounding | KEEP | implementation spec + fresh validation |
| When involvement rises, what happens to death exposure? | validated | calibrated but unsafe | population-common sign | outcome/shared-rate confounding | REDESIGN or DEFER | owner semantic decision |
| Within completed sessions, what changes early to late? | validated | insufficient evidence | not assessable | structural long-session scarcity | DEFER | more tuning data under frozen rules |

Recommend a conceptually frozen **two-family Finding universe: Transfer and
Post-Loss Response**. Presence & Exposure and Session Drift remain research-
only. This is a product/family-definition recommendation made before fresh
validation, not a multiplicity or yield workaround.

## Three release/research paths

Scores are 1–5; higher complexity and compatibility risk are worse.

| path | user value | defensibility | time to safe implementation | complexity | compatibility risk | V7 reuse | reversibility | decision |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| four-family recovery now | 5 | 2 | 1 | 5 | 4 | 4 | 2 | reject |
| reduced registered universe | 4 | 5 | 4 | 2 | 2 | 5 | 4 | recommend |
| stage mature families, others research-only | 4 | 5 | 4 | 3 | 2 | 5 | 5 | compatible if versioned |

The recommended path combines the latter two: freeze Transfer + Post-Loss as
the new registered universe and stage them in a new analytical lineage, while
keeping the other families research-only. No current persisted report is
rewritten, and no production behavior changes in this task.

## V7 reuse map

Transfer and Post-Loss family questions, sign-randomization nulls, margin
methodology, split/LOO/robustness gates, publication state machine, and
provenance machinery are provider-agnostic. Presence & Exposure may become
safer with real role, patch, team-tempo, and richer match-state context, but a
population-baseline semantic decision is still required. STRATZ cannot create
more completed long sessions from the existing profiles; Session scarcity is
principally behavioral-history shape, not missing field richness.

## Repository integration plan

```text
ANALYTICAL COMMIT CHAIN: 2ce777b..44bba6d, then this nightshift commit
MAIN-ONLY COMMIT CHAIN: 2ce777b..6d088f7
OVERLAPPING FILES: suppression-autopsy complete evidence only; identical bytes
EXPECTED CONFLICTS: none demonstrated; re-check at integration time
SAFE CHERRY-PICK ORDER: analytical chain in chronological order, then nightshift
DOCS THAT MUST LAND: this evidence and the single next-blocker prompt
RESEARCH SCRIPTS THAT SHOULD / SHOULD NOT LAND: land the runner; never land .local outputs
LOCAL-ONLY ARTIFACTS TO PRESERVE: .local/diagnostics/v61-blocker-resolution-nightshift/
TEMP WORKTREE CLEANUP: remove after validated commit
```

No integration was performed and no unique analytical branch was deleted.

## Recommended next action

Owner approval is required for the two-family V6.1 universe and for deferring
the raw Presence & Exposure question. After approval, write the final
implementation specification with BY `m=2`, implement the research candidate,
repeat method/parity/calibration checks, freeze new candidate artifacts, and
only then predeclare a fresh sealed validation. Do not touch the revealed
holdout.

## What must NOT change yet

- Production estimators, thresholds, family IDs, semantic outcomes, copy,
  report contracts, flags, database, Redis, infrastructure, or deployment.
- Frozen V6.1 source binding or artifact package.
- The current tuning/holdout split or any revealed holdout output.
- Presence & Exposure semantics without owner approval.
- Session support or margin minimums.
- The external multiplicity denominator before the family universe is frozen.

## Files created

Tracked:

- `scripts/v61_blocker_resolution_nightshift.py`
- `docs/evidence/free-dna-v6.1-blocker-resolution-nightshift-2026-08-28.md`
- `docs/prompts/v61-findings-next-blocker-resolution.md`

Local-only under `.local/diagnostics/v61-blocker-resolution-nightshift/`:

- `session_attrition_funnel.csv`
- `session_margin_method_candidates.json`
- `session_margin_validation.csv`
- `presence_exposure_formula_audit.md`
- `presence_exposure_direction_decomposition.csv`
- `presence_exposure_confounder_diagnostics.csv`
- `presence_exposure_population_slope.json`
- `transfer_hardening.csv`
- `postloss_hardening.csv`
- `multiplicity_audit.csv`
- `finding_yield_diagnostics.csv`
- `family_decision_matrix.json`
- `v61_path_comparison.json`
- `v7_reuse_map.json`
- `repo_integration_plan.md`
- `aggregate_summary.json`

## Integrity verification

- HOLDOUT PROFILES TOUCHED = **0**
- EXTERNAL PROVIDER CALLS = **0**
- PRODUCTION ANALYTICAL CHANGES = **0**
- FROZEN ARTIFACTS CHANGED = **0**
- DEPLOYMENTS = **0**
- OWNER WORKTREE TRACKED FILES MODIFIED = **0**
- PUBLIC FAMILY QUESTION CHANGED = **NO**
- PUBLICATION YIELD USED TO SELECT A METHOD OR MARGIN = **NO**
