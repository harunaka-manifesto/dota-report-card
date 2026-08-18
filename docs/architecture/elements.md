# Elements

Elements are the 17 public atomic measurements in `free-elements-4.0.0`. They
are descriptive signals, not player types. Every result carries status,
confidence, sample size, coverage, zone, receipts, confounders, and missing
reasons. A field that does not clear its sample or coverage gate remains
`limited` or `unavailable`; it is never filled with a neutral guess.

## Shared measurement contract

- Scores are normalized to a bounded 0–1 value and mapped to five reviewed
  zones. The public zone is the interpretation surface; the raw score stays
  secondary evidence.
- `minimum_sample` is the minimum usable row count for the Element. A
  comparison Element may additionally need both sides of its comparison.
- `minimum_coverage` is the minimum share of the bounded history with the
  required fields. A zero means the Element still has its own row-level
  validity checks.
- Receipts expose the source summary field and unit used by the score. They do
  not expose raw rows or match IDs in the public report.
- All 17 are Free summary-history measurements. Deep Scan is a separate,
  opt-in match-detail surface; it does not silently upgrade a Free Element.

## Owner catalog

The `Patterns` column names every active Free Pattern that consumes the
Element, either as a required gate or as a modifier. “None” is intentional:
an Element can be useful in the Element view without being a current Pattern
ingredient.

| ID / public label | Internal key | Human meaning and why it exists | Source fields and score basis | Reviewed zones | Minimum / coverage | Limitations and confounders | Patterns | Surface / version |
|---|---|---|---|---|---|---|---|---|
| E01 · Breadth | `hero_pool_breadth` | How wide the meaningful hero pool is. Separates a genuinely broad established pool from a long tail of one-off picks. | Summary hero counts and concentration; bounded absolute breadth score. | Focused · Selective · Mixed · Varied · Wide | 30 / 0% | Hero availability and patch changes can shape the pool. | Same Playbook, Comfort Edge, Versatile Core, Proven Flexibility | Free summary · `free-elements-4.0.0` |
| E02 · Stability | `hero_pool_stability` | How settled versus shifting the pool is over time. Supplies the time context for Stable Style. | Dated hero distribution across comparison windows; window-comparison score. | Restless · Shifting · Mixed · Settled · Steady | 60 / 0% | Patches, hero releases, and the bounded history window can move the distribution. | Stable Style | Free summary · `free-elements-4.0.0` |
| E03 · Exploration | `hero_exploration_rate` | How often new or unfamiliar heroes enter the pool. Keeps novelty separate from breadth. | Dated hero familiarity and entry transitions; conditional-comparison score. | Comfort · Familiar · Open · Curious · Experimental | 60 / 0% | A short recent window can make exploration look larger than it is. | Comfort Edge (modifier) | Free summary · `free-elements-4.0.0` |
| E04 · Toolkit | `toolkit_breadth` | How varied the Dota jobs underneath the picks are. Explains why a focused or broad hero list may still cover different work. | Versioned hero taxonomy toolkit signatures and entropy; bounded absolute score. | Compact · Focused · Mixed · Versatile · Diverse | 30 / 80% | Taxonomy labels are editorial and versioned; insufficient taxonomy coverage is unavailable. | Same Playbook, Versatile Core | Free summary · `free-elements-4.0.0` |
| E05 · Familiarity | `post_loss_familiarity_shift` | Where hero choice moves after a loss. Makes the observable next-pick transition explicit without naming a motive. | Summary outcome, hero familiarity, and valid chronological transitions; conditional-comparison score. | Branches out · Explores · Unchanged · Returns · Comfort pick | 30 / 0% | Session gaps and stopping behavior affect valid transitions. | Comfort Edge (modifier), Loss Response | Free summary · `free-elements-4.0.0` |
| E06 · Role | `role_breadth` | How broad the credible role contexts are. Prevents role context from being mistaken for seven independent behavior scores. | Summary lane/role hints and their credible distribution; bounded breadth score. | Anchored · Centered · Mixed · Flexible · Fluid | 30 / 40% | Lane-role values are hints, not exact position labels. | None in the active Free Pattern registry | Free summary · `free-elements-4.0.0` |
| E07 · Involvement | `combat_involvement` | How frequently the player appears in kill events per time. Provides an interpretable activity rate. | Kills plus assists divided by match minutes; events-per-minute normalization. | Quiet · Selective · Present · Active · Everywhere | 30 / 0% | Team tempo and hero style affect involvement rate. | Selective Closer, Controlled Presence, Heavy Exposure, Assist Presence | Free summary · `free-elements-4.0.0` |
| E08 · Finishing | `finisher_orientation` | How involvement splits between final kill credit and assists. Separates finishing expression from total presence. | Kills divided by kills plus assists, with an explicit zero-event guard; finishing-share normalization. | Setup · Support · Split · Closer · Cleanup | 30 / 0% | Team kill totals and role mix are only partly visible in summary history. | Selective Closer, Assist Presence; Controlled Presence and Heavy Exposure modifiers | Free summary · `free-elements-4.0.0` |
| E09 · Deaths | `death_exposure` | How exposed the player is to deaths per unit of time. Keeps risk language tied to a rate rather than a raw count. | Deaths divided by match minutes, reported as deaths per 10 minutes; rate normalization. | Elusive · Safe · Mixed · Exposed · Frequent | 30 / 0% | Some heroes and role contexts structurally trade deaths for map value. | Controlled Presence, Heavy Exposure; Selective Closer and Assist Presence modifiers | Free summary · `free-elements-4.0.0` |
| E10 · Transfer | `off_pool_performance` | Whether observable performance holds outside the familiar pool. Shows transfer without claiming skill in an abstract sense. | Familiar versus off-pool outcome proxy and valid comparison cells; conditional-comparison score. | Falls off · Slips · Holds · Travels · Carries over | 40 / 0% | Patch, draft quality, and hero learning can differ between windows. | Comfort Edge, Partial Transfer, Proven Flexibility | Free summary · `free-elements-4.0.0` |
| E11 · Presence | `off_pool_activity_stability` | Whether combat activity holds outside the familiar pool. Distinguishes disappearing from fights from a result-only change. | Familiar versus off-pool events-per-minute cells; self-relative comparison score. | Changes shape · Shifts · Similar · Holds · Unchanged | 24 / 0% | Role and game tempo can change with hero choice. | Partial Transfer | Free summary · `free-elements-4.0.0` |
| E12 · Volatility | `performance_volatility` | How variable the observable performance proxy is match to match. Makes consistency a measured spread, not a personality claim. | Summary outcome/KDA/time performance proxy and robust spread; self-relative variability score. | Rock solid · Steady · Variable · Swingy · Wild | 30 / 0% | The proxy is not a full performance model. | None in the active Free Pattern registry | Free summary · `free-elements-4.0.0` |
| E13 · Form | `recent_form_shift` | How recent observable form moved against an earlier window. Separates current movement from style identity. | Dated outcome proxy in balanced recent/prior windows; window-comparison delta. | Sliding · Cooling · Flat · Rising · Surging | 45 / 0% | Recent opponents, patches, and hero mix are not controlled. | Stable Style | Free summary · `free-elements-4.0.0` |
| E14 · Pace | `recent_activity_shift` | How recent combat activity moved against an earlier window. Gives Stable Style a second, independent style signal. | Events per minute in dated comparison windows; window-comparison delta. | Quieter · Calmer · Same · Busier · Full tilt | 45 / 0% | Team tempo and role mix may differ between windows. | Stable Style | Free summary · `free-elements-4.0.0` |
| E15 · Duration | `session_length_tendency` | What session length tends to appear. Provides the long-session context for drift Patterns. | Chronological session grouping, matches per session, and session duration; bounded tendency score. | Burst · Short · Medium · Long · Marathon | 25 / 0% | The history limit can truncate a session boundary. | Session Fade, Session Rise, Session Hold | Free summary · `free-elements-4.0.0` |
| E16 · Drift | `late_session_performance` | What happens to results later in a session. Describes repeated late-session movement without claiming fatigue or warm-up. | Session position and outcome proxy in early/late cells; window-comparison score. | Drops · Fades · Holds · Warms up · Finishes strong | 27 / 0% | Stopping behavior and role mix can confound session position. | Session Fade, Session Rise, Session Hold | Free summary · `free-elements-4.0.0` |
| E17 · Tempo | `post_loss_activity_shift` | How next-game activity moves after a loss. Complements Familiarity for observable loss-response variants. | Outcome transitions, next-game events per minute, and valid chronology; conditional-comparison score. | Pulls back · Quieter · Same · Speeds up · Accelerates | 30 / 0% | A next match may have a different role or team tempo. | Loss Response | Free summary · `free-elements-4.0.0` |

## Public safety boundary

The report can say that an Element landed in a zone under a stated sample and
coverage boundary. It cannot say why the pattern occurred, diagnose a player,
assign a grade, or treat a summary proxy as a complete performance model.
Retired keys are not aliases and are not emitted by v4: `signature_dependence`,
`role_switch_rate`, `off_role_performance`, `long_game_performance_shift`,
`post_loss_performance_response`, and `post_loss_death_shift`.
