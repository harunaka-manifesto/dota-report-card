# Free DNA — Death Context Final Completion

## Status

**PARTIAL** — the final transport campaign completed the frozen panel and the
registered analysis ran, but the candidate failed a frozen scientific gate.

## Terminal verdict

```text
DROP_DEATH_CONTEXT
```

Reason: the adjusted residual IQR was below the frozen `0.10` minimum.

## Final transport completion

- unresolved at start: 10;
- physical calls: 10;
- first-attempt successes: 10;
- retries: 0;
- retry successes: 0;
- unresolved at end: 0;
- final panel: 960 / 960;
- cost IDR: Rp20 pro rata (USD $0.001);
- replay parses: 0.

The final campaign used only the exact unresolved frozen IDs. It made no
replacement calls, adaptive top-up, replay parse, STRATZ, Steam, holdout, or
fresh sealed-validation call.

## Provider behavior

Final-10 campaign:

- 429s: 0;
- other transient failures: 0;
- request P50: 1.183s;
- P90: 1.657s;
- P95: 1.752s;
- max: 1.847s;
- pacing used: concurrency 1, 2.5s minimum start interval; observed start-gap P50 5.605s and minimum 4.977s;
- paced final-queue wall time: 51.748s.

Cumulative Death Context transport across the original supplement,
continuation, and final-10 campaigns was 1,000 physical GETs: 960 successful
details, 39 HTTP 429 attempts, one HTTP 500 attempt, 29 retries, and seven
retry successes. Cumulative request latency was P50 0.924s, P90 1.387s,
P95 1.587s, max 4.620s.

## Teamfight semantics

- status: LIKELY;
- core completeness: 100% across the complete 960-detail panel;
- malformed fights: 0;
- valid ten-player participant arrays: 960 / 960;
- valid unique player-slot mappings: 960 / 960;
- teamfight windows: 9,940;
- overlapping window pairs: 381;
- caveats: the numerator remains the provider-indexed teamfight player-death
  sum; overlapping provider windows are not an independently timed unique-death
  reconstruction.

## Personalization

- residual IQR: 0.091519 (FAIL; required `>=0.10`);
- dominant direction: negative, 17 / 32; dominant fraction 0.53125 (PASS;
  common-law stop not triggered);
- hero control: 0.875 direction retention (PASS);
- role control: 0.96875 direction retention (PASS);
- outcome/game-state control: 0.96875 direction retention (PASS);
- patch control: 0.96875 direction retention (PASS);
- median attenuation: -0.015198 (PASS; below 0.50);
- common-law stop: NOT TRIGGERED.

## Stability

- N20: split-half Spearman 0.329179; repeated-subsample sign agreement 1.000;
- N25: split-half Spearman 0.512097; repeated-subsample sign agreement 1.000;
- N30: split-half Spearman 0.509530; repeated-subsample sign agreement 1.000;
- lowest plausible N: N25 for the stability criterion, but no N is promoted because the residual-IQR gate failed;
- verdict: stability PASS at N25 and N30; overall candidate FAIL.

The complete deterministic run also evaluated N10 and N15; their split-half
Spearman values were 0.269062 and 0.290689 respectively, below the registered
stability threshold.

## Pilot gates

- frozen panel completion: PASS — 960 / 960;
- core fields `>=95%`: PASS — 100%;
- all details match stored parsed marker: PASS — 960 / 960;
- no replay parse workflow: PASS — 0;
- teamfight semantics: PASS for structural gate; semantic confidence LIKELY;
- adjusted residual IQR `>=0.10`: **FAIL — 0.091519**;
- dominant residual direction `<90%`: PASS — 0.53125;
- controls retain direction `>=70%`: PASS — hero 0.875, primary/outcome/game-state/patch 0.96875;
- median absolute attenuation `<50%`: PASS — -0.015198;
- N25/N30 stability: PASS;
- interpretation remains death-context composition: PASS;
- latency routing: final-10 paced transport was 51.748s, which is in the
  background/progressive band; this is not normal Free UX evidence.

## Product implication

- Death Context survives: **NO**;
- synchronous Free routing: not recommended; the final recovery transport
  would route background/progressive, and normal Free UX feasibility remains
  unvalidated;
- data-availability ceiling at recommended N: no recommended N after rejection;
  the outcome-independent N30 upper bound remains 391 / 1,609 profiles
  (24.30%);
- publication coverage known: NO.

## Next

- DROP: STOP; do not redesign;
- no calibration design was opened;
- no production report, V6.1 artifact, threshold, public contract, or deployment changed.

## Next prompt

```text
NOT CREATED
```

## Reusable corpus

- canonical path: `.local/corpora/opendota/free-dna-tier2/`;
- frozen panel records: 960 persisted successful live details;
- total normalized records: 979;
- manifest digest: `1ceafed83e7d001be14f40591d88aad871a81ff3c50c9001894a18258728bff1`;
- manifest SHA-256: `46ec54f8c8d56e775eeb26f5f0c04897616e8d857b4185308d690d4ab2332ff3`;
- provenance preserved: YES;
- analytical outcome results generated: YES, for this research-only rejection receipt.

## Execution note

The first local full-analysis attempt exposed two implementation defects in the
existing research helper: `expected_rate` returned a scalar where its caller
expected a pair, and the leave-match-out baseline looked up an all-panel
aggregate instead of a per-match aggregate. Both were corrected before the
accepted run. The corrections restore the already-registered
leave-player-and-match-out calculation; no estimator choice, threshold, gate,
panel, or production analytical behavior was changed. The invalid intermediate
outputs were discarded and are not evidence.

## Staging

- staging before: `2c6c18bea7780a4b9b42a66266853bf1458264ee`;
- completion commit: RECORDED AFTER INTEGRATION;
- staging after: RECORDED AFTER INTEGRATION;
- integrated: PENDING CLEANUP;
- main changed: NO.

## Cleanup

- temporary worktree removed: PENDING;
- temporary branch deleted: PENDING;
- unique local assets preserved: YES;
- unknown branches deleted: NO.

## Integrity

- panel changed = NO;
- replacements = 0;
- adaptive top-up = 0;
- replay parse requests = 0;
- STRATZ calls = 0;
- old holdout evaluated = 0;
- fresh sealed validation evaluated = 0;
- thresholds changed = NO;
- production analytical behavior changed = NO;
- deployment = NO.

## Completion receipt

```text
TASK TYPE: ANALYTICAL RESEARCH + DOCUMENTATION + REPOSITORY HYGIENE
BASE SHA: 2c6c18bea7780a4b9b42a66266853bf1458264ee
NEW SHA: RECORDED AFTER INTEGRATION
CHANGED FILES: research runner, frozen research helper, final evidence, rejection evidence, prior Death Context evidence/design records
BACKEND FILES CHANGED: NO
ANALYTICAL FILES CHANGED: YES (research execution helper only; frozen method restored)
PUBLIC REPORT CONTRACT CHANGED: NO
PERSISTED REPORT COMPATIBILITY TESTED: NOT APPLICABLE
PRODUCTION-SHAPED FIXTURE: NOT APPLICABLE
BROWSER E2E: NOT APPLICABLE
TYPECHECK: NOT APPLICABLE
LINT: PASS
BUILD: NOT APPLICABLE
ANALYTICAL BEHAVIOR CHANGED: NO (production)
HOLDOUT RERUN: NO
RECALIBRATION: NO
OPENDOTA QA CALLS: 10 final-10 recovery GETs
DEPLOYED: NO
SAFE TO MERGE: YES, pending owner review on local staging
```
