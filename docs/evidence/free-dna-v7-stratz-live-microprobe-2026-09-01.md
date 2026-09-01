# V7 STRATZ live microprobe

Date: 2026-09-01  
Task: current-schema sentinel, parsed subtype sentinel, and parsed evidence
batch economics  
Status: complete for the recommended five-call path; optional branches deferred

## Evidence boundary

This was a bounded V7 research probe against direct server-side STRATZ
GraphQL. It was not corpus acquisition, Finding estimation, calibration,
holdout validation, report generation, or production QA.

- OpenDota calls: 0.
- Playback calls: 0.
- Physical STRATZ requests: 5 of the hard 8-request ceiling.
- Logical operations: 5.
- HTTP-successful responses: 5 (all HTTP 200); transport retries: 0.
- Strict usable evidence calls: 4; one returned a partial 16-ID batch and is
  not counted as a safe parsed batch.
- Fallback call: not attempted; the 4-ID batch succeeded.
- Optional short-trajectory and parsed-availability calls: not attempted.
- Approved input: one locally recovered history specimen; its identifiers and
  payload remain local and are not reproduced here.

The live archive and request ledger are under the ignored local path
`.local/corpora/stratz/v7-prep/runs/`. The captured response files are
immutable local evidence. The 16-ID response was re-read with the committed
strict response-shape guard; the archive was not rewritten.

## Phase checkpoints

| checkpoint field | value |
|---|---|
| phase | `V7_STRATZ_LIVE_MICROPROBE` |
| phase status | `COMPLETE_RECOMMENDED_PATH` |
| branch | `v7/luna-a-live-microprobe` |
| base SHA | `84bc26d0272983b1d7661b5dc280adc1f4d2d866` |
| endpoint | `https://api.stratz.com/graphql` |
| operation registry | versioned V7 research operations in `services/api/app/stratz/queries.py` |
| physical request budget | `5 / 8` |
| max retries configured | `1`; used `0` |
| cache hits / misses | `0 / 5` |
| schema sentinel | pass: 7 / 7 required core types non-null |
| subtype sentinel | pass: 27 / 27 aliases present; 26 available, `eRune` unavailable |
| largest safe parsed batch | `8` |
| largest attempted parsed batch | `16` |
| fallback | not required; not attempted |
| schema drift | not observed |
| raw response archive | pass; local ignored storage, secret-redacted |
| request ledger | pass; 5 physical rows with status, bytes, latency, rate metadata, retry, and cache fields |
| token exposed | `NO` |
| raw data committed | `NO` |
| analytical behavior changed | `NO` |
| public report contract changed | `NO` |
| acquisition decision | cap the full selection at 8 pending a fresh missing-ID/list-cardinality investigation; do not acquire a corpus from the 16 result |

## Operation registry and live results

All seven research operations are registered at version `1.0.0` with stable
document digests. Only the first three operation kinds below were called.

| operation | document SHA-256 | live status |
|---|---|---|
| `V7SchemaSentinel` | `fce9e9c3d31aeacf13a129ef1ad7cf44698450c0d664a66351ee984cd1123fca` | called, pass |
| `V7ParsedSubtypeShapeSentinel` | `8b2ee55e3b02626e53cd6d8151ef0e0b48523340c51e3e7a9abb92aaffda86bb` | called, pass |
| `ProbeParsedEvidenceBatch` | `351fae1cf03765ed02407acc8a4b25c2ee41af5cce3e8197e27a395259f161e5` | called at 4, 8, 16 |
| `ProbeParsedCoreBatchFallback` | `a09210e652613d3652deb7964067e9e8ffe2eb2997e01217ab7bf707274a4184` | not called |
| `FindShortParsedTrajectory` | `7bccd6f5b31b8612825a28704f738961b98566f45d7073e813f24688559a7790` | deferred |
| `GetShortParsedTrajectory` | `5d9d2d427739d88e8fc570ae9d3ef108a3c872188979894637692891f431852b` | deferred |
| `ProbeParsedAvailability` | `ce9f477212ed326137d72b3d19be9adbc29ebfc92eb39d1f7c0b67d833ea9e1b` | deferred |

### Schema sentinel

The current response contained all seven required non-null `__Type` records:
`MatchType`, `MatchPlayerType`, `MatchPlayerStatsType`,
`MatchPlayerPlaybackDataType`, `MatchPlaybackDataType`, `PlayerType`, and
`PlayerMatchesRequestType`. No GraphQL error, complexity error, or response
shape drift was observed.

### Parsed subtype sentinel

All 27 requested aliases were present. Twenty-six returned a type shape. The
`RuneTypeEnum` lookup returned `null` (`eRune`), so rune vocabulary remains
unresolved. The available response exposed shallow shapes for combat events,
inventory, item use, lane/tower/draft context, and native lane/position/role,
leaver, lobby, and game-mode enums. This establishes names and shape only; it
does not establish field semantics or eligibility meaning.

### Parsed batching ladder

The full current selection was sent sequentially with 4, 8, and 16 unique
locally selected parsed IDs. The strict guard requires every requested match,
the selected player row, and a non-null object-valued `stats` field.

| attempted batch | HTTP | response bytes | latency (s) | returned matches | non-null `stats` | strict result |
|---:|---:|---:|---:|---:|---:|---|
| 4 | 200 | 13,619 | 0.378245 | 4 | 4 | safe |
| 8 | 200 | 28,099 | 0.375302 | 8 | 8 | safe |
| 16 | 200 | 35,358 | 0.265309 | 10 | 10 | partial; not safe |

The 16-ID response had no GraphQL error, but it returned only 10 of the 16
requested IDs. This is an observed partial response, not evidence of a fixed
provider-wide cap: missing-ID/list-cardinality behavior needs a separately
approved investigation. The largest safe batch for this probe is therefore 8;
the largest attempted batch is 16.

Across all five responses, captured response bytes totaled 128,862 and the
sum of per-operation latencies was 1.925539 seconds (wall time approximately
2.009938 seconds). These are observations for this probe, not an SLA.

## Complexity and rate-limit behavior

No complexity value was exposed in response headers or payloads, and no
complexity error occurred. Complexity was recorded as unavailable rather than
estimated. The local ledger still records an `observable_complexity` field for
every physical attempt.

The provider returned safe rate metadata on every response. Observed limits
were:

```text
RateLimit-Limit: 8
X-RateLimit-Limit-Second: 8
X-RateLimit-Limit-Minute: 150
X-RateLimit-Limit-Hour: 1500
X-RateLimit-Limit-Day: 15000
```

`RateLimit-Remaining` was 7 or 6 during the run; the structured second bucket
was likewise 7 or 6. The structured minute, hour, and day remaining values
decreased from 149, 1432, and 14899 on the first response to 145, 1428, and
14895 on the final response. `RateLimit-Reset: 1` was observed. No 429,
`Retry-After`, 401, 403, 5xx, or transport failure occurred.

The ledger records `cache_hit: false` and `cache_miss: true` for each physical
request. No local response was substituted for a live call.

## Schema drift and unresolved semantics

Current schema drift was not observed on either sentinel. The unavailable
`eRune` lookup and the partial 16-ID result are recorded as unresolved
capability/response questions, not silently mapped or treated as successful
coverage.

The following remain unresolved and are intentionally not promoted to V7
analytical meaning:

- why 10 of 16 requested parsed IDs were returned by the batch operation;
- whether the level array is one entry per level or has a fixed length (the
  optional short-trajectory branch was deferred);
- semantics of the newly exposed combat, inventory, item-use, objective, ward,
  and lane-report fields (only shallow subtype shapes were requested);
- rune enum vocabulary and rune-event meaning;
- parsed availability and selection bias over a full year;
- representative hero/role/position/patch reference distributions;
- lane-to-side/lane-outcome mapping and native leaver eligibility semantics;
- any P0 estimator, checkpoint, threshold, stability, significance, or
  publication rule.

No role, position, or lane was converted to an OpenDota vocabulary. No
`roleBasic`, rank/MMR, proprietary score, behavior label, or model output was
requested.

## Acquisition recommendation

Do not authorize a population corpus from this microprobe alone. For future
bounded parsed acquisition, use the 8-match full-selection batch as the
provisional transport ceiling, retain strict requested-ID and non-null-stats
checks, and record every raw response/ledger row. Investigate the 16-ID
partial result with a fresh owner-approved, low-cost probe before raising the
batch size. Keep reference-population, parsed-availability, semantic, and
analytical calibration work as separate V7 phases.

This probe does not justify a Finding, an estimator, a threshold, a human patch
mapping, a role mapping, or a corpus-size claim.

## Privacy and release accounting

- `STRATZ_API_TOKEN` loaded only from the runtime `--dotenv-path`; it was not
  printed, logged, archived, committed, hashed, or copied into a fixture.
- Token exposed: **NO**.
- Raw provider data committed: **NO**.
- Raw responses and headers: local ignored archive only; authorization and
  credential-bearing headers are excluded, and response bodies are secret-
  redacted before local archival.
- Analytical files/artifacts changed: **NO**.
- V6/V6.1 thresholds, estimators, significance, qualification, publication,
  identity, holdout, calibration, and source binding: unchanged.
- Public report contract: unchanged.
- Deployment: **NO**.
