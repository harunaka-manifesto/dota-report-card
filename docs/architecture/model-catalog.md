# Free DNA model catalog

This file is the generated owner-facing registry reference. It is refreshed by
`make dna-catalog` from the production Element and Pattern registries.

The human-readable model decisions live in [Elements](elements.md),
[Patterns](patterns.md), and [Hero Portfolio](hero-portfolio.md).

<!-- BEGIN GENERATED MODEL CATALOG -->
## Registry versions

| Registry | Version | Active count |
| --- | --- | --- |
| Free Elements | free-elements-4.0.0 | 17 |
| Free Patterns | free-patterns-4.0.0 | 14 |

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

## Free Patterns

| ID | Key | Family | Tier | Required Elements | Modifier Elements |
| --- | --- | --- | --- | --- | --- |
| P01 | same_playbook | breadth_toolkit | A | `hero_pool_breadth`, `toolkit_breadth` | — |
| P02 | comfort_edge | breadth_transfer | A | `hero_pool_breadth`, `off_pool_performance` | `hero_exploration_rate`, `post_loss_familiarity_shift` |
| P03 | partial_transfer | presence_transfer | A | `off_pool_activity_stability`, `off_pool_performance` | — |
| P04 | stable_style | form_stability | A | `recent_form_shift`, `hero_pool_stability`, `recent_activity_shift` | — |
| P05 | versatile_core | breadth_toolkit | A | `hero_pool_breadth`, `toolkit_breadth` | — |
| P06 | proven_flexibility | breadth_transfer | A | `hero_pool_breadth`, `off_pool_performance` | — |
| P07 | selective_closer | involvement_finishing | B | `combat_involvement`, `finisher_orientation` | `death_exposure` |
| P08 | loss_response | post_loss | B | `post_loss_familiarity_shift`, `post_loss_activity_shift` | — |
| P09 | controlled_presence | involvement_deaths | B | `combat_involvement`, `death_exposure` | `finisher_orientation` |
| P10 | heavy_exposure | involvement_deaths | B | `combat_involvement`, `death_exposure` | `finisher_orientation` |
| P11 | session_fade | session_drift | B | `session_length_tendency`, `late_session_performance` | — |
| P12 | session_rise | session_drift | B | `session_length_tendency`, `late_session_performance` | — |
| P13 | session_hold | session_drift | B | `session_length_tendency`, `late_session_performance` | — |
| P14 | assist_presence | involvement_finishing | B | `combat_involvement`, `finisher_orientation` | `death_exposure` |

## Product tier

| Tier | Active model surface | Evidence boundary |
| --- | --- | --- |
| Free | 17 Elements · 14 Patterns · Hero Portfolio | One bounded summary-history read; no match-detail or replay-parse reads |
| Deep Scan | Explicit selected-match analysis | Separate opt-in budgets and coverage gates |
<!-- END GENERATED MODEL CATALOG -->

## Copy and safety guardrails

- Describe observable match behavior and name the comparison being made.
- Keep interpretation separate from receipt values.
- Preserve unavailable and no-clear states.
- Never imply motive, intent, diagnosis, grade, or causality from summary rows.
