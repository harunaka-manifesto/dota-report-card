# V7 Backend Bugfix Report

## Executive Summary

- Confirmed bugs fixed: 11 of 11 (`BUG-001` through `BUG-011`).
- Remaining confirmed bugs: none found by the audited synthetic reproductions.
- Probable bugs: `PROB-001` and `PROB-002` confirmed and fixed.
- Owner decisions required: define a canonical owner credential before any private V7 read endpoint is exposed.
- FE integration recommendation: **YES WITH CAVEATS**. The allowlisted public projection is safe for real-player reads. Private Recommendation/provenance reads remain intentionally unavailable.

The pass changed evidence eligibility, validation, failure isolation, access control, copy, and packaging. It did not change frozen analytical methodology or artifacts. STRATZ calls: 0. OpenDota calls: 0. Protected split access: none.

## Commits

| Task | Bug IDs | Commit | Changed files | Sol review |
|---|---|---|---|---|
| Privacy route boundary | BUG-001 | `7f50d77` | `routes.py`; V7 capability/runtime-service tests | Accepted; both V7 read routes return only the typed public projection. |
| Effective Recommendation support | BUG-005 | `c541096` | `runtime.py`, `report_contract.py`; focused tests | Accepted; eligibility only, no inference change. |
| Missing and unknown evidence | BUG-002, BUG-003 | `79271b1` | Six V7 research modules; seven focused test files | Accepted after scope reduction; unavailable evidence is omitted and observed empty evidence remains distinct. |
| Failure isolation | BUG-004, BUG-011 | `f18e088` | Context projection, runtime, two table modules; five test files | Accepted; only `UnsupportedContextLevel` is recoverable and artifact failures remain fatal. |
| SQL reuse parity | BUG-006 | `fff6a1e` | SQL repository; SQLite lifecycle regression | Accepted; no retention-policy change. |
| Persistence and event coverage | BUG-009, BUG-010 | `8374493` | Assembly, payload, descriptive/report contracts, runtime; focused tests | Accepted; additive compatibility field and stricter persisted validation. |
| Favorable public fallback | BUG-008 | `e843699` | Public projection; focused tests | Accepted; unsafe Finding fallback removed until explicit polarity policy exists. |
| Canonical semantic copy | BUG-007 | `89257ff` | Runtime/content generator/catalog; registry initially changed; focused test | Accepted only with follow-up correction below. |
| Package assets | PROB-001 | `cbe9185` | `pyproject.toml`; isolated package smoke script | Accepted; wheel and sdist verified outside checkout. |
| Nullable transport hardening test | BUG-004 | `338a437` | STRATZ client test | Accepted as a failing regression that reopened BUG-004. |
| Nullable duration follow-up | BUG-004 | `9cc1daa` | Pass-2 observation validity gate | Accepted; closes normalized provider-to-runtime crash. |
| Frozen registry correction | BUG-007 | `2b78531` | Registry restore; runtime copy override | Accepted; restores the frozen candidate-registry digest without reverting corrected public copy. |
| Recommendation action polarity | PROB-002 | `ed84e5e` | Recommendation policy helper, runtime eligibility, focused tests | Accepted after owner decision; eligibility only, with ranking and instructions unchanged. |

Two Wave 5 workers hit the usage limit after leaving useful work. Sol reviewed the committed BUG-008 change and completed/committed the bounded BUG-007 work. No worker commit was squashed.

## Bug Closure

### BUG-001 — Unauthenticated private V7 reads

- Original failure: both `/v1/v7/reports/{report_id}` and generic `/v1/reports/{report_id}` returned complete private V7 payloads without authorization.
- Root cause: both routes loaded the persisted document directly; frontend omission and UUID obscurity were the only barriers.
- Implementation: both V7 paths validate the stored private payload and return only its typed, allowlisted `public_projection`. Generic non-V7 behavior is unchanged. Arbitrary bearer headers do not elevate access because no canonical owner credential exists.
- Regression: route tests cover both endpoints and assert Recommendation, provenance, adverse/loss-run material, rank, identifiers, and report ID are absent.
- Reproduction after fix: both unauthenticated routes return HTTP 200 public projections with no private fields.
- Status: **FIXED**. Private owner reads remain intentionally unavailable pending a separate authentication decision.

### BUG-002 — Unavailable evidence became zero

- Original failure: null wards, farm components, tower evidence, kill arrays, and own event streams created zero observations or fabricated shares.
- Root cause: falsey defaults collapsed explicit null and observed empty collections.
- Implementation: shared feature/table gates preserve unavailable (`None`), observed empty, and observed zero as distinct states; only dependent observations are omitted.
- Regression: provider-normalized null transport tests plus vision, lane/jungle, fight conversion, kill-grid, Recommendation, and Archetype tests.
- Reproduction after fix: null ward/farm/tower/event streams produce no dependent observation; observed empty streams retain their documented empty/zero behavior.
- Status: **FIXED**.

### BUG-003 — Unknown outcome, side, and hero gained meaning

- Original failure: unknown result became loss, unknown side became Dire, and unknown hero participated in hero transitions and warmups.
- Root cause: truthiness and string conversion at feature/context boundaries.
- Implementation: nullable identity is retained in chronology but explicitly gated from result-, side-, and hero-dependent observations.
- Regression: history retention, Pass-1/Pass-2 context, post-loss, hero-switch, novelty, comfort-pool, and session tests.
- Reproduction after fix: unknown values remain unknown and produce no affected observation or transition.
- Status: **FIXED**.

### BUG-004 — Nullable normalized evidence crashed the report

- Original failure: null duration, null lead slots, and missing death timestamps raised untyped errors from accepted provider shapes.
- Root cause: derived table/context functions performed arithmetic before evidence validation.
- Implementation: nullable duration/trajectory/event inputs return unavailable at the narrow table or Pass-2 context boundary. A later normalized-provider regression found and closed one remaining `duration_bucket` path.
- Regression: direct table cases, `analyze_v7` isolation, and provider normalization through the full runtime.
- Reproduction after fix: all three original rows, plus normalized `durationSeconds=None`, produce a readable report while refusing affected analytical paths.
- Status: **FIXED**.

### BUG-005 — Recommendation effective support below minimum

- Original failure: 56 raw wins/24 raw losses emitted advice even though block-paired inference retained only 8 wins/24 losses.
- Root cause: the 15-per-arm gate ran before homogeneous-block exclusion, and persisted validation allowed counts of 1.
- Implementation: runtime rechecks `n_control`/`n_treated` after the unchanged inference call; persisted `Recommendation` requires the canonical `MIN_PER_ARM` for both arms.
- Regression: original 80-row sequence and persisted 14/15/15 boundary cases.
- Reproduction after fix: effective 8/24 support is refused; 15/15 validates and 14 in either arm fails.
- Status: **FIXED**.

### BUG-006 — SQL reused jobs without reports

- Original failure: a completed SQL job whose report was deleted or expired returned `reused=True` and a dead report ID.
- Root cause: SQL reuse lacked the in-memory repository's report-readability check.
- Implementation: SQL reuse verifies the referenced report whenever `report_id` exists; missing/expired reports return no reusable job.
- Regression: real SQLite-backed lifecycle tests for deletion and expiry.
- Reproduction after fix: both cases start a replacement job with `reused=False`.
- Status: **FIXED**.

### BUG-007 — Player questions overstated metric semantics

- Original failure: copy claimed map area, teammate distance, build completion, and queue-click latency.
- Root cause: stale canonical/display strings were broader than the approved estimands.
- Implementation: runtime and generated content now say observer-ward active time, deaths during minutes without team kill activity, eighth purchase progress, and time until the next recorded game. Frozen research-registry strings were restored after the full suite detected a digest change; presentation/runtime overrides carry the corrected copy.
- Regression: generated-catalog consistency and exact semantic-string tests; frozen registry digest tests.
- Reproduction after fix: public/runtime copy uses only measured semantics and the frozen registry digest still matches.
- Status: **FIXED**.

### BUG-008 — Topical section treated as favorable polarity

- Original failure: a negative `vision_coverage` Finding was labeled `favorable_finding` because its section was `what_is_good`.
- Root cause: public selection treated topical section membership as valence.
- Implementation: no Finding receives the favorable fallback until an explicit metric-level polarity policy exists; hero/activity/window fallback remains.
- Regression: negative, zero, and positive directions all fall through safely; historical `favorable_finding` payload shape remains readable.
- Reproduction after fix: the adverse vision Finding selects the safe descriptive fallback.
- Status: **FIXED**.

### BUG-009 — Event-detail count described parsed flags

- Original failure: one parsed history row and zero deep rows reported `matches_with_event_detail=1`.
- Root cause: assembly had only the history parsed count, not accepted deep evidence count.
- Implementation: new reports carry optional `acquired_event_detail_match_count` and use it for metadata. Historical reports lacking it keep their legacy parsed-count interpretation.
- Regression: zero/one accepted deep rows and historical field absence.
- Reproduction after fix: parsed=1/deep=0 reports event detail 0; deep=1 reports 1.
- Status: **FIXED**.

### BUG-010 — Persisted validation accepted incoherent analytics

- Original failure: support of 1, direction opposite the gap, and infinite interval bounds validated.
- Root cause: weak support fields, no Recommendation direction invariant, and an incomplete finiteness scan.
- Implementation: minimum effective support, direction/gap consistency, and recursive finite-number validation at typed persistence boundaries.
- Regression: persisted reload, JSON round trip, both interval bounds, both arm minima, and direction mismatch.
- Reproduction after fix: every corrupt mutation is rejected; valid payloads round-trip.
- Status: **FIXED**.

### BUG-011 — Unsupported context aborted unrelated capabilities

- Original failure: one `NEW_PATCH` observation raised `ContextProjectionError` and aborted the report.
- Root cause: unsupported player level and invalid artifact shared one exception type and no per-dimension refusal boundary existed.
- Implementation: `UnsupportedContextLevel` subclasses the fatal artifact error but is caught only around player residual projection for the affected dimension.
- Regression: direct unsupported level, full readable report, and fatal artifact-load/schema/digest/binding coverage.
- Reproduction after fix: affected dimension is refused; unrelated descriptive output continues; artifact errors still raise.
- Status: **FIXED**.

## Probable Bugs

### PROB-001 — Installed package assets

- Investigation result: **confirmed**. Baseline wheel/sdist omitted `app/stratz/item_vocabulary.json` and hero taxonomy JSON; installed loaders and V7 service construction failed.
- Action: added explicit package-data entries for `app.stratz` and `app.heroes`, plus a disposable wheel/sdist install smoke script.
- Result: both distributions load 573 items and 127 heroes and construct the service outside the checkout.
- Remaining decision: none.

### PROB-002 — Opposite gap with fixed instruction

- Investigation result: reproduced with 20 wins/60 losses of effective support. Losses warded 300 seconds earlier than wins, producing gap `-300`, direction `negative`, reliability `1.0`, yet the instruction remained “Place your first ward before the horn.”
- Owner decision: refuse sign-inconsistent Recommendations because experiment framing would require clearer product copy.
- Action: added an eligibility predicate using the existing per-dimension `higher_is_worse` policy. Positive loss-minus-win gaps are eligible only when higher is worse; negative gaps are eligible only when higher is better; zero and non-finite gaps are refused. Absolute-gap ranking, scales, fitted gaps, and canonical instructions remain unchanged.
- Result: the reproduced `-300` first-ward gap is refused; the sign-consistent `+300` case remains eligible.
- Remaining decision: none for Recommendation polarity.

## Analytical Safety

Accepted changes altered evidence validity and eligibility only. They did not alter the analytical estimator or frozen lineage.

| Invariant | Changed? |
|---|---|
| Context coefficients | NO |
| Population μ/τ | NO |
| Frozen dependence parameters | NO |
| Recommendation scale | NO |
| Recommendation ranking | NO |
| Archetype cut | NO |
| Finding estimand | NO |
| Block geometry | NO |
| Cohort fitting | NO |
| Artifact lineage | NO |

No population/context JSON, frozen artifact, calibration output, holdout output, or release binding changed. The first full-suite run caught a candidate-registry digest drift from copy editing; commit `2b78531` restored the frozen registry, and the final full suite passed.

## Privacy Review

- `/v1/v7/reports/{report_id}` returns only the typed allowlisted public projection.
- Generic `/v1/reports/{report_id}` applies the same boundary to V7 payloads while preserving legacy non-V7 behavior.
- Recommendation, provenance, loss-run/adverse private history, rank display, account/match/session identifiers, and report ID do not appear in either V7 response.
- Random/unknown bearer tokens cannot unlock private fields.
- A private owner endpoint was not invented because no canonical owner credential exists.

## Runtime Failure Isolation

Incomplete player evidence is represented as unavailable and omitted at the dependent feature/table/context boundary. Unsupported player context raises the typed `UnsupportedContextLevel` and refuses only the affected dimension. Malformed or incompatible frozen artifacts continue to raise the broader fatal `ContextProjectionError`; schema, digest, population binding, and compatibility checks were not weakened.

## Persistence / API Review

- SQL completed-job reuse now requires a readable, unexpired report, matching in-memory semantics.
- Persisted Recommendations require 15 effective observations per arm and direction consistent with the stored gap.
- All analytical numeric values, including interval bounds, must be finite.
- New reports distinguish accepted deep event evidence from provider parsed flags through optional `acquired_event_detail_match_count`; historical payloads retain legacy interpretation when the field is absent.

## QA

All commands were run offline from `v7/backend-bugfix-pass-1`.

| Check | Command | Result |
|---|---|---|
| Full repository | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider` | **1397 passed, 3 skipped**, 2 deprecation warnings, 169.86s |
| V7/provider suite | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q -p no:cacheprovider tests/unit/test_v7_*.py tests/unit/test_stratz_client.py tests/unit/test_stratz_normalize.py tests/unit/test_stratz_item_vocabulary.py` | **608 passed**, 1 warning |
| Original trigger rerun | Explicit 30-node pytest selection covering BUG-001..011 | **30 passed**, 1 warning |
| Ruff | `.venv/bin/ruff check --no-cache services/api tests scripts/smoke_test_v7_package.py scripts/v7_build_content_catalog.py` | PASS |
| Mypy | `.venv/bin/mypy --cache-dir=/dev/null` | PASS, 252 source files |
| Docs | `.venv/bin/python scripts/check_docs.py` | PASS |
| Content catalog | `.venv/bin/python scripts/v7_build_content_catalog.py --check` | PASS |
| Build/install | `.venv/bin/python scripts/smoke_test_v7_package.py` | wheel PASS; sdist PASS; 573 items; 127 heroes; service construction PASS |
| Diff whitespace | `git diff --check` | PASS |

An exploratory Ruff command that included every file under `scripts/` found two issues in the pre-existing untracked user file `scripts/stratz_v7_pass1_recollect.py`. That file is outside the branch diff and was preserved untouched; the canonical tracked scope above passes.

### Reproduction Closure Table

| Bug | Before | After | Status |
|---|---|---|---|
| BUG-001 | Both unauthenticated routes returned private payload | Both return allowlisted public projection only | FIXED |
| BUG-002 | Missing evidence emitted zero/share observations | Missing evidence omitted; observed empty remains distinct | FIXED |
| BUG-003 | Unknown result/side/hero became loss/Dire/hero identity | Unknown remains unknown; dependent observations omitted | FIXED |
| BUG-004 | Nullable provider evidence crashed report | Affected paths unavailable; report remains readable | FIXED |
| BUG-005 | Raw 56/24 emitted with effective 8/24 | Effective 8/24 refused; persisted minimum enforced | FIXED |
| BUG-006 | Deleted/expired SQL report reused | Replacement job starts | FIXED |
| BUG-007 | Copy claimed map/distance/build/queue semantics | Copy names measured proxy/landmark/gap | FIXED |
| BUG-008 | Negative topical Finding labeled favorable | Falls through to safe descriptive card | FIXED |
| BUG-009 | Parsed=1/deep=0 reported event detail 1 | Reports event detail 0 | FIXED |
| BUG-010 | Low support, wrong direction, infinities accepted | Typed persisted read rejects all | FIXED |
| BUG-011 | `NEW_PATCH` aborted report | Affected dimension refused; artifact failures fatal | FIXED |

## Remaining Risks

- Private Recommendation/provenance retrieval has no owner-authenticated endpoint. This is an intentional privacy-safe limitation, not authorization by obscurity.
- Two deprecation warnings remain: Starlette's current TestClient/httpx integration and Alembic's legacy `prepend_sys_path` parsing.

## FE Readiness

- FE real-player integration safe: YES WITH CAVEATS
- analytical recalibration required: NO
- provider recollection required: NO
- protected split access required: NO

The safe integration surface is the allowlisted public projection. Private Recommendation/provenance integration waits for owner authentication.
