# Free DNA V6.1 release gates

Current state: **State A complete; State D handoff ready — public release blocked**. Keep
`FREE_DNA_V61_ENABLED=false`.

The repository contains the additive route, strict schema, canonical ingestion
contract, typed registries, estimator wiring, deterministic copy, accessible
relationship rendering, fixture artifacts, and synthetic checks. Those checks
exercise implementation behavior; they do not substitute for calibration on a
real public/consented corpus or a sealed holdout.

## State model

| State | Required evidence | Current status |
|---|---|---|
| A: implementation | all planned runtime/model/API/web/calibration/test/docs/migration/rollback work; V5/V6 compatibility; fixture artifacts; unit, contract, type, lint, and synthetic checks | complete locally |
| B: calibration-ready | approved corpus; canonical runtime/calibration parity; player-exclusive 70/30 split; frozen training artifacts and sealed holdout | blocked externally |
| C: release-ready | measured interval coverage/FDR; identity stability; copy and Dota review; privacy/data-basis/statistical approval; container/checksum verification; operator authorization | blocked externally |
| D: Figma Markdown handoff | implemented-contract brief, exact documentation tasks, unresolved inputs, future-agent DoD | ready; Figma execution still needs target access/input |

## Required measured gates

- At least 1,000 public/consented profiles using the canonical one-request
  projection and normalization contract.
- Deterministic player-exclusive 70/30 train/holdout split, stratified without
  rank or MMR.
- Empirical 95% interval coverage from 93% through 97%.
- Empirical family false-discovery rate at or below 5%, including the nested
  family/branch procedure.
- Nonblank identity for at least 80% of eligible holdout players and at least
  80% split-half agreement for high-confidence identity slots.
- Zero forbidden causal, motive, psychology, positioning, death-quality,
  rank, or MMR claims.
- Dota reviewer precision at least 90% on supported-and-believable examples.
- Independent statistical and data-basis approvals with references.
- Byte-identical artifact rebuilds, checksum-linked image verification, and an
  explicit operator decision for every traffic stage.

## State A evidence

`scripts/evaluate_v61_calibration.py` runs 2,000 seeded fixture/synthetic
replicates. The current fixture result is approximately 96.65% interval
coverage and 4.8% global-null family discovery. These values prove that the
test harness and fail-closed state evaluator work; they are not empirical
production claims. The evaluator uses a fixed required-check manifest and
reports State A true only when every named implementation item and the
synthetic harness pass. It must report States B and C false when real-corpus,
holdout, review, privacy, container, or authorization evidence is absent.

## Verification commands

```bash
uv run pytest -q tests/unit/test_free_dna_v61_contract.py \
  tests/unit/test_v61_estimators.py tests/unit/test_opendota_client.py
uv run pytest -q tests/calibration/test_v61_calibration_evaluation.py
uv run pytest -q tests/unit/test_build_v61_calibration_artifacts.py
uv run ruff check services/api/app/player_analysis_v61 \
  services/api/app/ingestion/summary_history_contract.py \
  services/api/app/reports/dna_assembly_v61.py
pnpm --dir apps/web run typecheck
make docs-check
```

See the [V6.1 release runbook](../operations/free-dna-v6.1-release.md) for
promotion and rollback rules.
