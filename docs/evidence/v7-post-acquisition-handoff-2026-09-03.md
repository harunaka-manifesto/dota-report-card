# V7 post-acquisition corpus handoff — 2026-09-03

Status: **RESEARCH_READY**. The STRATZ acquisition recorded as
`PARTIAL_PAUSED` in
`docs/evidence/free-dna-v7-stratz-corpus-qa-atlas-2026-09-02.md` subsequently
reached `COMPLETE`. This document is the independent handoff validation of the
finished corpus. It was produced without a single new provider request.

```text
PHASE: V7_POST_ACQUISITION_HANDOFF
STATUS: PASS
NEW STRATZ PHYSICAL CALLS THIS PHASE: 0
NEW PLAYBACK CALLS: 0
OPENDOTA CALLS: 0
RAW DATA COMMITTED: NO
MAIN TOUCHED: NO
CALIBRATION_RESERVED TOUCHED: NO
SEALED_VALIDATION TOUCHED: NO
```

## Canonical artefacts

| artefact | location |
|---|---|
| corpus root | `.local/corpora/stratz/v7-corpus-2026-09-02/` (ignored, local only) |
| acquisition freeze root | `.local/corpora/stratz/v7-acquisition-freeze-2026-09-01/` |
| raw response archive | `<corpus>/raw/` — paired `.body` + `.json` metadata per attempt |
| request ledger | `<corpus>/ledgers/request-ledger.jsonl` |
| normalized projection | `<corpus>/normalized/{history,parsed}/` |
| canonical research tables | `<corpus>/canonical/{history,parsed}/` |
| neutral aggregate atlas | `<corpus>/derived/qa-atlas.json` |
| run manifest | `<corpus>/manifests/run-manifest.json` |
| resumable runner state | `<corpus>/manifests/state.json` |
| validator | `scripts/v7_post_corpus_handoff.py` |

The validator recomputes every reconciliation from the immutable artefacts. It
does not trust the runner's own `reconciled: true` claim.

## Frozen bindings

| binding | SHA-256 |
|---|---|
| split manifest | `ef24c63b1c2f56e4bb21b4947b0b43dedf0550bd3547ee818cc9346f4275d885` |
| corpus plan | `9a77fb59fc22e8ac9cad036e3c7854f2668f97a46ed155d6a0a2a86aebac8dd0` |
| source frame | `98a442c0f04f7db8b5d5c32a51acdc0ece47e9fbc490408a29dfb23219bffaa9` |
| `GetPlayerHistoryPage` v1.0.0 | `b6012c49e7a0150340e447ca0695cc9782075c02e04fb3c6ae7774e964c5589e` |
| `GetParsedAcquisitionBatch` v1.0.0 | `e8db761e962fb0aa411424ac2eccf3c6f74a41b880897bdc1410a6cd992bd8fc` |
| recomputed raw-body manifest | `46fff10b1a998ebc895d8f83dbe0eb95f3c2b2a83f4ef59a0dca825fa3f8e1b9` |

The split-manifest digest recomputed from disk equals the digest frozen in the
run manifest. Both canonical tables were validated against the frozen
membership, not against a regenerated split.

## Collection reconciliation

| measure | value |
|---|---|
| request-ledger rows | 23,023 |
| distinct physical ordinals | 23,023 (no duplicates, no gaps) |
| immutable successes | 22,985 |
| archived response bodies / metadata objects | 22,996 / 22,996 |
| ledger-referenced bodies | 22,996 |
| orphan raw bodies | 0 |
| missing raw bodies | 0 |
| response-hash mismatches | 0 |
| malformed successful GraphQL bodies | 0 |
| GraphQL `errors` responses archived as success | 0 |
| partial-data responses | 0 |
| operation-document digest mixing | none |
| ledger schema versions | 1 (`stratz-v7-request-ledger-1.0.0`) |
| cache hits during the live phase | 0 |
| response bytes | 506,810,902 |
| retained request variables | none (SHA-256 and safe key names only) |
| retained token-bearing headers | none |

HTTP outcomes: 22,985 × 200, nine 403, two 520, and 27 transport errors with no
response. All 38 non-success attempts are ledgered, retried, and carry an
archived edge response where one existed.

Eleven archived bodies are not JSON. Every one belongs to a **failed** attempt
(seven `authentication_failure` 403, two `transient_forbidden` 403, two 520)
and stores the plain-text edge error, for example the intermittent
`You cannot use different IP Addresses when using the API.` These are auditable
provenance for a failed call, not corpus corruption: no failed attempt
contributes a canonical row. The validator separates the two cases explicitly
so that a genuinely malformed *successful* body would still fail the gate.

## Cohort, splits, and reserved-partition integrity

| partition | frozen accounts | parsed subset | canonical history docs | canonical parsed docs |
|---|---:|---:|---:|---:|
| `DISCOVERY` | 600 | 128 | 600 | 116 |
| `CANDIDATE_TEST` | 300 | 128 | 300 | 119 |
| `CALIBRATION_RESERVED` | 150 | 0 | 0 | 0 |
| `SEALED_VALIDATION` | 150 | 0 | 0 | 0 |

```text
CALIBRATION_RESERVED touched: NO
SEALED_VALIDATION touched: NO
```

- 1,200 frozen members, 1,200 unique pseudonyms, identity overlap 0.
- Every canonical document's pseudonym exists in the frozen manifest and
  carries the split the manifest declares. No mismatch, no stray document.
- No reserved or sealed account appears in the parsed subset or in any
  canonical table.

The 21 parsed-subset accounts without a canonical parsed document are fully
accounted for by predeclared rules: 19 `skipped_anonymous` and 2
`no_valid_opportunities`. No account was topped up, replaced, or adaptively
reselected to compensate.

## Canonical table integrity

| measure | history | parsed |
|---|---:|---:|
| players | 900 | 235 |
| rows | 580,323 | 128,688 |
| unique match IDs | 571,929 | 127,692 |
| matches appearing for more than one sampled player | 8,182 | 923 |
| duplicate match rows within a player | 0 | 0 |
| rows deduplicated during canonicalization | 0 | 3,997 |
| rows outside the frozen 365-day window | 0 | 0 |
| rows with an invalid timestamp | 0 | 0 |
| median rows per player | 543 | 457 |
| min / max rows per player | 0 / 2,500 | 1 / 2,392 |
| canonical schema versions | 1 | 1 |
| forbidden provider fields present | none | none |

History completeness: 891 `complete`, 9 `truncated` at the 25-page safety
ceiling. Truncation is recorded, never treated as completeness, and the nine
affected players are flagged for exclusion from any estimand that assumes a
full 365-day window.

A match shared by two sampled players is expected and is not a dedupe error:
both operations are account-filtered, so the two rows describe different
players in the same match. The cross-player overlap is small (8,182 of 571,929
history matches, 1.4%) but is large enough to matter for any estimand that
would otherwise treat player-rows as independent draws over matches, and is
carried forward as a known dependency for the statistical tournament.

## Forbidden-surface gate

The canonical tables carry no rank, MMR, bracket, leaderboard, IMP, behaviour,
smurf, award, proprietary prediction, or playback field. The gate is executable
(`scripts/v7_research/corpus.py`, `tests/unit/test_v7_research_corpus.py`) and
fails closed: research code cannot request `CALIBRATION_RESERVED` or
`SEALED_VALIDATION` through the ordinary corpus reader at all, and a forbidden
field name anywhere in a canonical document is reported rather than ignored.

The name-based gate is a backstop, not the whole control. A hidden skill proxy
under an innocuous name is a semantic problem, and is handled by the candidate
review and the red-team pass rather than by this check.

## Known constraint carried into research

`GetParsedAcquisitionBatch` v1.0.0 deliberately omits the player's own
`networthPerMinute`, `lastHitsPerMinute`, `deniesPerMinute`,
`heroDamagePerMinute`, and `deathEvents`. Parsed evidence therefore supplies
match-level `radiantNetworthLeads`, `radiantKills`, `direKills`, and lane
outcomes, plus the player's own kill, assist, and item-purchase timings. Any
candidate family that requires a personal farm, damage, or death-timing
trajectory is not supported by this corpus and must not be designed around one.
This constraint is stated here so that discovery does not silently assume a
field the completed collection never acquired.

## Verdict

```text
research-ready: YES
critical findings: 0
recollection required: NO
```

Continue directly to canonical-table semantic validation and the neutral
capability atlas.
