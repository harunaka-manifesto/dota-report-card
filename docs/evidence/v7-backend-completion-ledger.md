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

### AD3 — V7 gets its own route prefix, not a branch inside the V6.1 routes

The survey found no existing answer to "where is a V7 report served from". The
V6.1 path (`POST /v1/analyses` → `GET /v1/reports/{id}`) returns an untyped
`JSONResponse`, so the report shape is invisible to OpenAPI today.

Decision: V7 is served under its own `/v1/v7/` prefix with a typed
`response_model`. Rationale: a separate prefix cannot regress V6.1 by
construction, which is the phase's hardest constraint; and a typed response
model puts the V7 contract into OpenAPI, which is what a frontend agent needs.
This departs from the existing untyped-report convention deliberately.

### AD4 — reuse the existing job coalescing rather than build a lock

The survey found that `repository.get_or_create_inflight_job` already coalesces
concurrent work on a unique `active_key` of
`f"{account_id}:{model_version}:{analysis_mode}"`, with an `IntegrityError`
race path that returns the winner. That satisfies the phase's duplicate-
acquisition requirement without new machinery. V7 reuses it with a V7-specific
`model_version` fingerprint, and must **not** reuse
`_compatibility_model_version`'s V6.1 branch, which would import
`default_versions_v61()` and make the V7 key meaningless.

### AD5 — V7 must not reuse the V6.1 ingestion path

`app/ingestion/summary_normalize.py` assumes OpenDota field names and
conventions (`radiant_win`, `player_slot < 128`, `duration`). V7 data is STRATZ
canonical and already has its own normaliser at `app/stratz/normalize.py`. The
V7 runtime stays on the STRATZ canonical types end to end. `_save_player_dna`
gets a sibling method, not a branch, so no OpenDota-shaped helper is in scope.

## Workstreams

| id | charter | model | status |
|---|---|---|---|
| W1 | Runtime architecture survey (read-only) | Sonnet | **done** — findings drove AD3/AD4/AD5 |
| W2 | Relocate the analytical library (AD1) | Sonnet | **done** — 96b14e3, verified by the orchestrator |
| W3 | Freeze population parameters (see §1 of the payload spec) | Sonnet | dispatched |
| W4 | Capability payload model | Sonnet | dispatched |
| W5 | Capability assembler | Sonnet | pending W3+W4 |
| W6 | Fixtures + contract tests | Sonnet | pending W4 |
| W7 | Service + route boundary (AD3) | Sonnet | pending W4 |
| W8 | Persistence + reuse (AD4) | Sonnet | pending W5 |
| W9 | Observability | Sonnet | pending W8 |
| W10 | Docs + FE handoff | Sonnet | pending W7 |
| W11 | Independent red-team | Opus | pending integration |

## Verification stance

A worker reporting "tests pass" is not evidence. Every workstream is re-verified
by the orchestrator from the integrated worktree before it is treated as done.
W2 was verified this way: the rank fence, the content-catalog drift check and
the absence of the old package were all re-run independently of the worker's
report.
