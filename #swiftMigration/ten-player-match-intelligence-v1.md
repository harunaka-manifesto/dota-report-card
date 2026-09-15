# Ten-Player Match Intelligence — Acquisition & Insight Design

> **Superseded for data-capability claims by
> [Post-Match Intelligence Deep Research V2](post-match-intelligence-deep-research-v2.md)
> (2026-09-14).** Key corrections: playback is available for matches up to ~90
> days old (not fresh-only); the 8-match core batch sits at the complexity cap
> (use 7); `timeDead` is buyback-truncated realized time dead; Roshan counts are
> historical via `farmDistributionReport.other`; several fields listed here are
> dead or unreliable.

Status: PROBE-VERIFIED FEASIBILITY + PROPOSED DESIGN — non-normative
Date: 2026-09-14
Repository base: `main` at `5d23eed`
Companion to: [Post-Match Intelligence Feasibility & Architecture](post-match-intelligence-feasibility-v1.md)
Provider calls made: **STRATZ 10** (bounded live probe, read-only), OpenDota 0
Probe artifacts (ignored, local): `.local/stratz-probe/ten-player-2026-09-14/`
Identifiers in this document: none. The probe never selected other players' account identities.

---

## 1. Answer

**We can get it.** STRATZ returns full parsed `stats` for **all ten players** —
camp stacks, ward placements with coordinates, dewards, per-minute net worth
and last hits, lane/jungle/ancient farm source, item purchase timings, runes,
tower damage by tower, and rich death and kill events (killer hero, map
position, time spent dead, gold lost, assisting heroes). It does so **8 matches
per request, with no complexity error, in about one second**, and the same data
is still available for a match played a year ago.

The earlier conclusion that other players were "almost opaque" was wrong. It
rested on a misattributed number: the 6,159,595 complexity rejection recorded
in the STRATZ field inventory came from a **full schema introspection query**
(`A1`), not from a ten-player stats query. The one ten-player specimen (`A6`)
requested scoreboard scalars only. Until this probe, nobody had actually asked
STRATZ for ten-player `stats`.

Two limits remain real:

1. **Match-level playback** (per-ward spawn/despawn with dewarder, time-stamped
   gold by reason) is rebuilt from the replay on demand: **one uncached match per
   request**, and it returned nothing for a one-year-old match. It is a
   fresh-match-only enrichment, not a backfill source.
2. **Everything is still parse-dependent.** Unparsed matches (8.0% Standard,
   27.6% Turbo in Pass-1 history) have no ten-player detail either.

---

## 2. Probe record

All calls used one bounded helper (`stratz_call.py`, 25-call ceiling, token read
from the environment and never written). Targets were public match IDs taken
from the existing Pass-2 corpus: 8 recent Standard matches, 1 Turbo match, and
1 match from 2025-09-01.

| # | Query | Scope | HTTP | Bytes | Latency | Result |
|---:|---|---|---:|---:|---:|---|
| 1 | Type-shape introspection (25 event/report types + query root) | — | 200 | 21,097 | 0.38 s | All shapes resolved |
| 2 | Ten-player `stats` (trajectories, events, wards, dewards, farm, runes, purchases) | 1 Standard match | 200 | 36,541 | 0.34 s | 10/10 players populated |
| 3 | Same selection, 8 aliased `match(id:)` fields | 8 Standard matches | 200 | 284,945 | 0.75 s | 80/80 player rows populated; no complexity error |
| 4 | Ten-player rich events (death/kill/assist detail, tower damage report, item used) | 1 match | 200 | 67,361 | 0.41 s | Populated |
| 5 | Match playback (wardEvents, buildingEvents, roshanEvents, towerDeathEvents, runeEvents) | 1 fresh match | 200 | 36,185 | 1.57 s | Ward/rune/tower events populated; **building and Roshan events empty** |
| 6 | Per-player playback light (deathEvents, buyBackEvents, goldEvents) | 1 fresh match | 200 | 148,749 | 0.42 s | Gold events with reasons populated |
| 7 | Ten-player `stats` | 1 Turbo match | 200 | 38,343 | 0.39 s | Populated |
| 8 | Combined 2 + 4 + 5 selection | 8 matches | 200 | 789,490 | 1.09 s | **Stats complete for 80/80 players; playback refused** ("at most 1 [uncached match] may be rebuilt at a time") |
| 9 | Match playback | 1 match from 2025-09-01 | 200 | 1,827 | 0.38 s | `playbackData` null |
| 10 | Ten-player rich events | same old match | 200 | 73,373 | 0.32 s | 10 players, 99 deaths, all with position and time dead |

Rate-limit headers after the final call: 14,990 of 15,000 daily requests remaining.

### 2.1 Sanity checks on the new data

| Check | Result | Reading |
|---|---|---|
| Ten-player `campStack` monotone | 80/80 non-decreasing; 31/80 series sum above final value | Same cumulative semantics already validated for the tracked player |
| Array lengths | `networthPerMinute` one longer than `lastHitsPerMinute` in 80/80 | Same alignment rule as Pass-2 |
| Death `attacker` | 85/86 values are hero IDs present in the match; 1 null | Killer hero; null = non-hero kill (to confirm) |
| Death `timeDead` | Present on 647/647 deaths; median 21 s before 10:00, 52.5 s after 30:00 | Consistent with respawn time rising with level |
| Death `positionX/Y` | Present on all deaths; range 60–194 | Same coarse grid as ward coordinates (grid mapping still unvalidated) |
| Stats ward placements vs playback ward spawns | 81 = 81 (32 observers + 49 sentries) | Placement stream is complete for both teams |
| Stats `wardDestruction` vs playback `playerDestroyed` | 15 = 15 | Deward counts reconcile |
| Playback observer lifetimes | Max 360 s; dewarded wards 56–141 s | Spawn/despawn pairing by `indexId` works |
| `isWardWalkThrough` | True on 375/647 deaths (58%) | **Provider heuristic with unclear meaning — do not use** |
| `isEngagedOnDeath`, `isBurst`, `isTracked`, kill `isSmoke`/`isGank`/`isSolo` | Populated | Provider-computed labels; quarantine until validated |
| Tower deaths `attacker` | Hero IDs or null | Last-hit hero; null for creep/other kills (to confirm) |
| Playback `goldEvents.reason` | `CREEPS`, `NEUTRAL`, `HEROES`, `STRUCTURES`, `ROSHAN`, `BOUNTY`, `WARD_DESTRUCTION`, `COURIERS`, `DEATH`, … | Time-stamped farm source and objective gold — fresh matches only |

**Sample size is 10 matches.** This establishes availability, shape, and cost.
It does not establish population coverage or semantics at corpus scale (§8).

---

## 3. What is now available, per player, for all ten players

| Category | Fields (all ten players) | Source | Backfillable |
|---|---|---|---|
| Economy | `networthPerMinute`, `lastHitsPerMinute`, `deniesPerMinute`, `experiencePerMinute`, `goldPerMinute`, `level` timestamps, final scalars | `stats` | Yes |
| Farm source | `farmDistributionReport`: `creepLocation`, `neutralLocation`, `ancientLocation`, `buildings`, `bountyGold`, `buyBackGold`, `abandonGold` | `stats` | Yes |
| Stacking | `campStack` cumulative per minute | `stats` | Yes |
| Vision placed | `wards {time, type, positionX, positionY}` | `stats` | Yes |
| Vision removed | `wardDestruction {time, isWard, gold, experience}` | `stats` | Yes |
| Ward lifecycle | `wardEvents {indexId, time, positionX, positionY, fromPlayer, wardType, action, playerDestroyed}` | match `playbackData` | **Fresh only**, 1 match/request |
| Deaths | `deathEvents {time, attacker, timeDead, positionX, positionY, goldLost, goldFed, xpFed, assist[], byAbility, byItem}` | `stats` | Yes |
| Kills / assists | `killEvents {time, target, positionX, positionY, gold, xp, assist[]}`, `assistEvents {time, target, positionX, positionY}` | `stats` | Yes |
| Objectives | `towerDeaths {time, npcId, isRadiant, attacker}`; per-player `towerDamageReport {npcId, damage, damageCreeps, damageFromAbility}` | match / `stats` | Yes |
| Roshan | `roshanEvents` empty in probe; `goldEvents.reason == ROSHAN` present | playback | Fresh only; semantics unverified |
| Items | `itemPurchases {time, itemId}`, `itemUsed {itemId, count}` | `stats` | Yes |
| Runes | `runes {time, rune}` per player; match `runeEvents` | `stats` / playback | Yes / fresh |
| Provider heuristics | `isEngagedOnDeath`, `isBurst`, `isTracked`, `isWardWalkThrough`, `isSmoke`, `isGank`, `isSolo`, `isTpRecently` | `stats` | Quarantine |
| Still unavailable | Movement paths, fight presence without credit, spell sequences, cooldown/mana state, courier behaviour beyond kills | — | No |

---

## 4. Acquisition design

### 4.1 Operation A — `GetTenPlayerMatchBatch` (primary, backfill + ongoing)

- `match(id:)` aliased ×8 per request (measured working).
- Match: timing/mode/patch, `radiantNetworthLeads`, `radiantKills`/`direKills`,
  lane outcomes, `towerDeaths`, `pickBans`.
- Every player: slot, side, hero, position/role/lane, final scalars, and the
  `stats` fields in §3 except the quarantined heuristics.
- **Never select** `steamAccountId`/`steamAccount` for players other than the
  tracked account, rank fields, IMP, awards, predictions, `behavior`, chat.
- Measured: ~36 KB/match without rich events; **~110 KB/match** JSON with rich
  death/kill/assist detail; ~1.1 s per 8-match request.
- Supersedes `GetDeepMatchBatch` v3.4.0 for the product path: same request
  count per match, ~7–8× the bytes.

### 4.2 Operation B — `GetFreshMatchPlayback` (optional enrichment)

- One match per request, only for matches discovered within the replay
  availability window (window length unmeasured; zero for a one-year-old match).
- Match `playbackData.wardEvents` (full ward lifecycle and dewarder) and
  optionally per-player `goldEvents {time, amount, reason}` (~149 KB with deaths).
- **Never** `playerUpdatePositionEvents` (movement stream, ~4.6 MB/match).
- Absence must be a normal state: cards that need Operation B degrade to
  Operation A approximations or are omitted.

### 4.3 Cost

| Scenario | Requests |
|---|---:|
| Onboarding backfill, 500 parsed matches | ~63 (Operation A only) plus history pages |
| A 5-match session, stats only | 1 history + 1 stats |
| A 5-match session with fresh playback | 1 history + 1 stats + 5 playback |
| Daily ceiling on one key | 15,000 |

Rough capacity per key: ~5,000 daily active players at ~3 requests each without
playback, ~2,000 with playback on every new match. Backfill: ~230 new users per
day if backfill were the only load.

Storage: ~110 KB/match uncompressed JSON (text-heavy, typically compresses
several-fold). A 500-match backfill is ~55 MB uncompressed. Trim candidates
before production: per-minute XP, hero damage, and healing arrays for the nine
other players, kill/assist `gold`/`xp`, and `itemUsed` for other players.

### 4.4 Policy decisions required (owner)

| Decision | Why it is needed | Recommendation |
|---|---|---|
| Collect and retain other players' parsed match data | V7 rules treated the other nine as "context, not subjects" and kept scalars only | Allow match-scoped data keyed only by match + slot + hero. No account IDs, no cross-match tracking of other people, no display of names |
| Lift the playback prohibition narrowly | V7 policy prohibited playback wholesale (cost and movement data) | Allow only match-level `wardEvents` and per-player `goldEvents` for fresh matches; keep movement prohibited |
| Provider heuristic flags | They are STRATZ model outputs, like `analysisOutcome` | Do not request, or quarantine like `actionsPerMinute` |
| New canonical schema + forbidden-field gate | `deep.py` normalization and the gate assume a single tracked player | Version a ten-player canonical schema; extend the gate to reject other-player identity |
| SSOT metrics that were blocked | Opponent trajectories now available | Re-open Mid Lane NW Advantage, Offlane Lane Pressure, Mid Early Fight Presence, Offlane Objective Involvement for implementation; consider Carry Time Dead after `timeDead` validation (new metric version decision) |

---

## 5. What this lets us tell the player — "their side of the match"

The product move: the player saw their own screen. The app shows them the
other nine — **especially the enemy five** — without making them watch a
replay.

Rungs as in the companion document: Fact, Observation, Pattern, Hypothesis.
"Your usual opponents" means a new history the product keeps per user:
observations of the enemy team in the user's own games, keyed by
`progression_bucket + effective_role` of the user (so it is still *their*
experience).

### 5.1 Stacking and jungle economy

| Card | Example | Data | Rung | Tier |
|---|---|---|---|---|
| Team stacks by 20:00 | "Their team stacked 9 camps by 20:00. Yours stacked 1." | ten-player `campStack` @20:00 | Fact | **P0** |
| Stacks vs games you play | "That's the most stacking you've faced in 30 Support games." | + opponent history | Observation | **P0** |
| Enemy jungle/ancient farm | "Their carry took 4.8k gold from neutral and ancient camps — 38% of their creep gold." | `farmDistributionReport` (whole match) | Fact | P1 |
| Stacks alongside farm | "Their supports stacked 9 camps; their carry's jungle and ancient gold was 4.8k." | both | Hypothesis (co-occurrence only) | P1 |
| Time-resolved stack payoff | "Their carry farmed 11 neutral camps between 12:00 and 20:00." | playback `goldEvents` reason `NEUTRAL` | Fact | P2 (fresh only) |

Never: "their stacks won the game", "your support should have stacked".
Stacks are whole-match and team-level; which stack was farmed by whom is not
observed in Operation A.

### 5.2 Vision and dewarding

| Card | Example | Data | Rung | Tier |
|---|---|---|---|---|
| Wards placed per team | "Their supports placed 26 observers; your team placed 11." | ten-player `wards` | Fact | **P0** |
| Dewards per team | "They cleared 9 of your wards; your team cleared 2 of theirs." | ten-player `wardDestruction` | Fact | **P0** |
| Your wards' fate (fresh) | "5 of your 8 observers were removed, 3 within a minute of placement." | playback `wardEvents` spawn/despawn + `playerDestroyed` | Fact | P1 (fresh only) |
| Placed-ward coverage per team | "Their observers were up for 81% of the game; yours 43%." | placements with 6-min upper bound (Operation A) or exact lifetimes (Operation B) | Fact (upper bound unless B) | P1 |
| Vision vs your usual opponents | "The heaviest dewarding you've faced in 20 Support games." | + opponent history | Observation | P1 |
| Where they warded | "Most of their observers sat in your jungle." | ward coordinates + map-region model | Fact | P2 until the coordinate grid is validated |

Never: "you lost map control", "they knew where you were". Placement and
removal are observable; what anyone saw is not.

### 5.3 Farming effectiveness

| Card | Example | Data | Rung | Tier |
|---|---|---|---|---|
| Lane opponent benchmark | "Your lane opponent (their carry) had 62 CS at 10:00 — the most any carry has had against you in 20 Offlane games." | opponent `lastHitsPerMinute` + opponent history | Observation | **P0** |
| Lane net-worth gap @10 | "You finished lane 900 gold ahead of their carry." | own + opponent `networthPerMinute[10]` (SSOT Offlane Lane Pressure) | Fact | **P0** |
| Core farm race | "Their carry reached 10k net worth at 17:10; yours at 22:40." | ten-player net worth curves | Fact | P1 |
| Enemy item spikes vs the swing | "Their carry finished BKB at 17:40. Your team's lead fell from +2k to −6k over the next 6 minutes." | `itemPurchases` + item vocabulary + lead curve | Hypothesis (co-occurrence) | P1 |

Teammate rule: allied cores may appear only as "your team" aggregates or as the
player's own lane partner in neutral framing; no "your carry was behind"
callouts.

### 5.4 Teamfights

Reconstructed by us from all ten players' kill, death, and assist events
(timestamps and positions): a fight is a cluster of ≥3 hero deaths with gaps
≤15–20 s (the same family of heuristic OpenDota uses), located by death
positions.

| Card | Example | Data | Rung | Tier |
|---|---|---|---|---|
| Fight record | "7 fights with 3+ deaths. Your team won 2 on deaths." | clustered death events | Fact (under a named heuristic) | P1 |
| Credited numbers per fight | "Their team had 5 heroes credited in 6 of 7 fights; your team averaged 3." | kill/assist/death credit per cluster | Fact (credit, not presence) | P1 |
| The deciding fight | "The 27:30 fight: 4 of yours died, 1 of theirs, two towers fell in the next 90 s." | clusters + tower deaths | Fact | P1 |
| Your fights | "You were credited in 5 of 7 fights; you died first in 3." | own events within clusters | Fact | P1 |

Never: "slow to respond", "late rotation", "bad initiation". Presence without
kill/assist/death credit, arrival time, and decision quality are not observed.
Provider flags (`isSmoke`, `isGank`, `isEngagedOnDeath`) stay out until validated.

### 5.5 Objectives

| Card | Example | Data | Rung | Tier |
|---|---|---|---|---|
| Tower race | "They took 6 towers before your team's first at 19:10." | `towerDeaths` | Fact | **P0** |
| Who hit their towers | "Their offlaner did 41% of the damage to towers your team lost." | ten-player `towerDamageReport` + tower ownership | Fact | P1 |
| After-fight objectives | "After the 27:30 fight they took 2 towers within 90 s." | clusters + `towerDeaths` | Fact | P1 |
| Roshan | "They took Roshan at 24:10." | playback gold reason `ROSHAN` | Fact if validated | P2 (fresh only; `roshanEvents` came back empty) |

### 5.6 Your deaths, with the other side filled in

| Card | Example | Data | Rung | Tier |
|---|---|---|---|---|
| Time dead | "You spent 4:10 dead — 11% of the game." | own `timeDead` | Fact (after validation) | **P0** |
| Who killed you | "Their Position 4 (Spirit Breaker) was on 6 of your 8 deaths." | `attacker` + `assist` hero IDs | Fact | **P0** |
| Where you died | "5 of your 8 deaths were in their half of the map." | death positions + validated map model | Fact | P1 after grid validation |
| Gold lost | "Your deaths cost 1,850 gold." | `goldLost` | Fact | P1 |

### 5.7 Runes and items

| Card | Example | Data | Rung | Tier |
|---|---|---|---|---|
| Rune control | "Their mid picked up 9 of the game's 12 power runes." | ten-player `runes` | Fact | P2 (enum partially known) |
| Enemy key timings vs your usual opponents | "Their carry's BKB came 6 minutes earlier than carries you usually face." | purchases + opponent history + item vocabulary | Observation | P2 |

---

## 6. Making it personal, not a second scoreboard

Ten-player data risks becoming "here are everyone's stats". Three rules keep it
the player's own discovery:

1. **Anchor every card to the player's game.** Lane opponent, the enemy team
   *they* faced, their wards' fate, their deaths' killers.
2. **Compare to the player's own history of opponents.** Keep per-user
   distributions of enemy-team observations (stacks @20, observers placed,
   dewards, lane opponent CS@10) by the user's bucket and effective role. A
   card fires only when the value is at the edge of the last 20 such games and
   above a minimum meaningful difference — the same gate as the companion
   document.
3. **Contrast, then stop.** "Their team stacked 9; yours 1" is a fact. The app
   does not add "which is why".

Corpus context for how rare these values are: in the Pass-2 corpus, a
tracked Support's camps stacked by 20:00 has median 0, 70.7% zero, and p90 of 2.
An enemy side stacking 7–9 by 20:00 is therefore genuinely unusual — but that
distribution must be re-measured on ten-player data before any threshold is set.

---

## 7. What remains too causal or impossible

**Too causal (never ship):** "their stacks won them the game", "their vision
caught you", "you lost map control", "your team responded too slowly", "their
carry's BKB decided it", "your support should have dewarded".

**Still impossible:** hero movement and rotations (movement stream prohibited),
presence in a fight without credit, arrival/reaction time, what anyone could
see, smoke usage beyond provider labels, cooldown/mana state, courier
behaviour, communication, intent.

**Available but untrusted until validated:** death/kill provider flags,
map-region interpretation of coordinates, Roshan timing, `timeDead` exact
meaning with buyback, tower `attacker` null cases.

---

## 8. Validation plan before any card ships

A Pass-3 validation corpus, not a product launch:

| Step | Scope | Cost |
|---|---|---|
| Collect Operation A for a stratified sample | ~2,000 parsed matches across Standard/Turbo, all five positions, three patches | ~250 requests |
| Collect Operation B for fresh matches | ~100 matches within days of play; plus ages 1, 3, 7, 14, 30 days to measure the playback window | ~150 requests |
| Coverage | Null rates per field per player; parsed availability for ten-player detail | offline |
| Semantics | `campStack` checkpoint alignment for all players; ward `type` mapping for all players; `timeDead` vs respawn formula and buyback; death `attacker` null cases; coordinate grid via fixed-position structures (tower deaths) and ward hotspots; `ancientLocation`/`bountyGold` totals vs gold; `goldEvents` reason enum; tower `attacker` | offline |
| Distributions | Enemy-team stacks @20, observers, dewards, lane opponent CS@10 by bucket and position; minimum meaningful differences | offline |
| Card rates | How often each §5 card fires under the gates; hand-read 50 recaps | offline |

The Pass-2 lessons apply unchanged: verify array semantics by measurement, never
by field name; fail closed on unknown enums; keep raw, normalized, and canonical
layers separate; record the operation digest in every row.

---

## 9. Adversarial pass

| Risk | How it could mislead | Mitigation |
|---|---|---|
| Ten-match probe | Availability might differ for older, low-parse, or Turbo-heavy players | §8 coverage corpus before design lock |
| Team comparisons read as blame | "Their supports stacked 9, yours 1" can shame teammates | Team aggregates only; no allied individual callouts; neutral copy |
| Duration bias | Long games accumulate more stacks, wards, dewards | Checkpoint (@20:00) or per-10-minute rates; one-sided games flagged |
| Stomp bias | Winning teams ward and deward more because they control the map | Show as context; never as explanation; opponent history compares like with like only loosely — document |
| Heuristic fights | Clusters miss 1–2-death skirmishes and merge overlaps | Name the rule ("fights with 3+ deaths") in copy detail |
| Provider labels | `isWardWalkThrough` true on 58% of deaths suggests a definition we don't know | Excluded |
| Coordinates | Grid origin/scale unvalidated; region model is ours | P2 until validated |
| Playback absence | Cards silently depend on fresh-only data | Operation B cards are optional; Operation A fallback or omission |
| Privacy creep | Other players' histories could be assembled across matches | No other-player identity is ever selected or stored |
| Cost growth | ~7–8× bytes per match | Trim other-player arrays not used by any card |
| Win/loss leakage | Enemy advantage metrics restate the result (winners have more wards, stacks, towers) | Prefer early checkpoints (@10/@20) and lane-opponent facts; flag cards whose values track the result |

---

## 10. Impact on the companion feasibility document

| Earlier statement | Corrected |
|---|---|
| "The other nine players exist only as final-scoreboard scalars" | That is what the current *queries* request. STRATZ serves full ten-player `stats` in 8-match batches |
| "*The enemy support stacked* is impossible today" | Possible with Operation A; blocked only on collection, validation, and policy |
| "Full stats for all ten players was rejected at complexity 6,159,595" | Misattributed: that number was the full introspection query; ten-player stats batch of 8 succeeded |
| Time dead: "no respawn intervals" | `deathEvents.timeDead` exists on the stats type; needs validation |
| Positions: "none usable" | Death, kill, assist, and ward coordinates exist; movement remains unavailable |
| Mid/Offlane lane advantage metrics blocked on opponent trajectories | Unblocked by Operation A |
| Roshan "not collected" | Still no usable Roshan events; gold reason `ROSHAN` is a fresh-only lead to validate |

---

## 11. Recommended next steps

1. **Owner decisions** in §4.4 (ten-player retention without identity; narrow
   playback exception; provider-flag quarantine).
2. **Version Operation A** in `services/api/app/stratz/queries.py` with a
   fail-closed normalizer and ten-player canonical schema.
3. **Run the §8 validation corpus** (~400 requests).
4. **Add three "their side" cards to V1** once validated: team stacks @20:00
   vs yours, vision placed/cleared per team, and lane opponent benchmark — plus
   time dead and who killed you.
5. Keep Operation B (fresh playback) as a later enrichment for ward fate and
   time-resolved farm source.
