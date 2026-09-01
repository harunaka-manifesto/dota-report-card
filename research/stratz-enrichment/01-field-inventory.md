# STRATZ verified field inventory

> **Superseding operational note — 2026-09-01:** **AUTOMATED STRATZ ACCESS
> BLOCKER = RESOLVED.** The 403 observations in §0 remain historical evidence
> from 2026-08-27. This inventory is a specimen record, not a current access
> test; the offline recovery/gap audit makes no provider requests.

**Status:** PARTIAL. Everything below is verified from live payloads captured
2026-08-27 or from live introspection. Nothing here is remembered or inferred
from field names.

**Provenance.** Payloads live in `.local/stratz-probe/enrichment/` (gitignored).
Every number is reproduced by `.local/stratz-probe/enrichment/analyze.py`.

| artifact | operation | what it is |
|---|---|---|
| `A1.json` | `A1_Introspection` | **REJECTED** — see complexity limit below |
| `A1b.json` | `A1b_NarrowIntrospection` | live introspection of 7 core types |
| `A2.json` | `A2_ParsedCore` | match 8867297163, POSITION_3 CORE, 3586s, RANKED, parsed |
| `A3.json` | `A3_ParsedSupport` | match 8900462650, POSITION_5 HARD_SUPPORT, 3444s, RANKED, parsed |
| `A4.json` | `A4_Unparsed` | match 8936709179, TURBO, `parsedDateTime: null` |
| `A5.json` | `A5_MatchContext` | match-level context for 8867297163 |
| `A6.json` | `A6_AllPlayers` | all ten slots of 8867297163 |
| `A7.json` | `A7_Playback` | playback for one player of 8867297163 |
| `specimen/q3.json` | `Q3_ParityPage` | 100-match history page, account 193875165, 61.1 days |

Sample size for every coverage number is **one account, one 100-match page,
61.1 days, one patch**. That is enough to establish *shape and semantics*. It
is not enough to establish *population coverage*. Treat every percentage below
as "observed on this specimen", never as a platform constant.

---

## 0. Operational limits discovered

**Query complexity ceiling — new, load-bearing, previously unmeasured.**

A standard full introspection query was rejected:

```
Query is too complex to execute. Complexity is 6159595;
maximum allowed on this endpoint is 310000.
```

This is a hard per-request budget and it constrains parsed-data acquisition
design directly: a request's cost is not just rows returned but selection-set
breadth × list cardinality. A2 (one player, full `stats`, one match) succeeded;
A1b (7 types, shallow introspection) succeeded. **Any per-match parsed query
must be complexity-budgeted, and the budget has to be measured, not assumed.**

**Historical access observation (2026-08-27).** `api.stratz.com` returned HTTP
403 from both the cloud sandbox and the device shell. Of the three checked-in
probe runs under `.local/stratz-probe/runs/`, only
`193875165-20260827T011356Z` made real requests: 8 requests, **all HTTP 403**,
including introspection. The other two runs made zero physical requests and
their 76-byte `introspection.json` files contain a `dry-run` stub, not an error
response. The 2026-09-01 superseding note records the blocker resolved for
future direct server-side access; this inventory remains a historical specimen
record, not a current access test. Licensing and population coverage remain
separate unresolved corpus decisions.

---

## 1. Classification of every verified path

Four classes, per the brief: **META** basic match metadata · **PLAYER** player
metadata from the scoreboard · **REPLAY** replay-derived, requires
`parsedDateTime` · **PROPRIETARY** computed STRATZ analytics.

### 1.1 `MatchType` — 56 fields (introspected, `A1b`)

| path | type | class | coverage | notes |
|---|---|---|---|---|
| `id` | `Long` | META | 100% | |
| `didRadiantWin` | `Boolean` | META | 100% | |
| `durationSeconds` | `Int` | META | 100% | |
| `startDateTime` / `endDateTime` | `Long` | META | 100% | |
| `lobbyType` | `LobbyTypeEnum` | META | 100% | observed `RANKED`, `UNRANKED` |
| `gameMode` | `GameModeEnumType` | META | 100% | observed `ALL_PICK_RANKED`, `TURBO` |
| `gameVersionId` | `Short` | META | **100%** | vs ~2.5% patch on OpenDota. See §3. |
| `firstBloodTime` | `Int` | META | observed | **can be negative** (`-15` in A5) |
| `towerStatusRadiant/Dire` | `Int` | META | observed | bitmask |
| `barracksStatusRadiant/Dire` | `Short` | META | observed | bitmask |
| `clusterId` / `regionId` | `Int`/`Byte` | META | requested, **0%** (null on all 100 specimen rows) | non-null in A5 (`152`, `5`) — so the nulls are a history-projection behaviour, not absence |
| `isStats` | `Boolean` | META | requested, **0%** in specimen | `false` in A5 **on a parsed match** |
| `leagueId` | `Int` | META | 0% | |
| `parsedDateTime` | `Long` | META | **91%** | the replay gate |
| `radiantKills` / `direKills` | `[Int]` | REPLAY | A5 | **see §2.3 — not what the name says** |
| `radiantNetworthLeads` | `[Int]` | REPLAY | A5 | per-minute net worth lead |
| `radiantExperienceLeads` | `[Int]` | REPLAY | A5 | per-minute XP lead |
| `bottomLaneOutcome` / `midLaneOutcome` / `topLaneOutcome` | `LaneOutcomeEnums` | REPLAY | A5 | observed `TIE`, `RADIANT_VICTORY` |
| `laneReport` | `MatchStatsLaneReportType` | REPLAY | **not fetched** | shape unknown → Pack B |
| `towerDeaths` | `[MatchStatsTowerDeathType]` | REPLAY | **not fetched** | shape unknown → Pack B |
| `pickBans` | `[MatchStatsPickBanType]` | REPLAY | **not fetched** | shape unknown → Pack B |
| `chatEvents` | `[MatchStatsChatEventType]` | REPLAY | **not fetched** | privacy-sensitive; see §5 |
| `playbackData` | `MatchPlaybackDataType` | REPLAY | A7 | see §4 |
| `analysisOutcome` | `MatchAnalysisOutcomeType` | **PROPRIETARY** | A5 | `"COMEBACK"` — model output |
| `predictedOutcomeWeight` | `Byte` | **PROPRIETARY** | — | model output |
| `winRates` / `predictedWinRates` | `[Decimal]` | **PROPRIETARY** | — | per-minute model win probability |
| `averageImp` | `Short` | **PROPRIETARY** | — | |
| `actualRank` / `averageRank` / `rank` / `bracket` | | **FORBIDDEN by policy** | — | Not literal members of `FORBIDDEN_ANALYTICAL_FIELDS` (that frozenset holds OpenDota snake_case names: `average_rank`, `rank_tier`, `rank`, `mmr`, `skill`, `skill_bracket`). These are the STRATZ equivalents and the `rank_or_mmr_used: False` audit assertion covers them. |
| `replaySalt`, `sequenceNum`, `didRequestDownload`, `statsDateTime`, `numHumanPlayers`, `tournamentId`, `tournamentRound`, `league*`, `*TeamId`, `series*`, `spectators`, `towerStatus` | | META | — | not relevant to this research |

### 1.2 `MatchPlayerType` — 55 fields (introspected, `A1b`)

| path | type | class | coverage | notes |
|---|---|---|---|---|
| `playerSlot`, `isRadiant`, `isVictory`, `heroId` | | PLAYER | 100% | |
| `kills`, `deaths`, `assists` | `Byte` | PLAYER | 100% | |
| `numLastHits`, `numDenies` | `Short` | PLAYER | A2/A3 | |
| `goldPerMinute`, `experiencePerMinute` | `Short` | PLAYER | A2/A3 | **scalar ≠ the array of the same name** (§2.2) |
| `networth`, `gold`, `goldSpent`, `level` | | PLAYER | A2 | |
| `heroDamage`, `towerDamage`, `heroHealing` | `Int` | PLAYER | A2/A3 | |
| `leaverStatus` | `LeaverStatusEnum` | PLAYER | 100% | observed `NONE` (92), `DISCONNECTED` (8). Full enum → Pack B |
| `partyId` | `Byte` | PLAYER | **8%** | null-means-solo vs null-means-unknown is **unestablished** |
| `isRandom` | `Boolean` | PLAYER | 0% in specimen | |
| `variant` | `Byte` | PLAYER | 100% | `0` throughout — facet, effectively no variance here |
| `lane` | `MatchLaneType` | REPLAY | **93%** | `SAFE_LANE`, `MID_LANE`, `OFF_LANE`, `JUNGLE` |
| `position` | `MatchPlayerPositionType` | REPLAY | **91%** | `POSITION_1`..`POSITION_5` |
| `role` | `MatchPlayerRoleType` | REPLAY | **93%** | `CORE`, `LIGHT_SUPPORT`, `HARD_SUPPORT` |
| `roleBasic` | `MatchPlayerRoleType` | **REJECTED** | 100% | **see §2.4 — rejected twice over** |
| `invisibleSeconds` | `Int` | PLAYER | A2/A3 | `1577` core vs `0` support; **semantics unestablished** |
| `item0Id`..`item5Id`, `backpack0..2Id`, `neutral0Id` | `Short` | PLAYER | A2 | *final* inventory only |
| `imp`, `award`, `streakPrediction`, `behavior` | | **PROPRIETARY** | — | opaque |
| `intentionalFeeding` | `Boolean` | **REJECT** | — | a moral judgment, not a behaviour |
| `stats` | `MatchPlayerStatsType` | REPLAY | — | §2 |
| `playbackData` | `MatchPlayerPlaybackDataType` | REPLAY | — | §4 |
| `abilities` | `[PlayerAbilityType]` | ? | **not fetched** | takes a `gameVerionId` arg (sic — typo is in the schema) |
| `heroAverage`, `additionalUnit`, `dotaPlus`, `dotaPlusHeroXp` | | — | not fetched | |

### 1.3 `MatchPlayerStatsType` — 37 fields (introspected, `A1b`)

**Fetched and confirmed populated** (A2 core / A3 support):
`networthPerMinute`, `goldPerMinute`, `experiencePerMinute`, `lastHitsPerMinute`,
`deniesPerMinute`, `heroDamagePerMinute`, `towerDamagePerMinute`, `healPerMinute`,
`actionsPerMinute`, `heroDamageReceivedPerMinute`, `tripsFountainPerMinute`,
`campStack`, `level`, `killEvents`, `deathEvents`, `assistEvents`,
`itemPurchases`, `wards`, `runes`.

**Exists in schema, shape unknown, NOT fetched** — these are the remaining
enrichment surface and every one is `BLOCKED — needs payload` (Pack B `B1`):
`towerDamageReport`, `courierKills`, `itemUsed`, `allTalks`, `chatWheels`,
`actionReport`, `locationReport`, `farmDistributionReport`, `abilityCastReport`,
`heroDamageReport`, `inventoryReport`, `matchPlayerBuffEvent`,
`spiritBearInventoryReport`, `wardDestruction`.

`impPerMinute` — **PROPRIETARY**, not fetched, not eligible.

### 1.4 `PlayerMatchesRequestType` — the acquisition lever

Introspection revealed server-side filters that materially change corpus and
report-time cost, and one that is analytically dangerous:

- `isParsed: Boolean` — **lets parsed-availability bias be measured rather than
  assumed** (Pack B `B4`). Also a trap: filtering to `isParsed: true` at
  acquisition time silently conditions the whole analysis on a non-random subset.
- `gameModeIds`, `lobbyTypeIds`, `heroIds`, `laneIds`, `roleIds`,
  `positionIds`, `gameVersionIds`, `regionIds`, `isParty`, `isVictory`,
  `isRadiant`, `withFriendSteamAccountIds`, `withEnemySteamAccountIds`,
  `minGameVersionId`/`maxGameVersionId`, `orderBy`, `after`/`before`.
- `rankIds`, `bracketIds`, `minImp`, `maxImp` — **must never be used.** The V6.1
  audit asserts `rank_or_mmr_used: False`.

`PlayerType` additionally exposes `matchesGroupBy`, `performance`,
`heroesPerformance`, `heroStreaks`, `activity`. These are precomputed
aggregates; they are a **cost lever worth investigating** and simultaneously a
**provenance risk** — an aggregate we did not compute is an aggregate we cannot
version. Not evaluated here.

---

## 2. Semantics established from data

### 2.1 Array length

Measured on A2 (3586s) and A3 (3444s):

```
len(per-minute array)   == floor(durationSeconds / 60)          # 59, 57
len(networthPerMinute)  == floor(durationSeconds / 60) + 1      # 60, 58
len(match-level array)  == floor(durationSeconds / 60) + 2      # 61, 61
len(stats.level)        == 30 in both samples                   # see BLOCKED
```

This fully explains the brief's unexplained "`networthPerMinute` had 26 entries;
`goldPerMinute` had 25" on a 25-minute match. `networthPerMinute` carries a
t=0 sample; the others do not. **Never assume index alignment across arrays** —
but the offsets are now known constants, not mysteries.

`len(stats.level) == 30` in both samples. A2's `players[0].level` scalar is
`30`; **A3 did not request that scalar and returns `null` for it**, so "both
players reached level 30" is *not* established from these payloads — only that
one did. Either way, "length equals final level" and "length is always 30"
remain observationally identical on this evidence. Resolved by Pack B `B3`.
Marked **BLOCKED**.

### 2.2 The `*PerMinute` arrays do not share a semantics

This is the single most dangerous field-level finding. Verified by summing each
array against its scalar counterpart:

| field | semantics | evidence |
|---|---|---|
| `lastHitsPerMinute` | **per-minute delta** | sum == `numLastHits` exactly (336, 359) |
| `deniesPerMinute` | per-minute delta | sum == `numDenies` exactly (7, 3) |
| `towerDamagePerMinute` | per-minute delta | sum == `towerDamage` exactly (615, 559) |
| `healPerMinute` | per-minute delta | sum == `heroHealing` exactly (0, 767) |
| `heroDamagePerMinute` | per-minute delta | A3 sum == `heroDamage` exactly (63354); A2 short by the unbucketed tail |
| `experiencePerMinute` | **XP gained in that minute** — not a rate | spiky with interior zeros; scalar `experiencePerMinute` (1185) is the real XPM |
| `actionsPerMinute`, `tripsFountainPerMinute` | per-minute delta | non-monotonic counters |
| `campStack` | **UNDETERMINED** | sums to 0 and is monotonic in both samples — the payloads cannot distinguish delta from cumulative. Do not classify it. |
| `goldPerMinute` | **running average GPM** | converges to the scalar (620 → 631); sum is meaningless |
| `networthPerMinute` | **cumulative level** | last ≈ `networth`; can *decrease* (death/buyback) |
| `heroDamageReceivedPerMinute` | **cumulative level** | strictly monotonic |

Four different meanings under one naming convention. Any trajectory feature
that treats them uniformly is silently wrong, and the error is invisible
because every array is `[Int]` of plausible length.

`stats.level` is **level-up timestamps in seconds**, not levels. First value is
negative (`-89`) — pre-horn. Strictly ascending.

### 2.3 `radiantKills` / `direKills` count opposing hero *deaths*

Cross-checked against the ten-player scoreboard (A6):

```
sum(radiantKills) = 75 == dire   total deaths (75); radiant scoreboard kills = 75
sum(direKills)    = 68 == radiant total deaths (68); dire   scoreboard kills = 67
```

The one-kill gap on the Dire side is a radiant hero death credited to no player
(tower, creep, neutral, or a denial). **The arrays count deaths on the opposing
side, not scoreboard-credited kills.** Getting this backwards silently corrupts
any participation denominator by a few percent — invisibly, and in a direction
that varies by match.

### 2.4 `roleBasic` is rejected twice over

The brief rejects `roleBasic` because it returns `"CORE"` on unparsed matches
where `lane`/`position`/`role` are all null. A4 confirms that. A6 adds a second,
independent reason: on a fully parsed match, **both hard supports come back
`roleBasic: LIGHT_SUPPORT`** while `role` correctly says `HARD_SUPPORT`. It is a
binary core/support collapse *and* a default. Its 100% coverage is the tell:
a field that is never null is not observing anything.

### 2.5 Unparsed degradation shape

`stats` on an unparsed match is **an object with every field `null`**, not
`stats: null`. Eligibility and coverage code must test per-field nullity.
A wrapper-presence check will report a field as available when it is not.

---

## 3. What changes without any formula changing

Two coverage facts are analytical changes in their own right.

**`gameVersionId` at 100% vs ~2.5%.** `patch` is a dimension in five of the six
`BASELINE_HIERARCHY` levels (`patch+hero+lane`, `patch+hero_function+lane`,
`patch+hero`, `patch+lane`, `patch`). Under OpenDota, patch is almost never
present, so almost every match falls through to the `overall` cell — meaning
today's "context-adjusted" Elements are, in practice, a **global mean
subtraction**. With patch and lane both populated, the top of the hierarchy
becomes reachable for the first time. `involvement`, `finishing` and
`death_exposure` would change their values, zones and confidence without a
single line of formula changing.

**Eligible-population drift.** On the specimen, `breadth` computed over all 100
matches is **12.35** effective heroes; over the 49 ranked-eligible matches it is
**10.60**. A 1.75-effective-hero swing from the eligible-population definition
alone. Any change to mode eligibility is an Element-value change.

---

## 4. Playback cost

A7 = **472.9 KB for one player**, dominated by 2271 `playerUpdatePositionEvents`
at a mean 1.61s gap. Ten players ≈ **4.6 MB per match**; at ~293 eligible
matches/year, ~1.3 GB per player-year for full-team playback.

**This is a floor, not the playback cost.** `MatchPlayerPlaybackDataType` has
**25** fields (A1b); A7 requested **7**. Eighteen event lists —
`heroDamageEvents`, `inventoryEvents`, `playerUpdateGoldEvents`,
`playerUpdateHealthEvents`, `playerUpdateBattleEvents`, `abilityUsedEvents`,
`experienceEvents` and others — were never requested. The real full-playback
figure is larger by an unmeasured factor, which only strengthens the conclusion
below.

Within the 7 fields fetched: `csEvents` (336) duplicates `numLastHits`;
`purchaseEvents` (54) duplicates `stats.itemPurchases`; `killEvents`/`deathEvents`
duplicate the `stats` versions. **Of what was fetched, the unique value is
`playerUpdatePositionEvents`, `abilityLearnEvents` (23, with `abilityId`) and
`buyBackEvents` (1)** — a statement about 7 fields, not about all 25.

`match.playbackData.roshanEvents` returned **length 0** — A7 does not carry
`durationSeconds`, but it is the same match as A2/A5, which give 3586s (59.8 min).
That is not credible. Flag the field as unreliable; do not read it as "no
Roshan was killed".

---

## 5. Semantics unestablished — the explicit list

No candidate may be founded on any of these until resolved.

| path | why it is unestablished |
|---|---|
| `stats.level` length rule | "== final level" vs "always 30" not separated (Pack B `B3`) |
| `invisibleSeconds` | 1577 on a POSITION_3 Earthshaker, 0 on a support. Meaning unknown |
| `partyId` 8% coverage | null-means-solo vs null-means-unknown not distinguished |
| `isStats` | `false` on a *parsed* match — relationship to `parsedDateTime` unknown |
| `variant` | `0` throughout; facet semantics and coverage untested |
| `wards.type` | `0` and `1` observed; observer/sentry mapping not confirmed |
| `wards.positionX/Y` | observed x ∈ [70, 170], y ∈ [68, 172] across 28 wards; grid origin and scale not confirmed |
| `runes.rune` | `BOUNTY` (7), `WISDOM` (2), `HASTE` (2), `INVISIBILITY` (1) observed across A2+A3; full enum unknown (Pack B `B1`) |
| `leaverStatus` enum | `NONE`, `DISCONNECTED` observed; full enum and the mapping onto V6.1's `0..5` unknown |
| `firstBloodTime` negative | pre-horn semantics plausible but unconfirmed |
| `match.playbackData.roshanEvents` | returned empty on a long game; suspected unreliable |
| all seven `*Report` objects | never fetched; shapes unknown |
| `itemUsed`, `wardDestruction`, `matchPlayerBuffEvent`, `courierKills`, `allTalks`, `chatWheels` | never fetched; shapes unknown |
| `abilities(gameVerionId:)` | never fetched; required-arg semantics unknown |
| `laneReport`, `towerDeaths`, `pickBans`, `chatEvents` | never fetched |
| `matchesGroupBy` / `performance` aggregates | never fetched; provenance unversionable |

## 6. Rejected as evidence, permanently

`imp`, `impPerMinute`, `averageImp`, `analysisOutcome`, `predictedOutcomeWeight`,
`winRates`, `predictedWinRates`, `streakPrediction`, `award`, `behavior` —
proprietary model outputs. "STRATZ says the player was good" is not a
behavioural observation and importing it makes our findings a function of
someone else's unversioned model.

`analysisOutcome` deserves a specific note: it returned `"COMEBACK"` on a match
whose `radiantNetworthLeads` swings from **−6023 to +13944 in the final two
minutes**. The classification is defensible — and *reconstructible from the raw
lead curve we already have*. That is the argument for rejecting it: we can
define comeback ourselves, version the definition, and state it. Using theirs
buys nothing and costs provenance.

`actualRank`, `averageRank`, `rank`, `bracket` (`MatchType`) and
`behaviorScore`, `ranks`, `leaderboardRanks` (`PlayerType`) — forbidden
analytical inputs by policy, unchanged. (The brief also names `seasonRank`; no
field of that name appears in any type introspected by `A1b`. The nearest real
field is `PlayerType.ranks`.)

`roleBasic` — rejected on sight, per §2.4.

`intentionalFeeding` — a moral judgment about a player, not a behaviour. It has
no place in this product at any tier.
