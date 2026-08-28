# Luna Pilot — Free DNA Death Context Tier-2

This is a bounded development-only OpenDota match-detail pilot. It tests one candidate:

> Of a player's deaths, how unusually often do they occur inside OpenDota-detected teamfights?

It is not production implementation, calibration, holdout validation, or permission to create other Death Context branches.

## Exact lineage and worktree

```text
REPO: harunaka-manifesto/dota-report-card
BASE: 7f08346a5fed34fa232b9a3648bbc1241e9c2930
BRANCH: research/free-dna-death-context-tier2-pilot
WORKTREE: /tmp/dota-death-context-tier2-pilot
```

Manage Git yourself. Verify the base exists and the fixed worktree path is absent. If the branch already exists with unknown/conflicting work, stop with `BRANCH_NAME_COLLISION`. Create the isolated worktree from the exact base. Do not touch the owner worktree, merge/rebase main, or deploy.

Read first:

- `/AGENTS.md` and relevant nested instructions;
- `docs/agent/production-safety.md`;
- `docs/agent/analytical-release-invariants.md`;
- `docs/evidence/free-dna-death-context-feasibility-2026-08-28.md`;
- `docs/design/free-dna-death-context-research-design.md`;
- `.local/diagnostics/free-dna-death-context-feasibility/`; and
- the prior parsed-feasibility evidence and diagnostics.

Before any provider access, print the task type, allowed/forbidden scope, stop conditions, base/main/worktree state, corpus digest state, exact request/cost/storage ceiling, and owner approval state.

## Hard owner approval gate

Complete all offline preflight, deterministic selection, code checks, and budget calculations, then stop. Do not make the first provider call unless the owner explicitly approves this exact ceiling in the active task:

```text
I approve up to 960 OpenDota match-detail GETs, Rp1,920 and $0.096 pro rata, 384 MiB local storage, zero retries, zero replay parse requests, and immediate stop on marker, schema, rate-limit, or budget failure.
```

No approval means return `BLOCKED — OWNER APPROVAL REQUIRED`. Approval for an earlier four-call QA or another campaign does not transfer.

## Hard firewall

Allowed after approval:

- GET `/matches/{match_id}` only for the 960 deterministically frozen, already-parsed match IDs;
- local immutable raw corpus storage, normalization, aggregate research analysis, and latency instrumentation; and
- tracked aggregate evidence/design updates without private identifiers.

Forbidden:

- replay parse POSTs, parse polling, or `OpenDotaParseClient`;
- fetching any match whose stored summary marker is not exactly `source_version == "22"`;
- history, public-match, STRATZ, Steam, or other provider calls;
- retries or outcome/payload/error-based replacements;
- old revealed holdout or fresh sealed-validation analytics;
- production analytical behavior, V6.1 thresholds/methodology/artifacts/source binding, report contracts, backend/frontend/database/infrastructure changes; and
- deployment, merging main, production flags, or environment changes.

Required final integrity:

```text
OpenDota GETs <= 960
replay parse requests = 0
retries = 0
STRATZ calls = 0
Steam calls = 0
old holdout evaluated = 0
fresh sealed validation analytically evaluated = 0
production analytical behavior changed = NO
deployed = NO
```

## Fixed panel

- Development/tuning profiles: **32**.
- Stored parsed-match minimum: **30**.
- Matches/profile: **30**.
- Total unique match IDs and detail GETs: **960**.
- Nested analysis prefixes: `N={10,15,20,25,30}`.
- Physical-call ceiling: **960**.
- Cost ceiling: **Rp1,920 and $0.096 pro rata**, currencies calculated independently.
- Storage ceiling: **384 MiB**, counting raw bodies, ledgers, normalized rows, and derived outputs.
- Replay parse requests: **0**.
- Retries: **0**.

Do not expand the panel if profiles, fields, responses, or signals are disappointing.

## Deterministic sampling before detail inspection

1. Use the existing eligible development/tuning profiles only. Never open validation profiles.
2. Create a new private 32-byte salt with mode `0600`. Commit only its SHA-256 digest and algorithm metadata, never the salt.
3. Profile rank: `HMAC-SHA256(salt, "death-context-profile:" + private_profile_identity)`, ascending digest with stable private identity as the tie-breaker.
4. Candidate matches are stored summary rows with exact `source_version == "22"`.
5. Match rank within profile: `HMAC-SHA256(salt, "death-context-match:" + decimal_match_id)`, ascending digest then numeric match ID.
6. Walk profiles in rank order. Select a profile only if it can contribute 30 match IDs not already assigned to an earlier selected profile. Take its first 30 globally unique ranked IDs.
7. Stop selection when exactly 32 profiles and 960 unique IDs are frozen.
8. Complete and digest the selection manifest before opening or requesting any selected detail payload.

Skipping is allowed only for insufficient stored parsed support or cross-profile duplicate IDs during this offline freeze. There are no replacements after detail inspection begins, including for 404, timeout, schema failure, latency, missing fields, or candidate outcome.

Do not print or commit raw account IDs, Steam IDs, match IDs, private profile identities, or the HMAC salt.

## Minimal QA is part of the panel

The first four selected match-detail GETs are sequential and count toward 960. For each require:

- stored summary `source_version == "22"`;
- detail `version == 22`;
- `od_data.has_parsed == true`;
- ten player rows with stable slot/order mapping;
- `teamfights` with ten-player arrays when non-empty;
- total player deaths and per-fight player deaths are nonnegative and fight deaths never exceed total deaths;
- hero, role, result, duration, patch, and advantage timeline have the expected shape;
- the transport is GET-only and no parse client/endpoint is imported or called; and
- request duration and bytes are recorded.

Any failure stops the campaign after four or fewer calls. Do not substitute a fifth match.

## Provider-safe request execution

After QA passes:

- zero retries;
- no more than 240 request starts/minute;
- bounded concurrency only: 1, 5, and 10;
- record a physical request in an append-only ledger before interpreting its response;
- preserve every successful body immutably with SHA-256 and byte count; and
- stop on 429, unexpected billing/auth behavior, schema drift, parse workflow evidence, indeterminate interrupted request, or any call/storage ceiling risk.

Use predeclared contiguous HMAC-order batches to measure concurrency. Include at least one complete 30-match profile at concurrency 1, one at 5, and one at 10. Execute the rest at 10 only if the earlier modes have no stop condition. Do not refetch a match to create a timing sample.

## Reusable Tier-2 corpus

Preserve locally:

```text
.local/corpora/opendota/free-dna-death-context-tier2/
  manifests/
  raw/responses/
  normalized/
```

Required manifests:

- lineage/base and provider;
- private-salt digest and HMAC algorithms;
- frozen profile/match selection digests;
- request/cost/storage ceilings;
- append-only request ledger digest;
- raw file paths, bytes, status, retrieval time, and SHA-256;
- normalized schema/version and source-body binding; and
- explicit validation/holdout non-use.

Local private manifests may contain identifiers with mode `0600`. Tracked outputs must contain aggregates and digests only.

Normalize one row per player-match with target-profile membership kept private. Preserve missing/null states. At minimum retain slot, hero, lane role, side/result, duration, patch, total deaths, teamfight windows and indexed player deaths, team gold-advantage series, parse state, and source digest. Do not fabricate absent fields.

## Field completeness audit

Report aggregate completeness and shape for:

- target slot/order mapping;
- total player deaths;
- teamfight start/end and ten-player arrays;
- teamfight player deaths;
- hero;
- lane/role;
- result/side;
- duration;
- patch;
- gold-advantage timeline;
- objectives and kills logs as diagnostics only; and
- `lane_pos` as a non-timeline diagnostic only.

The primary core fields must be at least 95% complete. Exact death timestamps, pre-objective context, phase context, and proximity are not fallback analyses.

## Frozen Death Context calculation

For target player `p` in match `m`:

```text
D_pm = players[target].deaths
F_pm = sum(teamfight.players[target_index].deaths across detected fights)
S_p  = sum(F_pm) / sum(D_pm)
```

Require at least 25 selected matches and 100 total deaths for a pilot-supported profile. Preserve zero-death matches in the match count and resampling; they contribute zero to numerator/denominator.

The personal residual is:

```text
theta_p = S_p - expected_S_p
```

Estimate `expected_S_p` from non-target player rows while leaving the target profile and entire target match out.

Primary death-weighted post-strata:

```text
lane_role × outcome × player-team-ahead-exposure quintile × patch
```

- Ahead exposure is the fraction of available minute points where the target player's team is ahead; invert Radiant advantage for Dire.
- Freeze quintile boundaries once from the complete development panel before calculating target residuals.
- Require at least 100 reference deaths per usable primary stratum.
- Unsupported player-match rows abstain; no fallback is allowed for the primary adjusted estimate.

Hero sensitivity:

```text
hero_id × outcome × patch
```

Require 100 reference deaths. If and only if that cell is structurally below support, use the predeclared `hero_id × outcome` fallback with the same minimum. Record fallback use.

Also report:

- unadjusted population residual;
- primary adjusted residual;
- hero-sensitive residual;
- dominant-hero-excluded residual;
- win-only and loss-only residual where supported; and
- raw observed/expected shares and support counts.

Do not label positive/negative as good/bad, aggressive/passive, skilled/unskilled, or well/poorly positioned.

## Dependency and stability

Matches are the independent units. Never bootstrap deaths or player rows independently.

For each profile:

- calculate nested HMAC-prefix estimates at N=10, 15, 20, 25, and 30;
- calculate chronological first-15 and last-15 estimates at N=30;
- run a whole-match cluster bootstrap for descriptive 95% intervals;
- run repeated whole-match subsamples at each N using a fixed seed derived from the private profile digest; and
- report ties/undefined estimates rather than coercing them to zero.

At N=25 or N=30, feasibility stability requires:

- cross-profile split-half Spearman at least 0.50; and
- median repeated-subsample sign agreement at least 0.75 among profiles with absolute full residual at least 0.05.

These are pilot continuation gates, not publication inference or production thresholds.

## Personalization and common-direction checks

Report residual median, IQR, P10/P90, positive/negative/tied counts, and the dominant-sign fraction before and after controls.

The candidate fails if:

- adjusted residual IQR is below 0.10;
- one residual sign covers at least 90% of supported profiles;
- fewer than 70% retain direction under the primary and hero controls; or
- median absolute residual attenuation after controls is at least 50%.

Do not tune strata, minimum reference deaths, quintiles, margins, or gates after seeing these results.

## Latency instrumentation

Separate and report:

- prior stored history latency (existing ledger only; no new history calls);
- match-detail request latency P50/P90/P95/max;
- response bytes and download time;
- JSON decode/normalization time;
- Death Context calculation time;
- 429/error rate;
- wall time for nested 20-GET and 30-GET prefixes at concurrency 1, 5, and 10 where measured without refetching; and
- total enrichment time.

Decision bands:

- ≤5s excellent synchronous;
- >5–15s acceptable synchronous;
- >15–30s borderline;
- >30–60s prefer progressive/background;
- >60s unacceptable as blocking Free generation.

A 30-GET total enrichment above 30 seconds routes the candidate to background even if analytically promising. Above 60 seconds blocks synchronous Free.

## Success criteria and stop rule

Continue research only if all pass:

1. core field completeness is at least 95%;
2. every response agrees with stored parsed state;
3. zero replay parse requests and no parse workflow;
4. no physical-call/cost/storage violation;
5. material residual heterogeneity: IQR at least 0.10 and dominant sign below 90%;
6. controls retain direction for at least 70% with median attenuation below 50%;
7. registered N=25/N=30 stability passes; and
8. the interpretation remains distinct from KDA, aggression, skill, generic outcome law, or causality.

If any fail, recommend dropping Death Context. Do not add calls, profiles, replacements, alternate branches, a suggestive tier, or weaker gates.

## Required outputs

Local diagnostics under `.local/diagnostics/free-dna-death-context-tier2-pilot/`:

- `preflight.json`
- `selection_manifest.json`
- `request_ledger.jsonl`
- `request_failure_ledger.json`
- `corpus_manifest.json`
- `field_completeness.csv`
- `match_context_rows.jsonl`
- `profile_estimates.jsonl`
- `baseline_summary.json`
- `control_sensitivity.csv`
- `stability_by_n.csv`
- `latency_summary.json`
- `cost_storage_summary.json`
- `pilot_verdict.json`
- `aggregate_summary.json`

Tracked aggregate evidence:

```text
docs/evidence/free-dna-death-context-tier2-pilot-2026-08-28.md
```

Never track raw identifiers, raw response bodies, private salts, or profile-level private values.

At the end, commit tracked research artifacts, keep the pilot branch, remove only the temporary worktree if safe, and do not merge main.
