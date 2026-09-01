# STRATZ V7 provider contract

Status: staging foundation, 2026-09-01. This document defines the provider
boundary only. It does not define or tune a V7 Finding.

## Boundary and endpoint

V7 uses direct server-side GraphQL over HTTPS:

```text
POST https://api.stratz.com/graphql
Authorization: Bearer <STRATZ_API_TOKEN>
Content-Type: application/json
User-Agent: STRATZ_API
```

The token is read from `STRATZ_API_TOKEN`, is never part of a fixture or
operation payload, and is redacted from logs and provider errors. The default
provider remains `DATA_PROVIDER=opendota`. Setting `DATA_PROVIDER=stratz`
constructs the V7 provider while the existing V6/V6.1 analysis service remains
on its OpenDota source seam.

## Operations

Named, versioned documents live in `services/api/app/stratz/queries.py`:

| operation | purpose | status |
|---|---|---|
| `GetPlayerProfile` v1.0.0 | public profile and privacy state | active |
| `GetPlayerHistoryPage` v1.0.0 | one bounded history page | active |
| `GetMatchCore` v1.0.0 | match context and player scoreboard rows | active |
| `GetParsedMatchCore` v1.0.0 | parsed-data acquisition hook | prepared, not called |
| `GetParsedMatchesBatch` v1.0.0 | parsed batch acquisition hook | prepared, not called |

Every operation has a stable SHA-256 document digest. The selected operation,
version, digest, provider schema version, raw payload hash, and request ledger
are retained as provenance for later V7 re-estimation.

## Rate limits and retries

The observed live limits are 8 requests/second, 150/minute, 1,500/hour, and
15,000/day. The client uses conservative local ceilings of 6/second,
120/minute, 1,200/hour, and 12,000/day, and also respects stricter remaining
and reset values reported by the service or an intermediary.

The client parses common `RateLimit-*` and `X-RateLimit-*` forms, accounts for
every physical attempt and retry, applies bounded exponential backoff with
jitter, honors `Retry-After`, and refuses a reset wait longer than 30 seconds.
Retries are bounded by `STRATZ_MAX_RETRIES` (default 3). No corpus, playback,
or Finding acquisition is part of this foundation.

## History and native schema

`GetPlayerHistoryPage` is requested with a maximum `take` of 100. The V7
history reader uses an inclusive Unix-second window (default 365 days), stable
descending start-time/ID ordering, multiple pages as needed, ID deduplication,
empty/short-page termination, outside-window termination, and a configurable
safety page ceiling (`STRATZ_MAX_HISTORY_PAGES`, default 25). A ceiling hit is
recorded as truncated provenance; it is not presented as complete history.

The STRATZ-native layer preserves these fields without renaming them into
OpenDota rows:

```text
match_id, started_at, ended_at, duration_seconds, hero_id,
did_radiant_win, is_radiant, is_victory, kills, deaths, assists,
game_version_id, position, role, lane, game_mode, lobby_type,
leaver_status, parsed_at, player_slot, party_id, variant
```

The V7 canonical layer keeps the player-relative values needed for future
features (`side`, `won`, combat counts) and retains native enum values as
`*_native` fields for game mode, lobby, and leaver status. It does not ingest
rank/MMR, opaque proprietary scores, behavior or smurf labels, chat, or parsed
analytics in this phase. Raw page data and hashes remain available for clean
future derivation.

## Role, position, lane, and enums

`position`, `role`, and `lane` are independent STRATZ observations. The
normalizer never passes `lane` through the legacy OpenDota `ROLE_HINTS` table
and never maps STRATZ enums to OpenDota integers. For example,
`HARD_SUPPORT + SAFE_LANE` is not carry, and `LIGHT_SUPPORT + OFF_LANE` is not
offlane. A future V7 role vocabulary must be explicitly versioned.

The code contains an audited vocabulary snapshot for
`LeaverStatusEnum`, `MatchLaneType`, `MatchPlayerPositionType`,
`MatchPlayerRoleType`, and lane outcomes. The snapshot is descriptive, not a
conversion table. Unknown enum values remain native strings; any future
dependent eligibility must fail closed until its semantics are verified.

## Cache and error identity

Provider identity and operation version are part of cache identity:

```text
stratz:player:<account-id>
stratz:history:<account-id>:<window>:<operation-version>:page:<skip>:<take>
stratz:match:<match-id>:<operation-version>
```

These keys cannot collide with the legacy OpenDota cache namespace. A V7
STRATZ fetch never reuses a completed OpenDota-compatible analysis by account
ID alone.

HTTP 403, 429, 5xx, timeouts, invalid JSON, GraphQL errors, missing data,
private profiles, and response-shape drift are distinct provider failures.
HTML returned for a 403 is an edge challenge error, not GraphQL data. Partial
GraphQL data with an `errors` array fails closed; it is not normalized as a
complete record.

## V6.1 isolation and staging policy

OpenDota remains available for current V6.1 production, persisted reports,
historical reproducibility, comparison, rollback, and audit. This foundation
does not modify V6.1 analytical code, frozen artifacts, thresholds, holdouts,
or public report contracts. It also does not switch the production runtime or
deploy anything.

V7 changes are developed on `v7/rebuild-stratz-backend`, validated without a
live token, pushed to that feature branch, and integrated into `staging` only
with normal non-force Git history. Main is not a V7 integration target.

## Test strategy

Fixture/unit tests cover request headers and body, redaction, HTTP and
GraphQL failure policy, rate-limit parsing, retries, pagination, 365-day
boundaries, deduplication, privacy, native role fields, provider selection,
cache isolation, OpenDota coexistence, and V6.1 fail-closed selection. Legacy
OpenDota/V6.1, storage, security, lifecycle, and persisted-report contract
tests remain in the suite. Live STRATZ QA is opt-in and is not required for
ordinary CI; this foundation uses zero live provider calls.
