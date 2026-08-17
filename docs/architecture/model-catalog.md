# Free DNA model catalog

This is the owner-facing reference for the active Free model. It answers the
practical questions: what exists, what evidence each layer needs, and where a
Pattern can hand off to Deep Scan. The tables below are generated from the
production registries in `services/api/app/behavior`.

For the complete human-readable explanation of every Element, Pattern, and
context Archetype, see the [Free DNA model guide](free-dna-model-guide.md).

An Element is deliberately narrow. A Pattern is a finite reviewed relationship
between Elements. A context Archetype is one label chosen locally within a
registered group; it is not a global personality verdict. A missing or weak
Element can suppress a Pattern or leave an Archetype unclassified.

Run:

```bash
make dna-catalog       # refresh the generated tables
make dna-catalog-check # fail if the tables drift from code
```

<!-- BEGIN GENERATED MODEL CATALOG -->
## Registry versions

| Registry | Version | Active count |
| --- | --- | --- |
| Dimensions | dimensions-1.0.0 | 10 |
| Free Elements | free-elements-1.0.0 | 23 |
| Free Patterns | free-patterns-1.0.0 | 15 |
| Context Archetypes | free-archetypes-1.0.0 | 3 |

## Dimensions

| Key | Label | Question the layer answers |
| --- | --- | --- |
| hero_identity | Hero Identity | How hero choice and toolkit shape observable identity. |
| role_identity | Role Identity | How stable or varied credible role-context hints are. |
| combat_expression | Combat Expression | How often the player joins kill events and how those events are distributed. |
| economy | Economy | Farm, item timing, and resource conversion behavior. |
| map_objectives | Map & Objectives | Objective pressure, vision, and map movement. |
| risk_survival | Risk & Survival | Observable death exposure and survival context. |
| adaptability | Adaptability | How observable performance and activity transfer across contexts. |
| consistency_form | Consistency & Form | Variation and recent movement in observable performance and activity. |
| session_response | Session Response | Session shape and what changes as a session continues. |
| progression | Progression | Future change-over-time comparisons beyond the current bounded report. |

## Free Elements

| ID | Key | Dimension | Axis | Minimum sample | Coverage | Required capabilities |
| --- | --- | --- | --- | --- | --- | --- |
| E01 | hero_pool_breadth | hero_identity | Specialized → Broad | 30 | 0% | `summary.hero` |
| E02 | hero_pool_stability | hero_identity | Changing → Stable | 60 | 0% | `summary.hero`, `summary.chronology` |
| E03 | hero_exploration_rate | hero_identity | Familiar picks → Exploratory picks | 60 | 0% | `summary.hero`, `summary.chronology` |
| E04 | toolkit_breadth | hero_identity | Narrow toolkit → Diverse toolkit | 30 | 80% | `summary.hero`, `hero.taxonomy` |
| E05 | signature_dependence | hero_identity | Little dependence → High dependence | 30 | 0% | `summary.hero`, `summary.outcome`, `summary.chronology` |
| E06 | post_loss_familiarity_shift | hero_identity | Explores after losses → Returns to familiarity after losses | 30 | 0% | `summary.hero`, `summary.outcome`, `summary.chronology` |
| E07 | role_breadth | role_identity | Role-anchored → Role-flexible | 30 | 40% | `summary.role_hint` |
| E08 | role_switch_rate | role_identity | Usually same context → Frequently switches context | 20 | 0% | `summary.role_hint`, `summary.chronology` |
| E09 | combat_involvement | combat_expression | Lower involvement → Higher involvement | 30 | 0% | `summary.kda`, `summary.time` |
| E10 | finisher_orientation | combat_expression | Assist-oriented → Kill-oriented | 30 | 0% | `summary.kda` |
| E11 | death_exposure | risk_survival | Lower exposure → Higher exposure | 30 | 0% | `summary.kda`, `summary.time` |
| E12 | off_pool_performance | adaptability | Drops off-pool → Travels off-pool | 40 | 0% | `summary.hero`, `summary.outcome`, `summary.chronology` |
| E13 | off_pool_activity_stability | adaptability | Activity changes off-pool → Activity travels off-pool | 24 | 0% | `summary.hero`, `summary.kda`, `summary.time` |
| E14 | off_role_performance | adaptability | Drops off-role → Travels off-role | 24 | 50% | `summary.role_hint`, `summary.outcome`, `summary.chronology` |
| E15 | performance_volatility | consistency_form | Steadier → More variable | 30 | 0% | `summary.outcome`, `summary.kda`, `summary.time` |
| E16 | recent_form_shift | consistency_form | Recent decline → Recent improvement | 45 | 0% | `summary.outcome`, `summary.chronology` |
| E17 | recent_activity_shift | consistency_form | Recently less involved → Recently more involved | 45 | 0% | `summary.kda`, `summary.time`, `summary.chronology` |
| E18 | long_game_performance_shift | consistency_form | Falls in long games → Improves in long games | 20 | 0% | `summary.outcome`, `summary.time` |
| E19 | session_length_tendency | session_response | Short bursts → Long sessions | 25 | 0% | `summary.chronology`, `summary.time` |
| E20 | late_session_performance | session_response | Declines later → Improves later | 27 | 0% | `summary.chronology`, `summary.outcome`, `summary.time` |
| E21 | post_loss_performance_response | session_response | Lower after losses → Higher after losses | 30 | 0% | `summary.outcome`, `summary.chronology` |
| E22 | post_loss_activity_shift | session_response | Slower after losses → More active after losses | 30 | 0% | `summary.kda`, `summary.time`, `summary.outcome`, `summary.chronology` |
| E23 | post_loss_death_shift | session_response | Lower exposure after losses → Higher exposure after losses | 30 | 0% | `summary.kda`, `summary.time`, `summary.outcome`, `summary.chronology` |

## Free Patterns

| ID | Key | Kind | Required Elements | Optional Elements | Deep diagnostic handoff |
| --- | --- | --- | --- | --- | --- |
| P01 | broad_pool_narrow_toolkit | identity | `hero_pool_breadth`, `toolkit_breadth` | — | — |
| P02 | broad_pool_narrow_safety_zone | contradiction | `hero_pool_breadth`, `off_pool_performance` | `post_loss_familiarity_shift`, `signature_dependence` | — |
| P03 | specialist_transferable_style | identity | `hero_pool_breadth`, `off_pool_activity_stability` | `off_pool_performance` | — |
| P04 | role_anchor_hero_explorer | identity | `role_breadth`, `hero_pool_breadth` | — | — |
| P05 | hero_anchor_role_flex | identity | `hero_pool_breadth`, `role_breadth` | — | — |
| P06 | signature_strength_with_tax | leak | `signature_dependence`, `off_pool_performance` | `hero_exploration_rate` | — |
| P07 | activity_travels_better_than_results | contradiction | `off_pool_activity_stability`, `off_pool_performance` | — | `lane_efficiency`, `item_timing_reliability`, `teamfight_participation` |
| P08 | high_involvement_controlled_exposure | style | `combat_involvement`, `death_exposure` | — | — |
| P09 | high_involvement_high_exposure | style | `combat_involvement`, `death_exposure` | `post_loss_death_shift` | `death_cost`, `teamfight_participation` |
| P10 | selective_finisher | style | `combat_involvement`, `finisher_orientation`, `death_exposure` | — | — |
| P11 | losses_change_picks_more_than_pace | trajectory | `post_loss_familiarity_shift`, `post_loss_activity_shift` | `post_loss_performance_response` | — |
| P12 | losses_change_pace_more_than_picks | trajectory | `post_loss_familiarity_shift`, `post_loss_activity_shift` | `post_loss_death_shift` | — |
| P13 | long_session_tax | leak | `session_length_tendency`, `late_session_performance` | `post_loss_performance_response` | `advantage_protection` |
| P14 | marathon_stability | edge | `session_length_tendency`, `late_session_performance` | — | — |
| P15 | form_identity_divergence | trajectory | `recent_form_shift`, `hero_pool_stability`, `recent_activity_shift` | — | — |

## Context Archetype groups

| Group | Required Elements | Optional Patterns | Finite labels |
| --- | --- | --- | --- |
| hero_identity | `hero_pool_breadth`, `hero_pool_stability`, `hero_exploration_rate` | `broad_pool_narrow_toolkit`, `specialist_transferable_style`, `activity_travels_better_than_results` | `specialist — Specialist`, `craftsman — Craftsman`, `explorer — Explorer`, `adapter — Adapter`, `free_agent — Free Agent` |
| combat_expression | `combat_involvement`, `finisher_orientation`, `death_exposure` | `high_involvement_controlled_exposure`, `high_involvement_high_exposure`, `selective_finisher` | `skirmisher — Skirmisher`, `enabler — Enabler`, `selective_finisher — Selective Finisher`, `connector — Connector`, `balanced — Balanced` |
| session_style | `session_length_tendency`, `late_session_performance` | `long_session_tax`, `marathon_stability`, `losses_change_picks_more_than_pace` | `sprinter — Sprinter`, `grinder — Grinder`, `second_wind — Second Wind`, `front_loaded — Front-Loaded`, `reset_player — Reset Player`, `even_keel — Even-Keel` |

## Product tier

| Tier | Active model surface | Evidence boundary |
| --- | --- | --- |
| Free | 23 Elements · 15 Patterns · 3 context groups | One bounded summary-history read; no match-detail or replay-parse reads |
| Deep Scan | Selected-match diagnostic families are a separate handoff | Explicit opt-in, bounded detail reads, and coverage gates |
<!-- END GENERATED MODEL CATALOG -->

## Copy guardrails

- Describe observable match behavior and name the comparison being made.
- Keep interpretation separate from receipt values.
- Use “can”, “suggests”, or “is consistent with” when the evidence is limited.
- Do not turn a session or post-loss shift into a claim about mood, intent, or
  character.
- Keep Deep Scan questions as questions. Summary history cannot answer them by
  implication.
