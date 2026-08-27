# V6.1 Findings Recovery — Implementation Specification

Status: **BLOCKED_PENDING_STATISTICAL_METHOD**.

Do not implement this draft. The 2026-08-27 hardening run rejected the proposed
scalar-centered bootstrap. The subsequent product redesign demoted Pool Shape
to the existing Breadth and Toolkit Elements and replaced Combat Expression
with one candidate Presence & Exposure relationship. The detailed five-family
rules below are preserved as historical recovery material, not an executable
specification.

Before this prompt can become implementation-ready, a new statistical pass
must:

- freeze exact estimands, nulls, statistics, support rules, and invalid-draw
  behavior for Transfer, Post-Loss, Presence & Exposure, and Session Drift;
- validate each retained family separately with a family-appropriate null;
- rerun Type-I and power/coverage validation before deriving margins;
- derive tuning-only practical margins without targeting publication yield;
- freeze executable stability and robustness gates; and
- validate the retained p-value dependence before choosing multiplicity rules.

See `docs/evidence/free-dna-v6.1-findings-statistical-hardening-2026-08-27.md`,
`docs/evidence/free-dna-v6.1-family-null-models-2026-08-27.md`, and
`docs/evidence/free-dna-v6.1-pool-combat-family-redesign-2026-08-27.md`.

## Scope and hard firewall

Implement a new research analytical candidate in an isolated branch. Do not
modify production configuration, call OpenDota/Steam/STRATZ, collect new data,
rerun the revealed holdout, tune against the revealed holdout, regenerate the
frozen V6.1 bundle, deploy, merge main, or change V6.1 release metadata.
Preserve these historical identities exactly:

- source SHA: `7df38e6d234ae9c4ee425490bc40b8cc92685f85`
- frozen full artifact package digest: `8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0`

The candidate is a new analytical lineage. Do not label changed estimates as
`free-dna-model-6.1.0` or claim the existing holdout validates them.

## One recommended architecture

- five family roots remain the hypothesis universe;
- each family has one predeclared scalar/max-contrast omnibus statistic;
- uncertainty is a corrected null-centered session-cluster bootstrap, exactly
  `B=2_000`, with a deterministic per-profile seed derived from candidate
  version, artifact checksums, profile digest, and salt;
- family p-values enter fixed five-family BH at `q=0.05` (`m=5`), even when a
  family is structurally unsupported; unsupported p-values are fail-closed at
  `1.0` and do not change m;
- branches are deterministic interpretation labels of the qualified family
  result; there is no branch BH in this candidate;
- a branch that is a genuinely distinct hypothesis must be deferred or added
  as a new registered statistic with an explicitly predeclared correction;
- V6 is `V6_MEASUREMENT_INPUT_ONLY`: an inherited V6 `published` boolean is
  never a V6.1 publication prerequisite;
- product output remains capped at three qualified findings after analytical
  qualification; the cap is not a statistical gate.

## Estimator interface

Add an internal pure interface, preferably in
`services/api/app/player_analysis_v61/production_statistics.py` or a new
research-only module:

```python
class FamilyStatistic(Protocol):
    family: str
    def point(self, matches: Sequence[Any], context: FamilyContext) -> FamilyEstimate: ...
    def resample(self, session_clusters: Sequence[SessionCluster], context: FamilyContext) -> FamilyEstimate: ...

@dataclass(frozen=True)
class FamilyEstimate:
    value: float | None
    opportunities: int
    sessions: int
    components: Mapping[str, float | None]
    evidence: Mapping[str, Any]
    valid: bool

@dataclass(frozen=True)
class BootstrapInference:
    point: float
    interval: tuple[float, float]
    raw_p: float
    family_q: float
    practical_effect: bool
    stable: bool
    robust: bool
    evidence_complete: bool
    state: str
```

### Rejected helper — do not implement

The recovery proposal asked the p helper to accept the point estimate
separately:

```python
def null_centered_bootstrap_p(
    draws: Sequence[float], *, point: float, null: float = 0.0
) -> float:
    extreme = sum(abs(draw - point) >= abs(point - null) for draw in draws)
    return (extreme + 1) / (len(draws) + 1)
```

This is not a valid family-level test specification. For max statistics it
centers only the selected scalar maximum and loses the joint component null;
for the Pool scalar it was still anti-conservative in several clustered nulls.
Reject empty/non-finite draws, but do not substitute this helper for the
current implementation or begin candidate implementation until a replacement
method is frozen.

## Resampling

1. Group eligible rows by `session_id`; missing IDs are individual fail-closed
   clusters, not silently merged.
2. Sample exactly the number of observed session clusters with replacement.
3. Recompute the family statistic on each resample; do not treat match rows as
   independent.
4. Preserve within-session chronology and session boundaries.
5. Keep cross-fitted calibration/frontier artifacts fixed during a report run;
   do not refit them inside a draw.
6. Return a percentile 95% interval and the corrected null-centered p.
7. Mark the estimate invalid if required denominators/coverage fail in the
   point estimate or in the evidence required for the claim.

## Family-specific source mapping and exact candidate rules

The machine-readable research specification below is authoritative. The
implementation worker must implement these fields as written; a missing field
or unresolved source is a STOP condition.

```json
[
  {
    "abstention_rule": "Missing completeness, <30 matches, <12 sessions, invalid draws, unstable direction, or incomplete portfolio evidence => insufficient/neutral; never fabricate a branch.",
    "alternative_hypothesis": "H1: Delta_pool != 0.",
    "behavioral_claim": "The supported hero-pool shape differs from the supported job/toolkit shape in a stable direction.",
    "branch_evidence": "Use signed scalar CI and source-specific descriptive rows; do not copy one omnibus draw into each old branch.",
    "branch_multiplicity_required": "NO for the retained label; YES only if a distinct branch is separately registered and tested.",
    "branch_type": "DIRECTIONAL_LABEL for the retained scalar; distinct old branches are not independently public",
    "confounders_adjustments": "No rank/MMR or inferred intent; taxonomy is frozen/cross-fitted. Record patch/hero/context coverage as limitations, not causal adjustments.",
    "correct_bootstrap_source": "portfolio_shape breadth/toolkit and predeclared chronological shape contrast, recomputed on each session resample",
    "current_bootstrap_source": "semantic_statistics.families.pool_shape = breadth - toolkit",
    "equivalence_rope_rule": "Not a public candidate for the directional omnibus. A compatible-shape statement requires the 95% CI wholly inside +/- the predeclared rope and remains neutral, not a Finding.",
    "estimand": "Delta_pool = signed predeclared contrast between hero breadth/chronological JSD and match-weighted job/toolkit shape; candidate v1 uses hero_JSD - job_JSD as the scalar omnibus.",
    "family": "pool_shape",
    "family_name": "Pool Shape",
    "independent_clustering_unit": "session_id; entire session is resampled together",
    "minimum_clusters_sessions": 12,
    "minimum_opportunities": 30,
    "null_hypothesis": "H0: Delta_pool = 0.",
    "opportunity_definition": "All normalized eligible matches inside the profile's 365-day window; chronological thirds preserve within-session order.",
    "player_facing_question": "What shape does your hero pool have beyond its most-used names?",
    "practical_effect_threshold": 0.09223679546260193,
    "publication_rule": "Publish only the retained scalar outcome after the state machine; V6 published is not a prerequisite.",
    "raw_observation_unit": "eligible summary-history match",
    "recommended_family_qualification": "p <= 0.05 after fixed five-family BH, CI excludes 0, absolute effect >= margin, and all support/evidence/stability/robustness gates pass.",
    "recommended_resampling_unit": "session cluster bootstrap with replacement; preserve rows and order within sampled sessions",
    "recommended_uncertainty_method": "Corrected null-centered two-sided cluster-bootstrap p plus percentile 95% CI, B=2,000; pass point and observed statistic separately.",
    "robustness_requirement": "Sign/direction persists under dominant-hero exclusion and taxonomy sensitivity; no single session contributes >25% of effective information.",
    "semantic_branches": [
      "pool_shape_contrast: hero wider vs job wider is a directional label",
      "hidden_center and names_changed_jobs_held are distinct hypotheses deferred to supporting evidence"
    ],
    "semantic_evidence_requirement": "Portfolio shape rows, denominator, chronology, taxonomy status, and alternatives all present.",
    "stability_requirement": "Sign agreement >= 0.80 across split-half and leave-one-session-out diagnostics; no more than 10% degenerate resamples.",
    "structural_eligibility": "Complete canonical history, at least 30 eligible matches, at least 12 sessions, taxonomy/cross-fit inputs valid."
  },
  {
    "abstention_rule": "If either comparison band lacks support, any component is invalid, or branch evidence is incomplete, publish no transfer claim.",
    "alternative_hypothesis": "H1: at least one supported component departs from its core value by the predeclared practical margin.",
    "behavioral_claim": "At the supported distance frontier, a specific covered component changes or remains compatible when the hero changes.",
    "branch_evidence": "Branch text must point to the component-specific CI and distance-band row that selected it; no shared family list may stand in for branch evidence.",
    "branch_multiplicity_required": "NO for deterministic labels of one family max statistic; YES for any newly public distinct component hypothesis.",
    "branch_type": "MUTUALLY_EXCLUSIVE_LABEL / COMPOSITE_INTERPRETATION",
    "confounders_adjustments": "Distance bands are cross-fitted; no hero-choice causality. Report taxonomy/context coverage and component-specific alternatives.",
    "correct_bootstrap_source": "continuous_transfer component deltas from core/reliable_stretch, recomputed by session cluster",
    "current_bootstrap_source": "semantic_statistics.families.transfer = transfer frontier score",
    "equivalence_rope_rule": "clean_transfer is a neutral/equivalence state unless a predeclared TOST/ROPE family test is added; require every component CI inside its rope for a compatibility label.",
    "estimand": "Delta_transfer,k = mean(component_k | reliable_stretch) - mean(component_k | core), k in {outcome, activity, survival}; candidate omnibus is the maximum predeclared standardized component departure.",
    "family": "transfer",
    "family_name": "Transfer",
    "independent_clustering_unit": "session_id; preserve band assignments fixed by the cross-fitted calibration",
    "minimum_clusters_sessions": 12,
    "minimum_opportunities": 30,
    "null_hypothesis": "H0: all Delta_transfer,k are 0 within the predeclared component ropes.",
    "opportunity_definition": "Both core and reliable-stretch bands must have at least 30 component-complete matches and 12 sessions; no edge band is public.",
    "player_facing_question": "What survives when the hero changes?",
    "practical_effect_threshold": {
      "activity": 0.05815105200559039,
      "outcome": 0.09223679546260193,
      "survival": 0.2346401477174622
    },
    "publication_rule": "Publish one transfer family outcome only after the family state is Qualified and a deterministic label has complete component evidence.",
    "raw_observation_unit": "match assigned to a cross-fitted core or reliable-stretch distance band",
    "recommended_family_qualification": "Family max statistic p <= 0.05 after fixed five-family BH, practical component margin, complete frontier evidence, and reliability gates.",
    "recommended_resampling_unit": "whole session cluster with replacement; keep cross-fitted band and calibration fixed",
    "recommended_uncertainty_method": "Corrected null-centered max-component bootstrap p plus component percentile CIs; separate CI-inside-ROPE decision for compatibility.",
    "robustness_requirement": "Cross-fitted frontier stable under dominant-hero and taxonomy perturbation; core/stretch result not driven by one session.",
    "semantic_branches": [
      "transfer_frontier_change: component/direction label",
      "clean_transfer: neutral equivalence interpretation",
      "old boundary labels are not separate p-values"
    ],
    "semantic_evidence_requirement": "Core/stretch counts, sessions, component deltas/CIs, frontier, cross-fit status, and alternatives present.",
    "stability_requirement": "Frontier direction/component selection agrees >=0.80 across split-half and leave-one-session-out; no band loses support in >20% of resamples.",
    "structural_eligibility": "Cross-fitted frontier valid, core/stretch denominators meet minima, component coverage valid, and 365-day history complete."
  },
  {
    "abstention_rule": "No supported state contrast, incomplete transition evidence, cross-session transition, invalid draw, or unstable sign => insufficient/neutral.",
    "alternative_hypothesis": "H1: at least one supported state contrast exceeds the practical movement margin.",
    "behavioral_claim": "Within supported same-session result states, next-choice movement differs in a predeclared way.",
    "branch_evidence": "Use only the state rows involved in the selected contrast, with transition counts, sessions, movement CIs, and next-result guardrail.",
    "branch_multiplicity_required": "NO for the one predeclared family max contrast; YES if multiple state contrasts become separate public claims.",
    "branch_type": "DISTINCT_OLD_HYPOTHESES_COLLAPSED_TO_ONE_PREDECLARED_CONTRAST",
    "confounders_adjustments": "Same-hero rate, next result, and context coverage are guardrails/descriptors; do not call the result causal or psychological.",
    "correct_bootstrap_source": "result_response_summary transition movements rebuilt from each resampled session",
    "current_bootstrap_source": "semantic_statistics.families.post_loss_response = finishing (incorrect)",
    "equivalence_rope_rule": "result_invariant_response is neutral unless a predeclared equivalence test is passed; require every compared state CI/range inside +/-0.5.",
    "estimand": "Delta_response = max_s,s' |mean(movement | state=s) - mean(movement | state=s')| over the predeclared state contrast set; no cross-session transitions.",
    "family": "post_loss_response",
    "family_name": "Post-Loss Response",
    "independent_clustering_unit": "session_id; transition rows within a session are not independent",
    "minimum_clusters_sessions": 12,
    "minimum_opportunities": 30,
    "null_hypothesis": "H0: all predeclared supported result-state movement means are equal.",
    "opportunity_definition": "Chronological adjacent matches within a session; prior result assigns win/one_loss/two_plus_losses/win_streak; rows never cross session boundaries.",
    "player_facing_question": "What does your next choice look like after a loss?",
    "practical_effect_threshold": 0.5,
    "publication_rule": "Publish one bounded result-state claim only after corrected source mapping and the complete state machine pass.",
    "raw_observation_unit": "ordered loss/result-state transition within a session",
    "recommended_family_qualification": "Family max-contrast p <= 0.05 after fixed five-family BH, practical effect, state support, and all reliability/evidence gates.",
    "recommended_resampling_unit": "whole session cluster with replacement; recompute transitions after resampling, never concatenate sessions",
    "recommended_uncertainty_method": "Corrected null-centered max-contrast session bootstrap p plus state-specific percentile CIs; TOST/ROPE only for the invariant label.",
    "robustness_requirement": "Result persists under same-hero exclusion and session-length stratification; no cross-session reuse.",
    "semantic_branches": [
      "result_state_response_contrast: state/direction label",
      "one_loss_runback/two_loss_switch are interpretations of the selected contrast",
      "invariant response remains neutral/equivalence"
    ],
    "semantic_evidence_requirement": "Transition construction, state definitions, per-state denominators, movement range, next-result guardrail, and alternatives present.",
    "stability_requirement": "Selected state contrast sign agrees >=0.80 across split-half and leave-one-session-out; state support survives >=90% of bootstrap draws.",
    "structural_eligibility": "At least 30 transitions and 12 sessions overall; every state used in a public contrast has at least 12 transitions across at least 8 sessions."
  },
  {
    "abstention_rule": "Invalid context, <30 matches, <12 sessions, <80% coverage, unstable relation, or missing component evidence => insufficient.",
    "alternative_hypothesis": "H1: at least one component relationship departs from the covered agreement region.",
    "behavioral_claim": "Context-adjusted involvement, exposure, and result components show a reproducible relationship in supported matches.",
    "branch_evidence": "Point/CI/evidence rows for every component named in the label; finishing remains an explicit guardrail where used.",
    "branch_multiplicity_required": "NO for labels of one family statistic; YES for localized variance or any new component hypothesis.",
    "branch_type": "MUTUALLY_EXCLUSIVE_LABEL for retained relationship; DISTINCT_HYPOTHESIS deferred",
    "confounders_adjustments": "Use frozen context baselines; never infer positioning, aggression, skill, intent, rank, or cause.",
    "correct_bootstrap_source": "context-adjusted involvement/death-exposure/outcome component vector, recomputed by session",
    "current_bootstrap_source": "semantic_statistics.families.combat_expression = involvement - death_exposure",
    "equivalence_rope_rule": "Agreement labels require all required component CIs inside their component ropes; otherwise describe the component that moves.",
    "estimand": "Delta_combat = predeclared discordance between context-adjusted involvement, death exposure, and outcome components; candidate v1 uses max absolute standardized component contrast.",
    "family": "combat_expression",
    "family_name": "Combat Expression",
    "independent_clustering_unit": "session_id; all match rows in a session resampled together",
    "minimum_clusters_sessions": 12,
    "minimum_opportunities": 30,
    "null_hypothesis": "H0: the covered combat components move together within their practical margins.",
    "opportunity_definition": "Matches with valid context-adjusted involvement and death exposure; finishing is separate evidence/guardrail, not silently substituted.",
    "player_facing_question": "Which covered match signals move together once the game starts?",
    "practical_effect_threshold": {
      "death_exposure": 0.05815105200559039,
      "involvement": 0.05815105200559039,
      "outcome": 0.09223679546260193
    },
    "publication_rule": "Publish a single bounded component relationship after the state machine; do not derive it from Element zones in a client.",
    "raw_observation_unit": "context-resolved match with involvement and death-exposure values",
    "recommended_family_qualification": "Family discordance statistic p <= 0.05 after fixed five-family BH, practical component effect, coverage, and robustness gates.",
    "recommended_resampling_unit": "whole session cluster with replacement; retain context-resolution and baseline version",
    "recommended_uncertainty_method": "Corrected null-centered max-component bootstrap p plus component CIs; no separate p for deterministic relationship labels.",
    "robustness_requirement": "Stable after dominant-hero/context stratification and overdispersion check; no one session dominates.",
    "semantic_branches": [
      "expression_result_discordance: involvement/exposure/result relationship label",
      "localized_variance deferred until independently registered"
    ],
    "semantic_evidence_requirement": "Component definitions, context coverage, CIs, denominator, overdispersion, and forbidden interpretations present.",
    "stability_requirement": "Relationship label/sign agrees >=0.80 across split-half and leave-one-session-out; context coverage stays >=80%.",
    "structural_eligibility": "At least 30 complete component matches, at least 12 sessions, and >=80% context coverage for each required component."
  },
  {
    "abstention_rule": "Fewer than two supported positions, missing completion, unreachable threshold, unstable sign, or wrong source mapping => insufficient/neutral.",
    "alternative_hypothesis": "H1: at least one supported position contrast exceeds the practical margin.",
    "behavioral_claim": "The direct covered expression curve changes across predeclared positions in completed sessions.",
    "branch_evidence": "Direct position counts/sessions/rates or expression values, censoring count, selected contrast, and selection alternative.",
    "branch_multiplicity_required": "NO for one predeclared position-contrast family statistic; YES for separately registered breakpoint/stopping hypotheses.",
    "branch_type": "DISTINCT_OLD_HYPOTHESES_COLLAPSED_TO_ONE_PREDECLARED_POSITION_CONTRAST",
    "confounders_adjustments": "Report selection into longer sessions and 365-day boundary; do not call fatigue, warm-up, intent, or cause.",
    "correct_bootstrap_source": "session_position_curve direct G1-G5+ positions, recomputed from completed sessions",
    "current_bootstrap_source": "semantic_statistics.families.session_drift = consistency (incorrect)",
    "equivalence_rope_rule": "A compatible curve is neutral unless every compared position CI is inside +/-0.8647735608975679; no directional Finding from equivalence alone.",
    "estimand": "Delta_session = max_g,g' |mean(expression at position g) - mean(expression at position g')| over the predeclared G1-G5+ position set.",
    "family": "session_drift",
    "family_name": "Session Drift",
    "independent_clustering_unit": "completed session_id; censoring is explicit and not imputed",
    "minimum_clusters_sessions": 12,
    "minimum_opportunities": 30,
    "null_hypothesis": "H0: the direct completed-session position curve is compatible across all predeclared positions.",
    "opportunity_definition": "Only completed sessions reaching each direct position; compare positions that each have >=12 sessions and >=30 position observations where required.",
    "player_facing_question": "Does the covered expression change across completed session positions?",
    "practical_effect_threshold": 0.8647735608975679,
    "publication_rule": "Publish one direct position-curve claim only after completion wiring and direct bootstrap evidence are implemented and validated.",
    "raw_observation_unit": "completed-session position observation (G1, G2, G3, G4, G5+)",
    "recommended_family_qualification": "Family position-contrast p <= 0.05 after fixed five-family BH, practical effect, position support, and selection/robustness gates.",
    "recommended_resampling_unit": "completed session cluster with replacement; exclude censored sessions from all positions",
    "recommended_uncertainty_method": "Corrected null-centered max-position-contrast bootstrap p plus position-specific CIs; no raw match independence assumption.",
    "robustness_requirement": "Early/late window and session-length sensitivity do not reverse the claim; selection into longer sessions remains disclosed.",
    "semantic_branches": [
      "position_curve_change: opening/gradual/breakpoint interpretation",
      "selection_only_drift and stopping response deferred until separately evidenced"
    ],
    "semantic_evidence_requirement": "Direct positions, completed/censored sessions, denominators, curve values, and alternatives present.",
    "stability_requirement": "Selected position contrast sign agrees >=0.80 across split-half and leave-one-session-out; supported positions remain supported in >=90% of draws.",
    "structural_eligibility": "At least two predeclared positions supported, at least 30 position observations, at least 12 completed sessions, and no unreachable calibration sentinel."
  }
]
```

Summary of the five public candidate branches:

| family | retained branch | branch treatment |
| --- | --- | --- |
| pool_shape | `pool_shape_contrast` | signed/directional label; old concentration/chronology branches deferred |
| transfer | `transfer_frontier_change` | component/direction label; `clean_transfer` is a ROPE/neutral state |
| post_loss_response | `result_state_response_contrast` | selected state-contrast label; no copied finishing evidence |
| combat_expression | `expression_result_discordance` | component relationship label; localized variance deferred |
| session_drift | `position_curve_change` | direct completed-position label; breakpoint/stopping deferred |

## Publication state machine

Evaluate states in this order and record the first and all blockers:

`NOT_STRUCTURALLY_ELIGIBLE → INSUFFICIENT_SUPPORT → ESTIMATOR_INVALID → NO_PRACTICAL_EFFECT → STATISTICALLY_UNQUALIFIED → UNSTABLE → CONFOUNDED → SEMANTIC_EVIDENCE_INCOMPLETE → QUALIFIED → PUBLISHABLE`.

Every failure is abstention. `PUBLISHABLE` additionally requires public
rollout status and the post-qualification product cap. `finding.published` from
V6 is not read as a gate. Expose only registered copy/evidence after the state
is `PUBLISHABLE`; otherwise redact claim/branch/interaction fields as the
existing strict schema requires.

## Exact modules/functions

Change only the future candidate implementation surfaces:

- `services/api/app/player_analysis_v61/production_statistics.py`: add the
  corrected p helper, explicit point/draw interface, and session-cluster
  inference result;
- `services/api/app/player_analysis_v61/family_statistics.py`: route candidate
  inference to the corrected helper; retain fixture-only helpers only if tests
  explicitly label them fixture-only;
- `services/api/app/player_analysis_v61/relationships.py`: expose direct
  post-loss transition and completed-session position estimands with stable
  session grouping;
- `services/api/app/reports/dna_assembly_v61.py`: use the family-specific
  evidence vectors, apply the single state machine, remove the inherited V6
  publication veto for the candidate version, and emit one retained semantic
  label per family;
- `services/api/app/player_analysis_v61/semantic_outcomes.py` and `copy.py`:
  add a new versioned candidate registry/copy surface only after the five
  retained branches and deferred branches are reviewed;
- `services/api/app/player_analysis_v61/versions.py`: add new candidate
  version keys without changing frozen V6.1 values;
- `scripts/build_v61_calibration_artifacts.py` (new candidate path only): pass
  `completed_sessions_by_profile` into threshold derivation; do not overwrite
  frozen V6.1 artifacts;
- new candidate artifact builder/reproducibility manifest: bind corpus/split,
  source, statistic version, q, margins, seed rule, and all checksums.

## Must remain untouched

- `infra/runtime-artifacts/free_dna_v61/6.1.0/**`;
- existing frozen V6.1 source binding and release metadata;
- the revealed holdout and all historical evidence files;
- `services/api/app/player_analysis_v6/**` semantics, unless an explicitly
  reviewed compatibility adapter is required and proves V6 behavior unchanged;
- database, Redis, providers, environment variables, flags, deployment files;
- frontend/presentation code and persisted report fixtures in this analytical
  implementation pass.

If a public schema or persisted report contract must change, STOP and request a
separate contract review; do not silently make the candidate backwards
incompatible.

## Required tests

- unit tests for the corrected p helper: exact null, noisy null, clustered null,
  heavy tail, constant positive, constant negative, empty, and non-finite;
- estimator tests for each five source mappings and minimum support boundaries;
- session-cluster resampling tests proving no cross-session transition and no
  match-level independence assumption;
- branch tests proving retained labels are not separate p-values and deferred
  distinct branches cannot publish;
- publication state-machine tests for every state and first-blocker ordering;
- deterministic synthetic null/positive tests with fixed seed, coverage,
  degeneracy, power trend, and cluster-size sensitivity;
- tuning-only regression against the 791 profiles, without loading any holdout;
- reproducibility run with byte-identical candidate outputs;
- negative controls and privacy scan.

## Protected holdout and network firewall

Test code must fail if it opens a socket or instantiates a provider client.
The existing 339-profile holdout may only be summarized as historical context;
it must not be loaded during tuning, candidate selection, threshold fitting, or
method comparison. No replacement holdout may be selected or executed here.

## Required outputs

Keep profile-level traces local-only, mode `0600`, pseudonymized by a stable
digest, and free of raw account/Steam/report/match/session identifiers. Emit
the same research outputs:

`.local/diagnostics/v61-findings-statistical-recovery/`

with provenance, diagnosis, contract/gate audits, p-value controls, family
specifications, method matrix, synthetic results, multiplicity architectures,
candidate rows, reliability checks, family verdicts, and aggregate summary.

## STOP conditions

Stop with `PARTIAL`/`BLOCKED` if provenance is ambiguous, source semantics are
not recoverable, a method fails synthetic null validity, a holdout is needed,
network access is needed, p/q would be fabricated, or implementation would
modify frozen V6.1 behavior/artifacts or production.

## Definition of Done

- exact source mapping and clustering tested for all five families;
- corrected p mechanism demonstrated and current pathology preserved as a
  historical diagnosis;
- fixed five-family BH and no-branch-BH architecture implemented;
- all support/effect/stability/robustness/confounder/semantic gates are actual
  publication decisions;
- V6 publication is not a candidate veto;
- synthetic validity and tuning regression pass;
- candidate artifacts are new, bound, reproducible, and not confused with
  frozen V6.1;
- fresh sealed holdout plan is written but not executed;
- no external calls, holdout rerun, production change, or deployment.
