# V6.1 Session Drift Recovery — Phase 1 Plan

## Status

**PARTIAL — the analytical execution policy is complete, but Phase 2 must not
make provider calls until the owner approves the 5,347-request ceiling and a
monetary ceiling.**

## Integrity

```text
TASK TYPE: ANALYTICAL + DOCUMENTATION, Phase-1 research only
ALLOWED SCOPE: frozen tuning data, lineage metadata, offline predictive calculations, collection/split design, execution prompt
FORBIDDEN SCOPE: providers, old or fresh holdout evaluation, production analytical code, thresholds/artifacts, integration, deployment
STOP CONDITIONS: ambiguous lineage; adaptive collection; descriptor-enriched selection; weakened Session rules; provider access; production edit
ANALYTICAL BASE SHA: 3323511da91329dc6c6af3e090e10e1be944ecef
LATEST MAIN SHA: 6d088f76e3c0ca39a3649a6c80ee2cfb1db93d95
OWNER WORKTREE STATUS: codex/v61-case-notes at c4df42df12f7b14bad0cdbc2e32c7bb632ff81f5 with unrelated untracked work preserved
RESEARCH WORKTREE: /tmp/dota-report-card-v61-session-drift-phase1-plan on research/v61-session-drift-phase1-plan
```

The analysis used only the 791-profile tuning partition and aggregate/private
lineage metadata. It did not open either holdout's outputs. The diagnostic has
one runnable self-check for every fixed beta-binomial boundary. Network access
was unnecessary and no provider call occurred.

| binding | value |
| --- | --- |
| canonical corpus SHA-256 | `5b80bd29d6ecd04c92e4ba37051b7a71f23775007614b9f6a110d9efa2090216` |
| canonical split SHA-256 | `2aa3b4292c0a24d9ca209c5f885ebd1590e3032323362f111befae678d816231` |
| analytical source SHA | `7df38e6d234ae9c4ee425490bc40b8cc92685f85` |
| frozen artifact digest | `8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0` |

## Starting state

The frozen tuning partition contains 791 profiles. Session Drift is
inferentially supported for 63 and supplies a finite paired-margin observation
for 62, below the registered minimum of 100. The owner has fixed the target
V6.1 family universe as Transfer, Post-Loss, and Session Drift; Presence &
Exposure is deferred. No support, significance, practical-margin, stability,
or validation rule may be weakened to obtain the third family.

## Existing-data inventory

The local lineage contains exactly 40 eligible replacement-scan profiles that
were never assigned, used, or evaluated for Session. They are safe for the
tuning extension. The current 339-profile replacement holdout and the 339
historical revealed holdout are permanently unavailable for tuning. The 845
ineligible scan candidates and 10 previously screened reserves are also
unavailable; recollecting them because their earlier histories were weak would
change selection.

```text
CAN LOCAL DATA ALONE REACH THE TARGET? NO
```

The complete pool classification is local in `existing_data_pool_audit.csv`.

## Why Session Drift is scarce

The prior forensic remains binding: the median history has many sessions, but
the median session has two matches and median qualifying-session coverage is
19.4%. The four-match early/late requirement and 50% qualifying-session
coverage leave 63 supported profiles; odd/even margin estimation loses only
one more. This is target-population scarcity under the frozen question, not an
implementation defect.

## Support-rate model

The observed rate is `62 / 791 = 0.07838`; its Wilson 95% interval is
`[0.06162, 0.09922]`. Prediction uses the Jeffreys posterior
`Beta(62.5, 729.5)` and the beta-binomial distribution.

Descriptor diagnostics show why enrichment would materially change the
sample. They are descriptive only and are forbidden selection inputs.

| descriptor band | profiles | margin eligible | rate |
| --- | ---: | ---: | ---: |
| 30–59 matches | 85 | 0 | 0.0% |
| 60–119 matches | 136 | 1 | 0.7% |
| 120–239 matches | 127 | 3 | 2.4% |
| 240+ matches | 443 | 58 | 13.1% |
| median session length 1 | 177 | 0 | 0.0% |
| median session length 2 | 398 | 0 | 0.0% |
| median session length 3 | 143 | 4 | 2.8% |
| median session length 4+ | 73 | 58 | 79.5% |
| activity window under 90 days | 46 | 1 | 2.2% |
| activity window 270+ days | 585 | 46 | 7.9% |
| dominant-hero share under 10% | 191 | 25 | 13.1% |
| dominant-hero share 30%+ | 101 | 9 | 8.9% |

Full fixed-bin results, including session count and qualifying coverage, are
in `session_support_model.json`.

## Fixed sample-size calculation

Thirty-eight additional legitimate margin observations are required. A naive
plug-in calculation gives 1,276 total tuning profiles. The beta-binomial
predictive calculation requires 663 additional profiles for 95% assurance and
758 for 99% assurance:

| target | additional tuning profiles | total tuning N |
| --- | ---: | ---: |
| plug-in expectation | 485 | 1,276 |
| predictive 95% | 663 | 1,454 |
| predictive 99% | 758 | 1,549 |

## Recommended sample size

Freeze total tuning `N=1,600`: the existing 791, all 40 safe local reserves,
and exactly 769 new eligible tuning profiles. Under the fitted predictive
model, the probability of obtaining at least 38 additional margin observations
from the 809-profile extension is `0.99612`. The rounded buffer must not be
revised after Phase-2 inspection.

External eligibility is separately modeled from the completed 1,224-candidate
scan (`379 / 1,224 = 30.96%`, Wilson 95% `[28.44%, 33.61%]`) with a Jeffreys
`Beta(379.5, 845.5)` posterior. The tuning arm needs 2,848 candidate accounts
for 99.5% predictive assurance of at least 769 eligible profiles. The sealed
validation arm needs 1,287 candidate accounts for 99.5% assurance of at least
339. The union bound gives at least 99% assurance that both arms reach target.

## Sampling frame

Phase 2 must preserve the original, imperfect target population: public-profile
players observed in sampled OpenDota public matches. It excludes anonymous and
private players and is not representative of every Dota player; this bias is
documented rather than silently repaired.

The discovery frame is exactly 12 descending `/publicMatches` pages of 100 seed
matches and exactly 1,200 `/matches/{match_id}` expansions. Deduplicate positive
public account IDs, exclude every historical/current candidate and profile,
HMAC-rank, and retain the first 4,135. Fewer than 4,135 is a hard failure. No
extra page, retry, replacement, or top-up is allowed. Long-session, session
count/support/effect, Finding yield, and rank/MMR enrichment are forbidden.

## Split design

Before any provider call, Luna generates a 32-byte private salt and records its
SHA-256 digest. After fixed candidate discovery and deduplication, but before
any player-history request, rank accounts by
`HMAC-SHA256(salt, "v61-session-phase2:" + decimal_account_id)`:

- first 2,848: tuning arm; first 769 canonically eligible profiles are used;
- next 1,287: sealed validation arm; first 339 canonically eligible profiles
  are sealed; and
- extra eligible profiles remain unused reserve in their original arm.

Only request mechanics, bytes, response shape, and canonical eligibility may
be inspected for the validation arm. No family feature, effect, p-value,
margin, or Finding may be computed before the candidate is frozen. No separate
calibration arm is needed: practical-margin calibration remains tuning-only.

## Collection economics

| quantity | value | label |
| --- | ---: | --- |
| new candidate accounts | 4,135 | KNOWN |
| public-match page requests | 12 | KNOWN |
| seed-match detail requests | 1,200 | KNOWN |
| player-summary requests | 4,135 | KNOWN |
| maximum physical request ceiling | 5,347 | KNOWN |
| expected physical requests | 5,347 | ESTIMATED |
| history requests per candidate | 1 | KNOWN |
| measured archived bytes per prior candidate | 73,147 | MEASURED |
| estimated new raw archive | 288.5 MiB | ESTIMATED |
| estimated new canonical data | 287.4 MiB | ESTIMATED |
| estimated combined storage | 575.9 MiB | ESTIMATED |
| elapsed at 240 requests/minute | 22.3 minutes | ASSUMED |
| elapsed at 60 requests/minute | 89.1 minutes | ASSUMED |
| retries | 0 | KNOWN |
| currency cost | unknown until provider/pilot accounting | UNKNOWN |

Partial failures are recorded in their assigned arm and are never retried or
replaced. Requests are sequential and paced at no more than 240 physical
requests/minute. Any count shortfall fails its gate.

## Pilot decision

Use Option 2: the first 100 HMAC-ranked tuning-arm history requests form an
operational pilot and count toward the fixed 2,848. Luna may inspect request
mechanics, failure rate, response shape, cost, bytes, and runtime only. Pass
requires no schema break, at most 10 transport/HTTP failures, at most 250 MiB
for the 100 responses, and projected full-collection cost within the
owner-approved monetary ceiling.
Failure stops collection without changing the frame, counts, retry rule, or
assignment.

## Frozen processing contract

- One 365-day summary history request per candidate, provider limit 10,000,
  retry limit zero.
- Require valid summary fields; lobby type `{0,7}`; game mode `{1,22}`;
  leaver status `{0,1}`. Exclude leaver status `2–5`; fail closed on invalid
  values or conflicting duplicate match IDs; require 30 eligible matches.
- Sessionize at a 90-minute start-time gap with 300-second clock tolerance.
  Exclude corrupt, left-censored first, and right-censored last sessions.
- In each boundary-safe completed session with at least four matches, sort by
  `(start_time, session_index, match_id)`, compare equal `floor(n/2)` early and
  late match groups, omit an odd middle match, and calculate late win rate minus
  early win rate.
- Require at least 12 informative non-tie sessions, 30 early/late
  opportunities, and 50% qualifying-session coverage. Theta is mean session
  effect sign. The p-value is the existing two-sided, 2,000-draw seeded
  signed-prevalence randomization with its existing SHA-256 seed namespace and
  add-one rule.
- The margin is the existing linearly interpolated P90 at `(n-1)*.90` of
  absolute odd/even chronological-interleaved theta disagreement divided by
  two across at least 100 tuning profiles.
- Require at least six informative sessions in each half with matching full
  direction, at least 80% leave-one-session-out direction agreement, and
  dominant-hero exclusion retaining structural support and the same non-zero
  direction.

Failure codes and exact field wording are frozen in `processing_contract.json`.

## Phase-2 success/failure gates

1. Complete the exact fixed frame and request manifest within 5,347 requests;
   otherwise stop with no top-up.
2. Compare the 769 new eligible tuning profiles with the original 791 using
   the fixed support-model bins. For every descriptor, natural-log
   Jensen-Shannon divergence (zero terms contribute zero) must be at most 0.10
   and each absolute bin-share difference at most 0.15; otherwise stop without
   corrective sampling.
3. Obtain at least 100 combined legitimate Session margin observations;
   otherwise stop and keep Session deferred.
4. Derive a finite practical margin under the frozen method; otherwise stop.
5. Pass registered null/type-I, split-half, leave-one-out, dominant-hero, and
   evidence-completeness hardening; otherwise stop.
6. Pass fixed three-family BY `q=.05` multiplicity validation; otherwise stop
   without dropping a family or switching procedure for yield.
7. Freeze and hash the candidate, then run the sealed validation once. Any
   validation failure fails the V6.1 three-family release.

## Three-family multiplicity plan

The registered universe is exactly Transfer, Post-Loss, and Session Drift,
with unsupported registered families assigned `p=1`. The release procedure is
Benjamini–Yekutieli at `q=.05`, fixed `m=3`; BH is a diagnostic comparator only.
Both are evaluated under global/subset nulls, one moderate alternative,
independence, feasible negative dependence, correlations `.5` and `.9`, and
empirical tuning dependence, using 10,000 datasets per cell and seed `20260828`.
BY must meet estimated FDR `<=.055` with Wilson lower bound `<=.05` in every
registered null scenario. Publication yield never selects the procedure.
Presence & Exposure is not a fake fourth family.

## Fresh sealed validation plan

The 339-profile validation is designed but was not run. Before opening it,
freeze and hash the source SHA, corpus/split manifest, three-family universe,
estimators, null and p-value methods, practical margins, stability and
robustness gates, BY `q=.05`, and semantic publication rules. Run once with no
output-based exclusions.

Using frozen tuning counts, precompute central 99.4444444% Jeffreys
beta-binomial predictive intervals (Bonferroni familywise 95% across nine
checks) for each family's supported-profile count, positive-direction supported
count, and analytically-qualified-before-product-cap count. All
nine validation counts must lie inside, and qualified rows must have 100%
semantic evidence completeness. There is no minimum Finding-yield target. A
failure ends the V6.1 three-family release; validation profiles cannot be
recycled and the candidate cannot be retuned.

## Luna Phase-2 execution scope

The execution-only prompt is
`docs/prompts/v61-session-drift-phase2-luna-execution.md`. It fixes base SHA,
branch/worktree behavior, local pools, candidate counts, frame, split, request
ceiling, pilot, processing, gates, artifacts, and Definition of Done. It stops
before provider access until the owner approves cost and request ceilings.

## Owner decisions required

Approve or reject one material proposal: up to 5,347 OpenDota requests, about
576 MiB estimated new local storage, and an explicit currency ceiling that the
100-request pilot must verify. Statistical implementation choices are not
delegated to the owner or Luna.

## Recommended next action

Approve the fixed ceiling and monetary limit, then hand the execution-only
prompt to Luna Max. If the budget is rejected, Session Drift remains deferred
without weakening its contract.

## Files created

- `scripts/v61_session_drift_phase1_plan.py`
- `docs/evidence/free-dna-v6.1-session-drift-phase1-plan-2026-08-28.md`
- `docs/prompts/v61-session-drift-phase2-luna-execution.md`
- `.local/diagnostics/v61-session-drift-phase1-plan/` with the 12 required
  aggregate artifacts

## Integrity verification

```text
EXTERNAL PROVIDER CALLS = 0
OLD HOLDOUT PROFILES EVALUATED = 0
FRESH HOLDOUT PROFILES EVALUATED = 0
PRODUCTION ANALYTICAL CHANGES = 0
THRESHOLDS CHANGED = 0
SESSION MINIMUM LOWERED = 0
DEPLOYMENTS = 0
RAW ACCOUNT IDS IN TRACKED OUTPUT = 0
```
