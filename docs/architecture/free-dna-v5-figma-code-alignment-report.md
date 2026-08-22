# Free DNA v5 — Figma-to-Code Alignment Implementation Report

Date: 2026-08-22  
Scope: the attached `free-dna-v5-figma-code-alignment-implementation-plan.md`, treated as implementation instructions and acceptance criteria. Product semantics remain subordinate to the reviewed Figma model and the checked-in registries.

## A. Baseline

| Field | Before | After |
|---|---|---|
| Starting commit | `164dd74330fde3046f3635553d511d31236c4d08` (`pattern revamp`) | — |
| Ending commit | — | `164dd74330fde3046f3635553d511d31236c4d08` with the implementation in the working tree |
| Branch | `main` | `main` |
| Behavior model | `behavior-model-5.0.0` | `behavior-model-5.1.0` |
| Element registry | `free-elements-5.0.0` | `free-elements-5.1.0` |
| Pattern registry | `free-patterns-5.0.0` | `free-patterns-5.1.0` |
| Pattern actions | `pattern-actions-5.0.0` | `pattern-actions-5.1.0` |
| Context baseline | implicit/duplicated | `context-baseline-1.0.0` |
| Public report | `free-dna-report-5.0.0` / `free-story-5.0.0` | `free-dna-report-5.1.0` / `free-story-5.1.0` |
| Model/copy | `free-dna-model-5.0.0` / `free-dna-copy-5.0.0` | `free-dna-model-5.1.0` / `free-dna-copy-5.1.0` |

The final commit is unchanged because the implementation has not been committed by this task.

## B. Changed files and impact

| File(s) | Reason | Semantic impact | Public-contract impact |
|---|---|---|---|
| `services/api/app/behavior/context_baseline.py` | Add the shared leave-group-out resolver | Centralizes comparable-context identity, fallback order, minimum reference count, weighting, exclusion, and provenance | Adds versioned baseline provenance and fallback metadata |
| `services/api/app/behavior/elements/service.py` | Refactor Drift and Recovery baselines | E16 and E18 use the shared hierarchy; E18 authority is clustered by independent session | Adds Recovery evidence/raw metrics for transitions, sessions, coverage, and fallback levels |
| `services/api/app/behavior/patterns/service.py` | Make Pattern qualification explicit | Adds registry coverage gates, selected-clause evidence authority, deterministic OR tie-breaking, and distinct suppression reasons | Adds `qualification_element_keys` and optional `qualification_clause_index` |
| `services/api/app/behavior/patterns/registry.py` | Preserve historical identities and reviewed clauses | Reserves `session_hold`, `assist_presence`, and prior retired keys; keeps 11 canonical Patterns | Registry version becomes `free-patterns-5.1.0` |
| `services/api/app/behavior/models.py` and `behavior/__init__.py` | Add qualification and action evidence models | All actions expose a normalized evidence envelope without removing action-specific fields | Additive `evidence_summary`, observed-difference coverage, qualification metadata |
| `services/api/app/behavior/actions.py` | Align action evidence and diagnostics | P03 has explicit direct gates and evidence-literal death wording; baseline-dependent actions share context logic | All 11 action variants serialize `evidence_summary` |
| `services/api/app/behavior/elements/registry.py` | Version corrected Element methodology | Preserves exactly 18 Elements and shared zone semantics | Registry version becomes `free-elements-5.1.0` |
| `services/api/app/behavior/service.py`, `core/config.py`, `hero_portfolio/version.py` | Version and fingerprint methodology changes | New baseline, Pattern, Recovery, and action semantics cannot masquerade as v5.0 | Version metadata is carried in reports and reproducibility fields |
| `services/api/app/reports/dna_assembly.py`, `analysis/service.py` | Propagate versions and baseline provenance | Current reports identify the corrected methodology and fingerprint inputs | Report/story versions become 5.1; context baseline is serialized |
| `services/api/app/api/report_schemas.py` | Validate additive current fields and old reports | Current v5.1 payloads validate while v5.0 payloads remain readable | Adds evidence/qualification fields and accepts both v5.0 and v5.1 |
| `packages/api-client/src/index.ts`, `apps/web/app/report/[reportId]/page.tsx`, `apps/web/tests/e2e/fixture-server.mjs` | Propagate the API contract | Web consumers accept the corrected report version and additive fields | TypeScript remains backward-compatible for historical optional fields |
| `services/api/app/content/free_dna/en.json` | Correct Drift/Recovery methodology copy | Copy describes self-relative comparable baselines, not fatigue, tilt, or resilience | Copy version becomes `free-dna-copy-5.1.0` |
| `tests/unit/test_v4_conformance.py`, `test_behavior_catalog.py`, `test_context_baseline.py`, `test_recovery_scoring.py`, `test_pattern_actions.py`, `test_copy_catalog.py`, `test_free_dna_contract.py` | Characterization, regression, invariant, and contract coverage | Locks the eight audit fixes, all reviewed clauses, boundaries, history compatibility, and action envelope | No breaking test fixture changes; old v5.0 payload is still validated |
| `README.md`, `ARCHITECTURE.md`, `docs/architecture/*`, generated model catalog | Document corrected methodology | Documents 18 Elements, 11 Patterns, selected clauses, shared baselines, action abstention, and version history | Catalog and docs checks pass |

## C. Audit gaps

| Gap | Previous behavior | Implemented behavior | Test proving the fix |
|---|---|---|---|
| GAP-01 | Pattern qualification relied on Element status and let coverage only reduce strength | Every selected clause Element must be present, available, at its registry minimum coverage, and at least `.45` confidence; coverage and confidence failures remain distinct | `tests/unit/test_v4_conformance.py` coverage boundary, zero-gate, and reason tests |
| GAP-02 | P06/P07 could include the unused Familiarity/Tempo branch in confidence, coverage, quality, strength, or blockers | `QualificationDecision` selects one clause; only selected keys are authoritative; ties use min confidence, mean confidence, min coverage, component sum, then registry order | P06/P07 OR matrix and unused-branch tests in `tests/unit/test_v4_conformance.py` |
| GAP-03 | Historical Pattern reservations omitted published identities | `RETIRED_PATTERN_KEYS` explicitly reserves `session_hold`, `assist_presence`, and prior identities, with no active-key collision | `test_retired_pattern_keys_are_reserved` and catalog invariants |
| GAP-04 | Element and action paths duplicated inconsistent context-baseline logic | One resolver implements hero+role+function → hero+function → function → role → overall, leave-group-out filtering, minimum 3 references, weighting, and provenance | `tests/unit/test_context_baseline.py` hierarchy, leakage, insufficient-cell, taxonomy/role, and weighted-median tests |
| GAP-05 | E18 counted independent sessions but weighted transition residuals directly | E18 still requires 30 transitions, 3 sessions, and 50% context coverage, but computes one within-session estimate and one recency weight per session | `tests/unit/test_recovery_scoring.py` proves duplicated transitions do not get linear authority and gates remain enforced |
| GAP-06 | Action payloads exposed heterogeneous evidence and abstention semantics | Every action carries `PatternActionEvidence` with status, sample, effective sample, coverage, confidence, independent groups, evidence keys, limitations, and provenance | `test_every_reviewed_action_exposes_the_common_evidence_envelope` plus report contract round-trips |
| GAP-07 | P03 direct diagnostics lacked an explicit confidence/coverage gate and used unsupported survivability wording | Named sample `.10`, confidence `.50`, and coverage `.50` gates are applied to the direct branch; branch precedence is direct → hypothesis → unresolved; death exposure is named literally | P03 direct gate, boundary, branch precedence, and wording tests in `tests/unit/test_pattern_actions.py` |
| GAP-08 | Drift/Recovery copy described results without the reviewed personal-baseline context | Public copy now names comparable personal baselines and same-session post-loss performance; guardrails reject fatigue, tilt, resilience, and similar unsupported interpretations | `tests/unit/test_copy_catalog.py` |

## D. Verified Pattern qualification clauses

The following table is checked against `PATTERN_REGISTRY` and the canonical Element zone labels by registry invariant tests. The selected clause is recorded on each qualified result.

| Pattern | Reviewed qualifying clause(s) |
|---|---|
| P01 Same Playbook | Breadth ∈ {Varied, Wide} AND Toolkit ∈ {Compact, Focused} |
| P02 Comfort Edge | Breadth ∈ {Varied, Wide} AND Transfer ∈ {Slips, Falls off} |
| P03 Partial Transfer | Presence ∈ {Holds, Unchanged} AND Transfer ∈ {Slips, Falls off} |
| P04 Versatile Core | Breadth ∈ {Focused, Selective} AND Toolkit ∈ {Versatile, Diverse} |
| P05 Proven Flexibility | Breadth ∈ {Varied, Wide} AND Transfer ∈ {Travels, Carries over} |
| P06 Bounceback | Recovery ∈ {Recovers, Surges} AND (Familiarity ≠ Unchanged OR Tempo ≠ Same) |
| P07 Performance Slide | Recovery ∈ {Drops, Slips} AND (Familiarity ≠ Unchanged OR Tempo ≠ Same) |
| P08 Controlled Presence | Involvement ∈ {Active, Everywhere} AND Deaths ∈ {Elusive, Safe} |
| P09 Presence Tax | Involvement ∈ {Active, Everywhere} AND Deaths ∈ {Exposed, Frequent} |
| P10 Session Fade | Duration ∈ {Long, Marathon} AND Drift ∈ {Drops, Fades} |
| P11 Session Rise | Duration ∈ {Medium, Long, Marathon} AND Drift ∈ {Warms up, Finishes strong} |

The active registry remains exactly 18 Elements and 11 Patterns. Pattern actions are attached only after qualification, so an unresolved or fallback action cannot demote a qualified Pattern.

## E. Element boundary contract

All 18 active Elements use the single `zone_for_score()` path with `bisect_right` and the same half-open boundaries:

| Score range | Zone |
|---|---|
| `[0.00, 0.20)` | 1 |
| `[0.20, 0.40)` | 2 |
| `[0.40, 0.60)` | 3 |
| `[0.60, 0.80)` | 4 |
| `[0.80, 1.00]` | 5 |

The exact boundary values `.20`, `.40`, `.60`, and `.80`, plus `0`, `0.199999`, `0.399999`, `0.599999`, `0.799999`, and `1.0`, are asserted. The 18 covered keys are:

`hero_pool_breadth`, `hero_pool_stability`, `hero_exploration_rate`, `toolkit_breadth`, `post_loss_familiarity_shift`, `role_breadth`, `combat_involvement`, `finisher_orientation`, `death_exposure`, `off_pool_performance`, `off_pool_activity_stability`, `performance_volatility`, `recent_form_shift`, `recent_activity_shift`, `session_length_tendency`, `late_session_performance`, `post_loss_activity_shift`, `post_loss_performance_response`.

## F. Test results

Final deterministic checks:

| Command | Result |
|---|---|
| `uv run pytest -q` / `make test` | 167 passed, 2 skipped, 1 warning |
| `make lint` | Passed: Ruff and Next ESLint; no errors or warnings |
| `make typecheck` | Passed: mypy, 144 source files; web `tsc --noEmit` passed |
| `make test-contract` | 4 passed, 1 warning |
| `make test-integration` | 4 passed |
| `make test-e2e` | 70 passed in 32.9s |
| `make taxonomy-validate` | Passed; 127 heroes validated |
| `make dna-catalog-check` | Passed against regenerated catalog |
| `make docs-check` | Passed |
| `make api-client` | Passed; generated client metadata remained synchronized |
| `git diff --check` | Passed |

The report contract test also confirms the current report has 18 Elements, 11 Patterns, v5.1 metadata, baseline provenance, additive action evidence summaries, and zero Free match-detail or replay-parse requests. A transformed v5.0 payload continues to validate with its original schema version and without the new additive fields.

## G. Known limitations

Live smoke was not run because no live API credentials were available in the workspace. Deterministic source/fixture, contract, integration, and browser suites cover the changed behavior without external calls. No unresolved methodology decision or silent TODO remains from the alignment plan.
