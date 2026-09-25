# Free DNA — Death Context Continuation

## Status

**BLOCKED** — the owner-authorized continuation exhausted the fixed missing-ID
queue without completing the frozen panel. The terminal verdict is:

```text
PILOT_COLLECTION_BLOCKED
```

This is a collection/provider-reliability result, not a Death Context
analytical result. No partial residuals, controls, bootstrap intervals,
stability result, calibration prompt, or production change was produced.

## Frozen panel and authorization

The continuation reused the exact prior outcome-blind panel. No reselection or
outcome-based substitution occurred.

| Measure | Result |
| --- | ---: |
| Frozen profiles | 32 |
| Matches per profile | 30 |
| Globally unique panel match IDs | 960 |
| Selection digest | `9855c1535a0e27223e62cb21fb686bdb1ca5acd169fd4d8220b05760c7e3da92` |
| Prior validated successes reused | 59 |
| Missing unique records at continuation start | 901 |
| Continuation retry policy | transient only; max 2 retries after initial |
| Continuation physical-call ceiling | 960 |
| Continuation cost ceiling | Rp1,920 / $0.096 |

The only network path was `GET /matches/{match_id}`. Replay parsing, STRATZ,
Steam, history, public-match, holdout, fresh sealed validation, and production
calls remained out of scope.

## Collection

| Measure | Result |
| --- | ---: |
| New physical calls | 930 |
| New successful unique details | 891 |
| Transient failure attempts | 39 HTTP 429 |
| Retry attempts after initial | 29 |
| Retry attempts that succeeded | 7 |
| Permanent failures | 0 |
| Final frozen-panel completion | 950 / 960 |
| Unresolved frozen-panel matches | 10 |
| Complete frozen profiles | 28 / 32 |
| Replay parse requests | 0 |
| Measured continuation cost | Rp1,860 / $0.093 |

The prior HTTP 500 match was requested first and returned a valid detail on the
continuation request. The remaining 900 never-attempted IDs were then visited
in deterministic panel order. Provider throttling left ten matches unresolved
after the predeclared retry limit; no adaptive top-up was made.

## Provider reliability

| Measure | Result |
| --- | ---: |
| HTTP 429 | 39 |
| HTTP 5xx | 0 |
| Timeouts | 0 |
| Retry success rate | 7 / 29 = 24.14% |
| Request P50, all attempts | 0.924s |
| Request P90, all attempts | 1.382s |
| Request P95, all attempts | 1.558s |
| Successful-detail P50 / P90 / P95 | 0.938s / 1.387s / 1.583s |

The first full 30-match batch at concurrency 5 completed in 9.317s, but the
provider returned 429s during a later concurrent batch. Concurrency was
reduced to 1 for the remainder. Subsequent 30-match groups had median wall
time 30.803s and maximum wall time 99.323s.

## Teamfight semantics

Structural QA on the 950 available successful panel details passed:

- core field completeness: 100% on available records;
- valid ten-player participant arrays: 950 / 950;
- valid unique player-slot mappings: 950 / 950;
- malformed or degenerate fights: 0;
- teamfight windows: 9,811;
- overlapping window pairs: 378.

The provider-indexed teamfight player-death sum and its overlap caveat remain
unchanged. `analysis_allowed` is **NO** because ten panel details are absent;
the structural subset cannot satisfy the full-panel semantic gate.

## Death Context personalization and stability

Not evaluated. The registered player-match estimand, residual IQR,
common-direction guard, controls, attenuation, bootstrap intervals, and
N=10/15/20/25/30 stability require all 960 frozen details. No analytical
meaning is inferred from the 950 available details.

## Free UX and coverage

The available 30-match concurrency-5 observation was 9.317s, which is within
the synchronous routing band, but the later 429-driven concurrency reduction
produced wall times up to 99.323s. Free-generation routing is therefore not a
validated product conclusion from this blocked continuation.

The outcome-independent development/tuning availability ceiling remains:

| Parsed details available | Profiles | Upper-bound share |
| ---: | ---: | ---: |
| ≥20 | 536 | 33.31% |
| ≥25 | 450 | 27.97% |
| ≥30 | 391 | 24.30% |

Publication coverage remains unknown.

## Pilot gates

The terminal collection gate failed before the scientific gates could be
evaluated. The frozen criteria were not relaxed, and no result was promoted:

```text
core fields on available records        PASS (100%)
full frozen-panel completion             FAIL (950/960)
zero replay parse requests               PASS (0)
retry policy                             PASS (max 2 after initial)
call/cost/storage ceilings               PASS
teamfight semantics                      NOT EVALUATED (incomplete panel)
residual, common direction, controls     NOT EVALUATED
stability                                NOT EVALUATED
terminal verdict                         PILOT_COLLECTION_BLOCKED
```

## Reusable Tier-2 corpus

Successful new details were preserved in the canonical ignored corpus without
claiming analytical results:

- path: `.local/corpora/opendota/free-dna-tier2/`;
- raw records persisted: 950 total successful live details (59 prior + 891 continuation);
- raw records referenced: 19 earlier immutable source bodies;
- normalized records: 969 total;
- normalized digest: `f6987a1b695c0c2446c140987ac992f651f7074e68afc501b86dc26d41c0b01f`;
- manifest SHA-256: `ba19ab9b7992c2e6b81988636ea7c0f5aaef475acd764f5edad9eee4a92cd6d4`;
- analytical outcome results generated: **NO**;
- measured local corpus-plus-diagnostics storage: 270,801,746 bytes / 258.26 MiB;
- provenance preserved: **YES**.

Raw bodies, queue records, private identifiers, and ledgers remain ignored and
mode-restricted; no raw provider payload was tracked.

## Integrity receipt

```text
OpenDota continuation physical GETs = 930
OpenDota continuation failed attempts = 39
replay parse requests = 0
STRATZ calls = 0
Steam calls = 0
old holdout evaluated = 0
fresh sealed validation analytically evaluated = 0
analytical behavior changed = NO
backend files changed = NO
production files changed = NO
deployed = NO
```

Required local receipts are under:

```text
.local/diagnostics/free-dna-death-context-continuation/
.local/corpora/opendota/free-dna-tier2/
```

## Next

Stop under this brief. Any further provider recovery requires separate owner
authorization, a newly named campaign, and a provider-rate plan that does not
silently extend this fixed panel budget. The partial panel must not be used to
publish or calibrate Death Context.

## Next prompt

> Review the blocked continuation receipt and decide whether to abandon Death
> Context or authorize a separately budgeted provider-recovery campaign; keep
> the frozen panel, estimand, gates, and the 950 preserved details unchanged.

