# V6.1 Session Drift Recovery — Luna Phase 3 Execution

## Purpose

Execute one fixed tuning-only acquisition wave. This is an execution-only
specification. Do not choose or change statistical policy.

## Exact starting point

```text
BASE SHA: c34f1a272005dda954af0932f7719a4cc230a23d
NEW BRANCH: execution/v61-session-drift-phase3
ANALYTICAL SOURCE SHA: 7df38e6d234ae9c4ee425490bc40b8cc92685f85
FROZEN ARTIFACT DIGEST: 8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0
TARGET SESSION MARGIN OBSERVATIONS: 110
PHASE-3 ELIGIBLE TUNING PROFILES: 407
PHASE-3 CANDIDATE ACCOUNTS: 792
VALIDATION ARM EXTENSION: NONE
```

Read `AGENTS.md`, every applicable nested instruction, the Phase-1 and Phase-2
Session Drift evidence and prompts, the Phase-2 runner, the complete local
Phase-2 diagnostics/corpus manifests, and
`docs/evidence/free-dna-v6.1-session-drift-phase3-plan-2026-08-28.md` before
action.

Verify the exact base, `main`, `origin/main`, the owner worktree, and the local
Phase-2 corpus. Check whether `execution/v61-session-drift-phase3` exists
locally or remotely. Reuse it only if it is the intended clean lineage;
otherwise stop with `BRANCH_NAME_COLLISION`. Never reset or delete an unknown
branch.

Create an isolated temporary worktree from the exact base. Do not merge,
rebase, cherry-pick, deploy, or modify the owner's active worktree. Commit only
reproducible runner code and aggregate sanitized evidence. Keep provider
payloads, salts, account IDs, private manifests, and profile-level outputs
under `.local/` with restrictive permissions.

## Mandatory owner approval stop

Before generating the Phase-3 salt or making any external call, require this
exact approval or an unambiguously equivalent approval:

> I approve the fixed V6.1 Session Drift Phase-3 tuning-only wave of 792 candidate accounts, exactly 4 public-match pages and 400 seed-match details, a hard ceiling of 1,196 physical OpenDota calls, Rp2,400 under the supplied whole-block rate, and 100 MiB additional retained storage, with zero retries, replacements, adaptive stopping, or top-ups.

If approval is absent, return
`OWNER_PHASE3_COLLECTION_BUDGET_APPROVAL_REQUIRED` and stop before salt
creation or provider access. Approval is research collection permission only;
it is not implementation, validation reveal, merge, or deployment permission.

## Hard firewall

You may inspect tuning outputs and the eligibility/count/integrity metadata
explicitly permitted for sealed validation. You must not:

- call STRATZ or Steam;
- inspect the old revealed holdout;
- compute any feature, effect, p-value, margin, Finding, or analytical output
  for any fresh sealed-validation profile;
- reassign any sealed-validation profile to tuning;
- reuse any old holdout or Phase-2 candidate as Phase-3 tuning;
- retry the two Phase-2 canceled/no-response assignments;
- lower the 100-observation minimum;
- change eligibility, sessionization, estimator, p-value, margin, stability,
  hardening, or semantic rules;
- change Transfer or Post-Loss;
- enrich on session length, completed-session count, Session support/effect,
  Finding yield, rank, or MMR;
- stop early or top up;
- change production code or artifacts; or
- deploy or merge.

Required final integrity:

```text
OLD REVEALED HOLDOUT EVALUATED = 0
FRESH SEALED VALIDATION ANALYTICALLY EVALUATED = 0
PRODUCTION ANALYTICAL BEHAVIOR CHANGED = NO
```

## Phase-2 evidence that must reconcile

Before collection, verify:

```text
fixed candidate frame = 4,135
physical requests = 5,346
interrupted/canceled markers = 2
tuning candidates = 2,848
tuning histories fetched = 2,848
canonically eligible tuning-arm profiles = 1,609
selected Phase-2 external tuning profiles = 769
unused eligible Phase-2 tuning-arm reserve = 840
fresh validation candidates = 1,287
fresh validation eligible-status count = 745
fresh validation analytically evaluated = 0
original/local/external Session margin observations = 62 / 2 / 35
combined Session margin observations = 99
distribution continuity = PASS
```

Any mismatch is `PHASE2_LINEAGE_OR_COUNT_MISMATCH` and a hard stop. The 840
unused eligible Phase-2 profiles remain excluded; do not use them as a cheaper
substitute.

## Private prior-candidate exclusion universe

Reconstruct the union before Phase-3 ranking from private manifests and raw
Phase-2 seed-detail capture. It must include:

1. all 4,135 Phase-2 fixed-frame accounts;
2. all 4,423 positive public accounts observed in the complete Phase-2
   seed-detail capture, including the 288 not retained in the fixed frame;
3. all original 791 tuning profiles;
4. all 40 local reserves;
5. all 339 historical revealed holdout profiles;
6. all 339 fresh replacement-holdout profiles;
7. all 1,287 Phase-2 fresh-validation candidates;
8. both canceled/no-response assignments;
9. all previously screened reserves, historical/current candidate pools, and
   earlier research candidate sets; and
10. all prior seed match IDs.

Store the union privately with mode `0600`. Record its count, source-manifest
digests, and canonical sorted-set SHA-256. No raw account, match, Steam,
profile, holdout, or validation identifier may enter a tracked file.

If the private sources cannot reconstruct the complete union, stop with
`PRIOR_CANDIDATE_EXCLUSION_INCOMPLETE`.

## Private salt and ranking

Only after owner approval:

1. Generate exactly 32 cryptographically secure random bytes.
2. Store them in a mode-`0600` local file.
3. Publish only the SHA-256 digest.
4. Rank remaining candidates by
   `HMAC-SHA256(salt, "v61-session-phase3:" + decimal_account_id)`.
5. Sort bytewise ascending digest, then decimal account ID as deterministic
   tie-breaker.

The campaign ID is `v61-session-drift-phase3-2026-08-28`. Do not reuse the
Phase-2 salt or `v61-session-phase2:` namespace.

## Exact fixed discovery frame

Continue strictly below the minimum seed match ID already attempted in the
Phase-2 fixed discovery. Use the private Phase-2 frame/raw manifest to obtain
that cursor; do not place the raw ID in tracked evidence.

Execute exactly:

```text
/publicMatches pages: 4
unique seed matches required per page: 100
/matches/{match_id} details: 400 maximum and expected
pagination: next less_than_match_id = minimum seed match ID already attempted
rank/MMR filters: NONE
retries: 0
```

Each page must yield 100 unique positive seed match IDs after excluding all
prior seed IDs. Attempt each of the fixed 400 details once. A failed detail
remains failed; do not replace it.

From successful details, collect positive public account IDs, deduplicate, and
apply the complete prior-candidate exclusion union. HMAC-rank the remainder
and retain exactly the first 792. If fewer than 792 remain, fail Gate 1 with
`PHASE3_FIXED_DISCOVERY_SHORTFALL`. Do not fetch a fifth page or another
detail.

## Assignment and split behavior

Phase 3 has one arm only:

```text
HMAC ranks 1..792 = TUNING EXTENSION CANDIDATES
VALIDATION ARM = NONE
```

Freeze and digest the 792-account assignment before any player-history
request or canonical/profile feature inspection.

Process every candidate history. In HMAC order, select the first 407 profiles
that pass the unchanged canonical 30-match eligibility contract. Later
eligible profiles remain unused reserve. If fewer than 407 are eligible, Gate
1 fails. Do not use Session support, effects, margins, or Findings to choose or
replace a profile.

## Fixed history collection

For each of all 792 candidates, make at most one OpenDota player-summary
history request:

```text
window: fixed 365 days
provider limit: 10,000
summary requests per candidate: 1
detail requests after discovery: 0
parse requests: 0
retry limit: 0
request pacing: sequential, no more than 240 physical requests/minute
```

Archive response bytes immutably with provider provenance, timestamps, status,
request parameters, byte count, SHA-256, retry metadata, and pseudonymous
filename. A transport, HTTP, schema, private, unavailable, or normalization
failure stays terminal and is not replaced.

The absolute physical OpenDota request ceiling is:

```text
4 public pages + 400 seed details + 792 histories = 1,196
```

Count every physical attempt, including failed responses. Crossing or
projecting a crossing of 1,196 is a hard stop. Retained Phase-3 corpus plus
diagnostics must not exceed 100 MiB. Whole-block cost must not exceed Rp2,400
under the owner-supplied rate. No pilot is needed: Phase 2 already established
schema, request, cost, size, and runtime mechanics under the identical history
contract.

## Exact no-optional-stopping rule

> **Collect/process the entire fixed Phase 3 frame even if Session observation #100, #110, or the target is reached early. Do not stop because the target has been reached. Do not top up if the target is missed.**

This rule applies to discovery, all 792 histories, canonical normalization, and
the fixed first-407 tuning selection. Evaluate the planned evidence exactly
once after the full fixed wave.

## Frozen canonical processing

Use the existing Phase-2 runner and canonical modules. Make only the smallest
fixed-count/campaign-append changes necessary. Apply these rules verbatim:

1. Normalize one 365-day summary history per candidate with
   `summary-normalization-2.0.0` into `v61-calibration-corpus-2.1.0`.
2. Required summary fields must be valid. Lobby type is `{0,7}`, game mode is
   `{1,22}`, and leaver status is `{0,1}`. Exclude leaver status `2–5`, rows
   outside the fixed window, and unsupported modes/lobbies. Fail closed on
   invalid fields or conflicting duplicate match IDs. Require at least 30
   eligible matches.
3. Sessionize with `sessions-5.0.0`: 90-minute start/end-aware queue gap and
   300-second clock tolerance.
4. Exclude corrupt sessions, the first left-censored session without a
   pre-window anchor, and the last right-censored session without a post-window
   gap over 90 minutes.
5. In each boundary-safe completed session with at least four matches, sort by
   `(start_time, session_index, match_id)`. Let `h=floor(n/2)`; early is the
   first `h`, late is the last `h`, and an odd middle match is omitted. Session
   effect is late win rate minus early win rate.
6. Require at least 12 informative non-tie completed-session effects, at least
   30 included early/late matches, and qualifying-session coverage at least
   50%. Theta is mean sign of non-zero session effects.
7. Use the unchanged two-sided 2,000-draw signed-prevalence randomization,
   `numpy.random.default_rng`, add-one p-value, and first-eight-SHA-256-byte
   big-endian seed namespace
   `research-signed-prevalence-calibration-1.0.0:<profile_key>:session_drift`.
8. The Session practical margin is the linearly interpolated P90 at
   `(n-1)*.90` of absolute odd/even chronological-interleaved theta
   disagreement, divided by two, across the pooled legitimate tuning
   profiles. Both halves require at least six informative sessions.
9. Stability requires odd and even theta to be non-zero and match the full
   direction plus at least 80% leave-one-session-out direction agreement.
10. Dominant-hero robustness excludes the profile's most-used hero, requires
    at least 30 remaining eligible matches and retained structural support,
    and must preserve the same non-zero direction.

Use existing failure codes. Do not add fallback logic or substitute a method.

## Pooling and continuity

Append exactly the first 407 eligible Phase-3 profiles to:

```text
791 original tuning
+ 40 safe local reserves
+ 769 Phase-2 external tuning
= 1,600 prior tuning
```

The resulting tuning set is 2,007 profiles. Record the corpus append as
`v61-session-drift-calibration-lineage-1.1.0`. Keep estimator version
`research-signed-prevalence-calibration-1.0.0`; the lineage bump records new
data, not a method change.

Before pooling, compare the 407 Phase-3 profiles separately with:

1. the original 791 tuning profiles; and
2. the Phase-2 external 769 profiles.

For match depth, session count, median session length, activity-window days,
and dominant-hero share, use the exact Phase-1/2 fixed bins. For both
comparisons require natural-log Jensen–Shannon divergence `<=0.10` and every
absolute bin-share difference `<=0.15`. Zero-probability terms contribute
zero. Failure stops without corrective sampling.

Retain `campaign_id` and `source_arm` for diagnostics. Weighting is forbidden.
Selective exclusions are forbidden beyond canonical eligibility and the
predeclared first-407 HMAC order.

## Ordered Phase-3 gates

Evaluate once, in order.

### Gate 1 — operational integrity

Pass only if the exact 4-page, 400-detail, 792-history frame completes within
1,196 physical requests, Rp2,400, and 100 MiB; all 792 assignments are frozen
before history inspection; and at least 407 are canonically eligible. Failure:
stop with no retry, replacement, extra page, or top-up.

### Gate 2 — provenance

Pass only if exclusion, frame, split, request, raw, normalized, and campaign
manifests/digests reconcile and contain no cross-arm or prior-frame member.

### Gate 3 — distribution continuity

Pass both fixed comparisons exactly as specified above. Failure: stop; do not
weight, trim, or corrective-sample.

### Gate 4 — combined Session evidence

Count legitimate finite pooled Session margin observations and classify:

```text
<100      = HARD_ANALYTICAL_FAILURE
100..109  = FROZEN_MINIMUM_MET_BUT_PHASE3_EVIDENCE_TARGET_MISSED
>=110     = PLANNED_EVIDENCE_TARGET_ACHIEVED
```

Only `>=110` passes Gate 4. Do not top up after either failure state.

### Gate 5 — practical margin

Derive one finite margin under the unchanged pooled P90/2 method. No alternate
quantile, interpolation, denominator, or fallback is permitted.

### Gate 6 — Session hardening

Run the registered known-truth/null Type-I suite and unchanged split-half,
leave-one-session-out, dominant-hero, and evidence-completeness checks. Every
registered check must pass.

### Gate 7 — exact three-family multiplicity

Register exactly:

1. Transfer
2. Post-Loss
3. Session Drift

Presence & Exposure is deferred and is not a fourth test. Unsupported families
remain at `p=1`.

Use fixed `m=3`, `q=.05`, BY release procedure, BH diagnostic comparator,
10,000 datasets per cell, 2,000 signed-prevalence null draws, and seed
`20260828`. Run complete null, mixed truth/one moderate alternative, and subset
nulls under independence, positive dependence `rho=.5` and `.9`, feasible
adverse dependence `rho=-.25`, and empirical tuning dependence.

Pass only if every registered BY null cell has estimated FDR `<=.055` and
Wilson lower bound `<=.05`. Do not select a procedure, family set, or scenario
based on Finding yield.

### Gate 8 — candidate freeze

Before any sealed-validation analytical access, hash-freeze:

- source SHA and clean-state assertion;
- both campaign corpus and combined manifests/digests;
- the exact three-family universe;
- estimators, nulls, p-values, and seeds;
- practical margins;
- stability, robustness, evidence, and semantic rules;
- BY `m=3`, `q=.05`;
- implementation/artifact checksums; and
- the nine one-shot validation predictive intervals computed from the final
  pooled tuning counts under the existing protocol.

This task does **not** open or run fresh validation. Stop after candidate
freeze and return a separate owner-review handoff. Sealed validation requires a
later explicit one-shot authorization.

## Reusable-corpus append

Do not overwrite any Phase-2 corpus byte or manifest. Create:

`.local/corpora/opendota/v61-session-drift-phase3-extension/`

with these immutable layers:

```text
raw provider capture
→ normalized OpenDota projection
→ cohort/split manifests
→ derived analytical features
```

Record provider, retrieval time, endpoint/request identity, response status,
bytes, SHA-256, retry metadata, normalizer/schema/sessionizer versions,
campaign ID, private-salt digest, and deterministic corpus digests. Use the
same salted SHA-256 pseudonym scheme with a new salt. Create a combined corpus
manifest that references, rather than rewrites, Phase-2 raw/normalized/split
digests.

Keep OpenDota provider-specific. Do not claim semantic equivalence with STRATZ.
Preserve future V7 cross-provider reuse through explicit field mapping and
visible missingness.

## Required local artifacts

Create `.local/diagnostics/v61-session-drift-phase3-execution/` with at least:

1. `owner_approval.json`
2. `phase2_lineage_reconciliation.json`
3. `prior_candidate_exclusion.private.json`
4. `candidate_frame_manifest.private.json`
5. `split_manifest.private.json`
6. `request_ledger.jsonl`
7. `request_failure_ledger.json`
8. `collection_manifest.json`
9. `raw_corpus_manifest.json`
10. `normalized_corpus_manifest.json`
11. `combined_corpus_manifest.json`
12. `tuning_extension_corpus.json`
13. `distribution_continuity_audit.json`
14. `old_vs_phase3_support_report.json`
15. `phase2_vs_phase3_support_report.json`
16. `session_margin_calibration.json`
17. `session_hardening.json`
18. `three_family_multiplicity.json`
19. `candidate_freeze_manifest.json`
20. `predictive_intervals.json`
21. `cost_ledger.json`
22. `aggregate_summary.json`

Private files may contain identifiers only under `.local`, mode `0600`. No raw
identifier or secret may be committed.

## Required tracked evidence

Create
`docs/evidence/free-dna-v6.1-session-drift-phase3-execution-2026-08-28.md`
with owner approval, exact request/cost/storage accounting, frame and exclusion
digests, conversion funnel, support counts, both continuity comparisons, every
gate result, margin/hardening/multiplicity results, candidate-freeze digest,
sealed-validation counter `0`, integrity counters, changed files, and branch
lineage.

Commit the smallest execution runner changes and sanitized evidence only.

## Checks

- Run the runner's direct self-checks for HMAC determinism, fixed boundaries,
  zero retries, selection of first 407 eligible profiles, and request ceiling.
- Run focused repository tests for changed research code.
- Run repository-equivalent Python lint/format checks on changed Python.
- Parse every required JSON/JSONL artifact and verify every required file.
- Recompute all recorded SHA-256 digests.
- Search the tracked diff for raw account/match/Steam/profile IDs, tokens,
  salts, payloads, and private cohort references.
- Confirm production API, worker, web, database, infrastructure, frozen
  runtime artifacts, and deployment files are untouched.
- Inspect `git diff --name-only c34f1a272005dda954af0932f7719a4cc230a23d...HEAD`.

## Stop conditions

Stop immediately on:

- missing owner approval;
- base, branch, Phase-2 count, lineage, or digest mismatch;
- incomplete prior-candidate exclusion;
- fewer than 100 unique seeds on a fixed page;
- fewer than 792 candidates after the fixed discovery/exclusion;
- projected or actual request, cost, or storage ceiling breach;
- fewer than 407 canonically eligible profiles;
- protected holdout access;
- any sealed-validation analytical inspection;
- adaptive retry, replacement, enrichment, optional stopping, or top-up
  pressure;
- distribution-continuity failure;
- final Session margin count below 110;
- non-finite frozen margin;
- Session hardening failure;
- exact `m=3` BY failure;
- inability to freeze the candidate completely;
- Phase-2 corpus overwrite;
- production, artifact, public-contract, database, infrastructure, or
  deployment change; or
- private identifiers in tracked output.

Report the first failure exactly. Do not improvise.

## Cleanup and branch disposition

After all applicable gates/checks:

1. commit tracked runner/evidence changes on
   `execution/v61-session-drift-phase3`;
2. record base SHA and final execution SHA;
3. preserve both local corpora and all private diagnostics;
4. remove only the temporary execution worktree if clean and safe;
5. keep the execution branch;
6. do not merge to main;
7. do not open sealed validation; and
8. do not deploy.

## Definition of done

Execution is done only if the fixed wave completed inside all ceilings; the
first 407 eligible profiles were selected without output-based choice; both
continuity comparisons passed; the combined legitimate margin count reached
at least 110; the frozen margin, Session hardening, and exact `m=3` BY grid
passed; the candidate was fully frozen; validation remained analytically
sealed; required private/aggregate artifacts and tracked evidence exist;
focused checks pass; no private data was committed; and no production or
deployment state changed.

Return `PHASE3_CANDIDATE_FROZEN_READY_FOR_OWNER_REVIEW` only if every condition
is true. Otherwise return the first exact failed gate/status.
