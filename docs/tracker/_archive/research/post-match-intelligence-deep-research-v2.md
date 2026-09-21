# Post-Match Intelligence — Deep Research & Validation V2

Status: RESEARCH + LIVE VALIDATION — non-normative product/engineering recommendation
Date: 2026-09-14
Repository base: `main` at `5d23eed`
Supersedes (for data capability claims): [Ten-Player Match Intelligence V1](ten-player-match-intelligence-v1.md); complements [Post-Match Intelligence Feasibility V1](post-match-intelligence-feasibility-v1.md)
Provider calls this phase: **STRATZ 122** (114 HTTP 200; 8 deliberate complexity-limit probes), OpenDota 0
Probe workspace (git-ignored): `.local/stratz-probe/deep-research-2026-09-14/` (`raw/`, `ledger.jsonl`, `schema_types.json`, analysis scripts)
Identifiers: none in this document. Other players' account IDs were never requested.

> **Corrections, 2026-09-15** (from [Deterministic Candidate Validation V1](../validation/post-match-deterministic-candidate-validation-v1.md)):
> 1. `inventoryReport` snapshots are **empty** (every item slot null) for current-patch matches — 0 of 7,780 player rows in a new 778-match pull; only 26% of rows in the older corpus had items. The "held ≥ 5 minutes" rule in §4.7 cannot be computed; held-at-end is determined from final inventory instead.
> 2. On 2026-09-15 STRATZ returned `playbackData: null` (no error) for **every** requested match, including a match that returned playback the previous day. Playback availability is not stable; every playback-dependent card must be optional.
> 3. "Bought, Never Activated" (§4.7) is far rarer than assumed: for active items still in the main inventory at match end and held ≥10 min (Standard) / ≥6 min (Turbo), only 0.5% / 1.2% were never activated, dominated by Mjollnir (passive value). It no longer qualifies as P0.

Nothing here changes the locked Role Metrics & Personal Baselines SSOT or the Match Lifecycle SSOT. Post-match intelligence is treated as a **separate layer** from progression metrics: many cards below are ephemeral match stories that should never enter a baseline.

---

## 1. Executive conclusion

**Post-match intelligence with STRATZ can be genuinely special.** Once all ten players are collected, the data supports statements a player cannot see from their own screen or the scoreboard:

- how their lane actually went **against the specific opponent** they laned with, minute by minute, including when a lead flipped;
- **who** killed them, **where**, and **how long** they spent dead — with buybacks accounted for;
- what the **enemy team did that they never saw**: stacks, observer wards, dewards, smoke uses, Roshan and Tormentor kills, item timings, farm pace;
- a **ward war** per team, including how many of the player's team's observers were destroyed;
- **who damaged whom** across the whole match, and who disabled the player most;
- **items bought but never activated**;
- **temporal sequences** between death clusters and objectives.

And, crucially, these become personal when compared with **the player's own history of matches and opponents** ("the most observers an enemy team has placed against you in your last 17 Turbo Support games").

### The breakthrough, in one paragraph

The earlier project assumption that other players were opaque was an artefact of which fields we queried. The STRATZ `stats` type is populated for all ten players and is **historically backfillable** (verified on matches a year old). Per-minute net worth for all ten players reconciles **exactly** with STRATZ's own team net-worth lead curve (median error 0 gold across 4,833 minute points), kill/death/assist events reconcile across player rows at 95.9%–99.2%, and the whole-match damage matrix is internally symmetric in 5,944 of 5,944 pairs. That is solid enough to build derived facts on. Replay playback adds timestamped ward lifecycles, gold by reason, item activations, Roshan timing, and damage events — but only for matches **up to ~90 days old**, one uncached match per request.

### What remains true

- **Causality is still unavailable.** Sequence ("after the fight, two towers fell within 94 seconds") is supportable; cause ("the fight cost you the towers") is not.
- **Visibility, intent, communication, movement, reaction time, and cooldown/mana state are not observable.**
- **Personal history is thinner than it looks.** In one real account's last 100 parsed matches, the largest bucket×role slice had 19 games and only 13 of 67 usable matches had ≥10 prior games in the same bucket and role. Enemy-team comparisons should therefore key on the **mode bucket**, not the user's role, whenever the metric does not depend on the user's role.
- **About 14% of recent matches were not parsed at query time; parse delay median ~28 minutes, p90 ~3.8 days.** The product must wait gracefully.

### Verdict by numbers

| Question | Answer |
|---|---|
| Can we show strong, non-scoreboard, enemy-aware cards for most parsed matches? | **Yes** |
| Is the core dataset historical and batchable? | **Yes** — 7 matches/request for core stats (complexity-bound), 4/request for heavy reports |
| Is replay-derived enrichment usable? | **Yes, recent only** — ≤90 days, 1 uncached match/request, 0.4–5.5 s |
| Can we reconstruct fights? | **As a validated heuristic** (time + space clustering of deaths), not as physical presence |
| Can we connect fights to objectives? | **As sequence facts**, with base rates disclosed internally (~2× control, but frequent by chance) |
| Can we say why the game was lost? | **No** |

---

## 2. Data capability map

### 2.1 How the data was mapped

1. **Schema:** recursive introspection of 172 types reachable from `DotaQuery`, `MatchType`, `MatchPlayerType`, `MatchPlayerStatsType`, `MatchPlaybackDataType`, `MatchPlayerPlaybackDataType`, and `ConstantQuery` (9 calls).
2. **External:** STRATZ API pages and community model repositories (no field semantics documented publicly), OpenDota parser behaviour (teamfight and objectives rules), Valve protobuf `DOTA_CHAT_MESSAGE` enum (to decode STRATZ `chatEvents.type`), community parser docs (ward lifetimes 6/7 min), Dota respawn mechanics.
3. **Live validation:** 131-match stratified corpus + one account's 100-match history + 7 full playback matches + 21 playback availability probes (§10).

### 2.2 Source A — batchable STRATZ match stats (historical)

Query shape: aliased `match(id:)` fields. Root `matches(ids:)` and `player.matches(request: {matchIds})` are **priced at a flat ~770k complexity** for this selection regardless of ID count, so they cannot carry it.

| Group | Key fields (all ten players unless noted) | Historical | Batch | Standard | Turbo | Enemy data | Reliability (validated) |
|---|---|---|---|---|---|---|---|
| Economy timelines | `networthPerMinute`, `lastHitsPerMinute`, `deniesPerMinute`, `experiencePerMinute`, `goldPerMinute`, `level` (level-up timestamps) | ✅ (1-year-old verified) | ✅ | ✅ | ✅ | ✅ | NW exact vs lead curve; XP cumsum ±43; CS sum = scalar in 57.5% (tail undercount, \|diff\|>5 in 11%) |
| Stacks | `campStack` cumulative per minute | ✅ | ✅ | ✅ | ✅ | ✅ | Monotone 100%; minute granularity |
| Deaths | `deathEvents {time, attacker, assist[], timeDead, positionX/Y, goldLost, goldFed, xpFed, byAbility, byItem, flags…}` | ✅ | ✅ | ✅ | ✅ | ✅ | attacker↔killer kill event 95.9%; `timeDead` = realized time dead (buyback-truncated) |
| Kills / assists | `killEvents {time, target, positionX/Y, gold, xp, assist[], isSmoke, isGank, isSolo…}`, `assistEvents {time, target, positionX/Y, gold, xp}` | ✅ | ✅ | ✅ | ✅ | ✅ | assist↔death 99.2% |
| Vision | `wards {time, type, positionX/Y}`, `wardDestruction {time, isWard, gold, experience}` | ✅ | ✅ | ✅ | ✅ | ✅ | counts = playback spawns 70/70; `isWard` = observer (303/309 correct) |
| Items | `itemPurchases {time, itemId}`, `itemUsed {itemId, count}` | ✅ | ✅ | ✅ | ✅ | ✅ | use counts = playback events 1,044/1,044 |
| Runes | `runes {time, rune, action PICKUP/BOTTLE, positionX/Y}` | ✅ | ✅ | ✅ | ✅ | ✅ | enum decoded; `gold` null |
| Objectives | match `towerDeaths {time, npcId, isRadiant, attacker}` (towers T1–T4, barracks, shrines, Ancient); per-player `towerDamageReport {npcId, damage, damageCreeps, damageFromAbility}` | ✅ | ✅ | ✅ | ✅ | ✅ | `isRadiant` = owner; attacker is a hero in 52% |
| Farm geography | `farmDistributionReport.creepLocation/neutralLocation/ancientLocation/creepType/buildings/other` | ✅ | ✅ | ✅ | ✅ | ✅ | `creepLocation.id` = `MapLocationEnums` index (verified); totals are a partial subset (~40% of GPM×min) — use shares |
| Roshan / Tormentor counts | `farmDistributionReport.other` id 133 (Roshan) and 861 (Tormentor) `count` per last-hitter | ✅ | ✅ | ✅ | ✅ | ✅ | Roshan counts = playback 13/13; Tormentor = chat 13/13; **no timestamp** |
| Courier kills | `courierKills {time, positionX/Y}` | ✅ | ✅ | sparse | none observed | ✅ | agrees with chat courier-lost in 47% — weak |
| Permanent buffs | `matchPlayerBuffEvent {time, abilityId, itemId, stackCount}` | ✅ | ✅ | ✅ | ✅ | ✅ | only permanent buffs (Shard, Scepter, Moon Shard, Duel) — not BKB |
| Match context | leads, kill arrays, lane outcomes, `pickBans`, first blood, bitmasks | ✅ | ✅ | ✅ | ✅ | n/a | first blood = chat exact |

### 2.3 Source B — batchable heavy reports (historical)

| Group | Key fields | Historical | Batch | Reliability |
|---|---|---|---|---|
| Damage matrix | `heroDamageReport.dealtTargets/receivedTargets {target, amount}`, `dealtSourceAbility/Item` | ✅ | 4/request | Σ dealtTargets = `heroDamage` (ratio 1.000); A→B = B←A 5,944/5,944 |
| Crowd control | `heroDamageReport.dealtTotal/receivedTotal {stunCount, stunDuration, disableDuration, slowDuration, allyHeal, selfHeal}` | ✅ | 4 | populated; **units unverified** (likely ms) — use ranks only |
| Casts on targets | `abilityCastReport {abilityId, count, targets {target, count, damage}}` | ✅ | 4 | targets are hero IDs (17,211 target rows) |
| Actions | `actionReport {glyphCast, scanUsed, pingUsed, …}` | ✅ | 4 | equals chat glyph count in 69% of matches; sampled mismatches differ by 1 |
| Inventory by minute | `inventoryReport` (≈ one snapshot per minute; items, backpack, neutral) | ✅ | 4 | length ≈ minutes+2; Aegis visibility is patch-dependent (§9) |
| Game-event chat | match `chatEvents {time, type, fromHeroId, toHeroId, value, isRadiant}` | ✅ | 4 | **subset of Valve's enum**: Tormentor kill (117) exact; glyph (12); first blood (5); courier lost (10); tower kill/deny (3/4); aegis stolen/denied (53/51); abandon/disconnect. **No** Roshan kill (9), Aegis pickup (8), buyback (7), ward kill (105/106), smoke (126) |
| Dead / unclear | `locationReport` (no timestamps, irregular cadence), `laneReport` (undocumented small creep counts), `towerStatus` (empty), `farmDistributionReport.buyBackGold` (always 0), `bountyGold` (0) | — | — | Do not use |

### 2.4 Source C — STRATZ replay playback (recent only)

| Property | Measured |
|---|---|
| Availability window | Present at 0.6, 1.5, 2.6, 5.2, 7.0, 9.0, 12, 15, 20, 26, 39, 45, 52, 60, 75, 90 days; **null at 120, 150, 200, 270, 360 days** |
| Batching | 1 **uncached** match per request (error otherwise); a batch of 3 already-cached matches succeeded |
| Latency | light selection 0.4–3.1 s first request; 0.31 s when repeated (cached) |
| Payload | light (ward lifecycle + gold events + item uses + buybacks): 90–385 KB; full minus 1-second tick streams: 4.0–9.4 MB for 54–80 min Standard; 1-second gold/health ticks add MBs |
| Standard / Turbo | Both |

| Stream | Content | Verified use | Reliability |
|---|---|---|---|
| Match `wardEvents` | spawn/despawn per ward, `fromPlayer`, `playerDestroyed`, coordinates | exact ward lifetimes and dewarder | Observers natural 360 s, sentries 420 s; dewarded observers median 82 s |
| Player `goldEvents` | time, amount, `reason` (CREEPS, NEUTRAL, HEROES, STRUCTURES, ROSHAN, BOUNTY, WARD_DESTRUCTION, DEATH, …) | Roshan timing; income mix over time | `ROSHAN` also fires for **Tormentor** kills; farm-report totals are a subset of reason totals |
| Player `csEvents` | each last hit: `npcId`, map coordinates, `mapLocation`, neutral/ancient flags | lane verification; Roshan last-hitter (npc 133); Tormentor (npc 861) | early last-hit lane agrees with STRATZ `lane` for 42/42 cores |
| Player `itemUsedEvents` | time, item, target | activation timing (BKB, Blink, Smoke, TP) | counts equal stats `itemUsed` 1,044/1,044 |
| Player `buyBackEvents` | time | buyback timestamps | `cost` and `deathTimeRemaining` always 0 — ignore those fields |
| Player `heroDamageEvents` | time, attacker, target, value, illusion flags | damage evidence of fight involvement | adds 12% more involved heroes than kill/assist/death credit |
| Player `abilityUsedEvents`, `healEvents`, `experienceEvents` (reason), `streakEvents`, `purchaseEvents` | timestamps | experimental | not needed for V1 |
| Match `buildingEvents`, `roshanEvents`, `courierEvents` | — | **empty in 19/19 matches** | Unusable |
| `playerUpdatePositionEvents` | movement | not requested | Prohibited surface; huge |

### 2.5 Source D — STRATZ constants

`constants { npcs, items, abilities, heroes }` (one ~310 KB call per patch) maps IDs: Roshan `npc_dota_roshan` = 133, Tormentor `npc_dota_miniboss` = 861, towers 16–37, barracks 38–49, Ancients 50–51, observer/sentry ward units 110/111, lotus pool 888, watchtower 822.

### 2.6 Source E — OpenDota (comparison / fallback)

OpenDota parsed matches expose `obs_log`/`obs_left_log` (with attacker), `camps_stacked`, parser `teamfights` (≥3 deaths, 15-second windows), `objectives` (building kills with unit, Roshan kill, Aegis), `life_state_dead`, `buyback_log`, `runes_log`. The repository's own evidence shows **only 19 of 1,200 sampled pub matches were parsed** unless a parse is requested, and parse requests depend on replay availability. Use it only as a semantic cross-reference, not as a production source.

### 2.7 Coverage and freshness

| Measure | Value |
|---|---|
| Recent matches (6 accounts, last 40 each) parsed at query time | 85.8% |
| Parse delay after match end | p10 348 s · median 1,672 s · p90 327,871 s |
| Corpus matches with no stats at all | 11 of 131 (7 unparsed Turbo, 1 unparsed Standard, 3 flagged parsed but stats null) |
| Parsed-row field presence | NW/CS/stacks/level/purchases/itemUsed/farm 100%; deaths 97–99%; wards 64–68% of player rows (non-warders); tower damage report 84–87% |
| Positions | exactly one of each position per team in 100% of parsed matches |

---

## 3. Insight capability matrix

Evidence levels: **A** RAW FACT · **B** DERIVED FACT · **C** VALIDATED HEURISTIC · **D** UNSUPPORTED INFERENCE.
Historical = works from backfillable stats. Playback = needs Source C (≤90 days).
Ship: **P0**, **P1**, **P2**, **EXP** (experimental), **NO**.

### 3.1 Lane

| Insight | Example user copy | Ev. | Required signals | Enemy? | Hist.? | Playback? | Role-specific | Confidence | Ship |
|---|---|---|---|---|---|---|---|---|---|
| Lane counterpart net-worth path | "At 5:00 you were +380 on Anti-Mage. By 10:00 you were −1,120." | B | own + counterpart `networthPerMinute`, `position` | ✅ | ✅ | — | cores (supports P2) | High | **P0** |
| CS vs NW decomposition vs counterpart | "You were 16 CS behind Lone Druid at 10:00 but 2,506 net worth ahead." | B | `lastHitsPerMinute`, `networthPerMinute`, kill/assist `gold` | ✅ | ✅ | — | cores | High | **P0** |
| Opposing counterpart unusually strong start | "Their Anti-Mage had 68 CS at 10:00 — the most any opposing carry has had against you in your last 11 Turbo Offlane games." | B + history | counterpart CS@10 history | ✅ | ✅ | — | cores | High (needs ≥10 prior) | **P0** |
| Lead flip minute | "You led your lane until 7:00; from 8:00 on you were behind." | B | per-minute NW diff | ✅ | ✅ | — | cores | High (minute granularity) | P1 |
| Level-6 race | "Their Mid hit level 6 at 5:40; you at 7:10." | B | `level` timestamps | ✅ | ✅ | — | mid/offlane | High | P1 |
| Lane geography of farm | "Most of your creep gold came from the bottom lane." | B | `creepLocation` shares | — | ✅ | — | cores | Medium (whole match) | P2 |
| Support duo lane NW | "Your lane supports finished 10:00 900 net worth behind theirs." | B | pos4/5 NW | ✅ | ✅ | — | support | Medium (pairing 94%) | P2 |
| STRATZ lane outcome label | "STRATZ scored your lane as a loss." | A (provider label) | `*LaneOutcome` | — | ✅ | — | all | Opaque method | P2 |

### 3.2 Economy and resource distribution

| Insight | Example user copy | Ev. | Required signals | Enemy? | Hist.? | Playback? | Role | Confidence | Ship |
|---|---|---|---|---|---|---|---|---|---|
| Enemy stacking vs yours | "Their team stacked 9 camps by 20:00. Yours stacked 1." | B | `campStack` @~20 min | ✅ | ✅ | — | all | High (minute granularity) | **P0** |
| Enemy stacking vs your history | "The most stacking an enemy team has done against you in your last 30 Standard games." | B + history | same | ✅ | ✅ | — | bucket comparator | High | **P0** |
| Enemy core pace to 10k/15k | "Their Faceless Void reached 10k net worth at 14:00 — the fastest enemy hero in your last 20 Standard games." | B + history | `networthPerMinute` | ✅ | ✅ | — | all | High | P1 |
| Economy concentration | "Their Medusa held 41% of their team's net worth at 25:00." | B | team NW shares | ✅ | ✅ | — | all | High | P1 |
| Enemy core jungle/ancient share | "58% of their carry's creep gold came from neutral and ancient camps." | B | `creepLocation`/`neutralLocation`/`ancientLocation` shares | ✅ | ✅ | — | all | Medium (partial totals) | P1 |
| Stacks → specific farmer | "Their Void farmed the camps their supports stacked." | D | no link between stack and later farm | — | — | — | — | — | **NO** |
| Gold lost to deaths | "Your deaths cost 2,340 gold." | A/B | `goldLost` | — | ✅ | — | all | Medium | P2 |
| Gold fed to enemy | "Your deaths gave the enemy 4,100 gold." | B | `goldFed` | — | ✅ | — | all | Unverified semantics | EXP |
| Income mix over time | "From 20:00 to 30:00 their carry earned 62% of their gold from neutrals." | B | playback `goldEvents` | ✅ | — | ✅ | all | High | P2 |
| Comeback size record | "Your team came back from 11.4k down — the largest deficit you've won from in 40 Standard games." | B + history | lead curve | — | ✅ | — | all | High | P1 |

### 3.3 Deaths and hero interactions

| Insight | Example user copy | Ev. | Required signals | Enemy? | Hist.? | Playback? | Role | Confidence | Ship |
|---|---|---|---|---|---|---|---|---|---|
| Time dead + record | "You spent 8:52 dead — 16% of the game, your longest in 16 Turbo Support games." | B + history | `timeDead` | — | ✅ | — | all | High | **P0** |
| Primary nemesis | "Pudge was on 6 of your 8 deaths. No other hero was on more than 3." | B (gated) | `attacker`, `assist` | ✅ | ✅ | — | all | High fact; low surprise unless gated | P1 |
| Quick re-deaths | "Three times you died again within 45 seconds of respawning." | B | death times + `timeDead` | — | ✅ | — | all | High | P1 |
| Where you died | "5 of your 7 deaths were on the Dire half of the map." | C | death positions + coordinate classifier | — | ✅ | — | all | Validated heuristic (94% cell purity) | P1 |
| Deaths near enemy observers (recent) | "4 of your 6 deaths happened within range of an enemy Observer Ward that was still standing." | B | death positions + playback ward lifecycle | ✅ | — | ✅ | all | High for proximity, not for vision | P1 |
| Deaths near enemy observers (historical) | same, older games | C | STRATZ `isWardWalkThrough` (77% corroborated) | ✅ | ✅ | — | all | Medium | EXP |
| Buybacks | "You bought back twice; your team bought back 5 times." | A (recent) / C (historical) | playback `buyBackEvents` / `timeDead` ratio rule | ✅ | ✅ (heuristic) | recent exact | all | Exact / 90% recall, 2.8% false flags | P1 |
| Who damaged you most | "Their Sniper dealt 31% of the hero damage you took." | B | `heroDamageReport.receivedTargets` | ✅ | ✅ | — | all | High | P1 |
| Most disabled | "You spent longer disabled than anyone else in the match." | B (rank only) | `receivedTotal.stunDuration/disableDuration` | ✅ | ✅ | — | all | Units unverified → ranks only | P1 |
| Spell focus | "Lion cast Finger of Death on you 4 times." | B | `abilityCastReport.targets` | ✅ | ✅ | — | all | High | P2 |
| Burst deaths | "3 of your deaths came from more than 60% of the damage landing in the last 2 seconds." | C | playback damage events | ✅ | — | ✅ | all | Needs HP context | EXP |
| "You died because you had no vision" | — | D | visibility unobservable | — | — | — | — | — | **NO** |

### 3.4 Vision war

| Insight | Example user copy | Ev. | Required signals | Enemy? | Hist.? | Playback? | Role | Confidence | Ship |
|---|---|---|---|---|---|---|---|---|---|
| Ward war totals | "They placed 26 observers. They destroyed 9 of your team's 21." | B | `wards.type`, `wardDestruction.isWard` | ✅ | ✅ | — | all | High | **P0** |
| Ward war vs history | "The most observers an enemy team has placed against you in your last 17 Turbo Support games." | B + history | same | ✅ | ✅ | — | bucket comparator | High | **P0** |
| Your wards' fate | "5 of your 8 observers were destroyed; 3 lasted under a minute." | B | playback `wardEvents` | ✅ | — | ✅ | support | High | P1 |
| Enemy ward placement regions | "11 of their 26 observers were placed on your side of the river." | C | ward coordinates + classifier | ✅ | ✅ | — | all | Medium-high | P1 |
| Observer uptime per team (exact) | "Their observers were up for 81% of the game; yours 43%." | B | playback lifecycle | ✅ | — | ✅ | all | High | P2 |
| Observer uptime (historical) | same | C (upper bound) | placements × 360 s | ✅ | ✅ | — | all | Overstates | EXP |
| Stats-only "which ward was killed" | — | D | 26% matching accuracy | — | — | — | — | — | **NO** |
| "They could see you" | — | D | visibility unobservable | — | — | — | — | — | **NO** |

### 3.5 Fights, objectives, tempo

| Insight | Example user copy | Ev. | Required signals | Enemy? | Hist.? | Playback? | Role | Confidence | Ship |
|---|---|---|---|---|---|---|---|---|---|
| Swing window | "The game turned between 18:00 and 26:00: from +4.2k to −7.9k." | B | lead curve | ✅ | ✅ | — | all | High | **P0** |
| Skirmish record | "12 clashes with 3+ deaths; your team lost 8 of them on kills." | C | death clusters (20 s, 30 units) | ✅ | ✅ | — | all | Validated heuristic | P1 |
| Clash → structures sequence | "After the 27:30 clash, Dire took two towers within 94 seconds." | B (sequence) | clusters + `towerDeaths` | ✅ | ✅ | — | all | High as sequence | P1 |
| Towers lost while you were dead | "Your team lost 4 towers while you were dead." | B | `timeDead` windows + `towerDeaths` | ✅ | ✅ | — | all | High | P1 |
| Tower race | "They took 6 towers before your team's first at 19:10." | B | `towerDeaths` | ✅ | ✅ | — | all | High | P1 |
| Barracks | "Your first barracks fell at 31:20; theirs never fell." | A | `towerDeaths` (rax npcIds) | ✅ | ✅ | — | all | High | P2 |
| Roshan count + last hitters | "They killed Roshan 3 times; your team once." | B | `farmDistributionReport.other[133]` | ✅ | ✅ | — | all | High (13/13) | P1 |
| Roshan timing | "Roshan fell at 24:10 and 35:40, both to Dire." | B | playback `goldEvents` ROSHAN minus Tormentor times, `csEvents` npc 133 | ✅ | — | ✅ | all | High | P1 |
| Tormentor | "Their Earthshaker killed a Tormentor at 39:30." | A | `chatEvents` type 117 | ✅ | ✅ | — | all | High | P2 |
| Smoke use | "They used Smoke 7 times; 5 were followed by a kill within a minute." | B | playback `itemUsedEvents` + kills | ✅ | counts ✅ / timing ❌ | timing ✅ | all | High | P1 |
| Glyph use | "They used Glyph 10 times." | A | `actionReport.glyphCast` | ✅ | ✅ | — | all | Medium | P2 |
| Lead not converted | "Your team led by 8k at 25:00 and took one tower in the next 5 minutes." | B | lead curve + towers | ✅ | ✅ | — | all | High | P2 |
| Who died first in lost clashes | "You were the first death in 3 of your team's 5 lost clashes." | C | clusters | ✅ | ✅ | — | all | Heuristic + blame risk | EXP |
| Physical presence in a fight | "You were in 9 of 12 fights." | C (damage) / D (credit only) | playback damage events | ✅ | — | ✅ | all | Partial | EXP |
| "Losing the fight cost you the towers" | — | D | causal | — | — | — | — | — | **NO** |

### 3.6 Items

| Insight | Example user copy | Ev. | Required signals | Enemy? | Hist.? | Playback? | Role | Confidence | Ship |
|---|---|---|---|---|---|---|---|---|---|
| Bought, never activated | "You bought Force Staff at 21:10 and never used it." | B | `itemPurchases` + `itemUsed` + item behaviour constants | — | ✅ | — | all | High (use counts exact) | **P0** |
| Enemy key item earlier than usual | "Their Void's BKB came at 17:40 — earlier than any enemy BKB in your last 20 Standard games." | B + history | `itemPurchases` | ✅ | ✅ | — | all | High | P1 |
| Counterpart item gap | "Their Mid finished Blink 3:40 before your Blink." | B | purchases | ✅ | ✅ | — | cores | High | P1 |
| Activation timing | "Their Sven used BKB 5 times; the first at 18:05." | A | playback `itemUsedEvents` | ✅ | counts ✅ | timing ✅ | all | High | P2 |
| Items held by minute | "You carried a Gem for 12 minutes." | B | `inventoryReport` | — | ✅ | — | all | Medium | P2 |
| "Didn't use BKB before dying" | — | D (cooldown/mana/stun unknown) | — | — | — | — | — | — | **NO** |
| Counter-item intent | "They built Silver Edge to counter you." | D | intent | — | — | — | — | — | **NO** |

---

## 4. Top-tier post-match insight catalog

Conventions for every card:

- **Bucket** = Standard (All Pick ranked/unranked) or Turbo; never mixed.
- **Effective role** = upstream role (SSOT); counterpart mapping uses provider positions of both players.
- **History gate**: record/rarity wording requires the comparator sample in the card ("in your last 12 …"). Minimums in §4.13.
- **Copy principle**: fact first, number second, comparator third; no "because", "cost you", "outplayed", "should have".

### 4.1 Lane Counterpart Path — P0

**Question it answers:** "Did I actually win my lane — against the person I laned with?"

**Examples**
- "At 5:00 you were +380 on their Anti-Mage. By 10:00 you were −1,120."
- "You were behind Storm Spirit by 640 at 5:00 and ahead by 910 at 10:00."
- "You finished 10:00 dead even with their Carry (±80)."

**Algorithm**
1. Counterpart: Carry (P1) ↔ enemy P3, Mid (P2) ↔ enemy P2, Offlane (P3) ↔ enemy P1; Supports P4 ↔ P5 (P2 tier). Require the two players' STRATZ `lane` values to map to the same map lane (`SAFE_LANE` Radiant = bottom, Dire = top; `OFF_LANE` inverse; `MID_LANE` = mid). Measured agreement: cores 98–99%, supports 94%.
2. `diff[t] = own.networthPerMinute[t] − opp.networthPerMinute[t]`, t in minutes (index t = t:00; verified by exact reconciliation with `radiantNetworthLeads[t+1]`).
3. Report t = 5 and 10 (Turbo: 3 and 6 as additional checkpoints if desired).
4. Flip: first minute in [3, 12] with diff ≥ +300 and first with diff ≤ −300; if both exist, the later one is the flip.

**Data:** `players.position`, `players.lane`, `players.isRadiant`, `stats.networthPerMinute`.

**Historical comparator:** own lane diff@10 distribution in bucket + role: "You usually finish lane +240 against opposing Mids. This game you were −1,080." Requires ≥10 prior.

**Eligibility:** both players parsed; lanes map to the same map lane; duration ≥ 10:00 (Turbo ≥ 6:00 for the early checkpoint).

**Evidence:** DERIVED FACT. Distribution (Standard, n=157–158): Carry vs enemy Offlane @10 median +154, p10 −1,458, p90 +1,668; Mid @10 p10/p90 ±1,558. A flip occurred in 26% of Mid lanes and 18% of Carry/Offlane lanes.

**Failure modes:** lane swaps or trilanes (lane mismatch → suppress); roaming P4 with `OFF_LANE` label; kill gold from rotations counts as "lane"; minute granularity.

**Copy restrictions:** never "won/lost the lane" without the numbers; never "outfarmed" (net worth ≠ farm); never "outplayed".

### 4.2 CS-vs-Net-Worth Split — P0

**Question:** "My net worth looked fine — was I actually farming?"

**Examples**
- "You were 16 CS behind Lone Druid at 10:00 but 2,506 net worth ahead." *(real corpus match)*
- "Even net worth at 10:00, but their Carry had 24 more last hits."
- "You out-farmed their Mid by 11 CS; they were still 600 ahead after 2 kills."

**Algorithm:** `cs10 = Σ lastHitsPerMinute[0..9]` for both; `nw10` as above; kill/assist gold before 10:00 from `killEvents.gold` + `assistEvents.gold` (use as a relative indicator; kill-event gold sums to ~73% of the playback HEROES total). Show when `|cs_diff| ≥ 10` and `sign(cs_diff) ≠ sign(nw_diff)` with `|nw_diff| ≥ 500` (Standard; Turbo thresholds from bucket distribution).

**Data:** `stats.lastHitsPerMinute`, `stats.networthPerMinute`, `stats.killEvents.gold`, `stats.assistEvents.gold`.

**Comparator:** none needed (intra-match contrast is the insight).

**Evidence:** DERIVED FACT. CS checkpoint sums are reliable (the undercount is at the match tail, not at 10:00).

**Failure modes:** denies not counted in CS; Alchemist/Hand of Midas/Track gold; neutral last hits inside lane phase.

**Copy restrictions:** do not attribute the gap to "kills instead of farming" unless kill gold before 10:00 is shown as a number.

### 4.3 Extreme Opponent Start — P0

**Question:** "Was my opponent unusually strong, or did I play badly?"

**Examples**
- "Their Anti-Mage had 68 CS at 10:00 — the most any opposing Carry has had against you in your last 11 Turbo Offlane games (usual: 26)." *(real history pattern: 68 vs prior median 26, 11 prior)*
- "Their Mid reached level 6 at 4:52, earlier than any Mid you've faced in 15 Standard games."

**Algorithm:** counterpart metric (CS@10, NW@10, level-6 time) this match; compare with the same metric for the counterparts in the user's previous matches in the same bucket + effective role. Fire only if strictly above all prior (record) or above the prior 90th percentile with ≥20 prior.

**Data:** as §4.1/§4.2; history store of *opponent* facts, no opponent identity.

**Minimum sample:** record ≥10 prior; percentile ≥20 prior.

**Evidence:** DERIVED FACT + personal history.

**Failure modes:** hero confounding (Anti-Mage and Alchemist farm faster by design) — show hero; Turbo heavy tails (Turbo P1 CS@10 p90 84 vs Standard 60).

**Copy restrictions:** "unusually strong start" is fine; "you couldn't handle" is not.

### 4.4 Time Dead — P0

**Question:** "How much of this game did I actually play?"

**Examples**
- "You spent 8:52 dead — 16% of the game."
- "Your longest time dead in your last 16 Turbo Support games: 8:52 (usual 3:58)." *(real history pattern: 532 s vs prior median 237.5 s)*
- "Three times you died again within 45 seconds of respawning."

**Algorithm:** `dead_s = Σ deathEvents.timeDead`; `dead_share = dead_s / durationSeconds`; quick re-death = `death[i+1].time − (death[i].time + death[i].timeDead) ≤ 45`.

**Data:** `stats.deathEvents {time, timeDead}`.

**Semantics verified:** `timeDead` is the **realized** time dead: for 73 playback-confirmed buybacks, `timeDead` equals buyback time − death time (73/73 within 2 s); later deaths never overlap an earlier `timeDead` window (45 exceptions in 9,864 pairs). Median `timeDead` rises from 21 s (0–10 min) to 98 s (50–60 min) in Standard.

**Comparator:** bucket + role; population context: median player dead share 15.4% Standard, 15.9% Turbo; p90 ~26%.

**Eligibility:** parsed; ≥1 death.

**Failure modes:** Aegis/reincarnation deaths have short `timeDead` (correctly short); disconnect time is not death time.

**Copy restrictions:** never "you wasted", "too aggressive", or reasons.

### 4.5 Enemy Stacking — P0

**Question:** "Did the other team do jungle work I never saw?"

**Examples**
- "Their team stacked 9 camps by 20:00. Yours stacked 1."
- "The most stacking an enemy team has done against you in your last 30 Standard games."
- "Both teams stacked 2 camps by 20:00." *(not shown — not surprising)*

**Algorithm:** per team, `Σ campStack[19]` (cumulative at the 20th minute sample; exact labelled checkpoint pending the SSOT time-aligned adapter). Fire on: enemy ≥ 5 and enemy − own ≥ 4 (Standard; Turbo ≥3 and ≥2), or record vs history.

**Data:** `stats.campStack` for all ten players.

**Comparator:** **bucket only** (enemy stacking does not depend on the user's role). Population: team stacks by 20:00 Standard median 2, p90 6, max 21; Turbo median 1, p90 3.

**Evidence:** DERIVED FACT.

**Failure modes:** games shorter than 20:00 (suppress); stacks after 20:00 excluded by design; which hero farmed the stacks is unknown.

**Copy restrictions:** never "their stacks won them the game"; never "your supports didn't stack" (teammate blame) — use team totals only.

### 4.6 Ward War — P0

**Question:** "What was happening in the vision game?"

**Examples**
- "They placed 26 Observer Wards. They destroyed 9 of your team's 21."
- "Your team destroyed 12 of their 15 observers."
- "The most observers an enemy team has placed against you in your last 17 Turbo Support games (usual: 9)." *(real history pattern: 15 vs prior median 9)*

**Algorithm:** per team: observers placed = count `wards.type == 0`; observers destroyed = count `wardDestruction.isWard == true` credited to the other team's players. Fire when either side's count is ≥ bucket p90 (Standard observers p90 31, observer kills p90 10; Turbo 19 and 7) or the ratio is ≥ 2:1 with ≥ 8 observers on the larger side, or history record.

**Data:** `stats.wards`, `stats.wardDestruction`.

**Semantics verified:** stats ward counts equal playback spawns 70/70; `isWard` true ↔ destroyed Observer (112/114), false ↔ Sentry (191/195).

**Comparator:** bucket only.

**Recent enrichment (playback):** exact lifetimes, "3 lasted under a minute", dewarder hero.

**Failure modes:** winning teams ward more (restates the result) — pair with the swing window rather than presenting as explanation; ward dispenser counts once per placement (fine).

**Copy restrictions:** never "they had map control", "they saw your rotations".

### 4.7 Bought, Never Activated — P0

**Question:** "Did I actually use the item I bought?"

**Examples**
- "You bought Force Staff at 21:10 and never used it."
- "Your Glimmer Cape was never activated."
- "Their Faceless Void activated BKB 4 times." *(enemy variant, P2)*

**Algorithm:** for items purchased (`itemPurchases`) that are active items (constants `item.stat.behavior` has an active flag; allow-list curated: BKB, Blink, Force Staff, Glimmer, Lotus, Satanic, Manta, Eul's, Ghost, Shivas, Pipe, Crimson, Solar Crest, Mekansm/Guardian, Silver Edge, Nullifier, Orchid/Bloodthorn, Hex, Abyssal, Refresher, Arcane Boots, Phase Boots, Mask of Madness, Mjollnir…), with the item held ≥ 5 minutes (`inventoryReport`), and `itemUsed.count == 0`.

**Data:** `stats.itemPurchases`, `stats.itemUsed`, B-report `inventoryReport`, constants.

**Semantics verified:** stats `itemUsed` counts equal playback activation events for 1,044/1,044 player-item pairs. In the playback sample: BKB bought 29 / used 29, Blink 34/33, Force Staff 14/8, Satanic 8/7, Sphere 1/0.

**Comparator:** optional: "the second game in a row" (session).

**Failure modes:** passive-value items bought for stats (Sphere, Satanic partially); items sold/disassembled; items bought in the last minutes.

**Copy restrictions:** never "you should have used it"; only "never activated" and the purchase time.

### 4.8 The Swing Window — P0 (carried from V1)

**Examples:** "The game turned between 18:00 and 26:00: your team went from +4.2k to −7.9k and lost 4 towers."

**Algorithm:** oriented lead curve; largest adverse or favourable change in an 8-minute window; objectives inside the window from `towerDeaths` (+ Roshan/Tormentor when available).

**Evidence:** DERIVED FACT. Unchanged from V1; now enriched with objectives and clashes.

### 4.9 Who Kept Finding You — P1

**Examples**
- "Pudge was on 6 of your 8 deaths. No other hero was on more than 3."
- "Their Spirit Breaker was on 5 of your 6 deaths before 20:00."

**Algorithm:** involvement per enemy hero = deaths where hero is `attacker` or in `assist`. **Gate:** top ≥ 5 deaths, top share ≥ 60%, and top − second ≥ 3.

**Why gated:** in the corpus the most-involved enemy is on a **median 78%** (p90 92%) of a player's deaths (players with ≥5 deaths). "X was on most of your deaths" is the norm, not a discovery. Only a clear gap between first and second is surprising.

**Evidence:** DERIVED FACT (attacker↔kill 95.9%, assist↔assist 99.2%).

**Copy restrictions:** never "focused", "hunted", "targeted" (intent).

### 4.10 Enemy Objective Sequences — P1

**Examples**
- "After the 27:30 clash, Dire took two towers within 94 seconds."
- "Your team lost 4 towers while you were dead."
- "They killed Roshan 3 times; your team once."

**Algorithms**
- Clash: deaths of both teams sorted by time; join to the current clash if ≤ 20 s after the previous death **and** within 30 grid units of the clash centroid; keep clashes with ≥ 3 deaths. (Time-only chaining merged spatially separate skirmishes in 30% of clusters; the spatial rule reduces that to ~1%.)
- Sequence: structures owned by the clash's losing side (more deaths) falling within 90 s after the last death.
- Dead-time objectives: `towerDeaths` with `isRadiant == own side` inside `[death.time, death.time + timeDead]`.
- Roshan count: `farmDistributionReport.other` entries with id 133, summed `count` per team (equals playback Roshan kills 13/13). Timing only with playback (`goldEvents.reason == ROSHAN` excluding Tormentor chat times).

**Base rate (why sequence ≠ cause):** a losing side lost a structure within 90 s after 43% of clashes versus 22% in a same-length window 5 minutes earlier (595 vs 306 of 1,377 clashes; even clashes count as non-conversions). The link is real enough to be interesting and common enough that it must never be framed as consequence.

**Evidence:** clash = VALIDATED HEURISTIC; sequence/dead-time/Roshan counts = DERIVED FACT.

**Copy restrictions:** "after", "within", "while" — never "because", "cost", "led to", "punished".

### 4.11 Damage and Control Received — P1

**Examples**
- "Their Sniper dealt 31% of the hero damage you took."
- "You were disabled longer than anyone else in the match."
- "Lion cast Finger of Death on you 4 times."

**Algorithm:** `receivedTargets` shares; disable rank from `receivedTotal.stunDuration + disableDuration` across ten players; casts from `abilityCastReport.targets` where target = user hero.

**Semantics verified:** Σ dealtTargets = heroDamage scalar; pairwise symmetry 5,944/5,944. Duration **units unverified** → rank and relative only.

**Evidence:** DERIVED FACT.

### 4.12 Enemy Item Timing — P1

**Examples**
- "Their Faceless Void finished BKB at 17:40 — earlier than any enemy BKB in your last 20 Standard games (usual first enemy BKB: 30:30)."
- "Their Mid had Blink 3:40 before you did."

**Algorithm:** earliest purchase time of a curated key-item list by any enemy (bucket comparator) or by the lane counterpart (role comparator). Population first team BKB: Standard median 30:30 (p10 23:10, p90 42:10); Turbo median 15:14.

**Evidence:** DERIVED FACT. Purchase ≠ assembled usage; use "finished" only for items without components that can be bought whole in a single purchase event, otherwise "bought".

**Copy restrictions:** no "counter-built", "rushed" (intent).

### 4.13 Minimum sample and comparator rules

| Claim form | Comparator | Minimum |
|---|---|---|
| Intra-match fact (no history) | none | eligibility only |
| "Most/least in your last N …" | same bucket (+ effective role when the metric depends on the user's role) | N ≥ 10 prior |
| "Above your usual" (median shown) | same | N ≥ 10 prior and effect ≥ metric MMD |
| Percentile / "top 10%" | same | N ≥ 20 prior |
| Hero-conditioned | bucket + role + hero | N ≥ 10 prior |
| Enemy-team metrics (stacks, wards, dewards, smoke, fastest to 10k, first BKB) | **bucket only** | N ≥ 10 prior |
| Counterpart metrics | bucket + role | N ≥ 10 prior |

Measured constraint: one active account's last 100 parsed matches yielded 67 role-labelled matches; the largest bucket×role slice was 19; **13 of 67** matches had ≥10 prior same bucket+role games. For enemy-team cards, a bucket-only comparator raises eligible matches in that history from 13 to 47 of 67.

---

## 5. Enemy Intelligence

The best insights **uniquely** enabled by enemy data, ranked by how rarely a player perceives them in-game:

| Rank | Enemy insight | Why it changes how the player reads their own match | Data | Tier |
|---:|---|---|---|---|
| 1 | Lane counterpart path and CS/NW split | Separates "I farmed badly" from "my opponent had an extreme lane" | NW/CS per minute, positions, lanes | P0 |
| 2 | Enemy stacking vs yours | Invisible jungle work that explains a sudden enemy farm jump | `campStack` | P0 |
| 3 | Ward war and your observers destroyed | The player sees their wards vanish but not the count or the other side's placements | wards, wardDestruction | P0 |
| 4 | Extreme opponent start vs your history | Context: this was the strongest opposing start you've faced | history | P0 |
| 5 | Who kept finding you (gated) | Names the repeated threat across deaths | death attackers/assists | P1 |
| 6 | Enemy Roshan / Tormentor | Roshan kills are often unseen by the other team; counts historical, times recent | farm `other`, playback gold reasons, chat 117 | P1 |
| 7 | Enemy smoke uses followed by kills | Smoke is invisible by design; 60% of smokes were followed by a kill within 60 s | playback item uses | P1 (recent) |
| 8 | Enemy core pace / economy concentration | Explains why fights became unwinnable without claiming it | NW per minute | P1 |
| 9 | Enemy key item timing vs your usual opponents | Rare early spikes | purchases | P1 |
| 10 | Who damaged/disabled you | Names the hero behind the pain | damage report | P1 |
| 11 | Enemy jungle/ancient farm share | Where their gold came from | farm report shares | P1 |
| 12 | Where they placed wards | Spatial pattern | ward coordinates + classifier | P1 |
| 13 | Enemy glyph use | Tempo detail | actionReport | P2 |

Every enemy card must answer "why is this about my match?" — the lane counterpart, the enemy team the user faced, the user's deaths, the user's wards. A card that is only "their Sniper had 900 GPM" does not ship.

---

## 6. Match Story Synthesis

### 6.1 Is multi-event narrative supportable?

Yes, if every sentence is an already-validated atom and the connectors are **temporal, not causal**. Allowed connectors: "then", "by", "over the next N minutes", "after", "while", "at the same time". Forbidden: "because", "so", "which led to", "cost", "allowed", "punished".

### 6.2 Story grammar

```text
[Lane beat]      counterpart diff at 5 and 10 (+ flip) or CS/NW split
[Invisible beat] one enemy-side fact from the same window (stacks, ward war, enemy pace, smoke)
[Turn beat]      swing window with structures/Roshan inside it
[Personal beat]  time dead / nemesis / item never used — or a record vs history
```

Rules: at most 4 beats; every beat must individually pass its card gate; beats must be in chronological order; no two beats from the same redundancy group; the story is omitted if fewer than 3 beats qualify.

### 6.3 Example — built only from supported atoms

> "Your lane was even at 5:00. By 10:00 their Anti-Mage was 1,120 ahead of you with 24 more last hits. Their supports stacked 7 camps by 20:00; yours stacked 1. Between 21:00 and 29:00 your team went from −1.8k to −11.4k and lost five towers. You spent 6:40 of the game dead."

Every sentence maps to §4.1, §4.2, §4.5, §4.8, §4.4. What it deliberately does **not** say: that the stacks fed Anti-Mage, that the lane decided the game, or that the deaths caused the towers.

### 6.4 The user's illustrative story, audited

> "Your lane was even through 8 minutes. Then the enemy Carry gained 1.3k NW over the next four minutes while farming 11 neutral creeps. At 13:40 they completed Maelstrom, 3:10 earlier than opposing Carries you usually face. They ended the next ten minutes with the highest farming rate in the match."

| Clause | Supportable? | Source |
|---|---|---|
| Even through 8 minutes; +1.3k over next four | ✅ DERIVED FACT | NW per minute |
| "while farming 11 neutral creeps" | ✅ only with playback `csEvents.isNeutral` (≤90 days); historical data has whole-match neutral totals only | playback |
| "completed Maelstrom at 13:40" | ✅ purchase time ("bought Maelstrom at 13:40") | `itemPurchases` |
| "3:10 earlier than opposing Carries you usually face" | ✅ with ≥10 prior counterpart observations | history |
| "highest farming rate in the match over the next ten minutes" | ✅ (LH or NW gain per minute, 10-player) | per-minute arrays |

The illustrative story is **fully supportable** for recent matches, and supportable minus the neutral-creep clause for older ones.

---

## 7. What we CANNOT know

| Tempting claim | Why it is not knowable |
|---|---|
| "They could see you" / "you had no vision" | Visibility and fog state are not in any stats or playback stream we can use. Ward proximity is not vision (trees, high ground, sentries, true sight, ward range). |
| "You were in the fight" | Kill/assist/death credit misses present heroes: damage events added 12% more involved heroes in 102 clashes. Damage evidence is playback-only, and even damage does not prove presence at the start of a fight. |
| Movement, rotations, TP reactions, arrival time | Movement stream is prohibited and not requested; `locationReport` has no timestamps; `isAttemptTpOut` fired once in 743 deaths. |
| "Bad positioning" | No validated model of positions relative to threats; death locations are not positioning quality. |
| "Didn't use BKB before dying" | Cooldown, mana, silence/stun state at death are not observed. |
| Player intent ("greedy", "tilted", "focused you", "counter-built") | Behavioural intent is not observable. |
| Communication, pings meaning, draft intent | `pingUsed` is a count; chat content is excluded and irrelevant. |
| Mistakes without an operational definition | "Mistake" presumes the correct alternative. |
| Which stacked camp was farmed by whom | `campStack` is a per-player counter; farm source has no link to the stack. |
| Why a lane was lost | Draft, rotations, pulls, blocks, and harass are unobserved. |
| Causal effect of any event on the result | No identification strategy; sequences have high base rates (§4.10). |
| Roshan timing for old matches | Stats give counts and last-hitters only; playback expires ~90–120 days. |
| Exact gold totals by source from stats | `farmDistributionReport` totals are a partial subset of real income. |

---

## 8. Validated-but-risky heuristics

| Heuristic | Evidence so far | Risk | Research needed before shipping |
|---|---|---|---|
| Clash reconstruction (≥3 deaths, ≤20 s chain, ≤30 grid units of centroid) | Spatial rule removes the 30% time-only merges; 11.8 clashes/match Standard+Turbo corpus | Two-death skirmishes ignored; near-simultaneous separate fights in the same area merge | Hand-label 50 clashes against replays; compare with OpenDota teamfight output on the same matches |
| Coordinate → map-region classifier | 8×8 grid cells carry a 94% majority STRATZ `mapLocation` label (5k+ playback last hits) | Label set is coarse; ward/death positions may cluster at borders | Build the classifier from a larger playback sample; validate on held-out matches |
| Historical buyback detection: `timeDead < 0.6 × median same-level timeDead` | Catches 64/71 playback buybacks; flags 17/606 non-buyback deaths | Aegis/reincarnation deaths look like buybacks | Exclude Aegis holders via `inventoryReport`/Roshan context; validate on Turbo |
| `isWardWalkThrough` as "died near an enemy observer" | True → enemy observer ≤25 units 77%; False → far/none 63% | Provider semantics undocumented | Larger playback comparison; decide whether to use our own proximity instead |
| `isBurst` | True cases always had ≥60% of 10-second damage in the last 2 s (72/72), but many such deaths were False | Unknown definition, low recall | Health-event validation (1-second HP ticks, playback) |
| `isSmoke` on kills | Precision 89% (41/46), recall 41% | Conservative label | Prefer playback smoke-use timing |
| Placed-ward coverage from stats | Placement × 360 s | Overstates when dewarded (dewarded observers median 82 s) | Use only as upper bound or require playback |
| Enemy jungle/ancient share | Location ids verified; totals partial | Share may be biased by missing income categories | Compare shares with playback gold reasons on more matches |
| Disable duration ranks | Values populated | Unit unknown | Compare with ability durations from constants |
| `goldFed` | Populated | Semantics unverified | Compare with killer's kill-event gold |

---

## 9. Rejected ideas (graveyard)

| Idea / field | Reason | Category |
|---|---|---|
| Playback `roshanEvents`, `buildingEvents`, `courierEvents` | Empty in 19/19 matches | Technically unavailable |
| `towerStatus` | Empty | Technically unavailable |
| `locationReport` | No timestamps; irregular cadence (duration/length 17–61 s); zero for some matches | Semantically ambiguous |
| `laneReport` | Undocumented lists of small creep counts | Semantically ambiguous |
| `farmDistributionReport.buyBackGold`, `bountyGold` | Always 0 / empty | Technically unavailable |
| `buyBackEvents.cost`, `deathTimeRemaining` | Always 0 | Technically unavailable |
| `chatEvents` for Roshan, Aegis pickup, buyback, ward kills, smoke, runes | Those types never appear; STRATZ stores a subset | Technically unavailable |
| Aegis in `inventoryReport` for Roshan timing | Present in 15/21 patch-180/181 matches but only 7/96 patch-182 matches | Insufficient coverage / patch drift |
| `analysisOutcome` (STOMPED/COMEBACK) | Proprietary; labelled NONE for 24 of 36 lead-curve comebacks | Misleading / provenance |
| `isEngagedOnDeath` | Weak agreement with damage evidence (364 false negatives vs 185 true positives) | Too noisy |
| `isAttemptTpOut` | 1 true in 743 deaths | Uninformative |
| "Most-involved enemy on most of your deaths" (ungated) | Population norm (median 78%) | Boring / misleading |
| Stats-only identification of which ward was destroyed | 26% accuracy | Too noisy |
| Root `matches(ids:)` / `player.matches(matchIds)` batching | Flat ~770k complexity for the core selection | Technically unusable |
| Movement heatmaps from playback positions | Prohibited, huge | Policy / cost |
| 1-second HP / gold tick streams for cards | MBs per match; low marginal card value | Cost |
| Stack beneficiary attribution | No link | Unsupported |
| Fight "presence" from credit only | Misses 12% of damage-evidenced heroes | Misleading |
| "Throw" labels | Judgement; replaced by neutral lead-change facts | Misleading |
| Teammate blame comparisons | Product harm | Misleading |
| OpenDota as production source | Pub parse coverage ~1.6% without parse requests | Insufficient coverage |

---

## 10. Validation evidence

### 10.1 Calls

| Purpose | Calls | Result |
|---|---:|---|
| Schema introspection (recursive, 172 types) | 9 | all 200 |
| Recent-match discovery (6 cohort accounts × 40) | 1 | 240 matches, 85.8% parsed |
| Constants (npcs, items, abilities, heroes) | 1 | 310 KB |
| Complexity experiments (full b1/b2/b4, split A/B b4/b8/b16, root `matches(ids)` 8/24, `player.matches` 8/24/lean) | 14 | 8 intentional COMPLEXITY rejections |
| Playback availability (0.6–360 days) + repeat + cached batch | 23 | available ≤90 d, null ≥120 d |
| Full playback (1 Turbo with 1 s ticks; 6 long Standard without ticks) | 7 | 3.2–9.4 MB |
| Validation corpus — core op (8 per request) | 17 | 131 matches |
| Validation corpus — reports op (4 per request) | 33 | 131 matches |
| Stats for playback matches | 3 | 7 matches |
| One account history (100 match IDs + 13 core batches) | 14 | 100 matches |
| **Total** | **122** | 91.9 MB; daily quota remaining after run: 14,868 |

### 10.2 Corpus

- 131 matches chosen from existing corpora: Standard long (>55 min), short (<23 min), stomps, close games, comebacks, bloodiest, many self-wards, many self-stacks, oldest (2025-09), patch 181, each position, Turbo long/short/random/old, other modes, leaver match, 8 unparsed, 13 recent (0.6–44.6 days).
- Parsed with full stats: 79 Standard, 38 Turbo, 3 other; 11 without stats.
- One account's 100 most recent parsed matches (50 Standard, 50 Turbo).
- 7 full playback matches: 6 Standard of 54–80 minutes containing 71 buybacks and 20 Roshan/Tormentor kills, 1 Turbo.

### 10.3 Cross-checks and results

| Check | Result |
|---|---|
| `radiantNetworthLeads[i]` vs Σ team `networthPerMinute[i−1]` | median error 0, p90 0 (n=4,833) — offset 0 error 1,089 |
| `radiantExperienceLeads[i]` vs Σ cumulative `experiencePerMinute` | median error 43 at offset −1 |
| Σ `lastHitsPerMinute` vs `numLastHits` | equal 673/1,170; diffs mostly −1 to −7 |
| Final `networthPerMinute` vs `networth` | median relative error 1.5% |
| Death attacker has matching kill event (±1 s, target) | 10,228/10,663 (95.9%); 349 null attackers |
| Death assist hero has matching assist event | 16,994/17,123 (99.2%) |
| `timeDead` vs buyback time − death time | 73/73 |
| Overlapping death windows | 45/9,864 |
| Stats ward count vs playback spawns per player | 70/70 |
| Stats deward count vs playback destroyed-by | 62/70 |
| `wardDestruction.isWard` vs destroyed ward type | Observer 112/114; Sentry 191/195 |
| Observer / sentry natural lifetime | 360 s / 420 s |
| Stats `itemUsed` vs playback item-use events | 1,044/1,044 |
| `heroDamageReport` Σ dealtTargets vs `heroDamage` | ratio 1.000 (p10/p90 1.000) |
| Damage symmetry A→B vs B←A | 5,944/5,944 |
| `farmDistributionReport.other[133].count` vs Roshan kills | 13/13 |
| `other[861].count` vs Tormentor kills (chat 117) | 13/13 |
| Chat 117 time vs Tormentor last hit (`csEvents` npc 861) | exact in all observed |
| Chat glyph vs `actionReport.glyphCast` | 81/117 equal; sampled mismatches differ by 1 |
| Chat first blood vs `firstBloodTime` | exact |
| `creepLocation.id` ↔ player lane | Radiant safe→3, off→7, mid→2; Dire safe→7, off→3, mid→6 (= `MapLocationEnums` geography) |
| Position uniqueness per team | 100% |
| Counterpart same map lane | P1/P3 98.7%, P2 98.3%, P4/P5 94% |
| Early last-hit lane vs STRATZ `lane` (playback) | cores 42/42; supports 11/14 |
| Coordinate grid | x 61–194, y 62–193; 8×8 cell label purity 94% |
| Complexity per match | core op 38,510; reports op ~52,200; full ~90,660; cap 310,000 |

### 10.4 Anomalies

- 3 matches report `parsedDateTime` but return null stats for every player — eligibility must test data, not the flag.
- `buyBackEvents` cost/remaining are always 0.
- STRATZ's `ROSHAN` gold reason includes Tormentor kills.
- Aegis stopped appearing in minute inventory snapshots in the newest patch sample.
- Chat events are a filtered subset of Valve's enum (no Roshan, Aegis pickup, buyback, ward kills, smoke).
- Turbo matches in the corpus had no `courierKills`.

---

## 11. Production acquisition recommendation

### 11.1 Core historical dataset (backfillable, batch-friendly)

**Operation CORE — `GetTenPlayerCoreBatch`**
- Aliased `match(id:)` × **7** per request (38,510 complexity per match → 269,570; 8 fits at 308,080 but leaves ~0.6% headroom for schema growth).
- Match: timing, mode, lobby, patch, leads, kill arrays, lane outcomes, first blood, `towerDeaths`, `pickBans`.
- Players (never `steamAccountId` for others): slot, side, hero, position, lane, role, leaver, final scalars, final items.
- Stats: `networthPerMinute`, `lastHitsPerMinute`, `deniesPerMinute`, `experiencePerMinute`, `level`, `campStack`, `killEvents`, `deathEvents` (without provider flags except `isWardWalkThrough` quarantined), `assistEvents`, `itemPurchases`, `itemUsed`, `wards`, `wardDestruction`, `runes`, `towerDamageReport`, `farmDistributionReport` (creepLocation, neutralLocation, ancientLocation, other).
- Measured ~125 KB/match JSON, ~1.1 s per request.

**Operation REPORTS — `GetTenPlayerReportsBatch`**
- Aliased × **4** per request (~52k/match).
- Stats: `heroDamageReport` (targets + totals), `abilityCastReport`, `actionReport`, `inventoryReport`; match `chatEvents`.
- Drop `locationReport`, `laneReport`, `towerStatus` (unusable) — re-measure complexity after trimming; batch may rise to 5–6.
- Measured ~137 KB/match with the unusable fields, ~0.6 s per request.

### 11.2 Recent-match enrichment (graceful degradation)

**Operation PLAYBACK_LIGHT — `GetRecentMatchPlayback`**
- One uncached match per request; only for matches ≤ 90 days old; repeat reads are cached.
- Match `wardEvents`; player `goldEvents`, `itemUsedEvents`, `buyBackEvents`, `csEvents` (for Roshan/Tormentor last hit and lane verification).
- Optional `heroDamageEvents` only if clash involvement ships (adds ~0.8 MB per 20-minute match).
- Measured 90–385 KB, 0.4–3.1 s. Cards depending on it degrade to historical versions or disappear.

### 11.3 Cost model

| Scenario | CORE | REPORTS | PLAYBACK | History page | Total requests |
|---|---:|---:|---:|---:|---:|
| New user backfill, 500 parsed matches (core only) | 72 | — | — | ~7 | ~79 |
| Backfill with reports for last 100 matches | 72 | 25 | — | ~7 | ~104 |
| One 5-match session | 1 | 2 | 5 | 1 | 9 |
| One single match | 1 | 1 | 1 | 1 | 4 |

- Daily ceiling 15,000 requests on one key: ~1,600 players playing a 5-match session per day with full enrichment; ~3,700 without playback. Backfill at ~104 requests is ~144 new users/day if it were the only load.
- Storage: CORE + REPORTS ≈ 260 KB/match uncompressed JSON; store compressed raw plus normalized facts; derived fact rows are KB-scale.
- Parse wait: median ~28 minutes; poll per the Lifecycle SSOT; never generate cards for unparsed matches.

### 11.4 Required engineering safeguards

- Version each operation and record its document digest on every row (existing V7 practice).
- Fail closed when stats are null despite `parsedDateTime`.
- Constants snapshot per `gameVersionId`.
- Forbidden-field gate extended to other players' identities, proprietary scores, and quarantined flags.
- Complexity regression test: any selection change must be re-measured at the chosen batch size before release.

---

## 12. Recommended V1 insight engine

```text
Raw Match Facts
  ↓
Derived Match Facts
  ↓
Historical Context
  ↓
Insight Candidates
  ↓
Reliability Filters
  ↓
Interestingness Ranking
  ↓
Post-Match Cards / Match Story
```

| Layer | Definition | Deterministic? |
|---|---|---|
| **Raw Match Facts** | Normalized CORE/REPORTS/PLAYBACK payloads for one match: per-player minute arrays, events, wards, purchases, structures, damage matrix. Immutable per operation digest. | Yes |
| **Derived Match Facts** | Versioned calculators: counterpart pairing and lane diffs; CS/NW split; team stacks @20; ward war; time dead and re-death chains; nemesis involvement; clash list (heuristic v1); structure sequences; Roshan/Tormentor counts (+times when playback); item never-activated; key item timings; swing window; region labels (heuristic v1). Each fact carries its evidence level and version. | Yes |
| **Historical Context** | Per-user store of *match-level facts about their games*, including opponent facts without opponent identity, keyed by bucket (+ effective role where role-dependent). Computes prior-N records, medians, percentiles as of the match (no hindsight). | Yes |
| **Insight Candidates** | Typed card candidates from derived facts × context: value, comparator, sample size, evidence level, redundancy group, copy template id, allowed slots. | Yes |
| **Reliability Filters** | Eligibility (parsed, duration, lanes matched), minimum samples (§4.13), evidence gates (no D; C only in P1+ with heuristic-safe copy), outcome-restating filter (e.g., ward war in a stomp only as context), playback availability. | Yes |
| **Interestingness Ranking** | Score (below); redundancy groups; one-criticism cap; novelty memory across recent recaps. | Yes |
| **Cards / Story** | Up to 3 cards + optional 3–4 beat story (§6). Templates first; any language model may only rephrase validated slots and must be post-validated. | Templates yes |

### Ranking model

```text
Value = Surprise × Personal Relevance × Explanatory Power × Reliability × (1 − Redundancy) × Novelty
```

| Factor | Definition |
|---|---|
| Surprise | Personal: 1 − empirical frequency of an equally extreme value in the comparator (record ≈ 1/(N+1)); intra-match contrasts (CS/NW split, 9 vs 1 stacks) scored by magnitude relative to bucket population p90 |
| Personal Relevance | 1.0 own hero/deaths/items; 0.9 lane counterpart; 0.75 enemy team vs own team; 0.5 match-wide |
| Explanatory Power | 1.0 if it reframes the user's own numbers (counterpart context, CS/NW split, time dead); 0.8 invisible enemy activity; 0.6 sequences; 0.4 standalone totals |
| Reliability | A 1.0 · B 0.95 · C 0.7 · D 0 |
| Redundancy | 1 when another selected card shares a group (lane, economy, deaths, vision, objectives, items) |
| Novelty | 0.5 if the same card type appeared in either of the last two recaps and is not a new record |

---

## 13. Prioritized final shortlist

### P0 — "This makes the product special"

1. **Lane Counterpart Path** — "At 5:00 you were +380 on their Anti-Mage. By 10:00 you were −1,120."
2. **CS-vs-Net-Worth Split** — "You were 16 CS behind Lone Druid at 10:00 but 2,506 net worth ahead."
3. **Extreme Opponent Start (history)** — "Their Anti-Mage had 68 CS at 10:00 — the most any opposing Carry has had against you in your last 11 Turbo Offlane games."
4. **Enemy Stacking** — "Their team stacked 9 camps by 20:00. Yours stacked 1."
5. **Ward War** — "They placed 26 observers and destroyed 9 of your team's 21."
6. **Time Dead (with record)** — "You spent 8:52 dead — your longest in 16 Turbo Support games."
7. **Bought, Never Activated** — "You bought Force Staff at 21:10 and never used it."
8. **Swing Window** — "The game turned between 18:00 and 26:00: from +4.2k to −7.9k, with 4 towers lost."

### P1 — Very valuable

- Who Kept Finding You (gated nemesis)
- Towers lost while you were dead
- Clash → structures sequence ("after the 27:30 clash, Dire took two towers within 94 seconds")
- Roshan count and last hitters (historical); Roshan times (recent)
- Enemy smoke uses followed by kills (recent)
- Enemy core pace to 10k (history) and economy concentration
- Enemy key item timing vs your usual opponents
- Who damaged you most / most disabled (rank)
- Quick re-deaths after respawn
- Deaths near standing enemy observers (recent, proximity wording)
- Where you died (region heuristic)
- Your observers' fate (recent)
- Buybacks (recent exact; historical heuristic)
- Level-6 race, lead flip minute, comeback-size record
- Enemy ward placement regions

### P2 — Nice additional context

- Tormentor kills; Glyph uses; barracks timeline
- Income mix over time (recent)
- Spell focus ("Lion cast Finger on you 4 times")
- Lane farm geography; support duo lane diff; STRATZ lane outcome label
- Items held by minute; enemy activation counts
- Observer uptime per team (recent exact)
- Gold lost to deaths

### Experimental

- Clash involvement from damage events
- Burst deaths
- Historical deaths near enemy observers via `isWardWalkThrough`
- Historical observer uptime upper bound
- `goldFed` insights
- Who died first in lost clashes
- Detection purchases vs enemy invisibility

### Do Not Ship

- Any visibility claim ("they saw you", "no vision")
- Any causal claim ("cost you", "because", "punished", "won them the game")
- Presence in fights from credit alone
- Stack beneficiary attribution
- "Didn't use BKB before dying"
- Intent, tilt, greed, focus, counter-building
- Teammate blame
- `analysisOutcome`, `isEngagedOnDeath`, `isAttemptTpOut`, `locationReport`, `laneReport`, `towerStatus`, buyback cost fields, Aegis-inventory Roshan timing

---

## Appendix A — Phase 1: analytical dimensions → reconstructability

| Dimension | What a good analyst notices | Reconstructable from | Best level |
|---|---|---|---|
| Laning | Who won which lane against whom, when it flipped | counterpart NW/CS/level per minute | B |
| Resource distribution | Who on each team was fed; support starvation | team NW shares per minute | B |
| Farming efficiency | Farm pace; lane vs jungle | CS/NW per minute; farm location shares | B |
| Map economy / neutral usage | Jungle/ancient reliance; stacks | campStack; farm report shares; playback neutral last hits | B |
| Pressure / tempo | Tower race, lead growth | towerDeaths; lead curve | B |
| Map control | Where a team operates | ward and death coordinates (region heuristic); **not** movement | C (partial) |
| Vision / dewarding | Ward war volume and fate | wards, wardDestruction; playback lifecycle | B |
| Rotations / ganks | Coordinated kills away from lanes | kill positions + clusters; smoke timings | C / D for intent |
| Deaths / repeated patterns | Chains, nemesis, locations, dead time | death events | B / C |
| Matchup pressure | Lane counterpart extremes | counterpart history | B |
| Objective pressure / sequencing | Structures after clashes, during dead time | towerDeaths + clusters + timeDead | B |
| Fight outcomes / aftermath | Clash results and what followed | clusters + structures + Roshan | C + B |
| Recovery / snowball / comebacks | Lead curve shape, comeback size | lead curve | B |
| Item timings / spikes / mismatches | Key items vs counterpart and usual opponents | purchases; history | B |
| Item usage | Active items never used; activation counts | itemUsed (+ playback timing) | B |
| Team resource allocation / carry protection | NW concentration; *protection is not observable* | NW shares | B / D |
| Support economy / stacking | Support NW, stacks, wards | NW, campStack, wards | B |
| Rune control | Power/bounty/wisdom pickups by team | runes | A |
| Buybacks / downtime | Dead time, buybacks | timeDead; playback buybacks; heuristic | B / C |
| Hero targeting | Who damaged/disabled whom | damage report, cast report | B |
| Repeated enemy involvement | Nemesis | death attackers/assists | B |
| Asymmetric strategies | One team stacks/wards/smokes far more | team totals | B |
| Unusual behaviour vs history | Records vs user's own and opponents' history | history store | B |
| Additional: Tormentor / Roshan control | Who took the bosses | farm other, chat 117, playback gold | A/B |
| Additional: smoke tempo | Smokes followed by kills | playback item uses | B (recent) |
| Additional: lead conversion | Lead without structures | lead curve + towers | B |

## Appendix B — Sources

External references consulted:

- [STRATZ API](https://stratz.com/api) and [STRATZ Knowledge Base › API](https://stratz.com/knowledge-base/API) (no public field-level semantics; page content partly inaccessible to automated fetch)
- [STRATZ_Models (auto-generated C# models)](https://github.com/TheAmazingLooser/STRATZ_Models) — no semantic documentation
- [STRATZ knowledge-base issues](https://github.com/STRATZ-Esports/knowledge-base/issues)
- [SteamDatabase GameTracking-Dota2 `dota_usermessages.proto`](https://raw.githubusercontent.com/SteamDatabase/GameTracking-Dota2/master/Protobufs/dota_usermessages.proto) — `DOTA_CHAT_MESSAGE` enum used to decode STRATZ `chatEvents.type`
- [gem-dota replay parser](https://github.com/whanyu1212/gem-dota) — ward lifetimes (observer 6 min, sentry 7 min), temporal teamfight windowing, objectives
- [odota/core issue #808 — Roshan & Aegis](https://github.com/odota/core/issues/808)
- [Liquipedia Death](https://liquipedia.net/dota2/Death) / [Dota 2 Wiki Death](https://dota2.fandom.com/wiki/Death) (search summaries: Turbo respawn 25% faster; buyback penalty mechanics)
- Repository: `research/opendota-parsed-match-insight-research.md` (OpenDota teamfight rule: ≥3 deaths, 15-second windows), `docs/evidence/free-dna-opendota-parsed-feasibility-2026-08-28.md` (pub parse coverage)
