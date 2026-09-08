# V7 STRATZ acquisition packs and cohort freeze — 2026-09-01

Status: **frozen offline research design**. No STRATZ or OpenDota acquisition
was performed by this phase. The population research arrangement is private and
local-only under the current terms disposition: raw/row-level redistribution is
not allowed, commits are aggregate-only, and raw retention is minimum and
purpose-bound. Public or commercial product use remains held for written
provider confirmation.

This freeze uses the [terms disposition](free-dna-v7-stratz-usage-storage-review-2026-09-01.md),
the [live microprobe](free-dna-v7-stratz-live-microprobe-2026-09-01.md), and the
current [STRATZ provider boundary](../architecture/stratz-v7-provider-contract.md).
The microprobe's 16-ID response is treated as unsafe partial data; all full
parsed batches are capped at the largest safe size, **8**.

## Phase checkpoint

```text
PHASE: V7_STRATZ_ACQUISITION_COHORT_FREEZE
STATUS: FROZEN_OFFLINE_PLAN
BRANCH: v7/luna-b-acquisition-design
BASE SHA: b26555569ec5659023ba13ef7dcd1fb797b147b6
STRATZ calls during this phase: 0
OpenDota calls during this phase: 0
raw identities printed or committed: NO
analytical outputs inspected: NO
CALIBRATION_RESERVED / SEALED_VALIDATION inspected or used: NO
adaptive top-up: NO
```

The source frame is the already-paid local public-match-derived frame at
`.local/corpora/opendota/v61-session-drift-expansion/manifests/fixed-frame-manifest.json`.
It contains 4,135 unique positive public accounts selected from sampled public
matches. Its source-file SHA-256 is
`98a442c0f04f7db8b5d5c32a51acdc0ece47e9fbc490408a29dfb23219bffaa9`.
The source frame is a sampling frame, not a representative population claim;
its prior V6.1 arm labels are ignored and a new salt is used.

## Cohort, splits, and denominators

The preselection size is **N = 1,200**. This is above the finite-population
minimum needed for a worst-case 95% reach margin of 2.5 percentage points from
the 4,135-account frame (the exact plan margin is 2.3837 percentage points;
maximum SE 0.0121618). The fixed partitions are:

| partition | accounts | parsed subset | use in this phase |
|---|---:|---:|---|
| `DISCOVERY` | 600 | 128 | candidate discovery and feature design |
| `CANDIDATE_TEST` | 300 | 128 | one predeclared confirmation pass remains viable |
| `CALIBRATION_RESERVED` | 150 | 0 | reserved; not inspected or used |
| `SEALED_VALIDATION` | 150 | 0 | reserved; not inspected or used |
| **total** | **1,200** | **256** | fixed before discovery |

Ordering is ascending HMAC-SHA256 over each source account with a new private
32-byte salt. Split boundaries are fixed contiguous counts in that order. The
parsed subset is independently HMAC-ranked within `DISCOVERY` and
`CANDIDATE_TEST` only. It is selected before any history output, candidate
yield, or analytical result is available; no top-up or replacement based on
Finding yield is permitted. The candidate-test history split has a worst-case
SE of 0.027804 (95% margin 5.450%), while the predeclared 128-account parsed
candidate-test subset has **n = 128**, a worst-case finite-population
proportion SE of 0.043510 (95% margin 0.085280, or 8.528%), and keeps a
complete parsed confirmation wave operationally possible. These are precision
bounds for reach-like proportions, not promises about final Finding tails.

The private local artifacts from the generated freeze are:

```text
.local/corpora/stratz/v7-acquisition-freeze-2026-09-01/salt.bin       mode 0600
.local/corpora/stratz/v7-acquisition-freeze-2026-09-01/manifests/split-manifest.json
.local/corpora/stratz/v7-acquisition-freeze-2026-09-01/manifests/corpus-plan.json
```

Only digests leave the local artifact boundary:

| artifact | SHA-256 |
|---|---|
| salt (32 bytes, local only) | `2d552949ff32480ab7089d979152423a5e8bffd57fe4f613b9c7db698bdee7e4` |
| split manifest | `ef24c63b1c2f56e4bb21b4947b0b43dedf0550bd3547ee818cc9346f4275d885` |
| corpus plan | `9a77fb59fc22e8ac9cad036e3c7854f2668f97a46ed155d6a0a2a86aebac8dd0` |

The split manifest contains HMAC pseudonyms, HMAC rank digests, source-frame
positions, partition labels, and parsed-subset flags. It contains no raw
account IDs. The salt and manifests are ignored, private, and mode `0600`.

Denominators are kept separate:

| denominator | exact status in this freeze |
|---|---|
| sampled frame | 4,135 accounts in the reused public-match-derived frame |
| selected preselection | 1,200 fixed HMAC-selected accounts |
| product eligible | unknown until public-profile/product availability checks; not inferred |
| structural eligible | unknown until history mode/lobby/native-leaver checks; leaver semantics remain unresolved |
| information eligible | candidate-specific non-null opportunities after acquisition; parsed availability is not assumed |

The unfiltered history operation is planned against **597 all-history rows per
account-year**, extrapolated from one recovered q3 specimen with 100 rows over
approximately 61 days. This is a planning proxy, **not population truth**. It
drives the six-page/account history proxy. Separately, the parsed-batch and
structural context scenario uses 293 structurally eligible matches per
account-year from the existing specimen research; that value is also not a
population estimate and must not be used to truncate unfiltered history.
Role, position, and lane observed specimen rates (93%, 91%, and 93%) are
recorded only as unresolved planning context; no population coverage is
claimed. Candidate gates remain candidate-specific: a role-shape pass needs
its declared match/session support, and parsed candidates require non-null
information opportunities. An account count is never substituted for an
opportunity count.

## Versioned acquisition packs

The pack set is deliberately small. History Core reuses the active
`GetPlayerHistoryPage` operation. Parsed Core and Parsed Extended share one new
minimum selection operation so acquiring the extended field does not create a
second duplicate parsed request. The operation is not called in this phase;
its digest is a registry identity only.

All field-level complexity contributions are **UNKNOWN**: the provider exposed
no per-field or query complexity value. The live batch response byte measure is
used for storage planning only, never as a complexity estimate. `KEEP` means
retain in the private provider-native research layer; local-only identifiers
are never committed or redistributed. No field below is a human-patch mapping
or a role conversion.

### History Core — `stratz-history-core-1.0.0`

Operation: `GetPlayerHistoryPage` v1.0.0,
SHA-256 `b6012c49e7a0150340e447ca0695cc9782075c02e04fb3c6ae7774e964c5589e`.
Consumers: T1-A Role Shape, T1-B post-loss control matching, eligibility and
context-baseline accounting.

| provider path | semantic class / meaning | alignment | null behavior | parsed required | complexity | candidate consumers | disposition |
|---|---|---|---|---:|---|---|---|
| `profile.isAnonymous` | PRIVACY — provider privacy state | profile | null fails public eligibility | no | UNKNOWN | product eligibility | KEEP |
| `profile.isStratzPublic` | PRIVACY — descriptive STRATZ-profile state; live history remained available when false | profile | retain null/false descriptively; do not gate data eligibility | no | UNKNOWN | QA stratification | KEEP |
| `match.id` | META — opaque local parsed-join key | one match | missing row fails closed | no | UNKNOWN | T2-A, T2-B local join | KEEP, local-only |
| `match.startDateTime` | META — match start timestamp | one match | null excludes chronology use | no | UNKNOWN | T1-A, T1-B | KEEP |
| `match.endDateTime` | META — match end timestamp | one match | null excludes chronology use | no | UNKNOWN | T1-B | KEEP |
| `match.durationSeconds` | META — match duration | one match | null excludes duration use | no | UNKNOWN | structural eligibility, T1-B | KEEP |
| `match.didRadiantWin` | META — match winning side | one match | null excludes outcome use | no | UNKNOWN | T1-B | KEEP |
| `match.gameMode` | META — native game-mode enum | one match | null fails mode eligibility | no | UNKNOWN | structural eligibility | KEEP |
| `match.lobbyType` | META — native lobby enum | one match | null fails lobby eligibility | no | UNKNOWN | structural eligibility | KEEP |
| `match.gameVersionId` | META — native game-version ID, not a human patch claim | one match | null excludes context stratification | no | UNKNOWN | T1-B, context baselines | KEEP |
| `match.parsedDateTime` | META — parsed availability timestamp | one match | null means parsed evidence unavailable | no | UNKNOWN | parsed-availability denominator | KEEP |
| `player.heroId` | PLAYER — player hero identity | one player row/match | null excludes hero comparisons | no | UNKNOWN | T1-A, T1-B | KEEP |
| `player.isRadiant` | PLAYER — player-relative side | one player row/match | null excludes side use | no | UNKNOWN | T1-B | KEEP |
| `player.isVictory` | PLAYER — player-relative outcome | one player row/match | null excludes outcome use | no | UNKNOWN | T1-B | KEEP |
| `player.kills` | PLAYER — scoreboard kills | one player row/match | null excludes combat summary | no | UNKNOWN | T1-B | KEEP |
| `player.deaths` | PLAYER — scoreboard deaths | one player row/match | null excludes exposure summary | no | UNKNOWN | T1-B | KEEP |
| `player.assists` | PLAYER — scoreboard assists | one player row/match | null excludes combat summary | no | UNKNOWN | T1-B | KEEP |
| `player.leaverStatus` | PLAYER — native leaver enum; mapping unresolved | one player row/match | null/unresolved fails eligibility | no | UNKNOWN | structural eligibility | KEEP |
| `player.position` | REPLAY — native position observation | one player row/match | null on unparsed/unavailable row | yes | UNKNOWN | T1-A, T1-B | KEEP |
| `player.role` | REPLAY — native role observation, independent of lane/position | one player row/match | null on unparsed/unavailable row | yes | UNKNOWN | T1-A, T1-B | KEEP |
| `player.lane` | REPLAY — native lane observation, never role-converted | one player row/match | null on unparsed/unavailable row | yes | UNKNOWN | T1-B | KEEP |

### Parsed Core — `stratz-parsed-core-1.0.0`

Operation: `GetParsedAcquisitionBatch` v1.0.0,
SHA-256 `e8db761e962fb0aa411424ac2eccf3c6f74a41b880897bdc1410a6cd992bd8fc`.
Consumers: T2-A Kill Participation Share and T2-B Lane Outcome Record. The
16-ID result is not used to raise the batch size; the safe transport cap stays
at 8.

| provider path | semantic class / meaning | alignment | null behavior | parsed required | complexity | candidate consumers | disposition |
|---|---|---|---|---:|---|---|---|
| `match.id` | META — opaque local parsed-join key | one match | missing row fails closed | yes | UNKNOWN | T2-A, T2-B | KEEP, local-only |
| `match.durationSeconds` | META — match duration | one match | null excludes match use | yes | UNKNOWN | T2-A, T2-B | KEEP |
| `match.startDateTime` | META — match start timestamp | one match | null excludes chronology use | yes | UNKNOWN | T2-A, T2-B | KEEP |
| `match.endDateTime` | META — match end timestamp | one match | null excludes chronology use | yes | UNKNOWN | T2-A, T2-B | KEEP |
| `match.didRadiantWin` | META — match winning side | one match | null excludes outcome use | yes | UNKNOWN | T2-B | KEEP |
| `match.gameVersionId` | META — native game-version ID | one match | null excludes context stratification | yes | UNKNOWN | T2-B | KEEP |
| `match.parsedDateTime` | META — parsed availability gate | one match | null fails parsed eligibility | yes | UNKNOWN | T2-A, T2-B | KEEP |
| `match.radiantKills` | REPLAY — radiant team hero-death denominator, not scoreboard kills | one match | null excludes participation denominator | yes | UNKNOWN | T2-A | KEEP |
| `match.direKills` | REPLAY — dire team hero-death denominator, not scoreboard kills | one match | null excludes participation denominator | yes | UNKNOWN | T2-A | KEEP |
| `match.radiantNetworthLeads` | REPLAY — radiant net-worth lead trajectory | one match trajectory | null excludes state context | yes | UNKNOWN | T2-B | KEEP |
| `match.bottomLaneOutcome` | REPLAY — native bottom-lane outcome enum | one match | null means unavailable | yes | UNKNOWN | T2-B | KEEP |
| `match.midLaneOutcome` | REPLAY — native mid-lane outcome enum | one match | null means unavailable | yes | UNKNOWN | T2-B | KEEP |
| `match.topLaneOutcome` | REPLAY — native top-lane outcome enum | one match | null means unavailable | yes | UNKNOWN | T2-B | KEEP |
| `player.isRadiant` | PLAYER — player-relative side | one player row/match | null excludes side mapping | yes | UNKNOWN | T2-B | KEEP |
| `player.isVictory` | PLAYER — player-relative outcome | one player row/match | null excludes outcome use | yes | UNKNOWN | T2-B | KEEP |
| `player.heroId` | PLAYER — player hero identity | one player row/match | null excludes hero control | yes | UNKNOWN | T2-A, T2-B | KEEP |
| `player.position` | REPLAY — native position observation | one player row/match | null excludes role stratification | yes | UNKNOWN | T2-A, T2-B | KEEP |
| `player.role` | REPLAY — native role observation | one player row/match | null excludes role stratification | yes | UNKNOWN | T2-A, T2-B | KEEP |
| `player.lane` | REPLAY — native lane observation | one player row/match | null excludes lane mapping | yes | UNKNOWN | T2-B | KEEP |
| `stats.killEvents[].time` | REPLAY — timestamped player kill events | one player-match event list | null/missing excludes evidence; empty means zero observed events | yes | UNKNOWN | T2-A | KEEP |
| `stats.assistEvents[].time` | REPLAY — timestamped player assist events | one player-match event list | null/missing excludes evidence; empty means zero observed events | yes | UNKNOWN | T2-A | KEEP |

### Parsed Extended — `stratz-parsed-extended-1.0.0`

This pack is frozen only because Item Signature is a credible research
candidate. It is research-only, not a product or publication commitment. No
other extended trajectory, event, coordinate, or subtype field clears the
current candidate gate; those fields are omitted.

Operation: `GetParsedAcquisitionBatch` v1.0.0,
SHA-256 `e8db761e962fb0aa411424ac2eccf3c6f74a41b880897bdc1410a6cd992bd8fc`.

| provider path | semantic class / meaning | alignment | null behavior | parsed required | complexity | candidate consumers | disposition |
|---|---|---|---|---:|---|---|---|
| `stats.itemPurchases[].time` | REPLAY — recorded item-purchase timestamp | one player-match event list | null/missing excludes evidence; empty means zero observed purchases | yes | UNKNOWN | T3 Item Signature, research-only | KEEP |
| `stats.itemPurchases[].itemId` | REPLAY — native item ID attached to a purchase event | one player-match event list | null/missing excludes evidence; empty means zero observed purchases | yes | UNKNOWN | T3 Item Signature, research-only | KEEP |

The union of the two parsed packs is the new operation's selection. It does
not request text, movement/playback, opaque model/proprietary, rank-like, or
legacy role-shortcut data. It does not use rank/MMR or any Finding output for
selection. Parsed availability and all native enum semantics remain measured
and fail-closed rather than guessed.

## Economics and execution envelope

The economics use the observed full parsed batch of 8 (28,099 response bytes)
and the recovered 100-match history specimen (103,441 bytes). Complexity was
not exposed, so no complexity number is fabricated.

| quantity | projected value | basis |
|---|---:|---|
| all-history rows/account-year | 597 | extrapolated from one recovered q3 specimen with 100 rows over approximately 61 days; **not population truth** |
| history pages/account-year proxy | 6 | `ceil(597 / 100)`; unfiltered history, all rows, planning proxy only |
| history calls, N=1,200 | 7,200 | 1,200 × 6 |
| parsed batches/parsed account-year | 37 | `ceil(293 / 8)`; upper bound before parsed availability is measured |
| parsed calls, 256 accounts | 9,472 | 128 discovery + 128 candidate-test, each × 37 |
| planned calls, all waves | 16,672 | history + parsed; retries are additional physical attempts |
| history raw bytes proxy | 744,775,200 | 7,200 × 103,441; specimen proxy, not SLA |
| parsed raw bytes upper bound | 266,153,728 | 9,472 × 28,099; safe-batch proxy |
| combined raw bytes upper bound | 1,010,928,928 | approximately 964.1 MiB, local-only |

The observed provider limits were 8/sec, 150/min, 1,500/hour, 15,000/day.
The orchestration ceilings are 5/sec, 100/min, 1,000/hour, 10,000/day. A 10%
daily reserve leaves a planned cap of 9,000 calls/day. The wave schedule is:

| day | waves | planned calls | reserve to 9,000 | wall time at 1,000/hour |
|---|---|---:|---:|---:|
| 1 | History Core | 7,200 | 1,800 | 7.2 h |
| 2 | Parsed Discovery | 4,736 | 4,264 | 4.736 h |
| 3 | Parsed Candidate Test | 4,736 | 4,264 | 4.736 h |
| **total** | — | **16,672** | — | **16.672 h at the hourly ceiling** |

The hourly ceiling binds before the second/minute limits for this schedule.
Retries, partial-response recovery, and reset waits count as physical attempts
and consume the daily reserve; each day stops before the 9,000 planned-call
cap. Six pages is an observed planning proxy, not a completeness ceiling: the
actual runner must paginate the unfiltered history to the 365-day window start
(or provider exhaustion), with a page ceiling only as a safety guard. Calls
and bytes can exceed the proxy only while remaining within the daily budget.
The 293-match structural scenario is a planning input, not a promise that all
accounts will be product, structural, or information eligible. Actual counts
are recorded by denominator after collection, with no adaptive top-up.

## Validation and release boundary

Offline checks implemented in `scripts/stratz_v7_acquisition_freeze.py`:

- source-frame schema, count, positive-ID uniqueness, contiguous ordering,
  public-match/HMAC provenance, and no output-based selection;
- HMAC ranking and opaque pseudonymization with a fresh 32-byte salt;
- private mode-0600 salt, split, corpus-plan, digest, and summary files;
- exact partition counts and zero split overlap;
- deterministic repeatability for a supplied salt;
- aggregate summary generation with raw-ID absence check;
- operation registry identity/digest checks and pack field checks;
- safe batch-8 economics, all-history page proxy, daily reserve, bytes, and
  wall-clock calculations, including the n=128 parsed candidate-test bound;
- repository-relative source-frame default so ordinary CI uses only synthetic
  test fixtures; the real source frame is supplied explicitly at freeze time.

The focused unit suite is credential-free and made no provider calls. The
source frame is read locally only. No analytical output, calibration data, or
sealed validation content was inspected. This is a research design and
acquisition boundary, not a V7 estimator, threshold, Finding, or product
release. V6.1 source binding, artifacts, semantic output, and public report
contract are unchanged.

## Completion record

```text
TASK TYPE: BACKEND RESEARCH TOOLING + ANALYTICAL DESIGN + DOCUMENTATION
BASE SHA: b26555569ec5659023ba13ef7dcd1fb797b147b6
NEW SHA: see final commit
CHANGED FILES: scripts/stratz_v7_acquisition_freeze.py; services/api/app/stratz/queries.py; services/api/app/stratz/__init__.py; tests/unit/test_stratz_v7_acquisition_freeze.py; docs/evidence/free-dna-v7-stratz-acquisition-cohort-freeze-2026-09-01.md
BACKEND FILES CHANGED: YES (query registry only; no runtime provider client)
ANALYTICAL FILES CHANGED: NO (research design/tooling only)
PUBLIC REPORT CONTRACT CHANGED: NO
PERSISTED REPORT COMPATIBILITY TESTED: NOT APPLICABLE
PRODUCTION-SHAPED FIXTURE: NOT APPLICABLE
BROWSER E2E: NOT APPLICABLE
TYPECHECK: PASS / focused script is outside mypy's configured services/api scope
LINT: PASS (focused ruff)
BUILD: NOT APPLICABLE
DOCS-CHECK: PASS
ANALYTICAL BEHAVIOR CHANGED: NO
HOLDOUT RERUN: NO
RECALIBRATION: NO
OPENDOTA QA CALLS: 0
STRATZ API CALLS: 0
DEPLOYED: NO
SAFE TO MERGE: YES (owner review of research freeze and provider terms remains required)
```
