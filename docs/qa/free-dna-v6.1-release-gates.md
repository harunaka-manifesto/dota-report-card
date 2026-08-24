# Free DNA V6.1 release gates

Current state: **State B complete; State C pending — public release blocked**. Keep
`FREE_DNA_V61_ENABLED=false` and all V6.1 shadow/experimental flags false.

For the owner-directed production beta, the automated State B result can be
paired with a separate `production-beta-authorization-6.1.0.json` file. That
file records the owner’s assumption that review approvals are complete and
authorizes beta traffic without changing the frozen training manifest. It does
not claim that independent reviews were performed.

The repository contains the additive route, strict schema, canonical ingestion
contract, typed registries, estimator wiring, deterministic copy, accessible
relationship rendering, fixture artifacts, and synthetic checks. Those checks
exercise implementation behavior; they do not substitute for calibration on a
real public/consented corpus or a sealed holdout.

## State model

| State | Required evidence | Current status |
|---|---|---|
| A: implementation | all planned runtime/model/API/web/calibration/test/docs/migration/rollback work; V5/V6 compatibility; fixture artifacts; unit, contract, type, lint, and synthetic checks | complete locally |
| B: calibration-ready | approved corpus; canonical runtime/calibration parity; player-exclusive 70/30 split; frozen training artifacts and sealed holdout | complete for the existing-corpus offline run |
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

## State B existing-corpus evidence

The owner-directed offline run reused the exact existing corpus; it did not run
the collector or make a new OpenDota request. The corpus is
`.local/calibration/v6-eligible-corpus-windowed.json`, SHA-256
`1cbce329f903ccad922aeddb93046b6aa2e505004937ebaaec1b854d853e41bd`. The
frozen seed-6000 split is `.local/calibration/manifests/split-6000.json`,
SHA-256 `a1433de109368ba06e54ea65ae595a83e8b8376c5832b2dc91cf2b1f37ac85e9`,
with 791 training and 339 holdout profiles and zero overlap.

The staged artifact build, sealed holdout, and byte-reproducibility record are
documented in [the existing-corpus calibration record](free-dna-v6.1-existing-corpus-calibration-record.md).
The aggregate result is State B true, while State C remains false because
independent statistical, Dota-believability, privacy/data-basis, accessibility,
product-comprehension, container, and operator approvals are still absent.
The separate production-beta path is the explicit owner authorization for the
requested beta rollout; it is not a replacement for the formal independent
review record.

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
