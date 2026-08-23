# Beyond the scoreboard: a forensic product study of one parsed OpenDota match

> If parsed OpenDota data were exploited almost absurdly well, what could we tell a Dota player about themselves that ordinary stat sites do not?

## Executive conclusion

The strongest product is not a dashboard. It is an evidence-backed behavioral mirror that says, in plain Dota language, **what context repeatedly triggers a decision, what the player does next, and what that choice costs**.

The parsed match endpoint is rich enough to support this direction, but less omniscient than its field count suggests. This specimen contains 55 top-level fields and 147 distinct player fields, including 450 timestamped purchases, all 47 hero kills, 96 timestamped ward placements, minute economy/XP/CS curves, target/source damage matrices, ability and item-use aggregates, draft data, objectives, and parser-defined teamfights. It does **not** expose the raw combat log, ordered full-match movement, exact assist timestamps, exact spell sequences, cooldown/mana state at death, or full inventory snapshots. The product must make that distinction visible internally or it will turn clever inference into fake replay review.

The ceiling is nevertheless high. The best concepts are causal-feeling chains such as:

```text
Fight won
→ player returns to farming while the objective window is open
→ team advantage rises but structures do not fall
→ the same opponent core respawns without paying an objective price
```

surfaced as:

> **You win fights better than you win games.**

The recommended system calculates hundreds of hidden signals, suppresses weak conclusions, and publishes only a handful of high-confidence stories. Every story must separate **observation** (directly measured), **inference** (defensible reconstruction), and **hypothesis** (a coaching interpretation worth checking in replay).

---

# Part 1 — Parsed payload anatomy

## 1.1 Acquisition and specimen integrity

Exactly one OpenDota API request was made:

```text
GET https://api.opendota.com/api/matches/8431600692
```

The response is preserved byte-for-byte at [`opendota-specimen/match_8431600692.raw.json`](./opendota-specimen/match_8431600692.raw.json). Acquisition details and checksum are in [`opendota-specimen/README.md`](./opendota-specimen/README.md).

| Property | Actual specimen |
| --- | --- |
| Match | 8431600692 |
| Match context | Team Falcons vs Team Spirit, FISSURE Universe Episode 6 |
| Mode / lobby | Captains Mode / practice lobby used for a professional match |
| Patch | OpenDota patch ID 58 (`7.39`) |
| Duration | 2,185 seconds (36:25), plus 90 seconds pre-game |
| Result | Falcons/Radiant 35–12 Spirit/Dire |
| Payload | 288,313 bytes; SHA-256 `7c0f73a8af1abd3e015a806a8b10289d801046cfca4a8b113a93e7409525edd5` |
| Parse proof | `version = 22`; `od_data.has_parsed = true` |
| Identity | 10/10 account IDs and persona names |
| Major arrays | 51 chat events, 29 objectives, 24 draft timings, 24 picks/bans, 37 gold-advantage points, 37 XP-advantage points, 2 teamfights |
| Player telemetry | 450 purchases, 47 kills, 5 buybacks, 46 rune pickups, 34 observer placements, 62 sentry placements, 1,850 aligned player-minute values across `times`/gold/XP/last-hit/deny arrays |

The match was chosen as a schema specimen, not as a behavioral baseline. Its professional context guarantees excellent identity and telemetry coverage, but pro coordination, role clarity, drafting, itemization, and ward economy differ radically from pubs. No product threshold or personality conclusion below is calibrated from this one match.

## 1.2 Where each field comes from

The response is a joined product, not a single replay-native record.

| Provenance layer | Examples | Product implication |
| --- | --- | --- |
| Valve match details | result, duration, final K/D/A, items, scores, lobby, teams | Usually authoritative end-state facts, but not replay chronology. |
| Game Coordinator / league metadata | replay salt, party IDs, permanent buffs, series/team identity | Useful context; availability differs for pubs and anonymous players. |
| Replay parser | ward logs, purchase/kill/rune logs, minute curves, `lane_pos`, ability/item uses, damage matrices, teamfights | Richest behavioral material; subject to parser version, heuristics, and missing replay coverage. |
| OpenDota post-processing | patch/region, win/lose, KDA, lane efficiency, position estimate, item summaries, `throw`/`loss`, percentiles | Derived rather than observed. Algorithms and comparison populations must be versioned. |
| Profile/database enrichment | persona name, rank tier, subscriber/contributor flags, computed MMR | Time-sensitive and potentially observed after the match, not necessarily at match time. |

This provenance distinction is supported by OpenDota's [open-source core](https://github.com/odota/core), its [parser](https://github.com/odota/parser), and the database split between match/player fields in [`create_tables.sql`](https://github.com/odota/core/blob/master/sql/create_tables.sql). OpenDota's [`compute.ts`](https://github.com/odota/core/blob/master/svc/util/compute.ts) shows which familiar-looking fields are post-processed calculations.

## 1.3 Complete match-level inventory

The specimen has 55 top-level keys. The table groups every one by meaning while preserving exact names.

| Family | Exact fields | Representation / granularity | Behavioral value and combinations |
| --- | --- | --- | --- |
| Identity and time | `match_id`, `match_seq_num`, `start_time`, `duration`, `pre_game_duration` | Static match facts | Align patches, longitudinal order, clock windows, and per-minute normalization. |
| Outcome | `radiant_win`, `radiant_score`, `dire_score`, `first_blood_time` | Static/aggregate | Context for every conditional behavior; scores alone do not say when the game changed. |
| Mode/context | `game_mode`, `lobby_type`, `human_players`, `leagueid`, `league`, `series_id`, `series_type`, `region`, `cluster`, `patch`, `engine`, `flags` | Static categorical | Mandatory cohort filters. Never compare Turbo, pro Captains Mode, ranked pubs, and unranked stacks without stratification. |
| Team identity | `radiant_team_id`, `radiant_name`, `radiant_logo`, `radiant_team_complete`, `radiant_captain`, `radiant_team`; Dire equivalents | Static relational | Stable teams, captains, side, and repeated teammate effects; often null in pubs. |
| Structures | `tower_status_radiant`, `tower_status_dire`, `barracks_status_radiant`, `barracks_status_dire` | Final bitmasks | End-state validation. Combine with timestamped `building_kill` objectives for conversion sequencing. |
| Advantage curves | `radiant_gold_adv`, `radiant_xp_adv` | One value per minute; 37 each here | Ahead/behind state, lead changes, comeback/throw context, and before/after windows. Minute resolution is not fight-tick precision. |
| Objectives | `objectives` | Timestamped heterogeneous events; 29 here | Towers/barracks, Roshan, Aegis, first blood, courier deaths. Combine with kill clusters and purchase spikes to study conversion. |
| Teamfights | `teamfights` | Parser-defined windows; 2 here | Per-player fight aggregates and death positions. This is a heuristic event reconstruction, not a complete engagement list. |
| Draft | `picks_bans`, `draft_timings` | Ordered pick/ban records; 24 each | Composition, pick order, captain timing, hero context, and item/target adaptation. Primarily useful in Captains Mode. |
| Communication | `chat`, `all_word_counts`, `my_word_counts` | Timestamped all-chat/chat-wheel events plus token counts | Potential communication style, but high privacy/context risk; team voice and most team chat are absent. Not suitable for emotional diagnosis. |
| Cosmetics | `cosmetics` | Match-level item/cosmetic mapping | Little gameplay value; useful only for presentation/profile identity. |
| Parse/provenance | `version`, `od_data`, `replay_salt`, `replay_url`, `metadata` | Parse state and replay linkage | Coverage gates, parser-version cohorts, auditability, and potential replay deep-linking. |
| OpenDota extrema | `throw`, `loss` | Derived maximum gold-advantage quantities | Coarse match labels. In this response they are duplicated into every player; they do not attribute responsibility. |

### Objective event schemas observed

| Type | Count | Fields | Meaning / caveat |
| --- | ---: | --- | --- |
| `building_kill` | 20 | `time`, `unit`, `key`, `slot`, `player_slot`, `type` | Timestamped tower/barracks destruction and credited unit/player. Controlled units and summons complicate attribution. |
| `CHAT_MESSAGE_COURIER_LOST` | 4 | `time`, `value`, `killer`, `team`, `type` | Courier death event; fields are chat-event protocol values, not self-describing names. |
| `CHAT_MESSAGE_ROSHAN_KILL` | 2 | `time`, `team`, `type` | Roshan death and team. Does not by itself prove who participated. |
| `CHAT_MESSAGE_AEGIS` | 2 | `time`, `slot`, `player_slot`, `type` | Aegis pickup/holder. Does not expose later transfer/drop or expiry directly. |
| `CHAT_MESSAGE_FIRSTBLOOD` | 1 | `time`, `slot`, `key`, `player_slot`, `type` | First-blood event. Cross-check with `first_blood_time` and kill logs. |

## 1.4 Complete player-level inventory

All 10 player objects expose a union of 147 fields. Every family below states granularity, scope, type, normalization, and the behavioral question it can support.

### Identity, roster, role, and outcome

Fields: `account_id`, `personaname`, `name`, `player_slot`, `team_number`, `team_slot`, `hero_id`, `hero_variant`, `isRadiant`, `radiant_win`, `win`, `lose`, `rank_tier`, `computed_mmr`, `party_id`, `party_size`, `position_est`, `lane`, `lane_role`, `is_roaming`, `pred_vict`, `randomed`, `firstblood_claimed`, `is_contributor`, `is_subscriber`, `last_login`, plus duplicated `cluster`, `region`, `patch`, `game_mode`, `lobby_type`, `start_time`, and `duration`.

- **Granularity/type:** static per player with match-level context duplicated into each object.
- **Scope:** all players and both teams; profile fields may be null or reflect later database state.
- **Normalization:** role, hero, bracket, party size, side, patch, and game mode are mandatory.
- **Behavioral use:** role expectation versus actual farm/ward/damage behavior; stable party effects; facet-specific identity; lane recovery.
- **Important caveat:** `position_est` is an OpenDota heuristic. Current source ranks 10–12 minute gold/last hits, uses early ward purchases as a support tie-breaker, and then uses `lane_role`; it is not an official role label. In the specimen it correctly separates positions 1–5, but professional roles make that unusually easy.

### Final combat and survival aggregates

Fields: `kills`, `deaths`, `assists`, `kda`, `kills_per_min`, `kill_streaks`, `multi_kills`, `hero_damage`, `hero_healing`, `tower_damage`, `stuns`, `max_hero_hit`, `life_state`, `life_state_dead`, `leaver_status`, `abandons`, `buyback_count`, `firstblood_claimed`, `teamfight_participation`.

- **Granularity/type:** end-of-match totals or summary maps; `max_hero_hit` is one timestamped extreme.
- **Behavioral use:** outcome, frontline tolerance, finisher/setup profiles, survival burden, and broad fight participation.
- **Combine with:** role, duration, damage sources/targets, teamfight windows, minute advantage, kills/death reconstruction, and item timings.
- **Do not infer:** initiation timing, exit timing, spell availability, or usefulness of a death from totals alone.

### Kill/death relationships

Fields: `kills_log`, `killed`, `killed_by`, plus objective/teamfight deaths.

- **Granularity/type:** `kills_log` is timestamped `{time,key}` per hero kill; `killed` counts every unit type; `killed_by` counts enemy heroes responsible for deaths.
- **Actual coverage:** 47 `kills_log` rows, equal to the 35–12 final score after self-kill filtering.
- **Reconstruction:** invert all players' `kills_log` rows by victim hero to estimate death time and killer. This is reliable in ordinary unique-hero modes but needs guards for suicides, denied heroes, reincarnation, Arc Warden/Meepo edge cases, illusions, controlled units, and parser filtering.
- **Behavioral use:** chain deaths, revenge kills, nemesis concentration, death order inside kill clusters, cleanup behavior, and post-death choices.
- **Missing:** assist timestamps and raw damage chronology. A kill cluster is not automatically a teamfight.

### Economy and CS time series

Fields: `times`, `gold_t`, `xp_t`, `lh_t`, `dn_t`, `gold`, `gold_per_min`, `xp_per_min`, `net_worth`, `gold_spent`, `total_gold`, `total_xp`, `last_hits`, `denies`, `level`, `gold_reasons`, `xp_reasons`, `lane_efficiency`, `lane_efficiency_pct`.

- **Granularity/type:** 37 aligned minute points for every player in this match; cumulative totals and reason-code maps.
- **Actual coverage:** 10 players × 5 aligned arrays × 37 points = 1,850 values, plus 74 team advantage values. Counting the four behavioral curves (`gold_t`, `xp_t`, `lh_t`, `dn_t`) yields 1,480 player-minute measurements.
- **Semantics:** parser source writes total earned gold/XP and cumulative last hits/denies at each minute. `gold_t` is not a current-wallet or net-worth series.
- **Lane efficiency caveat:** OpenDota's current post-processing divides 10-minute gold by a static creep/passive/starting-gold constant. It is patch-sensitive and not a literal percentage of all theoretically available lane gold.
- **Behavioral use:** farm share, resource redistribution, farm reset after events, lane-to-midgame transition, economy volatility, and state-dependent play.
- **Cannot answer exactly:** “250 gold from item” without reconstructing a noisy wallet from earned gold, purchases, buybacks, and item costs. Sales, shared items, reliable/unreliable gold, and assembly details are incomplete.

### Purchases, inventory, and item behavior

Fields: `purchase_log`, `purchase`, `purchase_time`, `first_purchase_time`, `item_usage`, `item_win`, `item_uses`, `purchase_tpscroll`, `purchase_ward_observer`, `purchase_ward_sentry`, `purchase_gem`, final `item_0`–`item_5`, `backpack_0`–`backpack_2`, `item_neutral`, `item_neutral2`, `aghanims_scepter`, `aghanims_shard`, `moonshard`, `neutral_item_history`, `neutral_tokens_log`.

- **Granularity/type:** 450 timestamped purchase rows plus match-wide use counts, final inventory slots, and timestamped neutral-item changes.
- **Behavioral use:** item timing, defensive adaptation, consumable philosophy, major-spike utilization, active-item use rate, ward economy, TP purchasing, and neutral-item fit.
- **Parser-derived summaries:** `purchase_time` is the sum of purchase timestamps per item; `first_purchase_time` is the first; `item_usage` is merely a binary “purchased” flag; `item_win` repeats match outcome. They are convenience fields, not behavior.
- **Missing:** exact item-use timestamps outside detected teamfights, cooldown state, charges, mana, inventory location through time, sales by item/time, swaps, drops, sharing, and component-to-completed-item ownership snapshots.

### Ability behavior

Fields: `ability_upgrades_arr`, `ability_uses`, `ability_targets`.

- **Granularity/type:** ordered upgrade IDs; match-wide use counts; nested ability→target counts. Teamfight windows also contain ability-use and sometimes target counts.
- **Behavioral use:** build adaptation, spell-use frequency, target preference, save-versus-offense tendencies, ultimate conservation proxies, and teamfight contribution.
- **Missing:** exact cast timestamps for the full match, ordered sequences, failed casts, cooldown/mana state, cast position, affected target count for AoE spells, and whether a cast was good. “Panic casting” and exact combos are not defensible from this endpoint.

### Damage, healing, and interaction matrices

Fields: `damage`, `damage_taken`, `damage_inflictor`, `damage_inflictor_received`, `damage_targets`, `hero_hits`, `healing`.

- **Granularity/type:** match-wide dictionaries. `damage_targets` is nested source→target→amount; `damage_taken` maps attacker units to totals; `healing` maps recipient heroes to amount.
- **Behavioral use:** target fixation, backline preference, frontline burden, nemesis damage, spell identity, protector relationships, execution efficiency, and draft/item response to actual incoming sources.
- **Combine with:** hero/role, enemy positions, kills, teamfight aggregates, items, and outcome state.
- **Missing:** chronology for most matrices, damage type, HP percentage, overkill/overheal, visibility, distance, and causal attribution for disables/saves.

### Farm composition and map-resource behavior

Fields: `last_hits`, `denies`, `neutral_kills`, `ancient_kills`, `lane_kills`, `hero_kills`, `tower_kills`, `courier_kills`, `observer_kills`, `sentry_kills`, `roshan_kills`, `necronomicon_kills`, `killed`, `camps_stacked`, `creeps_stacked`, `towers_killed`, `roshans_killed`.

- **Granularity/type:** match-wide counts derived from killed-unit keys and interval/player-resource values.
- **Behavioral use:** creep diet, jungle/lane preference, stacking contribution, objective last hits, dewarding, and role-consistent resource behavior.
- **Missing:** timestamp/location for creep kills and stack clears. The endpoint cannot directly show a full-match farming route, dead-lane farm, neutral-camp circuit, or who consumed a specific stack.

### Spatial behavior

Fields: `lane_pos`, ward logs, and teamfight `deaths_pos`.

- **`lane_pos`:** nested x→y→count grid, sampled only while `time <= 600` in parser source. The aggregation discards sample order and timestamps. It can describe first-10-minute territory, lane assignment, spread, and early roaming—not a trajectory.
- **Ward logs:** exact placement/removal timestamps and x/y/z coordinates, suitable for territorial vision, reaction windows, and ward survival.
- **Death positions:** only inside OpenDota-detected teamfights, stored as coordinate counts. Ordinary pickoffs and many two-death skirmishes have no location.
- **Behavioral use:** early comfort zones, repeated teamfight death zones, ward territory, deward hotspots, and early lane attachment.
- **Not supported:** late-game movement paths, chase distance, fight entry/exit routes, farming circuits, or teleport destinations.

### Vision

Fields: `obs_log`, `obs_left_log`, `sen_log`, `sen_left_log`, `obs`, `sen`, `obs_placed`, `sen_placed`, `observers_placed`, `observer_uses`, `sentry_uses`, `observer_kills`, `sentry_kills`, ward purchases and `item_uses`.

- **Granularity/type:** 96 timestamped placements here, exact coordinates, entity handles, and corresponding leave/destruction records where available.
- **Behavioral use:** proactive/reactive timing, territory, redundancy, ward survival, objective preparation, deward duels, and buyer/placer separation proxies.
- **Caveat:** a leave log can represent expiry or destruction. In this specimen, many sentry leave times occur after match end because the parser projects entity removal/expiry; attacker fields are not sufficient by themselves. Match by entity handle, compare lifetime to patch-specific ward duration, and treat ambiguous removals as censored.

### Runes, buybacks, connection, and special events

Fields: `runes`, `runes_log`, `rune_pickups`, `buyback_log`, `buyback_count`, `connection_log`, `permanent_buffs`, `neutral_item_history`, `neutral_tokens_log`.

- **Granularity/type:** timestamped rune and buyback rows, aggregate rune-type counts, connection events, and special-item/buff history.
- **Behavioral use:** rune conversion, comeback commitment, buyback value, neutral adaptation, and data-quality exclusions for disconnects.
- **Normalization:** rune schedule/type, hero, role, game state, patch, death timer, objective state, and team buybacks.

### Input/actions

Fields: `actions`, `actions_per_min`, `pings`.

- **Granularity/type:** counts by Dota unit-order code, overall APM, total pings.
- **Behavioral use:** action mix/entropy, command complexity, item/ability/train/order style, and longitudinal mechanical change.
- **Caveat:** counts have no timestamps. Current constants do not even label action code `42` seen in the specimen, demonstrating schema drift. APM is not decision quality.

### OpenDota comparison fields

Fields: `benchmarks` with `gold_per_min`, `xp_per_min`, `kills_per_min`, `deaths_per_min`, `assists_per_min`, `last_hits_per_min`, `denies_per_min`, `hero_damage_per_min`, `hero_healing_per_min`, and `tower_damage`; each contains `raw`, `pct`, and sometimes `pct_bracket`.

- **Granularity/type:** per-player percentile enrichment against hero distributions, optionally rank-bracket restricted.
- **Behavioral use:** evidence calibration and peer comparison for simple outcome metrics.
- **Caveat:** not role-, item-, team-state-, or patch-perfect. OpenDota source reads rolling Redis distributions and reverses the direction for deaths. Persist comparison epoch and cohort definition if displayed.

## 1.5 Teamfight anatomy and its hard limit

Each teamfight contains `start`, `end`, `last_death`, `deaths`, and a 10-row `players` array. Per-player rows contain `deaths_pos`, `ability_uses`, `ability_targets`, `item_uses`, `killed`, `deaths`, `buybacks`, `damage`, `healing`, `gold_delta`, `xp_delta`, `xp_start`, and `xp_end`.

OpenDota's [`CreateParsedDataBlob.java`](https://github.com/odota/parser/blob/master/src/main/java/opendota/CreateParsedDataBlob.java) reveals the detector:

1. A real hero death starts a window 15 seconds before that death.
2. Each subsequent hero death extends `last_death`.
3. The window closes on an interval at least 15 seconds after the last death.
4. Windows with fewer than three deaths are discarded.

The specimen has 47 hero deaths but only two teamfights (3 deaths and 7 deaths). Therefore:

- “Detected teamfight” means a specific parser heuristic, not “all meaningful fights.”
- Zero teamfight participation may mean the engagement was omitted.
- The window starts before the first death, not necessarily at initiation.
- Per-player use/damage totals are window aggregates, not ordered actions.
- Exact arrival, departure, initiation, target switching, and spell sequences remain unknown.

Any product using these fields should label them internally as `death_cluster_3plus_v22`, preserve parse version, and reconstruct additional lightweight kill clusters separately rather than silently calling the two records “all fights.”

## 1.6 Reliability hierarchy

| Reliability | Examples | Product treatment |
| --- | --- | --- |
| High: directly timestamped / final state | purchase rows, kill rows, rune rows, ward placements, buybacks, objective times, final stats | Can anchor evidence, after sanity checks. |
| Medium-high: aligned parser state | minute gold/XP/LH/DN, ward removal matched by entity handle | Good for trends; respect sampling resolution and censoring. |
| Medium: aggregate interaction maps | damage sources/targets, ability/item uses, healing recipients, action counts | Strong for repeated tendencies, weak for causal order. |
| Medium-low: parser reconstruction | teamfights, death locations, lane position histogram | Useful when named and versioned as a heuristic. |
| Low without cohort/model | lane efficiency, position estimate, benchmark percentile, throw/loss | Evidence features, not personality truths. |
| Unsupported from this endpoint | full routes, exact fight entry/exit, assist timing, spell sequences, cooldown/mana availability, win probability, current gold through time | Do not claim; require raw replay reprocessing or a different telemetry layer. |

## 1.7 Normalization contract

No behavioral insight should ship without a declared comparison unit. The minimum contract is:

```text
hero × inferred position × bracket × patch family × game mode
× duration band × party-size band × side
```

Add state-specific normalization when relevant:

- **Team state:** gold/XP advantage bucket and numerical alive state.
- **Game phase:** lane (0–10), early midgame (10–20), midgame (20–35), late game.
- **Composition:** initiation burden, save count, wave clear, scaling, global mobility.
- **Opportunity:** detected fights, deaths, completed items, ward purchases, Roshan events—not matches alone.
- **Player history:** empirical-Bayes shrinkage toward the cohort so five flashy games do not become a personality label.
- **Schema:** endpoint, parser version, field coverage, constants version, and reconstruction algorithm version.

---

# Part 2 — Signal map

| Data family | What it tells us | Interesting combinations | Reliability | Normalization needed |
| --- | --- | --- | --- | --- |
| Match context | Mode, patch, side, duration, party/pro status | Every other signal | High | Always stratify |
| Final K/D/A | Outcome footprint | Kill order, damage, role, team result | High but shallow | Per minute, role, hero |
| Kill logs | Exact killer/victim hero and time | Team death order, objectives, streaks, advantage | High-medium | Hero uniqueness, reincarnation, suicides |
| Teamfight windows | Multi-death fight aggregates | Items, abilities, deaths, gold/XP delta | Medium | Detector/version, hero, state |
| Team advantage | Who is ahead each minute | Purchases, deaths, wards, objectives, farm allocation | High-medium | Side, duration, phase |
| Player economy curves | Earned gold and XP trajectory | Team share, event windows, item timing | High-medium | Position, hero, state |
| CS curves | Farming cadence | Deaths, fights, objectives, team allocation | High-medium | Position, hero, phase |
| Purchase log | Exact purchase behavior | Kill/death triggers, spike windows, enemy sources | High | Item graph, patch, role |
| Final inventory | End-state build | Purchase history, enemy damage, match state | High but endpoint-only | Duration, patch, hero |
| Item-use counts | How often actives/consumables were used | Ownership time, fights, deaths | Medium | Charges, item, opportunity |
| Ability uses | Spell frequency | Fight count, cooldown, hero/facet | Medium | Opportunity and cooldown |
| Ability targets | Target preference | Ally role, damage/healing, outcomes | Medium | Ability semantics, target availability |
| Damage sources | Actual sources dealt/received | Items, deaths, draft, target preference | Medium-high aggregate | Hero, role, enemy lineup |
| Damage targets | Who received each source | Kills, roles, fight participation | Medium-high aggregate | Target availability/HP |
| Healing recipients | Who receives sustain/save value | Deaths, role, duo patterns | Medium | Overheal, hero kit |
| Ward placements | When and where vision is placed | Deaths, objectives, state, ward survival | High | Role, team vision burden, patch |
| Ward removals | Survival and deward contest | Entity handles, enemy ward kills, objectives | Medium | Ward duration, censoring |
| Early position grid | First-10-minute territory | Lane role, early kills, lane efficiency | Medium | Side transform, hero mobility |
| Teamfight death position | Where detected-fight deaths occur | Repetition, ward coverage, objective area | Medium-low | Detector coverage, map version |
| Creep/unit kills | Farm composition and utility | CS curves, position, team farm share | Medium-high aggregate | Summons, hero kit, role |
| Stacks | Contribution to future farm | Team economy after stack timing (not exposed) | Medium-low | Role, hero, missing timestamps |
| Runes | Pickup timing/type | Kills, objectives, bottle/item timing | High | Rune schedule, hero/role |
| Buybacks | Commitment and second-life events | Subsequent objectives/kills/deaths | High event, modeled value | Death timer, state, net worth |
| Objectives | Conversion and map progress | Kill clusters, items, buybacks, advantage | High-medium | Objective type, phase, lineup |
| Draft/facet | Strategic expectations | Targets, item adaptation, role burden | High | Patch, captain mode vs pub |
| Actions/APM | Command composition | Hero complexity, longitudinal change | Medium-low | Hero, units controlled, duration |
| Benchmarks | Coarse peer percentiles | Evidence framing | Medium | Cohort epoch and bracket |
| Chat/pings | Observable communication traces | Event windows | Low/context-sensitive | Language, privacy, channel coverage |

## 2.1 High-value combinations ordinary stat sites underuse

1. **Kill/death order + team advantage + player fight survival** → “you do not start bad fights; you stay after they collapse.”
2. **Purchase proximity + earned-gold slope + death time + next objective** → “you become greediest when your item is almost finished.”
3. **Ward time/location + preceding negative events + following objectives** → proactive versus reactive vision.
4. **Won kill cluster + subsequent CS/gold share + structure/Roshan timing** → fight-to-objective conversion personality.
5. **Ahead/behind minute state + farm/fight/ward/item decisions** → winning and losing personalities.
6. **Incoming damage sources + defensive purchase timing + prior deaths** → adaptation speed rather than build correctness.
7. **Healing/ability targets + teammate roles + death order** → protector and duo relationships.
8. **Team farm-share changes around player deaths/fights** → farm entitlement, sacrifice, and recovery style.
9. **Early position grid + lane efficiency + 15/20-minute advantage** → lane attachment, roaming cost, and lane-to-map transition.
10. **Longitudinal phase-specific errors** → improvement, regression, and “the problem moved.”

---

# Part 3 — Ranked insight candidate library

## Reading the library

- **A — Single-match capable:** a meaningful observation can be produced in one match.
- **B — Multi-match required:** repeated behavior is necessary.
- **C — Population baseline required:** a comparable hero/position/bracket/patch cohort is required.
- **D — Model-enhanced:** clustering, spatial models, sequence models, causal adjustment, or anomaly detection materially improves it.
- Evidence lines below are **copy templates**, not claims about the specimen unless explicitly labeled “specimen.”
- Confidence is opportunity-based. “20 matches” is insufficient if it contains only two relevant fights or one buyback.

## #1 — Win Fights, Lose Windows — OOOH 9.35

**OOOH headline:** **You win fights better than you win games.**

**Explanation:** Your team creates real windows—multiple enemies dead, forced buybacks, or an Aegis advantage—but your next action is disproportionately farm/reset rather than tower, Roshan, or map restriction. The problem is not fighting execution; it is recognizing when a won fight has changed what the map allows.

**Evidence:** “After 31 clear fight wins, your team secured an objective within 90 seconds 42% of the time. Comparable position-2 players convert 61%; your personal CS share instead rises from 24% to 34% during those windows.”

**Why care:** Unconverted wins let the enemy respawn without paying a structural price, forcing you to win the same game twice.

**Data recipe:** Reconstructed kill clusters plus `teamfights`; kill/death order; `radiant_gold_adv`; `objectives`; `buyback_log`; player/team `lh_t` and `gold_t` deltas; `purchase_log`; role/hero/patch cohort.

**Detection logic:** Label a fight win when enemy deaths minus allied deaths ≥2 or a core dies with no equivalent trade. Open a 45/90/150-second conversion window; score tower, barracks, Roshan/Aegis, forced buyback, and net territorial vision gain. Compare the player's farm share and objective credit during that window with matched opportunities.

**Confounders:** Low HP/mana is not exposed; enemy wave position, glyph, lineup objective damage, unavailable ultimates, buybacks, and deliberate reset can make farming correct.

**Confidence requirements:** ≥25 qualifying won windows across ≥20 matches; show only with stable direction in at least two time splits and a cohort-adjusted gap ≥0.6 SD.

**Interaction concept:** A stack of “window cards.” Scrub from last enemy death to the next 120 seconds; reveal kills, buybacks, CS gain, wards, and objectives, then compare “what happened” with the matched conversion distribution.

**Shareable version:** **THE WINDOW SHOPPER — You create openings, then browse the jungle. Your teams convert your won fights less often than 84% of comparable mids.**

## #2 — You Fixed It; It Moved — OOOH 9.20

**OOOH headline:** **You stopped dying in lane. The same mistake moved to minute 18.**

**Explanation:** Your total deaths improved, but the underlying decision pattern did not disappear—it migrated to a different phase or context. For example, early lane deaths fall while post-item farming deaths or post-fight salvage deaths rise.

**Evidence:** “In your first 25 games, 46% of deaths occurred before 12:00. In your latest 25, that fell to 17%—but deaths within three minutes of a major purchase rose from 9% to 31%.”

**Why care:** A flat death average can hide genuine learning and a new bottleneck. Naming both prevents the demoralizing conclusion that “nothing changed.”

**Data recipe:** Longitudinal match order; reconstructed death times; kill clusters; `purchase_log`; minute curves; advantage state; objectives; role/hero/patch and phase labels.

**Detection logic:** Represent each death as a context vector (phase, state, preceding event, purchase proximity, killer role, cluster order). Compare early and recent windows using Bayesian multinomial proportions or optimal-transport distance; surface a migration only when one context credibly decreases and another credibly increases.

**Confounders:** Hero-pool/role changes, patch changes, rank improvement, party changes, small phase denominators, and altered match duration.

**Confidence requirements:** ≥60 recent parsed matches and ≥20 deaths in each comparison window; posterior probability of both decrease and increase >95% after cohort adjustment.

**Interaction concept:** A Sankey-like “death migration” story: old death contexts flow into reduced, unchanged, and newly dominant contexts, with three evidence moments.

**Shareable version:** **THE PROBLEM MOVED — You fixed your lane. Your new leak is greed immediately after your first big item.**

## #3 — The Last Man Out — OOOH 9.15

**OOOH headline:** **You don't start bad fights. You stay in them too long.**

**Explanation:** You often survive the opening exchange, but when the fight turns numerically bad you continue committing and die late. This distinguishes poor entry from poor disengagement without pretending the endpoint can see exact movement.

**Evidence:** “You are alive after the second allied death in 74% of losing death clusters, yet 61% of your fight deaths happen after that point. In matched fights, your role exits alive 54% of the time.”

**Why care:** One earlier disengage preserves buyback, objective defense, and the ability to farm the enemy's downtime.

**Data recipe:** All players' `kills_log` inverted into deaths; detected `teamfights`; `last_death`; fight `deaths`, `killed`, `damage`, item/ability uses; buybacks; advantage; hero/position.

**Detection logic:** Order allied and enemy deaths in every 3+ death cluster. Mark a collapse after the second net allied death or a modeled win-probability drop. Count target-player deaths after collapse and survival at cluster end. Use fight aggregates only as corroboration, not exact exit time.

**Confounders:** Deliberate save/sacrifice, high-ground defense, reincarnation, buyback plans, escape unavailable, ally respawn timing, and heroes expected to be last alive.

**Confidence requirements:** ≥18 losing multi-death clusters and ≥8 post-collapse decisions; posterior excess ≥15 percentage points versus matched peers.

**Interaction concept:** A horizontal death-order strip. Teammate portraits fall left to right; the player's decision zone changes from green to amber to red. “Show evidence” opens the match page at the cluster.

**Shareable version:** **THE LAST MAN OUT — You survive the start of lost fights better than most players, then pay for trying to save the wreckage.**

## #4 — Two Personalities — OOOH 9.10

**OOOH headline:** **Ahead, you hunt. Behind, you disappear.**

**Explanation:** Your decisions change sharply with the scoreboard state. The revealing part is not whether that happens—it happens to everyone—but which behaviors swing, how quickly, and whether the swing helps.

**Evidence:** “At +3k team gold, your kill-cluster participation rises 38% and your farm share falls. At −3k, you place deeper vision less often and your neutral-creep share rises 44%, even on tempo heroes.”

**Why care:** Players often identify as “aggressive” or “patient,” while their actual identity is conditional. Knowing the trigger makes the style controllable.

**Data recipe:** Minute `radiant_gold_adv`/`radiant_xp_adv`; player `gold_t`, `lh_t`, unit-kill composition, ward time/location, purchases, kill clusters, objectives, buybacks, hero/position.

**Detection logic:** Segment player-minutes into behind/even/ahead using side-corrected advantage bands. Estimate state-conditioned rates for farm share, fight participation, vision territory, defensive purchases, deaths, and conversion. Cluster the deltas into winning/losing archetypes.

**Confounders:** Team strategy, draft scaling, hero timings, role, high-ground state, and the fact that advantage causes opportunity changes.

**Confidence requirements:** ≥80 parsed matches with ≥300 observed minutes in both ahead and behind states; shrink per-feature estimates and require at least three aligned signals.

**Interaction concept:** Split-screen story. A single toggle flips the same player's map/economy/fight card between **WHEN WINNING** and **WHEN LOSING**.

**Shareable version:** **YOUR TWO DOTA PERSONALITIES — The hunter at +3k. The bunker farmer at −3k.**

## #5 — Gold Fever — OOOH 9.05

**OOOH headline:** **You become greediest exactly when you're closest to your item.**

**Explanation:** As a major item approaches, your farming cadence increases and your death risk rises before completion, delaying the timing further. The endpoint cannot observe exact current gold, so this is a research-grade latent-wallet estimate rather than fake dollar precision.

**Evidence:** “Within the estimated final 500 gold before major items, your CS rate rises 29% and death hazard rises 1.8×. Those deaths delay the item by a median 2:40 and overlap the next objective in 43% of cases.”

**Why care:** The moment a player feels “almost there” is exactly when map discipline should tighten, not loosen.

**Data recipe:** `gold_t`; timestamped `purchase_log`; patch-specific item graph/costs; buybacks; reconstructed deaths; `lh_t`; team advantage; objectives; role/hero.

**Detection logic:** Build a probabilistic wallet from cumulative earned gold minus observed purchases and estimated buyback costs; model completed-item latent progress. Compare death hazard and CS rate in distance-to-item bands using a within-player survival model. Link deaths to realized completion delay and missed objective windows.

**Confounders:** Sales, shared items, secret-shop travel, assembly, disassembly, reliable/unreliable gold, item-plan changes, and correct risk-taking to hit a timing.

**Confidence requirements:** ≥35 major-item approaches, ≥10 near-completion deaths or a strong survival-model effect; do not display a precise gold threshold unless wallet reconstruction is validated on raw replays.

**Interaction concept:** An item icon fills like a progress ring while a risk line rises. Let the player reveal each “almost there” death and its downstream timing cost.

**Shareable version:** **GOLD FEVER — Your danger sense weakens when the item icon is almost complete.**

## #6 — Lane Win, Map Loss — OOOH 9.00

**OOOH headline:** **You win your lane, then surrender the next ten minutes.**

**Explanation:** Your 10-minute economy compares well with the matchup, but by minute 20 your advantage, objective involvement, or team territory has vanished. This isolates transition quality from laning quality.

**Evidence:** “You leave lane ahead in 62% of comparable games. By 20:00, that personal advantage survives only 29% of the time, and your teams take fewer first post-lane towers than peers with the same lane lead.”

**Why care:** Many players keep practicing the part they already win because the scoreboard makes the transition leak hard to see.

**Data recipe:** `gold_t`/`xp_t` at 10, 15, 20; `lane_efficiency_pct`; lane/position; early `lane_pos`; first post-lane objectives; purchases; kill clusters; peer matchup baselines.

**Detection logic:** Estimate expected 10-minute advantage for the exact hero/lane matchup. For positive residuals, measure retained personal/team advantage and conversion by 20 minutes. Attribute transition fingerprints: excessive farm share, low fight presence, deaths, or no objective follow-through.

**Confounders:** Lane swaps, sacrificial lanes, team draft, supports leaving early, comeback mechanics, and item timings designed for a later spike.

**Confidence requirements:** ≥25 genuine lane wins on the same position and enough matchup support for the expected-value model.

**Interaction concept:** A relay baton visual: **LANE LEAD** at 10:00 passes—or drops—through item timing, first rotation, and first objective.

**Shareable version:** **THE DROPPED BATON — Strong lane, weak handoff. Your lead usually expires before your first major item matters.**

## #7 — The Rescue Tax — OOOH 8.90

**OOOH headline:** **Your loyalty is costing a second death.**

**Explanation:** After an ally is caught, you frequently die shortly afterward without an offsetting kill, objective, or meaningful damage swing. That observable sequence looks less like bad initiation and more like an expensive rescue attempt.

**Evidence:** “When an ally dies first near a detected cluster, you become the next allied death 32% of the time—double the peer rate. Only 18% of those sequences recover a kill or objective.”

**Why care:** Saving a teammate is valuable; donating a second core makes the map unplayable. The insight teaches a stop-loss decision, not selfishness.

**Data recipe:** Ordered death reconstruction; detected teamfights; teamfight damage/healing/ability targets; kill trades; subsequent objectives; hero/role and save-kit metadata.

**Detection logic:** Find allied first deaths followed by target death within 5–25 seconds. Exclude simultaneous bursts. Score rescue evidence from healing/save ability targets and fight participation; score return from kills, gold/XP, and objectives. Compare with role-matched opportunities.

**Confounders:** Deliberate sacrifice, buyback bait, required high-ground defense, save heroes, core-for-core trade, and missing exact cast order.

**Confidence requirements:** ≥15 eligible ally-first sequences; use “possible rescue tax” unless save-cast evidence is present.

**Interaction concept:** A branching card asks “Would you follow?” then reveals ally death, the player's subsequent resources, and the trade outcome.

**Shareable version:** **THE RESCUER — You try to save lost teammates more than most players. Too often, the map loses both of you.**

## #8 — Power-Spike Tourist — OOOH 8.85

**OOOH headline:** **You arrive at your item timing, take a photo, and keep farming.**

**Explanation:** Major items complete on respectable timings, but the next few minutes show no increase in fight involvement, objective conversion, or enemy pressure. You buy a window without changing behavior inside it.

**Evidence:** “After Blink/BKB-class completions, your fight participation does not rise for a median 4:10. Comparable offlaners join or force a decisive event within 2:20.”

**Why care:** A timing is valuable because it temporarily changes which fights are favorable. Delayed use turns a power spike into ordinary net worth.

**Data recipe:** Major completed-item inference from `purchase_log`; kill clusters/teamfights; objectives; `lh_t`/`gold_t`; item-use counts inside fights; hero/role/patch item metadata.

**Detection logic:** Detect completion timestamp from final component/completed item. Define hero-item-specific activation window. Compare pre/post rates for fights, kills, deaths, objectives, and farm share; model time-to-first-consequential-event.

**Confounders:** Defensive item intended to avoid rather than start fights, team not ready, smoke unavailable, lanes unpushed, item bought while behind, or completion inference error.

**Confidence requirements:** ≥20 comparable major completions and ≥8 on the same item class; effect must persist after state adjustment.

**Interaction concept:** Item-completion gong followed by a silent timeline. The first consequence lights up; peers appear as ghost markers.

**Shareable version:** **POWER-SPIKE TOURIST — Good timings. Late consequences.**

## #9 — Lead Poisoning — OOOH 8.80

**OOOH headline:** **A lead makes you less disciplined.**

**Explanation:** When ahead, your death rate, unsupported kill chasing, or farm concentration worsens instead of improving. The lead changes the player's safety margin more than the game actually changed.

**Evidence:** “At +5k or more, your death hazard is 41% higher than at even state after hero and phase adjustment. Those deaths erase a median 28% of the current lead.”

**Why care:** Closing games is a skill distinct from earning a lead. One needless core death can reopen Roshan and high ground.

**Data recipe:** Side-corrected gold/XP advantage; reconstructed deaths; kill streaks; teamfight outcomes; buybacks; objective swings; farm share; hero/role cohort.

**Detection logic:** Fit within-player death hazard by advantage band, controlling phase and hero. For deaths while strongly ahead, measure immediate advantage loss and objectives conceded in 180 seconds. Require repeated context-response-consequence chains.

**Confounders:** Correct map constriction exposes the leading team to more enemy territory; initiator roles and high-ground attempts naturally increase risk.

**Confidence requirements:** ≥250 minutes played at strong advantage and ≥12 deaths in that state; credible adjusted hazard ratio >1.25.

**Interaction concept:** A lead meter fills, then cracks at each death. Toggle “earned aggression” versus “unreturned death.”

**Shareable version:** **LEAD POISONING — You build leads like a closer and spend them like a gambler.**

## #10 — Chain-Feed Return — OOOH 8.75

**OOOH headline:** **Your most dangerous place is the map immediately after you respawn.**

**Explanation:** Consecutive deaths cluster because you re-enter action before the map state has reset. The endpoint cannot see the return route, but it can reveal unusually short death-to-death intervals and what you accomplished between them.

**Evidence:** “After dying, your chance of dying again within four active minutes is 1.7× baseline. In 68% of those repeats you record no kill, objective, or major item completion between deaths.”

**Why care:** Chain deaths erase recovery time, compound map control, and are often more fixable than isolated deaths.

**Data recipe:** Reconstructed death times; estimated respawn duration from phase/level; buybacks; kills; objectives; minute CS/gold; purchases; advantage state.

**Detection logic:** Convert wall-clock death gaps into estimated alive-time gaps, treating buybacks separately. Compare post-death hazard to the player's normal hazard in matched state. Classify productive versus empty returns by intervening events.

**Confounders:** Immediate high-ground defense, buyback defense, short early respawns, intentional space creation, and approximate respawn times.

**Confidence requirements:** ≥35 deaths and ≥8 repeat-death opportunities; show exact examples and a confidence band.

**Interaction concept:** Respawn doors open into a four-minute danger corridor. Each second death shows the intervening actions—or absence of them.

**Shareable version:** **THE REVOLVING DOOR — Your death risk peaks just after you come back.**

## #11 — Reactive Vision — OOOH 8.65

**OOOH headline:** **You ward the place where the mistake already happened.**

**Explanation:** Your vision spikes after deaths, lost towers, or failed fights instead of before your team enters those areas. The behavior is measurable because ward logs have exact times and coordinates even though player movement does not.

**Evidence:** “58% of your aggressive wards are placed within 90 seconds after a nearby allied death or lost objective; peers in your role place 36% reactively. Your pre-objective vision rate is below median.”

**Why care:** Autopsy wards explain yesterday's danger; predictive wards change the next decision.

**Data recipe:** `obs_log`/`sen_log` timestamps and coordinates; ward removals; objectives; reconstructed deaths and death positions when available; map-region model; role/patch/team vision burden.

**Detection logic:** For each placement, search preceding and following event windows in the same map region. Classify reactive, preparatory, maintenance, and recovery wards. Compare player mix with matched supports and measure survival/next-event value.

**Confounders:** Restocking cadence, wards placed by another support, defensive necessity after losing territory, smoke plans, and missing full death locations.

**Confidence requirements:** ≥80 placements across ≥20 matches; ≥20 classified aggressive/pre-objective placements.

**Interaction concept:** A map rewinds 90 seconds from each ward. The player guesses “before or after the bad event?” before the timeline reveals it.

**Shareable version:** **THE AUTOPSY WARDER — Your vision often explains danger after it arrives.**

## #12 — Role Betrayal — OOOH 8.60

**OOOH headline:** **Your hero is position 4. Your resource habits are position 2.**

**Explanation:** Your inferred role and hero say one thing; your farm share, ward economy, item timing, and objective behavior say another. This can expose healthy role flexibility or a repeated mismatch that starves the lineup.

**Evidence:** “On position 4, you take 17% of team earned gold from minutes 12–25—position-3 territory—while your observer placement share falls below the support median.”

**Why care:** Role is an economic contract, not a lane label. Breaking it unknowingly changes every teammate's timing.

**Data recipe:** `position_est`, `lane_role`; player/team `gold_t` and `lh_t`; wards and purchases; items; damage/healing; objectives; hero-role cohort.

**Detection logic:** Build role-behavior embeddings from farm share, ward burden, item cost/timing, damage, saves, and objectives. Compare declared/inferred role with nearest behavioral role and link mismatch to team timing outcomes.

**Confounders:** Greedy position 4 strategies, support hero scaling, teammates intentionally sacrificing farm, role swaps, and position-estimation error.

**Confidence requirements:** ≥30 matches on the claimed position; posterior role mismatch in ≥65% of games and at least three corroborating families.

**Interaction concept:** Two silhouettes overlap: **QUEUED ROLE** and **PLAYED ROLE**. Evidence tokens slide to the silhouette they resemble.

**Shareable version:** **THE SECRET CORE — Your queue says support; your map economy disagrees.**

## #13 — Farm Reset Reflex — OOOH 8.55

**OOOH headline:** **Every fight sends you back to farming—even the fights you win.**

**Explanation:** Your default post-engagement response is a sharp CS/farm-share increase. Sometimes that is excellent reset discipline; sometimes it abandons a live objective window.

**Evidence:** “Your CS rate rises 52% in the three minutes after detected fights, regardless of result. After wins, peers convert more while your farm response barely changes.”

**Why care:** The same habit can be a strength after bad fights and a leak after good ones. Context, not farm volume, decides.

**Data recipe:** Teamfight/kill-cluster end times and result; `lh_t`, `gold_t`; objectives; purchases; advantage; player role.

**Detection logic:** Estimate pre/post three-minute farm-rate change for every engagement. Interact response with fight result, alive advantage, and objective availability. Label adaptive reset versus automatic reset.

**Confounders:** Minute resolution, lane waves already prepared, carry role, team call, low resources, and objective damage capability.

**Confidence requirements:** ≥30 engagements with at least 10 wins and 10 losses; stable context interaction.

**Interaction concept:** A metronome cycles **FARM → FIGHT → ?**. The player's real third beat fills in by state.

**Shareable version:** **THE RESET BUTTON — Win or lose, your next instinct is always farm.**

## #14 — Delayed Seatbelt — OOOH 8.45

**OOOH headline:** **You buy survivability after it would have mattered most.**

**Explanation:** Defensive items repeatedly arrive only after a cluster of deaths to the same damage/control profile. The insight evaluates adaptation timing, not whether a textbook build contains BKB.

**Evidence:** “In 14 games against heavy magic/control, your first defensive component arrives after your second relevant death 64% of the time. Once completed, your next-death interval improves substantially.”

**Why care:** A correct item built late can be functionally wrong; delayed protection misses the opponent's strongest window.

**Data recipe:** Enemy heroes; `damage_inflictor_received`; `killed_by`; reconstructed death times; `purchase_log`; item taxonomy; advantage and expected role-item baselines.

**Detection logic:** Infer the match's threat vector from lineup and actual incoming sources. Detect first meaningful defensive commitment, compare it with threat onset and death sequence, then estimate post-purchase survival change with matched controls.

**Confounders:** Item cost, farming role, dispel from teammates, defensive item not visible in final taxonomy, intentionally greedy timing, and chronology missing from damage-source totals.

**Confidence requirements:** ≥20 comparable threat matches and ≥8 delayed adaptations; avoid causal “item fixed it” language without within-match controls.

**Interaction concept:** A threat timeline lays damage sources above purchases and deaths. The “seatbelt” snaps in at its actual time versus the peer window.

**Shareable version:** **THE DELAYED SEATBELT — Your defensive builds are right. Your timing is late.**

## #15 — Old You vs New You — OOOH 8.40

**OOOH headline:** **You no longer recover from bad lanes by hiding. You recover by fighting.**

**Explanation:** The player's response strategy changes over months even if aggregate win rate barely moves. Longitudinal behavior is more personal than a trend line because it names what changed.

**Evidence:** “After losing the lane, your early sample devoted 63% of minutes 10–20 to farm-share recovery. Recently, fight participation rises instead and your team closes the deficit 2:10 sooner.”

**Why care:** It validates learning, reveals deliberate or accidental style change, and distinguishes progress from patch noise.

**Data recipe:** Chronological matches; lane residual; midgame farm share; kill-cluster participation; objectives; advantage recovery; hero/role/patch controls.

**Detection logic:** Fit time-varying coefficients for state-conditioned behavior. Detect change points only after accounting for hero pool, role, and patch. Translate the largest stable coefficient shift into Dota language.

**Confounders:** Meta shifts, hero-pool changes, coaching/party changes, rank climb, and sparse parsed coverage over time.

**Confidence requirements:** ≥120 parsed matches spanning ≥8 weeks with ≥35 matches on each side of a detected change point.

**Interaction concept:** A “then/now” replay pair with identical context but different next decisions; slide between them.

**Shareable version:** **PLAYER PATCH NOTES — Recovery behavior reworked: less jungle retreat, more early counter-fighting.**

## #16 — Buyback Conviction — OOOH 8.35

**OOOH headline:** **When you buy back, the game usually agrees—or punishes you immediately.**

**Explanation:** Buybacks reveal commitment under pressure. Measure whether the second life produces a saved objective, kill swing, Roshan defense, or merely a second death and lost economic option.

**Evidence:** “Your buybacks create positive objective/kill value 58% of the time, but buybacks made while the team is already down three heroes succeed only 17% of the time.”

**Why care:** Buyback quality is a high-leverage decision that players remember emotionally but rarely audit systematically.

**Data recipe:** `buyback_log`; death order; objectives; subsequent kills/deaths; advantage curves; item purchases delayed; approximate buyback cost/death timer; role.

**Detection logic:** For each buyback, score 120-second outcomes: objectives saved/taken, kill balance, survival, advantage swing, and next-item delay. Compare with state-matched buybacks and classify defense, re-entry, greed, or desperation.

**Confounders:** Exact current net worth/reliable gold absent, team call, base defense, tournament stakes, and value outside the 120-second window.

**Confidence requirements:** ≥12 buybacks for a personal tendency; single-match card allowed as an observation only.

**Interaction concept:** A literal second-life ledger: **COST** on the left, **WHAT IT BOUGHT** on the right.

**Shareable version:** **SECOND-LIFE ROI — Your disciplined buybacks save games; your 3v5 buybacks buy another death.**

## #17 — Cleanup Crew — OOOH 8.30

**OOOH headline:** **You are most dangerous after everyone else has committed.**

**Explanation:** Your kills cluster late in multi-death engagements, after allies and enemies have already spent lives. This is a genuine finisher strength unless it comes with chronic absence from the opening damage.

**Evidence:** “62% of your fight kills occur after the third hero death, versus 34% for comparable carries. Your teamfight damage remains above median, so this is cleanup—not kill stealing.”

**Why care:** It can validate patience and target access, or reveal over-delayed entry when damage contribution is low.

**Data recipe:** Ordered `kills_log` within reconstructed clusters; teamfight `damage`, `killed`, item/ability uses; role/hero; fight result.

**Detection logic:** Assign each player kill an ordinal position within clusters. Model late-kill share and first-contribution proxy from fight damage/uses. Separate high-damage finisher, low-damage last hitter, and absent opener.

**Confounders:** Carry hero design, resets, execute abilities, illusions, no raw damage timing, and omitted two-death skirmishes.

**Confidence requirements:** ≥25 multi-death clusters and ≥15 player kills inside them.

**Interaction concept:** A fight “credits sequence” where the player's portrait enters when their kill footprint begins; damage and kills reveal separately.

**Shareable version:** **CLEANUP CREW — When a fight gets messy, it becomes your kind of fight.**

## #18 — First Casualty Personality — OOOH 8.25

**OOOH headline:** **Your fights are usually decided before your second spell: you are the first body down.**

**Explanation:** Across comparable engagements, you are the first allied death unusually often. The endpoint cannot say exactly how you entered, but repeated first-death status combined with low/high damage and role gives a strong coaching branch.

**Evidence:** “You are your team's first death in 39% of losing multi-death clusters; comparable position-3 heroes are first in 24%. Half of those deaths produce below-median fight damage.”

**Why care:** First deaths remove spells, auras, saves, and target information before the fight develops.

**Data recipe:** Inverted kill logs; teamfight death order and player damage/ability/item use; role/hero; advantage and fight result.

**Detection logic:** Identify first allied death in every cluster and normalize by expected frontline burden. Split useful initiation deaths (high damage/kill trade/win) from low-return first deaths.

**Confounders:** Initiator/sacrifice role, Aegis, reincarnation, bait strategy, and missing damage timing.

**Confidence requirements:** ≥20 eligible clusters; ≥8 first-death events for subtype language.

**Interaction concept:** “Who falls first?” prediction cards followed by a return-on-death breakdown.

**Shareable version:** **THE FIRST DOMINO — You absorb the opening more often than your role should.**

## #19 — Same Enemy Tax — OOOH 8.20

**OOOH headline:** **One enemy keeps collecting your game.**

**Explanation:** A disproportionate share of deaths goes to one opposing hero or damage profile, often across games. The valuable version distinguishes an expected counter from a repeated adaptation failure.

**Evidence:** “Storm Spirit accounts for 31% of your deaths when present, nearly twice the matchup expectation. Your defensive timing and target damage do not adjust after the first death.”

**Why care:** A nemesis pattern gives a concrete item, positioning, or target-priority review instead of generic “die less.”

**Data recipe:** `killed_by`; kill-log inversion and times; enemy hero/role; `damage_inflictor_received`; purchases; ability/damage targets; matchup baseline.

**Detection logic:** Estimate expected killer share from hero matchup, role, and exposure. Flag excess concentration; then test whether defensive purchases, return kills, or target pressure change after first death across matches.

**Confounders:** Hard counters, assassin role, lane matchup, team target assignment, and lack of temporal damage-target matrices.

**Confidence requirements:** Enemy hero appears in ≥15 matches with ≥12 deaths attributable to it; credible excess versus matchup baseline.

**Interaction concept:** A “wanted poster” that opens into the exact death sequence and adaptation checklist.

**Shareable version:** **YOUR NEMESIS — This hero kills you far more often than the matchup alone explains.**

## #20 — Death Geography Déjà Vu — OOOH 8.15

**OOOH headline:** **You keep dying in the same kind of place.**

**Explanation:** Teamfight death coordinates cluster around repeated map contexts: enemy triangle entrances, river ramps, Roshan approaches, or the same high-ground edge. Because coordinates exist only for parser-detected fights, this is a partial but powerful spatial pattern.

**Evidence:** “43% of your detected-fight deaths occur in two enemy-side chokepoint clusters, versus 19% for comparable players. Nearby allied observer coverage is absent in most examples.”

**Why care:** A location pattern makes an abstract positioning leak concrete enough to recognize in the next game.

**Data recipe:** Teamfight `deaths_pos`; ward placement/removal; map-region polygons and path/chokepoint graph; objectives; side transform; role/hero/state.

**Detection logic:** Reflect Dire/Radiant coordinates into a common frame; cluster death points with HDBSCAN or a map graph; compare density with peer opportunity and nearby friendly vision. Name only semantically stable regions.

**Confounders:** Locations missing for most deaths, objective defense forces repetition, map patches, and detector bias toward large fights.

**Confidence requirements:** ≥20 located deaths across ≥30 matches with a stable cluster containing ≥6 deaths and a peer-adjusted excess.

**Interaction concept:** A fogged map slowly reveals recurrent red “memory scars,” each opening an evidence fight.

**Shareable version:** **DANGER DÉJÀ VU — Your deaths remember this ramp even when you do not.**

## #21 — Selective Attendance — OOOH 8.10

**OOOH headline:** **You are excellent in the fights you choose—and too selective about choosing them.**

**Explanation:** In detected engagements your impact is strong, but you register no damage, spell/item use, kill, death, or meaningful XP delta in an unusual share of important team fights. This measures attendance, not exact arrival timing, which the endpoint does not expose.

**Evidence:** “Your impact ranks in the top quartile when present, yet you are absent from 37% of high-value multi-death fights; peers in your position miss 21%.”

**Why care:** Mechanical fight skill cannot compensate for choosing farm during the fight that decides Roshan.

**Data recipe:** Teamfight player aggregates; reconstructed clusters; pre/post objectives; XP delta as proximity proxy; role/hero/state; `lh_t`/`gold_t` during window.

**Detection logic:** Mark presence from positive damage/healing, ability/item use, kill/death, or abnormal XP delta. Weight fights by deaths, objective proximity, and advantage swing; compare attendance and impact conditional on attendance.

**Confounders:** Split-push trade, global abilities, fight detector omissions, dead at start, and positive passive XP near but not participating.

**Confidence requirements:** ≥25 high-value detected fights, ≥8 absences, and strong impact/presence contrast.

**Interaction concept:** A scouting report with two grades: **IN-FIGHT EXECUTION** and **FIGHT SELECTION**; each opens different evidence.

**Shareable version:** **THE SELECTIVE CARRY — A-grade fighting, C-grade attendance.**

## #22 — Resource Gravity — OOOH 8.05

**OOOH headline:** **Farm bends toward you when the game gets uncertain.**

**Explanation:** Your share of team-earned gold and last hits expands after setbacks or in even games, then may shrink when comfortably ahead. This reveals who absorbs uncertainty and whether the response matches role and comeback value.

**Evidence:** “At even or negative state, your position-3 farm share rises from 19% to 28%; your position-1 teammate's next-item timing slips by a median 1:35.”

**Why care:** Resource allocation is a team decision made through thousands of small map choices, often without anyone noticing the pattern.

**Data recipe:** Player/team `gold_t` and `lh_t` minute deltas; advantage buckets; roles; purchase timings for all teammates; deaths/fights/objectives.

**Detection logic:** Compute rolling earned-gold and CS shares. Model share change after state transitions and negative events; attribute downstream item-timing shifts to teammates cautiously.

**Confounders:** Correct recovery priority, hero scaling, dead teammates, assigned dangerous farm, summons, and minute resolution.

**Confidence requirements:** ≥50 matches with ≥250 midgame minutes in relevant states; three aligned farm/timing signals.

**Interaction concept:** A gravity well visualization: five team portraits orbit available economy; the pull changes by game state.

**Shareable version:** **THE FARM GRAVITY WELL — When the game feels unstable, resources start orbiting you.**

## #23 — Space Dividend — OOOH 8.00

**OOOH headline:** **Some of your deaths make your team richer. Most do not.**

**Explanation:** Instead of declaring deaths “good” by intuition, measure what the other four players gain while you are dead and immediately afterward: farm-share expansion, objectives, and favorable trades. This builds a personal useful-death profile.

**Evidence:** “Your offlane deaths generate a positive team dividend 38% of the time. Deaths on the enemy side near objectives do; isolated lane deaths rarely do.”

**Why care:** It separates legitimate space creation from retroactively romanticizing a feed.

**Data recipe:** Death times; approximate respawn windows; teammate `gold_t`/`lh_t`; objectives; kill trades; advantage; teamfight death location when present; role/hero.

**Detection logic:** Estimate teammate excess economy during the death window versus matched alive windows, then add objective and kill value and subtract advantage loss. Classify positive, neutral, or negative dividend with uncertainty.

**Confounders:** Respawn timing approximation, causality (team may gain despite death), wave states, and unobserved map position.

**Confidence requirements:** ≥35 deaths and ≥10 in the same context; never call a single death “space created” without corroborating team gains.

**Interaction concept:** A death receipt shows **TEAM EARNED WHILE YOU WERE GONE** and **WHAT THE ENEMY BOUGHT WITH YOUR DEATH**.

**Shareable version:** **SPACE WITH RECEIPTS — 4 of your last 11 offlane deaths paid a real team dividend.**

## #24 — Objective Hangover — OOOH 7.95

**OOOH headline:** **After taking an objective, you chase the feeling instead of resetting.**

**Explanation:** Towers, Roshan, or barracks are followed by extra pursuit, deaths, or buybacks that return part of the gain. The pattern is the mirror image of weak conversion: converting correctly, then overstaying.

**Evidence:** “Within 90 seconds of successful objectives, your death rate is 1.6× peers and 44% of those deaths trigger an enemy return objective.”

**Why care:** Good Dota often ends a successful sequence one decision earlier than instinct wants.

**Data recipe:** Objective times/types; subsequent kill/death order; buybacks; advantage curves; player farm and purchases; hero/role.

**Detection logic:** Open a post-objective risk window; score additional friendly gains versus deaths, buybacks, and objectives conceded. Compare with state- and objective-matched peers.

**Confounders:** Correct chain objectives, enemy contest, high-ground siege, Aegis, and team calls.

**Confidence requirements:** ≥25 team objective events and ≥8 post-objective deaths.

**Interaction concept:** Objective banner appears, followed by a “cash out / press again” branching timeline.

**Shareable version:** **OBJECTIVE HANGOVER — You take the tower, then give the celebration kill back.**

## #25 — Frontline Tolerance — OOOH 7.90

**OOOH headline:** **You absorb more of the fight than your role suggests—and survive less of it.**

**Explanation:** Incoming hero damage share, first-death rate, and survival are triangulated against role and hero durability. The trait can be valuable courage, excessive exposure, or deliberate tanking depending on return.

**Evidence:** “As position 4, you absorb 19% of team incoming hero damage versus a 12% peer median, but your team's cores deal more damage in those fights only half the time.”

**Why care:** Frontlining is useful only when it buys access, spells, or survival for higher-value teammates.

**Data recipe:** `damage_taken`, `damage_inflictor_received`; teamfight damage/deaths; death order; items; role/hero durability metadata; healing received if reconstructable.

**Detection logic:** Compute role-adjusted incoming-damage share and first-death odds, then measure ally damage/kill return. Classify productive tanking versus unsupported exposure.

**Confounders:** Damage totals lack chronology/type; illusions, self-damage, heals, barriers, and hero mechanics alter effective durability.

**Confidence requirements:** ≥25 matches on a role/hero family; multiple combat families must agree.

**Interaction concept:** A shield silhouette fills with damage absorbed while team output appears behind it.

**Shareable version:** **THE HUMAN SHIELD — You stand in front more than your badge says. The question is what your team buys with it.**

## #26 — Vision Half-Life — OOOH 7.85

**OOOH headline:** **Your wards die young.**

**Explanation:** Observer/sentry placements survive for unusually little of their patch-specific expected lifetime, especially in particular territories or after repetitive placement. This turns “ward more” into a quality diagnosis.

**Evidence:** “Aggressive observers survive a median 92 seconds, versus 214 seconds for matched support wards. Reused cliff cells account for most early removals.”

**Why care:** A ward that dies instantly gives the enemy gold and advertises where your team wants to play.

**Data recipe:** `obs_log`/`sen_log`; `obs_left_log`/`sen_left_log` matched by `ehandle`; ward duration constants; coordinates; enemy ward-kill counts; objectives.

**Detection logic:** Match placement to removal, censor at match end, distinguish likely expiry from early removal, and fit survival curves by region/context. Flag repeated early-death cells.

**Confounders:** Parser removal artifacts, deliberate disposable vision, deward bait, match ending, and patch duration changes.

**Confidence requirements:** ≥60 matched placements with ≥20 non-censored observers.

**Interaction concept:** Ward candles burn for their real lifetime on a map; short flames group into risky habits.

**Shareable version:** **SHORT-LIVED VISION — Your aggressive wards survive less than half as long as peer wards.**

## #27 — Aegis Lease — OOOH 7.80

**OOOH headline:** **You hold Aegis safely—but the map barely notices.**

**Explanation:** After Aegis pickup, measure whether the holder/team converts structures, forces buybacks, takes fights, or simply farms until the advantage expires. The endpoint sees pickup but not exact expiry, so timing uses patch rules and death events.

**Evidence:** “Across 18 Aegis pickups, your teams take fewer structures than peers during the lease window, while your farm share rises.”

**Why care:** Aegis is borrowed tempo. Safe possession without pressure may waste the strongest map permission in Dota.

**Data recipe:** `CHAT_MESSAGE_AEGIS`; Roshan events; holder; objectives; deaths; teamfight/kill clusters; farm share; buybacks; patch-specific Aegis duration.

**Detection logic:** Open an Aegis lease from pickup until estimated expiry or holder death/reclaim sequence. Score structures, kills, forced buybacks, advantage, and holder farm share.

**Confounders:** Exact reclaim/expiry absent, defensive Aegis, lineup scaling, second Roshan rewards, and team—not holder—decision ownership.

**Confidence requirements:** Team-level tendency ≥15 Aegis windows; player-holder tendency ≥10.

**Interaction concept:** A five-minute lease clock counts down while the map records what was purchased with it.

**Shareable version:** **AEGIS TENANT — You keep the extra life safe. Too often, the enemy keeps its buildings safe too.**

## #28 — Streak Cashout — OOOH 7.75

**OOOH headline:** **Your kill streak ends before its pressure pays rent.**

**Explanation:** After building a streak, the next event is often an isolated death rather than an objective, item timing, or sustained lead. This evaluates what momentum becomes.

**Evidence:** “After 3+ kill streaks, you die within five minutes 36% of the time and convert a structure first only 22%.”

**Why care:** Streak value is not the announcer line; it is the map permission and gold bounty preserved afterward.

**Data recipe:** `kills_log`, `kill_streaks`, reconstructed deaths; objectives; purchases; advantage; farm share.

**Detection logic:** Reconstruct streak start/end sequences, then score first consequential event after threshold: objective, major item, further kill, or death. Compare with peers and baseline state.

**Confounders:** In-game streak definition, support kills, bounty incentives, correct aggressive play, and team conversion ownership.

**Confidence requirements:** ≥15 streak episodes.

**Interaction concept:** A streak meter becomes a branching “cashed into” ledger.

**Shareable version:** **MOMENTUM SPENDER — Your streaks create pressure, then expire as bounties.**

## #29 — Post-Death Personality — OOOH 7.70

**OOOH headline:** **After consecutive deaths, you speed up instead of calming down.**

**Explanation:** No emotion is diagnosed. The observable fact is that after one or two deaths, your next-few-minute mix shifts toward kills/fights, purchases, farm, wards, or another death.

**Evidence:** “After two deaths within eight minutes, your next kill-cluster involvement arrives 31% sooner and your CS rate falls 24%; the second-repeat death hazard rises.”

**Why care:** A state-triggered behavioral change can be interrupted with a simple reset rule.

**Data recipe:** Death sequence; next kill/fight event; `lh_t`/`gold_t`; ward placements; purchases; objectives; advantage; role/hero.

**Detection logic:** Compare post-death windows with matched no-death windows for the same player/state. Estimate a multivariate behavior shift; describe only observed changes.

**Confounders:** Team must defend, death changes map opportunity, short respawns, and regression to the mean.

**Confidence requirements:** ≥25 single-death and ≥12 double-death episodes; repeated direction across time splits.

**Interaction concept:** A “what you do next” decision wheel shown before and after deaths.

**Shareable version:** **AFTER DEATH: ACCELERATE — Your observable response to setbacks is more action, not less.**

## #30 — Target Fixation — OOOH 7.65

**OOOH headline:** **Once you choose a target, the rest of the lineup disappears.**

**Explanation:** Match-wide damage and ability-target matrices show unusually concentrated attention on one enemy role/hero, even when kills or fight outcomes do not justify it. The endpoint cannot see mid-fight switches, so this is repeated allocation—not literal tunnel-vision chronology.

**Evidence:** “One enemy receives 48% of your hero damage in matched lineups, but only 21% of your kills and no improvement in fight win rate.”

**Why care:** Target choice is often a bigger fight lever than raw damage.

**Data recipe:** `damage_targets`; `ability_targets`; kills; enemy positions; damage-source semantics; teamfight outcomes; hero/role.

**Detection logic:** Compute target entropy and role-weighted concentration, compare with target availability/expected durability, then test conversion to kills and fight wins.

**Confounders:** Correct focus target, tanky frontliner availability, AoE/spread mechanics, illusions, and lack of chronology.

**Confidence requirements:** ≥30 matches on a hero family and ≥15 relevant multi-target lineups.

**Interaction concept:** Enemy portraits receive a heat halo proportional to attention, then flip to outcome value.

**Shareable version:** **TARGET LOCKED — Nearly half your damage keeps finding the same kind of hero.**

## #31 — Protector Instinct — OOOH 7.60

**OOOH headline:** **You protect one teammate more than your role chart would predict.**

**Explanation:** Healing and targeted defensive ability usage repeatedly favor a particular role or player. The relationship can reveal a natural duo, protection bias, or neglected win condition.

**Evidence:** “Your position 4 receives 41% of targeted support value while your carry receives 23%, even after proximity/opportunity adjustment.”

**Why care:** Teams often have an unconscious center of gravity; knowing it can align saves with the actual win condition.

**Data recipe:** `healing`; `ability_targets`; defensive item/ability taxonomy; teammate roles; deaths; party identity; fight participation.

**Detection logic:** Attribute targeted support value by recipient and normalize for games together, hero, role, and recipient exposure. Link protection concentration to recipient survival and team outcome.

**Confounders:** Ability semantics, self-casts, AoE saves, proximity absent, duo party strategy, and recipient damage taken.

**Confidence requirements:** ≥30 games with targeted-support heroes and ≥15 games with the same role/peer pattern.

**Interaction concept:** A teammate constellation with support-value links; strongest bond opens its evidence.

**Shareable version:** **YOUR UNCONSCIOUS DUO — Your spells play around position 4 more than your carry.**

## #32 — Executioner vs Setup — OOOH 7.55

**OOOH headline:** **Your scoreboard says finisher; your fights say architect.**

**Explanation:** Kills, assists, damage, stuns, healing, target distribution, and fight deltas can reveal whether a player finishes, enables, soaks, or cleans up. This replaces KDA identity with contribution shape.

**Evidence:** “Only 12% of teamfight kills are yours, but your disables/targeted spells and team damage return place you in the top support quartile.”

**Why care:** Players chase visible outputs when their best contribution may be invisible setup—or overrate setup that produces no return.

**Data recipe:** K/D/A; stuns; ability targets/uses; damage/healing; teamfight kills/damage/gold/XP; role/hero cohort.

**Detection logic:** Fit a contribution-mixture model with latent roles: execution, setup, sustain, tank, cleanup. Require consistency across several families.

**Confounders:** Stun duration accuracy, unobserved soft control, hero kit, and teamfight detector coverage.

**Confidence requirements:** ≥35 matches on a stable role; posterior archetype probability >70%.

**Interaction concept:** A scouting radar with contribution verbs, not stats; each axis opens evidence.

**Shareable version:** **THE ARCHITECT — Fewer last hits on heroes, more fights built for everyone else.**

## #33 — Item Active Amnesia — OOOH 7.50

**OOOH headline:** **You buy the active. Your fingers keep forgetting it.**

**Explanation:** Active-item use counts are low relative to ownership time and relevant detected fights. A stronger version isolates deaths/fights where the item was likely owned but unused, without claiming it was off cooldown.

**Evidence:** “Your Force Staff is used in 38% fewer eligible fights than role peers. In six detected deaths after purchase, the fight window records no use.”

**Why care:** An unused active is dead net worth at the exact moment it was purchased to matter.

**Data recipe:** `purchase_log`; `item_uses`; teamfight `item_uses`; detected deaths/fights; item cooldown/opportunity rules; hero/role.

**Detection logic:** Estimate ownership interval from purchase to end (censor sales). Count relevant fight windows and expected uses; model usage rate. Label “unused in window,” never “available and forgotten.”

**Confounders:** Cooldown, charges, item sold/shared, no valid target, passive purpose, duplicate uses, and missing fights.

**Confidence requirements:** ≥15 ownership-matches or ≥20 eligible detected fights for an item class.

**Interaction concept:** Inventory icons light up in each fight window; unused actives remain dark with an uncertainty badge.

**Shareable version:** **THE EXPENSIVE PASSIVE — You own active items more often than you activate them.**

## #34 — Ultimate Patience — OOOH 7.45

**OOOH headline:** **You hold your ultimate longer than the game asks you to.**

**Explanation:** Ultimate casts per eligible time/fight are unusually low, especially in losses or while ahead. This can be disciplined conservation or missed opportunity; outcomes and hero-specific opportunity models separate them imperfectly.

**Evidence:** “Your ultimate appears in 43% of detected eligible fights versus a 67% hero-role baseline; fights without it are not offset by a stronger next fight.”

**Why care:** The fear of wasting a cooldown can waste the fight instead.

**Data recipe:** `ability_uses`; teamfight ability uses; ability cooldown by level/facet/patch; upgrade order; fight windows/outcomes; duration.

**Detection logic:** Estimate maximum plausible casts and eligible detected fights after unlock. Compare actual use and next-window value; classify patient, normal, or over-conservative.

**Confounders:** Cooldown state, mana, silence/death, ability not needed, transformation/passive ultimates, and omitted fights.

**Confidence requirements:** ≥25 matches on the same ultimate family and ≥20 eligible fights.

**Interaction concept:** A cooldown moon fills across fights; show “used,” “held,” and “unknown.”

**Shareable version:** **THE HELD ULT — Your patience sometimes outlives the fight.**

## #35 — Spell Target Loyalty — OOOH 7.40

**OOOH headline:** **Your signature spell has a favorite teammate.**

**Explanation:** Targeted abilities repeatedly favor a specific allied role or enemy archetype. Unlike raw cast count, this reveals who the player believes deserves resources or control.

**Evidence:** “Your save spell targets offlaners twice as often as carries after exposure adjustment, and those casts produce better survival value.”

**Why care:** It can validate exceptional synergy or reveal that the highest-value target is being ignored.

**Data recipe:** `ability_targets`; ability semantics; team/enemy heroes and positions; healing, deaths, kills, party identity.

**Detection logic:** Build target-choice distributions per ability, normalize for target availability, and relate choice to recipient survival or target death.

**Confounders:** Self-casts, AoE abilities, clone/illusion names, target unavailable, and aggregate chronology.

**Confidence requirements:** ≥100 targeted casts across ≥25 matches for the ability.

**Interaction concept:** Spell icon projects threads to portraits; compare actual and expected target mix.

**Shareable version:** **SPELL LOYALTY — Your best save keeps choosing the offlaner.**

## #36 — Build Stubbornness — OOOH 7.35

**OOOH headline:** **Your build changes less than the problems in front of it.**

**Explanation:** Item sequences remain unusually similar across very different enemy threat profiles and game states. Consistency can be mastery; stubbornness is consistency that underperforms specifically when adaptation signals are strong.

**Evidence:** “Your first three major items are identical in 71% of games. Against heavy silence/control, peers pivot while your sequence and timing barely change.”

**Why care:** A memorized build solves an average game; Dota is rarely average.

**Data recipe:** `purchase_log`; final items; enemy lineup/facets; incoming damage sources; game state; outcome and survival; hero/role baselines.

**Detection logic:** Encode item sequences and threat vectors. Measure conditional sequence entropy and performance residual; flag only low adaptation plus negative outcome in threat-specific cohorts.

**Confounders:** Hero has a mandatory core build, patch meta, player executes familiar items better, and outcome confounding.

**Confidence requirements:** ≥50 games on the hero with ≥15 across at least two distinct threat clusters.

**Interaction concept:** A deck of enemy drafts flips while the player's item row remains—or does not remain—the same.

**Shareable version:** **THE AUTOPILOT BUILD — Different enemies. Same six answers.**

## #37 — Adaptation Speed — OOOH 7.30

**OOOH headline:** **You adapt—but one death later than your best games do.**

**Explanation:** Purchases respond to observed threats, yet the response lag differs. Measure time from threat evidence (first relevant death/damage pattern) to defensive or utility commitment.

**Evidence:** “Your dispel response begins a median 5:20 after the first silence-driven death; in your winning games it begins before the second exposure.”

**Why care:** Adaptability is not just item choice; it is how quickly the player updates their plan.

**Data recipe:** Death times/killer; aggregate incoming source profile; purchase log; item taxonomy; enemy lineup; state and hero/role.

**Detection logic:** Define threat-onset events and first matching counter purchase. Model response-time distribution and subsequent survival; aggregate across threat families into an adaptability trait.

**Confounders:** Damage chronology absent, gold constraints, shop access, team-provided counters, and plan chosen during draft.

**Confidence requirements:** ≥25 threat-response episodes across ≥3 threat families.

**Interaction concept:** A reaction-time card: **THREAT APPEARED → PLAN CHANGED** with percentile context.

**Shareable version:** **PATCH NOTES ARRIVE LATE — You read the enemy correctly, one death after they reveal the lesson.**

## #38 — Creep Diet — OOOH 7.25

**OOOH headline:** **You recover through jungle, not lanes—even when the map wants the opposite.**

**Explanation:** Lane, neutral, and ancient kill composition reveals what kind of farm a player consumes. At scale, state-conditioned creep diet can distinguish safe retreat, lane pressure, and role-inappropriate jungle dependence, though exact farm locations/times are absent.

**Evidence:** “When behind, 58% of your counted creep kills are neutral/ancient versus a 41% role baseline; your team loses lane-objective access faster in those games.”

**Why care:** Farm source changes map pressure and what resources remain for teammates.

**Data recipe:** `killed`; derived lane/neutral/ancient kills; advantage; `lh_t`; role/hero; objectives.

**Detection logic:** Compute match-level creep composition, then model it by average/early/midgame state using only matches dominated by that state. For phase precision, require raw replay extensions; do not invent timestamps.

**Confounders:** Summons, hero-specific neutral farming, match duration, farm totals lack chronology, and assigned recovery plans.

**Confidence requirements:** ≥40 matches; use state language only when state dominates a defined phase.

**Interaction concept:** A plate divided into lane creeps, normal neutrals, and ancients, toggled by wins/losses.

**Shareable version:** **YOUR FARM DIET — Under pressure, your map becomes 60% jungle.**

## #39 — Early Map Anxiety — OOOH 7.20

**OOOH headline:** **Your first ten minutes happen inside a smaller map than everyone else's.**

**Explanation:** The early position histogram has unusually low spatial spread or remains close to safe-side cells, even for roaming-capable heroes. This is territorial caution, not full-match passivity.

**Evidence:** “Your first-10-minute occupied area is in the 14th percentile for position 4, with fewer river/enemy-side samples despite comparable lane state.”

**Why care:** Early supports create information and pressure through where they can stand, not just ward counts.

**Data recipe:** `lane_pos`; side-normalized map grid; early kills; lane/role/hero mobility; lane efficiency; wards.

**Detection logic:** Reflect sides, compute occupied-area, entropy, centroid, river-crossing cell share, and distance from safe structures. Compare with hero-position-matchup cohort.

**Confounders:** Histogram loses order/time, lane assignment, losing matchup, stationary summons, and map patch.

**Confidence requirements:** ≥30 matches on the position and stable map version.

**Interaction concept:** The player's first-10-minute “personal map” appears as a visible territory mask against a peer ghost.

**Shareable version:** **THE SMALL MAP — Your early comfort zone is narrower than 86% of position 4s.**

## #40 — Lane Attachment — OOOH 7.15

**OOOH headline:** **You keep playing the lane after the lane has stopped paying you.**

**Explanation:** Early spatial concentration remains anchored to one lane while runes, kills, and lane efficiency suggest diminishing return. Because `lane_pos` stops at ten minutes, this insight is strictly an early-lane tendency.

**Evidence:** “From minutes 7–10 (approximated by parser samples only when an extended timestamp grid is available) you remain lane-concentrated more than peers while early objective/kill involvement is lower.”

**Why care:** The final lane minutes often decide whether a support/core transfers pressure or merely protects a solved lane.

**Data recipe:** Standard endpoint `lane_pos` for aggregate attachment; early kills/runes/wards; lane outcome; ideally raw replay or an extended time-bucketed position parser for minute 7–10 specificity.

**Detection logic:** Endpoint-only version uses lane-cell concentration across the entire first 10 minutes and labels it cautiously. Production-quality version retains timestamp buckets and detects late-lane persistence after lane value drops.

**Confounders:** The stock endpoint discards sample order, assigned lane duty, siege timing, core protection, and matchup.

**Confidence requirements:** Endpoint-only ≥40 matches and headline softened to “early lane-attached”; exact “after lane ended” requires extended replay telemetry.

**Interaction concept:** A lane tether stretches as map opportunities light up elsewhere; uncertainty makes the missing time order explicit.

**Shareable version:** **LANE-TETHERED — Your early map keeps pulling you back to the same lane.**

## #41 — Recovery Style — OOOH 7.10

**OOOH headline:** **When your lane goes badly, you recover by fighting—not farming.**

**Explanation:** After a negative 10-minute residual, players choose different recovery signatures: absorb safe economy, invade/fight, ward defensively, or accelerate utility. The insight reveals the repeated response and whether it actually closes the deficit.

**Evidence:** “After losing lane, your fight participation rises 33% while farm share remains flat. You recover team advantage faster than farming peers, but your repeat-death risk is higher.”

**Why care:** Recovery is a decision system, not a GPM result. Knowing the personal default lets the player choose rather than react.

**Data recipe:** 10-minute gold/XP residual; minutes 10–20 farm share; kill clusters; wards; purchases; advantage recovery; role/hero.

**Detection logic:** Cluster post-lane behavior vectors into farm, fight, utility, split, and mixed recovery; estimate deficit-closing and death outcomes within matched contexts.

**Confounders:** Draft plan, teammate lane outcomes, role, hero spike, and lane residual error.

**Confidence requirements:** ≥25 clearly lost lanes and ≥8 in the dominant recovery cluster.

**Interaction concept:** A “choose your recovery path” map reveals the player's historical branch and outcomes.

**Shareable version:** **THE COUNTERPUNCHER — Bad lanes make you fight sooner, not hide longer.**

## #42 — Comeback Catalyst — OOOH 7.05

**OOOH headline:** **Your best Dota begins when the game says it is slipping away.**

**Explanation:** Some players produce disproportionate positive fight, objective, or economy swings from disadvantage. This is not generic comeback win rate; it identifies the repeated action that starts recovery.

**Evidence:** “From −5k or worse, your presence in the first positive 1k swing is above the 85th percentile, usually through a kill cluster followed by vision and Roshan.”

**Why care:** It validates a real strength and shows the exact comeback recipe worth repeating.

**Data recipe:** Advantage curves; swing change points; kills/teamfights; player damage/healing/kills; wards; objectives; purchases; role/hero.

**Detection logic:** Detect trough-to-recovery segments. Attribute catalyst evidence from player involvement in the first positive swing event, then compare recovery probability with matched disadvantaged states.

**Confounders:** Team attribution, rubber-band mechanics, opponent throw, and minute curve resolution.

**Confidence requirements:** ≥20 strong-disadvantage episodes and ≥8 recoveries; use “present at” rather than causal “caused” unless stronger telemetry exists.

**Interaction concept:** An advantage graph is dark until the comeback inflection; the player's evidence lights first.

**Shareable version:** **THE CATALYST — When the graph hits bottom, your impact starts climbing.**

## #43 — One More Minute — OOOH 7.00

**OOOH headline:** **Your last minute before death is unusually farm-heavy.**

**Explanation:** Without full creep locations, the endpoint cannot prove “one more wave.” It can still show that CS accumulation immediately before death is unusually high, especially under poor map information or disadvantage.

**Evidence:** “Your minute-before-death last-hit gain is 1.5× your normal rate, and these deaths are less likely to occur in recognized teamfights.”

**Why care:** It exposes a greed threshold with honest telemetry instead of inventing where the farm happened.

**Data recipe:** Death timestamps; minute `lh_t`/`gold_t`; teamfight membership; advantage; friendly ward coverage proxy; major-item proximity.

**Detection logic:** Compare last-hit gain in the 60–120 seconds before death with matched alive windows. Interact with disadvantage, fight absence, and item proximity; label “farm-heavy pre-death,” not “wave death.”

**Confounders:** Minute alignment, carry role, defending waves, death after successful farming, and no creep location.

**Confidence requirements:** ≥30 deaths with ≥12 non-teamfight deaths; adjusted pre-death farm excess.

**Interaction concept:** A death card rewinds one minute and counts every added last hit before the portrait falls.

**Shareable version:** **ONE MORE MINUTE — Your farm rate peaks immediately before too many deaths.**

## #44 — Momentum Dependency — OOOH 6.95

**OOOH headline:** **Your impact compounds leads—but rarely starts recoveries.**

**Explanation:** Impact is much higher after the team is already ahead than in even or losing states. This can describe an excellent accelerator or a player dependent on favorable map conditions.

**Evidence:** “Your kill participation, objective damage, and survival jump above the 80th percentile when ahead, but remain below median at even state.”

**Why care:** Scouting should distinguish lead creation from lead amplification.

**Data recipe:** State buckets; K/D/A and teamfight impact; tower damage/objectives; farm share; wards; hero/role cohort.

**Detection logic:** Estimate state-conditioned impact residuals and decompose creation (events preceding lead) versus amplification (events after lead). Build a momentum-dependence index from several families.

**Confounders:** Role assignment, scaling hero, team strength, causal opportunity, and lineup.

**Confidence requirements:** ≥80 matches with adequate minutes in even/ahead/behind states.

**Interaction concept:** Two grades: **CREATE THE LEAD** and **PRESS THE LEAD**.

**Shareable version:** **THE ACCELERATOR — Once ahead, you make the game feel impossible.**

## #45 — Economy Volatility — OOOH 6.90

**OOOH headline:** **Your farm arrives in bursts, not a rhythm.**

**Explanation:** Minute earned-gold and CS derivatives alternate between explosive spikes and empty stretches more than peers. This can reflect efficient stack clearing, fight-heavy roles, death downtime, or broken farming cadence.

**Evidence:** “Your midgame gold-gain volatility is in the 91st percentile. Empty minutes cluster after fights, while your recovery bursts consume a large team share.”

**Why care:** Stable cadence makes item timings predictable; volatility can strand a player between power spikes.

**Data recipe:** Differenced `gold_t`, `lh_t`, `xp_t`; deaths; fights; stacks; purchases; role/hero/state.

**Detection logic:** Compute robust coefficient of variation and burstiness on active midgame minutes; attribute empty/burst segments to deaths, fights, and stack/neutral profile.

**Confounders:** Support roles, alchemist-like mechanics, stacks, long fights, and minute sampling.

**Confidence requirements:** ≥30 matches and role-adjusted volatility stable over time.

**Interaction concept:** A heartbeat-like economy trace compares the player's rhythm with a smooth peer pulse.

**Shareable version:** **BURST ECONOMY — Feast, pause, feast: your item timings are built in waves.**

## #46 — Farm Entitlement — OOOH 6.85

**OOOH headline:** **When resources are scarce, you take the first share.**

**Explanation:** In low-team-income periods, the player's fraction of earned gold/CS rises rather than falls. That may be correct protection of a win condition or role-inappropriate resource capture.

**Evidence:** “During bottom-quartile team farm minutes, your share rises from 23% to 35%; comparable position 3s yield more to the carry.”

**Why care:** Scarcity reveals priority more clearly than abundance.

**Data recipe:** Player/team minute gold/CS deltas; roles; item timings; state; deaths; hero scaling cohort.

**Detection logic:** Identify scarce-economy minutes and estimate conditional player share. Compare with expected role/hero priority and teammates' delayed spikes.

**Confounders:** Player is the intended win condition, assigned dangerous farm, teammates dead, or summons inflate CS.

**Confidence requirements:** ≥250 scarce-economy minutes across ≥40 matches.

**Interaction concept:** A five-way resource pie shrinks; watch whose slice expands.

**Shareable version:** **FIRST SHARE — When the map runs out of money, it still finds you.**

## #47 — Fight Participation Quality — OOOH 6.80

**OOOH headline:** **You attend many fights. Too few of them improve because you are there.**

**Explanation:** Participation rate is separated from contribution quality: damage, healing, kills, deaths, gold/XP delta, and outcome conditional on presence. High attendance can conceal low-return participation.

**Evidence:** “You register in 78% of detected fights, but your contribution residual is below median in losses and strong only in fights already favored.”

**Why care:** “Join more fights” is bad coaching when selection or execution quality is the real issue.

**Data recipe:** Teamfight aggregates; state at start; player presence; role/hero; fight result; buybacks; objectives.

**Detection logic:** Predict expected contribution and outcome from hero, role, state, and fight size. Score attendance and residual quality separately.

**Confounders:** Detector omissions, initiation value not captured, soft control, and team causality.

**Confidence requirements:** ≥30 detected fights.

**Interaction concept:** Attendance and impact appear as orthogonal axes, locating the player's fight archetype.

**Shareable version:** **PRESENT ≠ IMPACTFUL — You rarely miss the fight; the next step is making your presence change it.**

## #48 — Aggressive Fighter, Conservative Map — OOOH 6.75

**OOOH headline:** **Inside fights you commit hard. Outside them, your map is cautious.**

**Explanation:** High fight damage/kill involvement coexists with a narrow early territory, defensive ward geography, or safe farm composition. Contradictions like this describe a person better than one aggression score.

**Evidence:** “Your fight commitment ranks high, while early territorial spread and aggressive vision rank in the bottom third.”

**Why care:** It reveals that confidence is context-specific; the player may need better setup, not more courage during combat.

**Data recipe:** Teamfight impact; target concentration; early `lane_pos`; ward territory; creep diet; state/role/hero.

**Detection logic:** Build separate combat-aggression and map-aggression latent factors. Surface statistically strong oppositions rather than averaging them away.

**Confounders:** Role, hero range, support duties, early-only position data, and team strategy.

**Confidence requirements:** ≥40 matches and ≥3 signals per latent factor.

**Interaction concept:** A contradiction card flips between **IN THE FIGHT** and **ON THE MAP**.

**Shareable version:** **TWO KINDS OF BRAVE — Aggressive in combat, conservative before it.**

## #49 — Objective Ownership — OOOH 6.70

**OOOH headline:** **When your team takes buildings, your fingerprints are usually on them.**

**Explanation:** Tower damage, credited building kills, item timing, and fight presence reveal who personally converts advantages into structures. This can validate an underappreciated closer.

**Evidence:** “You account for 37% of team tower damage and are credited in 42% of building events despite average kill involvement.”

**Why care:** The Ancient falls to conversion, not KDA.

**Data recipe:** `tower_damage`; `building_kill` player/unit credit; team totals; objectives after fights; hero/role/patch.

**Detection logic:** Compute role/hero-adjusted tower share, credited structure involvement, and post-win objective presence. Separate summon/illusion attribution.

**Confounders:** Summons, last-hit credit, lineup, split push, and team strategy.

**Confidence requirements:** ≥30 matches and ≥20 team structure events.

**Interaction concept:** A demolished map labels each player's structural fingerprints.

**Shareable version:** **THE CLOSER — The scoreboard remembers kills; enemy buildings remember you.**

## #50 — Tower Allergy — OOOH 6.65

**OOOH headline:** **Your damage finds heroes. It avoids buildings.**

**Explanation:** Hero damage and kill contribution are high while tower damage and post-fight building involvement remain low for the hero/role. The useful version adjusts for heroes that genuinely cannot hit towers safely.

**Evidence:** “Your hero-damage percentile is 82; tower contribution is 19, and won-fight windows rarely change that.”

**Why care:** Fighting is only valuable when it changes map state or protects scaling.

**Data recipe:** Hero/tower damage; building events; won clusters; role/hero objective-damage baseline; items.

**Detection logic:** Model expected tower share from hero, role, duration, and team opportunity; flag persistent negative residual after clear won windows.

**Confounders:** Siege safety, wave state, team assignment, low attack range, and objective taken by allies.

**Confidence requirements:** ≥35 matches with ≥20 conversion opportunities.

**Interaction concept:** A damage beam splits toward heroes and buildings; compare actual and expected.

**Shareable version:** **TOWER ALLERGY — Your fights hurt. Their buildings recover.**

## #51 — High-Ground Patience — OOOH 6.60

**OOOH headline:** **You are better at earning high ground than waiting for it.**

**Explanation:** After outer objectives or Aegis, the team/player repeatedly enters costly death/buyback sequences before a safer timing. The endpoint observes consequences and objective order, not exact ramp entry.

**Evidence:** “In high-ground opportunity windows, your teams suffer a core death before the next building in 44% of attempts versus 29% for matched lineups.”

**Why care:** High ground punishes impatience more than almost any other Dota state.

**Data recipe:** Building sequence/status; Aegis; death/buyback sequence; advantage; items; lineup siege baseline.

**Detection logic:** Infer high-ground opportunity after outer towers and strong lead/Aegis. Score death/buyback before barracks versus clean conversion or reset.

**Confounders:** Exact positions absent, base defense, glyph, lineup, tournament strategy, and inferred opportunity.

**Confidence requirements:** ≥15 inferred high-ground windows; headline softened to consequence language.

**Interaction concept:** A ramp gate opens only after evidence conditions; show whether the next event was barracks or a death.

**Shareable version:** **THE LAST RAMP — You solve the map, then rush its hardest ten seconds.**

## #52 — Rune Conversion — OOOH 6.55

**OOOH headline:** **You collect power runes. The next two minutes barely change.**

**Explanation:** Rune pickups are evaluated by subsequent kills, objectives, survival, and economy—not pickup count. Hero- and rune-specific expectations matter.

**Evidence:** “After offensive power runes, your next-two-minute kill involvement is below the hero-role median despite above-average pickup control.”

**Why care:** Rune control is borrowed tempo, much like Aegis on a smaller clock.

**Data recipe:** `runes_log` and type constants; subsequent kills/deaths/objectives; item timing; state; hero/role.

**Detection logic:** Open rune-specific effect windows; score consequential events and compare with matched pickups. Separate bounty/wisdom/lotus-like economy runes from combat runes.

**Confounders:** Rune donated/refilled bottle interactions, exact buff usage absent, defensive rune value, and global team play.

**Confidence requirements:** ≥40 relevant rune pickups; ≥15 offensive power runes for combat language.

**Interaction concept:** Rune icon starts a two-minute fuse; consequences appear before it burns out.

**Shareable version:** **RUNE TOURIST — You secure the power-up more reliably than you spend it.**

## #53 — Roshan Discipline — OOOH 6.50

**OOOH headline:** **Your team earns Roshan windows but starts him in the wrong ones.**

**Explanation:** Roshan timing is compared with enemy deaths, team deaths, advantage, and immediate contest outcome. Player attribution is team-level unless the player is Aegis holder or fight participant.

**Evidence:** “A third of your Roshan attempts/pickups occur without a recent enemy core death or strong vision/lead context; contested outcomes are worse in that subset.”

**Why care:** Roshan converts map control into the safest high-ground attempt; a bad Roshan does the reverse.

**Data recipe:** Roshan/Aegis objectives; preceding/following deaths; ward placements near pit; advantage; buybacks; holder; team identity.

**Detection logic:** Score Roshan safety context in the 120 seconds before kill and consequences after. At player level, describe participation/holder behavior only where supported.

**Confounders:** Attempt start time absent—the endpoint exposes kill, not when Roshan began; smoke/vision and enemy location incomplete.

**Confidence requirements:** Team-level ≥15 Roshan kills; exact “start choice” requires replay extension, so endpoint copy says “Roshan completions.”

**Interaction concept:** Pit-risk dial at Roshan death with preceding map evidence.

**Shareable version:** **ROSHAN TIMING — Your best Roshans begin with dead enemies; your worst begin with hope.**

## #54 — TP Tax — OOOH 6.45

**OOOH headline:** **You spend more on returning to the map than your role peers.**

**Explanation:** TP purchases and total uses can expose expensive map-reset habits or excellent global response, but exact destinations/timing are absent. This is an economy/style signal, not a “late TP” detector.

**Evidence:** “You purchase 28% more TP scrolls per 30 minutes than comparable cores, largely in high-death games; the extra spend overlaps delayed components.”

**Why care:** Repeated inefficient resets quietly tax item timings.

**Data recipe:** `purchase_tpscroll`, purchase log, `item_uses.tpscroll`, deaths, duration, item timings, role/hero.

**Detection logic:** Normalize TP purchases/uses by active minutes and deaths; estimate gold cost and correlate excess with item delays. Do not infer destination or lateness.

**Confounders:** Free TPs on death, Boots of Travel, global response duties, canceled channels, and patch rules.

**Confidence requirements:** ≥40 matches; stable excess and timing association.

**Interaction concept:** A receipt totals the player's “map travel budget.”

**Shareable version:** **THE TP TAX — Your map resets cost more gold than 78% of comparable cores.**

## #55 — Consumable Philosophy — OOOH 6.40

**OOOH headline:** **You buy prevention early—or repairs late.**

**Explanation:** Tangos, salves, raindrops, smokes, dust, wards, and grenades form a repeated spending signature. Timing relative to lane damage, deaths, and threat reveals preventive versus reactive utility.

**Evidence:** “Your raindrop/detection spending begins after the first relevant death more often than peers, while lane sustain is unusually front-loaded.”

**Why care:** Cheap items encode anticipation and can change expensive outcomes.

**Data recipe:** Timestamped consumable purchases; use counts; deaths; incoming sources; wards; lane outcome; role/hero/patch.

**Detection logic:** Build consumable-category timing features and cluster players into preventive, reactive, minimalist, and utility-heavy styles; relate to context-specific outcomes.

**Confounders:** Team buyer versus user, starting items, shared wards/detection, charges, and item semantics.

**Confidence requirements:** ≥50 matches and stable category mix.

**Interaction concept:** A Dota “packing list” labeled **BEFORE TROUBLE** and **AFTER TROUBLE**.

**Shareable version:** **YOUR SURVIVAL PHILOSOPHY — Sustain before lane, detection after death.**

## #56 — Deward Duel — OOOH 6.35

**OOOH headline:** **You keep winning the same invisible fight.**

**Explanation:** Ward kills, sentry placement, and enemy ward survival identify players who consistently read common vision and protect/deconstruct specific areas.

**Evidence:** “Your observer-kill rate per sentry is in the top 12% near Roshan-side entrances, with fewer redundant sentries than peers.”

**Why care:** Vision removal creates safe plays that never appear in KDA.

**Data recipe:** Observer/sentry placement/removal; ward kill counts; coordinates; entity lifetimes; objectives; role/patch.

**Detection logic:** Estimate deward yield from enemy early removals near own sentry placements, normalize by sentry count and territory, and separate natural expiry.

**Confounders:** No explicit placer-to-killer link for every removal, shared detection, Gem, and parser artifacts.

**Confidence requirements:** ≥100 sentry placements and ≥25 plausible enemy ward removals.

**Interaction concept:** An “invisible duel” map pairs likely ward and counter-ward events.

**Shareable version:** **VISION HUNTER — Your sentries find real wards more often than 88% of supports.**

## #57 — Vision Redundancy — OOOH 6.30

**OOOH headline:** **Your wards repeat locations before the enemy forgets them.**

**Explanation:** Placements cluster on the same cells/nearby cliffs across matches, especially after early removals. Repetition can be sound map control or a predictable habit.

**Evidence:** “Half of your aggressive observers land in four small clusters; repeat placements there survive 40% less time.”

**Why care:** Predictable vision is easy vision gold.

**Data recipe:** Side-normalized ward coordinates/times; removals/lifetimes; objective and state context; map patch.

**Detection logic:** Spatially cluster placements, compute conditional repeat probability and survival penalty, and compare with map-wide objective need.

**Confounders:** Strong ward spots should repeat, map changes, team playbook, and disposable vision.

**Confidence requirements:** ≥120 placements with ≥30 aggressive observers.

**Interaction concept:** Ward fingerprints show the four locations the player “signs” most often.

**Shareable version:** **YOUR WARD FINGERPRINT — The enemy only needs to remember four favorite spots.**

## #58 — Ability Build Adaptation — OOOH 6.25

**OOOH headline:** **Your skill build reacts to the lane—or follows the guide anyway.**

**Explanation:** Ordered ability upgrades can vary with lane matchup, early deaths, and role. Measure whether deviations are context-sensitive and whether they improve lane/recovery outcomes.

**Evidence:** “Against high-pressure lanes, you still follow the same first seven upgrades in 83% of games; adaptive peers take the defensive point earlier.”

**Why care:** One skill point can be the cheapest adaptation in Dota.

**Data recipe:** `ability_upgrades_arr`; hero/facet/patch ability metadata; lane matchup; early kill/death events; 10-minute economy; role.

**Detection logic:** Encode upgrade sequences, compare conditional entropy by matchup/threat, and estimate outcome residual for common alternatives.

**Confounders:** Upgrade array lacks exact timestamps, talents/innates, mandatory builds, and selection bias.

**Confidence requirements:** ≥60 games on a hero and ≥15 in a target matchup family.

**Interaction concept:** A skill tree branches at the first meaningful alternative and shows context/outcomes.

**Shareable version:** **GUIDE LOYALTY — Different lane, same seven points.**

## #59 — Facet Identity — OOOH 6.20

**OOOH headline:** **You do not just pick a facet. You become a different player with it.**

**Explanation:** `hero_variant` can condition target choice, farm/fight balance, itemization, spell usage, and survival. The result is a behavioral facet identity rather than simple facet win rate.

**Evidence:** “Facet A makes you fight earlier and target supports; Facet B shifts you toward farm and longer survival, even after patch/state adjustment.”

**Why care:** The “best” facet may not fit the player's strongest decision style.

**Data recipe:** `hero_variant`; ability/item uses; target matrices; minute curves; purchases; fights; outcomes; patch.

**Detection logic:** Estimate within-player facet-conditioned behavioral vectors and outcomes; require overlap in patch/context and shrink sparse variants.

**Confounders:** Facet meta changes, opponent draft determines choice, small samples, and facet ID mapping drift.

**Confidence requirements:** ≥25 matches on each compared facet in overlapping patches.

**Interaction concept:** Two hero portraits split into distinct behavioral silhouettes.

**Shareable version:** **YOUR OTHER FACET — Same hero portrait. Different player underneath.**

## #60 — Neutral Item Adaptation — OOOH 6.15

**OOOH headline:** **You keep the neutral you found, not the neutral the game needs.**

**Explanation:** Timestamped neutral-item history and use counts reveal swap timing and fit with actual incoming threats or role. It is a smaller lever, but unusually personalized.

**Evidence:** “Defensive neutral options appear in your history, but your final choice remains farm-oriented in high-burst games more often than peers.”

**Why care:** Neutral items are free adaptation; poor fit costs no gold but still costs fights.

**Data recipe:** `neutral_item_history`; final neutral IDs; item uses; incoming sources; role/hero/state; patch item taxonomy.

**Detection logic:** Score each available/held neutral against a context-fit model, measure swap delay and fight outcomes after changes.

**Confounders:** Endpoint does not expose all choices offered or team stash availability; item availability is random.

**Confidence requirements:** ≥50 matches and repeated comparable choice opportunities; language must acknowledge unseen availability.

**Interaction concept:** A neutral-item fitting room shows “held,” “swapped,” and “unknown alternatives.”

**Shareable version:** **NEUTRAL LOYALTY — You keep farm tools even when the game starts asking for survival.**

## #61 — Action Entropy — OOOH 6.10

**OOOH headline:** **Your APM is high because you repeat—not because your decisions are varied.**

**Explanation:** Action count and action-type distribution separate mechanical volume from command diversity. This is descriptive, not a skill grade.

**Evidence:** “Your APM is top-quartile, but 86% of orders are move commands and your action entropy is below role peers on comparable heroes.”

**Why care:** It punctures vanity APM while identifying real command-complexity growth longitudinally.

**Data recipe:** `actions`; `actions_per_min`; order-type constants; hero/unit-control metadata; duration; role.

**Detection logic:** Compute normalized Shannon entropy and category mix; compare within hero/controlled-unit cohort and over time.

**Confounders:** Parser action codes drift (`42` is unlabeled in current constants), spam/cancel behavior, summoned units, and no timing.

**Confidence requirements:** ≥30 matches per hero-complexity family.

**Interaction concept:** APM bar splits into command types, then compresses into effective diversity.

**Shareable version:** **APM, DECODED — Fast hands, narrow command vocabulary.**

## #62 — Duo Gravity — OOOH 6.05

**OOOH headline:** **Your games quietly orbit one teammate.**

**Explanation:** Across repeated games together, targeted spells/healing, shared fight presence, ward territory, and synchronized item/farm changes can reveal a natural duo. Exact full-match proximity is unavailable, so the relationship is interaction-based rather than movement-based.

**Evidence:** “With this player, your targeted support value and shared detected-fight presence rise sharply, and both of your outcomes improve beyond party baseline.”

**Why care:** Natural synergy is useful for stacks, role planning, and understanding who shapes a player's decisions.

**Data recipe:** Account/party IDs; ability targets; healing; shared teamfight presence; roles; wards; outcomes; repeated-peer baseline.

**Detection logic:** Build a player-interaction graph from normalized directed support and co-participation edges; detect stable dyads and compare behavior with/without the peer.

**Confounders:** Party selection, team strategy, hero pair, skill difference, and no full proximity data.

**Confidence requirements:** ≥20 games together and ≥40 comparable games apart.

**Interaction concept:** A teammate constellation reveals the strongest behavioral orbit and how the player's style changes beside them.

**Shareable version:** **YOUR NATURAL DUO — Your Dota changes most when this teammate is in the lobby.**

---

# Part 4 — Master ranking

Scores are integers from 1–10 and the weighted total is calculated exactly as specified:

```text
OOOH = .20 Surprise + .20 Resonance + .20 Accuracy
     + .15 Actionability + .15 Shareability
     + .05 Analytical Depth + .05 Uniqueness
```

The scores are intentionally not engineering-priority scores. Accuracy penalizes concepts whose strongest wording exceeds endpoint telemetry; complexity is reported separately. `A/B/C/D` are the data-requirement classes defined above.

| Rank | Insight | OOOH | Surprise | Resonance | Accuracy | Actionability | Shareability | Depth | Unique | Complexity | Data requirement |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | Win Fights, Lose Windows | 9.35 | 9 | 10 | 9 | 10 | 9 | 9 | 9 | Tier 2 | A/B/C/D |
| 2 | You Fixed It; It Moved | 9.20 | 10 | 10 | 7 | 9 | 10 | 9 | 10 | Tier 3 | B/C/D |
| 3 | The Last Man Out | 9.15 | 9 | 10 | 8 | 9 | 10 | 8 | 10 | Tier 2–3 | A/B/C/D |
| 4 | Two Personalities | 9.10 | 10 | 10 | 7 | 8 | 10 | 10 | 10 | Tier 3 | B/C/D |
| 5 | Gold Fever | 9.05 | 10 | 10 | 6 | 9 | 10 | 10 | 10 | Tier 4 | B/C/D |
| 6 | Lane Win, Map Loss | 9.00 | 9 | 10 | 8 | 10 | 9 | 8 | 7 | Tier 3 | A/B/C/D |
| 7 | The Rescue Tax | 8.90 | 9 | 10 | 8 | 9 | 9 | 9 | 7 | Tier 3 | A/B/C/D |
| 8 | Power-Spike Tourist | 8.85 | 9 | 9 | 8 | 9 | 9 | 9 | 10 | Tier 2 | A/B/C/D |
| 9 | Lead Poisoning | 8.80 | 9 | 9 | 8 | 9 | 9 | 8 | 10 | Tier 2 | B/C/D |
| 10 | Chain-Feed Return | 8.75 | 8 | 9 | 9 | 9 | 9 | 8 | 9 | Tier 2 | A/B/C/D |
| 11 | Reactive Vision | 8.65 | 8 | 9 | 9 | 9 | 8 | 8 | 10 | Tier 3 | A/B/C/D |
| 12 | Role Betrayal | 8.60 | 9 | 10 | 8 | 8 | 8 | 8 | 8 | Tier 3 | B/C/D |
| 13 | Farm Reset Reflex | 8.55 | 8 | 9 | 9 | 9 | 8 | 8 | 8 | Tier 2 | A/B/C/D |
| 14 | Delayed Seatbelt | 8.45 | 8 | 9 | 8 | 9 | 8 | 9 | 9 | Tier 3 | A/B/C/D |
| 15 | Old You vs New You | 8.40 | 9 | 10 | 7 | 8 | 8 | 8 | 8 | Tier 4 | B/C/D |
| 16 | Buyback Conviction | 8.35 | 8 | 9 | 8 | 9 | 8 | 8 | 8 | Tier 2 | A/B/C/D |
| 17 | Cleanup Crew | 8.30 | 8 | 9 | 8 | 8 | 9 | 8 | 7 | Tier 2 | A/B/C/D |
| 18 | First Casualty Personality | 8.25 | 8 | 9 | 8 | 9 | 7 | 9 | 8 | Tier 1–2 | A/B/C |
| 19 | Same Enemy Tax | 8.20 | 8 | 9 | 8 | 9 | 8 | 7 | 6 | Tier 2 | A/B/C/D |
| 20 | Death Geography Déjà Vu | 8.15 | 9 | 9 | 6 | 7 | 9 | 10 | 9 | Tier 3 | A/B/C/D |
| 21 | Selective Attendance | 8.10 | 8 | 8 | 8 | 8 | 8 | 9 | 9 | Tier 2 | A/B/C/D |
| 22 | Resource Gravity | 8.05 | 8 | 8 | 8 | 8 | 8 | 8 | 9 | Tier 2 | B/C/D |
| 23 | Space Dividend | 8.00 | 8 | 8 | 8 | 7 | 8 | 9 | 10 | Tier 3 | A/B/C/D |
| 24 | Objective Hangover | 7.95 | 8 | 8 | 8 | 7 | 8 | 9 | 9 | Tier 2 | A/B/C |
| 25 | Frontline Tolerance | 7.90 | 7 | 8 | 8 | 8 | 8 | 9 | 9 | Tier 2 | A/B/C/D |
| 26 | Vision Half-Life | 7.85 | 7 | 8 | 8 | 8 | 8 | 8 | 9 | Tier 2 | A/B/C/D |
| 27 | Aegis Lease | 7.80 | 8 | 8 | 8 | 7 | 7 | 9 | 9 | Tier 2 | A/B/C |
| 28 | Streak Cashout | 7.75 | 7 | 8 | 8 | 7 | 8 | 9 | 9 | Tier 1–2 | A/B/C |
| 29 | Post-Death Personality | 7.70 | 7 | 7 | 8 | 8 | 8 | 9 | 9 | Tier 3 | B/C/D |
| 30 | Target Fixation | 7.65 | 7 | 7 | 8 | 8 | 8 | 8 | 9 | Tier 2 | A/B/C/D |
| 31 | Protector Instinct | 7.60 | 7 | 8 | 8 | 7 | 7 | 9 | 9 | Tier 3 | B/C/D |
| 32 | Executioner vs Setup | 7.55 | 7 | 7 | 8 | 7 | 8 | 9 | 9 | Tier 3–4 | B/C/D |
| 33 | Item Active Amnesia | 7.50 | 7 | 7 | 7 | 8 | 8 | 9 | 9 | Tier 2 | A/B/C |
| 34 | Ultimate Patience | 7.45 | 7 | 7 | 8 | 7 | 8 | 8 | 8 | Tier 3 | B/C/D |
| 35 | Spell Target Loyalty | 7.40 | 7 | 7 | 7 | 8 | 8 | 8 | 8 | Tier 2 | B/C/D |
| 36 | Build Stubbornness | 7.35 | 7 | 7 | 8 | 7 | 7 | 8 | 9 | Tier 3 | B/C/D |
| 37 | Adaptation Speed | 7.30 | 7 | 7 | 8 | 7 | 7 | 8 | 8 | Tier 3 | B/C/D |
| 38 | Creep Diet | 7.25 | 7 | 7 | 7 | 7 | 8 | 8 | 8 | Tier 1–2 | B/C |
| 39 | Early Map Anxiety | 7.20 | 7 | 7 | 7 | 7 | 7 | 9 | 9 | Tier 3 | B/C/D |
| 40 | Lane Attachment | 7.15 | 7 | 7 | 7 | 7 | 7 | 8 | 9 | Tier 4 for exact copy | B/C/D |
| 41 | Recovery Style | 7.10 | 7 | 7 | 7 | 7 | 7 | 8 | 8 | Tier 3 | B/C/D |
| 42 | Comeback Catalyst | 7.05 | 7 | 7 | 7 | 7 | 7 | 7 | 8 | Tier 3 | B/C/D |
| 43 | One More Minute | 7.00 | 7 | 7 | 7 | 6 | 7 | 8 | 9 | Tier 2 | A/B/C/D |
| 44 | Momentum Dependency | 6.95 | 7 | 7 | 7 | 6 | 7 | 8 | 8 | Tier 3 | B/C/D |
| 45 | Economy Volatility | 6.90 | 6 | 7 | 7 | 7 | 7 | 8 | 8 | Tier 2 | A/B/C/D |
| 46 | Farm Entitlement | 6.85 | 6 | 7 | 7 | 7 | 7 | 7 | 8 | Tier 2 | B/C/D |
| 47 | Fight Participation Quality | 6.80 | 7 | 7 | 7 | 6 | 6 | 8 | 8 | Tier 3 | A/B/C/D |
| 48 | Aggressive Fighter, Conservative Map | 6.75 | 6 | 7 | 7 | 6 | 7 | 8 | 8 | Tier 3 | B/C/D |
| 49 | Objective Ownership | 6.70 | 6 | 6 | 7 | 7 | 7 | 8 | 8 | Tier 1–2 | A/B/C |
| 50 | Tower Allergy | 6.65 | 6 | 6 | 7 | 7 | 7 | 7 | 8 | Tier 2 | A/B/C |
| 51 | High-Ground Patience | 6.60 | 6 | 7 | 7 | 6 | 6 | 8 | 8 | Tier 3 | A/B/C/D |
| 52 | Rune Conversion | 6.55 | 6 | 6 | 7 | 6 | 7 | 8 | 8 | Tier 2 | A/B/C |
| 53 | Roshan Discipline | 6.50 | 6 | 7 | 7 | 6 | 6 | 7 | 7 | Tier 3 | A/B/C/D |
| 54 | TP Tax | 6.45 | 6 | 6 | 7 | 6 | 7 | 7 | 7 | Tier 1 | B/C |
| 55 | Consumable Philosophy | 6.40 | 6 | 6 | 6 | 7 | 7 | 7 | 7 | Tier 2–3 | B/C/D |
| 56 | Deward Duel | 6.35 | 6 | 6 | 7 | 6 | 6 | 7 | 8 | Tier 3 | A/B/C/D |
| 57 | Vision Redundancy | 6.30 | 6 | 6 | 7 | 6 | 6 | 7 | 7 | Tier 3 | B/C/D |
| 58 | Ability Build Adaptation | 6.25 | 6 | 6 | 6 | 6 | 7 | 7 | 7 | Tier 3 | B/C/D |
| 59 | Facet Identity | 6.20 | 6 | 6 | 6 | 6 | 6 | 8 | 8 | Tier 3 | B/C/D |
| 60 | Neutral Item Adaptation | 6.15 | 6 | 6 | 6 | 6 | 6 | 7 | 8 | Tier 3 | B/C/D |
| 61 | Action Entropy | 6.10 | 6 | 6 | 6 | 6 | 6 | 7 | 7 | Tier 2 | A/B/C/D |
| 62 | Duo Gravity | 6.05 | 6 | 6 | 6 | 6 | 6 | 6 | 7 | Tier 4 | B/C/D |

---

# Part 5 — Top 20 deep dives

## 5.1 Win Fights, Lose Windows

**Exact concept and chain**

```text
Favorable multi-hero exchange
→ temporary alive/advantage window
→ player increases personal farm instead of conversion behavior
→ no structure/Roshan/forced buyback before respawns
→ opponent retains map state
```

**Data dependencies:** all `kills_log` rows; side/hero/position mapping; `teamfights`; `radiant_gold_adv`; `objectives`; `buyback_log`; player/team `lh_t` and `gold_t`; purchases; patch objective rules.

**Likely algorithm:** Build two engagement layers: OpenDota `teamfights` and independent death clusters using a 20-second rolling gap. A cluster creates a *conversion opportunity* when net enemy deaths ≥2, an enemy position 1/2 dies with no allied core trade, or buyback is forced. Estimate a window end from respawn models or fixed 45/90/150-second horizons. Score conversion as weighted structures, Roshan/Aegis, further kills without equivalent loss, forced buybacks, and aggressive ward gain. Measure player post-window CS/gold share and tower credit. Fit a mixed model for conversion probability with player random effect.

**Normalization and edge cases:** Match on hero position, game minute, lead, alive differential, lineup building damage, outer towers remaining, and Aegis. Censor base-ending sequences and fights where the entire team is too low only when an extended replay layer can verify resources; stock endpoint cannot. Do not blame one player for a team call—word copy as a repeated personal response correlated with weak conversion.

**Minimum sample/confidence:** 25 windows, at least 10 structurally convertible, ≥70% classification coverage, posterior probability of below-peer conversion >95%, and effect replicated in early/recent halves. Confidence badge should show opportunity count and uncertainty.

**Experience:** One insight per viewport. First show only the headline. “Show me” reveals three 120-second timelines, with a farm-share band under deaths/buybacks/objectives. A counterfactual ghost shows the peer conversion distribution, not a fake claim that one tower was guaranteed.

**Share card:** **THE WINDOW SHOPPER** / “Won-fight conversion: 84th percentile from the bottom” / one tiny sequence of skulls → jungle creeps → intact tower.

**Example copy:** “You are good at producing favorable fights. Your leak begins after the last enemy dies: your share of team farm jumps, while towers and Roshan arrive less often than they do for comparable mids.”

## 5.2 You Fixed It; It Moved

**Exact concept and chain**

```text
Old error context declines
→ overall metric appears improved or unchanged
→ a different context absorbs a larger share of the remaining errors
→ coaching should acknowledge the fix and retarget the new bottleneck
```

**Data dependencies:** longitudinal parsed matches; death context vector; item proximity; phase; state; killer role; cluster order; wards/objectives; hero/role/patch/party history.

**Likely algorithm:** Encode each death into a multi-label context: lane/phase, ahead/even/behind, fight ordinal, minutes since last death, minutes to/from major item, recent objective, killer archetype, farm-heavy prior minute, and located region where available. Use hierarchical Dirichlet-multinomial estimates across an early and recent rolling window, then compute category transport: credible declines, stable mass, credible growth. A Bayesian change-point model chooses the split, while a holdout confirms it.

**Normalization and edge cases:** Reweight both windows to the same hero/role/patch mix or compare only overlapping strata. Separate absolute-rate improvement from compositional shift: a category can become a larger share while its raw rate still falls. Do not say “the same mistake” unless the latent trait linkage is triangulated; otherwise say “the remaining deaths moved.”

**Minimum sample/confidence:** 60–100 parsed matches; ≥20 deaths per side; effective sample ≥12 in both shrinking and growing categories; >95% posterior direction and <10% sensitivity to window length.

**Experience:** Start with a win: “You fixed this.” Then animate the residual problem flowing into a new bucket. Evidence includes matched then/now examples and a methodology drawer explaining reweighting.

**Share card:** **PLAYER PATCH NOTES** with `FIXED`, `IMPROVED`, and `NEW ISSUE` rows.

**Example copy:** “Your lane discipline genuinely improved: early deaths fell even after accounting for your newer hero pool. The remaining leak moved to the three minutes before major items, where your risk now rises.”

## 5.3 The Last Man Out

**Exact concept and chain**

```text
Player survives opening
→ second allied death creates strong numerical collapse
→ player remains represented in subsequent fight events
→ player dies late without sufficient return
→ defense/objective availability worsens
```

**Data dependencies:** reconstructed death order; detected teamfight boundaries; player death, kills, damage, healing, item/ability use; buybacks; next objectives; role/hero/frontline expectation.

**Likely algorithm:** For every 3+ death cluster, construct team-alive sequence. Define collapse at `net_allied_deaths >= 2`, or with a calibrated state model using advantage, role value, and buyback. For players alive at collapse, label late death, survival, or unknown. Score return after collapse: enemy deaths, fight result reversal, objective save, high player damage/healing after inferred collapse (exact timing unavailable in stock teamfight aggregates, so this last feature requires a replay extension). Endpoint-only logic must restrict itself to death order and total return.

**Normalization and edge cases:** Position 5 save heroes, durable offlaners, Aegis/reincarnation, base defense, and buyback strategy have different late-death priors. Avoid “refuses to leave” because no movement/exit path exists; “dies after collapse” is observed, “keeps trying to salvage” is a hypothesis.

**Minimum sample/confidence:** 18 losing clusters, 8 alive-at-collapse opportunities, and a 15-point adjusted excess. Single-match version is a moment card, never a trait.

**Experience:** Death-order strip with the player initially highlighted green. At second allied death, background turns red. The final card explicitly labels `Observed`, `Inferred`, and `Replay question`.

**Share card:** **THE LAST MAN OUT** / “Alive for the opening. Dead after the collapse.”

**Example copy:** “You are rarely the first problem in lost fights. You are often the last casualty: once two teammates fall, you die afterward far more often than comparable offlaners.”

## 5.4 Two Personalities

**Exact concept and chain**

```text
Advantage state changes
→ farm/fight/vision/item behavior shifts
→ shift either amplifies or undermines the state
→ player has distinct winning and losing operating modes
```

**Data dependencies:** side-corrected minute advantage; farm-share derivatives; cluster attendance/quality; ward geography/timing; purchase categories; deaths; objectives; roles/heroes.

**Likely algorithm:** Create player-minute features and state labels: `behind <= -3000`, `even`, `ahead >= 3000`, with phase-scaled alternatives. Use a hierarchical generalized additive model to estimate within-player state effects while controlling hero, role, minute, and party. Compress correlated deltas into latent axes—pressure, risk, resource consumption, vision territory, conversion. Cluster axes only after stable individual estimates.

**Normalization and edge cases:** Advantage changes available actions; the model is descriptive, not causal. Scale threshold by game minute, because 3k at minute 10 differs from 3k at minute 50. Separate team decision from player response and do not mix pro/ranked/Turbo.

**Minimum sample/confidence:** 300 minutes in each ahead and behind state across ≥80 matches, ≥3 stable signal families, and empirical-Bayes reliability >0.75.

**Experience:** Winning/losing toggle keeps layout fixed so differences feel physical. Use short sentences: “Ahead: wards move forward; farm share falls; fights arrive sooner. Behind: wards contract; jungle share rises.”

**Share card:** Split portrait: **THE HUNTER** / **THE BUNKER FARMER**.

**Example copy:** “You are not simply aggressive. You are aggressive with permission: when ahead you trade farm for pressure; when behind you retreat into resources more sharply than most position 1s.”

## 5.5 Gold Fever

**Exact concept and chain**

```text
Major item nearly affordable (latent)
→ player CS/farm intensity rises
→ death hazard increases
→ item completion is delayed
→ objective/power-spike window is missed
```

**Data dependencies:** minute total-earned-gold curve; purchase timestamps; item DAG and costs by patch; buybacks; deaths; CS; item-plan inference; objectives; role/state.

**Likely algorithm:** Reconstruct a probabilistic wallet distribution rather than a point estimate. Start from earned-gold curve; subtract timestamped purchases using component DAGs; account for duplicate components and consumables; add uncertain sale/buyback latent variables. Infer likely next major item from observed components and eventual completion. Use a time-varying Cox model for death hazard as a function of estimated distance-to-item, within player and state. Attribute realized delay from death to completion and overlap with objective windows.

**Normalization and edge cases:** The stock endpoint lacks current gold, sales by item/time, reliable/unreliable split, and exact net-worth curve. Validate on a raw-replay sample before using numeric thresholds. Do not publish “250 gold away” from endpoint-only data; publish distance bands with uncertainty. Exclude abandoned item plans and secret-shop/recipe ambiguity.

**Minimum sample/confidence:** 35 item approaches, wallet calibration error small enough to preserve distance-band ordering, and adjusted hazard ratio >1.4 with credible interval excluding 1.

**Experience:** The user first sees a simple item ring and the headline. Methodology expands to a translucent probability band, making uncertainty part of the elegance rather than fine print.

**Share card:** **GOLD FEVER** / “Risk peaks in the last stretch before your item.”

**Example copy:** “We cannot see your exact wallet, but across 41 item approaches the same pattern survives the uncertainty: your farm rate and death risk rise together near completion.”

## 5.6 Lane Win, Map Loss

**Exact concept and chain**

```text
Positive matchup-adjusted lane residual
→ transition decision after minute 10
→ personal/team lead decays before minute 20
→ first post-lane objective or timing is lost
```

**Data dependencies:** 10/15/20-minute player and team gold/XP; lane role and early position histogram; matchup cohort; purchases; early objectives; kill/death sequence.

**Likely algorithm:** Train expected 10-minute economy from hero matchup, position, side, patch, bracket, and party. Define lane win as positive residual with credible threshold, not `lane_efficiency_pct` alone. Measure retained residual at 15/20, first major item timing, first objective involvement, deaths, farm share, and fight presence. Learn transition subtypes: over-farm, bad death, failed rotation proxy, no conversion, or team collapse.

**Normalization and edge cases:** Supports sacrifice lane economy; lane swaps and tri-lanes break matchup labels; global/team events influence 10-minute gold. Require both personal and lane-opponent evidence where possible. Exact rotation timing needs richer positions, so endpoint copy should speak about lead decay and correlated behavior.

**Minimum sample/confidence:** 25 lane-win opportunities in a stable position, reliable matchup model, and transition decay gap ≥0.5 SD.

**Experience:** A baton story at 10, 15, 20 minutes. Each checkpoint asks “Still yours?” and reveals one cause candidate with evidence strength.

**Share card:** **THE DROPPED BATON** / “Lane: won. Lead at 20:00: usually gone.”

**Example copy:** “Laning is not your bottleneck. You beat the matchup more often than peers, but that advantage survives to minute 20 less often—usually after a farm-heavy transition rather than an early objective.”

## 5.7 The Rescue Tax

**Exact concept and chain**

```text
Ally becomes first casualty
→ target player remains/commits resources
→ target becomes next allied death
→ exchange/objective does not improve
```

**Data dependencies:** death order; cluster gaps; fight ability targets/healing/item uses; role/save-kit taxonomy; subsequent kills, objectives, advantage.

**Likely algorithm:** Detect ally-first sequences with next allied death within 5–25 seconds. Score *rescue evidence* from targeted heals/saves in the teamfight aggregate and player role. Score *tax* as second death minus enemy kill/objective/advantage return. Create three labels: supported rescue tax, possible salvage death, and ordinary correlated death. Never collapse them.

**Normalization and edge cases:** Save heroes and sacrificial supports should have higher expected follow-up death. Simultaneous AoE deaths, high-ground defense, and bait plans are excluded or down-weighted. Aggregated ability targets do not prove cast order; that lowers rescue confidence.

**Minimum sample/confidence:** 15 sequences; at least 6 with support evidence for the strong label; adjusted excess versus role peers.

**Experience:** Interactive “follow or fold?” moment. The product does not claim the correct answer before reveal; it shows the historical cost of the branch.

**Share card:** **THE RESCUER** / “Loyalty creates a second casualty more often than it creates a trade.”

**Example copy:** “We cannot see your intent, but the sequence is consistent: after an ally falls first, you are unusually often next, and those second deaths rarely recover equivalent value.”

## 5.8 Power-Spike Tourist

**Exact concept and chain**

```text
Major item completes
→ expected temporary power window opens
→ behavior remains farm/reset
→ first consequential event arrives late
→ relative timing advantage decays
```

**Data dependencies:** item completion inference; hero-item timing distributions; fights/objectives; item uses; player/team farm share; state and teammate readiness proxies.

**Likely algorithm:** Resolve completed item time from purchase log and item DAG. For each hero-item-role cohort, estimate distribution of time-to-next consequential event: player-present fight, kill, objective, forced buyback, or meaningful item use. Fit competing risks where “productive event,” “death,” and “no activation before next enemy spike” compete. Compare behavior before/after completion.

**Normalization and edge cases:** BKB, Blink, aura, farming, and defensive items have different expected activation. A defensive purchase may succeed through non-events. Team readiness and lane state are missing, so avoid asserting the player should have fought in a specific minute.

**Minimum sample/confidence:** 20 major completions, 8 in one item class, and stable delay residual ≥45 seconds or 0.6 SD.

**Experience:** Item completion gets a satisfying audio/visual beat followed by a measured silence. “What counted as activation?” is expandable.

**Share card:** **POWER-SPIKE TOURIST** / “Fast item. Slow consequence.”

**Example copy:** “Your timings are good. The behavior after them is quiet: compared with similar offlaners, your Blink changes the game about two minutes later.”

## 5.9 Lead Poisoning

**Exact concept and chain**

```text
Strong lead
→ player's adjusted death hazard rises
→ death transfers bounty/map access
→ objective or advantage is returned
```

**Data dependencies:** state curves; deaths; streak/bounty proxy; next objectives; buybacks; farm share; hero/role; enemy comeback potential.

**Likely algorithm:** Create side-corrected, phase-scaled lead z-scores. Fit player-specific survival model with nonlinear lead effect and controls. For strong-lead deaths, measure 180-second lead loss, structures/Roshan conceded, and whether death occurred in a recognized conversion/high-ground window. Distinguish pressure deaths with team returns from isolated loss events.

**Normalization and edge cases:** Leading teams occupy dangerous territory and attempt objectives, so naive ahead/behind death rates are biased. Match on objective attempt, role, hero, game minute, and team alive state. “Reckless” is interpretive; “death hazard rises while ahead” is observed.

**Minimum sample/confidence:** 250 strong-lead minutes, 12 deaths there, adjusted HR >1.25, and measurable downstream cost in ≥6 events.

**Experience:** The lead graph physically fractures at player deaths; productive deaths are green cracks, returned-map deaths red.

**Share card:** **LEAD POISONING** / “Your safety margin shrinks when your gold lead grows.”

**Example copy:** “Your aggression creates pressure, but your personal death risk rises after +5k even after accounting for high-ground and role. Those deaths return more map than your pressure earns.”

## 5.10 Chain-Feed Return

**Exact concept and chain**

```text
Death/respawn
→ short alive-time before next exposed event
→ second death with little intervening value
→ recovery and map control compound negatively
```

**Data dependencies:** death times; phase/level respawn estimate; buybacks; intervening kills/objectives/purchases/CS; advantage; role.

**Likely algorithm:** Estimate alive-time between deaths by subtracting expected respawn duration, with a distribution rather than exact value. Treat buyback as zero/short respawn and separate. Define repeat death within four active minutes; calculate intervening value. Compare post-respawn hazard to matched alive windows using self-controlled case series.

**Normalization and edge cases:** Early short respawns, base defense, buyback, and global heroes need separate models. Level at exact death is approximated from `xp_t`; uncertainty propagates into alive-time band. The endpoint cannot prove returning to the same location.

**Minimum sample/confidence:** 35 deaths, 8 repeat opportunities, post-death incidence ratio >1.4, and examples with low intervening value.

**Experience:** Respawn corridor begins only when the estimated respawn ends. The uncertainty band is visible; the second death lands inside or outside it.

**Share card:** **THE REVOLVING DOOR** / “Your next four active minutes are your most dangerous.”

**Example copy:** “The pattern is not simply ‘two deaths close together.’ After accounting for respawn time, your first four active minutes back carry an unusually high repeat-death risk.”

## 5.11 Reactive Vision

**Exact concept and chain**

```text
Death/lost objective in a map region
→ observer/sentry placed nearby shortly afterward
→ vision explains the previous failure
→ next dangerous entry was not prepared in advance
```

**Data dependencies:** exact ward time/location/entity handle; deaths with known/estimated region; building/Roshan events; ward survival; map polygons; role and team ward burden.

**Likely algorithm:** Normalize map coordinates by side. For each ward, classify region and search ±180 seconds for related events. A probabilistic classifier uses time direction, distance, state, objective schedule, and ward type to label preparatory, reactive, recovery, maintenance, or ambiguous. Build a personal mix and estimate downstream ward survival and event outcome.

**Normalization and edge cases:** Most ordinary death locations are missing, so use building/Roshan and teamfight death positions as high-confidence anchors and kill timing/ward region as lower confidence. Losing territory makes reactive defense correct. Shared support duties require team-level denominator and buyer/placer split.

**Minimum sample/confidence:** 80 placements, 20 high-confidence aggressive/pre-objective placements, classification precision validated on replay samples, and a ≥15-point mix difference.

**Experience:** “Guess what happened first?” is the right interaction because it turns temporal direction into a felt discovery. After the reveal, compare proactive and reactive examples side by side.

**Share card:** **THE AUTOPSY WARDER** / ward icon behind a faded skull.

**Example copy:** “Your ward count is healthy. Its timing is not: your aggressive vision is much more likely to appear after a nearby loss than before the team enters.”

## 5.12 Role Betrayal

**Exact concept and chain**

```text
Queued/inferred position sets resource expectation
→ actual farm/ward/item/interaction vector resembles another position
→ teammate timings and team composition shift
→ player is functionally playing a different role
```

**Data dependencies:** `position_est` with uncertainty; lane role; rolling farm share; ward burden; item cost/timing; damage/healing/targeting; objectives; teammate item timings.

**Likely algorithm:** Learn a behavioral role embedding per patch/bracket from high-confidence positions. Features include 10–25-minute farm share, ward placement/purchase share, item spend category, support-target value, tower share, fight contribution, and creep diet. Infer nearest played-role distribution and compare with queued/estimated role. Link mismatch to teammate timing displacement, but do not declare causation.

**Normalization and edge cases:** Flexible 3/4 roles, greedy supports, sacrificial cores, role swaps, and unusual drafts are legitimate. Require stable mismatch over many matches and never use a single OpenDota `position_est` as ground truth. Party/team strategies deserve their own cohort.

**Minimum sample/confidence:** 30 matches on claimed role, behavioral posterior >70% for another role, and ≥3 independent family mismatches.

**Experience:** Two role jerseys overlap. The user can drag evidence chips between them and inspect how the classification changes.

**Share card:** **THE SECRET CORE** / “Position 4 queue. Position 2 economy.”

**Example copy:** “Your hero pool says roaming support; your minutes 12–25 say secondary core. This is not about total GPM—farm share, item spend, and ward burden all move together.”

## 5.13 Farm Reset Reflex

**Exact concept and chain**

```text
Engagement ends
→ player's CS/gold-share slope rises
→ response is similar after wins and losses
→ adaptive reset becomes automatic reset
```

**Data dependencies:** engagement end; minute CS/gold derivatives; result; alive differential; objectives; item timing; role/state.

**Likely algorithm:** For each engagement, compare 3-minute pre/post active farm rate and team share. Fit interaction between response and fight result/opportunity score. A healthy adaptive profile is high reset after losses/even trades and lower reset when conversion score is high. An automatic profile has a large intercept and weak context interaction.

**Normalization and edge cases:** Carries appropriately reset more; low HP/mana and lane state are unobserved. Minute boundaries smear short windows. Use multiple horizons and exclude engagements crossing match end.

**Minimum sample/confidence:** 30 engagements, ≥10 wins/losses, and context-interaction reliability >0.7.

**Experience:** A rhythm animation shows `farm → fight → farm`; winning-fight examples interrupt the loop with objectives when peers do.

**Share card:** **THE RESET BUTTON** / “Same next move, different fight result.”

**Example copy:** “Reset discipline is one of your strengths. The leak is that it barely changes when the fight win leaves a tower or Roshan open.”

## 5.14 Delayed Seatbelt

**Exact concept and chain**

```text
Enemy threat is visible in draft/first death
→ offensive/core build continues
→ repeated relevant death occurs
→ defensive purchase begins/completes
→ dangerous window has already passed
```

**Data dependencies:** enemy lineup; killer/death timing; aggregate incoming damage sources; purchase sequence; item counter taxonomy; state and gold constraints.

**Likely algorithm:** Build threat embeddings from draft and observed incoming sources. Define threat onset as draft prior updated by first relevant death. Identify first counter commitment at component level, not only completion. Model response lag in deaths and minutes; compare survival before/after with matched episodes and peer timing.

**Normalization and edge cases:** BKB is not always the answer; teammates may provide dispel/save; gold and shop access constrain timing; damage totals lack chronology. Use a counter set with expert priors and allow “no personal item required.”

**Minimum sample/confidence:** 20 threat matches, 8 clearly delayed episodes, and response-lag gap ≥1 death or 120 seconds.

**Experience:** Threat icons appear at draft, strengthen after evidence, and the defensive component arrives on the same line. The user can inspect alternative items but sees no prescriptive certainty.

**Share card:** **THE DELAYED SEATBELT** / “Correct protection. One death late.”

**Example copy:** “You do adapt to silence-heavy games. The recurring issue is timing: your first defensive commitment most often begins after the second relevant death.”

## 5.15 Old You vs New You

**Exact concept and chain**

```text
Same adverse context over time
→ next-action distribution changes
→ outcome distribution changes or remains stable
→ player receives behavioral patch notes
```

**Data dependencies:** chronological history; context-conditioned actions; stable identity; hero/role/patch overlap; outcomes and confidence.

**Likely algorithm:** Create behavior vectors for standardized contexts—lost lane, strong lead, consecutive deaths, new major item, won fight. Fit a dynamic hierarchical model or fused-lasso change points per feature. Only report a change that persists after matching early/recent hero-role-patch composition and survives a placebo split.

**Normalization and edge cases:** Meta and role changes may be the story rather than noise; show them separately. Parsed-match coverage may be non-random over history. Never infer deliberate learning unless the user confirms it.

**Minimum sample/confidence:** 120 matches over ≥8 weeks, 35 each side, effective overlap >0.6, and change posterior >95%.

**Experience:** “Patch notes” is ideal: Buffed, Nerfed, Reworked, Unchanged. Each statement opens a then/now evidence pair under matched context.

**Share card:** **PLAYER PATCH 2026.08** / “Recovery: reworked from farm-first to fight-first.”

**Example copy:** “The old version of you hid after losing lane. The recent version contests the next action sooner—and closes the deficit faster, at the price of slightly higher volatility.”

## 5.16 Buyback Conviction

**Exact concept and chain**

```text
Death under objective pressure
→ buyback commits gold/future option
→ second life changes or fails to change next 120 seconds
→ quantify what the commitment purchased
```

**Data dependencies:** buyback time; death time/order; objective sequence; kills/deaths after buyback; advantage swing; future item purchase delay; approximate death timer/cost.

**Likely algorithm:** Classify buyback context: base defense, objective contest, fight re-entry, farm/tempo, desperation. Score a second-life value vector: objective saved/taken, net kills, survival, lead swing, and delayed next major item. Compare with state-matched role peers, not with a fictional no-buyback counterfactual.

**Normalization and edge cases:** Exact buyback cost needs current net worth not exposed as a series; use range estimates. Team calls dominate. A buyback can be correct even if the game remains lost. Separate decision quality from realized outcome.

**Minimum sample/confidence:** A single-match ledger is valid; a personal label requires ≥12 buybacks and ≥5 in a repeated context.

**Experience:** The ledger starts with “This is what you spent” and “This is what the next life produced.” A methodology drawer explains why outcome is not identical to correctness.

**Share card:** **SECOND-LIFE ROI** with Saved / Traded / Wasted distribution.

**Example copy:** “Your base-defense buybacks produce real value. Your re-entry buybacks after the team is already down three heroes usually purchase only another short life.”

## 5.17 Cleanup Crew

**Exact concept and chain**

```text
Fight develops and resources are spent
→ player kills occur late in death order
→ high damage/return distinguishes finisher from last hitter
→ cleanup identity can be strength or delayed commitment
```

**Data dependencies:** ordered cluster kills/deaths; player teamfight damage/kills/uses; hero role and execute/reset mechanics; fight result.

**Likely algorithm:** Compute kill ordinal percentile per cluster and late-kill share. Combine with total fight damage, kill conversion, survival, and item/ability use into three subtypes: high-output finisher, low-output last hitter, delayed/absent opener. Raw event extension would improve first-contribution timing but is not required for the conservative subtype.

**Normalization and edge cases:** Carry/reset/execute heroes expect later kills; two-death skirmishes need separate treatment; no damage chronology. Use hero-specific baselines and avoid “kill stealing.”

**Minimum sample/confidence:** 25 multi-death clusters and 15 player kills inside; subtype agreement across two time splits.

**Experience:** Fight credits roll from first to last death while damage and kill layers can be toggled independently.

**Share card:** **CLEANUP CREW** / “Your kills arrive after the fight becomes chaos.”

**Example copy:** “You are not farming last hits on heroes: your late kills come with high total fight damage. Your strength is surviving long enough to finish the expensive targets.”

## 5.18 First Casualty Personality

**Exact concept and chain**

```text
Engagement produces first allied death
→ player is that death more than role/hero expectation
→ return determines productive initiation versus lost opening
```

**Data dependencies:** death order; fight size/result; player damage/healing/kills/uses; role/hero durability; objectives.

**Likely algorithm:** Estimate expected first-death probability from position, hero, side, phase, state, and fight size. Calculate residual. Subtype first deaths by team return, player contribution, and fight result. Strong copy requires both excess frequency and low return; otherwise celebrate initiation burden.

**Normalization and edge cases:** Aegis/reincarnation, bait, saves, base defense, and deliberate sacrifice. Damage total may occur before or after a revival/buyback inside window.

**Minimum sample/confidence:** 20 clusters and 8 first deaths; residual >15 points.

**Experience:** The product asks “First domino or first move?” and reveals return evidence.

**Share card:** **THE FIRST DOMINO** / useful-first-death percentage.

**Example copy:** “Your role expects contact. The issue is return: you are first down more often than comparable offlaners, and too many of those openings create little damage or trade.”

## 5.19 Same Enemy Tax

**Exact concept and chain**

```text
Specific enemy archetype appears
→ player suffers excess death/damage concentration
→ item/target response does not adjust enough
→ matchup cost repeats across games
```

**Data dependencies:** killer identity/time; damage sources received; enemy role/hero; item response; player target allocation; matchup cohort.

**Likely algorithm:** Model expected killer share for each enemy hero/archetype from matchup, position, lane, and exposure. Use beta-binomial shrinkage to estimate excess. Then evaluate adaptation proxies: defensive purchase timing, return kills, and total pressure toward that target. Generate advice only from known counter families and evidence.

**Normalization and edge cases:** Assassins legitimately kill backliners; lane counters inflate exposure; killer gets last hit while another source caused death. Combine killer and incoming-source evidence.

**Minimum sample/confidence:** Enemy appears ≥15 times, ≥12 relevant deaths, posterior excess >95%.

**Experience:** A wanted poster is emotionally legible, followed immediately by “matchup expectation” so it does not become superstition.

**Share card:** **YOUR NEMESIS** / expected deaths versus actual.

**Example copy:** “This hero is supposed to threaten your role. It still kills you far more often than the matchup predicts, and your item response changes less than peers'.”

## 5.20 Death Geography Déjà Vu

**Exact concept and chain**

```text
Detected-fight deaths produce coordinates
→ side-normalized points cluster in semantic map regions
→ nearby friendly vision/objective context repeats
→ player gets a recognizable spatial warning pattern
```

**Data dependencies:** teamfight `deaths_pos`; side; map version and semantic polygons/graph; wards and lifetimes; objective context; role/state.

**Likely algorithm:** Reflect coordinates into a common Radiant-oriented frame. Snap points to a navigation/semantic map graph and use HDBSCAN with map-distance rather than Euclidean distance. Estimate opportunity-adjusted excess from peer death locations and player fight presence. Annotate clusters with nearby friendly vision and objective type.

**Normalization and edge cases:** Location coverage is sparse and biased to ≥3-death fights. Map topology changes by patch. Repeated high-ground defense deaths may be forced. Present coverage (“20 of 61 deaths located”) prominently.

**Minimum sample/confidence:** 20 located deaths, cluster ≥6, silhouette/stability threshold, peer-adjusted density excess, and map-version consistency.

**Experience:** A map of “memory scars” is more resonant than a generic heatmap. Each scar opens its fights and shows whether allied vision existed.

**Share card:** **DANGER DÉJÀ VU** / named region / located-death share.

**Example copy:** “We can locate only deaths inside large parsed fights. Within that honest subset, one pattern is hard to ignore: your deaths repeatedly collect at enemy-side chokepoints without nearby observer coverage.”

---

# Part 6 — Top 10 “holy shit” experiences

Engineering difficulty is intentionally ignored here. These define the ceiling.

## 1. The personal cause-and-effect movie

Combine **Gold Fever**, **One More Minute**, **Power-Spike Tourist**, and the next objective into a 30-second story: item nearly complete → farm accelerates → death → item delayed → objective missed. It is powerful because it does not merely label greed; it shows the trigger, behavior, and cost in the player's own timeline.

## 2. Winning You / Losing You

The user toggles between two complete behavioral silhouettes built from the same features and layout. The shock comes from recognizing that “my playstyle” is actually conditional: pressure, farm, wards, purchases, and death risk all change together with the advantage state.

## 3. The fight that ends twice

For **The Last Man Out**, replay the death-order sequence as portraits falling. Stop after the second allied death and ask the player what they think they usually do next. The reveal is a distribution of late deaths, survivors, and reversals—not a generic coaching clip.

## 4. You win fights better than you win games

Show five undeniable won-fight windows followed by intact towers, unclaimed Roshan, and rising personal farm share. The concept is memorable because it reframes a player's perceived strength (“we win fights”) as the doorway to the real weakness (“we fail to cash them”).

## 5. Death migration

Animate old mistakes disappearing and remaining deaths flowing to new contexts. This feels deeply personal because it acknowledges learning before finding the next frontier; ordinary stat products flatten both into the same average.

## 6. Player patch notes

Publish quarterly behavioral patch notes: “lane deaths fixed,” “recovery style reworked,” “lead discipline nerfed.” The ideal execution pairs statistically matched old/new moments and lets the player verify each change rather than accepting a black-box trend.

## 7. The role you actually play

Put queued/inferred role beside behavioral role and make the evidence draggable: farm share, ward burden, item spend, protection targets, objective damage. A contradiction like “position 4 hero, position 2 economy” is instantly stack-shareable and strategically useful.

## 8. Guess what happened before this ward

Show a ward placement alone and ask whether it came before or after the death/objective in that region. A sequence of reveals makes **Reactive Vision** visceral; the player learns to feel preparatory versus autopsy vision.

## 9. The map remembers

Instead of a generic death heatmap, reveal a small number of semantic “memory scars” with names, confidence, vision context, and evidence fights. The honesty of “we can locate 20 of 61 deaths” makes the repeated cluster more believable, not less.

## 10. Your Dota relationship graph

Build a constellation of teammates and enemies from directed support, target, kill, damage, and shared-fight edges. The most powerful result is not “most played with”; it is “this teammate changes your resource and protection behavior” or “this enemy archetype owns an unexplained share of your deaths.”

---

# Part 7 — Insight combinations and narrative systems

Standalone cards become substantially stronger when they form a trait → pattern → moment → consequence → recommendation chain.

## 7.1 Commitment without stop-loss

```text
Trait: high commitment
→ Last Man Out + Rescue Tax + Objective Hangover
→ three death-order moments after numerical collapse
→ deaths remove buyback/objective defense
→ recommendation: define a personal second-allied-death stop rule
```

User-facing synthesis: **“Your courage is real. Your stop-loss is late.”** This avoids calling the player simply reckless; the same trait produces valuable frontlining and costly salvage.

## 7.2 Timing greed

```text
Trait: item-oriented risk tolerance
→ Gold Fever + One More Minute + Power-Spike Tourist
→ farm rises before completion; death delays item; activation arrives late
→ two separate objective windows miss the timing
→ recommendation: play safer before completion, faster after completion
```

User-facing synthesis: **“You take the most risk before your item and the least risk after it.”** The contradiction is more revealing than either metric.

## 7.3 Conversion gap

```text
Trait: strong combat, weak closure
→ Cleanup Crew + Win Fights, Lose Windows + Tower Allergy
→ high late-fight output
→ no structural conversion and low tower share
→ recommendation: make the next objective call before the fight begins
```

## 7.4 Setback acceleration

```text
Trait: action-biased recovery
→ Post-Death Personality + Chain-Feed Return + Recovery Style
→ re-engagement comes sooner after consecutive deaths
→ repeated deaths compound map loss
→ recommendation: one wave/ward/item reset gate before re-entry
```

Copy: **“You respond to setbacks by speeding up. Your best recoveries add one reset first.”**

## 7.5 Lead discipline

```text
Trait: momentum amplifier
→ Momentum Dependency + Lead Poisoning + Objective Hangover
→ excellent pressure while ahead
→ extra post-objective commitment returns the lead
→ recommendation: cash out after the objective, not after the next kill
```

## 7.6 Invisible support identity

```text
Trait: protector
→ Protector Instinct + Spell Target Loyalty + Executioner vs Setup
→ repeated support value flows to one teammate/role
→ recipient survives and produces team damage
→ recommendation: formalize the duo—or redirect when win condition changes
```

## 7.7 Reactive map control

```text
Trait: evidence-driven rather than anticipatory vision
→ Reactive Vision + Vision Redundancy + Vision Half-Life
→ wards follow losses and reuse familiar cells
→ early removals reduce the next information window
→ recommendation: one pre-objective ward in a non-repeated cluster
```

## 7.8 Economic identity conflict

```text
Trait: resource gravity
→ Role Betrayal + Farm Entitlement + Resource Gravity
→ farm share expands under scarcity
→ teammate core timing shifts later
→ recommendation: explicitly choose who owns recovery farm before queues begin
```

## 7.9 Lane-to-map bottleneck

```text
Trait: excellent opening, weak handoff
→ Lane Win, Map Loss + Lane Attachment + Farm Reset Reflex
→ lane advantage exists at 10
→ early map remains narrow and next response is farm
→ recommendation: pre-plan the first move unlocked by the lane lead
```

## 7.10 Adaptive item intelligence

```text
Trait: slow plan updating
→ Same Enemy Tax + Build Stubbornness + Delayed Seatbelt + Adaptation Speed
→ threat repeatedly kills player
→ build remains stable; counter arrives after second death
→ recommendation: define first-evidence component triggers by threat family
```

## 7.11 Higher-level latent traits

| Trait | Observable triangulation | Never reduce it to |
| --- | --- | --- |
| Commitment | late cluster deaths, rescue sequences, post-objective continuation, buybacks | deaths per match |
| Greed | pre-death farm, latent item proximity, scarce-economy share, defensive response lag | GPM |
| Discipline | state-conditioned death hazard, conversion/reset choices, active use, ward preparation | KDA |
| Initiative | presence in first recovery swing, pre-objective vision, first post-lane conversion | fight participation total |
| Adaptability | threat-to-purchase lag, build entropy, skill/facet changes, recovery strategy | number of different items |
| Territoriality | early position spread, ward regions, objective follow-through, death-region clusters | a movement heatmap |
| Conversion | won-window objectives, tower share, Aegis lease, streak cashout | tower damage alone |
| Team reliance | protector/duo edges, resource redistribution, attendance quality | party size |
| Volatility | economy burstiness, chain-death hazard, state-conditioned swings | standard deviation of KDA |

Each trait should be published only when at least three independent signal families agree. Otherwise, show the granular insight without forcing a personality label.

---

# Part 8 — Interactive report architecture

## 8.1 Product form: a story, not a dashboard

Use one insight per viewport and a deliberate rhythm:

```text
Cold open revelation
→ “show me the evidence”
→ one interactive proof
→ why it matters
→ one practical experiment
→ next revelation
```

The default report should expose 5–8 conclusions, not all eligible metrics. A ranking service selects insights using:

```text
publish_score = OOOH_prior
              × confidence
              × personal_effect_size
              × evidence_completeness
              × novelty_to_this_player
              × diversity_penalty_adjustment
```

The diversity term prevents five death cards or three versions of farm greed from crowding out the story.

## 8.2 Report acts

1. **Hook — “The thing you probably do not know.”** Lead with one high-confidence contradiction or causal chain.
2. **Combat identity.** One fight-selection/death-order insight with a specific moment.
3. **Map/economy identity.** Vision, farm, or item timing.
4. **State identity.** Winning/losing personality or recovery style.
5. **Relationships.** Teammate/enemy graph when coverage supports it.
6. **Change over time.** A genuine improvement or migration; suppress if history is short.
7. **Synthesis.** Two or three latent traits, each grounded in cards already seen.
8. **One experiment.** A narrow behavior to try for the next ten games.
9. **Share finale.** A single identity card plus optional report link; never dump private match detail by default.

## 8.3 Evidence contract on every insight

Every card internally carries:

- `observation`: directly measured facts.
- `inference`: reconstruction plus algorithm version.
- `hypothesis`: Dota interpretation to verify.
- `coverage`: relevant matches/opportunities and missingness.
- `cohort`: hero, role, bracket, patch, mode, party filters.
- `effect`: point estimate and interval.
- `examples`: representative, not cherry-picked; include one counterexample when possible.
- `confounders`: the two most material for this user.
- `freshness`: date range and parser/constants versions.

The UI converts this into a simple confidence label—**Strong pattern**, **Promising pattern**, or **One-match observation**—with full methodology behind “How sure are we?”

## 8.4 Which interaction fits which insight

| Insight shape | Best interaction | Avoid |
| --- | --- | --- |
| Ordered deaths/fights | Portrait death-order strip, short timeline, replay deep link | Pie chart of death types |
| Cause→decision→cost | Scroll-triggered causal chain with exact events | Correlation scatter as the primary view |
| State contrast | Fixed-layout winning/losing toggle | Separate pages users must remember |
| Spatial pattern | Semantic map scars, ward rewind, side-normalized overlay | Undifferentiated heat cloud |
| Item timing | Filling item ring, threat/purchase timeline, activation fuse | Build list with timestamps only |
| Longitudinal change | Then/now matched moments, player patch notes, migration flow | Raw monthly trend line |
| Relationships | Directed constellation with target/support edges | “Most played with” table |
| Population comparison | Percentile ghost/interval plus cohort label | Leaderboard framing |
| Method-heavy model | Plain conclusion first; expandable recipe and uncertainty | Model jargon in headline |

## 8.5 Progressive disclosure

Three layers are enough:

1. **Revelation:** headline, two evidence numbers, one sentence of consequence.
2. **Proof:** interactive timeline/map/comparison and 2–4 representative examples.
3. **Method:** fields, algorithm, cohort, uncertainty, confounders, and exclusions.

Experts can inspect layer 3; most players should understand layer 1 in under eight seconds.

## 8.6 Recommendations as experiments

Avoid pretending the data knows a universally correct play. Convert findings into falsifiable personal experiments:

- “For ten games, after the second allied death, disengage unless a core trade is already secured.”
- “Complete the pre-planned objective call before the power-spike item arrives.”
- “Place one objective ward before entering the region, not after the first loss.”
- “After two deaths, require one resource reset—wave, ward, or component—before the next uncertain fight.”

The report then measures whether the targeted signal changes. This closes the coaching loop and powers **Old You vs New You** without claiming emotion or intent.

## 8.7 Share design and privacy

Share cards should contain identity, one defensible comparison, sample size, and a memorable visual. They should omit account ID, exact teammate names, chat, and match IDs unless the user opts in. A card must never say “you are tilted,” “you are selfish,” or “you panic”; it can say the observed behavior changes after a setback.

## 8.8 End-of-report synthesis

The synthesis should sound like a scout who watched the games:

> “You are a high-commitment momentum player. Your best Dota appears once a fight is already moving: you survive openings, clean up well, and press leads. Your losses come from the same strength running one decision too long—late exits, post-objective pursuit, and buybacks into collapsed numbers. The experiment is not ‘be less aggressive.’ It is ‘cash out one decision earlier.’”

That paragraph is assembled only from insights the user has already seen and can reopen. No free-floating personality prose.

---

# Part 9 — Technical feasibility tiers

## Tier 1 — Straightforward deterministic logic

Primarily exact logs, simple windows, and transparent aggregation:

- First Casualty Personality
- Buyback Conviction (single-match ledger)
- Streak Cashout
- Objective Ownership
- TP Tax
- Creep Diet
- Rune Conversion
- basic Farm Reset Reflex
- basic Power-Spike Tourist
- basic Same Enemy Tax

Requirements: constants catalog, hero↔player mapping, kill/death inversion, item DAG, event-window library, and coverage flags.

## Tier 2 — Advanced analytics

Multiple signals, matched cohorts, and careful reconstruction:

- Win Fights, Lose Windows
- The Last Man Out
- Lane Win, Map Loss
- Chain-Feed Return
- Lead Poisoning
- Rescue Tax
- Farm Reset Reflex (state-aware)
- Delayed Seatbelt
- Cleanup Crew
- Selective Attendance
- Objective Hangover
- Frontline Tolerance
- Vision Half-Life
- Aegis Lease
- Target Fixation
- Item Active Amnesia
- Spell Target Loyalty
- One More Minute
- Economy Volatility
- Farm Entitlement
- Tower Allergy
- Consumable Philosophy
- Action Entropy

Requirements: opportunity tables rather than match averages, hierarchical cohort baselines, side-correct state model, uncertainty propagation, ward entity matching, and feature provenance.

## Tier 3 — Heavy computation

Spatial models, longitudinal adjustment, interaction graphs, or high-dimensional state conditioning:

- Two Personalities
- Role Betrayal
- Old You vs New You
- Reactive Vision
- Resource Gravity
- Space Dividend
- Death Geography Déjà Vu
- Post-Death Personality
- Protector Instinct
- Executioner vs Setup
- Build Stubbornness
- Adaptation Speed
- Early Map Anxiety
- Recovery Style
- Comeback Catalyst
- Momentum Dependency
- Fight Participation Quality
- Aggressive Fighter, Conservative Map
- High-Ground Patience
- Roshan Discipline
- Deward Duel
- Vision Redundancy
- Ability Build Adaptation
- Facet Identity
- Neutral Item Adaptation

Requirements: map-version geometry, sequence/change-point models, interaction graphs, reliable role estimation, feature store partitioned by parser/patch, and large cohort infrastructure.

## Tier 4 — Research-grade

- Gold Fever: latent wallet/item-plan reconstruction and survival modeling.
- You Fixed It; It Moved: context-distribution transport with longitudinal causal adjustment.
- Duo Gravity: repeated-peer behavioral graph with selection-bias controls.
- Exact Lane Attachment after lane value changes: needs time-bucketed position telemetry absent from the stock endpoint.
- Exact fight entry/exit, hesitation, panic casts, chase distance, TP lateness, escape availability, and spell sequences: require a raw replay event/state extension, not cleverer use of this JSON.

## 9.1 Foundational engineering sequence

```text
Raw payload vault + checksum
→ schema/version profiler
→ normalized event/opportunity tables
→ item/hero/ability/map constants snapshots
→ kill-cluster and state reconstruction
→ feature provenance and coverage gates
→ cohort baseline service
→ insight detectors with calibration tests
→ evidence bundle API
→ story ranking and interactive renderer
```

The evidence bundle—not the prose—is the core product contract. Copy can evolve only if every claim remains traceable to fields, transformations, and representative matches.

---

# Part 10 — What I would actually build

## V1: 10 insights people remember

V1 optimizes for strong evidence, varied story shapes, and a balance of usefulness/shareability. It deliberately postpones the dazzling but fragile latent-wallet and longitudinal models.

| Order | V1 insight | Why it earns the slot |
| ---: | --- | --- |
| 1 | The Last Man Out | Highest personal resonance with a transparent death-order proof. |
| 2 | Win Fights, Lose Windows | Product-defining conversion insight; highly actionable. |
| 3 | Power-Spike Tourist | Exact purchases plus consequence windows produce a clear item story. |
| 4 | Reactive Vision | Distinctive spatial/temporal experience; especially strong for supports. |
| 5 | Chain-Feed Return | Easy to understand, behavior-first, and immediately coachable. |
| 6 | Lane Win, Map Loss | Separates lane skill from transition skill; useful across roles. |
| 7 | First Casualty Personality | Transparent single-match and multi-match evidence with role adjustment. |
| 8 | Buyback Conviction | Memorable second-life ledger; valuable even as a single-match observation. |
| 9 | Same Enemy Tax | Enemy relationship creates a natural, shareable coaching hook. |
| 10 | Farm Reset Reflex | Connects fights, farm, and conversion without pretending farm is bad. |

V1 should ship only 3–6 of these per user report. The other detectors remain silent when opportunity count or coverage fails.

## V2: 20 more insights that broaden the identity

1. Lead Poisoning
2. Role Betrayal
3. Delayed Seatbelt
4. Cleanup Crew
5. Death Geography Déjà Vu
6. Selective Attendance
7. Resource Gravity
8. Space Dividend
9. Objective Hangover
10. Frontline Tolerance
11. Vision Half-Life
12. Aegis Lease
13. Streak Cashout
14. Post-Death Personality
15. Target Fixation
16. Protector Instinct
17. Item Active Amnesia
18. Build Stubbornness
19. Recovery Style
20. One More Minute

V2 adds state, spatial, role, relationship, and death-value breadth. It also creates enough independent signals for a cautious latent-trait synthesis.

## Later: the ambitious analytical system

Build the research-grade ceiling once the event store, cohorts, and calibration corpus are mature:

- Two Personalities
- Gold Fever
- You Fixed It; It Moved
- Old You vs New You
- Duo Gravity and the full relationship constellation
- Contribution archetypes (Executioner vs Setup)
- state-conditioned Momentum Dependency and Comeback Catalyst
- full map/vision identity
- action/ability/facet longitudinal fingerprints
- raw-replay extensions for exact movement, fight entry/exit, cast sequence, cooldown/resource state, inventory snapshots, and teleport destinations

## 10.1 Product-owner rationale

The memorable product is not the one with the most detectors. It is the one that can reliably deliver this sequence:

1. One statement that feels painfully personal.
2. One interaction that proves it with the player's own games.
3. One consequence the player cares about.
4. One experiment they can try tonight.
5. One share card their stack understands instantly.

V1 creates that loop with relatively defensible endpoint signals. V2 broadens identity. The later system earns the right to make “how the hell did it know that?” claims by first building an unusually honest evidence and calibration foundation.

---

# Source and method notes

Primary technical references:

- [OpenDota API documentation](https://docs.opendota.com/)
- [OpenDota core](https://github.com/odota/core) and [match computation source](https://github.com/odota/core/blob/master/svc/util/compute.ts)
- [OpenDota response assembly and benchmark enrichment](https://github.com/odota/core/blob/master/svc/util/buildMatch.ts)
- [OpenDota parser](https://github.com/odota/parser), especially [`Parse.java`](https://github.com/odota/parser/blob/master/src/main/java/opendota/Parse.java) and [`CreateParsedDataBlob.java`](https://github.com/odota/parser/blob/master/src/main/java/opendota/CreateParsedDataBlob.java)
- [OpenDota schema tables](https://github.com/odota/core/blob/master/sql/create_tables.sql)
- [OpenDota/dotaconstants](https://github.com/odota/dotaconstants) for patch, mode, lobby, region, hero, ability, item, rune, and order mappings

Context and product references:

- [Dota2ProTracker match 8431600692](https://dota2protracker.com/matches/8431600692) for independent match/roster/result context before the single API request
- [Dotabuff TrueSight](https://www.dotabuff.com/pages/truesight) for the current detailed-match product baseline: builds, farm, vision, objectives, and combat logs
- [OpenDota core issue on parsed ranked-game acquisition](https://github.com/odota/core/issues/2840), which confirms `/parsedMatches` is normally used to find parsed IDs; this research intentionally did not spend an additional OpenDota call on it

The specimen audit is empirical: counts, field coverage, nested schemas, and examples come from the saved raw JSON. Field semantics and reconstruction caveats were checked against the open-source implementation. Product candidates are designs, not claims validated on a population; their thresholds and copy must be calibrated on a much larger, role/hero/bracket/patch-stratified corpus before launch.
