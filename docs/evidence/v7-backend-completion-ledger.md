# V7 backend completion — orchestration ledger

```text
PHASE: V7_BACKEND_COMPLETION
STATUS: IN PROGRESS
BRANCH: v7/post-corpus-finding-research
WORKTREE: /private/tmp/dota-report-card-v7-post-corpus
BASE COMMIT: 3d0a094
RESERVED SPLITS: untouched (CALIBRATION_RESERVED, SEALED_VALIDATION)
PROVIDER CALLS: 0
```

A resumable record of the fan-out. Each workstream lists its charter, owner
model, file ownership, status and outcome.

## Architecture decisions taken by the orchestrator

### AD1 — the analytical library must move into the app package

`pyproject.toml` packages only `services/api` (`[tool.setuptools.packages.find]
where = ["services/api"]`). `scripts/` is not part of the installed
distribution, so a deployed API **cannot import `scripts.v7_research`** — the
research tests only pass because pytest adds `.` to `pythonpath`.

Section 6 of the phase brief requires one source of truth per calculation, so
copying formulas into a service layer is out. Therefore the **library** moves to
`services/api/app/player_analysis_v7/research/`, and the **runnable scripts**
(collectors, supervisors, one-shot analyses) stay in `scripts/` and import from
the new location. This matches the real layering: `v7_research` is a library;
everything else in `scripts/` is an executable.

Consequence: this move blocks every other implementation workstream, so it runs
first and alone.

### AD2 — no analytical logic in the assembler

The runtime assembler orchestrates and does not compute. Any statistical
expression appearing outside the research package is a defect.

## Workstreams

| id | charter | model | status |
|---|---|---|---|
| W1 | Runtime architecture survey (read-only) | Sonnet | dispatched |
| W2 | Relocate the analytical library (AD1) | Sonnet | dispatched |
| W3 | Capability assembler | Sonnet | pending W2 |
| W4 | Persistence + reuse | Sonnet | pending W2 |
| W5 | API/contract/typing | Sonnet | pending W3 |
| W6 | Fixtures + contract tests | Sonnet | pending W3 |
| W7 | Observability | Sonnet | pending W4 |
| W8 | Docs + FE handoff | Sonnet | pending W5 |
| W9 | Independent red-team | Opus | pending integration |
