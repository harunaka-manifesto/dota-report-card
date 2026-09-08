# BLOCKED list and prepared operations

> **Superseding operational note — 2026-09-01:** **AUTOMATED STRATZ ACCESS
> BLOCKER = RESOLVED.** The access failures referenced by this research remain
> historical evidence from 2026-08-27; direct server-side GraphQL access is now
> available for the V7 provider foundation.

Every empirical question this research could not answer, with the exact
operation that would resolve it. Ordered by how much depends on the answer.

Prepared operations live in:

- `.local/stratz-probe/enrichment/pack-a.graphql` — **run, results captured**
- `.local/stratz-probe/enrichment/pack-b.graphql` — written, **not yet run**
- `.local/stratz-probe/enrichment/pack-c.graphql` — written below, **not yet run**

---

## Tier 0 — decides whether the parsed tier exists

### C1 · Can parsed matches be batched into one request?

**Why it matters more than anything else here.** At one request per match,
per-match parsed evidence costs ~299 requests per player-year against the
brief's stated 10,000/day ceiling — roughly 33 reports per day, versus ~1,600 on
the history tier. (That ceiling is quoted from the brief, not measured here.) That difference is the whole argument for the two-corpus split in
`04-corpus-lineage-roadmap.md`. If `PlayerMatchesRequestType.matchIds: [Long]`
returns full `stats` for N matches in one response, the parsed tier's cost falls
by roughly N× and Tier 2 becomes affordable at product scale.

The binding constraint is the measured complexity ceiling of **310,000**
(discovered when `A1_Introspection` was rejected at 6,159,595). `C1` walks the
batch size until it trips.

**Status: BLOCKED — needs payload.**

### C2 · Does `matchesGroupBy` return usable aggregates?

`PlayerType.matchesGroupBy(request:)` exists and was never fetched. If it
aggregates server-side it is a large cost lever. It is also a **provenance
risk**: an aggregate we did not compute is an aggregate we cannot version, and
`docs/evidence-contract.md` requires methodology versioning on every public
Element. Worth measuring, probably not worth using.

**Status: BLOCKED — needs payload.** Query `C2` below.

---

## Tier 1 — needed before Tier 1 candidates can be implemented

### B1 · Shapes of the seven `*Report` objects and the unfetched event lists

`towerDamageReport`, `courierKills`, `itemUsed`, `allTalks`, `chatWheels`,
`actionReport`, `locationReport`, `farmDistributionReport`, `abilityCastReport`,
`heroDamageReport`, `inventoryReport`, `matchPlayerBuffEvent`,
`spiritBearInventoryReport`, `wardDestruction`, plus `laneReport`, `towerDeaths`,
`pickBans`, and all the playback sub-types.

Until these are introspected, roughly a third of the parsed surface is
un-queryable — not "probably empty", *un-queryable*, because a selection set
cannot be written without field names. Candidates 46 and 49 in the catalog are
blocked on this specifically.

**Status: BLOCKED — needs payload.** `pack-b.graphql` `B1_SubTypes`.

### B3 · The `stats.level` length rule

Both sampled matches ran ~58–60 minutes and both players finished at level 30,
so `len(stats.level) == final_level` and `len(stats.level) == 30` are
observationally identical in the data captured. The XP Timing candidate cannot
be specified until they separate.

**Status: BLOCKED — needs payload.** `pack-b.graphql` `B3_FindShortGames`.

### B4 · Parsed-availability selection bias, measured over a full year

The specimen gives Turbo 44/51 (86%) parsed and ranked 47/49 (96%) parsed on a
single 100-match page. That already contradicts the brief's stronger claim that
unparsed matches "skew Turbo", but 100 matches on one account is not a
measurement of a selection mechanism. `PlayerMatchesRequestType.isParsed`
(discovered in `A1b`) makes this directly countable over 365 days.

**Status: BLOCKED — needs payload.** `pack-b.graphql` `B4_ParsedCoverage`.

### Enum vocabularies, especially `LeaverStatusEnum` — **quantified**

`leaverStatus` was observed as `NONE` (92) and `DISCONNECTED` (8). V6.1 treats
integers `0..5` as valid and `{2,3,4,5}` as material abandons. **The mapping
from STRATZ's enum onto that integer contract is unknown.**

This is not a hypothetical. On the specimen the two readings differ by **4
matches**, and that propagates all the way through the plan:

| | `DISCONNECTED` → 1 | `DISCONNECTED` → 2..5 |
|---|---|---|
| eligible (100-match specimen) | 49 | 45 |
| support share | 20/49 (41%) | 20/45 (44%) |
| eligible / 365d | 293 | 269 |
| requests / player-year (parsed tier) | 299 | 275 |
| Corpus P (100 players) | ~29,300 | ~26,900 |

Every figure in this research uses the left column. Covered by `B1`'s `E`
fragment.

**Status: BLOCKED — needs payload.**

---

## Tier 2 — needed before Tier 2 candidates can be implemented

### The lane → side mapping

`bottomLaneOutcome` / `midLaneOutcome` / `topLaneOutcome` are map-side outcomes;
`players[].lane` is `SAFE_LANE` / `MID_LANE` / `OFF_LANE`. The mapping depends
on `isRadiant` (Radiant safe lane is bottom; Dire safe lane is top). **A sign
error inverts the Lane Outcome finding and would be invisible in aggregate.**
Requires a labelled set of matches where the mapping can be checked against
known outcomes — not a single query.

**Status: BLOCKED — needs corpus, not just a payload.**

### `laneReport` richness

Whether `laneReport` carries per-lane per-player detail (which would supersede
the three coarse enums) is unknown. `pack-b.graphql` `B2` is written but
deliberately commented out — it needs `B1`'s field names.

**Status: BLOCKED — needs `B1` first.**

---

## Tier 3 — semantics unestablished, no candidate may depend on these

Each now has a prepared operation (Pack C `C3`–`C5`) rather than only a note.

| unknown | resolved by |
|---|---|
| full `RuneTypeEnum`, `LeaverStatusEnum`, `MatchLaneType`, `MatchPlayerPositionType`, `MatchPlayerRoleType`, `LaneOutcomeEnums`, `MatchAnalysisOutcomeType` | Pack B `B1` (`E` fragment) |
| `wards.type` observer/sentry mapping; `positionX/Y` grid origin and scale | `C3` — a support match with many wards, cross-read against `match.playbackData.wardEvents` (whose type carries a team/entity field per `B1`) |
| `partyId` null semantics (solo vs unknown) | `C4` — same window with `isParty: true` and `isParty: false`; if the two counts partition the total, null means solo |
| `isStats` on a parsed match; `variant`; negative `firstBloodTime` | `C4` — a small multi-match projection carrying all three |
| `invisibleSeconds` | `C5` — the same field across a hero with no invisibility mechanic and one with; if the no-invisibility hero returns non-zero, the name is misleading |
| `match.playbackData.roshanEvents` reliability | `C5` — request it on three long matches; three empty results on 50+ minute games confirm the field is broken rather than merely empty |
| `abilities(gameVerionId:)` required-arg semantics | `C5` — pass the observed `gameVersionId` (182) |

---

## Not blocked — resolved by this research

For the record, so these are not re-opened:

- per-minute array lengths and their four distinct semantics — **resolved**, §2.1–2.2
- `stats.level` as level-up timestamps — **resolved**, §2.2
- `radiantKills`/`direKills` as opposing hero deaths — **resolved**, §2.3
- `roleBasic` unusability — **resolved twice over**, §2.4
- unparsed degradation shape (`stats` = object of nulls) — **resolved**, §2.5
- playback cost — **resolved**, §4 (473 KB/player/match)
- query complexity ceiling (310,000) — **resolved**
- role coverage and the role vocabulary gap — **resolved**, reassessment §0.1
- the 128-signal catalog being generated rather than designed — **resolved**, §0.2

---

## Prepared operations — Pack C

Written to `.local/stratz-probe/enrichment/pack-c.graphql`.

```graphql
# ============================================================================
# C1 — PARSED BATCHING CEILING     [save as c1-batch-<N>.json, one file per alias]
# ----------------------------------------------------------------------------
# THE question. Run the aliases one at a time by deleting the others, smallest
# first, and record for each: (a) did it return, (b) did it error with
# COMPLEXITY, (c) how many matches came back with non-null stats.
#
# The answer converts directly into the parsed tier's cost:
#   requests per player-year = ceil(269 / largest_working_batch)
#
# Match ids are real, from the specimen, all parsed and all ALL_PICK_RANKED.
# ============================================================================
query C1_Batch2 {
  player(steamAccountId: 193875165) {
    matches(request: { matchIds: [8867297163, 8900462650] }) {
      id
      durationSeconds
      players(steamAccountId: 193875165) {
        heroId position role lane
        stats {
          networthPerMinute
          lastHitsPerMinute
          killEvents { time }
          deathEvents { time }
          assistEvents { time }
          itemPurchases { time itemId }
        }
      }
    }
  }
}

# Then repeat with matchIds lists of length 5, 10, 25, 50, 100.
# If COMPLEXITY trips, halve the selection set (drop itemPurchases first,
# then the event lists) and re-walk — the tradeoff between batch size and
# selection breadth is itself the finding.

# ============================================================================
# C2 — SERVER-SIDE AGGREGATION           [save as c2-groupby.json]
# ----------------------------------------------------------------------------
# Does matchesGroupBy return usable aggregates, and at what granularity?
# If this errors on the groupBy argument shape, send me the error — the arg
# enum is not in A1b and B1 does not cover it either.
# ============================================================================
query C2_GroupBy {
  player(steamAccountId: 193875165) {
    matchesGroupBy(request: {
      startDateTime: 1756252800
      endDateTime: 1787788800
      take: 100
    }) {
      __typename
    }
  }
}

# ============================================================================
# C3 — WARD SEMANTICS                      [save as c3-wards.json]
# ----------------------------------------------------------------------------
# Match 8900462650 is the support game with 27 wards. Cross-reading the player's
# own ward list against the match-level ward event stream should reveal whether
# `type` is observer/sentry and what the coordinate grid is anchored to.
# Sub-fields on wardEvents come from B1 -- RUN B1 FIRST and I will fill them in.
# ============================================================================
query C3_WardSemantics {
  match(id: 8900462650) {
    id
    durationSeconds
    players(steamAccountId: 193875165) {
      position
      role
      stats { wards { time type positionX positionY } }
    }
  }
}

# ============================================================================
# C4 — PARTY NULL SEMANTICS + SMALL FIELD SWEEP   [save as c4-party.json]
# ----------------------------------------------------------------------------
# If allParty + allSolo == allMatches, then partyId null means SOLO and the 8%
# coverage figure is not a coverage problem at all -- it is 8 party games.
# If they do not partition, null means unknown and every party-context candidate
# stays rejected.
# ============================================================================
query C4_PartyAndFields {
  player(steamAccountId: 193875165) {
    allMatches: matches(request: {
      startDateTime: 1756252800 endDateTime: 1787788800 take: 100 skip: 0
    }) { id isStats players(steamAccountId: 193875165) { partyId variant } }
    allParty: matches(request: {
      startDateTime: 1756252800 endDateTime: 1787788800 isParty: true take: 100 skip: 0
    }) { id }
    allSolo: matches(request: {
      startDateTime: 1756252800 endDateTime: 1787788800 isParty: false take: 100 skip: 0
    }) { id }
  }
}

# ============================================================================
# C5 — invisibleSeconds, roshanEvents, abilities   [save as c5-misc.json]
# ----------------------------------------------------------------------------
# 8867297163 is hero 7 (Earthshaker -- no innate invisibility) and returned
# invisibleSeconds = 1577. If that is real the field does not mean what its name
# says. Three long matches also settle whether roshanEvents is simply broken.
# gameVersionId 182 is the observed value for the `abilities` required argument.
# ============================================================================
query C5_Misc {
  a: match(id: 8867297163) {
    durationSeconds
    playbackData { roshanEvents { time } }
    players(steamAccountId: 193875165) {
      heroId invisibleSeconds
      abilities(gameVerionId: 182) { __typename }
    }
  }
  b: match(id: 8900462650) {
    durationSeconds
    playbackData { roshanEvents { time } }
    players(steamAccountId: 193875165) { heroId invisibleSeconds }
  }
  c: match(id: 8921018460) {
    durationSeconds
    playbackData { roshanEvents { time } }
    players(steamAccountId: 193875165) { heroId invisibleSeconds }
  }
}
```

**Every one of these is a read. None of them collects a corpus, and none is
authorized to.**
