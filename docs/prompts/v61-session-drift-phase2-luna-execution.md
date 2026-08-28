# V6.1 Session Drift Recovery — Luna Max Phase 2 Execution

## Purpose

Execute the approved fixed Session Drift data expansion. This is an
execution-only specification. Do not choose or change analytical policy.

## Exact starting point

```text
BASE SHA: 3323511da91329dc6c6af3e090e10e1be944ecef
ANALYTICAL SOURCE SHA: 7df38e6d234ae9c4ee425490bc40b8cc92685f85
FROZEN ARTIFACT DIGEST: 8e9e22a9fa36aa351abced843023b910488fea17c34c57b8d9b221c0c9b3aae0
```

Read `AGENTS.md`, all applicable nested instructions,
`docs/evidence/free-dna-v6.1-session-drift-phase1-plan-2026-08-28.md`, and the
canonical ingestion/session/Session calibration code in full. Verify the base,
`main`, `origin/main`, and active owner worktree before action.

Create an isolated worktree from the exact base on
`research/v61-session-drift-phase2`. Do not merge, rebase, cherry-pick, deploy,
or modify the owner's active worktree. Keep all provider payloads, account IDs,
split salt, and private manifests under `.local/`; commit only aggregate,
sanitized evidence and reproducible research code. Commit validated work and
remove only the temporary worktree at completion.

## Mandatory owner approval stop

Before generating a salt or making any provider call, obtain explicit owner
approval for all three limits:

```text
MAXIMUM PHYSICAL OPENDOTA REQUESTS: 5,347
ESTIMATED NEW LOCAL STORAGE: 576 MiB
MAXIMUM CURRENCY COST: owner must provide an explicit amount/currency
```

If any limit is not explicitly approved, return
`OWNER_COLLECTION_BUDGET_APPROVAL_REQUIRED` and stop. Approval authorizes this
fixed research collection only; it is not deployment permission.

## Scientific firewall

Never inspect the historical revealed holdout, current 339-profile replacement
holdout, or any validation-arm family output before the candidate is frozen.
Never use rank/MMR, Session support/effect, Finding yield, session length, or
session count to select an account. Never lower a support, margin, stability,
hardening, significance, or validation rule. Never make an adaptive top-up,
retry, or replacement request.

## Local tuning extension

Use all 40 eligible profiles in the unused replacement-scan reserve. Derive
them locally as the eligible candidates in the precommitted 1,224-candidate
replacement scan that are not among the first 339 selected holdout profiles.
Verify from metadata that the count is exactly 40, none was assigned to either
holdout, and no Session output was evaluated. Do not list raw identifiers in a
tracked file.

Do not reuse:

- the current 339-profile replacement holdout;
- the 339-profile historical revealed holdout;
- the 845 candidates ineligible in their fixed scan window; or
- the 10 previously screened reserves.

Any count or lineage mismatch is a hard stop.

## Private salt and provenance

After owner approval and before provider access:

1. Generate exactly 32 random bytes with a cryptographically secure generator.
2. Store the salt in a local mode-`0600` file.
3. Record its SHA-256 digest, creation time, base SHA, provider policy, and this
   prompt path in a local manifest. Do not track the salt.
4. Define rank as
   `HMAC-SHA256(salt, "v61-session-phase2:" + decimal_account_id)` with bytewise
   ascending digest order and decimal account ID as deterministic tie-breaker.

## Fixed candidate discovery

Reuse the existing `PublicMatchCollector` and OpenDota client behavior, but do
not call the existing adaptive `collect_until_target` loop. Implement or invoke
the smallest fixed-batch wrapper that performs exactly:

```text
12 /publicMatches requests
100 unique seed match IDs required per page
1,200 /matches/{match_id} detail requests maximum
pagination: next less_than_match_id = minimum seed match ID already attempted
rank/MMR filters: NONE
retries: 0
```

If a public page does not provide 100 unique seed match IDs, record failure and
stop. A failed seed detail remains failed; do not replace it. From successful
details, retain positive public account IDs, deduplicate, then exclude every
account/profile ever present in the historical candidate, original/current
population, previous reserve, replacement scan, tuning, or holdout manifests.

HMAC-rank the remaining accounts and retain exactly the first 4,135. If fewer
than 4,135 remain, fail Gate 1 and stop. Do not fetch another page.

## Predeclared arm assignment

Assign before any player-history request or feature/effect inspection:

```text
HMAC ranks 1..2,848     = TUNING EXTENSION ARM
HMAC ranks 2,849..4,135 = FRESH SEALED VALIDATION ARM
```

Write a private split manifest with candidate counts, HMAC digests, exclusion
manifest digests, arm digests, and salt digest. The tracked evidence may contain
counts and digests only.

Within each arm, preserve HMAC order:

- tuning: use the first 769 canonically eligible external profiles;
- validation: seal the first 339 canonically eligible profiles; and
- leave every additional eligible profile as unused reserve in its assigned
  arm.

Arm assignment and target counts never change after history acquisition.

## Fixed history collection

For each of the 4,135 assigned candidates, make at most one player-summary
history request under the existing contract:

```text
window: 365 days per profile
provider limit: 10,000
summary requests per candidate: 1
detail requests: 0
parse requests: 0
retry limit: 0
request pacing: sequential, no more than 240 physical requests/minute
```

Archive raw responses privately with pseudonymous filenames, request metadata,
checksums, and restrictive permissions. A transport/HTTP/private/unavailable
failure stays in its original arm and is never replaced.

The absolute provider ceiling for candidate discovery plus histories is 5,347
physical requests. Count failed physical attempts. Crossing or projecting a
crossing of the ceiling is a hard stop.

## Operational pilot

The first 100 HMAC-ranked tuning-arm history requests are the pilot and count
toward the fixed 2,848. Inspect only request mechanics, transport/HTTP failure
rate, response schema, request cost, byte size, and runtime. Do not normalize
Session features or compute support/effects.

Pilot passes only if:

```text
exactly 100 assigned requests attempted
schema-contract breaks = 0
transport/HTTP failures <= 10
total response/archive bytes <= 250 MiB
projected full-collection cost from provider accounting remains within owner-approved currency ceiling
```

On failure, stop before remaining history requests. Do not change count, frame,
assignment, retry rule, or threshold. On pass, continue the already-fixed
collection.

## Frozen canonical processing

Apply these rules verbatim:

1. One fixed 365-day history window. Required summary fields must normalize.
   Lobby type is `{0,7}`; game mode is `{1,22}`; leaver status is `{0,1}`.
   Exclude leaver status `2–5`, out-of-window rows, and unsupported modes/lobbies.
   Deduplicate match ID; conflicting duplicates fail closed. Require at least
   30 eligible matches per profile.
2. Sessionize by match start time with a 90-minute gap and 300-second clock
   tolerance using `sessions-5.0.0` behavior.
3. A boundary-safe completed session excludes corrupt sessions, the first
   left-censored session without a pre-window anchor, and the last
   right-censored session without a post-window gap over 90 minutes.
4. For each boundary-safe completed session with at least four matches, sort by
   `(start_time, session_index, match_id)`. Let `h=floor(n/2)`; early is the
   first `h`, late is the last `h`, and an odd middle match is omitted. Session
   effect is late win rate minus early win rate.
5. Require at least 12 informative non-zero completed-session effects, at least
   30 included early/late matches, and qualifying-session coverage at least
   50%. Theta is the mean sign of non-zero session effects.
6. Use `numpy.random.default_rng` and the existing two-sided signed-prevalence
   randomization with exactly 2,000 draws and add-one p-value. Seed from the
   first eight SHA-256 bytes, interpreted big-endian, of
   `research-signed-prevalence-calibration-1.0.0:<profile_key>:session_drift`.
   Session has one component.
7. Margin is the existing linear-interpolated P90 at index `(n-1)*.90` across
   legitimate tuning profiles of absolute odd/even chronological-interleaved
   session-theta disagreement divided by two. Both halves require at least six
   informative sessions. At least 100 finite margin observations are required.
8. Stability requires odd and even theta to be non-zero and match the full
   direction, plus at least 80% leave-one-session-out direction agreement.
9. Dominant-hero robustness excludes the profile's most-used hero, requires at
   least 30 remaining eligible matches and retained Session structural support,
   and must preserve the same non-zero direction.

Use the failure codes in the Phase-1 `processing_contract.json`. Do not create
new fallback logic or substitute a margin method.

## Validation-arm sealing rule

Before final candidate freeze, validation-arm processing may expose only:

- request success/failure;
- raw/canonical byte counts and checksums;
- response schema validity; and
- the canonical 30-match eligibility flag needed to select the first 339.

Do not compute sessions, descriptors, family features/effects, support, theta,
p-values, margins, robustness, or Findings for that arm. Encrypt or permission
separate its payloads if needed to enforce the boundary.

## Phase-2 gates

Evaluate in order; every failure stops without adaptive repair.

### Gate 1 — fixed collection

Pass only if the 12-page/1,200-detail frame is complete, 4,135 candidates were
assigned before history inspection, all attempted requests are within 5,347,
and private manifests/digests reconcile. Failure: stop; no top-up.

### Gate 2 — distribution continuity

Using only original tuning and the 769 selected external eligible tuning
profiles, apply the exact bin edges from Phase-1 `session_support_model.json`
for match depth, session count, median session length, activity window, and
dominant-hero share. Compute Jensen-Shannon divergence with natural logarithms,
midpoint `(p+q)/2`, and zero-probability terms contributing zero. For each
descriptor, require divergence `<=0.10` and every absolute bin-share difference
`<=0.15`. Failure: stop for Sol/owner review; do not corrective-sample.

### Gate 3 — margin count

Combine the original 791, 40 local reserves, and 769 selected external tuning
profiles. Pass only with at least 100 legitimate finite Session margin
observations. Failure: Session remains deferred; no top-up.

### Gate 4 — practical margin

Pass only if the frozen P90/2 method yields a finite practical theta margin
from at least 100 observations. Failure: stop; do not substitute a method.

### Gate 5 — Session hardening

Run the registered known-truth/null Type-I suite and the frozen split-half,
leave-one-out, dominant-hero, and evidence-completeness checks. Every registered
check must pass. Failure: Session remains research-only.

### Gate 6 — three-family multiplicity

Register exactly Transfer, Post-Loss, and Session Drift. Unsupported families
remain in the vector at `p=1`. Evaluate BH and BY at `q=.05`, fixed `m=3`, under
global null, subset nulls, one moderate alternative, independence, feasible
negative dependence, correlations `.5` and `.9`, and empirical tuning
dependence. Use 10,000 datasets per cell and seed `20260828`. BY is the release
procedure; BH is diagnostic only. Require BY estimated FDR `<=.055` and Wilson
lower bound `<=.05` in every registered null scenario. Failure: stop; do not
drop a family or switch for yield.

Presence & Exposure remains deferred and is not a fourth test.

## Candidate freeze and one-shot validation

Before opening the sealed arm, commit/hash one immutable candidate manifest
containing:

```text
source SHA
corpus and split manifests
three-family universe
estimators
null and p-value methods
practical margins
stability and robustness gates
BY multiplicity procedure, m=3, q=.05
semantic publication rules
all implementation/artifact checksums
```

Before reveal, use the final frozen tuning counts to compute central
99.4444444% Jeffreys beta-binomial
predictive intervals (two-sided equal tails; Bonferroni familywise 95% across
nine checks) for each family's supported-profile count, positive-direction
supported count, and analytically-qualified-before-product-cap count
in validation N=339. For each tuning count `s/n`, use posterior
`Beta(s+0.5,n-s+0.5)` and its beta-binomial predictive CDF; each integer bound
is the smallest count whose CDF reaches the relevant equal-tail probability
`0.025/9` or `1-0.025/9`. Freeze those nine integer intervals in the candidate
manifest. Do not define a minimum Finding-yield target.

Only after Gates 1–6 pass and the candidate manifest is frozen may Luna process
the first 339 canonically eligible validation profiles in HMAC order. Run once,
with no output-based exclusion. Pass only if all nine counts lie inside their
frozen intervals, qualified rows have 100% semantic evidence completeness, and
every frozen integrity/checksum/method gate passes. Any failure fails the V6.1
three-family release. Do not reuse the validation set or retune after reveal.

## Required local artifacts

Create `.local/diagnostics/v61-session-drift-phase2/` with at least:

1. `owner_approval.json`
2. `candidate_frame_manifest.private.json`
3. `split_manifest.private.json`
4. `pilot_report.json`
5. `request_accounting.json`
6. `collection_manifest.json`
7. `tuning_extension_corpus.json`
8. `sealed_validation_manifest.private.json`
9. `session_attrition_funnel.csv`
10. `distribution_shift.json`
11. `session_margin_calibration.json`
12. `session_hardening.json`
13. `three_family_multiplicity.json`
14. `candidate_freeze_manifest.json`
15. `fresh_validation_result.json`
16. `aggregate_summary.json`

Private artifacts may contain identifiers only under `.local` with restrictive
permissions. Aggregate artifacts and tracked evidence must not.

## Required tracked evidence

Create
`docs/evidence/free-dna-v6.1-session-drift-phase2-execution-2026-08-28.md`
with owner approval, exact request accounting, frame/split digests, pilot result,
support/margin counts, every gate, frozen candidate digest, validation result,
integrity counters, changed files, and repository lineage. Commit reproducible
research code and the sanitized evidence only.

## Checks

- Run the smallest direct self-check for candidate ranking/count boundaries.
- Run focused tests for any changed research/collection code.
- Run Ruff or repository-equivalent lint on changed Python.
- Verify all JSON parses and all required artifacts exist.
- Search tracked diff for raw account IDs, tokens, salts, payloads, and private
  cohort references.
- Confirm production code, frozen runtime artifacts, database, Redis, frontend,
  infrastructure, and deployment files are untouched.
- Inspect `git diff --name-only 3323511da91329dc6c6af3e090e10e1be944ecef...HEAD`.

## Stop conditions

Stop immediately on missing owner approval, lineage/count mismatch, insufficient
candidate frame, pilot failure, projected request-ceiling breach, protected
holdout access, validation-arm analytical inspection before freeze, adaptive
top-up/replacement pressure, processing ambiguity, any Gate 1–6 failure, or
one-shot validation failure. Report the failure; do not improvise.

## Definition of Done

Done means the owner budget was approved; the fixed frame, split, pilot, and
collection executed within 5,347 requests; the tuning extension used exactly
40 local plus 769 external eligible profiles; Gates 1–6 passed; the candidate
was frozen; the 339-profile validation ran once; all validation gates passed;
required private/aggregate artifacts and sanitized evidence exist; focused
checks pass; a validated research commit exists; no production/deployment state
changed; and the temporary worktree was cleaned up.

Return `THREE_FAMILY_VALIDATION_PASS` only if every condition is true. Otherwise
return the first exact failed gate or `OWNER_COLLECTION_BUDGET_APPROVAL_REQUIRED`.
