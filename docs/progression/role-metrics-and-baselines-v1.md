> **Superseded.** Current rules are in [App Foundation](../tracker/app_foundation/SSOT.md); this document is historical evidence only.

# Role Metrics & Personal Baselines V1

Status: **SUPERSEDED**
Scope: Role Metrics & Personal Baselines V1
Last audited: 2026-09-12

This is the authoritative contract for role-based Dota match measurements,
personal role baselines, match-to-baseline comparisons, and Personal Bests
derived directly from those measurements. It is not the SSOT for ingestion,
role classification, persistence, mobile APIs, reports, subscriptions, or
presentation.

## 1. Purpose and authority

The feature answers:

> How did this match compare with how I usually perform in this role?

Over time it answers whether a player's measured performance in that role is
changing. It does not produce a universal performance score and it does not
produce judgments such as “great game,” “bad game,” “better decision making,”
or “you deserved to win.”

The authority order is:

1. explicit owner decisions in this SSOT and its change history;
2. the latest validated progression implementation;
3. validated metric/provider evidence;
4. tests;
5. older research and planning documents.

Older documents are evidence, not competing contracts. If code contradicts a
locked rule, the contradiction is recorded here and must be fixed or
explicitly re-decided; it must not be silently adopted.

### Audit boundary

The checked-out branch was `main` at `ed5f7acc77091625ccb3317b385df91038a60f91`.
It does not contain the reported progression module or validation evidence.
The latest candidate implementation inspected was the one-commit-ahead branch
`codex/backend-role-metric-contracts` at `d691008`. References below to the
“candidate implementation” mean that commit and are not claims that the code
is already on `main`.

The candidate implementation files are:

- `services/api/app/progression/role_metrics.py`;
- `services/api/app/stratz/queries.py` and `services/api/app/stratz/deep.py`;
- `tests/unit/test_progression_role_metrics.py`; and
- `docs/evidence/backend-role-metric-contract-validation-2026-09-12.md`.

The current branch therefore has a release/integration gap even where the
candidate status below says IMPLEMENTED or VALIDATED.

## 2. Feature scope

V1 has four player-facing progression roles:

| Role | Included positions | History identity |
|---|---|---|
| Carry | Position 1 | `carry + metric_id + metric_version` |
| Mid | Position 2 | `mid + metric_id + metric_version` |
| Offlane | Position 3 | `offlane + metric_id + metric_version` |
| Support | Positions 4 and 5 combined | `support + metric_id + metric_version` |

Position 4 and Position 5 are one Support track. Heroes never split a role
track: Luna Carry, Phantom Assassin Carry, and Slark Carry update the same
Carry history for the same metric definition version.

The active registry contains 20 V1 metrics: Carry 6, Mid 5, Offlane 4, and
Support 5. Support Control is unsupported and is not counted in that registry.

Status words used throughout this document:

- **LOCKED** — product meaning or rule is settled here.
- **IMPLEMENTED** — code exists in the inspected candidate implementation.
- **VALIDATED** — telemetry or behavior has supporting evidence/tests.
- **OPEN** — an owner decision or semantic contract is still unresolved.
- **UNSUPPORTED** — trusted telemetry cannot support the metric in V1.
- **DEFERRED** — intentionally in the V1 contract but not yet implemented.

## 3. Status and open-decision summary

Current implementation status is not complete:

| Area | `main` | Candidate branch `d691008` |
|---|---|---|
| Complete 20-metric registry | Not present | No; registry contains only five supported calculators plus the unsupported Control entry |
| Validated metric calculators | None on `main` | Support Healing, Support Fight Presence, Camps Stacked, Mid Early Fight Presence, Offlane Objective Involvement |
| Eligibility and role-isolated prior window | None on `main` | Implemented in memory: All Pick gate, role filter, prior-20 cap, current exclusion, five measured prior minimum |
| Baseline statistic | None on `main` | **CONTRACT CONFLICT:** candidate uses arithmetic mean (`fmean`), while this SSOT requires median |
| Persisted role histories | None | Not implemented |
| Personal Best persistence/rebuild | None | Only an in-memory comparison flag exists; no persisted PB engine |
| Role-correction recalculation | None | Not implemented |

The genuinely open decisions are kept small and explicit:

| Open decision | Why unresolved | Blocks which batch? | Recommended options |
|---|---|---|---|
| Imported-history PB behavior | No import/reconciliation or historical-PB persistence path exists. | F, G | Treat imported records as historical evidence with no retroactive celebration; or explicitly migrate them into the V1 PB ledger. |
| Camps Stacked comparison normalization | The candidate compares the cumulative final count directly; no owner decision establishes a per-10-minute or duration-normalized basis. | E, F | Keep final cumulative count as the comparison value; or adopt a declared rate with a new metric version. |
| Edge-match eligibility: safe-to-leave, remake, and long-abandon semantics | The candidate has `duration >= 300` and `leaverStatus == NONE`, but does not define the provider enum meanings or a separate remake/safe-to-leave rule. | A, H | Keep the narrow gate and document every enum; or add explicit refusal codes and a versioned short/remake policy. |

The following checks are not open in the candidate implementation, but are
contract requirements that need tests when the implementation is integrated:

- PB comparison uses the normalized comparison value, including normalized
  metrics; and
- an exact tie does not create a new PB because the candidate uses strict
  `>`/`<` comparisons.

## 4. Terminology

- **Observation** — one valid metric value for one player, match, role, metric
  ID, and metric version.
- **Raw/display value** — the direct value retained as evidence or shown as a
  count/amount, such as `heroHealing` or `total_dead_seconds`.
- **Comparison value** — the value placed in the role baseline, such as
  healing per ten minutes or a damage share.
- **Measured** — required inputs exist and the metric has a meaningful value,
  including a legitimate zero.
- **N/A** — the metric cannot be meaningfully calculated for this match.
- **Baseline building** — fewer than five prior measured observations for the
  same role, metric, and version.
- **Baseline ready** — at least five prior measured observations exist.
- **Delta** — current comparison value minus the baseline median, in the
  comparison value's units. A direction-adjusted delta reverses the sign for
  lower-is-better metrics.
- **Personal Best (PB)** — a current measured observation that exceeds the
  prior role/metric record in the correct direction after the baseline gate.

## 5. Role progression model

### Role resolution

The candidate implementation resolves a row as follows:

| Provider position/role | Effective role |
|---|---|
| `POSITION_1` | Carry |
| `POSITION_2` | Mid |
| `POSITION_3` | Offlane |
| `POSITION_4` or `POSITION_5` | Support |
| missing position but `SUPPORT`, `HARD_SUPPORT`, or `LIGHT_SUPPORT` native role | Support |
| anything else or missing | No progression role |

This document does not define the generic role-assignment algorithm. It only
defines how an effective role selects these histories.

### Isolation invariant

For every metric:

```text
Carry history != Mid history != Offlane history != Support history
```

Identical formulas do not merge histories. Carry Objective Damage Share and
Mid Objective Damage Share have different baselines and PBs. Support and
Offlane Fight Presence may share primitives, but never share observations.

## 6. Match eligibility for progression

Eligibility is defined only for participation in these role histories. An
excluded match may still be retained or measured by another product feature.

### Eligible contexts

| Context | Progression status |
|---|---|
| Ranked All Pick | Eligible |
| Unranked All Pick | Eligible |
| Turbo | Excluded |
| Ability Draft | Excluded |
| Captain's Mode | Not part of V1; excluded |
| Other/special structurally different modes | Excluded |

The candidate gate accepts native mode values `ALL_PICK`,
`ALL_PICK_RANKED`, or `ALL_PICK_UNRANKED`, native lobby values `RANKED` or
`UNRANKED`, a positive match ID, a non-negative start time, duration of at
least 300 seconds, a valid player row, a resolved role, and
`leaverStatus == NONE`.

### Edge behavior

- **Abandon/disconnect:** any non-`NONE` leaver status is currently excluded
  by the candidate gate. The full provider enum mapping is not yet part of
  this contract.
- **Remake:** a match shorter than 300 seconds is currently excluded. There is
  no separate validated remake signal, so a longer match with `NONE` could
  pass; this is part of the open edge-match decision.
- **Safe-to-leave:** no dedicated safe-to-leave interpretation is currently
  implemented. A non-`NONE` status is excluded; `NONE` is not treated as
  evidence that a match was not safe-to-leave.
- **Very short match:** duration `< 300` seconds is ineligible in the
  candidate implementation. This is a five-minute implementation threshold,
  not a license to infer a product meaning for every short match.
- **Incomplete parsed telemetry:** a match can pass context eligibility while
  an individual metric is N/A because its required field, event stream,
  checkpoint, team denominator, or identity is absent/malformed. Such an N/A
  observation does not enter a baseline or PB record. No missing value is
  converted to zero.

## 7. Personal baseline contract

For every metric observation:

1. Resolve the effective role.
2. Resolve the metric ID and version.
3. Measure the current match.
4. Gather only earlier, progression-eligible observations with the same role,
   metric ID, and metric version.
5. Exclude the current match by match identity and chronology.
6. Sort by `(started_at, match_id)` and retain at most the 20 most recent
   previous observations.
7. Remove N/A/unmeasured observations.
8. Require at least five prior measured observations.
9. Use the **median** of the retained comparison values.
10. Compare the current comparison value with that median using the metric's
    direction.

The first generally comparable observation is the sixth eligible measured
observation for that role and metric. Before then, the canonical state is
`BASELINE_BUILDING`; the candidate's equivalent status is
`insufficient_history`. At five or more measured prior observations, the
canonical state is `BASELINE_READY`.

The baseline window is previous-only. The current match never contributes to
its own baseline. A role-specific metric version can never read observations
from another version.

### Comparison semantics

Let `x` be the current comparison value and `b` the rolling median:

```text
value_delta     = x - b
direction_delta = x - b                  if higher_is_better
                  b - x                  if lower_is_better
```

`value_delta` preserves the metric's native units. Percentages use percentage
points, raw counts use count units, and normalized metrics use their declared
rate or share units. `direction_delta > 0` means movement in the favorable
direction; it does not prove skill, causality, or outcome impact.

The candidate implementation currently computes `fmean(values)` at the
baseline step. That is a **CONTRACT CONFLICT** and must become a median before
the implementation can be considered V1-conformant.

## 8. N/A versus zero

The distinction applies to every metric.

| State | Use when | Examples |
|---|---|---|
| `0` | Inputs are valid, an opportunity/denominator exists where required, and the measured numerator is genuinely zero. | 0 Healing; 0 Wards Placed with a valid ward stream; 0% Objective Damage Share while team tower damage is positive. |
| `N/A` | The metric cannot be meaningfully calculated. | Match ends before NW@20; team has zero credited kills for Fight Presence; team has zero tower damage for Objective Damage Share; required telemetry is missing. |

N/A observations never enter baselines, PB records, or rolling-window counts.
Legitimate zeros remain numeric zero. A missing field, malformed event, absent
checkpoint, or zero denominator must not be silently coerced to zero.

## 9. Canonical metric registry

The entries below are the single canonical V1 registry. Each entry appears
once. “Comparison” is the value used for the rolling baseline and PB unless a
future version explicitly changes it.

### Carry

#### `carry.last_hits_at_10.v1` — CS at 10:00

| Field | Contract |
|---|---|
| Role / version | Carry / v1 |
| Definition / formula | Total last-hit deltas in the first ten complete match minutes, `[0:00, 10:00)`. |
| Raw STRATZ/canonical inputs | Player `lastHitsPerMinute` delta series; canonical time-bucket alignment. The whole-match `numLastHits` scalar is not an acceptable substitute. |
| Raw/display value | Last hits at 10:00. |
| Comparison value | Same count. |
| Direction | Higher is better. |
| Zero rule | `0` is measured if the ten-minute interval and required trajectory are valid. |
| N/A rule | N/A when the match ends before 10:00, the required trajectory is missing/malformed, or bucket alignment is unavailable. |
| Baseline / PB | Participates when measured; PB allowed after the five-prior gate. |
| Limitations | Last hits measure resource acquisition, not last-hit accuracy, lane quality, or skill; opportunity and matchup are unobserved. |
| Status | LOCKED / DEFERRED; no calculator exists on `main` or in the candidate module. |
| Evidence / tests | `lastHitsPerMinute` is validated as a per-minute delta in `services/api/app/player_analysis_v7/research/pass2_tables.py`; exact progression extraction still needs an acceptance test. |

#### `carry.cs_10_to_20.v1` — CS gained from 10:00 through 20:00

| Field | Contract |
|---|---|
| Role / version | Carry / v1 |
| Definition / formula | Sum of last-hit deltas in `[10:00, 20:00)`, i.e. the ten-minute window beginning at 600 seconds and ending before 1,200 seconds. |
| Raw STRATZ/canonical inputs | Player `lastHitsPerMinute` delta series with explicit bucket alignment. |
| Raw/display value | Last hits gained in the window. |
| Comparison value | Same count. |
| Direction | Higher is better. |
| Zero rule | `0` is measured when the complete window is present and contains no last-hit events. |
| N/A rule | N/A if the match ends before 20:00 or required trajectory coverage is missing/malformed. |
| Baseline / PB | Participates when measured; PB allowed after the five-prior gate. |
| Limitations | A fixed farm window does not measure opportunity, pressure, or whether farm was appropriate for the team. |
| Status | LOCKED / DEFERRED; no calculator exists on `main` or in the candidate module. |
| Evidence / tests | Delta semantics are documented in `services/api/app/player_analysis_v7/research/pass2_tables.py`; exact window extraction is unimplemented. |

#### `carry.net_worth_at_20.v1` — Net Worth at 20:00

| Field | Contract |
|---|---|
| Role / version | Carry / v1 |
| Definition / formula | Player net worth at the 20:00 checkpoint: `networthPerMinute[20]` under the canonical checkpoint convention. |
| Raw STRATZ/canonical inputs | Player `networthPerMinute`, a cumulative level series with the validated checkpoint convention. |
| Raw/display value | Net worth at 20:00. |
| Comparison value | Same gold amount. |
| Direction | Higher is better. |
| Zero rule | A valid zero checkpoint is numeric zero, though a normal match should normally have positive net worth. |
| N/A rule | N/A if the match ends before 20:00, the checkpoint is absent/null, or the series is malformed. |
| Baseline / PB | Participates when measured; PB allowed after the five-prior gate. |
| Limitations | Net worth includes more than farming and is affected by kills, deaths, item state, and team resource allocation. |
| Status | LOCKED / DEFERRED; no calculator exists on `main` or in the candidate module. |
| Evidence / tests | Cumulative semantics and checkpoint helpers are documented in `services/api/app/player_analysis_v7/research/pass2_tables.py`. |

#### `carry.dead_time.v1` — Time Spent Dead

| Field | Contract |
|---|---|
| Role / version | Carry / v1 |
| Definition / formula | Whole-match sum of the player's valid dead intervals: `total_dead_seconds`. |
| Raw STRATZ/canonical inputs | Authoritative death and return-to-play timestamps/intervals. `deathEvents` alone is insufficient to reconstruct dead duration. |
| Raw/display value | `total_dead_seconds`. |
| Comparison value | `dead_time_rate = total_dead_seconds / match_duration_seconds`. |
| Direction | Lower is better. |
| Zero rule | `0` is measured when valid interval telemetry proves no time dead. |
| N/A rule | N/A if duration or complete dead-interval telemetry is missing/malformed. |
| Baseline / PB | Baseline uses dead-time rate. PB basis follows the candidate's normalized-value rule; no raw-seconds PB is created separately. |
| Limitations | Time dead is not a judgment about the cause, tactical sacrifice, positioning, or decision quality. |
| Status | LOCKED / DEFERRED; current role-metric acquisition does not provide the required return-to-play interval. |
| Evidence / tests | No current V1 calculator; do not infer dead duration from death count or death timestamps alone. |

#### `carry.hero_damage_share.v1` — Hero Damage Share

| Field | Contract |
|---|---|
| Role / version | Carry / v1 |
| Definition / formula | `player hero damage / total hero damage by player's team`. |
| Raw STRATZ/canonical inputs | Player `heroDamage` and the five allied players' `heroDamage`. |
| Raw/display value | Player hero damage, with team total retained as supporting evidence. |
| Comparison value | The share ratio, normally represented as a percentage. |
| Direction | Higher is better. |
| Zero rule | If team hero damage is positive and player damage is zero, measured `0%`. |
| N/A rule | If team hero damage is zero, or any required team damage is unavailable/malformed, N/A. |
| Baseline / PB | Share participates in the role-specific baseline; PB allowed after the five-prior gate. |
| Limitations | Damage share is team- and hero-dependent; it does not establish fight quality, target value, or causality. |
| Status | LOCKED / DEFERRED; candidate role-metric query does not select the required team damage fields. |
| Evidence / tests | Scalar `heroDamage` is present in the broader STRATZ player projection; no V1 progression calculator exists. |

#### `carry.objective_damage_share.v1` — Objective Damage Share

| Field | Contract |
|---|---|
| Role / version | Carry / v1 |
| Definition / formula | `player tower damage / total tower damage by player's team`; Roshan damage is excluded by the tower-damage field semantics. |
| Raw STRATZ/canonical inputs | Player `towerDamage` and allied players' `towerDamage`. |
| Raw/display value | Player tower damage, with team tower damage retained as supporting evidence. |
| Comparison value | The tower-damage share ratio. |
| Direction | Higher is better. |
| Zero rule | Team tower damage > 0 plus player tower damage = 0 yields measured `0%`. |
| N/A rule | Team tower damage = 0, or required player/team values are missing/malformed, yields N/A. |
| Baseline / PB | Carry-only share history; PB allowed after the five-prior gate. |
| Limitations | This is contribution share, not proof that the player caused a structure to fall. |
| Status | LOCKED / DEFERRED; no calculator exists on `main` or in the candidate module. |
| Evidence / tests | Broader STRATZ projection exposes tower damage; the role-metric query currently omits the required inputs. |

### Mid

#### `mid.lane_net_worth_advantage_at_10.v1` — Mid Lane Net Worth Advantage

| Field | Contract |
|---|---|
| Role / version | Mid / v1 |
| Definition / formula | `own net worth at 10:00 - opposing Mid net worth at 10:00`. |
| Raw STRATZ/canonical inputs | Own and opponent `networthPerMinute[10]`; opposing Mid is the player on the opposite side with native `POSITION_2`. Exactly one valid opponent is required. |
| Raw/display value | The gold difference, including its sign. |
| Comparison value | Same gold difference. |
| Direction | Higher is better. |
| Zero rule | `0` is measured when both checkpoints exist and are equal. |
| N/A rule | N/A if either checkpoint is missing/malformed or the opposing Position 2 cannot be identified uniquely. |
| Baseline / PB | Mid-only history; PB allowed after the five-prior gate. |
| Limitations | Net-worth advantage is affected by matchup, lane partner, rotations, kills, and resource transfers. |
| Status | LOCKED / DEFERRED; no calculator or team net-worth projection exists in the candidate role-metric module. |
| Evidence / tests | Native `position`, `networthPerMinute`, and side fields exist in the broader deep projection; no V1 acceptance test yet. |

#### `mid.level_6_time.v1` — Time Reaching Level 6

| Field | Contract |
|---|---|
| Role / version | Mid / v1 |
| Definition / formula | The sixth entry of the level-up timestamp series: `level_up_times[5]`. The validated `stats.level` series is one elapsed-seconds entry per level reached, not a minute grid. |
| Raw STRATZ/canonical inputs | Player `stats.level`, normalized as `self.trajectories.level`. |
| Raw/display value | Seconds after match start when level 6 was reached. |
| Comparison value | Same seconds value. |
| Direction | Lower is better (earlier). |
| Zero rule | A timestamp of 0 is valid if the provider records it. |
| N/A rule | N/A if fewer than six valid level timestamps exist or the series is malformed. |
| Baseline / PB | Mid-only history; PB allowed after the five-prior gate, using the lower-is-better direction. |
| Limitations | Earlier level access is not automatically better if it came from taking resources from an ally. |
| Status | LOCKED / DEFERRED; timestamp semantics are validated, but no V1 calculator exists. |
| Evidence / tests | `level_up_times()` and its boundary tests live in `services/api/app/player_analysis_v7/research/pass2_tables.py` and `tests/unit/test_v7_research_pass2_tables.py`. |

#### `mid.early_fight_presence.v1` — Early Fight Presence

| Field | Contract |
|---|---|
| Role / version | Mid / v1 |
| Definition / formula | `credited team hero kills through 15:00 with player's kill/assist credit / credited team hero kills through 15:00`. |
| Raw STRATZ/canonical inputs | All ten players' `stats.killEvents { time }`; tracked player's `killEvents { time }` and `assistEvents { time }`; player side and slot. |
| Raw/display value | The ratio plus numerator and denominator event counts. |
| Comparison value | The ratio. |
| Direction | Higher is better. |
| Zero rule | A valid numerator of zero is measured as `0` when the team had at least one credited kill by the cutoff. |
| N/A rule | Team credited kills = 0, missing/malformed team event data, missing own assist stream, invalid identity, or impossible numerator > denominator yields N/A. |
| Baseline / PB | Mid-only history; PB allowed after the five-prior gate. |
| Limitations / exact event behavior | The cutoff is inclusive: `0 <= time <= 900`. The denominator counts killer event rows for the player's five-person team. The numerator counts the player's killer rows plus assist rows in the same interval. Timestamps are not deduplicated because the selected provider shape has no event ID; two kills in the same second remain two events. Kill and assist rows are separate credit types; this is not Gank Frequency. |
| Status | LOCKED / IMPLEMENTED / VALIDATED on candidate branch `d691008`; absent from `main`. |
| Evidence / tests | Candidate `role_metrics.py`, `tests/unit/test_progression_role_metrics.py`, and the 2026-09-12 backend validation evidence. |

#### `mid.net_worth_at_20.v1` — Mid Net Worth at 20:00

| Field | Contract |
|---|---|
| Role / version | Mid / v1 |
| Definition / formula | Own `networthPerMinute[20]` at the 20:00 checkpoint. |
| Raw STRATZ/canonical inputs | Own `networthPerMinute` cumulative series. |
| Raw/display value | Own net worth at 20:00. |
| Comparison value | Same gold amount. |
| Direction | Higher is better. |
| Zero rule | Valid zero is numeric zero. |
| N/A rule | Match ends before 20:00, checkpoint missing/null, or series malformed. |
| Baseline / PB | Mid-only history; PB allowed after the five-prior gate. |
| Limitations | Same primitive as Carry Net Worth at 20:00, but history and PB are entirely Mid-specific. |
| Status | LOCKED / DEFERRED; no calculator exists in the candidate role-metric module. |
| Evidence / tests | Cumulative net-worth semantics are documented in `services/api/app/player_analysis_v7/research/pass2_tables.py`. |

#### `mid.objective_damage_share.v1` — Objective Damage Share

| Field | Contract |
|---|---|
| Role / version | Mid / v1 |
| Definition / formula | `player tower damage / total tower damage by player's team`. It is mathematically the same as Carry Objective Damage Share but is a separate track. |
| Raw STRATZ/canonical inputs | Player and allied `towerDamage`. |
| Raw/display value | Player tower damage and team total as supporting evidence. |
| Comparison value | Tower-damage share ratio. |
| Direction | Higher is better. |
| Zero rule | Positive team tower damage plus player zero damage yields measured `0%`. |
| N/A rule | Team tower damage = 0 or required values missing/malformed. |
| Baseline / PB | Mid-only history; PB allowed after the five-prior gate. |
| Limitations | Contribution share is not causality. Do not revive the retired Mid Tower Influence concept. |
| Status | LOCKED / DEFERRED; no calculator exists in the candidate role-metric module. |
| Evidence / tests | No current V1 calculator; separate metric ID is required even though the formula matches Carry. |

### Offlane

#### `offlane.lane_net_worth_advantage_at_10.v1` — Offlane Lane Pressure

| Field | Contract |
|---|---|
| Role / version | Offlane / v1 |
| Definition / formula | `own net worth at 10:00 - opposing safelane Carry net worth at 10:00`. |
| Raw STRATZ/canonical inputs | Own and opposing `networthPerMinute[10]`; opposing Carry is the enemy-side player with native `POSITION_1`. Exactly one valid opponent is required. |
| Raw/display value | Signed gold difference. |
| Comparison value | Same gold difference. |
| Direction | Higher is better. |
| Zero rule | `0` is measured when both checkpoints exist and are equal. |
| N/A rule | Missing checkpoint, malformed series, or no unique opposing Position 1 yields N/A. |
| Baseline / PB | Offlane-only history; PB allowed after the five-prior gate. |
| Limitations | The difference is a pressure proxy, not proof of lane control, matchup quality, or causality. |
| Status | LOCKED / DEFERRED; no calculator exists in the candidate role-metric module. |
| Evidence / tests | Native positions and cumulative net-worth semantics are available in the broader deep projection; V1 calculator is pending. |

#### `offlane.net_worth_at_10.v1` — Offlane Economy

| Field | Contract |
|---|---|
| Role / version | Offlane / v1 |
| Definition / formula | Own `networthPerMinute[10]`. |
| Raw STRATZ/canonical inputs | Own cumulative net-worth series. |
| Raw/display value | Own net worth at 10:00. |
| Comparison value | Same gold amount. |
| Direction | Higher is better. |
| Zero rule | Valid zero checkpoint is numeric zero. |
| N/A rule | Match ends before 10:00, checkpoint missing/null, or series malformed. |
| Baseline / PB | Offlane-only history; PB allowed after the five-prior gate. |
| Limitations | Economy reflects more than lane farming and is affected by kills, deaths, and team allocation. |
| Status | LOCKED / DEFERRED; no calculator exists in the candidate role-metric module. |
| Evidence / tests | Cumulative semantics are documented in `services/api/app/player_analysis_v7/research/pass2_tables.py`. |

#### `offlane.fight_presence.v1` — Fight Presence

| Field | Contract |
|---|---|
| Role / version | Offlane / v1 |
| Definition / formula | Whole-match credited kill participation: `(player kills + player assists) / credited hero kills by the player's team`. |
| Raw STRATZ/canonical inputs | Ten-player scoreboard kills/assists or an equivalent validated credited-kill event construction; player identity and side. Do not use `radiantKills`/`direKills` as the authoritative denominator because those arrays count opposing deaths, not necessarily scoreboard-credited kills. |
| Raw/display value | Ratio plus numerator and denominator counts. |
| Comparison value | The ratio. |
| Direction | Higher is better. |
| Zero rule | A valid numerator of zero is measured as `0` when team credited kills are positive. |
| N/A rule | Team credited kills = 0 or required scoreboard/event identity is missing/malformed. |
| Baseline / PB | Offlane-only history; PB allowed after the five-prior gate. |
| Limitations | Participation is observable credit, not fight quality, timing quality, or causality. |
| Status | LOCKED / DEFERRED; the candidate only implements the analogous Support calculator. |
| Evidence / tests | The candidate Support implementation demonstrates the validated scoreboard pattern; Offlane-specific implementation is pending. |

#### `offlane.objective_involvement.v1` — Objective Involvement

| Field | Contract |
|---|---|
| Role / version | Offlane / v1 |
| Definition / formula | `credited enemy towers / total enemy towers destroyed by team`. A tower is credited if the player dealt positive damage to that specific tower, or recorded a kill/assist in the inclusive 60 seconds before it fell. |
| Raw STRATZ/canonical inputs | Match `towerDeaths { time, isRadiant, npcId }`; tracked-player `towerDamageReport { npcId, damage }`; tracked-player kill/assist event times; player side. |
| Raw/display value | Credited-tower count over total enemy-tower count. |
| Comparison value | The ratio. |
| Direction | Higher is better. |
| Zero rule | If towers were destroyed and none were credited, measured `0`. A positive team tower count is required. |
| N/A rule | No enemy towers, missing/malformed tower report, missing/malformed proximity events, or missing player side yields N/A. There is no automatic fallback to Objective Damage Share. |
| Limitations / exact implementation | Enemy towers are those whose `isRadiant` differs from the player side. Candidate code deduplicates exact `(time, npc_id)` tower-death pairs and counts each tower once. `towerDamageReport` has no timestamp, so direct attribution joins on NPC ID. Proximity is `[tower_time - 60, tower_time]`; it does not claim causation. Missing report is N/A even when scalar tower damage exists. |
| Status | LOCKED / IMPLEMENTED / VALIDATED on candidate branch `d691008`; absent from `main`. |
| Evidence / tests | Candidate role-metric tests cover Radiant/Dire orientation, NPC matching, 45/60/90-second sensitivity, zero towers, and missing reports; validation evidence says the report was present in 6/8 probe matches. |

### Support

#### `support.fight_presence.v1` — Fight Presence

| Field | Contract |
|---|---|
| Role / version | Support / v1 |
| Definition / formula | `(player kills + player assists) / credited hero kills by the player's five-person team`. |
| Raw STRATZ/canonical inputs | Ten-player scoreboard `playerSlot`, `isRadiant`, `kills`, and `assists`; tracked-player identity and side. |
| Raw/display value | Ratio plus numerator and denominator counts. |
| Comparison value | The ratio. |
| Direction | Higher is better. |
| Zero rule | Valid numerator zero with positive team kills is measured as `0`. |
| N/A rule | Team credited kills = 0; incomplete ten-player scoreboard; invalid identity; or impossible numerator greater than denominator. |
| Baseline / PB | Support-only history; PB allowed after the five-prior gate. |
| Limitations / exact implementation | Candidate requires ten valid, unique slots and exactly five players on each side, then sums scoreboard kills on the player's side. It does not use `radiantKills`/`direKills` arrays. |
| Status | LOCKED / IMPLEMENTED / VALIDATED on candidate branch `d691008`; absent from `main`. |
| Evidence / tests | Candidate tests cover side selection, zero denominator, zero involvement, malformed scoreboards, and rejection of impossible values; validation evidence reports 10 complete scoreboard rows. |

#### `support.observer_wards_placed.v1` — Wards Placed

| Field | Contract |
|---|---|
| Role / version | Support / v1 |
| Definition / formula | Count tracked-player ward events with `type == 0`, the validated Observer mapping. `type == 1` is Sentry and is not counted. |
| Raw STRATZ/canonical inputs | Player `stats.wards { time, type, ... }`. |
| Raw/display value | `observer_wards_placed`. |
| Comparison value | `wards_per_10 = observer_wards_placed / match_duration_minutes * 10`. |
| Direction | Higher is better. |
| Zero rule | Valid ward stream plus zero Observer events yields measured `0`. |
| N/A rule | Missing/malformed ward stream or non-positive duration yields N/A. |
| Baseline / PB | Rate enters Support history; PB uses the comparison rate after the five-prior gate. |
| Limitations | Counts placement, not useful vision, duration, map coverage, or support quality. |
| Status | LOCKED / DEFERRED; the `type` mapping is validated in the existing V7 research code, but the candidate progression query/calculator does not implement this metric. |
| Evidence / tests | `services/api/app/player_analysis_v7/research/pass2_features.py` records the 2026-09-05 purchase-stream validation; `tests/unit/test_v7_research_pass2_features.py` covers type 0/1 behavior. |

#### `support.vision_denial.v1` — Vision Denial

| Field | Contract |
|---|---|
| Role / version | Support / v1 |
| Definition / formula | Count attributed `wardDestruction` events for the player. V1 does not filter on unresolved `isWard` subtype semantics. |
| Raw STRATZ/canonical inputs | Player `stats.wardDestruction` event stream. |
| Raw/display value | `dewards`. |
| Comparison value | `dewards_per_10 = dewards / match_duration_minutes * 10`. |
| Direction | Higher is better. |
| Zero rule | Valid destruction stream plus no destruction events yields measured `0`. |
| N/A rule | Missing/malformed destruction stream or non-positive duration yields N/A. |
| Baseline / PB | Rate enters Support history; PB allowed after the five-prior gate. |
| Limitations | Do not claim Observer-only destruction, information denial quality, or downstream impact. |
| Status | LOCKED / DEFERRED; the candidate query and normalizer do not yet expose the required event stream to this calculator. |
| Evidence / tests | The broader pass-2 query selects `wardDestruction`, but older research marked its subtype semantics unresolved; V1 therefore counts attributed events without subtype claims. |

#### `support.camps_stacked.v1` — Camps Stacked

| Field | Contract |
|---|---|
| Role / version | Support / v1 |
| Definition / formula | Final value of the validated cumulative, non-decreasing `campStack` player series. |
| Raw STRATZ/canonical inputs | Player `stats.campStack`, normalized as `self.trajectories.camp_stack`. |
| Raw/display value | Final cumulative camp-stack count. |
| Comparison value | **Current candidate behavior:** the same final count, with no duration normalization. The owner decision on whether this is the final comparison basis remains OPEN. |
| Direction | Higher is better. |
| Zero rule | Valid non-empty series ending at zero is measured `0`. |
| N/A rule | Missing/empty/malformed/non-monotonic series yields N/A. |
| Baseline / PB | No N/A history entry. PB basis is blocked on the open normalization decision. |
| Limitations | A stack action is observable; later ally consumption, safety, opportunity cost, and resource effectiveness are not. Do not call this Resources Enabled. |
| Status | LOCKED / IMPLEMENTED / VALIDATED on candidate branch `d691008`; OPEN comparison normalization; absent from `main`. |
| Evidence / tests | 2026-09-12 validation found a non-decreasing step series and supports cumulative final-value extraction; candidate tests cover final value, zero, missing, non-monotonic, and role isolation. |

#### `support.healing.v1` — Healing

| Field | Contract |
|---|---|
| Role / version | Support / v1 |
| Definition / formula | Player scalar `heroHealing`; `healPerMinute` deltas corroborate the scalar but do not replace it. |
| Raw STRATZ/canonical inputs | Player `heroHealing`; `stats.healPerMinute` as corroborating trajectory evidence. |
| Raw/display value | `heroHealing`. |
| Comparison value | `healing_per_10 = heroHealing / match_duration_minutes * 10`. |
| Direction | Higher is better. |
| Zero rule | Valid `heroHealing == 0` is measured as raw zero and comparison zero. |
| N/A rule | Missing/malformed healing or non-positive duration yields N/A. |
| Baseline / PB | Rate enters Support history; PB uses the rate after the five-prior gate. |
| Limitations | This is hero healing under the provider's semantics; do not rename it Ally Healing or infer saves/effectiveness. |
| Status | LOCKED / IMPLEMENTED / VALIDATED on candidate branch `d691008`; absent from `main`. |
| Evidence / tests | 2026-09-12 validation supports `heroHealing` and `healPerMinute`; candidate tests cover scalar/rate extraction, zero, malformed duration, missing value, and role isolation. |

## 10. Normalized versus raw values

The backend may retain/display a raw amount while comparing a normalized value.
The distinction is part of the contract, not UI copy.

| Metric(s) | Raw/display value | Comparison value |
|---|---|---|
| Carry Survival | `total_dead_seconds` | `dead_time_rate = total_dead_seconds / match_duration_seconds` |
| Carry Hero Damage Share | Player hero damage | Player hero damage / team hero damage |
| Carry/Mid Objective Damage Share | Player tower damage | Player tower damage / team tower damage |
| Mid/Offlane/Support Fight Presence | Credited numerator and denominator | Numerator / denominator |
| Mid Early Fight Presence | Early credited numerator and denominator | Early numerator / early denominator |
| Offlane Objective Involvement | Credited towers / total enemy towers | Credited-tower ratio |
| Support Wards Placed | Observer ward count | Observer wards per 10 minutes |
| Support Vision Denial | Deward event count | Dewards per 10 minutes |
| Support Healing | `heroHealing` amount | Healing per 10 minutes |
| Support Camps Stacked | Final cumulative count | Same count in the candidate; normalization decision OPEN |

All remaining registry metrics use their raw value as their comparison value.
The baseline, delta, and PB must use the comparison column, never an ad hoc UI
conversion. A formula change between raw and comparison values requires a new
metric version.

## 11. Personal Best contract

V1 has Personal Best only. It has no Season Best and no broader achievement
system.

A PB is scoped by role, metric ID, and metric version. It requires:

- a measured current observation;
- an eligible progression context;
- at least five previous measured observations for the same role/metric/version;
- a ready rolling baseline/history; and
- comparison in the metric's declared direction.

For a higher-is-better metric, the candidate recognizes a PB only when:

```text
current_comparison_value > max(previous_comparison_values)
```

For a lower-is-better metric:

```text
current_comparison_value < min(previous_comparison_values)
```

Exact ties do not create a PB. N/A, insufficient history, excluded modes, and
unsupported metrics never create one. PBs do not cross roles or metric
versions. The candidate compares normalized values; this is the V1 basis for
rate/share metrics once the corresponding metric is implemented.

Imported historical PB behavior remains OPEN: the product must decide whether
imported records are historical evidence only or are migrated into the V1 PB
ledger and eligible for future celebration. No future implementation may
silently award an imported PB.

## 12. Role correction impact

Role correction changes only the affected match's effective role and the
derived histories that depend on it:

```text
Support → Carry
```

must:

- remove the match from every Support metric history and Support PB path;
- add it to each available Carry metric history for which its telemetry is
  valid;
- recalculate affected rolling baselines and PBs deterministically; and
- leave the effective roles and histories of all other matches unchanged.

The original predicted role/confidence may remain as metadata elsewhere. It is
not a second progression role. Role correction does not change the metric
definition or fabricate unavailable telemetry.

The candidate implementation has no persistent history or recalculation path;
this behavior is therefore a required future batch, not an existing feature.

## 13. Hard invariants

- Heroes do not split role progression.
- Carry, Mid, Offlane, and Support histories never contaminate one another.
- The same formula in two roles still means two progression tracks.
- The current match never enters its own baseline.
- A baseline uses at most the previous 20 eligible observations.
- Five prior measured observations are required before comparison/PB.
- The baseline statistic is the median, not the mean.
- N/A never becomes zero.
- N/A never enters a baseline, history count, or PB.
- A legitimate zero remains zero.
- Turbo, Ability Draft, Captain's Mode, and other excluded modes never enter
  these progression histories.
- Every metric definition is versioned.
- A formula, input, boundary, denominator, direction, zero/N/A rule, or
  normalization change requires a new metric version or an explicit migration.
- A Dota patch change alone does not reset progression history.
- A role correction deterministically rebuilds only affected role histories and
  records.
- Provider arrays are not interpreted by name alone; their validated semantics
  are preserved in the canonical adapter.
- `radiantKills` and `direKills` are not assumed to be credited team kills.
- Unsupported Control is never represented as an available metric through a
  proxy such as casts, actions, damage, or K/A.
- Measurements do not become judgments, causal claims, or a global score.

## 14. Unsupported and deferred metrics

### Support Control — `UNSUPPORTED_V1`

Control is outside the active registry. Current trusted telemetry does not
provide a reliable generic player-attributed disable/control-duration measure.
`actionReport` supplies counters, not control duration. Do not use ability cast
count, action count, damage, or kill/assist counts as proxies.

### Retired or intentionally absent concepts

- Mid Tower Influence is not a V1 metric. Mid uses Objective Damage Share.
- Hero-specific baselines are not a V1 default.
- Position 4 and Position 5 are not separate progression roles.
- There is no universal player score, population percentile, recommendation,
  medal, challenge, Season Best, or achievement catalog in this SSOT.

## 15. Open decisions

This table intentionally repeats the small open set so it remains visible near
the contract's end.

| Open decision | Why unresolved | Blocks which batch? | Recommended options |
|---|---|---|---|
| Imported-history PB behavior | No import/reconciliation or historical-PB persistence path exists. | F, G | Historical evidence only with no retroactive celebration; or migrate explicitly into the V1 PB ledger. |
| Camps Stacked comparison normalization | Candidate compares final cumulative count directly; no owner decision establishes a rate. | E, F | Keep raw cumulative count; or adopt a declared duration-normalized rate with a new metric version. |
| Edge-match eligibility: safe-to-leave, remake, and long-abandon semantics | Candidate only has `duration >= 300` and `leaverStatus == NONE`; provider enum meanings and remake semantics are not fully mapped. | A, H | Keep the narrow gate with documented enum mapping; or add explicit refusal codes and a versioned edge policy. |

Closed by inspected implementation, subject to integration tests:

| Decision checked | Current authoritative behavior |
|---|---|
| PB raw versus normalized basis | Candidate uses normalized comparison values for baseline and PB. |
| PB tie behavior | Strict inequality; an exact tie is not a PB. |
| Five-minute threshold | Candidate excludes duration `< 300` seconds; whether that rule covers every remake/safe-to-leave case is still open above. |

## 16. Explicitly out of scope

This SSOT does not specify:

- newest-match fetching, polling, or refresh strategy;
- STRATZ authentication, provider quotas, or general ingestion architecture;
- database technology, migrations, or storage schema;
- mobile API shape or Swift architecture;
- UI/card design, charts, animation, or onboarding;
- subscription or Pro entitlement implementation;
- annual reports, medals, challenges, notifications, or generic achievements;
- the generic role-assignment algorithm;
- global player scoring, population percentiles, or recommendation engines.

External systems are mentioned only when their fields are required to define a
metric input.

## 17. Feature-only development batches

Each batch below is independently mergeable and covers only this feature.

### Batch A — Complete the versioned metric registry and eligibility contract

- **Goal:** Make the 20 active metrics, versions, directionality, availability
  reasons, edge eligibility, and unsupported Control explicit in code.
- **Requirements:** Add missing IDs/specs; preserve role isolation; replace the
  candidate mean with median; encode the open edge decision once resolved.
- **Likely modules:** `services/api/app/progression/role_metrics.py` and its
  unit tests; no ingestion or persistence changes.
- **Prerequisites:** Owner decisions for edge-match behavior; this SSOT.
- **Tests:** Registry count/uniqueness, version isolation, mode/leaver/duration
  gates, zero/N/A, median versus mean, and unsupported Control.
- **Definition of Done:** One registry contains all 20 active metrics exactly
  once, every status is truthful, and no candidate code violates the median
  invariant.
- **Out of scope:** New provider fields, persistence, PB import, role
  correction, and UI.

**Candidate status:** PARTIAL, not merge-ready. Five calculators and the
eligibility/window helpers exist, but the registry is incomplete and the mean
conflict remains.

### Batch B — Implement the remaining metric calculators and inputs

- **Goal:** Add Carry, Mid, Offlane, and Support calculators not present in the
  candidate branch while preserving the exact registry formulas.
- **Requirements:** CS checkpoints/windows, NW@10/NW@20, level-6 timestamp,
  dead-time intervals, damage shares, Offlane/Mid lane opponent identity,
  Offlane Fight Presence, Observer Wards, and Vision Denial.
- **Likely modules:** progression calculators plus the minimal role-metric
  STRATZ query/normalizer fields and tests.
- **Prerequisites:** Batch A; validated provider shapes for any missing field.
- **Tests:** checkpoint boundaries, 15:00/20:00 boundaries, team denominators,
  Radiant/Dire orientation, ward type mapping, missing telemetry, and zero/N/A.
- **Definition of Done:** Every active registry entry has one calculator or an
  explicit unavailable state; no fallback invents a value.
- **Out of scope:** History persistence, baseline windows, PB persistence, and
  role corrections.

**Candidate status:** PARTIAL. Five metric calculators are implemented and
validated on `d691008`; 15 active metrics remain without calculators.

### Batch C — Role-isolated observation histories

- **Goal:** Record eligible measured observations by `role + metric ID +
  metric version`.
- **Requirements:** Exclude N/A, excluded modes, malformed contexts, and other
  roles; preserve raw/comparison values and provenance; never mix versions.
- **Likely modules:** progression domain/history repository and focused tests.
- **Prerequisites:** Batch A and B; persistence design is otherwise out of
  scope for this document.
- **Tests:** Carry/Mid separation, hero changes within Carry, Support 4/5
  merging, N/A omission, and version-key isolation.
- **Definition of Done:** A match can update only its effective role's valid
  metric histories.
- **Out of scope:** Match discovery, database technology choice, UI, and PB
  celebration.

**Candidate status:** NOT IMPLEMENTED.

### Batch D — Rolling personal baselines

- **Goal:** Compute previous-20 rolling medians with the five-prior gate.
- **Requirements:** Current exclusion, chronological ordering, N/A omission,
  `BASELINE_BUILDING`/`BASELINE_READY`, and metric-version isolation.
- **Likely modules:** baseline resolver and tests.
- **Prerequisites:** Batch C.
- **Tests:** Exactly four prior, exactly five prior, >20 prior, out-of-order
  rows, current-row duplication, and median values where mean differs.
- **Definition of Done:** Sixth eligible measured observation is comparable and
  every baseline is a median of at most 20 prior observations.
- **Out of scope:** PB records, role correction, and copy.

**Candidate status:** PARTIAL. The in-memory prior-window helper and minimum
gate exist, but the candidate uses mean and has no persisted history boundary.

### Batch E — Comparison engine and value semantics

- **Goal:** Emit raw/display values, comparison values, units, direction, deltas,
  and explicit unavailable reasons for every registry metric.
- **Requirements:** Apply rates/shares exactly as registered; use percentage
  points for rate deltas; invert lower-is-better direction; retain raw context.
- **Likely modules:** progression comparison DTO/domain and tests.
- **Prerequisites:** Batch B and D; Camps normalization decision.
- **Tests:** Healing/Wards/Dewards per-10, dead-time rate, share denominators,
  higher/lower deltas, and N/A/zero states.
- **Definition of Done:** No caller must infer whether raw and comparison values
  differ.
- **Out of scope:** UI wording, charts, and recommendations.

**Candidate status:** PARTIAL. The five candidate calculators carry raw and
  normalized values, but the complete registry and Camps decision are missing.

### Batch F — Personal Best engine

- **Goal:** Persist and expose role/metric/version PBs derived from ready
  histories.
- **Requirements:** Five-prior gate, normalized comparison basis, strict
  direction-aware inequality, no tie PB, no N/A PB, and resolved imported-history
  behavior.
- **Likely modules:** PB domain/repository and tests.
- **Prerequisites:** Batch C, D, E; imported-history decision.
- **Tests:** Higher/lower records, exact ties, normalized metrics, insufficient
  history, N/A, excluded mode, and imported rows.
- **Definition of Done:** Every PB is reproducible from the versioned history;
  no PB is awarded offline or from fabricated data.
- **Out of scope:** Season Best, medals, challenges, notifications, and UI
  celebration.

**Candidate status:** PARTIAL. It returns an in-memory boolean for five
  calculators; no persisted PB engine or import behavior exists.

### Batch G — Role-correction recalculation

- **Goal:** Deterministically rebuild affected histories and PBs after an
  effective role correction.
- **Requirements:** Remove old-role observations, add valid new-role
  observations, recalculate downstream baselines/PBs, and leave other matches
  unchanged.
- **Likely modules:** history rebuild service, correction record, and tests.
- **Prerequisites:** B through F and an owner-approved correction boundary.
- **Tests:** Support→Carry, reverse correction, missing new-role telemetry,
  repeated corrections, idempotence, and unaffected-role snapshots.
- **Definition of Done:** Rebuilding the same corrected match set twice produces
  identical histories and records.
- **Out of scope:** Role-assignment design, match refresh, and mobile routes.

**Candidate status:** NOT IMPLEMENTED.

### Batch H — Feature acceptance suite

- **Goal:** Prove the complete contract with deterministic fixtures.
- **Requirements:** Acceptance matrix below, all edge states, no provider calls,
  and no OpenDota calls.
- **Likely modules:** progression unit/integration tests and sanitized canonical
  fixtures only.
- **Prerequisites:** B through G.
- **Tests:** Every matrix row, including role isolation, median, N/A/zero,
  normalization, PB, and correction rebuild.
- **Definition of Done:** The suite fails on mean-vs-median regression, role
  contamination, current inclusion, metric-version mixing, or missing-data
  coercion.
- **Out of scope:** Browser E2E, UI, deployment, and live provider collection.

**Candidate status:** PARTIAL. The candidate has focused tests for five
calculators and the query; the feature-level suite does not exist.

## 18. Acceptance matrix

| Acceptance case | Expected contract behavior | Current evidence/status |
|---|---|---|
| Luna Carry and Slark Carry | Both update the same Carry metric track. | Contract; persistence test pending. |
| Mid match versus Carry history | Mid never changes Carry history. | Candidate role filter supports this; end-to-end history test pending. |
| Carry versus Mid Objective Damage Share | Same formula may be reused, but histories/PBs remain separate. | Contract; registry implementation pending. |
| Turbo match | May be measured, but never updates or compares against progression history. | Candidate test passes on candidate branch. |
| Fifth prior observation | Five prior measured values are enough for the next observation to compare. | Contract; exact boundary test required. |
| Current match | Never included in its own baseline. | Candidate helper/test covers current exclusion. |
| More than 20 prior observations | Only the 20 most recent prior eligible values are used. | Candidate helper has cap; exact 21-row test required. |
| Median versus mean | Baseline is median, including when it differs from mean. | **FAIL:** candidate uses `fmean`; must be fixed. |
| Match ends before 20:00 | NW@20 is N/A. | Calculator not implemented. |
| N/A observation | Omitted from baseline and PB history. | Candidate comparison filters unmeasured values; persistence test pending. |
| Zero Healing | Raw and comparison value remain 0 when duration/telemetry are valid. | Candidate test passes on candidate branch. |
| Zero team kills | Fight Presence is N/A, not zero. | Candidate Support/Mid tests cover this on candidate branch. |
| Positive team tower damage plus player zero damage | Objective Damage Share is measured at 0%. | Calculator/test pending. |
| Zero team tower damage | Objective Damage Share is N/A. | Calculator/test pending. |
| Wards Placed | Raw observer count is retained; baseline compares wards per 10. | Contract; calculator pending. |
| Vision Denial | Raw deward count is retained; baseline compares dewards per 10; no subtype claim. | Contract; calculator pending. |
| Healing | Raw `heroHealing` is retained; baseline compares healing per 10. | Candidate test passes on candidate branch. |
| Survival | Lower dead-time rate is favorable; PB direction is inverted. | Calculator/test pending. |
| Mid Early Fight Presence at 15:00 | Events at exactly 900 seconds count; events after 900 do not. | Candidate test passes on candidate branch. |
| Offlane Objective Involvement orientation | Only enemy-side towers count for Radiant/Dire; NPC joins and 60-second prior events apply. | Candidate tests pass on candidate branch. |
| Support Control | Cannot appear as an available V1 metric or use a proxy. | Candidate negative test passes; exclude from active registry. |
| Role correction Support→Carry | Remove old-role observations, add valid new-role observations, rebuild affected baselines/PBs only. | Not implemented. |
| Metric version change | Old and new version observations never mix. | Contract; persistence test pending. |

## 19. Change and versioning policy

Metric IDs and versions are part of the progression data contract. A change to
any of the following requires a metric-version review and normally a new
version:

- formula or numerator/denominator;
- raw input or provider-field interpretation;
- time boundary or checkpoint indexing;
- role eligibility or opponent identification;
- directionality;
- zero/N/A behavior;
- raw-to-comparison normalization;
- PB comparison basis or tie behavior.

A Dota patch change by itself does not reset a role history. If a provider
schema or game-rule change materially changes a metric's meaning, create a new
metric version and define migration/recalculation explicitly. Never silently
mix versions in one baseline or PB record.

This document is the contract future implementation agents must follow. Any
product change to metric meaning, eligibility, baselines, comparisons, or
records must update this SSOT before code changes land. Older research remains
historical evidence and cannot override this file.
