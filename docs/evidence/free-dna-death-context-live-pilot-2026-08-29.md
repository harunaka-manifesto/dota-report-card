# Free DNA — Death Context Live Pilot

## Status

**BLOCKED** — the owner-authorized live supplement stopped on the first
provider error after preserving the successful responses. The terminal pilot
verdict is:

```text
PILOT_COLLECTION_BLOCKED
```

The failure is collection/provenance, not an analytical result. The registered
Death Context outcome analysis was not run, no calibration prompt was created,
and no production behavior changed.

## Frozen panel and authorization

The panel was reproduced before any live GET from the existing development /
tuning lineage:

| Measure | Result |
| --- | ---: |
| Development profiles | 32 |
| Details per profile | 30 |
| Globally unique selected match IDs | 960 |
| Frozen panel selection digest | `9855c1535a0e27223e62cb21fb686bdb1ca5acd169fd4d8220b05760c7e3da92` |
| Source marker | exact `source_version == "22"` |
| Outcome-blind before GETs | YES |
| Fresh validation / old holdout used | NO |

The run used only `GET /matches/{match_id}`. It made no history, public-match,
replay-parse, STRATZ, Steam, or production calls. The owner ceiling was 960
physical GETs, Rp1,920 / $0.096, 384 MiB, and zero retries.

## Collection result

| Measure | Result |
| --- | ---: |
| Physical GETs | 60 |
| Successful HTTP 200 details | 59 |
| Provider failures | 1 |
| Retries | 0 |
| Replay parse requests | 0 |
| Complete frozen profiles | 1 |
| Successful selected matches | 59 / 960 |
| Remaining call budget | 900 |
| Remaining cost ceiling | Rp1,800 / $0.090 |

The provider failure was an HTTP 500 with body `{"error":"Internal Server
Error"}`. It occurred in the second measured profile batch at concurrency 5.
The append-only ledger contains the request and response record; the raw error
body was retained locally for provenance. In-flight concurrent requests that
had already started were allowed to finish, producing the 60-call total. No
retry, replacement, adaptive top-up, or outcome-based selection occurred.

The current campaign is terminal under the frozen brief. The remaining budget
was intentionally not spent.

## Field and teamfight semantics on the available subset

The 59 successful details pass shape QA, but they do not constitute the frozen
960-detail panel gate:

| Measure | Result |
| --- | ---: |
| Applicable-detail core field minimum | 100% |
| Player rows | 590 |
| Teamfight windows | 629 |
| Teamfight participant rows | 6,290 |
| Malformed / degenerate fights | 0 |
| Details with valid ten-player participant arrays | 59 / 59 |
| Details with valid unique player-slot mapping | 59 / 59 |
| Overlapping window pairs | 19 |
| Semantics status | LIKELY |

The numerator remains the provider-indexed teamfight player-death sum. The
overlap caveat remains: the provider windows are not an independently timed
unique-death reconstruction. The subset supports structural reuse and shape
QA only. Target-player mapping, baselines, residuals, controls, bootstrap
intervals, common-direction checks, and stability were not evaluated because
the full frozen panel was unavailable.

## Latency and Free routing

Values below are derived from request-start and response-completion timestamps
in the local ledger. The 30-match concurrency-5 batch is explicitly an
attempted batch and includes the one provider failure.

| Observation | Concurrency | Responses | Wall time |
| --- | ---: | ---: | ---: |
| Four-request semantic QA | 1 | 4 / 4 | 4.090s |
| Profile 0, 20-match batch | 1 | 20 / 20 | 19.946s |
| Profile 0, 30-match batch | 1 | 30 / 30 | 28.271s |
| Profile 1, 20-match batch | 5 | 20 / 20 | 7.293s |
| Profile 1, 30-match attempted batch | 5 | 30 / 30; 1 failed | 11.024s |

Successful request latency across 59 details was P50 **0.898s**, P90
**1.352s**, P95 **2.018s**, and max **3.215s**. Concurrency 10 was not
reached. Local analysis time and full end-to-end enrichment time are
**unmeasured** because analysis did not run; synchronous Free feasibility is
therefore unverified.

## Coverage ceiling

The outcome-independent development/tuning profile distribution remains:

| Parsed details available | Profiles | Upper-bound share |
| ---: | ---: | ---: |
| ≥20 | 536 | 33.31% |
| ≥25 | 450 | 27.97% |
| ≥30 | 391 | 24.30% |

This is a data-availability ceiling, not publication coverage. Publication
coverage is **known: NO**. No recommended N can be selected from a blocked
collection.

## Cost and storage

The measured pro-rata spend is **Rp120 / $0.006** for 60 physical GETs. The
canonical local research storage is **17,187,144 bytes / 16.39 MiB**, within
the 384 MiB ceiling. The local raw bodies and ledgers remain ignored/private;
no raw provider payload or private identifier is tracked.

## Reusable Tier-2 corpus

The successful data was added to the canonical local corpus without claiming
analytical results:

- canonical path: `.local/corpora/opendota/free-dna-tier2/`;
- raw records persisted: 59 new live responses;
- raw records referenced: 19 earlier immutable source bodies;
- normalized records: 78 total;
- normalized digest: `09b7322304a001e2fe08e84f742f5e66da15eb5aa97b2dcf235be73f2b6223c3`;
- manifest SHA-256: `0aa3b41f89812dbced0d8dda138d00845e3b8db4aa25e49091755635e9c2f7b8`;
- analytical outcome results generated: **NO**;
- provenance preserved: **YES**.

The corpus is reusable for future offline research and schema QA. It is not a
completed Death Context panel and does not authorize another provider run.

## Integrity receipt

```text
OpenDota physical GETs = 60
OpenDota failed GETs = 1
replay parse requests = 0
STRATZ calls = 0
Steam calls = 0
old holdout evaluated = 0
fresh sealed validation analytically evaluated = 0
analytical behavior changed = NO
production files changed = NO
deployed = NO
```

Required local artifacts are under:

```text
.local/diagnostics/free-dna-death-context-live-pilot/
.local/diagnostics/free-dna-death-context-overnight/progress.json
```

Next status under the current brief is **STOP — PILOT_COLLECTION_BLOCKED**.
Any future provider attempt requires a separately authorized, newly named
campaign that resolves the provider failure; this campaign must not be
silently retried.

## Final-10 completion and frozen analysis — 2026-08-29

A separately authorized final-completion campaign reused the same frozen panel
and requested only the ten unresolved IDs. All ten returned valid details on
their first attempt: 10 physical GETs, 0 retries, 0 HTTP 429s, and Rp20 pro
rata. The panel reached 960 / 960 without replacement, adaptive top-up, replay
parse, STRATZ, Steam, holdout, or fresh sealed-validation calls.

The complete registered analysis then ran locally. Teamfight structural QA was
100% complete with 0 malformed fights, 9,940 provider windows, and 381
overlapping window pairs. Personalization controls and N25/N30 stability
passed, but adjusted residual IQR was 0.091519 against the frozen 0.10 gate.
The terminal verdict is `DROP_DEATH_CONTEXT`; no calibration prompt or
production change was created. Full details are in
`docs/evidence/free-dna-death-context-final-completion-2026-08-29.md` and
`docs/evidence/free-dna-death-context-rejection-2026-08-29.md`.
