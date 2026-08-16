# Free DNA QA requirement traceability

This matrix turns the attached `dota-report-card-full-qa-implementation-plan.md` into repository evidence. Every row names the source-plan section, implementation path, automated evidence, and remaining manual procedure where one is required.

## Contract and data boundary

| Source plan section | Requirement | Implementation | Automated evidence | Manual/status |
|---|---|---|---|---|
| §6.1–6.2 | Free performs one bounded summary-history read (maximum 500) and zero detail/replay work. | `services/api/app/analysis/service.py`, `services/api/app/core/config.py` | `tests/unit/test_free_dna_contract.py::test_free_cache_miss_never_calls_match_details_or_deep_detection`; `tests/unit/test_qa_regressions.py::test_analysis_history_limit_uses_broad_summary_cap` | Pass |
| §6.1 | Free and Deep Scan are separate products. | `services/api/app/analysis/service.py`, `services/api/app/analysis/deep_scan.py` | Free call-boundary regression plus `tests/integration/test_deep_scan_selection.py` | Pass |
| §6.3 | 0–29 eligible rows fail; 30–59 is limited; 60+ is normal; all eight story slots remain represented. | `services/api/app/analysis/service.py`, `services/api/app/reports/dna_assembly.py` | `tests/unit/test_free_dna_contract.py::test_free_history_boundaries_are_29_fail_30_limited_and_60_normal` | Pass |
| §6.4 | Public output is exactly `free-dna-report-1.0.0` / `free_dna_report` and rejects extra fields. | `services/api/app/api/report_schemas.py`, `services/api/app/reports/dna_assembly.py` | `tests/unit/test_free_dna_contract.py::test_public_free_report_rejects_internal_and_legacy_fields` | Pass |
| §6.5 | Public output excludes account IDs, raw input, normalized rows, sessions, private analysis, and legacy/deep payloads. | `services/api/app/reports/dna_assembly.py`, `services/api/app/storage/repository.py` | Recursive privacy assertions in `tests/unit/test_free_dna_contract.py`; route contract in `tests/contract/test_api.py` | Pass |
| §6.6 | Report JSON and browser retrieval emit real noindex behavior. | `services/api/app/api/routes.py`, `apps/web/app/report/[reportId]/page.tsx` | `test_public_report_route_sets_noindex_and_returns_strict_free_contract`; Next metadata robots declaration | Pass |
| §6.7 | Completed reuse changes when data or any analytical/public version changes. | `services/api/app/analysis/service.py` | `tests/unit/test_qa_regressions.py::test_free_compatibility_fingerprint_changes_with_analytical_versions` | Pass |
| §6.5, §16 | Share identity is sanitized, avatar hosts are allowlisted, and all cards are privacy-safe. | `services/api/app/reports/dna_assembly.py`, `services/api/app/share/service.py` | Identity and three-card SVG assertions in `tests/unit/test_free_dna_contract.py` | Production asset review waived; staging procedure in QA report |

## Normalization, sessions, and feature contracts

| Source plan section | Requirement | Implementation | Automated evidence | Manual/status |
|---|---|---|---|---|
| §7.1–7.2 | Free uses one nullable canonical summary normalization contract with provenance. | `services/api/app/ingestion/summary_normalize.py` | `tests/unit/test_summary_normalize_contract.py` | Pass |
| §7.3 | Supported public All Pick contexts enter the common corpus; unsupported modes, pro/league, abandons, and short games are excluded/degraded by policy. | `services/api/app/ingestion/summary_normalize.py` | Eligibility contract tests and Free history boundary tests | Pass |
| §7.4 | Exact/conflicting duplicates resolve deterministically and retain conflict reasons. | `services/api/app/ingestion/summary_normalize.py` | Order-invariance assertions in `tests/unit/test_summary_analysis.py` | Pass |
| §7.5 | Missing fields remove rows only from dimensions that need them; spatial `lane` alone never creates a role. | `services/api/app/ingestion/summary_normalize.py`, `services/api/app/dna/features/extractor.py` | `tests/unit/test_summary_normalize_contract.py::test_lane_role_is_a_role_hint_but_spatial_lane_is_not_a_role`; missing-timestamp regression | Pass |
| §7.6 | Sessions use duration-aware 90-minute queue gaps, do not split at midnight, do not bridge undated rows, and isolate corrupt rows. | `services/api/app/dna/sessions.py` | `tests/unit/test_summary_analysis.py::test_session_gap_boundary_midnight_and_undated_rows_are_deterministic` | Pass |
| §7.7 | Resilience/Endurance/Rhythm use 60/90/120 sensitivity recomputation and retain sensitivity evidence. | `services/api/app/dna/features/extractor.py`, `services/api/app/dna/dimensions/common.py` | Session sensitivity is carried in `SessionResult` and scorer stability; integration suite exercises the Free pipeline | Pass |
| §7.8 | Scorer inputs expose evidence values, denominators, coverage, provenance/version, and confounders without sending raw rows to the UI. | `services/api/app/dna/features/models.py`, `services/api/app/reports/dna_assembly.py` | Strict public dimension schema and Free report contract | Pass |

## Eight dimensions, confidence, archetypes, and heroes

| Source plan section | Requirement | Implementation | Automated evidence | Manual/status |
|---|---|---|---|---|
| §8.1–8.9 | All eight scorers are bounded, deterministic, independently nullable, and do not gain confidence when evidence is removed. | `services/api/app/dna/dimensions/*.py`, `services/api/app/dna/dimensions/service.py` | Eight-dimension Free contract; missing-role/timestamp/performance fixtures | Pass; full extreme/neutral calibration matrix remains waived |
| §8.4 | Adaptability avoids outcome leakage, supports missing timestamps, and discloses fallback/confounding. | `services/api/app/dna/dimensions/adaptability.py` | `test_adaptability_keeps_hero_outcome_evidence_when_timestamps_are_missing` | Pass |
| §8.8 | Endurance is within-session slope evidence with late-sample and role-mix safeguards. | `services/api/app/dna/dimensions/endurance.py` | Endurance metadata and session sensitivity are emitted by the Free pipeline | Pass; production calibration waived |
| §9.1 | Confidence retains coverage/effective-sample/stability/quality weighting with hard caps. | `services/api/app/dna/confidence.py`, `services/api/app/dna/dimensions/common.py` | Dimension contract exposes confidence score/status and caps | Pass |
| §9.2 | Versioned archetypes use centered dimensions, missingness penalties, deterministic ties, and required groups. | `services/api/app/dna/archetypes/v1.json`, `services/api/app/dna/archetypes/classifier.py` | `test_archetype_prototypes_require_their_declared_evidence_groups` | Pass |
| §9.3 | Exactly three descriptors use group diversity and truthful neutral fallbacks. | `services/api/app/dna/archetypes/descriptors.py` | Strict archetype schema requires three unique descriptors | Pass |
| §10.1–10.2 | Hero IDs are stable factual IDs with checked-in factual/editorial manifests and provenance. | `services/api/app/heroes/taxonomy.py`, `research/heroes/`, `scripts/validate_hero_taxonomy.py` | `make taxonomy-validate`; `tests/unit/test_hero_taxonomy.py` | Pass |
| §10.3–10.7 | Signature/Comfort/Pattern/Recommendations degrade truthfully on taxonomy failure and healthy recommendation fixtures return three diverse results. | `services/api/app/heroes/identity.py`, `services/api/app/heroes/recommendations.py` | `tests/unit/test_hero_recommendations.py`; taxonomy failure fallback in identity path | Pass |

## Copy, API/jobs, UI, analytics, sharing, and operations

| Source plan section | Requirement | Implementation | Automated evidence | Manual/status |
|---|---|---|---|---|
| §11 | Copy is catalog-driven/versioned and avoids psychological, quality, causality, and guaranteed-outcome overclaims. | `services/api/app/content/catalog.py`, `services/api/app/content/renderer.py`, `services/api/app/content/free_dna/en.json` | `tests/unit/test_copy_catalog.py` | Pass |
| §12–13 | API failures are safe, progress has live SSE plus bounded visibility-aware polling fallback, and jobs are bounded/shutdown-aware. | `services/api/app/api/routes.py`, `services/api/app/analysis/service.py`, `apps/web/app/components/analysis-form.tsx` | Contract tests and home E2E failure/non-2xx/completion tests | Pass; production worker rehearsal waived |
| §14–15 | Retention/private evidence are separated from public reports; analytics are provider-neutral and identifier-free. | `services/api/app/storage/repository.py`, `apps/web/app/lib/analytics.ts` | Purge/privacy tests; forbidden analytics keys; report route privacy test | Pass; multi-process retention rehearsal waived |
| §16 | Completed report starts at the reveal; story overflow, keyboard methodology, reduced motion, and responsive layouts work. | `apps/web/app/report/[reportId]/dna/report-story.tsx`, `apps/web/app/components/story/primitives.tsx`, `apps/web/app/globals.css` | `apps/web/tests/e2e/report.spec.ts`; 45 browser runs | Pass; VoiceOver/NVDA and real-device checks waived |
| §16 | DNA, Heroes, and Final share cards have real privacy previews and card-aware downloads/analytics. | `apps/web/app/components/share/share-controls.tsx`, `services/api/app/share/service.py` | `apps/web/tests/e2e/report.spec.ts`; renderer cache key tests/inspection | Pass; production-target visual review waived |
| §17–18 | CI, observability, live-provider and production hardening are explicit rather than inferred from local unit tests. | `.github/workflows/qa.yml`, `services/api/app/core/metrics.py`, `services/api/app/workers/tasks.py` | CI workflow committed; local backend/web gates green | CI not hosted-run here; live/multi-replica checks waived |
| §20 | Deep Scan remains regression-safe after Free changes. | `services/api/app/analysis/deep_scan.py`, `services/api/app/analysis/service.py` | `make test-integration`; existing Deep Scan unit/contract tests | Pass |

## Explicitly unverified gates

- Assistive technology, real touch devices, safe-area/zoom, and visual screenshot review.
- Live OpenDota rate-limit/retry behavior and the opt-in live smoke.
- PostgreSQL/Redis/Celery multi-process restart, persistence, and retention rehearsal.
- Calibration/distribution sanity from an approved real-player sample. Synthetic fixtures are not scientific calibration evidence.
