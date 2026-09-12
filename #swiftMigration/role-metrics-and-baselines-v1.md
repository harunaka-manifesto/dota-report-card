# Role Metrics & Personal Baselines V1

Status: ACTIVE SSOT
Scope: Role Metrics & Personal Baselines V1
Last audited: 2026-09-13

This is the authoritative contract for role-based Dota match measurements,
personal role baselines, match-to-baseline comparisons, and Personal Bests
derived directly from those measurements. It is not the SSOT for match
discovery or lifecycle, ingestion mechanics, role resolution, persistence,
mobile APIs, reports, subscriptions, or presentation. Match discovery,
processing, readiness, correction, recovery, and notification lifecycle are
defined in [Match Lifecycle V1](match-lifecycle-v1.md).

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

### NON-NORMATIVE IMPLEMENTATION AUDIT — audit boundary

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
| Carry | Position 1 | `progression_bucket + carry + metric_id + metric_version` |
| Mid | Position 2 | `progression_bucket + mid + metric_id + metric_version` |
| Offlane | Position 3 | `progression_bucket + offlane + metric_id + metric_version` |
| Support | Positions 4 and 5 combined | `progression_bucket + support + metric_id + metric_version` |

Position 4 and Position 5 are one Support track. Heroes never split a role
track: Luna Carry, Phantom Assassin Carry, and Slark Carry update the same
Carry history within a progression bucket for the same metric definition
version.

The active registry contains 20 V1 metrics: Carry 6, Mid 5, Offlane 4, and
Support 5. Support Control is unsupported and is not counted in that registry.

Status words used throughout this document:

- **LOCKED** — product meaning or rule is settled here.
- **IMPLEMENTED** — code exists in the inspected candidate implementation.
- **VALIDATED** — telemetry or behavior has supporting evidence/tests.
- **OPEN** — an owner decision or semantic contract is still unresolved.
- **UNSUPPORTED** — trusted telemetry cannot support the metric in V1.
- **DEFERRED** — intentionally in the V1 contract but not yet implemented.

## 3. Status and owner-decision summary

### NON-NORMATIVE IMPLEMENTATION AUDIT

Current implementation status is not complete:

| Area | main | Candidate branch d691008 |
|---|---|---|
| Complete 20-metric registry | Not present | No; the candidate contains only five supported calculators plus the unsupported Control entry |
| Validated metric calculators | None on main | Support Healing, Support Fight Presence, Camps Stacked, Mid Early Fight Presence, Offlane Objective Involvement |
| Eligibility and role-isolated prior window | None on main | In-memory candidate gate with All Pick filtering, role filtering, prior-20 baseline cap, current exclusion, five measured prior minimum, and duration >= 300; conflicts with the locked 600-second gate and effective-role input boundary |
| Baseline statistic | None on main | CONTRACT CONFLICT: candidate uses arithmetic mean (fmean); V1 requires median |
| Personal Best scope | None on main | Candidate comparison is tied to the prior-20 reference window; V1 PB history is all currently known eligible history |
| Persisted role histories | None | Not implemented |
| Personal Best persistence/rebuild | None | Only an in-memory comparison flag exists; no persisted PB engine |
| Role-correction recalculation | None | Not implemented |

These rows are an implementation snapshot only. They do not define the
product contract and must remain non-normative as files, branches, and
implementation status change.

### Owner decision summary

No owner decision remains unresolved in this SSOT. Implementation details such
as provider enum mapping, retry timing, and persistence technology require
validation or implementation policy; they do not reopen the product contract.

### LOCKED OWNER DECISIONS

| Decision | Locked rule |
|---|---|
| Role input | This feature consumes upstream effective_role. A user-confirmed role is authoritative; otherwise upstream supplies it. The feature never independently reclassifies the player. Positions 4 and 5 share Support once that effective role is supplied. |
| Progression buckets | STANDARD is ranked or unranked All Pick; TURBO is Turbo. Both are eligible and use identical V1 roles, metric definitions/versions, previous-20 median baseline, five-prior gate, PB comparison rules, N/A/zero semantics, the >=10-minute gate, and fail-closed integrity rules. Their histories, baselines, PB indexes, ordering, and finalization are completely isolated. |
| History identity | Every observation, baseline, and PB is keyed by `progression_bucket + effective_role + metric_id + metric_version`. No bucket, role, metric, or version may read another key. |
| Tower Damage Share naming | Carry and Mid use Tower Damage Share with role- and bucket-specific histories and IDs carry.tower_damage_share.v1 and mid.tower_damage_share.v1. |
| Recent baseline | Baseline is the median of the latest 20 previous eligible measured observations for the same progression bucket, effective role, metric ID, and metric version, after a minimum of five. |
| PB history | PB compares against all eligible historical observations currently known for the same progression bucket, effective role, metric ID, and metric version; it is not restricted to the recent baseline window. |
| PB comparison basis | PB uses comparison_value, not raw/display value. |
| PB ties | Strict inequality only. An exact tie is not a new PB; retain the earliest record/source match unless a later owner decision changes that rule. |
| Camps Stacked | The canonical value is cumulative campStack at the 20:00 checkpoint, using the validated time-aligned trajectory extraction and no final-value fallback. |
| Progression duration | duration_seconds >= 600 is required. Below 600 seconds is INELIGIBLE_FOR_PROGRESSION. |
| Competitive integrity | Ambiguous remake, safe-to-leave, abandon-like, or otherwise non-competitive evidence fails closed and makes progression ineligible. Provider enum mapping requires implementation validation and is not an open product decision. |
| Imported/recovered history | Trustworthy eligible imported or recovered observations may update the current best-known PB/index and future comparisons once admitted. They never create retroactive celebration events or rewrite already-finalized match snapshots. |

## 4. Terminology

- **Observation** — one valid metric value for one player, match, progression
  bucket, effective role, metric ID, and metric version.
- **Raw/display value** — the direct value retained as evidence or shown as a
  count/amount, such as heroHealing or total_dead_seconds.
- **Comparison value** — the canonical value placed in the role baseline and PB
  comparison, such as healing per ten minutes or a damage share.
- **Measured** — required inputs exist and the metric has a meaningful value,
  including a legitimate zero.
- **N/A** — the metric cannot be meaningfully calculated for this match.
- **Progression identity** — `progression_bucket + effective_role + metric_id +
  metric_version`; every observation, baseline, PB index, and comparison uses
  this complete key.
- **Recent personal baseline** — the median of the latest 20 previous eligible
  measured observations for the same progression bucket, effective role, metric
  ID, and version; at least five are required.
- **PB history** — all eligible historical measured observations currently known
  for the same progression bucket, effective role, metric ID, and version,
  including observations older than the recent baseline window.
- **Baseline building** — fewer than five prior measured observations for the
  same `progression_bucket + effective_role + metric_id + metric_version`
  identity.
- **Baseline ready** — at least five prior measured observations exist.
- **Delta** — current comparison value minus the baseline median, in the
  comparison value's units. A direction-adjusted delta reverses the sign for
  lower-is-better metrics.
- **Personal Best (PB)** — a current measured observation that strictly exceeds
  the best known earlier PB-history comparison value for the same progression
  identity in the correct direction, after the baseline gate. An exact tie is
  not a PB.

## 5. Role progression model

### Effective-role input boundary

The progression feature receives exactly one effective_role for each match. The
effective role is one of Carry, Mid, Offlane, or Support.

- A user-confirmed role, when present, is authoritative.
- Otherwise, the upstream role-resolution system supplies effective_role.
- This feature never independently predicts, reclassifies, or overrides the
  player's effective role.
- Position 4 and Position 5 are one Support progression track once upstream
  supplies that effective role.
- Missing or unresolved effective_role means the match cannot enter role
  progression.

Role detection and role resolution remain outside this SSOT's scope.

### NON-NORMATIVE IMPLEMENTATION AUDIT — candidate role resolution

The inspected candidate independently maps provider position values to Carry,
Mid, Offlane, and Support, and falls back to native Support role labels when a
position is absent. That mapping is implementation evidence only. It conflicts
with the locked input boundary until the candidate consumes upstream
effective_role instead of independently reclassifying the player.

### Isolation invariant

For every metric and effective role:

    STANDARD history != TURBO history

and, within each bucket:

    Carry history != Mid history != Offlane history != Support history

Identical formulas do not merge histories. Carry Tower Damage Share and Mid
Tower Damage Share have different baselines and PBs. Support and Offlane Fight
Presence may share primitives, but never share observations. A Standard
observation never updates, compares against, or blocks a Turbo observation, and
vice versa.

## 6. Match eligibility for progression

Eligibility is defined only for participation in these role histories. An
excluded match may still be retained or measured by another product feature.

### Match-level eligibility

A progression-eligible match must satisfy all of the following:

1. a supported progression bucket: STANDARD or TURBO;
2. duration_seconds >= 600;
3. the tracked player did not abandon;
4. an effective_role is available;
5. available evidence does not indicate an invalid or non-competitive match; and
6. the required metric telemetry exists for each metric that will actually be
   measured.

The canonical duration gate is duration_seconds >= 600. A match below 600
seconds is INELIGIBLE_FOR_PROGRESSION and must not contribute to role
histories, baselines, or PB history.

### Eligible contexts

| Context | Progression status |
|---|---|
| Ranked All Pick | Eligible as `STANDARD` |
| Unranked All Pick | Eligible as `STANDARD` |
| Turbo | Eligible as `TURBO` |
| Ability Draft | Excluded |
| Captain's Mode V1 | Excluded |
| Other/special structurally different modes | Excluded |

Supported contexts are Ranked All Pick and Unranked All Pick in the `STANDARD`
bucket and Turbo in the `TURBO` bucket. Ability Draft, Captain's Mode V1, and
special or structurally different modes are excluded from progression.

### Competitive-integrity policy

The integrity rule is fail closed:

> If the backend cannot confidently establish that a remake, safe-to-leave,
> abandon-like, or otherwise abnormal match is a normal competitive match,
> progression is ineligible.

Do not invent provider enum meanings. Where provider semantics are not yet
validated, record that provider mapping requires implementation validation.
That mapping work is an implementation task, not an OPEN product decision.

A tracked-player abandon or non-finish signal is ineligible. A missing or
ambiguous integrity signal is also ineligible when it prevents confident
classification as a normal competitive match.

### Match eligibility versus metric availability

MATCH_ELIGIBLE != EVERY_METRIC_AVAILABLE.

A match can be progression-eligible while an individual metric is N/A. For
example, a valid 18-minute Ranked All Pick can have valid Support Fight
Presence, Wards Placed, and Healing observations while NW@20 and Camps
Stacked @20 are N/A because the match ended before the checkpoint.

N/A metric observations never enter that metric's bucket/role baseline or PB
history.
Earlier or full-match metrics may still participate. Missing metric telemetry,
a malformed event stream, an unavailable checkpoint, an invalid denominator, or
an invalid identity makes that metric N/A; it does not make a valid match
globally ineligible unless the match-level requirements above fail. No missing
value is converted to zero.

### NON-NORMATIVE IMPLEMENTATION AUDIT — candidate eligibility conflicts

The inspected candidate uses duration >= 300 and a provider-position-derived role
gate. Those are implementation details that conflict with the locked
duration_seconds >= 600 rule and effective_role input boundary. The candidate's
leaverStatus == NONE check is not a substitute for the fail-closed competitive
integrity policy.

## 7. Personal baseline contract

### Recent personal baseline

For every measured metric observation:

1. Consume the upstream progression_bucket and effective_role.
2. Resolve the metric ID and version.
3. Measure the current match.
4. Gather only earlier, progression-eligible, measured observations with the
   same progression bucket, effective role, metric ID, and metric version.
5. Exclude the current match by match identity and chronology.
6. Sort by the deterministic chronology key `(provider_started_at,
   provider_source_match_id)` and retain at most the 20 most recent previous
   observations.
7. Require at least five prior measured observations.
8. Use the median of those retained comparison values.
9. Compare the current comparison value with that median using the metric's
   direction.

The first generally comparable observation is the sixth eligible measured
observation for that bucket, role, and metric. Before then, the canonical state
is BASELINE_BUILDING; the candidate equivalent is insufficient_history. At
five or more measured prior observations, the canonical state is
BASELINE_READY.

The baseline window is previous-only and represents the player's recent usual.
The current match never contributes to its own baseline. A bucket/role-specific
metric version can never read observations from another bucket, role, or
version.

### Personal Best history boundary

PB history is separate from the recent baseline. For the same progression
bucket, effective role, metric ID, and metric version, PB comparison uses all
eligible historical measured observations currently known to the product before
the current match. It is not limited to the latest 20 observations. N/A
observations, excluded matches, other buckets, other roles, and other versions
never enter PB history.

Example: if a player's recent Carry Tower Damage Share median is 31% and the
historical Carry PB is 52%, a new 45% match is above the recent baseline but is
not a new PB.

### Comparison semantics

Let x be the current comparison value and b the rolling baseline median:

    value_delta     = x - b
    direction_delta = x - b                  if higher_is_better
                      b - x                  if lower_is_better

value_delta preserves the metric's native units. Percentages use percentage
points, raw counts use count units, and normalized metrics use their declared
rate or share units. direction_delta > 0 means movement in the favorable
direction; it does not prove skill, causality, or outcome impact.

### NON-NORMATIVE IMPLEMENTATION AUDIT — baseline and PB conflicts

The inspected candidate computes fmean(values) for the baseline and restricts
its PB comparison reference to the prior-20 window. Both behaviors conflict
with the locked V1 contract: baseline median and all-known eligible PB history.

## 8. N/A versus zero

The distinction applies to every metric.

| State | Use when | Examples |
|---|---|---|
| `0` | Inputs are valid, an opportunity/denominator exists where required, and the measured numerator is genuinely zero. | 0 Healing; 0 Wards Placed with a valid ward stream; 0% Tower Damage Share while team tower damage is positive. |
| `N/A` | The metric cannot be meaningfully calculated. | Match ends before NW@20; team has zero credited kills for Fight Presence; team has zero tower damage for Tower Damage Share; required telemetry is missing. |

N/A observations never enter baselines, PB records, or rolling-window counts.
Legitimate zeros remain numeric zero. A missing field, malformed event, absent
checkpoint, or zero denominator must not be silently coerced to zero.

## 9. Canonical metric registry

The entries below are the single canonical V1 registry. Each entry appears
once. “Comparison” is the value used for the rolling baseline and PB unless a
future version explicitly changes it.
Status and Evidence / tests fields inside registry entries are NON-NORMATIVE
IMPLEMENTATION AUDIT snapshots; the metric definitions and rules above remain
the durable contract.

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
| Baseline / PB | Participates when measured in the matching progression identity; PB allowed after the five-prior gate. |
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
| Baseline / PB | Participates when measured in the matching progression identity; PB allowed after the five-prior gate. |
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
| Baseline / PB | Participates when measured in the matching progression identity; PB allowed after the five-prior gate. |
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
| Baseline / PB | Matching progression identity uses dead-time rate for its baseline and PB; no raw-seconds PB is created separately. |
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
| Baseline / PB | Share participates in the matching progression-bucket/effective-role baseline; PB allowed after the five-prior gate. |
| Limitations | Damage share is team- and hero-dependent; it does not establish fight quality, target value, or causality. |
| Status | LOCKED / DEFERRED; candidate role-metric query does not select the required team damage fields. |
| Evidence / tests | Scalar `heroDamage` is present in the broader STRATZ player projection; no V1 progression calculator exists. |

#### `carry.tower_damage_share.v1` — Tower Damage Share

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
| Baseline / PB | Carry-only history within each progression bucket; PB allowed after the five-prior gate. |
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
| Baseline / PB | Mid-only history within each progression bucket; PB allowed after the five-prior gate. |
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
| Baseline / PB | Mid-only history within each progression bucket; PB allowed after the five-prior gate, using the lower-is-better direction. |
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
| Baseline / PB | Mid-only history within each progression bucket; PB allowed after the five-prior gate. |
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
| Baseline / PB | Mid-only history within each progression bucket; PB allowed after the five-prior gate. |
| Limitations | Same primitive as Carry Net Worth at 20:00, but history and PB are entirely Mid-specific. |
| Status | LOCKED / DEFERRED; no calculator exists in the candidate role-metric module. |
| Evidence / tests | Cumulative net-worth semantics are documented in `services/api/app/player_analysis_v7/research/pass2_tables.py`. |

#### `mid.tower_damage_share.v1` — Tower Damage Share

| Field | Contract |
|---|---|
| Role / version | Mid / v1 |
| Definition / formula | `player tower damage / total tower damage by player's team`. It is mathematically the same as Carry Tower Damage Share but is a separate track. |
| Raw STRATZ/canonical inputs | Player and allied `towerDamage`. |
| Raw/display value | Player tower damage and team total as supporting evidence. |
| Comparison value | Tower-damage share ratio. |
| Direction | Higher is better. |
| Zero rule | Positive team tower damage plus player zero damage yields measured `0%`. |
| N/A rule | Team tower damage = 0 or required values missing/malformed. |
| Baseline / PB | Mid-only history within each progression bucket; PB allowed after the five-prior gate. |
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
| Baseline / PB | Offlane-only history within each progression bucket; PB allowed after the five-prior gate. |
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
| Baseline / PB | Offlane-only history within each progression bucket; PB allowed after the five-prior gate. |
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
| Baseline / PB | Offlane-only history within each progression bucket; PB allowed after the five-prior gate. |
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
| N/A rule | No enemy towers, missing/malformed tower report, missing/malformed proximity events, or missing player side yields N/A. There is no automatic fallback to Tower Damage Share. |
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
| Baseline / PB | Support-only history within each progression bucket; PB allowed after the five-prior gate. |
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
| Baseline / PB | Rate enters the matching progression-bucket Support history; PB uses the comparison rate after the five-prior gate. |
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
| Baseline / PB | Rate enters the matching progression-bucket Support history; PB allowed after the five-prior gate. |
| Limitations | Do not claim Observer-only destruction, information denial quality, or downstream impact. |
| Status | LOCKED / DEFERRED; the candidate query and normalizer do not yet expose the required event stream to this calculator. |
| Evidence / tests | The broader pass-2 query selects `wardDestruction`, but older research marked its subtype semantics unresolved; V1 therefore counts attributed events without subtype claims. |

#### `support.camps_stacked.v1` — Camps Stacked

| Field | Contract |
|---|---|
| Role / version | Support / v1 |
| Definition / formula | Cumulative camps stacked at the canonical 20:00 checkpoint. |
| Raw STRATZ/canonical inputs | Player stats.campStack, normalized as self.trajectories.camp_stack. |
| Raw/display value | camps_stacked_at_20 |
| Comparison value | The same cumulative count at 20:00. |
| Direction | Higher is better. |
| Zero rule | A valid 20:00 checkpoint with cumulative value 0 is measured as numeric 0. |
| N/A rule | N/A when the match ends before 20:00, the series is missing, malformed, or non-monotonic, or the 20:00 checkpoint is unavailable. |
| Baseline / PB | The @20:00 count is used for both the recent baseline and all-known PB history in the matching progression identity; no final-match fallback is allowed. |
| Limitations | Stacking opportunity is concentrated earlier in the game; final totals reward longer matches. A stack action is observable, while later ally consumption, safety, opportunity cost, and resource effectiveness are not. Do not call this Resources Enabled. |
| Status | LOCKED / IMPLEMENTED / VALIDATED on candidate branch d691008; implementation conflict: candidate reads the final cumulative value instead of the @20:00 checkpoint; absent from main. |
| Evidence / tests | Repository pass2_tables.trajectory() clips standard trajectories to a defensive duration bound but explicitly does not establish a universal array offset. The normative extraction must use a validated time-aligned trajectory adapter, select the sample labeled elapsed time 1,200 seconds exactly, and return N/A when that labeled checkpoint is unavailable; never guess series[20], use a nearest sample, or fall back to the final value. |

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
| Baseline / PB | Rate enters the matching progression-bucket Support history; PB uses the rate after the five-prior gate. |
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
| Carry/Mid Tower Damage Share | Player tower damage | Player tower damage / team tower damage |
| Mid/Offlane/Support Fight Presence | Credited numerator and denominator | Numerator / denominator |
| Mid Early Fight Presence | Early credited numerator and denominator | Early numerator / early denominator |
| Offlane Objective Involvement | Credited towers / total enemy towers | Credited-tower ratio |
| Support Wards Placed | Observer ward count | Observer wards per 10 minutes |
| Support Vision Denial | Deward event count | Dewards per 10 minutes |
| Support Healing | `heroHealing` amount | Healing per 10 minutes |
| Support Camps Stacked | Cumulative count at 20:00 | Same cumulative @20:00 count |

All remaining registry metrics use their raw value as their comparison value.
The baseline, delta, and PB must use the comparison column, never an ad hoc UI
conversion. A formula change between raw and comparison values requires a new
metric version.

## 11. Personal Best contract

V1 has Personal Best only. It has no Season Best and no broader achievement
system.

A PB is scoped by progression bucket, effective role, metric ID, and metric
version. It requires:

- a measured current observation;
- an eligible progression context;
- at least five previous measured observations for the same
  `progression_bucket + effective_role + metric_id + metric_version` identity so
  the recent baseline is ready;
- all eligible historical measured observations currently known for that same
  progression identity; and
- comparison in the metric's declared direction.

### LOCKED OWNER DECISION — comparison value

The PB record is determined by the metric's canonical comparison_value, not
necessarily its raw/display value. Normalized metrics therefore earn PBs on
their normalized comparison basis:

- Support Wards Placed: wards_per_10, not raw ward count.
- Support Vision Denial: dewards_per_10, not raw deward count.
- Support Healing: healing_per_10, not raw heroHealing.
- Carry Survival: dead_time_rate, not raw total_dead_seconds; lower is better.

The UI may display a raw amount, but the backend PB record is determined by
comparison_value.

For a higher-is-better metric:

    current_comparison_value > historical_best_comparison_value

For a lower-is-better metric:

    current_comparison_value < historical_best_comparison_value

Strict inequality only. Exact ties do not create a new PB. Prefer retaining
the earliest record/source match when the current value equals the historical
best or when multiple historical observations share that best value, unless a
later separate product decision changes that rule.

The historical comparison set includes all eligible prior observations currently
known for the `progression_bucket + effective_role + metric_id + metric_version`
identity, not only the recent-20 baseline.
A raw value can be higher while its normalized comparison value is lower than
the existing PB; that observation does not create a PB. N/A, insufficient
history, unsupported modes, and unsupported metrics never create one.

Trustworthy eligible imported or recovered observations are admitted to the
same progression-bucket/role/metric/version history once their provenance and
eligibility are validated. They may update the current best-known PB/index and
future comparisons, but never create a retroactive celebration event or rewrite
an already-finalized match snapshot. The append-only celebration ledger is
distinct from current derived PB truth.

## 12. Role correction impact

Role correction changes only the affected match's effective role and the
derived histories that depend on it, within the same progression bucket:

```text
Support → Carry
```

must:

- remove the match from every old-role metric history and PB index;
- add it to each available new-role metric history for which its frozen source
  telemetry is valid;
- recalculate all chronologically later affected progression snapshots and
  current PB indexes for the old and new roles only, using the original metric
  versions;
- invalidate unpublished affected outputs and recompute them before READY; and
- leave every other bucket, role, and unaffected match unchanged.

The original predicted role/confidence may remain as metadata elsewhere. It is
not a second progression role. Role correction does not change the metric
definition or fabricate unavailable telemetry. Already-delivered PB
celebrations/notifications are immutable ledger events: do not retract or
re-send them; if exposed, mark them superseded/auditable while current derived
truth reflects the correction.

### NON-NORMATIVE IMPLEMENTATION AUDIT

The candidate implementation has no persistent history or recalculation path;
this behavior is therefore a required future batch, not an existing feature.

## 13. Hard invariants

- Heroes do not split role progression.
- STANDARD and TURBO are eligible progression buckets with identical V1 metric
  definitions and rules, but histories, baselines, PB indexes, ordering, and
  finalization are completely isolated.
- Carry, Mid, Offlane, and Support histories never contaminate one another.
- The same formula in two roles still means two progression tracks.
- Progression consumes effective_role and never independently reclassifies the player.
- The current match never enters its own baseline.
- A baseline uses at most the previous 20 eligible observations.
- Every observation, baseline, and PB index uses the identity
  `progression_bucket + effective_role + metric_id + metric_version`.
- PB history uses all currently known eligible prior observations for the same
  `progression_bucket + effective_role + metric_id + metric_version` identity;
  it is not limited to the baseline window.
- Five prior measured observations are required before comparison/PB.
- The baseline statistic is the median, not the mean.
- Matches below 600 seconds are INELIGIBLE_FOR_PROGRESSION.
- Ambiguous competitive-integrity evidence fails closed.
- N/A never becomes zero.
- N/A never enters a baseline, history count, or PB.
- A legitimate zero remains zero.
- Camps Stacked uses the cumulative count at the exact 20:00 checkpoint and never falls back to the final count.
- Ranked and unranked All Pick enter STANDARD; Turbo enters TURBO. Ability
  Draft, Captain's Mode, and other unsupported modes never enter progression
  histories and receive an explicit ineligible classification.
- Every metric definition is versioned.
- A formula, input, boundary, denominator, direction, zero/N/A rule, or
  normalization change requires a new metric version or an explicit migration.
- A Dota patch change alone does not reset progression history.
- A role correction deterministically rebuilds only affected same-bucket old/new
  role histories, downstream snapshots, and current PB indexes; immutable
  celebration events are not retracted or re-sent.
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

- Mid Tower Influence is not a V1 metric. Mid uses Tower Damage Share.
- Hero-specific baselines are not a V1 default.
- Position 4 and Position 5 are not separate progression roles.
- There is no universal player score, population percentile, recommendation,
  medal, challenge, Season Best, or achievement catalog in this SSOT.

## 15. Open decisions

No owner decision remains open.

Provider enum meanings for remake, safe-to-leave, and abandon-like states require
implementation validation, but the product rule is already locked: ambiguous
competitive integrity fails closed. Camps Stacked @20:00 definition, PB comparison basis,
PB tie behavior, role input, progression bucket isolation, imported/recovered
history treatment, Tower Damage Share naming, and the 600-second duration gate
are not open decisions.

## 16. Explicitly out of scope

This SSOT does not specify:

- match discovery, processing lifecycle, retries, and refresh strategy;
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
  reasons, effective-role input boundary, 600-second gate, fail-closed
  integrity policy, Tower Damage Share IDs, and unsupported Control explicit.
- **Requirements:** Add missing IDs/specs; preserve
  `progression_bucket + effective_role + metric_id + metric_version` identity;
  consume progression_bucket and effective_role; enforce the median baseline,
  the 600-second progression gate, and fail-closed integrity policy; use
  carry.tower_damage_share.v1 and mid.tower_damage_share.v1 for both isolated
  buckets.
- **Likely modules:** `services/api/app/progression/role_metrics.py` and its
  unit tests; no ingestion or persistence changes.
- **Prerequisites:** This SSOT; provider enum mapping is implementation
  validation, not an additional product decision.
- **Tests:** Registry count/uniqueness, complete bucket + role + metric +
  version identity, effective-role input, 600-second boundary, fail-closed
  integrity, zero/N/A, median versus mean, Tower Damage Share IDs, both bucket
  definitions, bucket isolation, and unsupported Control.
- **Definition of Done:** One registry contains all 20 active metrics exactly
  once, every status is truthful, and no candidate code violates the median
  invariant.
- **Out of scope:** New provider fields, persistence, PB import, role
  correction, and UI.

**NON-NORMATIVE IMPLEMENTATION AUDIT — candidate status:** PARTIAL, not merge-ready. Five calculators and the
eligibility/window helpers exist, but the registry is incomplete and the
median, 600-second, effective-role, and integrity conflicts remain.

### Batch B — Implement the remaining metric calculators and inputs

- **Goal:** Add Carry, Mid, Offlane, and Support calculators not present in the
  candidate branch while preserving the exact registry formulas.
- **Requirements:** CS checkpoints/windows, NW@10/NW@20, level-6 timestamp,
  dead-time intervals, Tower Damage Share inputs, Offlane/Mid lane opponent
  identity, Offlane Fight Presence, Observer Wards, Vision Denial, Camps
  Stacked @20:00, and the renamed Carry/Mid Tower Damage Share contracts.
- **Likely modules:** progression calculators plus the minimal role-metric
  STRATZ query/normalizer fields and tests.
- **Prerequisites:** Batch A; validated provider shapes for any missing field.
- **Tests:** checkpoint boundaries, 15:00/20:00 boundaries, team denominators,
  Radiant/Dire orientation, ward type mapping, Camps @20:00 checkpoint behavior,
  missing telemetry, and zero/N/A.
- **Definition of Done:** Every active registry entry has one calculator or an
  explicit unavailable state; no fallback invents a value.
- **Out of scope:** History persistence, baseline windows, PB persistence, and
  role corrections.

**NON-NORMATIVE IMPLEMENTATION AUDIT — candidate status:** PARTIAL. Five metric calculators are implemented and
validated on `d691008`; 15 active metrics remain without calculators.

### Batch C — Bucket- and role-isolated observation histories

- **Goal:** Record eligible measured observations by
  `progression_bucket + effective_role + metric ID + metric version`.
- **Requirements:** Exclude N/A, unsupported modes, malformed contexts, and
  other bucket/roles; preserve raw/comparison values and provenance; never mix
  buckets or versions.
- **Likely modules:** progression domain/history repository and focused tests.
- **Prerequisites:** Batch A and B; persistence design is otherwise out of
  scope for this document.
- **Tests:** Standard/Turbo separation, cross-bucket independence, Carry/Mid
  separation, hero changes within Carry, Support 4/5 merging, N/A omission,
  and complete identity-key isolation.
- **Definition of Done:** A match can update only its effective role's valid
  metric histories.
- **Out of scope:** Match discovery, database technology choice, UI, and PB
  celebration.

**NON-NORMATIVE IMPLEMENTATION AUDIT — candidate status:** NOT IMPLEMENTED.

### Batch D — Rolling personal baselines

- **Goal:** Compute the recent-20 rolling median baseline with the five-prior
  gate and keep it separate from all-known PB history.
- **Requirements:** Current exclusion, deterministic chronology, N/A omission,
  `BASELINE_BUILDING`/`BASELINE_READY`, bucket/role/metric-version isolation,
  and an explicit separation between the recent-20 baseline window and
  all-known-history PB.
- **Likely modules:** baseline resolver and tests.
- **Prerequisites:** Batch C.
- **Tests:** Exactly four prior, exactly five prior, >20 prior, out-of-order
  rows, current-row duplication, median values where mean differs, and parallel
  Standard/Turbo histories that never cross-read.
- **Definition of Done:** Sixth eligible measured observation is comparable and
  every baseline is a median of at most 20 prior observations.
- **Out of scope:** PB records, role correction, and copy.

**NON-NORMATIVE IMPLEMENTATION AUDIT — candidate status:** PARTIAL. The in-memory prior-window helper and minimum
gate exist, but the candidate uses mean and has no persisted history boundary.

### Batch E — Comparison engine and value semantics

- **Goal:** Emit raw/display values, comparison values, units, direction, deltas,
  and explicit unavailable reasons for every registry metric.
- **Requirements:** Apply rates/shares exactly as registered; use percentage
  points for rate deltas; invert lower-is-better direction; retain raw context.
- **Likely modules:** progression comparison DTO/domain and tests.
- **Prerequisites:** Batch B and D; the fixed Camps Stacked @20:00 comparison
  contract.
- **Tests:** Camps Stacked @20:00 extraction and no-final-fallback behavior,
  Healing/Wards/Dewards per-10, dead-time rate, Tower Damage Share
  denominators, higher/lower deltas, and N/A/zero states.
- **Definition of Done:** No caller must infer whether raw and comparison values
  differ.
- **Out of scope:** UI wording, charts, and recommendations.

**NON-NORMATIVE IMPLEMENTATION AUDIT — candidate status:** PARTIAL. The five candidate calculators carry raw and
  normalized values, but final-value Camps extraction conflicts with the locked
@20:00 contract.

### Batch F — Personal Best engine

- **Goal:** Persist and expose bucket/role/metric/version PBs derived from ready
  histories.
- **Requirements:** Five-prior baseline gate, comparison_value PB basis, strict
  direction-aware inequality, no tie PB, no N/A PB, all-known eligible-history
  PB scope, complete progression-bucket + role + metric + version isolation, and
  admitted trustworthy imported/recovered history updating current PB indexes
  without celebration or snapshot rewrite.
- **Likely modules:** PB domain/repository and tests.
- **Prerequisites:** Batch C, D, E; validated import/recovery provenance.
- **Tests:** Higher/lower records, exact ties, normalized metrics, insufficient
  history, all-known history beyond 20, normalized-value-vs-raw-value conflict,
  N/A, unsupported mode, role isolation, Standard/Turbo isolation, imported or
  recovered rows, and no retroactive celebration.
- **Definition of Done:** Every PB is reproducible from the versioned history;
  no PB is awarded offline or from fabricated data.
- **Out of scope:** Season Best, medals, challenges, notifications, and UI
  celebration.

**NON-NORMATIVE IMPLEMENTATION AUDIT — candidate status:** PARTIAL. It returns an in-memory boolean for five
  calculators; no persisted PB engine or import behavior exists.

### Batch G — Role-correction recalculation

- **Goal:** Deterministically rebuild affected histories and PBs after an
  effective role correction.
- **Requirements:** Within one progression bucket, remove old-role observations,
  add valid new-role observations from the frozen source and original metric
  versions, rebuild chronologically later affected snapshots/current PB indexes
  for old and new roles only, and leave other buckets/roles unchanged. Keep
  delivered celebration events immutable and auditable; never retract or resend.
- **Likely modules:** history rebuild service, correction record, and tests.
- **Prerequisites:** B through F and an owner-approved correction boundary.
- **Tests:** Support→Carry, reverse correction, missing new-role telemetry,
  repeated corrections, correction during processing, idempotence, same-bucket
  downstream rebuild, cross-bucket independence, and unaffected-role snapshots.
- **Definition of Done:** Rebuilding the same corrected match set twice produces
  identical histories and records.
- **Out of scope:** Role-assignment design, match refresh, and mobile routes.

**NON-NORMATIVE IMPLEMENTATION AUDIT — candidate status:** NOT IMPLEMENTED.

### Batch H — Feature acceptance suite

- **Goal:** Prove the complete contract with deterministic fixtures.
- **Requirements:** Acceptance matrix below, both buckets and their independence,
  all edge states, no provider calls, and no OpenDota calls.
- **Likely modules:** progression unit/integration tests and sanitized canonical
  fixtures only.
- **Prerequisites:** B through G.
- **Tests:** Every matrix row, including effective-role authority, bucket
  isolation and cross-bucket independence, role isolation, median, 600-second
  duration, fail-closed integrity, N/A/zero, Camps @20, Tower Damage Share
  naming, normalized comparison-value PBs, all-known PB history, ties, imported
  history, and correction rebuild.
- **Definition of Done:** The suite fails on mean-vs-median regression, role
  contamination, current inclusion, metric-version mixing, or missing-data
  coercion.
- **Out of scope:** Browser E2E, UI, deployment, and live provider collection.

**NON-NORMATIVE IMPLEMENTATION AUDIT — candidate status:** PARTIAL. The candidate has focused tests for five
calculators and the query; the feature-level suite does not exist.

## 18. Acceptance matrix

| Acceptance case | Expected contract behavior | Current evidence/status |
|---|---|---|
| Luna Carry and Slark Carry | Both update the same Carry metric track. | Contract; persistence test pending. |
| Mid match versus Carry history | Mid never changes Carry history. | Candidate role filter supports this; end-to-end history test pending. |
| Carry versus Mid Tower Damage Share | Same formula may be reused, but histories/PBs remain separate. | Contract; registry implementation pending. |
| Standard versus Turbo match | Both may be measured and update/compare only within their own bucket; they use identical metric definitions and rules. | Contract; bucket-isolation test pending. |
| Cross-bucket ordering | A Standard predecessor never blocks or releases a Turbo queue, and vice versa. | Contract; lifecycle/integration test pending. |
| Fifth prior observation | Five prior measured values are enough for the next observation to compare. | Contract; exact boundary test required. |
| Current match | Never included in its own baseline. | Candidate helper/test covers current exclusion. |
| More than 20 prior observations | Only the 20 most recent prior eligible values are used. | Candidate helper has cap; exact 21-row test required. |
| Median versus mean | Baseline is median, including when it differs from mean. | **FAIL:** candidate uses `fmean`; must be fixed. |
| Match ends before 20:00 | NW@20 is N/A. | Calculator not implemented. |
| N/A observation | Omitted from the matching bucket/role/metric/version baseline and PB history. | Candidate comparison filters unmeasured values; persistence test pending. |
| Zero Healing | Raw and comparison value remain 0 when duration/telemetry are valid. | Candidate test passes on candidate branch. |
| Zero team kills | Fight Presence is N/A, not zero. | Candidate Support/Mid tests cover this on candidate branch. |
| Positive team tower damage plus player zero damage | Tower Damage Share is measured at 0%. | Calculator/test pending. |
| Zero team tower damage | Tower Damage Share is N/A. | Calculator/test pending. |
| Wards Placed | Raw observer count is retained; baseline compares wards per 10. | Contract; calculator pending. |
| Vision Denial | Raw deward count is retained; baseline compares dewards per 10; no subtype claim. | Contract; calculator pending. |
| Healing | Raw `heroHealing` is retained; baseline compares healing per 10. | Candidate test passes on candidate branch. |
| Survival | Lower dead-time rate is favorable; PB direction is inverted. | Calculator/test pending. |
| Mid Early Fight Presence at 15:00 | Events at exactly 900 seconds count; events after 900 do not. | Candidate test passes on candidate branch. |
| Offlane Objective Involvement orientation | Only enemy-side towers count for Radiant/Dire; NPC joins and 60-second prior events apply. | Candidate tests pass on candidate branch. |
| Support Control | Cannot appear as an available V1 metric or use a proxy. | Candidate negative test passes; exclude from active registry. |
| Role correction Support→Carry | In the same bucket, remove old-role observations, add valid new-role observations from the frozen source/version, rebuild chronologically later affected snapshots/current PB indexes for old/new roles only, and leave delivered celebration events immutable. | Not implemented. |
| Metric version change | Old and new version observations never mix. | Contract; persistence test pending. |
| Confirmed effective role versus provider position | A user-confirmed Carry remains Carry even when provider position data differs; progression consumes effective_role and does not override it. | Contract; upstream integration test pending. |
| Tower Damage Share naming | Carry and Mid use Tower Damage Share with the same formula but separate bucket/role histories and IDs. | Contract; registry implementation pending. |
| Baseline versus PB scope | With 30 previous eligible observations, baseline uses the latest 20 while PB checks all 30. | Contract; persistence/PB test pending. |
| PB comparison basis | A raw value that is higher while its normalized comparison value is below the existing PB does not create a PB. | Contract; PB test pending. |
| PB tie | Current comparison value exactly equal to historical best does not create a PB; earliest record/source match is retained. | Contract; PB test pending. |
| Imported/recovered history | Trustworthy eligible observations can update current best-known PB/index and future comparisons after admission, but never create retroactive celebration events or rewrite finalized snapshots. | Contract; import/recovery test pending. |
| Camps Stacked @20:00 | If the cumulative count is 3 at 20:00 and 6 at match end, the metric, baseline, and PB value are 3. | Contract; checkpoint extraction test pending. |
| Camps Stacked zero | A valid 20:00 cumulative value of 0 is measured zero. | Contract; checkpoint test pending. |
| Camps Stacked missing checkpoint | No valid 20:00 checkpoint yields N/A with no final-value fallback. | Contract; checkpoint test pending. |
| Duration boundary | 599 seconds is progression-ineligible; 600 seconds passes the duration gate when other requirements are valid. | Contract; boundary test pending. |
| Eligible match with unavailable checkpoint | A valid 18-minute All Pick can be match-eligible while NW@20 and Camps Stacked @20 are N/A and earlier/full-match metrics still participate. | Contract; match-versus-metric test pending. |
| Ambiguous competitive integrity | Provider evidence cannot confidently distinguish a remake, safe-to-leave, or abnormal match, so progression fails closed as ineligible. | Contract; provider mapping/integrity test pending. |

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

The pre-production Carry and Mid Tower Damage Share IDs are
carry.tower_damage_share.v1 and mid.tower_damage_share.v1. The former
legacy names are not active V1 IDs.

A Dota patch change by itself does not reset a role history. If a provider
schema or game-rule change materially changes a metric's meaning, create a new
metric version and define migration/recalculation explicitly. Never silently
mix versions in one baseline or PB record.

This document is the contract future implementation agents must follow. Any
product change to metric meaning, eligibility, baselines, comparisons, or
records must update this SSOT before code changes land. Older research remains
historical evidence and cannot override this file.
