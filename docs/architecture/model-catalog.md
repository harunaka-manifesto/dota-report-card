# Free DNA model catalog

This file is the generated owner-facing registry reference. It is refreshed by
`make dna-catalog` from the production Element and Pattern registries.

The human-readable model decisions live in [Elements](elements.md),
[Patterns](patterns.md), and [Hero Portfolio](hero-portfolio.md).

<!-- BEGIN GENERATED MODEL CATALOG -->
## Registry versions

| Registry | Version | Active count |
| --- | --- | --- |
| Free Elements | free-elements-5.2.0 | 18 |
| Free Patterns | free-patterns-5.1.0 | 11 |
| V6.1 public Elements | free-elements-6.1.0 | 7 |
| V6.1 family roots | free-findings-6.1.0 | 5 |
| V6.1 supporting signals | supporting-signals-1.0.0 | 128 |
| V6.1 semantic outcomes | semantic-outcomes-1.0.0 | 28 |

## Free Elements

| ID | Key | Label | Axis | Minimum sample | Coverage |
| --- | --- | --- | --- | --- | --- |
| E01 | hero_pool_breadth | Breadth | Focused → Wide | 30 | 0% |
| E02 | hero_pool_stability | Stability | Restless → Steady | 60 | 0% |
| E03 | hero_exploration_rate | Exploration | Comfort → Experimental | 60 | 0% |
| E04 | toolkit_breadth | Toolkit | Compact → Diverse | 30 | 80% |
| E05 | post_loss_familiarity_shift | Familiarity | Branches out → Comfort pick | 30 | 0% |
| E06 | role_breadth | Role | Anchored → Fluid | 30 | 40% |
| E07 | combat_involvement | Involvement | Quiet → Everywhere | 30 | 0% |
| E08 | finisher_orientation | Finishing | Setup → Cleanup | 30 | 0% |
| E09 | death_exposure | Deaths | Elusive → Frequent | 30 | 0% |
| E10 | off_pool_performance | Transfer | Falls off → Carries over | 40 | 0% |
| E11 | off_pool_activity_stability | Presence | Changes shape → Unchanged | 24 | 0% |
| E12 | performance_volatility | Volatility | Rock solid → Wild | 30 | 0% |
| E13 | recent_form_shift | Form | Sliding → Surging | 45 | 0% |
| E14 | recent_activity_shift | Pace | Quieter → Full tilt | 45 | 0% |
| E15 | session_length_tendency | Duration | Burst → Marathon | 25 | 0% |
| E16 | late_session_performance | Drift | Drops → Finishes strong | 27 | 0% |
| E17 | post_loss_activity_shift | Tempo | Pulls back → Accelerates | 30 | 0% |
| E18 | post_loss_performance_response | Recovery | Drops → Surges | 30 | 0% |

## Free Patterns

| ID | Key | Family | Tier | Required Elements | Modifier Elements |
| --- | --- | --- | --- | --- | --- |
| P01 | same_playbook | breadth_toolkit | A | `hero_pool_breadth`, `toolkit_breadth` | — |
| P02 | comfort_edge | breadth_transfer | A | `hero_pool_breadth`, `off_pool_performance` | `hero_exploration_rate`, `post_loss_familiarity_shift` |
| P03 | partial_transfer | presence_transfer | A | `off_pool_activity_stability`, `off_pool_performance` | — |
| P04 | versatile_core | breadth_toolkit | A | `hero_pool_breadth`, `toolkit_breadth` | — |
| P05 | proven_flexibility | breadth_transfer | A | `hero_pool_breadth`, `off_pool_performance` | — |
| P06 | bounceback | post_loss_recovery | B | `post_loss_performance_response`, `post_loss_familiarity_shift`, `post_loss_activity_shift` | — |
| P07 | performance_slide | post_loss_recovery | B | `post_loss_performance_response`, `post_loss_familiarity_shift`, `post_loss_activity_shift` | — |
| P08 | controlled_presence | involvement_deaths | B | `combat_involvement`, `death_exposure` | `finisher_orientation` |
| P09 | presence_tax | involvement_deaths | B | `combat_involvement`, `death_exposure` | `finisher_orientation` |
| P10 | session_fade | session_drift | B | `session_length_tendency`, `late_session_performance` | — |
| P11 | session_rise | session_drift | B | `session_length_tendency`, `late_session_performance` | — |

## Active V6.1 public ontology

Supporting signals below are evidence and never additional public score cards.

| Public Elements (7) | Family roots (5) |
| --- | --- |
| `breadth` | `pool_shape` |
| `toolkit` | `transfer` |
| `involvement` | `post_loss_response` |
| `finishing` | `combat_expression` |
| `death_exposure` | `session_drift` |
| `transfer` | — |
| `consistency` | — |

## V6.1 version matrix

| Surface | Version | Disposition | Compatibility |
| --- | --- | --- | --- |
| report | `free-dna-report-6.1.0` | changed | V6.0 remains validator-routed and immutable |
| model | `free-dna-model-6.1.0` | changed | new generation selector only |
| elements | `free-elements-6.1.0` | changed | same seven ordered public keys |
| findings | `free-findings-6.1.0` | changed | same five roots; nested outcomes |
| supporting_signals | `supporting-signals-1.0.0` | new | private graph; selected evidence only |
| semantic_outcomes | `semantic-outcomes-1.0.0` | new | frozen hierarchical registry |
| expression | `summary-expression-multisignal-2.0.0` | changed | V6.1 estimators only |
| statistics | `stats-cluster-bootstrap-2.0.0` | changed | recomputed/cross-fitted estimators |
| context_baseline | `context-baseline-3.0.0` | changed | V6.1 artifact schema |
| thresholds | `metric-thresholds-6.1.0` | changed | registry-key manifest |
| claims | `claim-contract-2.0.0` | changed | alternatives and verification added |
| story | `free-story-6.1.0` | changed | same nine beats; interaction-aware payload |
| copy | `free-dna-semantic-copy-6.1.0` | changed | outcome-owned deterministic copy |
| recommendations | `free-dna-recommendations-6.1.0` | changed | five-game verification contract |
| deep_diagnostics | `deep-diagnostics-2.1.0` | changed | protected qualifying cohort references |
| share_renderer | `share-svg-6.1.0` | changed | semantic cards gated separately |
| interactions | `report-interactions-1.1.0` | changed | additive kinds; old sessions readable |
| summary_history | `summary-history-schema-3.0.0` | new | one physical request contract |

## V6.1 semantic outcomes

| Family | Branch | Outcome key | Denominator | Rollout | Interaction |
| --- | --- | --- | --- | --- | --- |
| pool_shape | shape | `hidden_center` | matches | public_candidate | contradiction_reveal |
| pool_shape | name_job | `names_wide_jobs_narrow` | matches | public_candidate | contradiction_reveal |
| pool_shape | name_job | `names_narrow_jobs_wide` | matches | public_candidate | contradiction_reveal |
| pool_shape | migration | `names_changed_jobs_held` | matches | public_candidate | contradiction_reveal |
| transfer | frontier | `clean_transfer` | matches | public_candidate | core_boundary |
| transfer | component_frontier | `results_stop_first` | matches | public_candidate | two_versions |
| transfer | component_frontier | `expression_stops_first` | matches | public_candidate | two_versions |
| transfer | component_frontier | `involvement_boundary` | matches | public_candidate | core_boundary |
| transfer | component_frontier | `exposure_boundary` | matches | public_candidate | core_boundary |
| transfer | function | `localized_function_bottleneck` | matches | public_candidate | core_boundary |
| post_loss_response | result_state | `one_loss_runback` | transitions | public_candidate | after_x |
| post_loss_response | streak_state | `two_loss_switch` | transitions | public_candidate | after_x |
| post_loss_response | bidirectional | `result_shaped_pool` | transitions | public_candidate | after_x |
| post_loss_response | equivalence | `result_invariant_response` | transitions | public_candidate | after_x |
| post_loss_response | chain | `adjustment_without_recovery` | transitions | public_candidate | after_x |
| combat_expression | conditional_expression | `involvement_holds_exposure_moves` | matches | public_candidate | two_versions |
| combat_expression | conditional_expression | `exposure_holds_involvement_moves` | matches | public_candidate | two_versions |
| combat_expression | result_expression | `same_expression_different_results` | matches | public_candidate | two_versions |
| combat_expression | result_expression | `different_expression_same_results` | matches | public_candidate | two_versions |
| combat_expression | variance | `localized_variance` | matches | public_candidate | variance_decomposition |
| session_drift | position_curve | `opening_game_signature` | sessions | public_candidate | session_curve |
| session_drift | position_curve | `gradual_session_drift` | sessions | public_candidate | session_curve |
| session_drift | breakpoint | `predeclared_breakpoint` | sessions | public_candidate | session_curve |
| session_drift | selection | `selection_only_drift` | sessions | public_candidate | session_curve |
| session_drift | stopping | `bounded_stopping_response` | sessions | public_candidate | session_curve |
| pool_shape | lifecycle | `hero_lifecycle` | matches | shadow_only | hero_lifecycle |
| pool_shape | eras | `identity_eras` | matches | shadow_only | identity_eras |
| session_drift | motif | `behavioral_loop` | occurrences | shadow_only | behavioral_loop |

## V6.1 supporting-signal catalog

| Key | Class | Exposure | Denominator | Consumers | Rejected reason |
| --- | --- | --- | --- | --- | --- |
| `A01` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A02` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A03` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A04` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A05` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A06` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A07` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A08` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A09` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A10` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A11` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A12` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A13` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A14` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A15` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `A16` | PUBLIC_ELEMENT_SUPPORT | evidence_only | matches | `breadth`, `toolkit`, `involvement`, `finishing`, `death_exposure`, `transfer`, `consistency` | — |
| `X01` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X02` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X03` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X04` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X05` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X06` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X07` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X08` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X09` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X10` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X11` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X12` | SUPPORTING | evidence_only | matches | `involvement`, `death_exposure`, `combat_expression` | — |
| `X13` | REJECTED | never | matches | `calibration` | actual role cannot be inferred from sparse summary lane fields |
| `X14` | REJECTED | never | matches | `calibration` | positioning is unavailable in summary history |
| `X15` | REJECTED | never | matches | `calibration` | aggression or intent is not observable |
| `X16` | REJECTED | never | matches | `calibration` | death quality is not observable |
| `L01` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L02` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L03` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L04` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L05` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L06` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L07` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L08` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L09` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L10` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L11` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L12` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L13` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L14` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L15` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `L16` | LONGITUDINAL | named_when_qualified | sessions | `pool_shape`, `identity` | — |
| `T01` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T02` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T03` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T04` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T05` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T06` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T07` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T08` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T09` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T10` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T11` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T12` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T13` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T14` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T15` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `T16` | CONDITIONAL | named_when_qualified | transitions | `post_loss_response`, `transfer` | — |
| `Q01` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q02` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q03` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q04` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q05` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q06` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q07` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q08` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q09` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q10` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q11` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q12` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q13` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q14` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q15` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `Q16` | RESEARCH_ONLY | never | sessions | `calibration` | — |
| `P01` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P02` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P03` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P04` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P05` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P06` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P07` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P08` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P09` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P10` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P11` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P12` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P13` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P14` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P15` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `P16` | SUPPORTING | evidence_only | matches | `breadth`, `toolkit`, `pool_shape`, `transfer` | — |
| `C01` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C02` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C03` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C04` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C05` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C06` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C07` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C08` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C09` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C10` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C11` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C12` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C13` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C14` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C15` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `C16` | FINDING_ONLY | named_when_qualified | matches | `combat_expression`, `session_drift` | — |
| `M01` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M02` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M03` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M04` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M05` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M06` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M07` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M08` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M09` | REJECTED | never | matches | `calibration` | rank/MMR conditioning is forbidden |
| `M10` | REJECTED | never | matches | `calibration` | local time cannot be inferred from UTC and cluster |
| `M11` | REJECTED | never | matches | `calibration` | patch causality is not identifiable |
| `M12` | REJECTED | never | matches | `calibration` | final inventory is not item-build identity |
| `M13` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M14` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M15` | RESEARCH_ONLY | never | matches | `calibration` | — |
| `M16` | RESEARCH_ONLY | never | matches | `calibration` | — |

## Product tier

| Tier | Active model surface | Evidence boundary |
| --- | --- | --- |
| Free | 7 Elements · 5 family roots · zero to three Findings | One physical previous-365-day canonical summary-history read; no detail, parse, status, rank, or MMR dependency |
| Deep Scan | Explicit selected-match analysis | Separate opt-in budgets and coverage gates |
<!-- END GENERATED MODEL CATALOG -->

## Copy and safety guardrails

- Describe observable match behavior and name the comparison being made.
- Keep interpretation separate from receipt values.
- Preserve unavailable and no-clear states.
- Never imply motive, intent, diagnosis, grade, or causality from summary rows.
