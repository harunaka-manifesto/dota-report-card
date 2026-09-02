# V7 STRATZ corpus runner and neutral QA atlas — 2026-09-02

Status: **PARTIAL_PAUSED** at the conservative local hourly ceiling. On
2026-09-02 the owner confirmed that `isStratzPublic=false` does not prevent
valid API history access and authorized continuing without using that
descriptive flag as an eligibility gate. `isAnonymous=true` remains excluded.
No reserved or sealed account was queried, no raw provider body is committed,
and no Finding, report, calibration, or holdout output was produced.

## Phase checkpoint

```text
PHASE: V7_STRATZ_HISTORY_ACQUISITION
STATUS: PARTIAL_PAUSED
RESEARCH GATE: OPEN — OWNER AUTHORIZED DESCRIPTIVE isStratzPublic HANDLING
RUN DATE: 2026-09-01 UTC
PHYSICAL STRATZ ATTEMPTS: 3,000
HISTORY ATTEMPTS: 3,000
PARSED BATCH ATTEMPTS: 0
OPENDOTA CALLS: 0
RESERVED/SEALED TOUCHED: NO
ADAPTIVE TOP-UP OR REPLACEMENT: NO
RAW IDENTITIES OR PROVIDER ROWS COMMITTED: NO
RESUME: after 2026-09-02T01:36:24.153426+00:00 under the same fixed cohort,
        window, operation digests, and local checkpoint
```

The run used only the predeclared `DISCOVERY` and `CANDIDATE_TEST` targets from
the frozen 1,200-account plan. The runner loaded no row-level details for
`CALIBRATION_RESERVED` or `SEALED_VALIDATION`; those members were used only for
the declared membership/count integrity check.

## Frozen bindings

| binding | SHA-256 or value |
|---|---|
| split manifest | `ef24c63b1c2f56e4bb21b4947b0b43dedf0550bd3547ee818cc9346f4275d885` |
| corpus plan | `9a77fb59fc22e8ac9cad036e3c7854f2668f97a46ed155d6a0a2a86aebac8dd0` |
| source frame | `98a442c0f04f7db8b5d5c32a51acdc0ece47e9fbc490408a29dfb23219bffaa9` |
| history operation | `GetPlayerHistoryPage` v1.0.0 — `b6012c49e7a0150340e447ca0695cc9782075c02e04fb3c6ae7774e964c5589e` |
| parsed operation | `GetParsedAcquisitionBatch` v1.0.0 — `e8db761e962fb0aa411424ac2eccf3c6f74a41b880897bdc1410a6cd992bd8fc` |

The local 365-day window is fixed in `manifests/state.json` and is reused on
resume. History pages use the provider-native, date-bounded request with
`take=100` and continue until provider exhaustion/window start. A 25-page
safety ceiling is recorded as truncation and is never treated as completeness.

## Acquisition counts at pause

The local aggregate atlas contains no account, Steam, match, session, or
pseudonym identifiers.

| measure | `DISCOVERY` | `CANDIDATE_TEST` | total allowed cohort |
|---|---:|---:|---:|
| predeclared history players | 600 | 300 | 900 |
| history attempted | 425 | 0 | 425 |
| history complete | 418 | 0 | 418 |
| history truncated at safety ceiling | 7 | 0 | 7 |
| history failed/pending at pause | 0 / 175 | 0 / 300 | 0 / 475 |
| predeclared parsed players | 128 | 128 | 256 |
| parsed batch attempts | 0 | 0 | 0 |

No private/unavailable response was observed. Among 426 profile states, 390
are non-anonymous and 36 are anonymous; 425 have the descriptive provider
flag `isStratzPublic=false` and one has it true, while their history operations returned data. The
owner therefore authorized eligibility based on actual operation availability
and required-field coverage rather than that flag. No account was topped up,
replaced, or adaptively selected.

The history archive contains 276,172 canonical rows. All have a known start
timestamp within the fixed window. Of these, 218,274 have non-null native
`parsedDateTime` and 57,898 do not. The observed history row duration summary
is count 276,172, minimum 326 seconds, maximum 7,578 seconds, mean 1,870.424
seconds. Native enum observations are retained separately: 211,052 rows have
no observed role/position/lane/leaver vocabulary failure and 65,120 fail at
least one observed enum check. Structural eligibility remains **unknown**
until native game-mode, lobby, and leaver semantics are verified; no row is
promoted to an eligible Finding denominator.

## Transport and archive QA

| gate | result |
|---|---|
| physical request ledger rows | 3,000 |
| immutable raw metadata/body objects | 2,999 / 2,999 |
| HTTP statuses | 2,999 × 200; one retried `ReadTimeout` without a response |
| retries | 1 |
| cache hits during live phase | 0 |
| response bytes | 124,865,588 |
| summed response latency | 1,170.693427 seconds |
| response hash manifest | `0d297707caa0aec6849abe9a7c147e52e6be09a5646472b6d82beeda252bf11a` |
| ledger/raw reconciliation | PASS |
| operation/version/document digest recorded | PASS |
| variables retained | NO — only a variables SHA-256 and safe variable-key metadata are retained |
| authorization/token-bearing headers retained | NO |
| lower live rate headers observed | none in this phase; local 5/sec, 100/min, 1,000/hour, 10,000/day ceilings applied |
| planned daily cap | 9,000 attempts including retries |

Every physical attempt has a contiguous ordinal, operation/version/document
digest, variables hash, response hash when a response exists, timestamp, safe
headers, status, byte count, latency, retry/cache fields, and an append-fsynced
ledger row. Successful immutable request keys are reused on resume; a cache hit
does not create a second physical attempt. Raw bodies and provider-native
normalized projections remain under ignored `.local/corpora/stratz/` storage.

## Architecture and fail-closed rules

```text
immutable raw response + metadata
    -> provider-native normalized projection
    -> V7 canonical history / parsed research tables
    -> aggregate-only neutral QA atlas
```

The history projection preserves native role, position, lane, game mode, lobby,
game version, and leaver values as separate fields. It never uses the legacy
OpenDota role mapping. Parsed acquisition is not started until a predeclared
parsed-subset account is non-anonymous and has valid non-null parsed
opportunities. `isStratzPublic` is retained descriptively but is not an access
gate. Batches are capped at eight requested IDs and require exact
requested-ID equality, one selected player row, and non-null `stats`.

Rows with unknown enum values fail closed for dependent structural use. Native
missingness is retained rather than filled. Repeated match IDs are deduplicated
within each account by deterministic completeness/hash ordering. A match that
appears for two accounts is not incorrectly collapsed: the parsed operation is
account-filtered and the selected player row is distinct, so the account-level
refetch is unavoidable and is retained as separate local research evidence.

The runner stops on persistent 401/403/429, schema drift, GraphQL partial/error
responses, changed live rate behavior, or a bounded-reset violation. It pauses
at the local hourly/daily ceilings and writes state, atlas, manifest, and
ledger before returning. It never adapts the cohort based on privacy,
eligibility, or Finding yield.

## Offline validation and release accounting

Focused client/runner tests: **25 passed**. They cover descriptive
`isStratzPublic` handling, anonymous-profile exclusion, dotenv-only token loading and
redaction, zero-network default, frozen split exclusion, native normalization,
exact parsed batches, duplicate handling, inclusive date boundaries, immutable
hashes and cache reuse, ledger reconciliation, auth failure, GraphQL partial
failure, forbidden fields, bounded retry accounting, rate-window behavior, and
the planned daily cap. Ruff and mypy pass for the runner and focused tests.

```text
TASK TYPE: BACKEND RESEARCH TOOLING + ANALYTICAL DATA ENGINEERING + DOCUMENTATION
BASE SHA: c538bb5ea99e3eaa4054df8db38c93728fa50808
STRATZ calls: 3,000 history; 0 parsed; 3,000 physical attempts total
OpenDota calls: 0
CALIBRATION_RESERVED / SEALED_VALIDATION touched: NO
raw committed: NO
Findings/report contract changed: NO
analytical behavior changed: NO
holdout rerun: NO
recalibration: NO
deployment: NO
```

The preserved local checkpoint is
`.local/corpora/stratz/v7-corpus-2026-09-02/`. It is intentionally ignored
and is not part of the commit. Continuation is owner-authorized after the
recorded hourly reset, using the same fixed cohort, window, operation digests,
and checkpoint. The provider flag remains descriptive; the cohort must not be
adaptively topped up, regenerated, or replaced.
