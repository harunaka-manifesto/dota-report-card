# Pass-2 field completeness audit — 2026-09-04

The owner asked whether the pass-2 collection can be run once and never redone.
This audits the proposed query against **every field the provider exposes** on
the three relevant types, using the introspection already captured in
`.local/stratz-probe/enrichment/A1b.json`. No provider call was made.

**Verdict: do not start collection yet.** The query as first written was
missing fields that three of the report's strongest Findings depend on, and a
further sixteen fields cannot be requested at all until one introspection call
resolves their shape.

```text
PHASE: V7_PASS2_FIELD_COMPLETENESS_AUDIT
STATUS: BLOCKED PENDING ONE PROBE
NEW STRATZ CALLS THIS PHASE: 0
```

## 1. Gaps found against the report's own requirements

Three of these serve Findings this project has already committed to.

| field | type | why it matters | consequence of omitting |
|---|---|---|---|
| `stats.itemUsed` | player | *did you use the item*, not just buy it | "Do you use your spike, or just buy it?" was going to be inferred from kill events near a purchase. Actual usage events make it direct. |
| `match.towerDeaths` | match | tower kills with timings | "Do you convert a won fight into a map?" — the single strongest Finding proposed — was going to lean on `towerDamagePerMinute` as a proxy. Real tower-death timings are the actual measurement. |
| `player.partyId` | player | solo or stacked | Both a Finding in its own right (*do you play better solo?*) and a confounder the tournament already flagged for the post-loss family. Missing it means post-loss behaviour stays partly unexplained. |
| `stats.level` | player | per-minute level curve | Level timing is half of laning, and XP-per-minute alone does not give it. |
| `stats.wardDestruction` | player | dewarding | Support Findings currently only measure placing vision, not taking it away. |
| `match.pickBans` | match | draft order | Draft position and first-pick behaviour; nothing else exposes it. |
| `match.laneReport` | match | per-lane summary | Direct laning evidence rather than reconstruction. |
| `stats.farmDistributionReport` | player | where farm comes from | Separates "farms lane creeps" from "sits in the jungle", which is a real and coachable difference. |
| `stats.tripsFountainPerMinute` | player | trips to base | The TP-discipline Finding was going to rest on item purchases alone. |
| `match.numHumanPlayers`, `match.isStats` | match | data quality | Detects bot-filled and unrecorded games. Cheap, and their absence silently pollutes every denominator. |

## 2. What has been added already

These have known shapes — they are scalars or `[Int]` — so they were added
directly and need no discovery. `GetDeepMatchBatch` is now **v2.1.0**,
document digest `dc28fb5c7b01faa7…`.

```text
match    statsDateTime, isStats, numHumanPlayers
player   partyId, invisibleSeconds
stats    level, actionsPerMinute, tripsFountainPerMinute
```

`actionsPerMinute` is included but **flagged**: click rate correlates with
skill, and while it is a legitimate behavioural descriptor it must go on the
red-team's hidden-skill-proxy watchlist rather than into a Finding unexamined.

## 3. What still cannot be requested, and why

Sixteen fields return object or list types whose selectable fields are unknown.
GraphQL will not accept a selection set against an unknown type, and a guessed
one fails on the first call of a multi-day collection.

| field | returns |
|---|---|
| `match.towerDeaths` | `MatchStatsTowerDeathType` |
| `match.pickBans` | `MatchStatsPickBanType` |
| `match.laneReport` | `MatchStatsLaneReportType` |
| `match.towerStatus` | `MatchStatsTowerReportType` |
| `player.abilities` | `PlayerAbilityType` |
| `stats.itemUsed` | `MatchPlayerStatsItemUsedEventType` |
| `stats.wardDestruction` | `MatchPlayerWardDestuctionObjectType` |
| `stats.farmDistributionReport` | `MatchPlayerStatsFarmDistributionReportType` |
| `stats.heroDamageReport` | `MatchPlayerStatsHeroDamageReportType` |
| `stats.towerDamageReport` | `MatchPlayerStatsTowerDamageReportType` |
| `stats.inventoryReport` | `MatchPlayerInventoryType` |
| `stats.actionReport` | `MatchPlayerStatsActionReportType` |
| `stats.abilityCastReport` | `MatchPlayerStatsAbilityCastReportType` |
| `stats.locationReport` | `MatchPlayerStatsLocationReportType` |
| `stats.matchPlayerBuffEvent` | `MatchPlayerStatsBuffEventType` |
| `stats.courierKills` | `MatchPlayerStatsCourierKillEventType` |

`locationReport` being an object type also explains a latent bug: the original
probe requested it bare, which GraphQL would have rejected.

`V7Pass2TypeSentinel` resolves all sixteen in **one** introspection call, and
the probe now runs it before anything else.

## 4. Deliberately excluded, and staying excluded

```text
imp, impPerMinute, award, behavior, intentionalFeeding, streakPrediction
actualRank, averageRank, averageImp, rank, bracket
analysisOutcome, predictedOutcomeWeight, winRates, predictedWinRates
chatEvents, allTalks, chatWheels
playbackData (match and player), dotaPlus, dotaPlusHeroXp
steamAccount identity for players other than the sampled one
```

`heroAverage` is excluded for a subtler reason: it is provider-computed
benchmark data rather than an observation of the player, and the project
computes its own reference distributions from the corpus. `replaySalt`,
league, team, series and tournament fields are excluded as irrelevant to pubs.

## 5. Answer to the question

> Can this run be done once and never redone?

Not with the query as it stood. With the v2.1.0 additions plus whatever the
type sentinel unlocks, the answer becomes yes **for everything the report
narrative and the eleven proposed Findings require** — that mapping is checked
field by field in
`docs/evidence/v7-report-narrative-and-data-requirements-2026-09-04.md`.

Two honest limits remain, and neither is fixable by collecting harder:

1. **Playback stays excluded.** Fine-grained positional movement, and anything
   derived from the replay stream, is a prohibited surface and is also
   prohibitively large. If a future Finding needs true movement data, that is a
   new decision and a new collection, not an oversight in this one.
2. **The cohort stays frozen.** Pass 2 deepens the *existing* 300 DISCOVERY
   accounts. Extending to `CANDIDATE_TEST` for confirmation is a separate,
   already-planned run. Reserved and sealed partitions stay untouched.

## 6. What to run

One probe, which now costs about five calls:

```bash
uv run python scripts/stratz_v7_pass2_probe.py --dotenv .env
```

It resolves its own target from the frozen cohort, runs the type sentinel,
reports the shape of all sixteen unresolved types, walks the batch ladder on
v2.1.0, and prints the projected collection cost. The query is then finalised
against measured shapes and measured complexity rather than against hope, and
collection runs once.
