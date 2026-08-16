# Free DNA QA report (v1 baseline)

This document records the earlier v1 QA baseline and its historical waivers.
The current finding-led v2 implementation and acceptance matrix are in
[`free-dna-finding-led-qa.md`](free-dna-finding-led-qa.md).

Audited commit: `0249ed7a759bb28b5fd99a46a97075a02661b117` (`revise pass 1`); remediation is in the current working tree and is not committed.

Overall status: **SHIP WITH EXPLICIT WAIVERS** for the automated Free-DNA beta gate; complete the operational and manual checks below before public production launch.

P0 open: **0**  
P1 open: **0**  
P2 waivers: **4**  
P3 hygiene items: **2**

Automated suites: **green**  
Browser matrix: **45/45 passed** across Chromium, Firefox, WebKit, iPhone 13, and reduced-motion Chromium  
Accessibility: automated keyboard/focus/reduced-motion checks green; assistive-technology and real-device checks waived  
Deep Scan regression: **green** (`make test-integration`, 4 passed)  
Calibration status: **unverified**; synthetic fixtures validate behavior, not scientific calibration or production archetype distributions

## Environment

- Darwin 25.5.0 arm64
- Node v26.5.0; pnpm 11.19.0
- Python 3.11.15 through uv 0.12.1
- Next.js 14.2.35; Playwright 1.62.1

## Frozen decisions

The four ambiguous v1 decisions are recorded in [`docs/decisions/free-dna-v1.md`](../decisions/free-dna-v1.md):

- Orientation: `0` Facilitator, `0.5` neutral, `1` Finisher.
- Share renderer: deterministic `share-svg-1.1.0`.
- Completed reports enter at `report-reveal`; pre-report states remain in the complete 23-state payload but are not replayed.
- `lane_role` is the only summary role hint; spatial `lane` alone never creates a role.

## Verification matrix

| Check | Result |
|---|---|
| `make test` | 62 passed, 2 skipped; one existing Starlette/httpx deprecation warning |
| `make test-contract` | 4 passed; one existing Starlette/httpx deprecation warning |
| `make test-integration` | 4 passed |
| `make lint` | Passed; two existing Next raw-image optimization warnings |
| `make typecheck` | Passed; mypy and TypeScript clean |
| `make taxonomy-validate` | Passed; 127 heroes, factual/editorial manifests accounted for |
| `make api-client` + generated diff check | Passed; no generated client drift |
| Direct Next production build | Passed; two non-blocking raw-image warnings |
| Playwright | 45 passed across all declared projects |
| Live OpenDota smoke | Not run; requires an opt-in API key |

## Defect ledger

### Fixed P0/P1 defects

| ID | Severity | Area | Observed behavior | Fix and regression evidence | Status |
|---|---|---|---|---|---|
| QA-FREE-001 | P0 | privacy/API | Identifier-shaped profile names and profile-host avatar URLs could cross the public report/share boundary. | Sanitize public identity and restrict avatars to trusted HTTPS CDN hosts; `test_public_free_report_sanitizes_identifier_shaped_identity_fields`. | Fixed |
| QA-FREE-002 | P0 | analytical integrity | Breadth coverage used a tautological valid-count ratio; missing-performance rows could create false outcome transitions. | Correct valid-row coverage and reset transitions across missing/short/corrupt rows; `test_missing_performance_rows_do_not_create_resilience_transitions`. | Fixed |
| QA-FREE-003 | P1 | analytical integrity | Adaptability dropped usable hero/outcome evidence whenever timestamps were absent. | Stable match-ID fallback with explicit limited methodology; `test_adaptability_keeps_hero_outcome_evidence_when_timestamps_are_missing`. | Fixed |
| QA-FREE-004 | P1 | archetype | A prototype could win without all declared evidence groups contributing. | Enforce required groups before ranking; `test_archetype_prototypes_require_their_declared_evidence_groups`. | Fixed |
| QA-FREE-005 | P1 | share/UI | The report exposed only the Final card even though the contract/rendering layer supported DNA, Heroes, and Final cards. | Added accessible card selector, card-aware preview/download names, and card-aware analytics; browser report suite covers all three. | Fixed |
| QA-FREE-006 | P1 | QA/build | Frontend type narrowing, Playwright reduced-motion configuration, and report-story hook dependencies were not clean at baseline. | Narrowed report variants, corrected context options, stabilized page-index callback; `make typecheck`, `make lint`, and 45 browser tests pass. | Fixed |

### Open P2 waivers

| ID | Owner | User/operational impact | Mitigation | Review condition |
|---|---|---|---|---|
| QA-WAIVER-001 | Release engineering | Live upstream rate limits/retries are not verified in this local run. | Live smoke is opt-in and CI does not require credentials; run `make test-live-smoke` with a controlled key. | Before public production |
| QA-WAIVER-002 | Platform engineering | Multi-replica PostgreSQL/Redis/Celery behavior is not exercised locally. | Persistent repository/worker seams and retention loop are present; run a deployment rehearsal. | Before public production |
| QA-WAIVER-003 | Product QA | VoiceOver/NVDA, touch gestures, zoom, and real-device safe-area behavior are not manually certified. | Automated keyboard dialog, focus restoration, reduced motion, mobile viewport, and overflow paths pass. | Before broad beta |
| QA-WAIVER-004 | Analytics/data science | Synthetic fixtures do not establish calibration, archetype frequency, or distribution sanity. | Production copy stays evidence-limited; run the calibration/distribution harness when an approved sample is available. | Before claims of calibrated distributions |

### P3 hygiene

- Next lint warns on two intentionally controlled plain-image elements used for generated SVG and allowlisted hero assets; this is non-blocking optimization polish.
- Playwright/Node emit dependency deprecation warnings during the fixture-backed browser run; no test or build failed.

## Deep Scan and preservation checks

The existing Deep Scan unit/contract/integration paths remain green. The Free regression explicitly monkeypatches the Deep pattern detector and rejects any detail-match call, proving that the Free boundary does not accidentally disable the separate Deep product or invoke it while building Free DNA.

## Remaining manual procedures

1. Run VoiceOver or NVDA through the report reveal, all dimension methodology dialogs, share selector, and error boundaries at 200% zoom.
2. Run the live smoke with a non-production key and record request count, latency, retry, and `Retry-After` behavior.
3. Run a production-like PostgreSQL/Redis/Celery rehearsal with two API instances and one worker, including restart and retention expiry.
4. Review all three SVG cards using production taxonomy assets and the actual native-share/download targets.

## Final recommendation

The repository is safer and more regression-resistant than the audited baseline, and the Free cost/privacy/schema invariants are automated. Ship the current changes to an automated beta/staging gate with the four waivers above; do not call the system fully production-ready until the manual accessibility, live-provider, multi-process, and calibration procedures are recorded.
