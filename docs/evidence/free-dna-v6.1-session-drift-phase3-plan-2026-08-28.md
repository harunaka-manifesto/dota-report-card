# V6.1 Session Drift Recovery — Phase 3 Plan

## Status

**PASS — a fixed tuning-only second wave can reach a 110-observation target
without adaptive stopping, validation reuse, or methodology changes. Owner
approval is required before the planned provider calls.**

## Integrity

```text
TASK TYPE: ANALYTICAL + DOCUMENTATION
ALLOWED SCOPE: offline Phase-2 evidence review, predictive planning, fixed-frame design, Luna execution prompt
FORBIDDEN SCOPE: providers, old revealed holdout, sealed-validation analytics, production behavior, methodology changes, deployment
PLANNING BASE: c34f1a272005dda954af0932f7719a4cc230a23d
ANALYTICAL SOURCE: 7df38e6d234ae9c4ee425490bc40b8cc92685f85
FROZEN ARTIFACT DIGEST: 8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0
PROVIDER CALLS: 0
OLD REVEALED HOLDOUT EVALUATED: 0
FRESH SEALED VALIDATION ANALYTICALLY EVALUATED: 0
PRODUCTION ANALYTICAL BEHAVIOR CHANGED: NO
```

The local Phase-2 corpus, diagnostics, request ledger, raw/normalized
manifests, split status, support report, and continuity audit were present and
reconciled. No raw account identifier is included in tracked evidence.

## Starting state

Phase 2 completed its fixed 4,135-candidate frame with 5,346 counted physical
requests, two separate canceled/no-response markers, zero retries, and 323.43
MiB retained storage. The tuning set contains 791 original profiles, 40 local
reserves, and the first 769 canonically eligible Phase-2 external profiles.

Session Drift has 99 legitimate margin observations: 62 original, 2 local
reserve, and 35 external. The frozen minimum remains 100. The frozen P90/2
margin was correctly not derived, hardening and fixed-m=3 multiplicity were not
run, and the fresh validation cohort remains analytically sealed.

## Why Phase 2 landed at 99

The planning shorthand `37 / 769` is not a valid rate. Its numerator combines
35 observations from 769 selected external profiles with 2 observations from
40 local reserves, while its denominator omits those 40 reserves.

The exact rates are:

| population | observations | eligible profiles | rate | Wilson 95% |
| --- | ---: | ---: | ---: | --- |
| original tuning | 62 | 791 | 7.84% | 6.16%–9.92% |
| Phase-2 external selected | 35 | 769 | 4.55% | 3.29%–6.26% |
| local reserve | 2 | 40 | 5.00% | 1.38%–16.50% |
| complete Phase-2 extension | 37 | 809 | 4.57% | 3.34%–6.24% |
| pooled tuning | 99 | 1,600 | 6.19% | 5.11%–7.48% |

Phase 1 forecast from the original 7.84% rate. The directly comparable new
external campaign realized 4.55%, so 809 extension profiles produced 37 rather
than the 38 required to reach 100.

## Old vs new support-rate reconciliation

The old and external observations use the same Session estimator, canonical
eligibility, sessionization, support, and paired-margin rules. They are not
fully exchangeable: they came from different collection campaigns, windows,
and source frames. A two-sample pooled score check for `62/791` versus
`35/769` gives `z=2.688`, two-sided `p=0.0072`.

Formal continuity still passed every predeclared gate. Natural-log
Jensen–Shannon divergences were 0.0008–0.0075 and every absolute bin-share
difference was below 0.077. Those broad limits do not imply identical support
rates. The external wave had fewer 240+ match histories (48.4% vs 56.0%) and
fewer profiles with median session length 4+ (5.7% vs 9.2%), both aligned with
lower Session support. Phase 3 therefore keeps the campaign indicator and
forecasts from the external rate rather than pooling upward.

## Predictive support model

Four models were compared for reaching 110 from the current 99:

| model | uncertainty | eligible profiles at 95% | at 99% | disposition |
| --- | --- | ---: | ---: | --- |
| pooled plug-in binomial, 99/1,600 | ignored | 271 | 321 | comparator only |
| external plug-in binomial, 35/769 | ignored | 370 | 438 | comparator only |
| pooled Jeffreys beta-binomial, Beta(99.5,1501.5) | included | 279 | 336 | comparator only |
| campaign-specific Jeffreys beta-binomial, Beta(35.5,734.5) | included | 400 | 495 | **selected** |

The selected model has posterior mean support rate 4.61%. Its reported
uncertainty reference is the directly observed external Wilson interval,
3.29%–6.26%. This is conservative without inventing a lower rate and carries
rate uncertainty into the predictive count.

## Target comparison

The table gives the minimum additional eligible tuning profiles under the
selected beta-binomial model.

| final target | additional observations | profiles for ≥95% | expected final | profiles for ≥99% | expected final |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 105 | 6 | 243 | 110.20 | 314 | 113.48 |
| 110 | 11 | 400 | 117.44 | 495 | 121.82 |
| 115 | 16 | 552 | 124.45 | 670 | 129.89 |
| 120 | 21 | 702 | 131.36 | 841 | 137.77 |
| 125 | 26 | 851 | 138.23 | 1,011 | 145.61 |

## Recommended target

Choose a final evidence target of **110 legitimate Session margin
observations**. This is ten above the frozen minimum, avoids another
knife-edge outcome, and keeps the expected final count inside the owner's
preferred 110–120 band.

The minimum 95% design needs 400 eligible profiles. Add seven predeclared
eligible profiles so the support-model probability is 95.57%. Combined with a
99.5% candidate-to-eligibility assurance, the conservative union lower bound
for both gates is 95.09%. Phase 3 therefore selects exactly the first **407**
canonically eligible profiles in its fixed HMAC order. Expected final Session
margin count is 117.76.

## Required eligible-profile expansion

```text
CURRENT LEGITIMATE MARGIN OBSERVATIONS: 99
PHASE-3 ELIGIBLE TUNING PROFILES: 407
FINAL TUNING PROFILES IF ALL GATES PASS: 2,007
TARGET LEGITIMATE MARGIN OBSERVATIONS: 110
EXPECTED FINAL LEGITIMATE MARGIN OBSERVATIONS: 117.76
```

Later eligible profiles in the fixed frame remain unused reserve. They are not
substituted based on Session output.

## Candidate-frame conversion

Phase-2 conversion is:

```text
whole frame: 4,135 candidates
→ 4,134 successfully fetched histories
→ 4,134 eligibility statuses determined
→ 2,354 canonically eligible profiles (permitted metadata)

tuning arm: 2,848 candidates
→ 2,848 successfully fetched histories
→ 2,848 eligibility statuses determined
→ 1,609 canonically eligible profiles
→ first 769 selected for Phase-2 tuning
→ 35 Session margin observations
```

The tuning-arm eligibility rate is 56.50%, Wilson 95% 54.67%–58.31%. The
validation-arm eligibility rate is 57.89%, Wilson 95% 55.17%–60.56%; the arm
difference is not material (`p=0.40`). Candidate planning uses only the lower,
directly comparable tuning-arm Jeffreys posterior `Beta(1609.5,1239.5)`.

Exactly 792 candidate accounts give 99.51% predictive assurance of at least
407 canonically eligible profiles. The 840 extra eligible Phase-2 tuning-arm
profiles are not reused because the owner required every prior frame member to
be excluded from the new acquisition wave.

## Sampling frame

Use the same public-profile target population as Phase 2. Continue strictly
below the minimum Phase-2 seed match ID and perform exactly:

```text
4 descending /publicMatches pages × 100 unique seed matches
400 /matches/{match_id} detail attempts
deduplicate positive public account IDs
exclude the complete prior-candidate union
HMAC-rank remaining candidates
retain exactly 792
```

Generate a new private 32-byte salt. Rank by
`HMAC-SHA256(salt, "v61-session-phase3:" + decimal_account_id)`, bytewise
ascending with decimal account ID as tie-breaker. The four-page discovery
frame is fixed before inspection; fewer than 792 remaining candidates is a
hard failure. No extra page is allowed.

Phase 2 observed 4,423 positive public accounts from 1,200 fixed seed details.
Four hundred new details provide a large discovery buffer relative to the 792
required candidates without changing the population logic.

## Prior-frame exclusion

Before ranking, privately reconstruct and exclude the union of:

- all 4,135 Phase-2 fixed-frame accounts;
- all 4,423 positive accounts seen in the Phase-2 seed-detail capture;
- all original 791 tuning profiles and 40 local reserves;
- the 339 historical revealed holdout profiles;
- the 339 fresh replacement-holdout profiles;
- all 1,287 Phase-2 fresh-validation candidates;
- both canceled/no-response assignments;
- all prior seed match IDs, screened reserves, and earlier research candidate
  pools.

The union is reconstructed from private manifests and raw capture, stored
mode-0600, and represented in tracked evidence only by count and SHA-256
digest. Do not retry either canceled/no-response assignment.

## Validation-extension decision

Permitted sealed metadata says:

```text
existing validation candidates: 1,287
successfully collected: 1,286
eligibility statuses determined: 1,286
canonically eligible: 745
target eligible: 339
analytically evaluated: 0
```

The existing cohort is more than sufficient for its planned one-shot
validation. Phase 3 is **tuning extension only**. Do not create or proportionally
extend a validation arm.

## Cost and storage

Recommended Plan B performs exactly 1,196 physical requests:

- 4 public-match pages;
- 400 seed-match details; and
- 792 summary histories.

At the owner-supplied rate this is Rp2,392 pro rata or Rp2,400 in whole
100-call blocks. Phase-2 area-specific payload sizes imply about 81 MiB added
retained storage after normalized, derived, manifest, and diagnostic overhead.
Use hard ceilings of **1,196 calls, Rp2,400, and 100 MiB**. Expected elapsed
time is about 18 minutes at the measured Phase-2 rate of 67.1 calls/minute.

This is 22.4% of Phase-2 physical request volume and does not approach the
prior wave's scale.

## Pooling contract

If all gates pass, append 407 Phase-3 profiles to the existing 1,600 under
`v61-session-drift-calibration-lineage-1.1.0`. The lineage bump records a new
campaign/corpus append; it does not change the estimator.

Required invariants:

- canonical schema remains `v61-calibration-corpus-2.1.0`;
- normalizer remains `summary-normalization-2.0.0`;
- estimator remains `research-signed-prevalence-calibration-1.0.0`;
- sessionization remains `sessions-5.0.0`;
- the frozen result-only early/late estimator, support rules, P90/2 margin,
  p-value, stability, and robustness rules remain unchanged;
- compare Phase 3 separately with the original 791 and Phase-2 external 769
  on the five fixed descriptor bins;
- require natural-log JS ≤0.10 and every absolute share difference ≤0.15 in
  both comparisons;
- retain `campaign_id`/`source_arm` for diagnostics;
- use no weighting and no selective exclusion beyond canonical eligibility
  and the first-407 HMAC order.

## Fixed no-optional-stopping rule

> **Collect/process the entire fixed Phase 3 frame even if Session observation #100, #110, or the target is reached early. Do not stop because the target has been reached. Do not top up if the target is missed.**

## Phase-3 gates

1. Operational integrity: complete the fixed 4-page, 400-detail, 792-history
   frame within 1,196 requests, Rp2,400, and 100 MiB.
2. Provenance: reconcile exclusion, frame, request, raw, normalized, split,
   and digest manifests.
3. Distribution continuity: pass both predeclared comparisons without
   corrective sampling.
4. Combined Session evidence: classify the final legitimate count exactly:
   `<100 = hard analytical failure`; `100–109 = frozen minimum met but Phase-3
   evidence target missed`; `≥110 = planned evidence target achieved`.
5. Margin derivation: derive a finite practical margin under the unchanged
   linear-interpolated P90/2 rule.
6. Session hardening: pass the frozen Type-I, split-half, leave-one-session-out,
   dominant-hero, and evidence-completeness gates.
7. Exact `m=3` multiplicity: pass the registered BY grid for Transfer,
   Post-Loss, and Session Drift.
8. Candidate freeze: hash source, corpora, methods, margins, gates,
   multiplicity, semantics, and predictive intervals before validation.

Every failure stops without retry, replacement, extra pages, top-up, weighting,
or method change.

## Three-family multiplicity execution plan

The universe is exactly Transfer, Post-Loss, and Session Drift. Presence &
Exposure remains deferred. Use existing validated stress machinery where
possible with:

```text
m = 3
q = .05
release procedure = Benjamini-Yekutieli
diagnostic comparator = Benjamini-Hochberg
repetitions per cell = 10,000
signed-prevalence draws = 2,000
seed = 20260828
truth = complete null, mixed truth/one moderate alternative, subset nulls
dependence = independent, rho .5, rho .9, feasible adverse rho -.25,
             empirical tuning dependence
```

Every registered BY null cell must have estimated FDR ≤.055 and Wilson lower
bound ≤.05. Publication yield cannot select BH, BY, the family universe, or a
stress scenario.

## Reusable corpus extension

Do not overwrite Phase-2 files. Create the sibling campaign
`.local/corpora/opendota/v61-session-drift-phase3-extension/` with:

```text
raw provider capture
→ normalized provider-specific projection
→ cohort/split manifests
→ derived analytical features
```

Preserve OpenDota provenance, deterministic digests, the salted SHA-256
pseudonym scheme, the new private Phase-3 HMAC salt/namespace, and campaign
identity. A combined manifest references both immutable campaign digests.
Future V7/STRATZ reuse requires separate provider layers and explicit field
mapping; no OpenDota field may be semantically relabeled as STRATZ.

## Recommended owner approval

Three fixed choices were evaluated:

| plan | target | eligible | candidates | requests | whole-block IDR | expected final | joint lower bound | storage ceiling |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A minimum | 105 | 248 | 493 | 796 | 1,600 | 110.43 | 95.07% | 75 MiB |
| **B balanced** | **110** | **407** | **792** | **1,196** | **2,400** | **117.76** | **95.09%** | **100 MiB** |
| C conservative | 125 | 862 | 1,641 | 2,348 | 4,800 | 138.74 | 95.06% | 180 MiB |

Approve Plan B. Plan A leaves only a five-observation formal target buffer;
Plan C moves expected evidence far beyond the owner's preferred range with
diminishing returns.

Exact requested approval:

> I approve the fixed V6.1 Session Drift Phase-3 tuning-only wave of 792 candidate accounts, exactly 4 public-match pages and 400 seed-match details, a hard ceiling of 1,196 physical OpenDota calls, Rp2,400 under the supplied whole-block rate, and 100 MiB additional retained storage, with zero retries, replacements, adaptive stopping, or top-ups.

## Luna Phase-3 execution scope

The execution-only prompt is
`docs/prompts/v61-session-drift-phase3-luna-execution.md`. It fixes the Phase-2
base SHA, branch/worktree workflow, owner approval stop, exclusion union,
candidate discovery, HMAC ranking, counts, tuning-only split, collection and
storage ceilings, frozen processing, continuity, pooling, gates, multiplicity,
corpus append, artifacts, cleanup, and branch disposition.

## What must NOT change

- Session minimum, estimator, sessionization, eligibility, p-value, margin,
  support, stability, robustness, or evidence-completeness rules.
- Transfer or Post-Loss contracts.
- The fixed three-family universe or BY release procedure based on yield.
- Any old/revealed holdout or fresh sealed-validation analytical output.
- Production code, frozen runtime artifacts, public report contract, database,
  Redis, infrastructure, release metadata, or deployment.
- Phase-2 corpus bytes, manifests, or provenance.

## Files created

Tracked:

- `scripts/v61_session_drift_phase3_plan.py`
- `docs/evidence/free-dna-v6.1-session-drift-phase3-plan-2026-08-28.md`
- `docs/prompts/v61-session-drift-phase3-luna-execution.md`

Local-only under `.local/diagnostics/v61-session-drift-phase3-plan/`:

- `phase2_support_reconciliation.json`
- `support_predictive_models.json`
- `target_comparison.json`
- `eligible_to_candidate_conversion.json`
- `phase3_sampling_frame_spec.json`
- `prior_candidate_exclusion_spec.json`
- `validation_extension_decision.json`
- `phase3_cost_model.json`
- `pooling_contract.json`
- `phase3_gates.json`
- `three_family_multiplicity_execution_plan.json`
- `reusable_corpus_extension_plan.json`
- `owner_decision_options.json`
- `aggregate_summary.json`

## Integrity verification

```text
PROVIDER CALLS = 0
OLD REVEALED HOLDOUT EVALUATED = 0
FRESH SEALED VALIDATION ANALYTICALLY EVALUATED = 0
SESSION MINIMUM LOWERED = NO
SESSION METHODOLOGY CHANGED = NO
TRANSFER OR POST-LOSS CHANGED = NO
PRODUCTION ANALYTICAL BEHAVIOR CHANGED = NO
DEPLOYMENT = NO
RAW ACCOUNT IDS IN TRACKED OUTPUT = 0
```
