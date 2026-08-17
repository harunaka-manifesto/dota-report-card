# Elements

Elements are the 17 stable atomic measurements in free-elements-4.0.0. Public
IDs are assigned in registry order as E01–E17; internal keys are stable API
references.

| ID | Key | Label | Axis |
|---|---|---|---|
| E01 | hero_pool_breadth | Breadth | Focused → Wide |
| E02 | hero_pool_stability | Stability | Restless → Steady |
| E03 | hero_exploration_rate | Exploration | Comfort → Experimental |
| E04 | toolkit_breadth | Toolkit | Compact → Diverse |
| E05 | post_loss_familiarity_shift | Familiarity | Branches out → Comfort pick |
| E06 | role_breadth | Role | Anchored → Fluid |
| E07 | combat_involvement | Involvement | Quiet → Everywhere |
| E08 | finisher_orientation | Finishing | Setup → Cleanup |
| E09 | death_exposure | Deaths | Elusive → Frequent |
| E10 | off_pool_performance | Transfer | Falls off → Carries over |
| E11 | off_pool_activity_stability | Presence | Changes shape → Unchanged |
| E12 | performance_volatility | Volatility | Rock solid → Wild |
| E13 | recent_form_shift | Form | Sliding → Surging |
| E14 | recent_activity_shift | Pace | Quieter → Full tilt |
| E15 | session_length_tendency | Duration | Burst → Marathon |
| E16 | late_session_performance | Drift | Drops → Finishes strong |
| E17 | post_loss_activity_shift | Tempo | Pulls back → Accelerates |

Scores map into five reviewed zones. Availability requires the Element’s
summary fields, minimum sample, and coverage gates. Public output includes
status, score, centered score, confidence, sample size, coverage, zone,
receipts, confounders, and missing reasons.

Retired keys are signature_dependence, role_switch_rate, off_role_performance,
long_game_performance_shift, post_loss_performance_response, and
post_loss_death_shift. They are not aliases and are not emitted by v4.
