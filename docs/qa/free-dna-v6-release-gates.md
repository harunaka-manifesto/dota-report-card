# Free DNA v6 release gates

The implementation, private training calibration, synthetic evaluation, and
sealed-holdout evaluation are complete. Every automated numerical gate passes.
Public release remains blocked on independent human review, data-basis
approval, and operator authorization. Keep `FREE_DNA_V6_ENABLED=false`.

## Required calibration evidence

- At least 1,000 public/consented profiles in the previous-year corpus.
- Deterministic player-exclusive 70/30 train/holdout split.
- Stratification by eligible history volume, hero-pool concentration, lobby mix,
  and region; never MMR.
- Empirical 95% interval coverage between 93% and 97%.
- Empirical finding-family FDR ≤5%.
- Nonblank identity for at least 80% of eligible holdout players.
- At least 80% split-half agreement for high-confidence identity zones.
- Zero forbidden causal, positioning, death-quality, or rank/MMR copy claims.
- Dota reviewer precision ≥90% on supported-and-believable fixtures.

The staged workflow emits candidate baseline and threshold files, measured
synthetic and holdout evidence, an aggregate evaluation artifact, and a release
manifest. `release_ready` is derived from every required gate. Fixture artifacts
under `tests/fixtures/v6` validate schema and wiring only.

## Automated gates

```bash
uv run pytest -q --ignore=tests/calibration
uv run pytest -q tests/calibration -m calibration
uv run ruff check .
uv run mypy services/api/app
pnpm --dir apps/web run build
pnpm --dir apps/web run typecheck
pnpm --dir apps/web exec playwright test tests/e2e/report-v6.spec.ts
```

The v6 workflow also runs a production build and a full-repository Ruff check.
No v6 E2E is skipped by environment flag. The Free report cost boundary must
remain one history request and zero detail, parse, and parse-status requests.

## Evidence snapshot

The following local private calibration evidence was recorded on 2026-08-23
from the dirty worktree based at `84075d54243115d63efead8898b5cd42ced1ed7d`.
Private paths and checksums are reported without profile or match identifiers.

| Gate / requirement | Command or process | Evidence artifact | Current status | Date | Commit SHA |
| --- | --- | --- | --- | --- | --- |
| Real corpus and split | `build_v6_calibration_artifacts.py migrate` then `validate` | 1,130 profiles; 422,147 matches; deterministic 791/339 split; no rank/MMR dimensions | pass | 2026-08-23 | working tree |
| Training baseline candidate | `build_v6_calibration_artifacts.py baseline` | 791 training profiles; 301,507 matches; 1,748 aggregate cells; strict load passes | candidate | 2026-08-23 | working tree |
| Training thresholds candidate | `build_v6_calibration_artifacts.py thresholds` | all 19 metrics; non-empty full and A/B samples; strict load passes | candidate | 2026-08-23 | working tree |
| Synthetic coverage/FDR | `evaluate_v6_calibration.py synthetic` | 226/240 interval coverage (94.17%); 9/200 global-null family discoveries (4.5% FDR); 2,000 iterations | pass | 2026-08-23 | working tree |
| Sealed holdout | `evaluate_v6_calibration.py holdout` | 339/339 profiles; 339 nonblank identities (100%); 220/226 split-half agreements (97.35%); zero copy/cost violations | pass | 2026-08-23 | working tree |
| Reproducibility | fresh baseline and 791-profile threshold rebuild | Byte-identical SHA-256: baseline `8b06e0aa…c674`, thresholds `8debcc54…3e41` | pass | 2026-08-23 | working tree |
| Human review and data basis | `review-packet`, independent review, then `ingest-review` | Human evidence must be supplied; the agent cannot self-approve | blocked externally | 2026-08-23 | not applicable |

Operational steps, monitoring boundaries, staged rollout, and rollback are in
[`docs/operations/free-dna-v6-release.md`](../operations/free-dna-v6-release.md).
