# V7 STRATZ offline specimen recovery and gap audit

Date: 2026-09-01
Task: offline specimen recovery, evidence audit, and future microprobe design
Status: complete without provider activity

## Scope and evidence boundary

This audit is strictly offline. It made zero STRATZ requests, zero OpenDota
requests, and no browser or authentication attempts. `STRATZ_TOKEN` was not
required. The recovered payloads are local research data and remain under the
ignored `.local/` tree.

The evidence labels used below are deliberately separate:

- `SEMANTICALLY_ESTABLISHED`: cross-field or cross-payload evidence supports
  the stated meaning for the captured specimen(s).
- `OBSERVED_ON_SPECIMEN_ONLY`: the shape or value was seen, but the sample does
  not establish population coverage or a platform-wide invariant.
- `LIKELY_BUT_UNVERIFIED`: the interpretation is useful as a probe hypothesis,
  but the captured fields do not settle it.
- `UNRESOLVED`: the payloads do not support a safe interpretation.

No conclusion below is based only on the committed synthetic fixture at
`tests/fixtures/stratz/get_player_history_page.json`. That fixture is useful
for unit tests and is explicitly not live STRATZ evidence.

## Recovery

The search covered the repository parent and every registered worktree. The
historical enrichment corpus was found in the existing ignored local corpus
and copied byte-for-byte into this worktree. The source location is not stored
in the manifest so private absolute paths are not committed.

Local recovery root:

```text
.local/corpora/stratz/v7-prep/
```

Local SHA-256 manifest:

```text
.local/corpora/stratz/v7-prep/recovery-manifest.json
```

The manifest records each artifact's source label, size, SHA-256, parse state,
inferred operation, provenance, and classification. It is ignored and is not
part of the commit.

| artifact | classification | inferred operation | bytes | JSON |
|---|---|---:|---:|---|
| `A1.json` | `LIVE_CAPTURE` | `A1_Introspection` | 329 | parses |
| `A1b.json` | `LIVE_CAPTURE` | `A1b_NarrowIntrospection` | 104,038 | parses |
| `A2.json` | `LIVE_CAPTURE` | `A2_ParsedCore` | 41,381 | parses |
| `A3.json` | `LIVE_CAPTURE` | `A3_ParsedSupport` | 51,053 | parses |
| `A4.json` | `LIVE_CAPTURE` | `A4_Unparsed` | 1,199 | parses |
| `A5.json` | `LIVE_CAPTURE` | `A5_MatchContext` | 5,971 | parses |
| `A6.json` | `LIVE_CAPTURE` | `A6_AllPlayers` | 6,965 | parses |
| `A7.json` | `LIVE_CAPTURE` | `A7_Playback` | 484,210 | parses |
| `q3.json` | `LIVE_CAPTURE` | `Q3_ParityPage` | 103,441 | parses |
| `analyze.py` | `DERIVED_ANALYSIS` | offline reproduction | 19,728 | n/a |
| `pack-a.graphql` | `UNKNOWN` | historical query pack A | 13,770 | n/a |
| `pack-b.graphql` | `UNKNOWN` | historical query pack B | 9,605 | n/a |
| `pack-c.graphql` | `UNKNOWN` | historical query pack C | 5,304 | n/a |

Recovery totals:

- historical response artifacts: 9;
- `LIVE_CAPTURE`: 9;
- `SANITIZED_FIXTURE`: 0 in the recovered set; the repository's committed
  synthetic history fixture is kept separate;
- `DRY_RUN_STUB`: 0 in the recovered set;
- `DERIVED_ANALYSIS`: 1;
- `UNKNOWN`: 3 historical query packs;
- provider-response bytes: 798,587;
- all recovered artifact bytes: 846,994.

All recovered response hashes were checked against their source files. The
recovered analyzer was run twice from the copied corpus. It completed with
exit code 0 and performed no network I/O.

## What the old payloads prove

### History and identity

The `q3.json` page is one captured 100-match page for one account, covering
about 61 days and one observed patch. On that page, the following fields were
present at the recorded rates:

| field/path | specimen observation | evidence label |
|---|---:|---|
| `player.matches[].id` | 100/100 | `SEMANTICALLY_ESTABLISHED` for identity shape; coverage is specimen-only |
| `startDateTime`, `endDateTime`, `durationSeconds` | 100/100 | `SEMANTICALLY_ESTABLISHED` for chronology shape; coverage is specimen-only |
| `players[].heroId` | 100/100 | `SEMANTICALLY_ESTABLISHED` for player hero identity; coverage is specimen-only |
| `players[].isRadiant`, `isVictory` | 100/100 | `SEMANTICALLY_ESTABLISHED` after cross-reading match/team fields |
| `gameVersionId` | 100/100, one observed value | `SEMANTICALLY_ESTABLISHED` as a native version ID; population and human-patch mapping are unresolved |
| `players[].position` | 91/100 | `SEMANTICALLY_ESTABLISHED` as a native position observation; coverage is specimen-only |
| `players[].role` | 93/100 | `SEMANTICALLY_ESTABLISHED` as a native role observation; coverage is specimen-only |
| `players[].lane` | 93/100 | `SEMANTICALLY_ESTABLISHED` as a native lane observation; side mapping is unresolved |
| `lobbyType`, `gameMode` | 100/100 | `SEMANTICALLY_ESTABLISHED` as native enum fields; full vocabulary is not established |
| `parsedDateTime` | 91/100 | `OBSERVED_ON_SPECIMEN_ONLY`; full-year parsed selection is unresolved |
| `leaverStatus` | 100/100; `NONE` and `DISCONNECTED` observed | `UNRESOLVED` for eligibility semantics and any legacy mapping |

The position, role, and lane fields are independent. The specimen contains
both `HARD_SUPPORT` with `SAFE_LANE` and `LIGHT_SUPPORT` with `OFF_LANE`; this
is not a safe basis for converting lane to a legacy role word. The old
`roleBasic` field is not a substitute: it defaults to `CORE` on the unparsed
specimen and collapses hard support to `LIGHT_SUPPORT` on the all-player
specimen.

The history page establishes feasibility, not coverage. It does not support a
platform-wide claim about role, patch, parsed availability, match rate, or
eligible population.

### Parsed resource trajectories

`A2.json` and `A3.json` are parsed matches for different native role
observations. The analyzer reproduced the following cross-checks:

| path | established observation | evidence label |
|---|---|---|
| `players[].stats.networthPerMinute` | one extra initial sample; cumulative resource level that can move down | `SEMANTICALLY_ESTABLISHED` on the two specimens |
| `players[].stats.experiencePerMinute` | minute XP gained, not the scalar XPM and not a rate despite the name | `SEMANTICALLY_ESTABLISHED` on the two specimens |
| `players[].stats.lastHitsPerMinute`, `deniesPerMinute` | per-minute deltas whose sums match the scalar totals | `SEMANTICALLY_ESTABLISHED` on the two specimens |
| `players[].stats.heroDamagePerMinute`, `towerDamagePerMinute`, `healPerMinute` | per-minute deltas; the hero-damage tail can be outside the sampled buckets | `SEMANTICALLY_ESTABLISHED` on the two specimens |
| `players[].stats.actionsPerMinute`, `tripsFountainPerMinute` | non-monotonic per-minute deltas | `SEMANTICALLY_ESTABLISHED` on the two specimens |
| `players[].stats.goldPerMinute` | running average converging toward the scalar GPM | `SEMANTICALLY_ESTABLISHED` on the two specimens |
| `players[].stats.heroDamageReceivedPerMinute` | cumulative level on both parsed specimens | `SEMANTICALLY_ESTABLISHED` on the two specimens |
| `players[].stats.level` | ascending level-up timestamps, including a pre-horn negative value | `SEMANTICALLY_ESTABLISHED` for timestamp shape; length rule remains `UNRESOLVED` |
| `players[].stats.campStack` | zero and monotonic in both samples | `UNRESOLVED`; delta and cumulative interpretations are indistinguishable |

The length rule is also established only at the observed shape level:

```text
ordinary per-minute arrays = floor(durationSeconds / 60)
networthPerMinute          = floor(durationSeconds / 60) + 1
match-level arrays         = floor(durationSeconds / 60) + 2
```

The two long matches both have a 30-entry level array, so “one entry per
level” and “always 30 entries” are not separated. This is not a blocker for a
first Lane Recovery input set based on net worth and minute XP, but it is a
real unresolved semantic gap for any level-timing feature.

For Lane Recovery, the existing specimens therefore already provide the
minimum raw ingredients for a feasibility prototype: a player's own net-worth
trajectory, a player's own XP-increment series, native hero, native role or
position, and a native game-version ID. They do not provide the expected
hero/role/patch trajectory, an eligibility population, or validated checkpoint
choices. Those are analytical re-estimation inputs and remain out of scope.

### Combat, death, and team context

The parsed specimens contain populated `killEvents { time }`,
`deathEvents { time }`, and `assistEvents { time }`. They also contain hero
damage given, cumulative hero damage received, and the match-level kill arrays.
This proves a useful capability boundary, not a Finding.

`A5.json` plus `A6.json` establish an important denominator semantic:
`radiantKills` and `direKills` count hero deaths on the opposing side, not
scoreboard-credited kills. The cross-check found the expected opposing-death
sums, including one death not credited to a player. A participation share can
therefore be computed with a real team-death denominator, but its role and
hero fairness still require a population.

The same A5 payload contains `radiantNetworthLeads` and
`radiantExperienceLeads` as match-level arrays. Their `floor(duration / 60) + 2`
shape is `SEMANTICALLY_ESTABLISHED` for the captured match context. They are
team lead curves, not a substitute for the player's own P0 resource trajectory.

`A6.json` also proves that all ten player rows and their native hero, side,
role, position, lane, and scoreboard fields can be returned together for one
match. It does not establish the cost of doing this across a corpus.

The event selections in the captured queries requested `time` only. Victim,
attacker, target, ability, fight, and detailed objective context were not
captured. The shapes of `heroDamageReport`, `actionReport`, `towerDeaths`,
`laneReport`, and related subtypes were not established.

Those missing details are `UNRESOLVED`, even where a parent type name appeared
in the narrow introspection response.

### Item and objective context

The specimens prove:

- final slot fields such as `item0Id` through `item5Id`, backpack, and neutral
  item fields can be returned for a parsed player;
- `stats.itemPurchases { time itemId }` provides purchase timing and item IDs
  for both a core and a support specimen;
- `stats.wards { time type positionX positionY }` is populated in the captured
  samples, including a role-skewed core/support count;
- `stats.runes { time rune }` is populated with native rune tokens; and
- match-level lane outcomes, tower status, and a playback tower-event timing
  list exist in the captured match context.

They do not prove the meaning of ward type or coordinate origin, the full rune
enum, item-use semantics, inventory evolution after purchases, item sales or
consumption, draft response semantics, or the shape of `inventoryReport`.
Final inventory is not a build identity and is rejected for that use.

`A7.json` is a playback research specimen: about 472.9 KB for one player and a
minimal match playback block, including 2,271 position events. It is not a
product-tier source for P0, P1, or P2. The playback Roshan list was empty on a
long match and must not be read as proof of no Roshan event.

### Unparsed and private-state behavior

`A4.json` establishes that an unparsed match returns a `stats` object whose
fields are null, rather than `stats: null`. It also returns null native
position, role, and lane while `roleBasic` remains `CORE`. Eligibility must be
field-aware and fail closed; wrapper presence is not data availability.

The recovered corpus does not contain a live private-profile response. The
provider's private/unavailable policy is protected by offline fixture tests,
but current live private-profile behavior remains a transport validation gap.

## Questionable or superseded historical statements

The 2026-08-27 research remains valuable historical evidence, but these parts
must not be treated as current V7 requirements:

1. The automated-access blocker is superseded. A dated note has been added to
   the old research; the earlier 403 responses remain historical evidence.
2. “No corpus was collected” still means that no population corpus was
   authorized or collected. It does not mean that no live specimens exist:
   the nine recovered response artifacts are schema specimens, not a corpus.
3. The old Pack A/B/C comments describe manual GraphiQL as the only route and
   include historical fixed IDs. They are preserved locally for provenance;
   the future plan below uses placeholders and direct HTTP only.
4. The old 10,000/day cost arithmetic was a brief assumption. The owner has
   since observed 8/second, 150/minute, 1,500/hour, and 15,000/day. Neither
   set of limits is a license for corpus collection in this phase.
5. Candidate rankings and V6.1 Finding reassessments are research direction,
   not frozen V7 implementation. No Finding, threshold, multiplicity rule,
   reference distribution, or public report claim was changed here.
6. The old rejection of final inventory as a build proxy remains correct, but
   its earlier explanation should now acknowledge that purchase events are a
   separate, potentially useful raw signal.

The following remain valid and are intentionally preserved: do not use
`roleBasic`, do not import proprietary STRATZ scores or model outputs, do not
map native enums to OpenDota integers, do not treat `*PerMinute` names as a
shared semantic type, and do not infer coverage from one account.

## V7 need-to-evidence gap matrix

“Existing live evidence” refers only to the recovered live captures. “Coverage
established?” is deliberately stricter: the one-account page cannot establish
population coverage.

| status | Need | Exact STRATZ field/path | Existing live evidence? | Semantics established? | Coverage established? | Needed for | Gap | Next action |
|---|---|---|---|---|---|---|---|---|
| `DONE_FROM_EXISTING_SPECIMEN` | Match identity | `player.matches[].id` | Yes, `q3` | `SEMANTICALLY_ESTABLISHED` | No; one page | all V7 history | no shape gap | Preserve native ID and provenance |
| `DONE_FROM_EXISTING_SPECIMEN` | Chronology and duration | `startDateTime`, `endDateTime`, `durationSeconds` | Yes, `q3`, A2/A3 | `SEMANTICALLY_ESTABLISHED` | No; one account/window | history, sessions, P0 timing | population depth | Use bounded native timestamps; no guessed local time |
| `DONE_FROM_EXISTING_SPECIMEN` | Hero identity | `players[].heroId` | Yes, `q3`, A2/A3/A6 | `SEMANTICALLY_ESTABLISHED` | No; specimen-only | history, P0/P2 | population depth | Retain native hero ID |
| `DONE_FROM_EXISTING_SPECIMEN` | Side and result | `players[].isRadiant`, `players[].isVictory`, `didRadiantWin` | Yes, A5/A6/q3 | `SEMANTICALLY_ESTABLISHED` on captured match structure | No; specimen-only | history, team context | broader validation | Keep side/result separate from lane |
| `DONE_FROM_EXISTING_SPECIMEN` | Native role/position/lane separation | `players[].role`, `position`, `lane` | Yes, q3/A2/A3/A6 | `SEMANTICALLY_ESTABLISHED` as independent native observations | No; 91–93% only on one page | history, P0, future role controls | population coverage | Preserve all three; never use `roleBasic` |
| `NEEDS_POPULATION_COVERAGE` | Role/patch/hero reference distributions | `gameVersionId`, `heroId`, `role`, `position` across `player.matches[]` | Yes, q3 | `SEMANTICALLY_ESTABLISHED` for source fields | No | Transfer, Post-Loss rebuild, Session Drift reference, P0 | no representative population or split | Build a consented, versioned history corpus later |
| `NEEDS_REVALIDATION` | Human patch mapping | `gameVersionId` | Yes, one observed ID | `SEMANTICALLY_ESTABLISHED` as an opaque/native ID; human label mapping `UNRESOLVED` | No | display/context strata | no verified mapping table | Keep ID native; resolve mapping separately |
| `NEEDS_POPULATION_COVERAGE` | Full-year history depth and parsed selection | `player.matches(request: {startDateTime, endDateTime, isParsed, take, skip})` | Partial: q3 is 100 rows/61 days | `SEMANTICALLY_ESTABLISHED` for request shape; full-year behavior `UNRESOLVED` | No | all V7 estimates and parsed economics | one page cannot establish year depth or selection bias | Measure during approved corpus acquisition, not this audit |
| `NEEDS_REVALIDATION` | Leaver eligibility semantics | `players[].leaverStatus`, `LeaverStatusEnum` | `NONE`/`DISCONNECTED` observed | `UNRESOLVED` for material-abandon meaning and legacy mapping | No | eligible history and every reference denominator | exact enum and policy relation not proven | Introspect and manually validate native values; fail closed meanwhile |
| `NEEDS_POPULATION_COVERAGE` | Lane-to-side/lane-outcome mapping | `players[].lane`, `isRadiant`, `bottomLaneOutcome`, `midLaneOutcome`, `topLaneOutcome` | Yes, A5/A6/q3 | `UNRESOLVED` for lane-to-side mapping | No | optional lane context and future P0 context | a sign error can invert interpretation | Use a labelled multi-match corpus; do not guess |
| `DONE_FROM_EXISTING_SPECIMEN` | P0 net-worth trajectory | `players[].stats.networthPerMinute` | Yes, A2/A3 | `SEMANTICALLY_ESTABLISHED` as a cumulative level with a t=0 sample | No; two parsed matches | Lane Recovery raw input | expected trajectory missing | Preserve raw series; derive only in a later V7 feature phase |
| `DONE_FROM_EXISTING_SPECIMEN` | P0 XP trajectory | `players[].stats.experiencePerMinute` | Yes, A2/A3 | `SEMANTICALLY_ESTABLISHED` as minute XP gained, not a rate | No; two parsed matches | Lane Recovery raw input | expected trajectory missing | Preserve increments and document index convention |
| `REJECTED_FIELD` | P0 gold trajectory | `players[].stats.goldPerMinute` | Yes, A2/A3 | `SEMANTICALLY_ESTABLISHED` as a running average | No | not primary Lane Recovery resource | same-name field is not a cumulative trajectory | Exclude from primary P0 until a separate use is justified |
| `NEEDS_REVALIDATION` | Lane-exit/recovery checkpoint alignment | array indexes plus `durationSeconds` | Array lengths are known; both samples are long | `LIKELY_BUT_UNVERIFIED` for exact timestamp/index convention | No | P0 opportunity definition | ~10–12 and ~20–25 minute checkpoints are not frozen | Validate on varied-duration parsed matches; do not tune here |
| `NEEDS_POPULATION_COVERAGE` | Expected hero/role/patch resource trajectory | no single field; distribution of the P0 series keyed by `heroId`, native role/position, `gameVersionId` | No population evidence | `UNRESOLVED` | No | P0 qualification | the reference is missing | Build and split a fresh V7 reference corpus |
| `NEEDS_POPULATION_COVERAGE` | Material deficit opportunity and closure | derived from `networthPerMinute` and XP increments | Feasible raw inputs only | `UNRESOLVED` as a V7 estimator | No | P0 only | no threshold, estimator, opportunity rule, or evidence unit | Re-derive after corpus and checkpoint validation |
| `NOT_NEEDED` | Eventual match win/loss as P0 qualification | `isVictory`, `didRadiantWin` | Yes | `SEMANTICALLY_ESTABLISHED` as outcome fields | No | secondary context only | using it would leak the outcome into recovery qualification | Keep out of the primary recovery definition |
| `DONE_FROM_EXISTING_SPECIMEN` | Unparsed fail-closed shape | `players[].stats` and native role fields | Yes, A4 | `SEMANTICALLY_ESTABLISHED`: object of null fields, not null wrapper | No | eligibility and missingness | broad coverage still unknown | Check fields individually; do not infer from wrapper presence |
| `DONE_FROM_EXISTING_SPECIMEN` | Kill timing | `stats.killEvents { time }` | Yes, A2/A3/A7 | `SEMANTICALLY_ESTABLISHED` for event timing fields | No; two players | P1 capability audit | event context absent | Keep timing as raw evidence only |
| `DONE_FROM_EXISTING_SPECIMEN` | Death timing | `stats.deathEvents { time }` | Yes, A2/A3/A7 | `SEMANTICALLY_ESTABLISHED` for event timing fields | No; two players | P1 capability audit | victim/state context absent | Keep timing as raw evidence only |
| `DONE_FROM_EXISTING_SPECIMEN` | Assist timing | `stats.assistEvents { time }` | Yes, A2/A3 | `SEMANTICALLY_ESTABLISHED` for event timing fields | No; two players | P1 capability audit | assist context absent | Keep timing as raw evidence only |
| `DONE_FROM_EXISTING_SPECIMEN` | Damage given | `stats.heroDamagePerMinute`, `players[].heroDamage` | Yes, A2/A3 | `SEMANTICALLY_ESTABLISHED` as per-minute deltas plus scalar total | No; two players | P1 capability audit | corpus and event context | Preserve both raw forms |
| `DONE_FROM_EXISTING_SPECIMEN` | Damage received | `stats.heroDamageReceivedPerMinute` | Yes, A2/A3 | `SEMANTICALLY_ESTABLISHED` as cumulative levels on specimens | No; two players | P1 capability audit | no received-damage event context | Do not treat it as a delta |
| `DONE_FROM_EXISTING_SPECIMEN` | Team kill denominator | `radiantKills`, `direKills`, `players[].isRadiant` | Yes, A5/A6 | `SEMANTICALLY_ESTABLISHED` as opposing hero-death arrays | No; one match | P1 participation proxy research | general role/hero fairness | Use only with explicit denominator provenance |
| `DONE_FROM_EXISTING_SPECIMEN` | Match-level lead context | `radiantNetworthLeads`, `radiantExperienceLeads` | Yes, A5 | `SEMANTICALLY_ESTABLISHED` as team lead curves; not player trajectory | No; one match | secondary P0/P1 context | no population context | Preserve separately from player resource series |
| `NEEDS_ONE_TARGETED_PAYLOAD` | Kill/death/assist context | subtype fields below `stats.killEvents`, `deathEvents`, `assistEvents` | Timing only; no context fields selected | `UNRESOLVED` | No | P1 capability audit | exact subtype fields were not fetched | Run subtype introspection, then one small parsed payload if safe |
| `NEEDS_BATCHING_ECONOMICS` | Ten-player/team/draft context at corpus scale | `match.players[]` and match-level context | Yes, A6 for one match | `SEMANTICALLY_ESTABLISHED` for one response shape | No | P1/P2 confounder control | repeated match acquisition cost unknown | Measure parsed batch sizes before acquisition |
| `NEEDS_ONE_TARGETED_PAYLOAD` | Objective timing/context | `towerDeathEvents`, `towerDeaths`, `laneReport`, `pickBans` | Partial: A5/A7 coarse fields/timing | `UNRESOLVED` for detail subtype shapes | No | P1 context only | no attribution/detail payload | Introspect subtype fields; do not include chat fields |
| `DONE_FROM_EXISTING_SPECIMEN` | Final inventory as raw state | `item0Id`…`item5Id`, backpack and neutral slots | Yes, A2 | `SEMANTICALLY_ESTABLISHED` as final slot snapshot | No; one player | P2 inventory audit | no evolution semantics | Retain raw snapshot, not build identity |
| `DONE_FROM_EXISTING_SPECIMEN` | Purchase timing and item IDs | `stats.itemPurchases { time itemId }` | Yes, A2/A3 | `SEMANTICALLY_ESTABLISHED` for purchase-event shape | No; two players | P2 capability audit | no population or adaptation baseline | Preserve native purchase events |
| `NEEDS_ONE_TARGETED_PAYLOAD` | Inventory evolution | `stats.inventoryReport` and/or playback `inventoryEvents` | No; only final slots and purchases | `UNRESOLVED` | No | P2 capability audit | sell/use/drop/slot evolution unavailable | Resolve subtype shape first; one targeted parsed payload only if useful |
| `NEEDS_ONE_TARGETED_PAYLOAD` | Item-use semantics | `stats.itemUsed` | Schema name was exposed, payload not fetched | `UNRESOLVED` | No | P2 capability audit | exact fields and meaning unavailable | Include in subtype sentinel; do not guess fields |
| `NEEDS_POPULATION_COVERAGE` | Routine-build versus adaptation baseline | purchase sequence + enemy/team heroes from `match.players[]` | One-match context only | `UNRESOLVED` as an adaptation estimator | No | P2 research only | no patch/hero/role population and no draft control | Defer until parsed batching and reference corpus exist |
| `NEEDS_ONE_TARGETED_PAYLOAD` | Parsed report subtype shapes | `MatchPlayerStats*ReportType`, event subtypes, `MatchStatsLaneReportType` | A1b exposes parent types only | `UNRESOLVED` | No | P1/P2 gap resolution | Pack B was prepared but never executed | Run narrow introspection sentinel; stop on complexity/schema drift |
| `NEEDS_REVALIDATION` | Ward/rune/native enum semantics | `stats.wards[].type`, `positionX/Y`, `stats.runes[].rune` | Values observed in A2/A3 | `UNRESOLVED` for type/grid/full enum meanings | No | P1/P2 research only | one role pair cannot establish enum meaning | Validate against a deliberately chosen small specimen |
| `NEEDS_BATCHING_ECONOMICS` | Parsed match batching | `player.matches(request: {matchIds: [...]})` with `stats` selection | A2/A3 are single-match only | `SEMANTICALLY_ESTABLISHED` for single-match fields; batch behavior `UNRESOLVED` | No | whether P1/P2 are affordable | 310,000 complexity ceiling and selection breadth | Run 4 → 8 → 16 ladder with early stop |
| `NEEDS_REVALIDATION` | Current schema and rate headers | narrow `__type` introspection; response headers | A1b and old research only | `OBSERVED_ON_SPECIMEN_ONLY` for old schema; current drift `UNRESOLVED` | No | every future live operation | captures are from 2026-08-27 | Capture schema digest and headers on first future call |
| `NOT_NEEDED` | Full playback for product P0/P1/P2 | `match.playbackData`, `players[].playbackData` | Yes, A7 | `SEMANTICALLY_ESTABLISHED` as a large research payload | No | not required for current packs | cost and privacy exceed foundation need | Keep as research instrument only |
| `REJECTED_FIELD` | RoleBasic as role | `players[].roleBasic` | Yes, A4/A6 | `SEMANTICALLY_ESTABLISHED` as a misleading/defaulted field | No | none | defaults and support collapse falsify it | Never normalize it |
| `REJECTED_FIELD` | Proprietary/model/rank inputs | `imp`, `averageImp`, `analysisOutcome`, rank/MMR and behavior fields | Some names/outputs observed | `SEMANTICALLY_ESTABLISHED` as out of policy | n/a | none | provenance, privacy, and policy risk | Exclude from raw-to-feature projection |

## Next live microprobe — design only, do not execute

The first future live run should use one approved public test profile and
unique parsed match IDs selected locally from the recovered history page. The
committed plan contains no account or match identifiers. Every request must be
sent to `https://api.stratz.com/graphql` with `User-Agent: STRATZ_API`, and
every response must be archived locally with its operation digest, response
headers (excluding authorization), and request ledger entry.

The recommended core path is five physical requests. The complete decision
tree has a maximum of eight. A failure stops the branch that depends on the
failed result; it never triggers blind retries beyond the transport's bounded
retry policy.

### Call 1 — current schema sentinel

Operation: `V7SchemaSentinel`, version `1.0.0`
Purpose: confirm the current top-level fields and request input still exist.
Why specimens do not answer it: A1b is a historical 2026-08-27 schema
snapshot.
Expected shape: non-null `__Type` records for the seven core types, with field
and enum names.
Kind: schema metadata; not history or parsed data.
Unlocks: whether any later query can be trusted.

Estimated complexity/risk: lower than the rejected full introspection, but the
current ceiling is not re-measured by this offline audit. A complexity error or
null required type is a hard stop.

Exact query:

```graphql
query V7SchemaSentinel {
  match: __type(name: "MatchType") { ...TypeShape }
  matchPlayer: __type(name: "MatchPlayerType") { ...TypeShape }
  playerStats: __type(name: "MatchPlayerStatsType") { ...TypeShape }
  playerPlayback: __type(name: "MatchPlayerPlaybackDataType") { ...TypeShape }
  matchPlayback: __type(name: "MatchPlaybackDataType") { ...TypeShape }
  player: __type(name: "PlayerType") { ...TypeShape }
  matchesRequest: __type(name: "PlayerMatchesRequestType") { ...TypeShape }
}

fragment TypeShape on __Type {
  kind
  name
  enumValues(includeDeprecated: true) { name }
  inputFields { name type { ...TypeRef } }
  fields(includeDeprecated: true) {
    name
    isDeprecated
    args { name type { ...TypeRef } }
    type { ...TypeRef }
  }
}

fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType { kind name }
    }
  }
}
```

Variables: `{}`.
Decision: if a required type or field is absent, stop and record schema drift;
do not spend calls on data.

### Call 2 — parsed subtype shape sentinel

Operation: `V7ParsedSubtypeShapeSentinel`, version `1.0.0`
Purpose: resolve the exact fields for combat, inventory, objective, and enum
subtypes before selecting them.
Why specimens do not answer it: A1b introspected the parent types only; Pack B
was prepared but never executed.
Expected shape: shallow field/type descriptions and enum members; null means a
type is unavailable in the current schema.
Kind: schema metadata; no player or match payload.
Unlocks: whether a safe detail payload can be written without guessing.

Estimated complexity/risk: a shallow, bounded introspection is expected to be
well below full introspection, but its current cost is unknown. The response
must be treated as a schema sentinel, not as proof that the subtype's values
are semantically understood.

Exact query:

```graphql
query V7ParsedSubtypeShapeSentinel {
  laneReport: __type(name: "MatchStatsLaneReportType") { ...Shape }
  towerDeath: __type(name: "MatchStatsTowerDeathType") { ...Shape }
  pickBan: __type(name: "MatchStatsPickBanType") { ...Shape }
  farmDistribution: __type(name: "MatchPlayerStatsFarmDistributionReportType") { ...Shape }
  locationReport: __type(name: "MatchPlayerStatsLocationReportType") { ...Shape }
  actionReport: __type(name: "MatchPlayerStatsActionReportType") { ...Shape }
  heroDamageReport: __type(name: "MatchPlayerStatsHeroDamageReportType") { ...Shape }
  abilityCastReport: __type(name: "MatchPlayerStatsAbilityCastReportType") { ...Shape }
  inventoryReport: __type(name: "MatchPlayerInventoryType") { ...Shape }
  killEvent: __type(name: "MatchPlayerStatsKillEventType") { ...Shape }
  deathEvent: __type(name: "MatchPlayerStatsDeathEventType") { ...Shape }
  assistEvent: __type(name: "MatchPlayerStatsAssistEventType") { ...Shape }
  wardEvent: __type(name: "MatchPlayerStatsWardEventType") { ...Shape }
  wardDestruction: __type(name: "MatchPlayerWardDestuctionObjectType") { ...Shape }
  itemPurchase: __type(name: "MatchPlayerItemPurchaseEventType") { ...Shape }
  itemUsed: __type(name: "MatchPlayerStatsItemUsedEventType") { ...Shape }
  buffEvent: __type(name: "MatchPlayerStatsBuffEventType") { ...Shape }
  courierKill: __type(name: "MatchPlayerStatsCourierKillEventType") { ...Shape }
  runeEvent: __type(name: "MatchPlayerStatsRuneEventType") { ...Shape }
  eLane: __type(name: "MatchLaneType") { ...EnumShape }
  ePosition: __type(name: "MatchPlayerPositionType") { ...EnumShape }
  eRole: __type(name: "MatchPlayerRoleType") { ...EnumShape }
  eLaneOut: __type(name: "LaneOutcomeEnums") { ...EnumShape }
  eLeaver: __type(name: "LeaverStatusEnum") { ...EnumShape }
  eLobby: __type(name: "LobbyTypeEnum") { ...EnumShape }
  eMode: __type(name: "GameModeEnumType") { ...EnumShape }
  eRune: __type(name: "RuneTypeEnum") { ...EnumShape }
}

fragment Shape on __Type {
  name
  kind
  fields(includeDeprecated: true) {
    name
    isDeprecated
    type { kind name ofType { kind name ofType { kind name } } }
  }
}

fragment EnumShape on __Type {
  name
  kind
  enumValues(includeDeprecated: true) { name }
}
```

Variables: `{}`.
Risk: stay shallow; do not expand nested field descriptions or run full schema
introspection.
Decision: if the response is rejected for complexity, retain all unknown
subtypes as unresolved and do not issue blind detail queries.

### Calls 3–5 — parsed batching ladder

Operation: `ProbeParsedEvidenceBatch`, version `1.0.0`
Purpose: measure whether the already-known P0/P1/P2 selection is affordable in
one request for 4, then 8, then 16 parsed matches.
Why specimens do not answer it: A2 and A3 are single-match captures.
Expected shape: requested matches, native metadata, and a per-player `stats`
object; count non-null stats and record complexity/errors, latency, response
bytes, and rate headers.
Kind: parsed match payload.
Decision: stop doubling at the first complexity or response-shape failure;
the largest successful batch is the only economics result used later.

Estimated complexity/risk: high relative to the schema calls because list
cardinality multiplies the selection set under the known 310,000 ceiling. A
partial response, null `stats`, or a complexity error is recorded separately;
it is not silently counted as a successful parsed batch.

Exact query for every ladder request:

```graphql
query ProbeParsedEvidenceBatch($accountId: Long!, $matchIds: [Long!]!) {
  player(steamAccountId: $accountId) {
    matches(request: { matchIds: $matchIds }) {
      id
      durationSeconds
      startDateTime
      endDateTime
      didRadiantWin
      gameMode
      lobbyType
      gameVersionId
      parsedDateTime
      players(steamAccountId: $accountId) {
        steamAccountId
        playerSlot
        isRadiant
        isVictory
        heroId
        position
        role
        lane
        kills
        deaths
        assists
        stats {
          networthPerMinute
          goldPerMinute
          experiencePerMinute
          lastHitsPerMinute
          deniesPerMinute
          heroDamagePerMinute
          heroDamageReceivedPerMinute
          actionsPerMinute
          tripsFountainPerMinute
          killEvents { time }
          deathEvents { time }
          assistEvents { time }
          itemPurchases { time itemId }
          wards { time type positionX positionY }
          runes { time rune }
        }
      }
    }
  }
}
```

Variables and branch:

| call | `accountId` | `matchIds` | condition |
|---|---|---|---|
| 3 | one approved public profile | 4 unique parsed IDs selected offline | always after Calls 1–2 pass |
| 4 | same | 8 unique parsed IDs | Call 3 succeeds with expected shape |
| 5 | same | 16 unique parsed IDs | Call 4 succeeds with expected shape |

If Call 3 fails only for complexity, issue one fallback request rather than
blindly retrying the same selection:

```graphql
query ProbeParsedCoreBatchFallback($accountId: Long!, $matchIds: [Long!]!) {
  player(steamAccountId: $accountId) {
    matches(request: { matchIds: $matchIds }) {
      id
      durationSeconds
      startDateTime
      gameVersionId
      parsedDateTime
      players(steamAccountId: $accountId) {
        heroId
        position
        role
        lane
        stats {
          networthPerMinute
          experiencePerMinute
          killEvents { time }
          deathEvents { time }
          assistEvents { time }
          itemPurchases { time itemId }
        }
      }
    }
  }
}
```

Fallback variables use the same account and two unique parsed IDs. If the
fallback fails, the parsed tier remains uneconomical or schema-blocked and no
corpus acquisition is authorized.

### Call 6 — short parsed trajectory finder (optional)

Operation: `FindShortParsedTrajectory`, version `1.0.0`
Purpose: separate “30 level-up timestamps means final level 30” from “the
array is always length 30.”
Why specimens do not answer it: both A2 and A3 are long games with a 30-entry
array.
Expected shape: up to 100 parsed matches with duration and player level
metadata.
Kind: history selection; no stats payload.
Decision: skip Call 7 if no short parsed match is returned.

Exact query:

```graphql
query FindShortParsedTrajectory(
  $accountId: Long!
  $startDateTime: Long!
  $endDateTime: Long!
) {
  player(steamAccountId: $accountId) {
    matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      isParsed: true
      take: 100
      skip: 0
    }) {
      id
      durationSeconds
      parsedDateTime
      players(steamAccountId: $accountId) {
        heroId
        position
        role
        lane
        level
      }
    }
  }
}
```

Variables: the approved profile, a bounded 365-day Unix-second window; choose
the shortest returned parsed match locally. Do not use rank/MMR filters.

Estimated complexity/risk: low compared with parsed payloads, but filtering by
`isParsed` is itself a selection mechanism and the returned page may contain no
short match. A miss is a reason to skip Call 7, not to widen the query with
forbidden filters.

### Call 7 — one short parsed trajectory (conditional)

Operation: `GetShortParsedTrajectory`, version `1.0.0`
Purpose: read the level array and P0 series on the selected short match.
Why specimens do not answer it: it supplies the missing duration/level
contrast.
Expected shape: one match, one requested player, native role/position/lane,
and the three relevant series.
Kind: parsed match payload.
Condition: only if Call 6 returns a parsed match materially shorter than the
two recovered long specimens.

Exact query:

```graphql
query GetShortParsedTrajectory($accountId: Long!, $matchId: Long!) {
  match(id: $matchId) {
    id
    durationSeconds
    parsedDateTime
    gameVersionId
    players(steamAccountId: $accountId) {
      heroId
      position
      role
      lane
      level
      stats {
        networthPerMinute
        experiencePerMinute
        level
      }
    }
  }
}
```

Variables: the approved profile and the ID returned by Call 6. Do not infer
the level length rule if `stats` is null or partial.

Estimated complexity/risk: one parsed match with a narrow selection; still
subject to current schema drift and parsed availability. It is not a Finding
or checkpoint-calibration request.

### Call 8 — parsed-availability sentinel (optional)

Operation: `ProbeParsedAvailability`, version `1.0.0`
Purpose: compare first-page parsed versus unfiltered rows for ranked and Turbo
without claiming full-year coverage.
Why specimens do not answer it: q3 is one 100-match page over about 61 days;
it cannot establish current full-year selection behavior.
Expected shape: four aliased match lists; count rows locally and record each
page's parsed status.
Kind: history selection.
Condition: run only if the owner specifically needs a current availability
spot-check after Calls 1–5; otherwise defer to population acquisition.

Exact query:

```graphql
query ProbeParsedAvailability(
  $accountId: Long!
  $startDateTime: Long!
  $endDateTime: Long!
) {
  player(steamAccountId: $accountId) {
    allRanked: matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      gameModeIds: [22]
      take: 100
      skip: 0
    }) { id parsedDateTime }
    parsedRanked: matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      gameModeIds: [22]
      isParsed: true
      take: 100
      skip: 0
    }) { id parsedDateTime }
    allTurbo: matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      gameModeIds: [23]
      take: 100
      skip: 0
    }) { id parsedDateTime }
    parsedTurbo: matches(request: {
      startDateTime: $startDateTime
      endDateTime: $endDateTime
      gameModeIds: [23]
      isParsed: true
      take: 100
      skip: 0
    }) { id parsedDateTime }
  }
}
```

Variables: approved profile and the bounded Unix-second window. The mode IDs
are historical request values and must be checked against Call 1/current error
responses; if they drift, skip this optional call rather than guessing a new
mapping. A full-year coverage result belongs to a later population plan, not
this eight-call microprobe.

Estimated complexity/risk: four list aliases can be more expensive than one
history page and each alias is capped at 100 rows. It is a spot-check only;
full-year pagination would exceed this microprobe's purpose and budget.

### Decision tree and budget

```text
1 schema sentinel
  ├─ fail or required type missing → stop (1)
  └─ pass
      2 subtype sentinel
        ├─ fail/complexity → retain subtype gaps; stop payload branch (2)
        └─ pass
            3 parsed batch, 4 IDs
              ├─ complexity → fallback core batch, 2 IDs; then optional 6/8 only by owner choice
              └─ pass → 4 parsed batch, 8 IDs
                          ├─ fail → largest safe batch is 4
                          └─ pass → 5 parsed batch, 16 IDs
                                      └─ fail → largest safe batch is 8
            optional 6 short-game finder
              └─ short parsed match → optional 7 one-match trajectory
            optional 8 first-page availability sentinel
```

Budget:

- maximum proposed physical requests on the full path: 8;
- recommended initial path: 5 (Calls 1–5);
- likely actual path: 5, with Call 6 or Call 8 only if the preceding result
  leaves that specific question decision-relevant;
- no separate profile, match-core, playback, or re-fetch call is needed;
- response headers and transport retry attempts are recorded by the existing
  request ledger; no separate rate-limit request is justified.

This plan deliberately does not propose a payload for `inventoryReport`,
unknown combat context, or `laneReport` fields until Call 2 returns their
exact selection names. Guessing those fields would violate the provider-native
and fail-closed rules.

## Offline transport and corpus preparation

The staging provider already has the future endpoint, named operation registry,
native models, provider-qualified cache keys, request ledger, bounded retries,
rate-limit parser, and raw-page provenance hooks. This audit did not execute
any of them against a provider.

The no-token guard is an explicit offline safety boundary: the client raises
before using the HTTP transport when no token is configured. The unit test now
also asserts that the request ledger remains at zero, so ordinary offline/CI
execution cannot silently make a network request.

The ignored local corpus is kept conceptually in separate layers:

```text
.local/corpora/stratz/v7-prep/
  recovered/       immutable raw responses and historical query packs
  normalized/      future STRATZ-native projections
  manifests/       future cohort/split manifests
  features/        future derived features
  operations/      operation documents and schema snapshots
  ledgers/         request, rate, and failure ledgers
```

Only the recovered raw layer and local recovery manifest were populated in
this phase. No sealed V6.1 validation data was opened.

## Test migration report

- tests added: none; existing focused STRATZ coverage already covered the
  transport, normalization, architecture, and fixture boundary;
- tests changed: one existing no-token test was renamed to state the offline
  contract and now asserts zero ledger requests in addition to zero handler
  calls;
- tests removed: none;
- tests retained: provider headers/body, auth redaction, HTTP/GraphQL failure
  policy, retries, rate parsing, pagination, deduplication, private profiles,
  native role separation, cache isolation, OpenDota coexistence, V6/V6.1
  fail-closed selection, and synthetic-fixture-only test boundaries;
- obsolete assumptions removed: none; no compatibility hack or mass deletion
  was used;
- V7 behavior protected: native role/position/lane separation, no
  `roleBasic` mapping, provider identity, partial-data fail-closed behavior,
  and zero-request operation without a token.

No analytical files, V6.1 artifacts, persisted report contracts, holdout data,
Finding estimators, or deployment configuration were changed.
