# V7 Backend Bug Sweep

## Executive Summary

**11 confirmed bugs: 1 CRITICAL, 6 HIGH, 4 MEDIUM, 0 LOW. Two probable bugs.**

The highest-risk area is the boundary between the private persisted capability payload and unauthenticated report reads. Both read routes return private Recommendation and analytical provenance when supplied a report ID. The public projection itself excludes those fields, but the HTTP routes do not enforce that boundary.

The analytical runtime also accepts incomplete provider evidence in ways that either manufacture observations or crash an entire report. A concrete Recommendation reproduction passed the initial 15-per-arm check but emitted only **8 supporting wins** after block selection. SQL completed-job reuse can return a deleted/expired report indefinitely.

**A bugfix pass is recommended before FE integration starts.** Existing offline checks passed, but their clean inputs do not exercise the failures below. This is a read-only audit, not a certification of production or frozen statistical validity.

## Scope and Environment

- Task type: BACKEND / ANALYTICAL audit; DOCUMENTATION output only.
- Repository: `/Users/nikanakamanifesto/Documents/GitHub/dota-report-card`.
- Branch: `main`.
- Expected and observed SHA: `cfc49bf35ebf49dbe72ae1bc189ad352363d8e46`.
- Sweep began September 8 and continued September 9, 2026, Asia/Jakarta. Requested filename retained.
- `docs/v7/` does not exist. This report uses `docs/evidence/`, the existing home of V7 audit and QA documents.
- Existing untracked `V7 Master Experience Plan v1.md` and `scripts/stratz_v7_pass1_recollect.py` were left untouched.
- STRATZ calls: **0**. OpenDota calls: **0**. Protected split data access: **NONE**.
- No source/test edits, commits, pushes, deployments, artifact regeneration, cohort fitting, recalibration, or holdout runs.
- Offline synthetic values and committed sanitized test helpers were used. No real player payload was opened.
- Existing test selection: **366 passed, 14 deselected**; Ruff PASS; Mypy PASS; docs check PASS. Details below.

Inspected modules include `player_analysis_v7/{service,runtime,assembly,lifecycle,acquisition_policy,context_projection,population,capability_payload,report_contract,display_semantics,public_projection,descriptive}.py`; research `features`, `tables`, `pass2_tables`, `pass2_features`, `pass2_observations`, `registry`, `inference`, `ranking`, `recommendation`, and `archetype`; `providers/{base,__init__}.py`; STRATZ `client`, `models`, `normalize`, `deep`, `item_vocabulary`, and provider adapter; API routes, app setup, repository read/write/reuse/retention paths; package configuration, Docker packaging, and taxonomy data loading. Relevant V7 tests, the handoff, capability specification, provider contract, mathematical contract, and Finding/Archetype producer paths were cross-checked. Inspection was targeted by runtime reachability, not a claim that every repository line was read.

Completion accounting: BASE SHA and NEW SHA are identical; only this Markdown file was created. BACKEND FILES CHANGED: NO. ANALYTICAL FILES CHANGED: NO. PUBLIC REPORT CONTRACT CHANGED: NO. PERSISTED REPORT COMPATIBILITY TESTED: YES, synthetic V7 in-memory round trips and typed reads only. PRODUCTION-SHAPED FIXTURE: NOT APPLICABLE to this read-only sweep; none inspected. BROWSER E2E: NOT APPLICABLE. TYPECHECK: PASS. LINT: PASS. BUILD: NOT APPLICABLE; fresh package build not performed. ANALYTICAL BEHAVIOR CHANGED: NO. HOLDOUT RERUN: NO. RECALIBRATION: NO. OPENDOTA QA CALLS: 0. DEPLOYED: NO. SAFE TO MERGE: NO release recommendation; no implementation commit exists.

## Runtime Map

| Step | Concrete runtime path |
|---|---|
| Input | `V7RuntimeService.generate(account_id, canonical_player)`; `StratzClient._positive_id` validates provider-facing IDs. No V7 public generation route exists yet; handoff explicitly defers it. |
| Wiring | `main.create_app` → `providers.build_v7_provider` → `StratzProvider`; service attached as `app.state.v7_runtime_service`. Legacy analysis/worker wiring remains separate. |
| Reuse/coalescing | `V7ReportLifecycle.locate_or_start` → repository `find_compatible_completed` / `get_or_create_inflight_job`; analytical identity hashes `runtime_versions()`. |
| History | `StratzProvider.fetch_history` → `StratzClient.get_player_history` / `get_player_history_page`; bounded pagination, typed native models, deduplication. |
| History normalization | `normalize_stratz_history` → `V7CanonicalHistory` / `V7CanonicalMatch`; native enum strings and nullable values retained. |
| Deep acquisition/cache | Service filters parsed product-context history IDs; `acquisition_policy.plan` selects up to 500, eight per request. Reads/writes account-keyed `DEEP_CACHE_ENDPOINT`; provider `fetch_deep_matches` → `get_deep_matches` → `normalize_deep_matches`. |
| Runtime evidence | `analyze_v7` → `history_rows`, product-context deep/history join, `chronological`, duplicate-deep-ID rejection, `parsed_rows`, `PlayerFrame`. |
| Frozen context | `load_context_projection` validates packaged JSON; `assert_population_compatible` checks population schema, lineage, projection digest, compatibility ID. `_estimate` applies per-Finding residualization. |
| Findings | `_finding_rows` calls Pass-2 `OBSERVATION_REGISTRY` or Pass-1 `extract`; `inference.player_inference`; population parameters keyed by Finding; `rank_player` → `select_stratified` → `apply_score_gate` → `_public_finding`. |
| Recommendation | `_recommendation` → seven `eligible_dimensions` → supported win/loss opportunities → denominator gate → frozen context/scale/dependence → inference → priority/select → private `Recommendation`. |
| Archetype | `_archetype` → `archetype.measure` → dominant-stratum frozen cuts → `assign`; all axes required; Lighthouse precedes Closer; otherwise 18-cell grid. |
| Capability | `assemble_v7_capability` derives descriptive facts, builds display semantics/public projection, stamps provenance, and validates `V7CapabilityPayload`. |
| Persistence | `V7ReportLifecycle.complete` → repository `save_report` (JSON plus retention metadata) → `complete_job`. No V7-specific SQL serializer drops analytical fields. |
| Reload/API | Lifecycle `load` or `GET /v1/v7/reports/{report_id}` removes repository envelope fields then validates V2. Generic `GET /v1/reports/{report_id}` returns saved JSON directly. |
| Public/private | `build_public_projection` constructs a small typed allowlist. Private payload retains Recommendation, loss-run facts, rank and provenance. HTTP authorization gap: BUG-001. |

### Individual Finding audit

Every shipping key resolves its own context projection and population fit; no swapped key binding was found. The common final inference geometry is 20 target blocks / 8 valid blocks / 4 opportunities per block, as explicitly frozen in the mathematical contract. It must not be replaced with the separate research `block_config` merely because the constants differ.

| Finding | Actual feature source and audit result |
|---|---|
| `vision_coverage` | Pass-2 observations → own observer uptime; ever-warded gate. Missing wards become zero (BUG-002); emitted map-area question overstates it (BUG-007). |
| `duration_tempo` | `features.duration_tempo`: log duration, context includes result. Missing result becomes loss (BUG-003). Log-unit conversion is correctly withheld without baseline. |
| `death_clustering` | Pass-2 consecutive death-gap indicators, <=90 seconds. Missing event times are skipped here but can crash the sibling deaths-alone path (BUG-004). Unit is death gaps, not distinct matches. |
| `lane_vs_jungle_share` | Pass-2 jungle gold / total creep gold. Missing component becomes zero (BUG-002), contradicting both-components-available contract. |
| `purchase_tempo` | Pass-1 parsed join: eighth timed purchase / duration. Implementation uses purchase ordinal correctly; build-completion question does not (BUG-007). |
| `deaths_alone_share` | Pass-2 death-minute/fight-activity proxy. Zero deaths correctly refuse; missing grid/time can abort report (BUG-004). Distance wording is unsupported (BUG-007). |
| `spike_usage` | First qualifying real-item purchase to next kill/assist, mean seconds in runtime. No purchase/follow-up yields no opportunity. Item-vocabulary packaging risk PROB-001. |
| `position_flexibility` | Consecutive parsed matches within session-gap threshold; both positions must be nonempty. Intermediate unparsed matches are omitted by design in current mathematical contract. |
| `fight_timing_centroid` | Parsed kill/assist normalized progress with >=3 timed events. Missing one event stream can leave a biased partial stream; see concrete missing-data risk below. |
| `hero_novelty` | 30-match warm-up, hero unseen for 30 days. Missing hero ID can act like an ordinary repeated hero (BUG-003). |
| `closer_vs_comeback` | Win indicator for crossing +10k / -10k team lead, potentially both arms per match. Correct player-side orientation for known side; nullable trajectory failure BUG-004. |
| `post_loss_session_continuation` | In-session continuation; last observed match omitted as right-censored. Missing outcome becomes loss (BUG-003). |
| `lead_retention` | Midpoint decided-ahead/behind win-indicator contrast, not literal lead-survival probability. Null outcomes/trajectories affected by BUG-003/004. |
| `post_loss_hero_switch` | Adjacent in-session hero inequality after loss vs win. Unknown outcomes/heroes are not gated (BUG-003). |
| `post_loss_requeue_latency` | Log gap from previous end to next start, minimum one second. Queue-click timing is not observed; existing player question still invokes queueing. Log conversion guard is correct. |
| `fight_conversion` | Won-fight minute followed by enemy tower in minute +1/+2; team association, not personal causality. Missing towers/kill slots can manufacture observations (BUG-002). |

For contrast Findings, the runtime and schema consistently derive `own_contrast_direction` from the shrunk contrast estimate and keep it separate from population `direction`. This does not authorize describing residuals as raw win rates. No new Finding was added or recalculated against a cohort during this audit.

## Confirmed Bugs

### BUG-001 — Unauthenticated reads expose private V7 payloads

- Severity: **CRITICAL**.
- Confidence: High; reproduced through both HTTP routes offline.
- Area: Privacy / API.
- File(s): `services/api/app/api/routes.py:907`, `:920`; `player_analysis_v7/capability_payload.py`.
- Function/class: `get_report`, `get_v7_report`.
- Trigger: Anyone possessing a valid V7 report ID calls either read endpoint without Authorization.
- Expected: Private Recommendation, adverse/private history and provenance require an owner/private read boundary; public reads use the approved projection.
- Actual: Both routes return the complete document, including Recommendation and provenance, with HTTP 200. Neither checks ownership or a private-read credential. `noindex` is not authorization.
- Impact: A report identifier disclosed in a link, client state, or logs grants access to fields expressly excluded from public/share output. UUID unpredictability limits discovery but does not separate public from private access. No claim is made that IDs are enumerable or that deployed V7 reports were accessed.
- Evidence: Synthetic persisted complete payload; unauthenticated TestClient GETs to both routes printed `200`, `private recommendation=True`, `provenance=True`. Generic read also bypasses V7 validation.
- Reproduction: Build `payload()` from `tests/unit/test_v7_capability_payload.py` via `runpy`, persist with `V7ReportLifecycle`/`InMemoryRepository`, use fixture `MappingSource` in `create_app`, then GET `/v1/v7/reports/{id}` and `/v1/reports/{id}` without headers.
- Suggested fix direction: Establish distinct authorized private and allowlisted public reads; close the generic-route bypass as well. Preserve the public projection's field allowlist. Do not treat frontend omission as access control.

### BUG-002 — Unavailable deep evidence becomes measured zero or a fabricated share

- Severity: **HIGH**.
- Confidence: High; several direct synthetic reproductions.
- Area: Finding / Recommendation / Archetype input correctness.
- File(s): `player_analysis_v7/research/pass2_features.py:515`, `pass2_tables.py:337`, `:451`, `pass2_observations.py` (`fight_conversion`), `archetype.py:164`; `stratz/deep.py`.
- Function/class: `_observer_ward_events`, `_match_vision_coverage`, `lane_vs_jungle_gold`, `fight_minutes`, `_enemy_tower_fell_soon_after`, `_fight_style_inputs`.
- Trigger: Nullable provider arrays, component totals, or own-event streams; the deep normalizer preserves these nulls.
- Expected: Missing evidence is unavailable; empty-but-observed evidence may support zero. Missing components must not satisfy evidence denominators.
- Actual: Missing wards produce coverage 0.0; absent lane gold with jungle gold 100 produces jungle share 1.0; missing tower events produce non-conversions; missing own kill/assist/death streams produce zero participation/death axes. Short/null kill arrays can be treated as zero kills.
- Impact: Artificial observations alter context-adjusted Findings, personal gaps, support counts, and identity axes. These are not merely UI omissions.
- Evidence: At duration 1200, a warded row plus `wards=None` emitted vision observations `[0.2857142857142857, 0.0]`. `recommendation.vision_coverage` returned `0.0` for null wards. Missing lane component emitted `[1.0]`. A 21-slot won-fight grid with `tower_deaths=None` emitted 21 zeros. Twenty rows with all own event streams null returned fight-style axes `(0.0, 0.0)`.
- Reproduction: Use `_deep_row()` from `test_v7_runtime_service.py`; set duration 1200 and match trajectories to 21 slots. Mutate the named field to null and call the named observation/axis functions. For vision's player gate include one other row with observer event `{'time': 0, 'type': 0}`.
- Suggested fix direction: Validate evidence completeness at the shared canonical/feature boundary, preserving the distinction between null and an observed empty list. Gate every dependent metric and its denominator on the fields it actually needs. Do not change frozen thresholds or coefficients to conceal this.

### BUG-003 — Unknown outcomes, side and hero IDs acquire analytical meaning

- Severity: **HIGH**.
- Confidence: High; reproduced extraction behavior on valid nullable canonical inputs.
- Area: History normalization / Findings / session modifier.
- File(s): `player_analysis_v7/runtime.py:78`; `research/features.py:169`, `:252`, `:558` and post-loss/hero extractors; `research/archetype.py:201`.
- Function/class: `history_rows`, `base_ctx`, `duration_tempo`, post-loss extractors, `hero_novelty`, `session_dispersion`.
- Trigger: A product-context canonical match has `won=None`, `side=None`, or `hero_id=None`.
- Expected: Unknown values remain unknown and exclude the affected observation/axis; they must not become losses, Dire, or a known hero.
- Actual: `history_rows` only filters absent timestamp/duration. Truthiness maps unknown result to `L`/`loss`/0, unknown side to `D`, and hero equality/history bookkeeping accepts `None` as a hero value.
- Impact: Incorrect contextual adjustment, post-loss arm allocation, hero-switch/novelty observations and session dispersion.
- Evidence: With nullable outcome and side, extraction returned context `result='L'`, `side='D'`, and post-loss continuation arm `loss`. The source provider-neutral dataclass explicitly allows both fields to be null.
- Reproduction: `dataclasses.replace(_history().matches[0], won=None, side=None)`; pass a history containing that row through `runtime.history_rows`; construct a `PlayerFrame`; inspect `duration_tempo`, `base_ctx`, and a two-row continuation series. For hero switching, compare an unknown hero with a known hero.
- Suggested fix direction: Add explicit per-observation validity gates before boolean coercion or hero comparisons. Preserve chronology gaps so omission does not invent a known transition.

### BUG-004 — Nullable normalized deep values crash the whole report

- Severity: **HIGH**.
- Confidence: High; reproduced through `analyze_v7`.
- Area: Deep normalization / failure isolation.
- File(s): `stratz/deep.py` (`_int`, `_series`); `research/tables.py:60`, `:77`; `research/pass2_tables.py:317`, `:366`; `runtime.py:341`.
- Function/class: `normalize_deep_matches`, `minute_grid_length`, `player_networth_lead`, `team_lead_curve`, `deaths_alone_share`, `analyze_v7`.
- Trigger: Joined product-context deep row has null duration with a trajectory, a null element in net-worth lead, or a death event with missing time.
- Expected: Typed invalid-evidence handling or omission/refusal of affected capabilities; no untyped arithmetic error from a shape the normalizer accepts.
- Actual: Null duration raises `TypeError: unsupported operand type(s) for /: 'NoneType' and 'int'`; null Radiant lead values raise comparison TypeError, while Dire negation can fail sooner. Missing death time raises ValueError. Runtime does not isolate these failures; service marks the entire job failed and rethrows.
- Impact: One incomplete parsed match prevents otherwise usable history/descriptive/analytical output.
- Evidence: `analyze_v7(history=_history(), deep_rows=[modified_row], ...)` produced the two TypeErrors above without provider access. The normalizer explicitly allows null integers and null series elements.
- Reproduction: Start with `_deep_row()`, use 21 lead slots, then independently set `duration_seconds=None` or `radiant_networth_leads=[None]*21`; keep match ID and product-context enums valid. Invoke `analyze_v7`.
- Suggested fix direction: Define required fields for each derived series and reject/omit invalid evidence before arithmetic. Keep artifact incompatibility fatal; distinguish it from a single incomplete provider row.

### BUG-005 — Recommendation passes 15-per-arm gate but uses only eight wins

- Severity: **HIGH**.
- Confidence: High; full `_recommendation` reproduction with real frozen parameters.
- Area: Recommendation evidence threshold.
- File(s): `player_analysis_v7/runtime.py:248`; `research/inference.py:288`; `report_contract.py:281`.
- Function/class: `_recommendation`, `has_denominator`, `player_inference`, `Recommendation`.
- Trigger: At least 15 raw wins/losses exist, but homogeneous chronological blocks are dropped from paired inference.
- Expected: The actual supporting observations must meet the stated minimum per arm before emitting advice.
- Actual: Denominator check occurs before block exclusion. No post-inference gate checks `n_control/n_treated`. Output schema only requires sample counts >=1.
- Impact: An apparently fully reliable recommendation can be emitted below its contractual minimum support.
- Evidence: 80 rows with outcomes `[win,loss,loss,loss]*8 + [win]*48`, first observer time 0 in wins and 300 in losses, patch 180 and valid contexts, produced `first_ward_time`, `sample_wins=8`, `sample_losses=24`, `reliability=1.0`, gap 300.
- Reproduction: Feed the above chronological rows to `runtime._recommendation(rows, load_population_parameters())`. Raw totals are 56 wins/24 losses; only eight mixed blocks survive.
- Suggested fix direction: Recheck effective arm support after inference and enforce it at the persisted contract boundary. Keep excluded blocks out of the counts; do not relabel raw observations as supporting the fitted contrast.

### BUG-006 — SQL reuse returns completed jobs whose reports no longer exist

- Severity: **HIGH**.
- Confidence: High; static production-path evidence plus isolated SQL-method reproduction.
- Area: Persistence / retention / reuse.
- File(s): `storage/repository.py:969`, `:1311`, `:1325`; `player_analysis_v7/lifecycle.py:29`.
- Function/class: `SqlAlchemyRepository.find_compatible_completed`, `purge_expired`, `V7ReportLifecycle.locate_or_start`.
- Trigger: Report expires or is purged while its completed analysis job remains.
- Expected: A compatible completed result is reusable only if the report is still readable.
- Actual: SQL method selects the completed job and returns it without checking its report, unless optional hash/fingerprint parameters happen to request a read. V7 passes neither. The in-memory implementation has an explicit existence check that SQL lacks.
- Impact: Subsequent generation returns `reused=True` and a report ID that resolves to 404, without starting replacement work. Retention makes this reachable in normal operation.
- Evidence: A fake SQL session returning a completed record, with `get_report` returning None, yielded `reused=True` and no report-existence checks. SQL purge removes reports but not the completed jobs selected here.
- Reproduction: Instantiate the SQL repository without its constructor, inject a context-manager session whose `scalar` returns a record, map that record to a completed synthetic job, and make `get_report` return None. Call the lifecycle. No database/provider needed; this exercises the actual SQL repository method.
- Suggested fix direction: Match the in-memory existence/expiry gate in SQL and add a real retention/reuse integration regression. Also define report freshness separately from retention.

### BUG-007 — Shipped questions contradict approved metric semantics

- Severity: **HIGH**.
- Confidence: High; exact runtime strings reproduced.
- Area: Finding contract / future frontend copy.
- File(s): `player_analysis_v7/runtime.py:59`, `_public_finding`; `research/registry.py:826`; `public_projection.py:51`.
- Function/class: `PASS2_PLAYER_QUESTIONS`, `_public_finding`, `build_public_projection`.
- Trigger: These Findings are selected and their explicitly player-facing question is displayed or shared.
- Expected: Own observer uptime, a team-kill-activity proxy, and eighth-purchase progress are described without claiming map area, physical teammate distance, or build completion.
- Actual: Runtime emits `How much of the map your wards keep lit`, `Dying away from your team`, and `How far into a game are you when your build comes together?`.
- Impact: A frontend following the contract can make materially unsupported claims. Correct separate display semantics do not repair contradictory player-facing strings; the public Finding copies the question directly.
- Evidence: `_public_finding(rank_player([synthetic_dimension])[0])` reproduced all three strings. The handoff explicitly forbids these interpretations.
- Reproduction: Use a valid `PlayerDimension` for each key with its frozen `mu/tau/section`, rank it, and call `_public_finding`; no cohort access required.
- Suggested fix direction: Correct the canonical questions and cover their runtime/public consumers. Keep the eighth-purchase feature and frozen analytics unchanged. Also clarify the post-loss match-gap question so it does not imply observed queue-click timing.

### BUG-008 — Topical section is mistaken for favorable direction in public selection

- Severity: **MEDIUM**.
- Confidence: High; reproduced deterministic projection.
- Area: Public share selection.
- File(s): `player_analysis_v7/public_projection.py:51`; `scripts/v7_finding_pipeline.py:113`.
- Function/class: `build_public_projection`.
- Trigger: No Archetype exists and a `what_is_good` Finding has an unfavorable direction, such as below-population vision coverage.
- Expected: Only an actually favorable Finding earns `selected_kind='favorable_finding'`; otherwise fall through to a safe hero/activity/window card.
- Actual: Selection checks section membership but never favorable polarity. The producer explicitly documents sections as topical, not verdicts.
- Impact: Share output can highlight a weakness as a strength, contrary to the handoff's favorable-only fallback.
- Evidence: A `vision_coverage` Finding with z=-3, direction negative, reliability .9 produced `selected_kind='favorable_finding'` with direction negative.
- Reproduction: Call `build_public_projection` with that valid Finding, existing fixture facts/semantics, and `archetype=None`.
- Suggested fix direction: Use an approved per-metric favorable-direction policy; for ambiguous/two-sided traits omit this fallback instead of guessing. Do not infer valence from the section name.

### BUG-009 — Event-detail count reports parsed flags rather than acquired evidence

- Severity: **MEDIUM**.
- Confidence: High; reproduced via `analyze_v7`.
- Area: Capability metadata / acquisition completeness.
- File(s): `player_analysis_v7/assembly.py:110`; `descriptive.py:146`; `service.py:66`; `capability_payload.py:461`.
- Function/class: `assemble_v7_capability`, `derive_descriptive_facts`, `analyze_v7`.
- Trigger: History marks matches parsed, but deep acquisition returns fewer rows, none, or is limited to 500.
- Expected: `matches_with_event_detail` describes event evidence available to this report; provider parsed flags have their own distinct meaning.
- Actual: Count equals all eligible history `is_parsed` flags. Assembly receives no acquired-deep count. Validation enforces equality with the parsed-flag count rather than actual evidence.
- Impact: FE can report analysis coverage that did not occur, including counts above the 500-match depth limit.
- Evidence: One parsed history match and `deep_rows=[]` produced `matches_with_event_detail=1`, with no deep evidence at all.
- Reproduction: `analyze_v7(history=_history(), deep_rows=[], hero_metadata={}, generated_at='2026-09-08T00:00:00Z')` using the committed runtime-service test helper.
- Suggested fix direction: Carry actual accepted deep acquisition/support counts to assembly, separately from provider history coverage. Update validation and compatibility additively; do not relabel older persisted counts silently.

### BUG-010 — Persisted validation accepts invalid Recommendation support/direction and infinite intervals

- Severity: **MEDIUM**.
- Confidence: High; reproduced model validation.
- Area: Persistence/API corruption boundary.
- File(s): `player_analysis_v7/report_contract.py:174`, `:262`, `:281`; `capability_payload.py:307`, `:427`.
- Function/class: `PointEstimateWithInterval`, `Recommendation`, `V7CapabilityPayload.validate_payload`.
- Trigger: Persisted JSON has a canonical Recommendation with one supporting win or contradictory direction, or a Finding interval containing infinity.
- Expected: Typed read rejects incoherent evidence counts/direction and every non-finite analytical number.
- Actual: A payload mutated to `sample_wins=1` and direction opposite its positive gap passes. A finite estimate point with interval `[-inf,+inf]` also passes; the finite scan does not inspect interval bounds. JSON-mode serialization can turn infinities into null or fail in stricter response serialization.
- Impact: The advertised fail-closed read boundary can return incoherent analytics or a non-round-trippable response. BUG-005 demonstrates that below-minimum support is not limited to hypothetical external corruption.
- Evidence: `V7CapabilityPayload.model_validate(document).validate_payload()` accepted both mutations of the complete test payload.
- Reproduction: Load `payload()` from `test_v7_capability_payload.py`, dump it, mutate the fields above, then validate. Infinity is an in-memory corruption probe, not a claim that strict JSON text represents infinity portably.
- Suggested fix direction: Validate effective minimums, direction/gap consistency, and finiteness for all numeric analytical fields. Add persisted read/serialization tests rather than only constructor happy paths.

### BUG-011 — One unsupported context level aborts unrelated capabilities

- Severity: **MEDIUM**.
- Confidence: High; direct exception reproduction plus uncaught runtime call chain.
- Area: Frozen projection / partial refusal.
- File(s): `player_analysis_v7/context_projection.py:87`; `runtime.py:133`, `:164`, `:341`; `service.py:124`.
- Function/class: `FactorProjection.coefficient_for`, `_estimate`, `_finding_rows`, `analyze_v7`.
- Trigger: A player opportunity contains a patch/hero/context level absent from the frozen vocabulary with refusal policy.
- Expected: Per the mathematical contract, an unseen level refuses the affected dimension. Artifact incompatibility still fails the runtime closed.
- Actual: `_estimate` projects all opportunities before evidence eligibility, and the unsupported-level exception escapes the whole runtime. No affected-dimension refusal is assembled.
- Impact: Even one low-support/new-context opportunity can prevent descriptive output and unrelated supported capabilities. New provider enums/patches make this a real integration boundary, not a suggested zero-effect fallback.
- Evidence: `_estimate('vision_coverage', [one_opportunity_with_patch_NEW_PATCH], ...)` raises `ContextProjectionError`; no caller isolates it. The error occurs even though one observation cannot qualify for inference.
- Reproduction: Construct a context from each factor's first fitted vocabulary level, replace `patch` with `NEW_PATCH`, and invoke `_estimate` with one finite observation.
- Suggested fix direction: Distinguish unsupported player context from corrupt/incompatible artifacts. Refuse the affected capability/dimension according to a reviewed policy without inventing coefficients; retain fatal artifact validation.

## Probable Bugs

### PROB-001 — Installed package may omit required STRATZ vocabulary and hero taxonomy

- Severity: **MEDIUM**; a standalone installed runtime can fail, but current Docker source-path behavior mitigates it.
- Confidence: Medium; packaging configuration traced, fresh wheel/sdist not built.
- Area: Packaging/runtime portability.
- File(s): `pyproject.toml`; `stratz/item_vocabulary.py:91`; `heroes/taxonomy.py:27`; `research/pass2_features.py:147`; `infra/docker/api.Dockerfile`.
- Function/class: `load_item_vocabulary`, `load_default_taxonomy`, `V7RuntimeService.__init__`.
- Trigger: Import/run V7 from a wheel or sdist install without the source checkout on PYTHONPATH.
- Expected: Every required runtime JSON asset is installed, not just population/context JSON.
- Actual: Explicit package-data configuration includes only `app.player_analysis_v7: data/*.json`. No MANIFEST.in was found. The item vocabulary and taxonomy loaders require sibling JSON files. Docker copies all source and sets PYTHONPATH to it, hiding a possible package omission.
- Impact: FileNotFoundError at service construction or item-feature extraction in a clean installed environment.
- Evidence: Config/load paths inspected. A read-only setuptools file-selection probe failed because setuptools is not installed in the local venv; no wheel was created.
- Reproduction: In a separately authorized disposable build environment, build/install wheel and sdist outside the checkout, unset source PYTHONPATH, and call the two loaders plus empty-data runtime. This was not executed during the sweep.
- Suggested fix direction: Include required data explicitly and add isolated package smoke coverage. Do not claim the current source-import tests verify wheel contents.
- Why probable: Actual package manifests/install behavior were not observed; tooling or generated metadata could affect inclusion.

### PROB-002 — Opposite personal gap still receives the same directional instruction

- Severity: **MEDIUM**.
- Confidence: Medium; code path certain, desired policy requires product/analytical adjudication.
- Area: Recommendation interpretation.
- File(s): `research/recommendation.py` (`higher_is_worse`, `priority`, `select`); `runtime.py:248`.
- Function/class: `RecommendationDimension`, `_recommendation`.
- Trigger: Largest supported gap has the opposite sign from the behavior the canonical instruction seeks to change.
- Expected: Advice should not imply that the observed own win/loss association supports the opposite intervention.
- Actual: Priority uses absolute gap; `higher_is_worse` is not used to choose/refuse/reverse the fixed instruction. For example, warding earlier in losses can still select “Place your first ward before the horn.”
- Impact: A personal-gap explanation can contradict its accompanying advice even though the payload reports the numeric direction correctly.
- Evidence: Static selection path and canonical instruction registry. The model explicitly specifies absolute-gap ranking, so this is not asserted to be a runtime deviation from the frozen algorithm.
- Reproduction: Reverse the win/loss ward times in BUG-005's series; use enough mixed blocks to retain >=15 per arm and inspect direction versus unchanged instruction.
- Suggested fix direction: Decide whether the product must refuse opposite-sign advice or frame it as an unproven experiment. Do not silently change the frozen ranking algorithm in a generic bugfix.
- Why probable: Fixed associational experimentation may be an intentional product policy; the current runtime/contract does not settle the contradiction.

## Test Gaps / Risks

1. **Transport-to-feature malformed evidence coverage:** existing runtime tests mainly project artificial opportunities or use one clean deep row. Add provider-normalized null/partial cases that reach the entire runtime, including missing side/result, partial kill/assist streams, unknown hero, null duration, null trajectory slots, missing farm components and missing wards/towers. Partial assist data can bias the centroid even when enough kill events remain; define completeness semantics before testing omission.
2. **SQL parity and retention:** the successful persistence tests use `InMemoryRepository`. Exercise SQL expiry/deletion/reuse and failed `save_report`/`complete_job` transactions. Report save and job completion are separate operations; failure after save may leave an orphan report.
3. **Acquisition retry durability:** `V7RuntimeService.generate` persists accumulated deep rows only after every batch succeeds. A late batch failure loses earlier successfully acquired batches from repository persistence; a retry may repeat acquisition. Deep service cache is account-keyed and ignores its stored operation-version metadata when reusing rows. Test partial failures and version changes before relying on “fetch once”. No live requests were made to establish transport-cache mitigation.
4. **Retention versus acquisition policy:** both repositories purge raw payloads on report retention, while acquisition policy declares stored matches never stale. Resolve retention/privacy requirements deliberately; do not simply retain private raw data forever. No changed retention policy is recommended without that decision.
5. **Freshness:** V7 lifecycle passes no `max_age_seconds`; compatible reports are reused without checking for new matches while retained. Define the intended refresh window before exposing generation. SQL expired reuse is separately confirmed as BUG-006.
6. **Artifact structural validation:** tested digest/schema/binding failures reject. Population parsing validates Finding numeric fits but not equivalent numeric ranges/ordering for every Recommendation scale or Archetype cut. A validly digested but semantically invalid artifact needs adversarial checks; self-digest alone proves consistency, not a correct fit. No actual shipped coefficient defect or cross-lineage mixing was found.
7. **Source/version compatibility:** runtime verifies the projection/population pair, but source/model version strings are mostly provenance rather than enforced code-version compatibility. Test a correctly digested bundle with incompatible estimator/feature identity, not only an altered digest. Avoid changing frozen data merely to make this test pass.
8. **Refusal specificity:** null Recommendation always becomes `insufficient_wins_or_losses_per_arm`, even when adequate raw arms exist but paired blocks cannot support inference. Missing session dispersion becomes `insufficient_event_support` for Archetype despite the declared `insufficient_sessions` code. Private/unavailable provider errors fail the job rather than producing the declared capability refusal codes. Document the error-versus-refusal interface before FE uses retry copy.
9. **Truncated history:** descriptive facts correctly retain provider completeness; runtime constructs `PlayerFrame(completeness='complete')` unconditionally. Current shipping extractors do not read this flag, so no extra confirmed output bug is claimed. Missing rows can nevertheless distort adjacency and novelty; propagate known gaps/completeness instead of promising full-history behavior.
10. **Corruption/public snapshot tests:** validation rebuilds a public projection against current builder/registry code during reload. Future editorial changes could reject an otherwise valid old saved projection; version the compatibility behavior and preserve old fixtures. Non-V2 rejection is currently intentional, not a discovered regression.
11. **Finding support documentation:** mathematical-contract tables mention registry minimums while the frozen final pipeline uses common blocked inference defaults without an additional registry gate. This audit did not substitute discovery-screen thresholds for the final producer. Resolve the prose ambiguity in tests/docs rather than silently changing estimator eligibility.
12. **Public semantic policy:** explicit adversarial privacy tests need to cover both HTTP routes, negative-direction fallback and conflicting semantic strings, not only absence of forbidden keys in `public_projection`.

## Non-Issues Investigated

- Runtime does not fit context/population parameters per request. All 16 keys resolve their own frozen projection and population record.
- Missing/corrupt context JSON, wrong schema, changed digest and cross-bound projection hash fail closed. No raw-value fallback after an incompatible artifact was found.
- The separate historical population 1.0.0 file is not selected by the current default loader.
- 20/8/4 final inference geometry is intentionally frozen; different research design constants are not a bug by themselves.
- Recommendation registry excludes both contaminated dimensions (`fight_conversion`, `death_clustering`) and selects only seven canonical candidates. Canonical instruction/verification text is checked in capability validation. BUG-005 concerns effective support, not removal of these exclusions.
- For valid known side, team lead orientation is correctly flipped for Dire. Contrast direction is separate from population z direction.
- Archetype assignment requires all measured axes and a real dominant stratum, with no default label. Grid contains 18 combinations; Lighthouse wins precedence and a Special replaces the label. No public rarity field was found.
- Special metrics are pooled over a player's deep rows and compared with cuts grouped by dominant stratum in both producer and runtime. Filtering only the runtime special inputs to a stratum would break current fit parity; this was not reported as a mismatch.
- Normalized history deduplicates deterministically; runtime rejects duplicate deep IDs. Ordering for history/deep evidence and ranking tie breaks is deterministic.
- Explicit anonymous/missing profiles and unknown accounts are rejected by the STRATZ client; malformed response shapes and provider failures have typed provider exceptions. No live availability was inferred.
- Deep normalizer rejects unrequested/duplicate match IDs, wrong player-count shape and malformed array/object types. Accepted nullable contents remain the problem in BUG-002/004.
- Descriptive hero metadata omission does not make provider calls; truncated descriptive coverage retains “recorded” semantics and does not claim complete coverage.
- The typed public projection contains no Recommendation, private provenance, raw account/match IDs, loss-run object or rarity. BUG-001 is a route boundary failure, not a hidden field in that projection.
- V7 JSON save/load preserves analytical fields through the synthetic round trip; typed read rejects a non-V7 schema. Missing optional capabilities with matching refusals are covered by passing tests.
- Broad service exception handling marks failure and rethrows; it does not convert arbitrary artifact/runtime exceptions into a successful normal-looking report.
- Reviewed runtime asserts in descriptive loss-run handling follow prior checks; they were not identified as independent reachable validation bypasses. No TODO/FIXME/NotImplemented stub on the central V7 generation path was found.

## QA Results

### Existing offline tests

Exact invocation (no changes to tests; file-writing fixture tests deselected to honor the one-file restriction):

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python - <<'PYTEST'
import pytest, socket
from pathlib import Path
class Guard:
    def pytest_collection_modifyitems(self, config, items):
        skip=[i for i in items if set(i.fixturenames)&{'tmp_path','tmpdir','tmp_path_factory'}]
        items[:]=[i for i in items if i not in skip]
        config.hook.pytest_deselected(items=skip)
socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('offline sweep: network disabled'))
files=['runtime','runtime_service','capability_payload','report_contract','provider_architecture','context_projection','population_parameters','descriptive','rank_fence','content_catalog','research_features','research_pass2_features','research_pass2_observations','research_pass2_tables','research_archetype','research_recommendation','research_ranking']
args=['-q','-p','no:cacheprovider']+[f'tests/unit/test_v7_{f}.py' for f in files]+['tests/unit/test_stratz_client.py','tests/unit/test_stratz_normalize.py','tests/unit/test_stratz_item_vocabulary.py']
raise SystemExit(pytest.main(args,plugins=[Guard()]))
PYTEST
```

Result: **366 passed, 14 deselected, 1 warning in 1.16s**. Warning: Starlette deprecates its current httpx TestClient integration. No failed test was suppressed or edited. Deselection prevents temporary-file fixtures, not failing assertions. Corpus-reader tests that intentionally open synthetic protected-split inputs were not included. No real protected split was read.

Coverage includes all-Finding projection checks, Recommendation/Archetype logic, provider architecture, synthetic STRATZ transport, artifact compatibility, V7 capability validation and in-memory persistence/API compatibility. This is not the previously reported full 1,343-test run and does not claim live PostgreSQL coverage.

### Static QA

```sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check --no-cache services/api tests
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy --cache-dir=/dev/null
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/check_docs.py
```

- Ruff: **All checks passed!**
- Mypy: **Success: no issues found in 252 source files**.
- Docs: **docs-check: ok**. The existing checker does not fully audit V7 handoff/runtime semantic agreement; BUG-007 remains despite this pass.
- Source import: exercised by tests and synthetic runtime/API probes; PASS for those paths.
- Wheel/sdist build/install: **NOT RUN**. Read-only setuptools file-selection probe failed with `ModuleNotFoundError: No module named 'setuptools'`. No dependency was installed and no build artifact created.
- Browser/live-provider QA: NOT RUN, outside scope.

### Synthetic reproduction commands and exact observations

All executed via `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=services/api:. .venv/bin/python - <<'PY'` with in-memory objects. Committed helpers were loaded using `runpy.run_path`, not by writing scratch files. Reproduction recipes appear per bug; this is the common setup and the central provider-edge probe:

```python
import runpy
from copy import deepcopy
from app.player_analysis_v7 import runtime
from app.player_analysis_v7.research import pass2_observations as obs
from app.player_analysis_v7.research import recommendation as rec, archetype
f = runpy.run_path('tests/unit/test_v7_runtime_service.py')
row = f['_deep_row']()
row.update(duration_seconds=1200, radiant_kills=[3]*21,
           dire_kills=[0]*21, radiant_networth_leads=[0]*21)
row['self']['events']['wards'] = None
assert rec.vision_coverage(row) == 0.0
warded = deepcopy(row)
warded['self']['events']['wards'] = [{'time': 0, 'type': 0}]
assert [o.value for o in obs.vision_coverage([warded, row])] == [6/21, 0.0]
row['self']['farm_distribution'] = {
    'creep_location': None, 'neutral_location': [{'gold': 100}]}
assert obs.lane_vs_jungle_share([row])[0].value == 1.0
row['tower_deaths'] = None
assert len(obs.fight_conversion([row])) == 21
assert {o.value for o in obs.fight_conversion([row])} == {0.0}
row['self']['events'] = dict(kill_events=None, assist_events=None, death_events=None)
assert archetype.fight_style_axes([row]*20) == (0.0, 0.0)
```

Recorded observations from the additional probes:

```text
null_duration TypeError unsupported operand type(s) for /: 'NoneType' and 'int'
null_lead TypeError '>' not supported between instances of 'NoneType' and 'NoneType'
unknown result/side: result='L'; side='D'; post-loss arms={'loss'}
zero acquired deep: matches_with_event_detail=1
Recommendation: first_ward_time; sample_wins=8; sample_losses=24; reliability=1.0; gap=300.0
/v1/v7/reports/: unauthenticated 200; recommendation=True; provenance=True
/v1/reports/: unauthenticated 200; recommendation=True; provenance=True
corrupt support/direction accepted: sample_wins=1
infinite interval accepted: interval_low=-inf; interval_high=inf
SQL deleted report reused: True; report existence checks=[]
adverse projection: selected_kind='favorable_finding'; direction='negative'
unseen single observation: ContextProjectionError unsupported level 'NEW_PATCH' for context factor 'patch'
projection bad digest/version: ContextProjectionError (expected)
cross-binding mismatch: ContextProjectionError (expected)
```

The first combined probe ended at an unsupported missing patch before its Recommendation example ran; rerunning that portion with valid frozen patch 180 produced the 8-win result. This is recorded to distinguish a probe-setup error from the confirmed denominator bug. No artifacts were written by the in-memory digest/binding checks.

Final repository audit commands:

```sh
git rev-parse HEAD
git diff --name-only cfc49bf35ebf49dbe72ae1bc189ad352363d8e46...HEAD
git diff --stat
git status --short
```

Expected SHA remained unchanged and tracked diffs remained empty. The only new deliverable is this uncommitted report; the two pre-existing untracked files remain.

## Recommended Bugfix Order

1. **Privacy/integrity:** BUG-001, both read routes. Do not expose V7 private payloads while relying on public-projection field tests alone.
2. **Wrong analytical behavior:** BUG-002, BUG-003 and BUG-005; preserve unknowns and effective support. Then BUG-007 and BUG-008 to prevent unsupported or adverse public claims.
3. **Runtime crashes:** BUG-004 and BUG-011; separate malformed player evidence from fatal artifact incompatibility.
4. **Persistence/API:** BUG-006, BUG-010, BUG-009; exercise actual SQL retention and typed serialization.
5. **Edge cases:** investigate PROB-001/002 and acquisition retry/cache/version/freshness risks. Do not silently alter retention or frozen Recommendation policy.
6. **Tests/docs:** add the concrete failing scenarios, retain historical payload fixtures, clarify refusal codes/support semantics, and repeat the offline checks. A green rerun alone does not resolve untested provider-null cases.

## Final Assessment

- FE integration safe now: **NO** for real-player integration; synthetic contract exploration can continue with these limitations explicit.
- Bugfix pass required before FE: **YES**.
- Analytical recalibration required: **NO** established by this sweep. Input validation, access control and contract repairs do not justify recalibration. If a proposed fix changes the frozen estimand or an audit later proves affected cohort inputs, obtain separate analytical-release authorization.
- Provider recollection required: **NO**.
- Protected split access required: **NO**.

No fix was implemented. The report separates confirmed runtime failures from policy/packaging questions so the fixing agent can act without repeating the safe paths already investigated.

V7_BACKEND_SWEEP_COMPLETE
