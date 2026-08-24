# Free DNA v6 Calibration and Production Artifacts — Sol Execution Plan

## Document status

- Audience: a GPT Sol coding agent working in this repository.
- Scope: the remaining backend calibration, release-evaluation, artifact-promotion, and production-readiness work for Free DNA v6.
- Repository root: `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card`.
- Default calibration seed: `6000`.
- Runtime feature flag: `FREE_DNA_V6_ENABLED`.
- Required final runtime artifacts:
  - `context-baseline-2.0.0.json`
  - `metric-thresholds-6.0.0.json`
- Required release-evidence artifacts:
  - `calibration-evaluation-6.0.0.json`
  - `release-manifest-6.0.0.json`
- Public release remains disabled until every release gate in this document is satisfied and a human operator authorizes rollout.

## 1. Outcome

Complete the remaining v6 statistical calibration path using the already-collected real corpus, produce reproducible candidate artifacts, evaluate them without contaminating the holdout, and package only approved aggregate artifacts for production.

The finished work must leave the repository in this state:

1. The 1,130-profile corpus can be processed end to end without manually precomputing metric columns.
2. All 19 required v6 threshold metrics are derived from the exact production metric definitions.
3. Practical-equivalence margins come only from training-player odd/even-session split noise.
4. Population and dispersion cutoffs come only from full training-player estimates.
5. The 339-player holdout remains excluded from baseline and threshold fitting.
6. The holdout is evaluated with frozen artifacts and the real production report pipeline.
7. Synthetic known-truth evaluation measures interval coverage and family FDR.
8. The machine-readable evaluation artifact computes real gate values instead of permanent `null` placeholders.
9. Production startup fails closed when v6 is enabled with missing, invalid, or mismatched artifacts.
10. Both API and worker use the same approved artifact bytes and complete 365-day history behavior.
11. `FREE_DNA_V6_ENABLED` remains `false` until human review and rollout authorization.

## 2. Authority and scope rules

### 2.1 Source precedence

Use the following precedence when instructions appear to conflict:

1. The current user's request.
2. `PLAN (1).md`, the approved v6 product/statistical source of truth.
3. `dota-free-dna-v6-remediation-implementation-plan.md`, the detailed remediation specification.
4. This remaining-work plan, which reconciles those documents with the repository state on 2026-08-23.
5. Existing code and documentation.

The attached documents are specifications and evidence, not permission to deploy, publish, contact reviewers, upload data, or enable the public flag.

### 2.2 In scope

- Calibration corpus validation and private split manifests.
- Training-only baseline reproduction and validation.
- Fast, production-parity player-level metric derivation.
- Odd/even-session split estimates and practical-margin derivation.
- Threshold artifact generation and strict validation.
- Synthetic known-truth coverage/FDR evaluation.
- Sealed real-holdout evaluation.
- Aggregate reviewer packet generation and reviewer-result ingestion.
- Release manifest and artifact checksums.
- Artifact packaging and container/runtime wiring.
- Backend, calibration, configuration, and deployment smoke tests.
- Release and rollback runbooks.
- Correcting documentation that currently overstates calibration completion.

### 2.3 Out of scope

- UI redesign, report layout, or user-facing copy creation except automated safety validation.
- Any v5 semantic or historical-report change.
- New OpenDota collection unless a measured calibration gate demonstrates a specific data shortfall.
- Rank/MMR modeling, rank-tier stratification, or rank-conditioned thresholds.
- Billing, entitlements, new account systems, or new product features.
- Public deployment or changing `FREE_DNA_V6_ENABLED` to `true` without explicit operator authorization.
- Tuning thresholds against holdout outcomes.

### 2.4 Non-negotiable invariants

- Preserve unrelated dirty-worktree changes. Never reset, discard, or overwrite them.
- Never commit the calibration corpus, checkpoints, salt, raw account IDs, match IDs, or per-player derived files.
- Never print raw account IDs or unsalted identifiers in logs, tests, reports, or completion messages.
- Rank/MMR must not enter splits, baselines, thresholds, copy, recommendations, evaluation groupings, or release analytics.
- Free remains one summary-history read and zero detail/parse/status calls.
- Production bootstrap remains exactly 2,000 deterministic session-clustered iterations with 95% intervals.
- Do not weaken sample, session, coverage, confidence, FDR, or release gates to make the corpus pass.
- Missing/conflicting evidence remains mixed, unknown, unavailable, or suppressed; never replace it with a neutral guess.
- Do not replace v6 formulas with faster approximations. Optimize data preparation and reuse while preserving exact definitions.
- Do not mark synthetic fixtures or test artifacts as production calibration evidence.

## 3. Verified starting state

The Sol agent must re-verify these facts before editing, but should not repeat already-completed collection work unless a fact is false.

### 3.1 Private corpus

| Item | Current state |
| --- | --- |
| Candidate file | `.local/calibration/v6-public-match-candidates.json` |
| Candidate IDs | 2,364 deduplicated public account IDs from 590 seed public matches |
| Corpus file | `.local/calibration/v6-eligible-corpus.json` |
| Corpus schema | `v6-calibration-corpus-1.0.0` |
| Eligible profiles | 1,130 |
| Eligible matches | 422,161 |
| Processed profiles | 1,923 |
| Ineligible profiles | 793 |
| Collection errors | 0 |
| Annual eligible match range | 30–2,613 per profile |
| MMR/rank fields | Absent; source declares `rank_or_mmr_used=false` |
| Identity storage | Salted pseudonymous profile hashes |
| Patch coverage | 100% |
| Region coverage | Approximately 90% |
| Session coverage | 100% |
| Literal lane-context coverage | Approximately 7.6%; fallback hierarchy is expected to carry most adjusted metrics |
| File permissions | Owner read/write only (`0600`) |
| Git status | `.local/` is ignored |

No additional collection is a prerequisite at the start of this plan.

### 3.2 Current training baseline candidate

Path:

```text
.local/calibration/artifacts/context-baseline-2.0.0.json
```

Observed contents:

- 791 training profiles and 301,517 training matches.
- 1,748 audit cells.
- 389 currently resolvable cells at the 200-match/50-player rule.
- Six hierarchy levels represented.
- `mmr_used=false`.
- Strict baseline validation passes.
- `BaselineResolver` has an indexed lookup path.

Treat this as a candidate baseline until its split manifest, checksum, and reproducibility are captured. Do not call it frozen or production-approved yet.

### 3.3 Current implementation gap

`scripts/build_v6_calibration_artifacts.py` currently expects every match row to already contain all 19 player-level calibration metrics. The real corpus instead contains raw match/session/context fields plus these raw metrics:

- outcome;
- involvement per minute;
- finishing share;
- death exposure per ten minutes.

Therefore, threshold generation fails at `breadth_effective_count` and cannot legitimately emit production thresholds.

`build_evaluation()` is also a placeholder. It hard-codes:

```json
{
  "release_ready": false,
  "status": "external-review-required"
}
```

and leaves interval coverage, FDR, nonblank identity, and split-half agreement unmeasured.

### 3.4 Performance constraint already observed

Running the complete production pipeline on the largest 2,613-match profile exceeded 60 seconds after baseline lookup was optimized. The remaining bottleneck is the repeated clustered bootstrap/BCa jackknife work. Training threshold derivation must therefore use an exact calibration point-estimate path; it must not run the full 2,000-iteration report bootstrap for every full/A/B training estimate.

The sealed holdout evaluation must still exercise the exact production bootstrap. Make that offline job checkpointed, resumable, and parallelizable rather than changing its statistical method.

### 3.5 Production configuration issue

`.env.example` correctly permits an unset `FREE_HISTORY_LIMIT`, but `infra/compose.yaml` still sets `FREE_HISTORY_LIMIT: 500` for both API and worker. That cap conflicts with the v6 365-day population contract and must be removed or explicitly unset before production validation.

## 4. Completion model

There are three separate completion states. Do not merge them in status reporting.

### State A — implementation complete

All code, tests, builders, validators, evaluation runners, and runbooks exist and pass using fixtures/smoke data. No real gate is claimed.

### State B — automated calibration complete

The real corpus has produced a valid candidate baseline, valid threshold artifact, completed synthetic evaluation, and completed sealed-holdout evaluation. Every automated numerical gate passes.

### State C — production release ready

State B passes, the Dota reviewer precision gate and independent calibration review are recorded, approved artifacts are promoted, production/container smokes pass, and the operator authorizes a rollout. Only State C may set `release_ready=true` in the release evidence. The repository default feature flag still remains false.

## 5. Target calibration data flow

```text
private real corpus (1,130 profiles / 422,161 matches)
  → strict corpus validation and checksum
  → deterministic, player-exclusive, stratified split (seed 6000)
      → private training IDs (791)
      → sealed private holdout IDs (339)
  → training matches only
      → context baseline candidate
      → per-player preprocessing
      → 19 full-history point estimates
      → 19 odd-session point estimates
      → 19 even-session point estimates
      → P90(abs(A-B))/2 practical margins
      → Q33/Q67 population and dispersion cutoffs
      → threshold candidate
  → freeze candidate baseline + threshold bytes/checksums
  → synthetic known-truth evaluation
      → interval coverage
      → dependent-family FDR
  → sealed holdout opened once
      → exact production v6 reports
      → nonblank identity
      → split-half agreement
      → abstention and per-metric coverage
      → forbidden-copy and Free-cost checks
  → human reviewer evidence
  → aggregate evaluation + release manifest
  → operator-approved production promotion
  → shadow/staff QA → 5% → 25% → 100%
```

## 6. Artifact boundaries

### 6.1 Private, never committed

- Candidate account IDs and seed matches.
- Corpus salt.
- Raw collection checkpoints.
- Full eligible corpus.
- Split manifests containing pseudonymous profile IDs.
- Per-player full/A/B estimates.
- Per-player holdout reports and reviewer packets if they contain profile-level evidence.
- Job checkpoints and performance profiles.

Keep them under `.local/calibration/` with `0600` files and owner-only directories.

### 6.2 Safe aggregate release candidates

- Context baseline artifact: aggregate cells only.
- Threshold artifact: aggregate cutoffs/gates only.
- Evaluation artifact: aggregate gate measurements only.
- Release manifest: checksums, versions, counts, commands, source revision, and approvals; no player identifiers.

### 6.3 Runtime-loaded artifacts

The application loads only the baseline and threshold artifacts. Evaluation and release manifests are audit/release evidence and must not become runtime analytical inputs.

## 7. Required metric derivation contract

Create one production-parity calibration estimator that accepts a player's match sequence, the training baseline resolver, taxonomy, completion metadata, and a requested match/session subset. It returns point estimates and eligibility diagnostics without bootstrap intervals or public copy.

The estimator must calculate all required keys:

| Threshold key | Exact calibration estimate |
| --- | --- |
| `breadth_effective_count` | `exp(-Σ p_h ln p_h)` over match-weighted hero counts |
| `toolkit_effective_count` | Shannon effective count over match-weighted reviewed hero-job labels; one match contributes total weight 1 split across its labels; 80% taxonomy coverage required |
| `involvement_adjusted` | Mean per-match `(kills + assists) / minutes - resolved_context_baseline` |
| `finishing_adjusted` | Mean per-match `kills / (kills + assists) - resolved_context_baseline`; zero-event matches excluded |
| `death_exposure_adjusted` | Mean per-match `deaths / minutes * 10 - resolved_context_baseline`; native orientation retained |
| `transfer_outcome_delta` | Stretch win rate minus core win rate |
| `transfer_activity_delta` | Stretch minus core mean context-adjusted involvement |
| `transfer_survival_delta` | Stretch minus core mean of `-context_adjusted_death_exposure` |
| `consistency_outcome_dispersion` | Runtime robust MAD-based dispersion of session win rate |
| `consistency_activity_dispersion` | Runtime robust MAD-based dispersion of session adjusted involvement |
| `consistency_death_dispersion` | Runtime robust MAD-based dispersion of session adjusted death exposure |
| `post_loss_outcome_delta` | Post-loss next-match outcome minus matched control outcome |
| `post_loss_activity_delta` | Post-loss next-match adjusted involvement minus matched control |
| `post_loss_survival_delta` | Post-loss next-match survival-oriented death exposure minus matched control |
| `post_loss_familiarity_delta` | `P(core hero after loss) - P(core hero in control)` |
| `post_loss_tempo_delta` | The runtime E17 post-loss activity shift; not time between games |
| `session_drift_outcome_delta` | Mean within-session late-minus-early outcome across qualifying completed sessions |
| `session_drift_activity_delta` | Mean within-session late-minus-early adjusted involvement |
| `session_drift_survival_delta` | Mean within-session late-minus-early survival-oriented death exposure |

For every key, retain private diagnostics:

- finite estimate or unavailable reason;
- usable match/transition/session count;
- independent session count;
- metric coverage;
- taxonomy coverage where applicable;
- baseline fallback counts and unresolved count;
- core/stretch counts where applicable;
- comparable-control count where applicable;
- qualifying completed-session count where applicable.

Do not create a generic row mean for nonlinear metrics. Breadth, Toolkit, Transfer, Consistency, Post-Loss, and Session Drift must be recomputed from their underlying match/session structures.

## 8. Session and split rules

### 8.1 Session authority

- Use the existing 90-minute `infer_sessions` semantics.
- Preserve corrupt-row/session handling.
- Reconstruct or persist exact completed-session metadata needed by Session Drift.
- A session is completed under the same rule as `SessionResult.completed_sessions`: not right-censored and not corrupt.
- Session order is chronological by earliest match start time, then stable session ID. Never use lexical ordering alone (`session-10` must not precede `session-2`).

### 8.2 Full, A, and B estimates

For each training player:

1. Full estimate uses all eligible matches/sessions.
2. Sort independent sessions chronologically.
3. Odd-position sessions form split A.
4. Even-position sessions form split B.
5. Recompute each metric independently in each split.
6. Include `abs(A-B)` in that metric's noise sample only when both halves satisfy that metric's minimum data and coverage rules.

For nonlinear membership-dependent metrics, “independently” is literal. Full Transfer uses full-history core/stretch membership; A and B each derive their own core/stretch membership from their own matches. Do not leak full-history membership into the halves.

### 8.3 Core/stretch and comparison gates

Use the approved runtime rules unchanged:

- Core heroes are selected by descending match count with stable hero-ID tie break until cumulative share reaches at least 60%.
- Transfer requires at least two heroes, 10 usable core matches, 10 usable stretch matches, and eight independent sessions.
- Consistency requires 12 usable sessions.
- Post-Loss requires 30 same-session loss transitions, 12 qualifying sessions, and 50% comparable-context coverage.
- Session Drift requires 12 completed sessions with at least four eligible matches and 50% qualifying-session coverage.
- Baseline-adjusted scalar metrics require 80% baseline coverage.
- Transfer components require 70% comparable baseline coverage.
- Toolkit requires 80% taxonomy coverage.

## 9. Phase-by-phase execution plan

### Phase 0 — Protect state and capture provenance

Tasks:

1. Record `git status --short`, current branch, and HEAD SHA.
2. Do not clean or reset the worktree.
3. Validate `.local/` is ignored and all private calibration files are `0600`.
4. Compute SHA-256 for the corpus, current baseline candidate, taxonomy source, and relevant plan documents.
5. Record corpus schema, window, counts, source projection versions, and `rank_or_mmr_used=false`.
6. Recompute the seed-6000 split IDs without evaluating holdout outcomes.
7. Write a private split manifest containing sorted pseudonymous training/holdout IDs, their digests, split algorithm version, seed, and per-stratum counts.
8. Verify training/holdout disjointness and exact 791/339 counts before proceeding.

Definition of done:

- Private provenance and split manifests exist under `.local/calibration/manifests/`.
- No private artifact is staged by Git.
- Training and holdout sets are disjoint and exhaustive.
- The current baseline's corpus counts match the training partition.
- The holdout has not been used for metric fitting or report inspection.

### Phase 1 — Make the real corpus an explicit validated input

Tasks:

1. Add a strict internal corpus validator for `v6-calibration-corpus-1.0.0`.
2. Validate required top-level window/source/summary/profile/match fields.
3. Validate finite values, unique `(profile_id, match_id)` rows, minimum 30 matches per eligible profile, and profile summary consistency.
4. Reject rank/MMR keys recursively.
5. Reject raw numeric account IDs as profile IDs in the materialized corpus.
6. Validate chronological/session data and derive completed-session mapping with the same production censoring rules.
7. Emit aggregate validation diagnostics without identifiers.
8. Avoid parsing the 325 MB JSON repeatedly. Load once per process or create an owner-only per-profile cache/checkpoint.

Likely files:

- Create `services/api/app/player_analysis_v6/calibration_corpus.py`.
- Modify `scripts/collect_v6_calibration_histories.py` only if completion metadata must be persisted for future corpora.
- Add `tests/calibration/test_v6_calibration_corpus.py`.

Definition of done:

- The real corpus validates without modification or a documented, deterministic private migration produces an equivalent validated corpus.
- Invalid identifiers, duplicate matches, non-finite data, missing session authority, and rank/MMR fields fail closed.
- Validation output contains only aggregates.
- No additional OpenDota fetch is required.

### Phase 2 — Implement a fast calibration point-estimate layer

Tasks:

1. Create a typed per-profile preprocessing object that groups matches/sessions once.
2. Resolve per-match baselines once and reuse adjusted values across all metrics.
3. Reuse the production formula helpers from `metrics.py`, `context_adjustment.py`, `post_loss.py`, and `session_drift.py`.
4. Extract small pure point-estimate helpers from runtime modules where needed so calibration and runtime call the same functions.
5. Do not import public copy, identity synthesis, story assembly, recommendation generation, or report serialization into the training estimator.
6. Do not call clustered bootstrap during training full/A/B derivation.
7. Add a private JSONL checkpoint format for one completed player at a time so interruption can resume safely.
8. Make output order deterministic regardless of worker count.
9. Bound multiprocessing by an explicit `--workers`; default conservatively and support `--workers 1`.

Likely files:

- Create `services/api/app/player_analysis_v6/calibration_derivation.py`.
- Refactor only the narrow pure-statistic seams in:
  - `services/api/app/player_analysis_v6/elements.py`
  - `services/api/app/player_analysis_v6/post_loss.py`
  - `services/api/app/player_analysis_v6/session_drift.py`
  - `services/api/app/player_analysis_v6/metrics.py`
- Keep `scripts/build_v6_calibration_artifacts.py` as CLI/orchestration rather than a second statistical implementation.
- Add `tests/calibration/test_v6_calibration_derivation.py`.

Required parity tests:

- On deterministic fixtures, every calibration point estimate equals the corresponding runtime point estimate within tight floating-point tolerance.
- Sample/session/coverage counts and unavailable reasons match.
- Baseline fallback audit counts match.
- Transfer core/stretch membership and component signs match.
- Consistency uses the same robust dispersion.
- Post-Loss control hierarchy and transition exclusions match.
- Session Drift completion and early/late buckets match.
- A `session-1`, `session-2`, `session-10` fixture proves chronological rather than lexical odd/even assignment.
- A largest-profile benchmark completes point-estimate derivation without invoking bootstrap and records elapsed time/peak memory.

Definition of done:

- All 19 metrics can be produced directly from the real corpus.
- No threshold key relies on a pre-derived match-row column.
- Training derivation is resumable and deterministic.
- Formula parity tests pass.
- No production semantic behavior changed except any explicitly tested helper extraction.

### Phase 3 — Freeze the training baseline candidate

Tasks:

1. Rebuild the baseline from training matches only using the frozen split.
2. Preserve the hierarchy:

```text
patch+hero+lane
→ patch+hero_function+lane
→ patch+hero
→ patch+lane
→ patch
→ overall
```

3. Keep audit cells below 200 matches/50 players, but prove the resolver never selects them.
4. Validate exact schema, finite metrics, unique logical cells, supported dimensions, and `mmr_used=false`.
5. Compare aggregate counts and cell values against the existing candidate. Investigate any difference before replacing it.
6. Support a fixed `--generated-at` or equivalent reproducible timestamp input so identical inputs can produce byte-identical artifacts.

Definition of done:

- Baseline is derived exclusively from 791 training profiles.
- Strict loader validation passes.
- Rebuilding with the same corpus, split, seed, and timestamp produces the same SHA-256.
- Resolver tests prove minimum-cell gates and fallback ordering.
- Baseline is still labeled candidate, not production, until release evaluation passes.

### Phase 4 — Derive all threshold values from training only

Tasks:

1. Run full/A/B point estimates for all 791 training profiles.
2. For each metric, build a noise sample of `abs(A-B)` for eligible split pairs.
3. Set practical margin to `P90(noise)/2` with only a tiny positive epsilon floor.
4. For Breadth and Toolkit, set low/high to training-player Q33/Q67. If their separation is less than `2 * margin`, center the two cutoffs on the training median at `median ± margin`.
5. For each Consistency component, set stable/variable to training-player Q33/Q67; use the approved median±margin fallback only when cutoffs collapse.
6. For centered metrics, set low/high to `-margin/+margin`.
7. Preserve approved minimum sample/session/coverage values and stability gates 0.75/0.90.
8. Emit per-metric private derivation diagnostics: full-estimate count, split-pair count, missing reasons, quantiles, margin, and fallback use.
9. Fail rather than emit a threshold when a metric has no defensible training distribution/noise sample.
10. Validate the completed artifact with `load_threshold_artifact()`.

Do not use any holdout estimate, holdout gate result, or holdout report to choose these values.

Definition of done:

- `metric-thresholds-6.0.0.json` contains exactly all 19 required keys.
- Every practical margin is finite and positive and traces to a non-empty training split-noise sample.
- Every cutoff traces to the training distribution.
- `train_profile_count=791`, `holdout_profile_count=339`, split method is `player-level-70-30`, noise method is `session-odd-even-split`, and `mmr_used=false`.
- Strict threshold validation passes.
- Same inputs produce byte-identical threshold bytes.
- The artifact remains a candidate until evaluation and review pass.

### Phase 5 — Replace placeholder evaluation with measured evaluation

Create a strict evaluation schema and two evaluation engines: synthetic known-truth and real sealed holdout.

#### 5A. Synthetic known-truth evaluation

Required scenarios from the approved remediation plan:

- null/no-effect profiles;
- positive and negative centered effects;
- mixed Transfer;
- stable and variable Consistency;
- no and real Post-Loss effects;
- no Session Drift, late rise, and late fade;
- patch boundary;
- missing baseline cells;
- sparse taxonomy;
- 30–59 limited histories.

Tasks:

1. Generate deterministic dependent sessions, not independent rows.
2. Run the exact production 2,000-iteration interval and family-statistics path for the full release job.
3. Measure whether nominal 95% intervals contain the known parameter.
4. Measure family false discovery rate under dependent null fixtures after BH across exactly five family slots.
5. Record scenario counts, seeds, metric-level results, aggregate coverage, and FDR.
6. Keep a small deterministic smoke configuration in normal CI and the statistically sized run as an explicit offline calibration job.

Synthetic gates:

- Aggregate 95% interval empirical coverage is between 93% and 97%, inclusive.
- Empirical finding-family FDR is at most 5%.
- Every missing family slot participates as `p=1.0`.
- No test is made to pass by reducing production bootstrap iterations.

#### 5B. Real sealed-holdout evaluation

Precondition: candidate baseline and threshold bytes/checksums are frozen. Opening holdout results before this point is prohibited.

Tasks:

1. Run exact production v6 analysis for all 339 holdout players with the frozen training baseline/thresholds and 2,000 bootstrap iterations.
2. Checkpoint one profile at a time and support resume/retry.
3. Use deterministic per-profile seeds derived from the global seed and pseudonymous profile hash; never use process order.
4. Generate full-history reports for coverage/abstention/nonblank checks.
5. Generate independent odd/even-session analyses for split-half agreement using the same session ordering rules.
6. Scan all public report strings for forbidden Tier-A inference.
7. Assert every Free cost ledger shows one history read and zero detail/parse/status requests.
8. Aggregate only; keep individual reports private.

Real-holdout metric definitions:

- **Eligible holdout denominator:** all holdout profiles with at least 30 eligible matches.
- **Nonblank identity numerator:** reports with at least three public Elements in an available/limited descriptive state and a non-empty coherent identity headline with supporting evidence references.
- **Split-half agreement denominator:** high-confidence full-history identity zones for which both A and B have enough data to emit the comparable zone/direction.
- **Split-half agreement numerator:** denominator cases where A and B emit the same zone/direction.
- **Abstention:** report and family counts for unavailable, suppressed, qualified, and published states, plus reasons.
- **Per-metric coverage:** availability, sample/session gates, raw-data coverage, baseline resolution, taxonomy coverage, and fallback-level distribution.

Real-holdout gates:

- Nonblank identity rate is at least 80%.
- Split-half agreement is at least 80%.
- Forbidden causal/positioning/death-quality/rank/MMR public-copy violations equal zero.
- Free cost violations equal zero.

#### 5C. Holdout discipline after evaluation

- Fixing a demonstrated implementation bug is allowed, but document it and rerun the exact same test.
- Changing formulas, gates, thresholds, cutoff selection, or copy qualification because of holdout results is statistical tuning and is not allowed on the same holdout.
- If material tuning is required, return to training-only cross-validation and obtain a new untouched validation set before claiming release readiness.
- Never lower coverage or confidence gates to reach 80% nonblank identity.

Definition of done:

- `calibration-evaluation-6.0.0.json` contains observed values for every automated gate.
- It distinguishes synthetic, real-holdout, copy, cost, and external-review evidence.
- `status` is one of `automated-gates-failed`, `external-review-required`, or `release-ready` based on evidence, not hard-coded.
- `release_ready` cannot be true while any required field is null, failed, or externally unapproved.
- The evaluation artifact contains no player or match identifiers.

### Phase 6 — Human review evidence

The Sol agent prepares the process; a human performs the judgment.

Status on 2026-08-23: the Dota-domain judgment is complete at 50/50 supported
and believable (100% precision). See
[`docs/qa/free-dna-v6-dota-review-record.md`](docs/qa/free-dna-v6-dota-review-record.md).
Independent statistical review and data-basis approval remain open and are not
implied by the Dota sign-off.

Tasks for the agent:

1. Generate a private, randomized review packet from Dota-believability fixtures and a bounded sample of holdout outputs.
2. Include claim, literal evidence, interval, sample/session/coverage, limitations, and permitted interpretation.
3. Remove profile IDs, match IDs, and any unnecessary identifying data.
4. Provide a simple review schema with independent `supported` and `believable` judgments plus optional notes.
5. Add an ingestion command that validates reviewer results and computes the aggregate precision gate.
6. Do not fabricate labels or self-approve the packet.

Tasks for the user/operator:

1. Select a Dota-knowledgeable reviewer for the supported-and-believable judgment.
2. Select an independent statistical reviewer, or explicitly nominate the same qualified reviewer for both roles.
3. Return completed review evidence to the agent.
4. Approve the data-basis statement that the source profiles are public/consented under the project's policy. This plan is not legal advice.

Human gates:

- Dota reviewer supported-and-believable precision is at least 90%.
- Statistical reviewer approves the split, practical-margin derivation, synthetic coverage/FDR interpretation, and holdout protocol.

Definition of done:

- Reviewer evidence validates and is referenced by checksum in the release manifest.
- The evaluation artifact records aggregate reviewer counts/precision and sign-off status.
- No private review packet is committed.

### Phase 7 — Build the release manifest and promote artifacts

Create `release-manifest-6.0.0.json` with no identifying data. Include:

- schema/version;
- source repository commit and dirty-worktree disclosure;
- builder/calibration model versions;
- corpus schema/window and SHA-256;
- aggregate corpus/train/holdout counts;
- split algorithm version, seed, and digests of sorted train/holdout pseudonyms;
- taxonomy, sessionization, baseline, threshold, report, and statistics versions;
- SHA-256 and byte size for baseline, threshold, and evaluation artifacts;
- exact generation/evaluation commands;
- automated gate results;
- reviewer evidence checksum and aggregate result;
- generation/review timestamps;
- `mmr_used=false`;
- approval state and approver reference;
- `release_ready` derived from all gates.

Recommended candidate directory:

```text
.local/calibration/releases/6.0.0/
```

Recommended production directory after explicit approval:

```text
services/api/artifacts/free_dna_v6/6.0.0/
```

Only copy these aggregate files into the production directory:

```text
context-baseline-2.0.0.json
metric-thresholds-6.0.0.json
calibration-evaluation-6.0.0.json
release-manifest-6.0.0.json
```

Before promotion, recursively scan artifact keys/values for raw IDs, profile hashes, match IDs, rank/MMR fields, non-finite values, and filesystem paths containing private usernames.

Definition of done:

- Candidate release directory contains four mutually consistent, checksum-linked aggregate artifacts.
- Promotion refuses to run unless every automated and human gate passes.
- Production artifact directory contains no corpus or per-player data.
- Fresh strict loads succeed from the promoted paths.
- Git diff shows only intended aggregate artifacts and code/docs; private files remain ignored.

### Phase 8 — Production wiring and fail-closed verification

Tasks:

1. Configure both API and worker with identical paths:

```text
FREE_DNA_V6_BASELINE_ARTIFACT=/app/services/api/artifacts/free_dna_v6/6.0.0/context-baseline-2.0.0.json
FREE_DNA_V6_THRESHOLD_ARTIFACT=/app/services/api/artifacts/free_dna_v6/6.0.0/metric-thresholds-6.0.0.json
FREE_DNA_V6_MODEL_VERSION=free-dna-model-6.0.0
FREE_DNA_V6_ENABLED=false
```

2. Remove `FREE_HISTORY_LIMIT: 500` from both API and worker in `infra/compose.yaml`, or explicitly set it to empty/unlimited using configuration semantics covered by a test.
3. Verify the API image copies the promoted artifact directory.
4. Verify worker and API load identical artifact SHA-256 values.
5. Add startup tests:
   - flag false + no artifacts: start succeeds and v5 behavior is unchanged;
   - flag true + missing baseline: fails clearly;
   - flag true + missing thresholds: fails clearly;
   - flag true + invalid/mismatched version: fails clearly;
   - flag true + valid production artifacts: service constructs successfully.
6. Add a container smoke that starts API and worker with valid artifacts while public routing remains disabled.
7. Add an annual-history regression proving the live source is not truncated at 500 before the 365-day window is filtered.

Definition of done:

- No production configuration caps v6 history at 500.
- API and worker use the same approved artifact release.
- Enabling v6 with untrusted artifacts is impossible.
- Disabling v6 requires no artifacts and preserves v5.
- Repository/config default remains `FREE_DNA_V6_ENABLED=false`.

### Phase 9 — Shadow, canary, monitoring, and rollback preparation

The Sol agent prepares code/runbooks and may run local/internal simulations. It must not deploy or enable public traffic without authorization.

Tasks:

1. Document internal shadow generation using frozen production candidate artifacts without returning v6 to users.
2. Verify staff/fixture QA across the approved believability scenarios.
3. Define 5%, 25%, and 100% stages using deployment-layer traffic splitting. If the deployment platform cannot split traffic, stop and ask the operator rather than inventing identity-based application cohorting.
4. Define promotion hold times and rollback triggers before the 5% stage.
5. Monitor only aggregate, non-identity-shaped measures:
   - report success/error/latency;
   - nonblank identity rate;
   - element/family abstention;
   - interval widths;
   - baseline fallback/unresolved rates;
   - Free OpenDota request count;
   - Deep detail/parse/cost ceilings;
   - story completion, recommendation selection, follow-up completion, and share eligibility.
6. Never emit player IDs, identity labels, element zones, or finding directions as analytics dimensions.
7. Rollback is `FREE_DNA_V6_ENABLED=false`; retain readable v6 snapshots and the exact artifact release used.

Definition of done:

- A reviewed rollout/rollback runbook exists.
- Monitoring queries/dashboards or exact metric definitions exist before canary.
- A rollback smoke proves v5 generation resumes and existing v6 snapshots remain readable.
- Public rollout has not occurred without an explicit operator decision.

### Phase 10 — Documentation correction and handoff

Update these documents after measurements exist:

- `dota-player-analysis-revision-implementation-plan.md`
- `docs/architecture/free-dna-v6-statistics.md`
- `docs/qa/free-dna-v6-release-gates.md`
- `docs/system-behavior-baseline.md`
- `.env.example`
- production/deployment runbook or README

Corrections must distinguish:

- fixture schema/wiring tests;
- real training calibration;
- synthetic known-truth evaluation;
- sealed real-holdout evaluation;
- human reviewer evidence;
- production promotion;
- public rollout status.

Do not retain language claiming the real corpus or external review is the only remaining prerequisite if metric derivation, evaluation, packaging, or deployment wiring is still incomplete.

Definition of done:

- Documentation matches actual artifact checksums and observed gates.
- No document calls candidate artifacts production or frozen before approval.
- The flag's actual default and deployment state are stated explicitly.

## 10. Required CLI behavior

The exact interface may be implemented as subcommands or compatible flags, but the operator must be able to perform these stages independently and resume them:

```bash
uv run python scripts/build_v6_calibration_artifacts.py validate \
  --input .local/calibration/v6-eligible-corpus.json

uv run python scripts/build_v6_calibration_artifacts.py baseline \
  --input .local/calibration/v6-eligible-corpus.json \
  --split-manifest .local/calibration/manifests/split-6000.json \
  --baseline-output .local/calibration/releases/6.0.0/context-baseline-2.0.0.json \
  --seed 6000

uv run python scripts/build_v6_calibration_artifacts.py thresholds \
  --input .local/calibration/v6-eligible-corpus.json \
  --split-manifest .local/calibration/manifests/split-6000.json \
  --baseline-input .local/calibration/releases/6.0.0/context-baseline-2.0.0.json \
  --threshold-output .local/calibration/releases/6.0.0/metric-thresholds-6.0.0.json \
  --checkpoint-dir .local/calibration/checkpoints/thresholds-6.0.0 \
  --seed 6000 \
  --workers 1

uv run python scripts/evaluate_v6_calibration.py synthetic \
  --baseline .local/calibration/releases/6.0.0/context-baseline-2.0.0.json \
  --thresholds .local/calibration/releases/6.0.0/metric-thresholds-6.0.0.json \
  --output .local/calibration/evaluation/synthetic-6.0.0.json \
  --seed 6000

uv run python scripts/evaluate_v6_calibration.py holdout \
  --input .local/calibration/v6-eligible-corpus.json \
  --split-manifest .local/calibration/manifests/split-6000.json \
  --baseline .local/calibration/releases/6.0.0/context-baseline-2.0.0.json \
  --thresholds .local/calibration/releases/6.0.0/metric-thresholds-6.0.0.json \
  --checkpoint-dir .local/calibration/checkpoints/holdout-6.0.0 \
  --output .local/calibration/evaluation/holdout-6.0.0.json \
  --seed 6000 \
  --workers 1

uv run python scripts/evaluate_v6_calibration.py aggregate \
  --synthetic .local/calibration/evaluation/synthetic-6.0.0.json \
  --holdout .local/calibration/evaluation/holdout-6.0.0.json \
  --review-evidence .local/calibration/review/reviewer-results-6.0.0.json \
  --output .local/calibration/releases/6.0.0/calibration-evaluation-6.0.0.json

uv run python scripts/promote_v6_calibration_release.py \
  --release-dir .local/calibration/releases/6.0.0 \
  --destination services/api/artifacts/free_dna_v6/6.0.0
```

Maintain backward compatibility with the existing `--baseline-only`/explicit-output interface or provide a documented migration with tests.

Every long-running command must:

- print aggregate progress at a bounded cadence;
- avoid identifiers in logs;
- write atomic checkpoints;
- resume without duplicating completed profiles;
- reject checkpoint/input checksum mismatch;
- return nonzero on validation or gate failure;
- write final outputs atomically;
- never modify the source corpus.

## 11. Evaluation artifact minimum schema

The strict aggregate evaluation artifact must contain at least:

```json
{
  "version": "calibration-evaluation-6.0.0",
  "generated_at": "...",
  "release_ready": false,
  "status": "external-review-required",
  "artifact_checksums": {},
  "corpus": {},
  "synthetic": {
    "interval_empirical_coverage": {},
    "family_fdr": {}
  },
  "holdout": {
    "nonblank_identity": {},
    "split_half_agreement": {},
    "abstention": {},
    "per_metric_coverage": {},
    "baseline_fallback": {},
    "free_cost": {}
  },
  "copy_safety": {},
  "external_review": {},
  "gates": {}
}
```

Requirements:

- Every gate stores required value, observed value, denominator/sample size, pass/fail, and evidence source.
- Missing evidence is represented explicitly and fails closed.
- `release_ready` is computed as `all(required_gate.passed)` and cannot be manually set independently.
- The artifact validator rejects identifiers, rank/MMR dimensions, non-finite values, unsupported versions, and inconsistent checksums.

## 12. Test strategy

### 12.1 Unit and calibration tests

Add or extend tests for:

- corpus schema/security validation;
- deterministic split and immutable split manifest;
- training/holdout exclusivity;
- chronological odd/even session assignment;
- all 19 full/A/B metric estimates;
- nonlinear metric recomputation;
- baseline fallback and coverage;
- practical-margin P90/2 calculation;
- Q33/Q67 and median±margin fallback;
- strict threshold schema;
- deterministic bytes/checksums;
- resumable checkpoints and checksum mismatch rejection;
- synthetic interval coverage harness;
- dependent-family FDR harness;
- holdout aggregation definitions;
- release-ready truth table;
- private-data exclusion from aggregate artifacts;
- promotion refusal on any failed/missing gate;
- fail-closed runtime loading;
- unlimited 365-day production history behavior;
- API/worker artifact parity.

### 12.2 Required regression suites

Run from repository root:

```bash
uv run ruff check .
uv run mypy services/api/app
uv run pytest -q --ignore=tests/calibration
uv run pytest -q tests/calibration
```

Run targeted suites during development:

```bash
uv run pytest -q \
  tests/unit/test_collect_v6_calibration_candidates.py \
  tests/unit/test_collect_v6_calibration_histories.py \
  tests/unit/test_opendota_client.py \
  tests/unit/test_player_analysis_v6_core.py \
  tests/calibration
```

Run web compatibility even though UI work is out of scope:

```bash
pnpm --dir apps/web install --frozen-lockfile
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run build
pnpm --dir apps/web exec playwright test tests/e2e/report-v6.spec.ts --project=chromium
```

Run container/config smokes after artifact promotion:

```bash
docker compose -f infra/compose.yaml config
docker compose -f infra/compose.yaml build api worker
```

Do not paste secrets or private file contents into CI logs. The full real-corpus job runs locally or in an approved private runner; normal CI runs only deterministic synthetic smoke data and schema fixtures.

## 13. Failure handling

| Failure | Required response |
| --- | --- |
| Corpus validation fails | Stop. Repair collector/adapter or deterministically migrate a private copy; do not skip rows silently. |
| Split differs from 791/339 | Stop before holdout evaluation. Explain whether code, corpus, or seed changed. |
| Baseline differs from existing candidate | Compare split/checksums/cell formulas; do not overwrite until explained. |
| A metric lacks usable training/noise data | Do not invent a threshold. Report the exact eligibility reason and decide whether targeted new data is required. |
| Training derivation is slow | Profile preprocessing/reuse; do not reduce metric fidelity or use production bootstrap in this stage. |
| Holdout job is slow | Resume/checkpoint/parallelize; do not reduce 2,000 iterations. |
| Synthetic coverage/FDR fails | Diagnose formula/bootstrap/FDR implementation using training/synthetic data; do not tune against holdout. |
| Holdout nonblank/agreement fails | Report failure. Do not weaken gates; return to training-only analysis and obtain a new holdout if statistical tuning is needed. |
| Reviewer precision fails | Correct demonstrably unsupported logic/copy under a documented protocol; re-review with uncontaminated examples. Do not relabel failures. |
| Artifact contains identifiers or MMR/rank | Reject and regenerate; never promote. |
| API/worker artifact SHA differs | Fail deployment smoke. |
| Canary regression | Disable v6, preserve reports/artifacts/logs, and diagnose offline. |

## 14. Agent stopping points and user decisions

The Sol agent can autonomously complete implementation, real training derivation, automated evaluation, candidate artifact generation, tests, and local/container smokes.

It must stop and ask the user before:

- collecting additional OpenDota profiles after a measured shortfall;
- sending a review packet to any external person;
- selecting or provisioning a production artifact store other than the recommended repository path;
- changing deployment traffic or production environment variables;
- enabling v6 for any public traffic;
- promoting after a failed gate;
- replacing the sealed holdout following statistical tuning.

The user/operator must ultimately provide:

- reviewer identity/qualification and completed review evidence;
- approval of the public/consented data-basis statement;
- production artifact destination approval;
- deployment platform/traffic-splitting details;
- explicit 5%, 25%, and 100% promotion decisions.

## 15. Definition of Done

### 15.1 Code and pipeline

- [ ] Real corpus validates strictly and privately.
- [ ] Split is deterministic, player-exclusive, stratified, frozen, and 791/339.
- [ ] Holdout IDs never enter baseline or threshold fitting.
- [ ] Baseline is training-only, reproducible, strict-valid, and non-MMR.
- [ ] All 19 threshold metrics derive from raw corpus fields using production-parity formulas.
- [ ] Full/A/B estimates are metric-specific and nonlinear metrics are recomputed.
- [ ] Session ordering is chronological.
- [ ] Practical margins equal `P90(abs(A-B))/2` on eligible training split pairs.
- [ ] Breadth/Toolkit cutoffs use training Q33/Q67 with approved fallback.
- [ ] Consistency cutoffs use training Q33/Q67 with approved fallback.
- [ ] Minimum sample/session/coverage and 0.75/0.90 stability gates are not weakened.
- [ ] Long jobs are deterministic, checkpointed, resumable, and identifier-safe.
- [ ] Placeholder evaluation fields are replaced with measured values.

### 15.2 Automated calibration gates

- [ ] At least 1,000 public/consented profiles are represented.
- [ ] MMR/rank is absent from corpus dimensions, split, models, artifacts, and evaluation.
- [ ] Synthetic 95% interval coverage is 93–97% inclusive.
- [ ] Synthetic empirical family FDR is at most 5%.
- [ ] Real-holdout nonblank identity is at least 80%.
- [ ] Real-holdout high-confidence split-half agreement is at least 80%.
- [ ] Forbidden Tier-A public-copy violations equal zero.
- [ ] Free cost violations equal zero.
- [ ] Per-metric coverage and abstention are measured and reported.

### 15.3 Human gates

- [x] Dota reviewer supported-and-believable precision is at least 90% (50/50,
      100%; recorded 2026-08-23).
- [ ] Independent statistical review is approved.
- [ ] Public/consented data-basis statement is approved by the operator.

### 15.4 Production artifacts and wiring

- [ ] Baseline, thresholds, evaluation, and release manifest are checksum-linked and contain no identifiers.
- [ ] Promotion fails closed on any missing/failed gate.
- [ ] Only approved aggregate artifacts are placed in the production directory.
- [ ] API and worker load identical artifact SHA-256 values.
- [ ] `FREE_HISTORY_LIMIT: 500` is removed from production API and worker configuration.
- [ ] Disabled v6 starts without artifacts and leaves v5 unchanged.
- [ ] Enabled v6 refuses missing/invalid/mismatched artifacts.
- [ ] Valid-artifact container smoke passes.
- [ ] Repository and production default remains `FREE_DNA_V6_ENABLED=false` until rollout approval.

### 15.5 Verification

- [ ] Ruff passes.
- [ ] Mypy passes.
- [ ] Normal backend tests pass.
- [ ] Calibration smoke/full suites pass as applicable.
- [ ] v5 regressions pass.
- [ ] Web typecheck/build/v6 E2E pass.
- [ ] Container configuration/build smoke passes.
- [ ] No required test is skipped to claim completion.
- [ ] Final diff contains no private calibration data or accidental unrelated rewrites.

### 15.6 Release and rollback

- [ ] Shadow/staff QA evidence is recorded.
- [ ] Monitoring and rollback triggers are documented.
- [ ] Deployment platform supports the planned staged traffic split or the operator has approved an alternative.
- [ ] 5%, 25%, and 100% promotions require separate operator decisions.
- [ ] Rollback disables new v6 generation while preserving historical v5 and readable v6 snapshots.

## 16. Required Sol completion report

When the Sol agent finishes a work session, report:

1. Branch name, starting HEAD, ending HEAD, and whether the worktree was already dirty.
2. Files created/modified, grouped by calibration, evaluation, runtime wiring, tests, and docs.
3. Corpus/train/holdout counts and checksums without identifiers.
4. Baseline/threshold/evaluation/release-manifest paths, versions, SHA-256 values, and candidate/approved status.
5. A 19-row metric table with full-estimate count, A/B noise-pair count, margin, cutoffs, and missing-data reasons.
6. Synthetic interval coverage and FDR with denominators.
7. Holdout nonblank identity, split-half agreement, abstention, per-metric coverage, forbidden-copy count, and Free-cost violations.
8. Reviewer status and precision, clearly marked external if pending.
9. Exact test/lint/type/build/container command summaries.
10. Final `FREE_DNA_V6_ENABLED` default and actual deployment state.
11. Any remaining blocker that genuinely requires external data, review, infrastructure, or operator authority.

Do not describe unfinished code, missing tests, placeholder evaluation, or ungenerated artifacts as a future improvement. Those are incomplete work. If any such item remains, state that the implementation is incomplete and name the exact next executable step.
