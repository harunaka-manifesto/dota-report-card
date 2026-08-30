# V6.1 Session Drift Phase 2 Execution

## Status
PARTIAL

This is a research-only execution record. OpenDota-derived data remains
provider-specific, validation remains sealed, and no production analytical
behavior was changed.

## Collection
- fixed candidate frame: 4135 (target 4135)
- physical OpenDota requests: 5346
- request ceiling: 5347
- estimated/API-recorded cost: 10800 IDR under owner-supplied assumption
- owner cost ceiling: 12,000 IDR
- retained storage: 323.43 MiB
- storage ceiling: 600 MiB
- adaptive top-ups: NO

## Reusable corpus
- raw/provider layer: `v61-session-drift-expansion/raw/`, immutable OpenDota response bodies with request ledger, status, bytes, and SHA-256
- normalized layer: `v61-session-drift-expansion/normalized/`, deterministic gzip-JSON tuning projections using frozen summary-history normalizer `summary-normalization-2.0.0` and canonical schema `v61-calibration-corpus-2.1.0`; fresh validation retained raw-only plus sealed eligibility status
- manifest/digest: raw `cb356a142b5ea59fca48b841e633a8e84adb4583f97228ec9afc820d06cd725d`, normalized `d964b3ff03db5c5aaa04203e147edbb9c1ae72db654c8e73aed44f7d763e9371`, split `800ff016abc0f6dcee558f0876fda194147efbcbd471290ca81f1c8f656bad31`
- pseudonymous identity: existing salted SHA-256 profile IDs plus private HMAC ranking; secret digest only
- V7/STRATZ reuse readiness: READY FOR FUTURE PROTOCOL, provider-specific layers remain separate
- important limitations: summary-only OpenDota data, sparse provider fields, no semantic equivalence with STRATZ, no validation reuse

## Reusable OpenDota corpus

### Provider provenance
OpenDota is the sole provider for this campaign; request identity, retrieval timestamps, HTTP status, response bytes, retry metadata, and SHA-256 digests are retained in the local ledger.

### Raw capture policy
Raw response bodies are immutable local-only capture artifacts. They are not included in the tracked commit.

### Normalized schema
Tuning projections are deterministic gzip-JSON envelopes using `summary-normalization-2.0.0` and `v61-calibration-corpus-2.1.0`. Fresh validation has raw capture plus sealed eligibility status only.

### Identity/pseudonymization
Profile IDs use the existing salted SHA-256 mechanism; HMAC ranking uses the private campaign salt. Only the salt digest is recorded in manifests.

### Split preservation
The fixed 4,135-account frame is split into 2,848 tuning and 1,287 fresh-sealed validation assignments before history inspection. The split manifest is versioned and digest-bound.

### Future V7/STRATZ reuse
The corpus is reusable for future authorized OpenDota research and V7/STRATZ comparison, with provider layers kept separate.

### Cross-provider limitations
OpenDota summary fields are not asserted to be semantically equivalent to STRATZ fields; future joins require an explicit mapping and visible missingness.

### Corpus digests
Raw, normalized, split, request-manifest, and private-salt digests are recorded in the local reusable-corpus and diagnostics manifests.

### Storage and cost
The campaign retained 323.43 MiB including diagnostics and recorded an estimated 10,800 IDR in whole 100-call blocks under the owner-supplied rate; both remain below the approved ceilings.

## Tuning
- existing tuning profiles: 791
- safe local reserves used: 40
- new external eligible tuning profiles: 769
- final tuning profiles: 1600

## Session Drift
- existing margin observations: 62
- new margin observations: 37
- combined margin observations: 99
- practical margin: None
- hardening: FAIL
- verdict: SESSION_DRIFT_REMAINS_DATA_LIMITED

## Three-family candidate
1. Transfer
2. Post-Loss
3. Session Drift

Presence & Exposure: DEFERRED

## Multiplicity
- procedure: Benjamini-Yekutieli
- q: 0.05
- stress result: NOT_RUN_SESSION_NOT_IMPLEMENTATION_READY (fixed m=3; BH diagnostic only)

## Tuning-only diagnostic
- 0 Findings: 0
- 1 Finding: 0
- 2 Findings: 0
- 3 Findings: 0
- NOT USED FOR TUNING DECISIONS: YES

## Fresh sealed validation
- target eligible profiles: 339
- collected/assigned: 1287
- analytically evaluated: 0
- status: SEALED

## Cost
- physical requests: 5346
- owner-supplied rate: Rp200 / 100 calls; $0.01 / 100 calls
- estimated IDR: 10800
- hard ceiling: 12,000
- exceeded: NO

## Next status
SESSION_REMAINS_BLOCKED

## Integration
- branch head at analysis: 43d8183f4b9be4bbf9cf096abf8b528598ce83e4
- latest main: 6d088f76e3c0ca39a3649a6c80ee2cfb1db93d95
- integration performed: NO
- recommended method: review this execution commit, then integrate tracked research code/evidence after owner approval; preserve local corpus outside main

## Branch / worktree disposition
- execution branch: execution/v61-session-drift-phase2
- base SHA: 43d8183f4b9be4bbf9cf096abf8b528598ce83e4
- final SHA: execution branch HEAD reported in the completion handoff
- temporary worktree removed: YES after final commit; verified in the completion handoff
- merged to main: NO
- should merge now: WAIT
- dependencies that must land first: NONE
- recommended integration order: 1. owner review; 2. merge tracked execution code/evidence if approved; 3. preserve local corpus and run a separately authorized validation/integration task
- raw/local corpus committed to main: NO

## Files / artifacts
- tracked runner: `scripts/v61_session_drift_phase2.py`
- tracked evidence: `docs/evidence/free-dna-v6.1-session-drift-phase2-execution-2026-08-28.md`
- local diagnostics: `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card/.local/diagnostics/v61-session-drift-data-expansion`
- local reusable corpus: `.local/corpora/opendota/v61-session-drift-expansion/`

## Integrity
- old revealed holdout used = NO
- fresh sealed validation evaluated = NO
- thresholds lowered = NO
- Session minimum lowered = NO
- long-session enrichment = NO
- adaptive top-up = NO
- raw provider provenance preserved = YES
- OpenDota data re-attributed to STRATZ = NO
- production analytical behavior changed = NO
- deployment = NO
