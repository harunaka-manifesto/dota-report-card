# V7 NEW-LINEAGE QA — 2026-09-08

Status: PASS for the analytical/runtime backend scope.

| Gate | Result |
|---|---|
| Frozen projection/population schema, version, self-digest, compatibility | PASS |
| Categorical vocabulary/order, missing artifact, unsupported level | PASS |
| No per-user fitting / synthetic research-runtime parity | PASS |
| Safe real DISCOVERY parity, all 16 Findings, tolerance 1e-12 | PASS |
| Finding ranking, D1 gate, shrinkage, withheld and negative-control fences | PASS |
| Recommendation 15/arm, contamination, canonical copy, refusal, privacy | PASS |
| Archetype 18-grid, specials, dominant mode, no default, refusal | PASS |
| Reviewed deep-query normalization and batch/schema refusal | PASS |
| Acquisition → canonical cache → frozen runtime → persistence → V7 API | PASS — fake provider, no network |
| Capability validation, persistence lifecycle, V7 API read boundary | PASS |
| Public projection leak checks | PASS |
| Protected split and rank fences | PASS |
| Full V7 and STRATZ tests | PASS — 710 passed |
| Full repository tests | PASS — 1,343 passed, 3 skipped |
| Ruff | PASS |
| Mypy | PASS — 252 source files |
| Python sdist/wheel and packaged artifact data | PASS |
| Runtime import/artifact compatibility smoke | PASS |
| Documentation check | PASS |
| Frontend TypeScript/build | NOT APPLICABLE — no frontend files changed; dependencies are absent in this worktree |
| Browser E2E | NOT APPLICABLE — no renderer change |

Warnings were limited to upstream Starlette/httpx and Alembic deprecations.
There were no provider calls. `CANDIDATE_TEST`, `CALIBRATION_RESERVED`, and
`SEALED_VALIDATION` were not read. No deployment or merge occurred.
