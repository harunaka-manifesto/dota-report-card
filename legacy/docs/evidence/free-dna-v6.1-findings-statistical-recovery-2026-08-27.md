# V6.1 Findings Statistical Recovery

## Status

**PASS — research specification complete; fresh validation required before any analytical release.** The runtime trace, method screen, and outputs were generated offline from the 791-profile training partition. This task did not implement the redesigned inference path.

## Integrity

| item | value |
| --- | --- |
| base SHA | 3d0e65cebb01434f14edcffd43aa797163057b93 |
| branch | codex/research-v61-findings-statistical-recovery-20260827 |
| origin/main | d1a5b8de2826644d66689073a4d4c2a68b290a49 |
| analytical source SHA | 7df38e6d234ae9c4ee425490bc40b8cc92685f85 |
| frozen artifact package | 8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0 |
| external collection calls | 0 |
| holdout reruns | 0 |
| production changes | 0 |

## Canonical evidence consumed

Latest evidence: `docs/evidence/free-dna-v6.1-suppression-autopsy-2026-08-27-complete.md`. Older partial evidence: `docs/evidence/free-dna-v6.1-suppression-autopsy-2026-08-27.md`. The replacement V2.1 corpus is the only corpus used for candidate comparisons; the protected holdout is summarized only as a pre-existing output.

| dataset | classification | profile_count | allowed_use |
| --- | --- | --- | --- |
| replacement canonical corpus | TUNING_ELIGIBLE | 1130 | method/architecture comparison and exploratory yield only on train partition |
| 791-profile frozen training partition | TUNING_ELIGIBLE | 791 | offline runtime reproduction and candidate comparison |
| 339-profile replacement holdout output | DESCRIPTIVE_ONLY | 339 | summarize already-frozen historical outcome; never select a method or threshold |
| historical V6.1 2.0.0 corpus | HISTORICAL_ONLY | 1130 | reconcile older conclusions; not method selection |
| frozen V6.1 runtime artifact package | DESCRIPTIVE_ONLY | None | read-only current runtime reproduction |
| stored bootstrap runtime trace | TUNING_ELIGIBLE | 791 | reproduce current path and compare research candidates |
| synthetic deterministic simulations | DESCRIPTIVE_ONLY | None | known-truth method validity only |
| future deeper-history or fresh sealed validation data | UNKNOWN_BLOCKED | None | not available; requires separately authorized collection/selection and cannot enter this comparison |

## Diagnosis reproduction

| family | current qualified | branch qualified | lost to V6 published=false | survived V6 | finally published |
| --- | --- | --- | --- | --- | --- |
| pool_shape | 0 | 0 | 0 | 0 | 0 |
| transfer | 70 | 70 | 65 | 5 | 5 |
| post_loss_response | 0 | 0 | 0 | 0 | 0 |
| combat_expression | 0 | 0 | 0 | 0 | 0 |
| session_drift | 0 | 0 | 0 | 0 | 0 |

Load-bearing results are marked as follows:

- **CONFIRMED:** 791/791 trace evaluation, zero errors, zero provider calls; Transfer 70 family-qualified → 5 inherited V6-published; branch p-values duplicate within family; Post-Loss and Session source projections mismatch their declared evidence; support/evidence gates are not final booleans.
- **PARTIALLY_CONFIRMED:** the older partial report's statement that Transfer/Combat/Pool bootstrap computation was blocked is superseded by the newer complete trace; its separate calibration-tool completion-wiring concern remains confirmed in `scripts/build_v61_calibration_artifacts.py:216-226` versus `derive_thresholds_v61(... completed_sessions_by_profile=...)`.
- **NOT USED FOR SELECTION:** the 339-profile holdout output, older V6.1 corpora, and any historical yield claim.

## Current publication architecture

| transition | source | state |
| --- | --- | --- |
| raw family evidence → family estimator | services/api/app/reports/dna_assembly_v61.py:1096-1121 | CALCULATED |
| family estimator → bootstrap/resampling | services/api/app/reports/dna_assembly_v61.py:1123-1145; :660-919 | CALCULATED |
| bootstrap/resampling → family statistic | services/api/app/reports/dna_assembly_v61.py:609-657; services/api/app/player_analysis_v61/family_statistics.py:19-26 | CALCULATED |
| family statistic → family multiplicity correction | services/api/app/player_analysis_v61/hierarchical.py:23-35 | CALCULATED + ENFORCED |
| family statistic → branch statistic | services/api/app/reports/dna_assembly_v61.py:1220-1244 | CALCULATED |
| branch statistic → branch correction | services/api/app/player_analysis_v61/hierarchical.py:35-55 | CALCULATED + ENFORCED |
| branch correction → inherited V6 state | services/api/app/reports/dna_assembly_v61.py:1246-1261 | INHERITED_FROM_V6 + ENFORCED |
| inherited V6 state → support/effect/stability/semantic checks | services/api/app/reports/dna_assembly_v61.py:1246-1261 | RECORDED_ONLY / IGNORED |
| checks → publication eligibility | services/api/app/reports/dna_assembly_v61.py:1256-1262 | ENFORCED for V6 flag, branch, rollout, cap, Pool completeness only |
| publication eligibility → report assembly | services/api/app/reports/dna_assembly_v61.py:1263-1322 | CALCULATED + ENFORCED |

## P-value pathology

| input_design | observed_statistic | returned_current_p | corrected_null_centered_p | valid_current | reason |
| --- | --- | --- | --- | --- | --- |
| A1_exact_null_constant | 0.0 | 1.0 | 1.0 | True | current function is finite but does not center the bootstrap sampling error at the null |
| A2_symmetric_noise_centered_null | 0.0024198569811456874 | 0.9940029985007496 | 0.9945027486256871 | True | current function is finite but does not center the bootstrap sampling error at the null |
| A3_clustered_null_varying_sizes | 0.10384496024799299 | 0.5662168915542228 | 0.4572713643178411 | True | current function is finite but does not center the bootstrap sampling error at the null |
| A4_heavy_tailed_null | -0.008529042207152455 | 0.9675162418790605 | 0.9655172413793104 | True | current function is finite but does not center the bootstrap sampling error at the null |
| B1_constant_positive | 1.0 | 1.0 | 0.0004997501249375312 | False | current function compares each draw to null using the observed bootstrap mean; constant non-null draws are all counted extreme, so p=1 |
| B2_constant_negative | -1.0 | 1.0 | 0.0004997501249375312 | False | current function compares each draw to null using the observed bootstrap mean; constant non-null draws are all counted extreme, so p=1 |
| B3_small_shift_noisy | 0.13948812602653318 | 0.7061469265367316 | 0.6956521739130435 | True | current function is finite but does not center the bootstrap sampling error at the null |
| B4_moderate_shift_noisy | 0.46026220075468793 | 0.495752123938031 | 0.06696651674162919 | True | current function is finite but does not center the bootstrap sampling error at the null |
| B5_strong_shift_noisy | 0.8995282344904413 | 0.49375312343828087 | 0.0004997501249375312 | True | current function is finite but does not center the bootstrap sampling error at the null |

- CURRENT P-VALUE PROCEDURE VALID? NO.
- FAILURE MODE: it treats the observed bootstrap mean as the observed statistic but compares every draw directly to the null; the bootstrap sampling-error distribution is not centered at the null.
- WHY CONSTANT NON-NULL SAMPLES BEHAVE AS THEY DO: if every draw is c != 0, the observed distance is |c| and every draw satisfies |c - 0| >= |c|, so the add-one estimate is (B+1)/(B+1)=1; a null-centered test compares |c-c|=0 with |c-0| and returns approximately 1/(B+1).
- WHICH FAMILIES ARE AFFECTED: every V6.1 production family/branch that uses semantic bootstrap evidence; the defect is shared, even where the evidence source is otherwise aligned.

## Family evidence-source audit

| family | intended_estimand | declared_evidence_source | actual_family_bootstrap_source | match | defect | correct_source_should_be | unit_of_evidence | clustering_unit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pool_shape | hero-pool shape versus match-weighted job/toolkit shape and chronological pool movement | portfolio_shape: breadth/toolkit, concentration, thirds, cross-fitted distance | semantic_statistics.families.pool_shape = breadth - toolkit | PARTIAL | omnibus scalar is narrower than the registered branch catalog; branch evidence is duplicated | predeclared portfolio-shape contrast vector, recomputed from portfolio_shape on session resamples | eligible summary-history match, with chronological session-aware aggregation | whole session |
| transfer | core-to-reliable-stretch component deltas for outcome, activity, and survival | transfer_frontier: cross-fitted distance bands and component deltas | semantic_statistics.families.transfer = transfer frontier score | YES_FOR_FAMILY / NO_FOR_BRANCHES | branch p-values are not branch-specific; equivalent and directional claims share one sample | continuous_transfer core/reliable_stretch component vector with fixed cross-fitted frontier | match in a core or reliable-stretch distance band | whole session, preserving band membership |
| post_loss_response | same-session chronological movement contrast across result states | result_response_summary: win, one_loss, two_plus_losses, win_streak transitions | semantic_statistics.families.post_loss_response = finishing | NO | assembly projects finishing instead of result-state transitions | result_response_summary transitions rebuilt inside each resampled session | ordered within-session transition; no cross-session transition | whole session |
| combat_expression | context-adjusted involvement/exposure relationship, with finishing as a separate guardrail | involvement, death_exposure, finishing and context coverage | semantic_statistics.families.combat_expression = involvement - death_exposure | YES_FOR_FAMILY / NO_FOR_BRANCHES | branch labels such as localized variance are not independently evidenced | context-adjusted component vector recomputed from involvement/death exposure by session | context-resolved match | whole session |
| session_drift | direct result/expression curve over completed-session G1, G2, G3, G4, G5+ positions | session_position_curve: direct positions and censoring | semantic_statistics.families.session_drift = consistency | NO | assembly projects information-weighted consistency instead of direct positions | session_position_curve rebuilt from completed sessions on each session resample | completed session-position observation | whole completed session; censored sessions excluded, not imputed |

## Branch-evidence audit

| family | public_semantic_branches | branch_types | identical_branch_p_frequency | profiles_with_identical_branch_p | classification_for_candidate | distinct_hypothesis_treatment |
| --- | --- | --- | --- | --- | --- | --- |
| pool_shape | ["hidden_center","names_wide_jobs_narrow","names_narrow_jobs_wide","names_changed_jobs_held"] | {"hidden_center":"DISTINCT_HYPOTHESIS","names_changed_jobs_held":"DISTINCT_HYPOTHESIS","names_narrow_jobs_wide":"DIRECTIONAL_LABEL","names_wide_jobs_narrow":"DIRECTIONAL_LABEL"} | 1.0 | 791 | interpretation-only labels; no branch BH | defer or register a separate statistic before making public |
| transfer | ["clean_transfer","results_stop_first","expression_stops_first","involvement_boundary","exposure_boundary","localized_function_bottleneck"] | {"clean_transfer":"COMPOSITE_INTERPRETATION","exposure_boundary":"MUTUALLY_EXCLUSIVE_LABEL","expression_stops_first":"MUTUALLY_EXCLUSIVE_LABEL","involvement_boundary":"MUTUALLY_EXCLUSIVE_LABEL","localized_function_bottleneck":"DISTINCT_HYPOTHESIS","results_stop_first":"MUTUALLY_EXCLUSIVE_LABEL"} | 1.0 | 791 | interpretation-only labels; no branch BH | defer or register a separate statistic before making public |
| post_loss_response | ["one_loss_runback","two_loss_switch","result_shaped_pool","result_invariant_response","adjustment_without_recovery"] | {"adjustment_without_recovery":"DISTINCT_HYPOTHESIS","one_loss_runback":"DISTINCT_HYPOTHESIS","result_invariant_response":"DISTINCT_HYPOTHESIS","result_shaped_pool":"DISTINCT_HYPOTHESIS","two_loss_switch":"DISTINCT_HYPOTHESIS"} | 1.0 | 791 | interpretation-only labels; no branch BH | defer or register a separate statistic before making public |
| combat_expression | ["involvement_holds_exposure_moves","exposure_holds_involvement_moves","same_expression_different_results","different_expression_same_results","localized_variance"] | {"different_expression_same_results":"MUTUALLY_EXCLUSIVE_LABEL","exposure_holds_involvement_moves":"MUTUALLY_EXCLUSIVE_LABEL","involvement_holds_exposure_moves":"MUTUALLY_EXCLUSIVE_LABEL","localized_variance":"DISTINCT_HYPOTHESIS","same_expression_different_results":"MUTUALLY_EXCLUSIVE_LABEL"} | 1.0 | 791 | interpretation-only labels; no branch BH | defer or register a separate statistic before making public |
| session_drift | ["opening_game_signature","gradual_session_drift","predeclared_breakpoint","selection_only_drift","bounded_stopping_response"] | {"bounded_stopping_response":"DISTINCT_HYPOTHESIS","gradual_session_drift":"DISTINCT_HYPOTHESIS","opening_game_signature":"DISTINCT_HYPOTHESIS","predeclared_breakpoint":"DISTINCT_HYPOTHESIS","selection_only_drift":"DISTINCT_HYPOTHESIS"} | 1.0 | 791 | interpretation-only labels; no branch BH | defer or register a separate statistic before making public |

## Publication-gate audit

| gate | declared | computed | enforced | source | failure_code_today | new_candidate |
| --- | --- | --- | --- | --- | --- | --- |
| structural eligibility | True | True | PARTIAL | dna_assembly_v6 + canonical history audit | data_eligibility / history_not_complete | True |
| opportunity minimum | True | True | False | semantic_outcomes registry; estimators | not a final publication boolean | True |
| minimum support | True | True | False | registry + diagnostic trace | minimum_support (diagnostic only) | True |
| estimator validity | True | True | PARTIAL | artifacts.py + family_statistics.py | invalid/empty evidence fails closed inconsistently | True |
| practical effect | True | True | False | semantic calibration ropes; estimators | effect recorded only | True |
| equivalence/ROPE | True | True | False | production_statistics.interval_inside_rope + family statistics | equivalence recorded only | True |
| family uncertainty | True | True | PARTIAL | production_statistics + semantic_statistics | p-value path is invalid | True |
| family statistical qualification | True | True | True | hierarchical_qualification | family_q | True |
| family multiplicity correction | True | True | True | benjamini_hochberg_five | fixed_m=5 | True |
| branch determination | True | True | True | dna_assembly_v61._semantic_key | semantic_key fallback | True |
| branch statistical qualification | True | True | True | hierarchical_qualification | branch_q | False |
| branch multiplicity correction | True | True | True | hierarchical_qualification._benjamini_hochberg | branch evidence duplicated | False |
| stability | True | True | False | base finding bootstrap_stability | recorded_only | True |
| robustness | True | True | False | semantic registry + estimator audits | recorded_only | True |
| confounder safety | True | False | False | no explicit final selection boolean | not_implemented | True |
| semantic evidence completeness | True | True | False | semantic bootstrap availability | semantic_evidence | True |
| rollout/public-candidate status | True | True | True | SEMANTIC_OUTCOME_REGISTRY | not_public_candidate | True |
| history completeness | True | True | POOL_ONLY | dna_assembly_v61:1258-1260 | history_not_complete | True |
| maximum-findings product cap | True | True | True | dna_assembly_v61:1257 | finding_cap | True |
| inherited V6 publication | True | True | True | dna_assembly_v61:1256 | inherited_v6_publication_gate | False |

## Family statistical specifications

| family | estimand | null | opportunities | sessions | current source | correct source | uncertainty | publication |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pool Shape | Delta_pool = signed predeclared contrast between hero breadth/chronological JSD and match-weighted job/toolkit shape; candidate v1 uses hero_JSD - job_JSD as the scalar omnibus. | H0: Delta_pool = 0. | 30 | 12 | semantic_statistics.families.pool_shape = breadth - toolkit | portfolio_shape breadth/toolkit and predeclared chronological shape contrast, recomputed on each session resample | Corrected null-centered two-sided cluster-bootstrap p plus percentile 95% CI, B=2,000; pass point and observed statistic separately. | Publish only the retained scalar outcome after the state machine; V6 published is not a prerequisite. |
| Transfer | Delta_transfer,k = mean(component_k \| reliable_stretch) - mean(component_k \| core), k in {outcome, activity, survival}; candidate omnibus is the maximum predeclared standardized component departure. | H0: all Delta_transfer,k are 0 within the predeclared component ropes. | 30 | 12 | semantic_statistics.families.transfer = transfer frontier score | continuous_transfer component deltas from core/reliable_stretch, recomputed by session cluster | Corrected null-centered max-component bootstrap p plus component percentile CIs; separate CI-inside-ROPE decision for compatibility. | Publish one transfer family outcome only after the family state is Qualified and a deterministic label has complete component evidence. |
| Post-Loss Response | Delta_response = max_s,s' \|mean(movement \| state=s) - mean(movement \| state=s')\| over the predeclared state contrast set; no cross-session transitions. | H0: all predeclared supported result-state movement means are equal. | 30 | 12 | semantic_statistics.families.post_loss_response = finishing (incorrect) | result_response_summary transition movements rebuilt from each resampled session | Corrected null-centered max-contrast session bootstrap p plus state-specific percentile CIs; TOST/ROPE only for the invariant label. | Publish one bounded result-state claim only after corrected source mapping and the complete state machine pass. |
| Combat Expression | Delta_combat = predeclared discordance between context-adjusted involvement, death exposure, and outcome components; candidate v1 uses max absolute standardized component contrast. | H0: the covered combat components move together within their practical margins. | 30 | 12 | semantic_statistics.families.combat_expression = involvement - death_exposure | context-adjusted involvement/death-exposure/outcome component vector, recomputed by session | Corrected null-centered max-component bootstrap p plus component CIs; no separate p for deterministic relationship labels. | Publish a single bounded component relationship after the state machine; do not derive it from Element zones in a client. |
| Session Drift | Delta_session = max_g,g' \|mean(expression at position g) - mean(expression at position g')\| over the predeclared G1-G5+ position set. | H0: the direct completed-session position curve is compatible across all predeclared positions. | 30 | 12 | semantic_statistics.families.session_drift = consistency (incorrect) | session_position_curve direct G1-G5+ positions, recomputed from completed sessions | Corrected null-centered max-position-contrast bootstrap p plus position-specific CIs; no raw match independence assumption. | Publish one direct position-curve claim only after completion wiring and direct bootstrap evidence are implemented and validated. |

The complete field-by-field specification is the `family_specifications.json` output and is repeated in the implementation prompt; no future worker is asked to choose an estimator, threshold, or multiplicity rule.

## Candidate inferential methods

| family | method | statistically_valid | tests_intended_estimand | handles_clustering | multiplicity_compatible | verdict | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pool_shape | corrected_null_centered_bootstrap | True | True | True | True | RECOMMEND | Corrects the null-centering defect while retaining the existing session-cluster design; family p can enter fixed five-family BH. |
| pool_shape | ci_practical_effect | True | True | True | False | VIABLE_ALTERNATIVE | Good semantic publication gate, but percentile CIs alone do not provide the chosen cross-family FDR control without a simultaneous-interval calibration. |
| pool_shape | rope_equivalence | False | False | True | only with a predeclared equivalence family test | NOT_APPLICABLE | Use only for claims whose meaning is compatibility/equivalence; it is not the omnibus primitive for a directional family. |
| pool_shape | permutation_randomization | False | False | False | False | REJECT | The observational summary history supplies no randomized treatment or exchangeability that would justify a permutation null; result states and hero bands are selected, not randomized. |
| transfer | corrected_null_centered_bootstrap | True | True | True | True | RECOMMEND | Corrects the null-centering defect while retaining the existing session-cluster design; family p can enter fixed five-family BH. |
| transfer | ci_practical_effect | True | True | True | False | VIABLE_ALTERNATIVE | Good semantic publication gate, but percentile CIs alone do not provide the chosen cross-family FDR control without a simultaneous-interval calibration. |
| transfer | rope_equivalence | True | True | True | only with a predeclared equivalence family test | VIABLE_ALTERNATIVE | Use only for claims whose meaning is compatibility/equivalence; it is not the omnibus primitive for a directional family. |
| transfer | permutation_randomization | False | False | False | False | REJECT | The observational summary history supplies no randomized treatment or exchangeability that would justify a permutation null; result states and hero bands are selected, not randomized. |
| post_loss_response | corrected_null_centered_bootstrap | True | True | True | True | RECOMMEND | Corrects the null-centering defect while retaining the existing session-cluster design; family p can enter fixed five-family BH. |
| post_loss_response | ci_practical_effect | True | True | True | False | VIABLE_ALTERNATIVE | Good semantic publication gate, but percentile CIs alone do not provide the chosen cross-family FDR control without a simultaneous-interval calibration. |
| post_loss_response | rope_equivalence | True | True | True | only with a predeclared equivalence family test | VIABLE_ALTERNATIVE | Use only for claims whose meaning is compatibility/equivalence; it is not the omnibus primitive for a directional family. |
| post_loss_response | permutation_randomization | False | False | False | False | REJECT | The observational summary history supplies no randomized treatment or exchangeability that would justify a permutation null; result states and hero bands are selected, not randomized. |
| combat_expression | corrected_null_centered_bootstrap | True | True | True | True | RECOMMEND | Corrects the null-centering defect while retaining the existing session-cluster design; family p can enter fixed five-family BH. |
| combat_expression | ci_practical_effect | True | True | True | False | VIABLE_ALTERNATIVE | Good semantic publication gate, but percentile CIs alone do not provide the chosen cross-family FDR control without a simultaneous-interval calibration. |
| combat_expression | rope_equivalence | True | True | True | only with a predeclared equivalence family test | VIABLE_ALTERNATIVE | Use only for claims whose meaning is compatibility/equivalence; it is not the omnibus primitive for a directional family. |
| combat_expression | permutation_randomization | False | False | False | False | REJECT | The observational summary history supplies no randomized treatment or exchangeability that would justify a permutation null; result states and hero bands are selected, not randomized. |
| session_drift | corrected_null_centered_bootstrap | True | True | True | True | RECOMMEND | Corrects the null-centering defect while retaining the existing session-cluster design; family p can enter fixed five-family BH. |
| session_drift | ci_practical_effect | True | True | True | False | VIABLE_ALTERNATIVE | Good semantic publication gate, but percentile CIs alone do not provide the chosen cross-family FDR control without a simultaneous-interval calibration. |
| session_drift | rope_equivalence | True | True | True | only with a predeclared equivalence family test | VIABLE_ALTERNATIVE | Use only for claims whose meaning is compatibility/equivalence; it is not the omnibus primitive for a directional family. |
| session_drift | permutation_randomization | False | False | False | False | REJECT | The observational summary history supplies no randomized treatment or exchangeability that would justify a permutation null; result states and hero bands are selected, not randomized. |

## Synthetic validity results

| scenario | truth_class | false_positive_rate | power_or_detection_rate | ci_practical_effect_detection_rate | interval_coverage | degeneracy_rate | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| exact_null | null | 0.0 | 0.0 | 0.0 | 1.0 | 1.0 | PASS_EXPECTED_DEGENERACY |
| noisy_null | null | 0.1125 | 0.1125 | 0.0 | 0.875 | 0.0 | PASS_VALIDITY_SCREEN |
| clustered_null | null | 0.05 | 0.05 | 0.05 | 0.9375 | 0.0 | PASS_VALIDITY_SCREEN |
| unbalanced_cluster_sizes | null | 0.125 | 0.125 | 0.0 | 0.8625 | 0.0 | PASS_VALIDITY_SCREEN |
| heavy_tailed_null | null | 0.0625 | 0.0625 | 0.0 | 0.9 | 0.0 | PASS_VALIDITY_SCREEN |
| low_opportunity | null | 0.1625 | 0.1625 | 0.05 | 0.8125 | 0.0 | LIMITATION_LOW_SUPPORT |
| high_opportunity | null | 0.1 | 0.1 | 0.0 | 0.9 | 0.0 | PASS_VALIDITY_SCREEN |
| small_stable_effect | positive | None | 1.0 | 0.0 | 0.8875 | 0.0 | PASS_VALIDITY_SCREEN |
| moderate_stable_effect | positive | None | 1.0 | 1.0 | 0.9375 | 0.0 | PASS_VALIDITY_SCREEN |
| strong_stable_effect | positive | None | 1.0 | 1.0 | 0.925 | 0.0 | PASS_VALIDITY_SCREEN |
| one_direction_only | positive | None | 1.0 | 1.0 | 0.95 | 0.0 | PASS_VALIDITY_SCREEN |
| effect_flips_across_sessions | flip | None | 0.0 | 0.0 | 1.0 | 0.0 | PASS_VALIDITY_SCREEN |
| hero_role_context_confounder | confounded | None | 1.0 | 0.8375 | 0.0 | 0.0 | PASS_VALIDITY_SCREEN |

Synthetic controls use seed `20260827`, 80 repetitions, and 250 draws for a fast validity screen. The production specification remains B=2,000. No method with an obvious null pathology advances.

## Multiplicity architectures

| id | name | eligibility_rule | correction_method | branch_treatment | failure_modes | verdict |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | CURRENT_FIXED_FIVE_FAMILY_BH | All five p-values enter BH; unsupported families receive a fail-closed p=1 but remain in m=5. | Benjamini-Hochberg, m=5, q=0.05. | Branches are not independent tests in the recommended candidate; deterministic labels only. | A permanently unsupported family consumes one slot and reduces power; p-values must first be valid. | RECOMMEND |
| M2 | STRUCTURALLY_ELIGIBLE_FAMILY_BH | Support/evidence/history only; no p, effect, q, or branch outcome may enter eligibility. | BH over the eligible subset with profile-specific m. | No branch BH for interpretation-only labels. | Data-dependent filtering can invalidate nominal FDR and makes m vary by profile. | VIABLE_ALTERNATIVE |
| M3 | FAMILY_BH_PLUS_BRANCH_BH | Branches only after family qualification. | BH at family level then BH inside each qualified family. | Independent branch correction. | Current branches receive identical family evidence; branch q is decorative and can hide semantic mismatch. | REJECT_CURRENTLY |
| M4 | FAMILY_BH_ONLY | All five roots fixed; support/effect/semantic gates occur after valid family evidence and do not change m. | Fixed five-family BH on corrected family p-values. | One retained branch label per qualified family; no branch p/q. | Distinct future branches cannot be smuggled in as labels; they need a new statistic and correction. | RECOMMEND_WITH_M1 |
| M5 | OTHER | None. | None. | Not applicable. | Would defer the required architecture decision. | REJECT |

## Tuning-corpus comparison

| method | rows | support/evidence/effect candidates | note |
| --- | --- | --- | --- |
| corrected_null_centered_bootstrap | 3955 | 1927 | diagnostic only; future reliability and fresh holdout remain required |
| ci_practical_effect | 3955 | 1945 | diagnostic only; future reliability and fresh holdout remain required |
| rope_equivalence | 3955 | 751 | diagnostic only; future reliability and fresh holdout remain required |
| permutation_randomization | 3955 | 0 | diagnostic only; future reliability and fresh holdout remain required |

The profile-level comparison has one row per tuning profile × family × method × retained candidate branch. Counts are training-only diagnostics, not estimated precision or a target publication rate. The corrected-bootstrap rows use the enhanced trace's source-specific draw summaries; missing future reliability is a publication blocker.

## Reliability checks

| family | check | status | pass_rate_at_0_75 | pass_rate_at_0_80 | value | reason |
| --- | --- | --- | --- | --- | --- | --- |
| pool_shape | stored_runtime_bootstrap_stability | DIAGNOSTIC_ONLY | 0.5967130214917825 |  | 0.7341713021491783 | Current V6.1 stability field is evidence, not an enforced release gate. |
| pool_shape | sign_consistency_from_family_bootstrap_point | DIAGNOSTIC_ONLY |  | 0.843236409608091 | 0.843236409608091 | Computed from the current scalar semantic projection; not a substitute for split-half/LOSO evidence. |
| transfer | stored_runtime_bootstrap_stability | DIAGNOSTIC_ONLY | 0.45764854614412137 |  | 0.6809220640222892 | Current V6.1 stability field is evidence, not an enforced release gate. |
| transfer | sign_consistency_from_family_bootstrap_point | DIAGNOSTIC_ONLY |  | 1.0 | 1.0 | Computed from the current scalar semantic projection; not a substitute for split-half/LOSO evidence. |
| post_loss_response | stored_runtime_bootstrap_stability | DIAGNOSTIC_ONLY | 0.6687737041719343 |  | 0.8099047619047619 | Current V6.1 stability field is evidence, not an enforced release gate. |
| post_loss_response | sign_consistency_from_family_bootstrap_point | DIAGNOSTIC_ONLY |  | 1.0 | 1.0 | Computed from the current scalar semantic projection; not a substitute for split-half/LOSO evidence. |
| combat_expression | stored_runtime_bootstrap_stability | DIAGNOSTIC_ONLY | 0.5423514538558787 |  | 0.7775682680151708 | Current V6.1 stability field is evidence, not an enforced release gate. |
| combat_expression | sign_consistency_from_family_bootstrap_point | DIAGNOSTIC_ONLY |  | 0.5057179161372299 | 0.5057179161372299 | Computed from the current scalar semantic projection; not a substitute for split-half/LOSO evidence. |
| session_drift | stored_runtime_bootstrap_stability | DIAGNOSTIC_ONLY | 0.27054361567635904 |  | 0.6545404551201011 | Current V6.1 stability field is evidence, not an enforced release gate. |
| session_drift | sign_consistency_from_family_bootstrap_point | DIAGNOSTIC_ONLY |  | 1.0 | 1.0 | Computed from the current scalar semantic projection; not a substitute for split-half/LOSO evidence. |
| all | split_half_stability | NOT_RUN | None |  | None | Not available in the compact trace; future implementation must recompute family estimands on disjoint session halves. |
| all | leave_one_session_out | NOT_RUN | None |  | None | Not run because the current candidate trace intentionally stores no raw session identifiers or per-session estimates. |
| all | hero_stratification | NOT_RUN | None |  | None | Not selected from the current frozen trace; must be predeclared and run after direct family evidence is repaired. |
| all | role_stratification | NOT_RUN | None |  | None | Summary history coverage is insufficient for an unambiguous role-stratified causal interpretation. |
| all | early_late_window | NOT_RUN | None |  | None | A deeper window is not present; no >365-day comparison is possible without new collection. |
| all | negative_controls | NOT_RUN | None |  | None | Synthetic null controls pass the validity screen; observational negative-control labels are not available. |

What evidence suggests additional findings are not noise? The synthetic null/positive controls show the corrected statistic has the expected qualitative behavior, and current traces supply diagnostic stability/sign summaries. There is no independent truth label in the tuning corpus; split-half, leave-one-session-out, stratified, and fresh-holdout evidence therefore remain required.

## Family verdicts

| family | status | recommended_estimator | recommended_uncertainty_method | recommended_multiplicity | recommended_branch_model | opportunity_coverage | main_evidence | main_risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pool_shape | KEEP_FAMILY_REDEFINE_BRANCHES | corrected null-centered bootstrap | session-cluster bootstrap, B=2,000, corrected null-centered p and 95% CI | fixed five-family BH; no branch BH for interpretation labels | one scalar family contrast; old distinct branches deferred | {"profiles":791,"semantic_evidence_complete":791,"support_pass":780} | family evidence is broad but registered branches are different constructs | new source mapping and reliability gates need fresh validation; tuning data has no independent truth labels |
| transfer | KEEP_MEASUREMENT_CHANGE_INFERENCE | corrected max-component bootstrap + ROPE semantic gate | session-cluster bootstrap, B=2,000, corrected null-centered p and 95% CI | fixed five-family BH; no branch BH for interpretation labels | one frontier-change label; no branch BH | {"profiles":791,"semantic_evidence_complete":511,"support_pass":565} | measurement is aligned; branch evidence is duplicated | new source mapping and reliability gates need fresh validation; tuning data has no independent truth labels |
| post_loss_response | KEEP_MEASUREMENT_CHANGE_INFERENCE | direct transition max-contrast bootstrap | session-cluster bootstrap, B=2,000, corrected null-centered p and 95% CI | fixed five-family BH; no branch BH for interpretation labels | one supported state-contrast label; no branch BH | {"profiles":791,"semantic_evidence_complete":741,"support_pass":687} | direct transition measurement exists but current bootstrap source is finishing | new source mapping and reliability gates need fresh validation; tuning data has no independent truth labels |
| combat_expression | KEEP_FAMILY_REDEFINE_BRANCHES | corrected max-component bootstrap | session-cluster bootstrap, B=2,000, corrected null-centered p and 95% CI | fixed five-family BH; no branch BH for interpretation labels | one component-relationship label; localized variance deferred | {"profiles":791,"semantic_evidence_complete":741,"support_pass":780} | family source is aligned but current branch catalog mixes distinct claims | new source mapping and reliability gates need fresh validation; tuning data has no independent truth labels |
| session_drift | REDESIGN_MEASUREMENT | direct completed-session position max-contrast bootstrap | session-cluster bootstrap, B=2,000, corrected null-centered p and 95% CI | fixed five-family BH; no branch BH for interpretation labels | one position-curve label; breakpoint/stopping deferred | {"profiles":791,"semantic_evidence_complete":715,"support_pass":707} | current semantic source is consistency and completion/calibration support must be repaired | new source mapping and reliability gates need fresh validation; tuning data has no independent truth labels |

## V6 inheritance decision

**V6_MEASUREMENT_INPUT_ONLY.** The new candidate may reuse V6's report skeleton or measurement inputs where needed for compatibility, but an inherited V6 `finding.published` boolean must not veto a V6.1 candidate result.

## Recommended publication state machine

`NOT_STRUCTURALLY_ELIGIBLE → INSUFFICIENT_SUPPORT → ESTIMATOR_INVALID → NO_PRACTICAL_EFFECT → STATISTICALLY_UNQUALIFIED → UNSTABLE → CONFOUNDED → SEMANTIC_EVIDENCE_INCOMPLETE → QUALIFIED → PUBLISHABLE`; every terminal failure abstains, and the V6 publication flag is not a transition.

## Product finding budget

Recommend **max 3 qualified findings**, applied after analytical qualification as a product/display cap. It is not part of the statistical test; non-selected qualified material must not be relabeled as a stronger claim.

## Recommended analytical architecture

**POOL:** keep measurement, collapse to one predeclared portfolio-shape contrast; **TRANSFER:** keep measurement, corrected max-component frontier inference plus ROPE semantic gate; **POST_LOSS:** keep measurement, direct same-session transition max-contrast; **COMBAT:** keep measurement, corrected component-discordance statistic; **SESSION:** redesign the measurement path to use direct completed-session positions. All five use a corrected null-centered session-cluster bootstrap, fixed five-family BH at q=0.05, interpretation-only branch labels with no branch BH, V6 measurement inputs only, and the state machine above. This is a new analytical lineage.

## Why this architecture

1. It fixes the shared p-value mechanism before interpreting yield.
2. It uses each family's declared evidence source and clustering unit.
3. It stops duplicated branch evidence from masquerading as independent hypotheses.
4. It keeps multiplicity auditable with fixed m=5.
5. It turns support, effect, stability, confounder, and semantic completeness into real gates.
6. It preserves descriptive Elements/Hero Portfolio without weakening Findings.
7. It can be calibrated and tested exactly once on a future sealed holdout.

## Rejected alternatives

Fixed-q relaxation, branch-q relaxation, wider history, and a Suggestive tier are rejected for this pass because current p-values/source mappings are not valid enough to choose them. Structurally filtered BH is viable only after an independent-filtering argument; it is not the recommendation. Permutation testing is rejected because the summary history provides no randomized or exchangeable treatment assignment.

## Versioning impact

The work is documentation/diagnostic only and does not change the frozen V6.1 release. The future implementation must create a new analytical lineage and version at least the statistics, findings/semantic branch catalog, publication contract, and calibration/artifact manifest. It must not relabel changed estimates as `free-dna-model-6.1.0` or reuse the frozen holdout as validation.

## Calibration requirements

Use the 791-profile tuning partition only to fit new margins/ROPEs and check reproducibility. Predeclare the estimator, B=2,000 seed rule, family statistic, structural minima, practical margins, equivalence boundary, stability/robustness criteria, and state machine before selecting a new sealed holdout. The current artifact numbers are research starting references, not release validation.

## Fresh validation plan

`statistical spec freeze → implementation → unit tests → synthetic validity tests → tuning/calibration → reproducibility → negative controls → candidate artifact freeze → fresh sealed holdout selection → predeclared acceptance criteria → exactly-once holdout execution → product/content review → staging → owner-authorized production`. The existing 339-profile output is revealed/descriptive-only and cannot validate this candidate.

## Future implementation plan

See `docs/prompts/v61-findings-recovery-implementation.md`. It names exact modules/functions to change and to leave untouched, the estimator interfaces, source mapping, branch model, multiplicity, state machine, tests, firewalls, artifacts, and stop conditions.

## What evidence would change this recommendation?

A repaired candidate with valid branch/source evidence and fresh sealed validation showing acceptable FDR/precision could justify a different margin, a separately registered branch test, or a Suggestive tier. A deeper pre-existing corpus with materially higher completed-session/transition support could justify a history change. Neither condition is established here.

## What must NOT change yet

- current V6.1 thresholds, estimator, significance logic, or production publication path;
- frozen artifacts or source binding;
- current 365-day collection contract;
- protected holdout outputs or membership;
- production flags, database/Redis state, or deployment;
- any p/q result label based on the current invalid path;
- public Suggestive findings;
- analytical version metadata.

## Files created

Tracked: `scripts/v61_findings_statistical_recovery.py`, `scripts/v61_suppression_autopsy.py` (enhanced local trace summaries), `docs/evidence/free-dna-v6.1-findings-statistical-recovery-2026-08-27.md`, and `docs/prompts/v61-findings-recovery-implementation.md`. Local-only: `.local/diagnostics/v61-findings-statistical-recovery/` with the 15 requested outputs. Existing historical autopsy evidence was preserved.

## Integrity verification

- production untouched;
- frozen analytical source preserved: `7df38e6d234ae9c4ee425490bc40b8cc92685f85`;
- frozen artifact bundle preserved: `8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0`;
- protected holdout not rerun or used for selection;
- zero OpenDota/Steam/STRATZ collection;
- no recalibration, deployment, or merge to main;
- profile-level local outputs contain pseudonymous digests only.
