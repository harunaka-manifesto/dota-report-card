# Free DNA V6.1 — GPT Sol Implementation Plan

## Document status

- **Audience:** a GPT Sol coding agent working in this repository.
- **Repository root:** `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card`.
- **Purpose:** implement the V6.1 patch described in [`research/free-dna-v6.1-cheap-history-ceiling.md`](research/free-dna-v6.1-cheap-history-ceiling.md), verify it, update all active documentation, and leave a separate implementation-grounded brief for a later Figma documentation agent.
- **Plan type:** execution specification, not proof that the work is already complete.
- **Public product boundary:** one saved 365-day OpenDota summary-history payload; no match-detail, replay-parse, status, rank, or MMR dependency.
- **Compatibility boundary:** existing V5 and V6.0 reports remain readable and immutable. V6.1 is a new versioned generation path, not an in-place reinterpretation of stored reports.
- **Release boundary:** code may merge behind flags before the statistical and human release gates pass. Public enablement is a separate operator decision.

## 1. Outcome in plain language

Keep the report simple on the outside and make it much smarter underneath.

The public report must still have exactly:

- seven Element scores: Breadth, Toolkit, Involvement, Finishing, Death Exposure, Transfer, and Consistency;
- five finding-family keys: Pool Shape, Transfer, Post-Loss Response, Combat Expression, and Session Drift;
- zero to three published Findings, with at most one from any family.

V6.1 does **not** add more public meters. It adds better hidden evidence: portfolio shape, continuous distance from a player's core, win/loss/streak responses, nonlinear session behavior, conditional variance, chronology, and carefully gated semantic outcomes. These hidden signals are supporting evidence and relationships; they are not new Elements because they are conditional, longitudinal, redundant with an existing Element, or too uncertain to deserve a permanent identity score.

The target data flow is:

```text
one saved summary-history payload
  → validate, deduplicate, audit coverage, preserve chronology
  → create 90-minute sessions and censored boundaries
  → compute atomic features and covered context residuals
  → build a private supporting-signal graph
  → compute exactly seven public Elements
  → test exactly five family-level global hypotheses
  → test frozen semantic outcomes only inside qualified families
  → publish zero to three Findings
  → compose PRIMARY + optional TWIST + ANCHOR identity
  → render a nine-beat story and supported interactions
  → pass the exact qualifying cohorts and unanswered alternatives to Deep
```

## 2. Authority and source precedence

When sources conflict, use this order:

1. The current user's explicit instructions.
2. This execution plan.
3. [`research/free-dna-v6.1-cheap-history-ceiling.md`](research/free-dna-v6.1-cheap-history-ceiling.md), especially Parts 12–15.
4. The implemented V6.0 contracts and release records.
5. Other active documentation.
6. Historical plans and archived documents.

The research document is the discovery record and analytical rationale. This plan converts that research into staged, testable work. Do not silently broaden the patch because a candidate appears in the 65-Finding library.

If implementation evidence reveals that a direction in this plan is unsafe or impossible, Sol must:

1. capture the concrete evidence;
2. preserve the public 7-Element/5-family and one-call invariants;
3. record the proposed deviation in an ADR or implementation note;
4. update this plan's status or the active successor plan;
5. stop before a public-contract or release-scope change that needs product approval.

## 3. Sol execution protocol

Before editing:

1. Read this file in full.
2. Read Parts 1, 4, 6, and 12–15 of the V6.1 research document.
3. Read the active V6 architecture, statistics, evidence, QA, and release documents named in Phase 9.
4. Inspect `git status --short` and preserve unrelated user changes. At plan-writing time, the tree already contained unrelated calibration-review work; do not overwrite or discard it.
5. Capture a baseline test result for the directly affected V6 unit and contract suites.
6. Locate every V6 version literal before changing versions. No compatibility branch may depend on a half-updated string.
7. Treat the saved specimen artifacts as read-only research evidence. Do not make another OpenDota request just to reproduce the research.

While implementing:

- Work in the phase order below unless a documented dependency requires a small reorder.
- Make each phase independently reviewable. Prefer narrow commits or clearly separable diffs.
- Add or update tests in the same change as behavior.
- Never tune against the sealed holdout or relax gates just to obtain a passing report.
- Never log raw account IDs, match IDs, bearer tokens, or private calibration rows.
- Never infer aggression, intent, personality, actual lane role, positioning, death quality, player skill, patch causality, geography, latency, or local time from this payload.
- Do not enable the public V6.1 flag or deploy. Operator authorization is outside this plan.
- Update generated files through their generator, not by hand.
- Keep a concise implementation record of decisions, commands, artifacts, remaining gates, and deliberate abstentions.

At the end:

- Report completion separately as **implementation complete**, **automated calibration complete**, and **public release ready**. These are not interchangeable.
- Create the Figma documentation-agent brief required by Phase 10 after the code and repository documentation are truthful.

## 4. Completion states

### State A — implementation complete

All planned runtime, model, API, web, calibration, test, generator, documentation, migration, and rollback work exists behind the correct flags. Fixture and synthetic verification passes. No real calibration or human-review gate is implied.

### State B — automated V6.1 calibration complete

Training-only V6.1 artifacts are frozen, synthetic known-truth tests pass, the sealed holdout is evaluated once with frozen bytes, automated gates pass, and the aggregate evidence/manifest is reproducible. This state does not include Dota reviewer approval or operator rollout authorization.

### State C — public release ready

State B passes; independent statistical and Dota-language reviews are recorded; copy, accessibility, cost, compatibility, and rollback gates pass; approved artifacts are promoted; and an operator authorizes rollout. The repository default flag remains off unless that operator separately changes it.

### State D — Figma documentation handoff ready

The Markdown brief in Phase 10 exists, references the implemented—not merely planned—contract, names the exact Figma documentation work, lists unresolved inputs, and is usable by a separate agent without rediscovering V6.1 from scratch. This state does not mean Figma itself has already been updated.

## 5. Non-negotiable invariants

### 5.1 Product invariants

- Exactly seven public Elements. Supporting signals never become additional public score cards.
- Exactly five stable family keys. `Post-Loss Response` may display as `Result Response` only when the qualified semantic outcome genuinely compares both directions; the persisted family key remains stable.
- Publish zero to three Findings; at most one per family.
- Empty or mixed evidence is a valid result. The system must never manufacture a Finding to fill a story beat.
- Stable identity uses annual evidence. Recent, conditional, and longitudinal observations use explicit scope and tense.
- A recommendation is never evidence and never masquerades as identity.
- Five-game follow-up is descriptive and can say “too early to tell”; it cannot claim causal improvement.

### 5.2 Data and cost invariants

- One physical OpenDota summary-history request for Free V6.1 generation, followed by saved/local analysis.
- No request pagination hidden behind a logical “one history call.” If provider limits make one physical request impossible, stop and record the economic/contract conflict instead of pretending parity.
- Zero match-detail, parse, status, rank, MMR, or `average_rank` calls/inputs for Free conclusions.
- A single canonical projection and schema contract is imported by runtime collection, calibration collection, fixtures, tests, and documentation.
- Raw payload hash, request manifest, provider/schema version, projection version, normalization version, eligibility audit, and coverage audit are preserved in reproducibility metadata.
- Optional fields such as lane, `version`, party, cluster, league, and hero variant are coverage-gated. Low coverage forces fallback and suppresses public claims.
- No raw private corpus or per-player calibration artifacts are committed.

### 5.3 Statistical invariants

- Sessions, not match rows, are the independence and bootstrap unit.
- Production uncertainty uses 2,000 deterministic session-cluster bootstrap iterations and 95% intervals unless a separately versioned, validated method supersedes it.
- Any estimator that learns a core, threshold, context, boundary, era, motif, or branch from the player's own rows must cross-fit, use discovery/verification splits, or correct selection inside bootstrap. It may not discover and confirm on the same rows.
- Practical equivalence requires the complete interval inside a predeclared ROPE. `p > .05` is not equivalence.
- Apply Benjamini–Hochberg across the five family-level global hypotheses, then the frozen branches/outcomes inside qualified families using a documented hierarchical procedure.
- P-values are eligibility evidence, never editorial ranking scores.
- Every public semantic outcome must satisfy opportunity, effect/equivalence, interval, stability, robustness, copy-entitlement, confounder, and family-error-control gates.
- Every published comparison reports its real denominator: matches, events, transitions, sessions, heroes, or era segments as appropriate.
- No shared generic score bands are introduced across unrelated metrics.

### 5.4 Compatibility and safety invariants

- Existing V5 and V6.0 stored payloads remain readable by their existing validators/renderers.
- V6.1 uses new schema/model/artifact versions. Never reinterpret a V6.0 snapshot under V6.1 formulas.
- Rollback disables new V6.1 generation; it does not delete or rewrite stored V6.1 reports.
- User self-assessments remain under `user_reported`; computed evidence remains under `observed`.
- Analytics contain interaction type/state and aggregate completion only. They exclude account, hero, finding, Element, outcome, token, and free-text identity values.

## 6. Verified starting state that Sol must re-check

The following was true when this plan was written. Re-verify rather than assuming it remains true.

### 6.1 Request and ingestion

- `services/api/app/analysis/service.py` requests history with `limit` and `days=365` but no canonical projection.
- Persisted runtime metadata records `projection: null` and adapter `opendota-summary-1.0.0`.
- `services/api/app/opendota/client.py::get_matches` internally paginates in 200-row pages, so the current “one history call” is not necessarily one physical request.
- `scripts/collect_v6_calibration_histories.py` owns a different projection/version and invokes the same paginating client.
- The `AnalysisSource` protocol types `project` more narrowly than the concrete OpenDota client, while fixture sources may ignore it.
- Runtime/calibration field parity is not enforced from one shared definition.

### 6.2 Current Elements and supporting calculations

- The Toolkit Element itself already uses match-weighted fractional job mass through `metrics.match_weighted_effective_count`. Do not rewrite it as though this repair were absent.
- `hero_portfolio.py` still identifies common jobs by counting labels on established hero rows rather than weighting every match fractionally.
- `hero_portfolio.py` can produce an accidental fourth timeline sliver because of integer chunking and label clamping.
- Transfer is still a binary core/stretch contrast based on the smallest hero set covering 60% of matches.
- Transfer bootstrap samples keep the original core/stretch definition rather than re-learning or cross-fitting the boundary.
- Consistency gives small sessions too much authority by reducing each session to an equally weighted mean.
- Finishing remains unstable in low `(kills + assists)` event volumes.
- Involvement and Death Exposure need duration/context residual work described in the research.

### 6.3 Current finding families and story

- `post_loss.py` only models loss→next-match transitions, greedily chooses the first comparison, and can reuse controls without an explicit cap.
- `session_drift.py` gates long-session evidence partly by `qualifying_sessions / total_sessions`, penalizing players with many unrelated one-game sessions.
- `findings.py` applies BH across five family results but lacks a frozen nested semantic-outcome tree.
- `FindingFamilyResult.outcome_key` is derived from a small hard-coded direction map rather than a versioned semantic registry.
- `identity.py` composes strongest + second distinct family + portfolio anchor without typed `PRIMARY/TWIST/ANCHOR` eligibility and compatibility.
- `report-story-v6.tsx` already implements the nine-beat V6 story, layered evidence, interaction state, follow-up, sharing, and Deep routing. Evolve it; do not replace it with a generic dashboard.

### 6.4 Versioning and documentation

- V6.0 report, Element, finding, threshold, story, copy, recommendation, share, and interaction versions are embedded across backend, settings, fixtures, web types, compose paths, generated docs, and tests.
- Active `docs/architecture/elements.md` and `patterns.md` still foreground V5-era 18/11 concepts, while the V6 SSOT appendix says 7/5. V6.1 documentation must reconcile this without erasing history.
- `scripts/check_docs.py` does not yet prove full V6.1 registry/catalog coverage.
- Existing V6.0 calibration and release work may be dirty or in progress. Integrate rather than reset it.

## 7. Scope

### 7.1 Required in this patch

1. Canonical one-request summary-history contract and runtime/calibration parity.
2. V6.1 version routing and immutable V6.0 compatibility.
3. Typed hidden supporting-signal graph with explicit public/private boundaries.
4. The seven Element estimator repairs specified in Phase 3.
5. Frozen semantic-outcome registry and hierarchical qualification.
6. High-value P1 portfolio, Transfer, result-response, Combat Expression, and session relationships.
7. Typed identity composition, recommendation verification, and Deep cohort handoff.
8. Additive API/web rendering for the selected V6.1 interactions.
9. V6.1 calibration/evaluation artifacts, release gates, flags, monitoring, and rollback.
10. Complete active documentation and generated-catalog updates.
11. A separate post-implementation Figma documentation-agent brief.

### 7.2 Required infrastructure, shadow-only semantics

These must have typed registry entries, offline evaluation support, fixtures for unavailable/experimental states, and explicit release gates. They must not publish to ordinary users until their gates pass:

- left-truncation-aware hero lifecycle;
- name-versus-job migration and at most three identity eras;
- discovered sequence motifs and behavioral loops;
- additional GPM/XPM/damage/healing/tower residual research signals;
- hero-variant/facet sensitivity.

### 7.3 Explicitly out of scope

- Shipping all 65 research candidates.
- Adding an eighth Element or sixth family.
- Rank/MMR conditioning, cohorts, copy, or evaluation.
- New archetypes or static personality labels.
- Actual-role, position 1–5, aggression, tilt, intent, death-quality, draft-quality, or causality inference.
- Item-build identity from final inventory snapshots.
- Local-time stories from UTC timestamps or geography/latency stories from cluster.
- Billing, new authentication, or a new entitlement product.
- Rewriting historical V5/V6.0 reports.
- Making a new OpenDota specimen request.
- Updating Figma itself during the implementation unless separately authorized. This plan requires the handoff brief, not the external design-file mutation.

## 8. Version and migration contract

### 8.1 Required version strategy

In Phase 0, create one checked-in version matrix and make code/tests import it rather than duplicating literals. Unless repository constraints require a documented alternative, use these V6.1 identities:

| Surface | V6.1 identity | Compatibility rule |
|---|---|---|
| Report schema | `free-dna-report-6.1.0` | V6.0 schema remains accepted by V6.0 renderer only. |
| Runtime model | `free-dna-model-6.1.0` | New reports/jobs fingerprint exact model + artifacts. |
| Elements | `free-elements-6.1.0` | Count/names unchanged; changed estimators require new version. |
| Findings | `free-findings-6.1.0` | Five family keys unchanged; nested outcomes added. |
| Supporting signals | `supporting-signals-1.0.0` | New private graph contract. |
| Semantic outcomes | `semantic-outcomes-1.0.0` | Frozen release registry/tree. |
| Context expression | `summary-expression-multisignal-2.0.0` | Duration/context estimators changed. |
| Statistical intervals | `stats-cluster-bootstrap-2.0.0` if estimator recomputation/cross-fitting changes bootstrap semantics | Retain 1.0 only if byte-for-byte method semantics remain valid. |
| Context baseline | new V6.1 baseline schema/version | Must encode new duration/count/shrinkage inputs; do not reuse incompatible `context-baseline-2.0.0`. |
| Thresholds | `metric-thresholds-6.1.0` | Registry-driven keys and opportunity gates. |
| Claim contract | `claim-contract-2.0.0` | Adds alternatives, verification, and interaction entitlement. |
| Story | `free-story-6.1.0` | Nine beats remain; payload becomes outcome/interaction aware. |
| Semantic copy | `free-dna-semantic-copy-6.1.0` | Every semantic outcome has reviewed tokens. |
| Recommendations | `free-dna-recommendations-6.1.0` | Five-game contract is explicit. |
| Deep diagnostics | `deep-diagnostics-2.1.0` | Qualifying cohort + alternative handoff is additive. |
| Share | `share-svg-6.1.0` | Only if new eligible semantic cards ship. |
| Interactions | `report-interactions-1.1.0` | Additive V6.1 interaction state, old sessions still readable. |

Do not blindly adopt a version label when its artifact schema is unknown. The version matrix must say whether a surface is changed, compatible, migrated, or deliberately unchanged and why.

### 8.2 Stored-report behavior

- Route by `schema_version` before parsing version-specific fields.
- Preserve a V6.0 backend serializer/validator and V6.0 web type guard.
- Add a V6.1 serializer/validator and type guard; do not loosen V6.0 validation with broad optional fields.
- Persist every component version and artifact checksum in the report/job fingerprint.
- Refresh creates a new V6.1 snapshot only when V6.1 generation is enabled. It never mutates an old snapshot.
- Ensure API/worker load identical artifact bytes and reject version/checksum mismatch at startup when V6.1 is enabled.

### 8.3 Feature flags

Add or formally define:

- `FREE_DNA_V61_ENABLED`: generate V6.1 instead of V6.0 for eligible new/refresh jobs; default false.
- `FREE_DNA_V61_SHADOW_ENABLED`: compute private candidate/evaluation output without serving it; default false.
- `FREE_DNA_V61_EXPERIMENTAL_EVOLUTION_ENABLED`: lifecycle/era candidate computation in approved offline/shadow contexts only; default false.
- `FREE_DNA_V61_EXPERIMENTAL_LOOPS_ENABLED`: motif/loop discovery in approved offline/shadow contexts only; default false.

If the repository's flag framework favors one enum/version selector instead of four booleans, use that framework but preserve the same independent controls and default-off behavior.

## 9. Work breakdown

## Phase 0 — Baseline, decision record, and compatibility skeleton

### Objective

Make the change reviewable before formulas move. Freeze the current contract, create the V6.1 routing skeleton, and remove ambiguous ownership.

### Required work

1. Record baseline results for affected tests and the current dirty worktree.
2. Add characterization tests proving current V6.0 behavior:
   - exact seven Elements, five family slots, maximum three published Findings, and nine story beats;
   - Toolkit match-weighted fractional entropy is already correct;
   - current report/version fingerprints;
   - stored V6.0 API payload still renders through the V6.0 web path;
   - Free performs no detail/parse/status calls.
3. Create a version matrix in code and documentation. Replace duplicated V6 literals only where doing so does not destabilize V6.0.
4. Add V6.1 schema routing with a minimal valid fixture before adding new fields.
5. Add separate flags/config validation. Enabling V6.1 with missing or mismatched artifacts must fail closed.
6. Add a short ADR under `docs/decisions/` covering:
   - unchanged public ontology;
   - new hidden feature graph;
   - nested semantic outcomes under five families;
   - V6.0 immutability;
   - experimental lifecycle/eras/loops remaining shadow-only.
7. Add a versioned implementation-status section to this plan or a successor record. Do not rewrite planned work as completed without evidence.

### Likely files

- `services/api/app/player_analysis_v6/constants.py`
- `services/api/app/player_analysis_v6/models.py`
- `services/api/app/analysis/service.py`
- `services/api/app/settings.py`
- `apps/web/app/report/[reportId]/v6/types.ts`
- report route/version selector files
- V6 fixtures under `tests/fixtures/`
- `tests/unit/test_free_dna_v6_contract.py`
- `tests/contract/test_v6_interaction_api.py`
- a new `docs/decisions/*free-dna-v6.1*.md`

### Phase acceptance

- V6.0 characterization snapshots pass unchanged.
- A minimal V6.1 fixture is accepted only by the V6.1 validator/renderer.
- Unknown 6.x schema versions fail safely.
- V6.1 cannot start enabled with V6.0-only artifacts.
- The ADR makes the 7/5 decision and experimental boundaries explicit.

## Phase 1 — Canonical one-request summary-history contract

### Objective

Make “one cheap history call” literally true and make runtime, calibration, fixtures, and docs consume the same schema definition.

### Required ownership

Create one provider-facing contract module, for example:

```text
services/api/app/ingestion/summary_history_contract.py
```

It should own:

- projection/schema version;
- the ordered OpenDota projection field list;
- required, optional, ignored, and forbidden analytical fields;
- type/nullability normalization;
- eligible mode/lobby/leaver rules;
- UTC chronology and deduplication rules;
- coverage calculation and fallback thresholds;
- request-manifest and payload-hash schema;
- a provider-neutral normalized match record used by analysis.

The exact module name may change to fit repository ownership, but there must be one authoritative definition.

### Required projection

Start from the calibration projection already used by the repository and audit each field:

```text
match_id, player_slot, radiant_win, duration, game_mode, lobby_type,
hero_id, start_time, version, kills, deaths, assists, leaver_status,
party_size, hero_variant, leagueid, cluster, lane, lane_role, is_roaming
```

Fields absent from this projection cannot power a V6.1 production claim. Fields present but poorly covered remain optional and private. Rank/MMR-related fields are forbidden even if the provider returns them.

### Required work

1. Add a dedicated OpenDota client method that performs one physical history request with the canonical projection and 365-day boundary.
2. Do not implement this method by calling the existing auto-pagination loop. Add a transport test that counts underlying HTTP requests.
3. Define provider truncation/limit behavior. If the response can be silently capped, surface an explicit `history_completeness` status and suppress annual/longitudinal claims that require complete history.
4. Normalize and save the response once. All downstream V6.1 computation reads the saved normalized history.
5. Make runtime generation, calibration collection, fixture sources, and specimen analyzers import or validate against the same contract.
6. Broaden/fix source protocol types so sequence projections are represented correctly; fixture/mapping sources must assert or emulate projection behavior instead of ignoring it silently.
7. Persist:
   - request count;
   - request parameters excluding secrets;
   - provider and projection versions;
   - raw payload SHA-256;
   - normalized payload SHA-256;
   - raw/eligible/deduplicated counts;
   - earliest/latest match times;
   - required/optional field coverage;
   - truncation/completeness status;
   - explicit `rank_or_mmr_used=false`.
8. Remove or reconcile production/config caps such as `FREE_HISTORY_LIMIT` that violate the 365-day contract.
9. Add parity tooling that fails if runtime, calibration, fixtures, or documentation claim different projections.

### Tests

- Unit normalization tests for nulls, wrong types, duplicate matches, unsupported modes, leavers, duration bounds, side/outcome derivation, chronology, and missing optional fields.
- Transport contract test proving exactly one underlying HTTP request.
- No-detail/no-parse/no-status request spy.
- Runtime/calibration same-payload equality test: normalized bytes and eligibility audit must match.
- Coverage-fallback tests for lane/version/party/variant.
- Truncated/incomplete response tests that suppress annual/era/lifecycle claims.
- Privacy test proving request manifests contain no secrets or raw account identifiers beyond the strictly necessary protected job boundary.

### Phase acceptance

- Given the same raw fixture payload, runtime and calibration produce the same normalized history hash and audit.
- Free V6.1 makes exactly one physical history request and zero forbidden calls.
- No code outside the canonical module owns a competing projection list.
- Documentation inventory is generated or checked from the canonical contract.

## Phase 2 — Typed hidden feature graph and registry boundaries

### Objective

Create an auditable private evidence layer so many useful signals can support seven public Elements and five family tests without leaking into new public meters.

### Required model types

Add typed, versioned equivalents of:

```text
SupportingSignalDefinition
  key
  classification       # PUBLIC_ELEMENT_SUPPORT | SUPPORTING | CONDITIONAL | LONGITUDINAL | FINDING_ONLY | RESEARCH_ONLY | REJECTED
  source_fields
  opportunity_contract
  estimator_version
  normalization_version
  coverage_contract
  public_exposure      # never | evidence_only | named_when_qualified
  allowed_consumers

SupportingSignalResult
  key
  status               # available | mixed | insufficient | unavailable | suppressed | experimental
  estimate/components
  interval
  opportunities
  sessions
  coverage
  robustness
  limitations
  provenance

SemanticOutcomeDefinition
  family_key
  hypothesis_branch
  semantic_outcome_key
  evidence_groups
  opportunity_contract
  effect_or_equivalence_contract
  robustness_checks
  claim/copy entitlement
  alternatives/confounders
  recommendation_key
  verification_metric_keys
  interaction_key
  share_key
  rollout_status
```

Keep private candidate collections out of the ordinary public payload. A selected public outcome may expose the bounded evidence required by the claim contract; failed or exploratory candidates belong in protected calibration/shadow diagnostics only.

### Required work

1. Create a finite, ordered registry for supporting signals and semantic outcomes.
2. Encode all 128 research features as catalog entries or explicit grouped mappings, including `REJECTED` reasons. Do not necessarily implement all estimators.
3. Make registration fail on duplicate keys, unknown family/Element consumers, missing opportunity contracts, unversioned estimators, missing copy tokens, or public exposure of research/rejected signals.
4. Generate catalog documentation and test fixtures from the registry.
5. Add an estimator dependency graph or explicit orchestration order so computations are deterministic and cycles fail at startup/tests.
6. Attach source field, taxonomy version, baseline version, and normalization provenance to every result.
7. Add availability before effect calculation. An unavailable branch must not emit a numerical zero that looks neutral.

### Suggested module split

Use repository conventions, but keep responsibilities narrow:

- `supporting_signals.py` — types, registration, dependency orchestration;
- `portfolio_shape.py` — portfolio mass, stable core/tail, redundancy;
- `portfolio_distance.py` — continuous familiarity/function distance;
- `result_response.py` — win/loss/streak transition opportunities;
- `conditional_expression.py` — variance/covariance localization;
- `session_behavior.py` — position curves, breakpoints, stopping opportunities;
- `evolution.py` — lifecycle/migration/era candidates, shadow-only;
- `sequences.py` — motif discovery/verification, shadow-only;
- `semantic_outcomes.py` — frozen family tree and public entitlement.

Do not create files solely to match this list; merge modules when cohesion is better. Do not put the whole graph back into one `analysis.py` switch.

### Phase acceptance

- Registry validation proves there are exactly seven `PUBLIC_ELEMENT` outputs and exactly five family roots.
- The 128-feature catalog has no unclassified entries.
- Private/research signals cannot serialize as public score cards.
- Adding a new claim-changing semantic outcome requires a new key and complete contract.
- Registry order and output are deterministic.

## Phase 3 — Repair and extend the seven Element estimators

### Objective

Improve the evidence behind the existing seven public Elements without changing their count, safe meaning, or stable names.

### 3.1 Breadth

Keep Shannon effective hero count as the public score. Add a private/public-evidence `portfolio_shape` object with:

- Shannon and Simpson effective counts;
- top-1/top-3/top-5/top-50%-mass shares;
- concentration/HHI or Gini, with one chosen primary definition and versioned others;
- bootstrap-stable core membership;
- reliable stretch and experimental tail mass;
- hero/job redundancy and single-point job coverage;
- rolling chronological windows for evidence, never silent recency weighting.

Do not combine these into a composite Breadth number. They explain the shape behind the existing score.

Fix `hero_portfolio.py` so common job evidence is match-weighted and fractionally split across labels. Add a test where one frequent multi-job hero outweighs several rare established heroes. Replace the chunking logic with exactly three non-overlapping chronological thirds or a named rolling-window structure; no accidental fourth sliver.

### 3.2 Toolkit

Preserve the already-correct match-weighted fractional entropy estimator. Work here is characterization and sensitivity:

- taxonomy coverage remains at least 80% for public availability;
- each match contributes total job mass 1 divided across mapped labels;
- add taxonomy version and sensitivity/perturbation status;
- suppress contradictions that disappear under plausible label perturbation;
- make supporting portfolio job summaries use the same mass definition.

Do not count “fix Toolkit” as complete merely because code changed; prove the existing correct behavior and remove inconsistent supporting calculations.

### 3.3 Involvement

Replace a single global rate residual with a versioned, cross-fitted, coverage-aware context estimator:

- response: `kills + assists` count;
- duration: nonlinear duration term or duration exposure appropriate to the selected model;
- covered context: hero first, fractional function fallback, and only literal covered lane context;
- no role inference and no “participation”/“aggression” wording;
- artifact stores the trained coefficients/cells, dispersion, fallback hierarchy, minimum counts, and calibration version;
- runtime returns adjusted estimate plus baseline/fallback provenance and coverage.

Select the simplest model that passes held-out calibration. Do not adopt a complex hierarchy for prestige; compare it against the current baseline on stability, coverage, and residual calibration.

### 3.4 Finishing

Make Finishing event-weighted and stabilized:

- aggregate kills out of total `kills + assists` opportunities;
- use a versioned beta-binomial/empirical-Bayes estimator trained without holdout leakage;
- zero-event matches contribute no share likelihood but do contribute to the coverage audit;
- require explicit total-event, match, and session opportunity gates;
- report posterior/interval uncertainty and abstain when events are thin;
- keep Finishing a modifier of summary expression, not a judgment of kill-securing quality.

Tests must include zero events, one giant-event match, many low-event matches, identical shares with different opportunity volumes, and context fallback.

### 3.5 Death Exposure

Use an overdispersed count/rate model with duration exposure and covered context:

- response: deaths count;
- exposure: match duration;
- robust dispersion/variance treatment;
- hero/function/literal-lane fallback only when cells meet training gates;
- output keeps native “higher observed death exposure” orientation and safe limitations;
- never infer positioning, intent, value, or preventability.

Compare against the current deaths-per-ten residual and require better held-out calibration or stability before promotion.

### 3.6 Transfer

Replace binary-only core/stretch analysis with a cross-fitted continuous distance model while retaining a simple UI frontier.

Define player-specific distance from:

- familiarity mass/frequency relative to a core learned only from training folds; and
- function distance from the weighted core job mixture using a versioned distance metric.

Calibrate named bands such as `core`, `reliable_stretch`, and `experimental_edge`; do not hard-code attractive cutoffs without training/holdout evidence. For every supported distance band, estimate three components:

- outcome;
- adjusted involvement/activity;
- adjusted death-exposure/survival orientation.

The public Transfer boundary is the farthest band whose required component intervals satisfy the versioned practical-equivalence/compatibility contract. Preserve semantic subtypes:

- clean transfer;
- result stops first;
- expression stops first;
- involvement boundary;
- exposure boundary;
- localized function bottleneck;
- mixed/unavailable.

Core/distance definition and contrast evaluation must be cross-fitted or fully recomputed inside bootstrap. A fixed full-history 60% core reused in every bootstrap is not sufficient V6.1 evidence.

### 3.7 Consistency

Separate internal repeatability components before synthesizing the public score:

- outcome repeatability;
- involvement repeatability;
- death-exposure repeatability;
- optional Finishing modifier only when its event gate passes;
- variance attribution by hero, function, core distance, session position, and residual within-context noise when support permits.

Shrink tiny-session means toward the player's annual center using a training-only, versioned information-weighting rule. One one-game session must not carry the same precision as a ten-game session. Retain session independence and robust dispersion.

Publish a single Consistency Element only when the component synthesis rule qualifies; otherwise use mixed/insufficient. Localized variance can support a Combat Expression semantic outcome without changing the global score.

### Common estimator tests

- deterministic seed and stable ordering;
- full-estimator recomputation in clustered bootstrap where required;
- odd/even and chronological stability;
- leave-one-dominant-hero sensitivity;
- taxonomy perturbation;
- sparse/missing context fallback;
- extreme durations and event counts;
- one-match versus long-session weighting;
- equivalence interval behavior;
- mixed/opposing components;
- unavailable does not become neutral.

### Phase acceptance

- Exactly seven public Element results serialize.
- Every changed estimator has a new version and artifact dependency.
- Toolkit characterization proves no regression from the already-correct core estimator.
- Transfer is distance/frontier based and cross-fitted.
- Consistency no longer treats tiny and large sessions as equally precise.
- Finishing abstains on thin event volume.
- Involvement/Death Exposure include duration/context provenance and pass their selected calibration comparison.

## Phase 4 — Frozen semantic outcomes and hierarchical family testing

### Objective

Turn each family from one coarse directional result into a finite, statistically governed set of meaningful relationships.

### 4.1 Registry rules

For V6.1, predeclare the public-candidate tree before calibration. Candidate generation may compute more private signals, but public semantic selection is limited to the frozen registry. Every outcome must specify:

- family and hypothesis branch;
- independent evidence groups;
- exact opportunity denominator and minimums;
- estimator/normalization/taxonomy/baseline versions;
- difference or equivalence contract and ROPE;
- family/branch error-control placement;
- temporal, dominant-hero, session-boundary, and taxonomy robustness requirements;
- supported and forbidden claim tokens;
- alternatives/confounders;
- recommendation and verification eligibility;
- interaction/share eligibility;
- public, shadow-only, or rejected rollout status.

### 4.2 Required first-wave public candidates

Implement and calibrate a deliberately small, high-value set. Final public enablement is per-outcome; an outcome that misses gates remains shadow-only without blocking unrelated outcomes.

#### Pool Shape

- `hidden_center` — wide effective pool with concentrated stable core.
- `names_wide_jobs_narrow` — hero-name diversity qualifies while job mixture is practically concentrated.
- `names_narrow_jobs_wide` — narrower hero set covers a qualified broad job mixture.
- `names_changed_jobs_held` — chronological hero distribution changes while job mixture is equivalent; must meet stronger longitudinal gates.

#### Transfer

- `clean_transfer` — outcome and expression remain equivalent through a supported distance frontier.
- `results_stop_first` — outcome diverges closer to core while expression remains equivalent farther out.
- `expression_stops_first` — result remains equivalent while activity/exposure diverge sooner.
- `involvement_boundary` and `exposure_boundary` — a supported component-specific frontier.
- `localized_function_bottleneck` — only when one mapped function independently localizes the gap and taxonomy sensitivity passes.

#### Post-Loss Response / editorial Result Response

- `one_loss_runback` — repeat/near-core probability differs after exactly one loss.
- `two_loss_switch` — the second consecutive loss is a replicated threshold, not an arbitrary best split.
- `result_shaped_pool` — wins and losses precede opposite, supported selection-distance movements.
- `result_invariant_response` — selection response is practically equivalent across result states.
- `adjustment_without_recovery` or its safe inverse — selection/expression changes but next-result evidence is equivalent, with no causal wording.

#### Combat Expression

- `involvement_holds_exposure_moves`.
- `exposure_holds_involvement_moves`.
- `same_expression_different_results`.
- `different_expression_same_results`.
- `localized_variance` — experiments/one hero/function explain a qualified share of variance; no blame language.

#### Session Drift

- `opening_game_signature`.
- `gradual_session_drift`.
- `predeclared_breakpoint` — compare only frozen candidate positions such as Game 2/3/4, with discovery/verification.
- `selection_only_drift` — pool choices move while expression remains equivalent.
- `bounded_stopping_response` — completed, boundary-safe session stopping differs after a frozen result state; no “fatigue” or intent claim.

These keys are descriptive placeholders until code registry naming is finalized. Once fixtures or artifacts use a key, semantic renaming requires an explicit migration/version change.

### 4.3 Opportunity construction

#### Result-response transitions

Replace the current greedy post-loss structure with records containing:

```text
prior_result, prior_run_length, source_match, next_match,
session_position, calendar band, source/next hero,
same_hero, job_overlap, familiarity/function distance movement,
continued_or_stopped, outcome/activity/exposure response,
left/right censor status
```

- Model wins, exactly one loss, and 2+ streak states.
- Controls must use no replacement, capped reuse, or explicit balancing weights with effective-sample diagnostics.
- Never let an early ordered row become the repeated comparison for many transitions.
- Predeclare state levels and threshold candidates.
- Exclude cross-session “next matches” from within-session response unless a separate calendar-response branch is registered.

#### Session behavior

- Build direct position opportunities for G1, G2, G3, G4, and G5+.
- Gate each comparison on observations and independent qualifying sessions at the relevant positions, not the proportion of all sessions that happen to be long.
- Treat the end of the observed 365-day window and incomplete/censored sessions explicitly.
- Run 60/90/120-minute session-boundary sensitivity for stopping or loop claims.
- Separate selection into a long session from within-session change; never label either as fatigue.

### 4.4 Family and branch statistics

1. Compute availability first.
2. Calculate one global/omnibus p-value per stable family from the frozen branch set.
3. Apply BH across exactly five family p-values at `q ≤ .05`.
4. Only for qualified families, apply the documented hierarchical allocation/adjustment inside that family.
5. A semantic outcome qualifies only if its effect/equivalence, interval, opportunity, stability, robustness, and copy gates also pass.
6. Rank qualified outcomes by evidence strength × user recognition/OOOH × evidence diversity × actionability; never by smallest p-value.
7. Publish at most one outcome per family and at most three total.
8. Suppress generic Element restatements when a stronger localized outcome explains the same evidence.
9. Suppress weaker component claims when a qualified chain/contradiction subsumes them.
10. Persist the full public selection audit without leaking failed private hypotheses into the user payload.

### Tests

- Synthetic null across all five families controls realized FDR.
- Dependent branch synthetic fixtures exercise hierarchical FDR.
- Equivalence fixtures distinguish interval-inside-ROPE from nonsignificance.
- No-control-reuse/capped-weight assertions.
- One-loss versus 2+ streak-state separation.
- Direct session-position denominators.
- Conflict, chain, redundancy, one-per-family, and max-three selection.
- Empty-state report with no qualified Findings.
- Copy entitlement rejects an unregistered semantic key or missing robustness gate.

### Phase acceptance

- Five family roots remain stable.
- The first-wave registry is finite and machine-reviewable.
- No public semantic outcome is selected through an unadjusted search.
- A report can honestly publish zero Findings.
- Every selected outcome exposes claim, evidence, interpretation, alternatives, recommendation eligibility, and verification contract separately.

## Phase 5 — Experimental lifecycle, evolution, eras, and loops

### Objective

Implement evaluation-capable P2 infrastructure without promoting seductive in-sample stories.

### 5.1 Hero lifecycle

- Use “first observed in the 365-day window,” never “discovered,” unless lifetime history exists.
- Define trial/tested/retained/dormant/returned from predeclared match/session/time opportunities.
- Account for left truncation and right censoring.
- Require at least the research gates: sufficient left-bound-safe candidates, retained events, matches, and sessions.
- Keep public outcome off until sensitivity and recognition review pass.

### 5.2 Name-versus-job migration and identity eras

- Session-block chronology; never split a session.
- Candidate features: hero composition, fractional job composition, Breadth/Toolkit, and optional covered expression centers/variances.
- Result is not the primary era-boundary objective.
- Use PELT or segment-neighborhood with a penalty calibrated on stationary simulations and held-out real histories.
- Maximum three eras.
- Minimum per era: 120 matches, 45 sessions, 45 observed days, and at least 10% of usable span.
- Discovery/verification or nested selection correction is mandatory.
- Require bootstrap boundary stability within ±14 days, 60/90/120-minute sensitivity, leave-one-hero-out, and taxonomy perturbation.
- Copy must name patch/meta as an unresolved alternative, never as the proven cause.
- “Stable year/no qualifying chapter” is a successful null outcome.

### 5.3 Sequence motifs and behavioral loops

- Encode a small observable state alphabet only: result, core-distance band, repeat/job-overlap/switch, session position, and cross-fitted expression band.
- Mine length 2–5 within-session motifs on discovery rows; qualify only frozen motifs on holdout rows.
- Minimum public gate: 30 non-overlapping occurrences in at least 20 sessions; lower 95% lift bound >1.25 versus the player's first-order transition baseline; no unnamed hero >40% of occurrences; directional lift in both chronological halves; session-boundary sensitivity; family qualification; and no shorter motif explaining the lift.
- Loops remain shadow-only in this patch unless every gate and user-comprehension review passes.

### Experimental phase acceptance

- Feature flags prevent ordinary public serialization.
- Stationary simulations measure false-era and false-loop rates.
- In-sample best boundaries/motifs cannot pass as verified results.
- Unavailable/null outcomes are first-class fixtures.
- Promotion requires a separate recorded decision and version update if it changes public copy entitlement.

## Phase 6 — Identity, claims, recommendations, and Deep handoff

### Objective

Make richer findings understandable without turning them into archetypes or overclaiming mechanisms.

### 6.1 Claim contract 2.0

Every published Finding must expose distinct fields for:

```text
CLAIM            literal supported relationship
EVIDENCE         estimate/interval/equivalence, denominator, sessions, coverage, comparison
INTERPRETATION   bounded user-facing meaning
ALTERNATIVES     plausible missing-data/context explanations
RECOMMENDATION   optional action allowed by summary evidence
VERIFICATION     five-game eligibility, controlled context, primary metric, guardrail, baseline
INTERACTION      allowed renderer and data, if any
DEEP HANDOFF     qualifying cohorts, exact IDs privately, comparison definition, unanswered questions
```

Do not collapse fields into one generated paragraph. Copy stays deterministic and registry-owned.

### 6.2 Dynamic identity

Replace strongest + second + anchor assembly with typed slots:

- `PRIMARY`: annual identity evidence stable in at least two chronological thirds.
- `TWIST`: one compatible contradiction, condition, or longitudinal change, preferably from a different family.
- `ANCHOR`: established hero, stable core, or top mapped job with adequate coverage.

Add a registry-owned compatibility matrix for redundancy, contradiction, temporal tense, grammar, and safe combinations. A primary may stand alone. A twist is optional. An anchor cannot be a disguised recommendation.

Required language scopes:

- `This year…` for annual evidence;
- `Recently…` for recent-state evidence;
- `In longer sessions…`, `After one loss…`, or comparable literal scope for conditional evidence;
- never flatten all three into a timeless personality label.

### 6.3 Recommendations and five-game follow-up

Every actionable outcome declares:

- what counts as one of five eligible games;
- approximate controlled context;
- one primary metric;
- one guardrail metric;
- baseline comparison;
- minimum data and abstention rule;
- descriptive follow-up wording.

Only recommend hero/toolkit choices or summary-observable behavior supported by the outcome. Deep-only topics remain positioning, death quality, items/timings, objectives, fight entry, draft mechanisms, and causality.

### 6.4 Deep handoff

Extend the existing Deep diagnostic question payload additively with protected references to:

- exact qualifying match/session cohorts;
- context/distance/result/session definitions;
- positive, negative, and control comparison groups;
- estimator/taxonomy/baseline/outcome versions;
- unresolved alternatives;
- the precise question that parsed evidence could answer.

The public report must not expose raw IDs. Deep may use the protected server-owned cohort references after authorization.

### Tests

- slot eligibility and compatibility matrix;
- primary-only and no-identity fallbacks;
- tense/scope token enforcement;
- observation/evidence/interpretation/alternatives/recommendation separation;
- forbidden-token catalog over every semantic outcome/direction/confidence combination;
- five-game eligibility and too-early-to-tell behavior;
- Deep handoff cohort integrity and authorization;
- no raw identifiers in public JSON or analytics.

### Phase acceptance

- Identity remains evidence composition, not an archetype lookup.
- Every public claim has alternatives and provenance.
- Every recommendation has a verification contract or is absent.
- Deep receives enough protected context to diagnose the exact Free relationship without Free claiming the mechanism.

## Phase 7 — API, web story, and interaction implementation

### Objective

Evolve the existing nine-beat story to reveal V6.1 relationships. Do not turn the report into a permanently expanded dashboard.

### 7.1 API/schema changes

Add V6.1-only types for:

- selected semantic outcome;
- supporting evidence safe for public display;
- alternatives/limitations;
- verification contract;
- interaction descriptor and its bounded payload;
- optional primary/twist/anchor identity slots;
- protected Deep cohort reference, not raw cohort IDs.

Generate the API client and web types from the canonical schema where the repository supports generation. The client must not recompute statistical meanings.

### 7.2 First-wave interactions

Implement reusable renderers keyed by a finite `interaction.kind`, prioritizing:

- `core_boundary` for Transfer frontiers;
- `after_x` for win/one-loss/2+-loss states;
- `two_versions` for result/expression contradictions;
- `contradiction_reveal` for names-versus-jobs or equivalent relationships;
- `session_curve` for G1→G5+ evidence;
- `variance_decomposition` if its evidence qualifies;
- the existing five-game commitment flow with V6.1 eligibility/guardrail fields.

Add typed but disabled/fixture-only support for:

- `identity_eras`;
- `hero_lifecycle`;
- `behavioral_loop`.

Unsupported, thin, or experimental states must render a truthful fallback, not a decorative empty chart.

### 7.3 Story rules

- Preserve nine ordered, skippable beats and the existing state/resume model unless a separately approved UX decision changes it.
- One interaction reveals one relationship.
- Hatched/disabled distance bands show unsupported evidence.
- Counts and sessions remain visible near conditional claims.
- Alternative explanations are accessible without burying the main claim.
- Self-estimates remain interaction prompts, never analytical evidence.
- Share candidates require their own high-confidence, no-confounder, standalone-context gate.

### 7.4 Accessibility and responsive behavior

- Keyboard, touch, and screen-reader operation for every interaction.
- Visible focus; semantic headings/controls; appropriate names, states, and descriptions.
- Reduced-motion mode does not hide evidence or require animation comprehension.
- Usable at 200% zoom, narrow mobile viewport, and with long localized copy.
- Color is not the sole state/direction encoding.
- Charts expose a textual/table alternative for estimates, intervals, and denominators.
- Interaction state is restorable and schema/revision validated.

### 7.5 Analytics and privacy

Allow only coarse events such as interaction opened, state selected, evidence drawer opened, commitment selected, follow-up completed, and story completed. Strip report/account/player/hero/finding/Element/outcome/free-text values. Document retention and aggregation.

### Tests

- V6.0 and V6.1 route/type-guard separation.
- Schema snapshots for each public first-wave interaction and every fallback.
- Component tests for keyboard/touch/reduced-motion/text alternative.
- E2E for a report with 0, 1, 2, and 3 Findings.
- E2E for resume/revision conflict/expiry/deletion/follow-up.
- Visual regression at desktop, narrow mobile, 200% zoom, dark/light if supported, and long copy.
- Analytics payload allowlist test.
- No client-side outcome selection or statistical recomputation.

### Phase acceptance

- The existing story remains coherent with no V6.1 Finding.
- Each first-wave outcome has one supported renderer or an explicit text-only fallback.
- All interactions meet accessibility and privacy requirements.
- V6.0 stored reports still render unchanged.

## Phase 8 — Calibration, evaluation, artifacts, and release controls

### Objective

Calibrate V6.1 without holdout leakage, measure whether it improves on V6.0, and keep release disabled until evidence and people approve it.

### 8.1 Corpus and split discipline

- Reuse the existing consented/private corpus if its canonical projection/completeness audit passes.
- Do not recollect merely because V6.1 exists. Recollect only if a documented required field or completeness gate fails and the user separately authorizes network/data work.
- Preserve the player-exclusive frozen training/holdout split where statistically valid.
- If the new contract invalidates the corpus, mark calibration blocked; do not silently create proxy fields.
- Training fits baselines, priors, distance bands, ROPEs, opportunity gates, penalties, and candidate registries.
- Holdout evaluates frozen bytes once. It never tunes them.

### 8.2 Artifact schemas

Create V6.1 aggregate artifacts for:

- context/duration models and fallback cells;
- Finishing priors/opportunity gates;
- metric zones/ROPEs and confidence gates;
- portfolio-distance bands/frontier parameters;
- session shrinkage and variance parameters;
- semantic-outcome branch thresholds and robustness gates;
- synthetic/holdout evaluation;
- release manifest with checksums, source revision, commands, versions, counts, and approvals.

Runtime loads only approved analytical artifacts. Evaluation/release manifests remain audit evidence, not inputs.

Replace fragile tests that assert “exactly 19 threshold metrics” with a versioned registry-manifest assertion: exact equality between required runtime keys and artifact keys for that model version. Unknown, missing, and extra keys fail closed.

### 8.3 Required comparisons

Evaluate V6.1 against frozen V6.0, not against a strawman. At minimum compare:

- request count and normalized-history parity;
- Element availability and abstention;
- interval coverage and width;
- split-half/chronological stability;
- family FDR and semantic-branch false discovery;
- duplicated/generic Finding rate;
- top-Finding recognition and supported-believable reviewer precision;
- forbidden/causal/role-language rate;
- report latency and memory;
- story completion and comprehension in approved internal tests;
- proportion of players receiving honest 0/1/2/3 Findings.

V6.1 must not “win” merely by publishing more.

### 8.4 Automated gates

Retain or strengthen existing V6 gates:

- synthetic 95% interval coverage between 93% and 97% for registered estimators;
- family-level empirical FDR ≤5%;
- registered semantic-branch empirical FDR within the documented hierarchical target;
- no runtime/calibration projection mismatch;
- exact one-request/zero-detail/zero-parse Free cost boundary;
- nonblank identity and high-confidence split-half thresholds at least as strong as V6, with per-outcome coverage reported;
- zero forbidden public claims over the full generated copy catalog;
- no experimental era/lifecycle/loop public output with flags off;
- deterministic artifacts and reports for fixed bytes/seed/version;
- API and worker artifact checksum equality;
- acceptable latency/memory budgets defined from measured V6 baseline, not invented after results.

Add specific P2 gates:

- era false-positive rate on stationary simulations and boundary robustness;
- lifecycle left/right-censor correctness;
- loop/motif discovery/verification false-positive rate and support thresholds;
- session-boundary sensitivity for stopping/loops;
- taxonomy perturbation for name/job and function-bottleneck claims.

### 8.5 Human gates

- Dota reviewer precision ≥90% for “supported and believable,” sampled across positive, negative, mixed, insufficient, and adversarial fixtures.
- Independent statistical review of cross-fitting, equivalence, hierarchy, selection correction, and holdout discipline.
- Copy review for overclaim, scope/tense, alternatives, and recommendation safety.
- Accessibility review of every first-wave interaction.
- Product comprehension review that the richer story does not read like extra permanent scores.
- Explicit operator rollout authorization.

### 8.6 Rollout and rollback

Rollout sequence:

```text
fixture/synthetic
  → offline private corpus
  → shadow generation
  → staff reports and blinded QA
  → 5% canary
  → 25%
  → 100%
```

Each stage needs predeclared stop conditions for errors, latency, cost, abstention collapse, forbidden copy, unexpected report-shape drift, or interaction failures. Rollback disables new V6.1 generation and restores the previous selector. Stored V6.1 reports remain readable.

### Phase acceptance

- State A can be achieved entirely with fixtures/synthetic data.
- State B requires frozen training artifacts and a sealed-holdout record.
- State C cannot be self-declared by passing tests alone.
- Default V6.1 and experimental flags remain off.
- Release and rollback commands are tested and documented.

## Phase 9 — Repository documentation and generated artifacts

### Objective

Make the repository explain the system that actually ships. Documentation is part of the patch, not cleanup deferred after merge.

### 9.1 Documentation ownership rules

- Keep the V6.1 research document as a research/evidence record. Link to it; do not turn it into the runtime SSOT.
- Active architecture docs describe the current V6.1 design and explicitly label V5/V6.0 historical compatibility.
- Preserve historical release records. Add V6.1 documents rather than retroactively pretending V6.0 used V6.1 formulas.
- Generate registries/catalogs from code and make drift checks fail CI.
- Write for three readers: product/Dota reviewer, backend/statistics engineer, and web/design implementer.
- Lead every document with what the reader should understand or do.

### 9.2 Required active-document updates

Audit and update at least:

- `README.md` — current product path, 7/5 contract, V6.1 architecture/release links.
- `ARCHITECTURE.md` — V6.0/V6.1 routing, one-request boundary, hidden graph, artifacts, flags, rollback.
- `docs/README.md` and `docs/architecture/README.md` — correct reading order and links.
- `docs/architecture/free-dna-system.md` — end-to-end V6.1 flow and public/private boundaries.
- `docs/architecture/free-dna-v6-statistics.md` — versioned V6.0 versus V6.1 estimator/error-control contract. Rename only if all inbound links/migrations are handled.
- a new `docs/architecture/free-dna-v6.1-feature-graph.md` — the seven Elements, supporting-signal classes, five family branches, semantic-outcome lifecycle, and suppression rules.
- `docs/architecture/elements.md` — reconcile historical V5 18-Element material with the active V6.1 seven-Element contract.
- `docs/architecture/patterns.md` — reconcile historical 11-pattern material with five family roots and nested semantic outcomes.
- `docs/architecture/pattern-presentation.md` — claim/evidence/interpretation/alternatives/recommendation/verification and interaction rules.
- `docs/architecture/hero-portfolio.md` — match-weighted fractional jobs, shape object, continuous distance, chronology, taxonomy sensitivity.
- `docs/architecture/report-flow.md` — schema routing, nine beats, empty state, interactions, follow-up, Deep handoff.
- `docs/architecture/data-provenance.md` — request/payload hashes, projection/completeness, estimator/artifact versions, protected cohorts.
- `docs/architecture/dota-dna-ssot.md` — active V6.1 ontology and explicit historical appendices.
- `docs/architecture/deep-diagnostics-v2.md` — exact-cohort V6.1 handoff and unanswered alternatives.
- `docs/evidence-contract.md` — cross-fitting, equivalence, hierarchical FDR, censoring, safe language, opportunity denominators.
- `docs/opendota-data-inventory.md` — canonical projection, coverage gates, forbidden inferences, one-request semantics.
- `docs/system-behavior-baseline.md` — V6.0 versus V6.1 flags, routes, stored-report behavior, empty/mixed states.
- `docs/qa/free-dna-v6-release-gates.md` — keep as V6.0 historical/active record as appropriate.
- a new `docs/qa/free-dna-v6.1-release-gates.md` — automated/human/experimental gates and evidence locations.
- `docs/operations/free-dna-v6-release.md` — preserve current V6.0 operations and link the new path.
- a new `docs/operations/free-dna-v6.1-release.md` — artifact promotion, shadow/canary, monitoring, rollback, incident actions.

### 9.3 Generated/documented contracts

Update generators and checked outputs for:

- model/version catalog;
- Element and supporting-signal registry;
- family/semantic-outcome registry;
- copy review catalog, including every direction/confidence/suppression state;
- interaction renderer/state catalog;
- OpenAPI and generated API client;
- artifact schema/key manifest;
- forbidden-claim and classification catalog.

Likely paths include `docs/architecture/model-catalog.md`, `docs/generated/`, `scripts/generate_*`, and API client outputs. Follow actual repository generators.

### 9.4 Documentation CI

Extend `scripts/check_docs.py` or equivalent so CI fails when:

- a V6.1 version/registry key is undocumented;
- active docs claim the wrong Element/family count;
- an outcome has no copy/alternatives/verification/interaction documentation;
- a projection field or coverage rule drifts from the canonical contract;
- a generated catalog is stale;
- a relative link is broken;
- V5/V6.0 historical content is presented as the active V6.1 contract;
- a rejected inference appears in active public-copy guidance.

### Documentation acceptance

- A new engineer can follow README → architecture → statistics → release without reading historical plans.
- A product/Dota reviewer can see why supporting signals are not new Elements.
- A web/design implementer can map every public outcome to payload fields, interaction, fallback, accessibility, and safe copy.
- All generators and `docs-check` pass with no hand-edited generated drift.
- Every materially changed code contract has an updated active document in the same patch.

## Phase 10 — Figma documentation-agent brief

### Objective

After implementation and repository documentation are accurate, Sol must create a standalone brief for a separate agent to update the V6.1 documentation in Figma.

### Required output

Create:

```text
docs/design/free-dna-v6.1-figma-documentation-update-agent-brief.md
```

If `docs/design/` does not exist, create it and add it to the appropriate documentation index.

### Timing rule

Write this brief **after** the implemented schema, story, interactions, copy catalog, and accessibility behavior are known. The brief must describe what landed, what stayed V6.0-compatible, and what remains experimental. It must not repeat planned features as shipped facts.

### Required brief contents

1. **Mission and non-goals**
   - Update Figma documentation, component annotations, state diagrams, and report-flow references for V6.1.
   - Do not redesign the product, invent new Elements/families, rewrite approved copy, or enable experimental views.

2. **Authoritative inputs**
   - exact implemented schema/model versions;
   - links to the final architecture, statistics, feature-graph, pattern-presentation, report-flow, evidence, accessibility/QA, and release docs;
   - links to the V6.1 web components, tokens/styles, fixtures, Storybook/screenshots if present, and interaction tests;
   - the research document as rationale only, clearly below implemented docs in precedence.

3. **Figma target inventory**
   - file URL/key, team/project, page names, sections, frames, components, variables, prototypes, and annotations to update;
   - exact “before → after” mapping for every affected node when discoverable;
   - if no Figma file or node references exist, state that as the only required user input and instruct the future agent not to guess a target.

4. **Product model to document**
   - exactly seven visible Elements and five family roots;
   - supporting signals are hidden evidence, not new cards;
   - zero-to-three Findings and truthful empty state;
   - typed `PRIMARY + optional TWIST + ANCHOR` identity;
   - claim/evidence/interpretation/alternatives/recommendation/verification layers;
   - one-request Free versus parsed-data Deep boundary.

5. **Screen and component changes**
   - version-routing/documentation note for V6.0 versus V6.1;
   - all implemented first-wave interaction kinds and their states;
   - disabled, loading, unavailable, insufficient, mixed, experimental, and error states;
   - 0/1/2/3 Finding story variants;
   - commitment and follow-up states;
   - share eligibility and Deep handoff entry;
   - no public frames for shadow-only lifecycle/era/loop behavior unless clearly labeled internal/experimental documentation.

6. **Data-to-design mapping table**
   - API field/path;
   - component/frame;
   - displayed copy/data;
   - state/eligibility rule;
   - fallback;
   - analytics event if any;
   - source code/test reference.

7. **Copy and evidence guardrails**
   - supported scope/tense;
   - forbidden inference list;
   - visible denominators, intervals/equivalence, coverage, and alternatives;
   - no causal language or invented role/intent;
   - no placeholder copy that changes a semantic outcome.

8. **Accessibility/responsive annotations**
   - keyboard/touch/focus order;
   - screen-reader labels/descriptions;
   - reduced motion;
   - 200% zoom and narrow mobile;
   - non-color state encoding;
   - textual alternative for visual evidence;
   - long/localized copy behavior.

9. **Prototype behavior**
   - transitions and state persistence;
   - resume/follow-up behavior;
   - unsupported-state fallback;
   - which animations are explanatory versus decorative;
   - no fake continuous precision or interactive states unsupported by API payloads.

10. **Deliverables and Definition of Done for the Figma agent**
    - updated pages/components/annotations/prototypes;
    - changelog listing node links and decisions;
    - implementation parity checklist against web fixtures;
    - accessibility annotation review;
    - screenshots or export references for changed states;
    - unresolved questions returned to engineering/product;
    - explicit confirmation that experimental behavior was not presented as public.

### Brief acceptance

- The future Figma agent can execute without reading the entire Git history.
- Every claim in the brief points to implemented code/docs/tests.
- Missing Figma coordinates are called out, not invented.
- The brief separates repository implementation completion from Figma update completion.

## Phase 11 — Final verification and handoff

### Objective

Prove the requested patch is complete at the claimed state and stop without silently expanding scope.

### Required command groups

Run the repository's actual commands; update this list if Make targets changed:

```text
make lint
make typecheck
make test
make test-contract
make test-integration
make api-client
make taxonomy-validate
make dna-catalog
make dna-catalog-check
make copy-review-catalog
make copy-review-catalog-check
make docs-check
make test-e2e
```

Also run focused V6.1 suites for:

- canonical one-request ingestion and parity;
- all seven Element estimators;
- semantic registry/hierarchical testing;
- identity/recommendation/Deep handoff;
- API schemas/version routing;
- interaction accessibility and privacy;
- calibration builders/validators/evaluators;
- release/rollback smoke behavior.

Long-running real-corpus, holdout, E2E, and human gates must be reported separately. Do not mark an unrun command as passing.

### Required final handoff from Sol

Provide:

1. the achieved completion state(s) A/B/C/D;
2. concise outcome summary;
3. changed-contract/version matrix;
4. list of public first-wave outcomes actually enabled;
5. list of shadow-only/withheld outcomes and why;
6. exact tests/commands run and results;
7. calibration/release artifact paths and checksums, if State B/C;
8. remaining human/operator gates;
9. compatibility and rollback proof;
10. documentation files updated/generated;
11. link to the Figma documentation-agent brief;
12. known limitations and deliberate abstentions;
13. confirmation that public flags remain in the intended default state.

## 10. Cross-phase test matrix

| Risk | Required proof |
|---|---|
| “One call” is still pagination | HTTP transport counter asserts one physical history request. |
| Runtime/calibration drift | Same raw fixture yields identical normalized hash, coverage, eligibility, and features. |
| V6.0 reports break | Frozen V6.0 backend/web snapshots and route tests pass. |
| Extra signals become extra meters | Registry and schema assert exactly seven public Element results. |
| Family proliferation | Registry asserts exactly five family roots and one outcome/family. |
| Statistical fishing | Frozen tree, family omnibus, hierarchical FDR, discovery/verification tests. |
| Nonsignificance called equivalence | Interval-inside-ROPE test and adversarial fixture. |
| Learned core tested on same rows | Cross-fit fold isolation and bootstrap recomputation test. |
| Tiny sessions dominate Consistency | Synthetic equal-pattern histories with different session sizes. |
| Thin events create confident Finishing | Low-event abstention and posterior-width tests. |
| Controls are reused greedily | Matching/weight-cap invariant and effective-sample diagnostics. |
| One-game sessions suppress drift | Direct G-position opportunity tests. |
| Stopping implies intent | Censoring + 60/90/120 sensitivity + copy-token tests. |
| Eras/loops overfit | Stationary simulations and held-out boundary/motif verification. |
| Taxonomy fiction | Coverage/perturbation tests and explicit mapped-job wording. |
| Public payload leaks IDs/private candidates | Schema/privacy/analytics allowlist tests. |
| UI recomputes meaning | API fixture-to-renderer tests with no client statistical branch. |
| Accessibility regresses | Keyboard, focus, screen reader, reduced motion, zoom, mobile, text alternative. |
| Docs drift | Registry/projection/version/generated catalog checks in `docs-check`. |
| Figma brief claims planned work shipped | Brief references final code/tests and lists withheld features. |

## 11. Definition of Done

### 11.1 Merge Definition of Done — State A

All boxes must be true before Sol calls the patch implementation-complete:

- [ ] V6.0 behavior is characterized and remains readable/renderable.
- [ ] V6.1 has distinct schema/model/component versions and fail-closed artifact validation.
- [ ] Free V6.1 performs exactly one physical canonical history request and zero forbidden calls.
- [ ] Runtime, calibration, fixtures, and docs share one projection/normalization contract.
- [ ] Raw/normalized hashes, request manifest, completeness, eligibility, and coverage are reproducible.
- [ ] The typed signal registry enforces exactly seven public Elements and five family roots.
- [ ] All 128 researched features are classified; unimplemented/rejected ones are explicit.
- [ ] Breadth shape evidence exists without becoming a composite/new score.
- [ ] Toolkit core estimator is preserved and all supporting job summaries use its fractional weighting semantics.
- [ ] Involvement, Finishing, Death Exposure, Transfer, and Consistency repairs are implemented and versioned.
- [ ] Transfer uses cross-fitted continuous distance/frontier evidence.
- [ ] Consistency uses information-weighted/shrunk session evidence.
- [ ] Finishing has event-opportunity gates and honest abstention.
- [ ] The first-wave semantic-outcome registry is frozen and machine validated.
- [ ] Five family omnibus tests and nested hierarchical FDR are implemented.
- [ ] Result response covers wins, exactly one loss, and 2+ loss states without uncontrolled control reuse.
- [ ] Session curves use direct position opportunities and stopping is censor-aware.
- [ ] Lifecycle/eras/loops are flag-protected and cannot publish accidentally.
- [ ] Identity uses typed `PRIMARY + optional TWIST + ANCHOR` compatibility.
- [ ] Every public Finding separates claim, evidence, interpretation, alternatives, recommendation, and verification.
- [ ] Deep handoff carries protected qualifying cohorts and unanswered questions.
- [ ] V6.1 API/web types and first-wave interactions are implemented with truthful fallbacks.
- [ ] Accessibility, privacy, resume, follow-up, and analytics tests pass.
- [ ] Calibration/evaluation builders and validators exist and work with fixtures/synthetic data.
- [ ] Release/rollback flags and fail-closed configuration are tested.
- [ ] Active architecture, evidence, QA, operations, and generated documentation are current.
- [ ] Documentation CI validates V6.1 registries, projections, versions, links, and catalogs.
- [ ] The Figma documentation-agent brief exists and reflects the implemented state.
- [ ] Focused and repository-wide feasible checks pass; unrun external gates are listed honestly.
- [ ] No unrelated user changes were discarded.

### 11.2 Automated calibration Definition of Done — State B

- [ ] Corpus compatibility/completeness passes the canonical contract.
- [ ] Training/holdout separation is reproducible and leak-free.
- [ ] V6.1 baseline, prior, distance, threshold, and semantic artifacts are generated from training only.
- [ ] Frozen artifact bytes/checksums are recorded before holdout evaluation.
- [ ] Synthetic interval coverage and family/branch FDR gates pass.
- [ ] Holdout evaluation runs through the exact production V6.1 pipeline.
- [ ] V6.1 versus V6.0 stability, abstention, precision, latency, and output-shape comparisons are recorded.
- [ ] Experimental era/lifecycle/loop gates are reported separately and remain disabled if they fail.
- [ ] Aggregate evaluation and release manifests contain no private identifiers.
- [ ] API and worker load identical approved candidate bytes.

### 11.3 Public-release Definition of Done — State C

- [ ] State B is complete.
- [ ] Independent statistical review is approved.
- [ ] Dota supported-and-believable precision is at least 90%.
- [ ] Copy/overclaim review reports zero blocking forbidden claims.
- [ ] Accessibility and product-comprehension review pass.
- [ ] Production smoke verifies exact cost/request behavior and artifact checksums.
- [ ] Monitoring and stage-specific stop conditions are live and privacy-safe.
- [ ] Rollback is rehearsed without deleting stored reports.
- [ ] An operator explicitly authorizes rollout.
- [ ] Only outcomes whose individual gates pass are public-enabled.
- [ ] Experimental flags remain off unless separately approved with their own evidence.

### 11.4 Figma-handoff Definition of Done — State D

- [ ] `docs/design/free-dna-v6.1-figma-documentation-update-agent-brief.md` exists.
- [ ] It names authoritative implemented sources and exact versions.
- [ ] It maps API fields/outcomes to components, states, fallbacks, accessibility, and tests.
- [ ] It lists the target Figma file/pages/nodes or identifies their absence as required input.
- [ ] It distinguishes public first-wave behavior from shadow-only experiments.
- [ ] It contains a Definition of Done for the future Figma agent.
- [ ] It is linked from the relevant docs index and Sol's final handoff.

## 12. Stop conditions and escalation

Sol must stop the affected track and report evidence when:

- OpenDota cannot provide the required complete 365-day history in one physical request;
- the existing corpus lacks a required canonical field/completeness property and new collection would be needed;
- V6.1 cannot coexist with immutable V6.0 storage/rendering without a migration decision;
- held-out or synthetic evidence shows estimator coverage/FDR/stability regression that cannot be fixed without changing product scope;
- a proposed semantic outcome needs causal, role, intent, patch, rank, or unobserved-game claims;
- an experimental era/loop/lifecycle path misses its false-positive or robustness gate;
- public enablement, deployment, private-data movement, new network collection, or external Figma mutation requires authorization not granted here;
- the target Figma file/key/pages cannot be discovered. The brief should record the missing input; it should not guess.

These conditions block only the affected outcome/phase when safe isolation exists. They do not justify weakening invariants or withholding completed unrelated documentation.

## 13. Final implementation principle

V6.1 succeeds when the player sees fewer, better-supported truths—not when the system computes the most features or fills every story slot.

Keep the seven gauges. Improve the sensors. Publish relationships only when their opportunity, uncertainty, error control, stability, copy, and product-usefulness gates all agree.
