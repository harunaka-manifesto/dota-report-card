# Free DNA v6 release gates

The implementation is complete, but public release is blocked on calibration.
Keep `FREE_DNA_V6_ENABLED=false` until all gates below are reviewed against the
real corpus.

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

The builder emits baseline, threshold, and machine-readable evaluation files,
but intentionally reports `external-review-required` until these measurements
exist. Fixture artifacts under `tests/fixtures/v6` validate schema and wiring;
they are not production calibration artifacts.

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

The following local evidence was recorded on 2026-08-23 from the uncommitted
implementation worktree. The base repository commit is
`78b57c0d0cd7f77d760afc1deffd5146776f0453`; no remediation commit has been
created yet.

| Gate / requirement | Command or process | Evidence artifact | Current status | Date | Commit SHA |
| --- | --- | --- | --- | --- | --- |
| Backend behavior and Free cost boundary | `uv run pytest -q --ignore=tests/calibration` | 266 passed, 2 skipped; v6 contract tests include one history request and zero detail/parse/status requests | pass | 2026-08-23 | working tree; base `78b57c0d` |
| Calibration artifact schema and deterministic smoke gates | `uv run pytest -q tests/calibration -m calibration` | 10 passed; fixture artifacts only | pass for wiring; production calibration still blocked | 2026-08-23 | working tree; base `78b57c0d` |
| Repository lint and backend types | `uv run ruff check .` and `uv run mypy services/api/app` | Ruff clean; mypy clean for 180 files | pass | 2026-08-23 | working tree; base `78b57c0d` |
| Web build and types | `pnpm --dir apps/web run build` and `pnpm --dir apps/web run typecheck` | Next production build and TypeScript check completed successfully | pass | 2026-08-23 | working tree; base `78b57c0d` |
| v6 story, interaction, Deep, responsive, and reduced-motion behavior | `pnpm --dir apps/web exec playwright test tests/e2e/report-v6.spec.ts` | 15 passed across Chromium, Firefox, WebKit, mobile Safari, and reduced-motion | pass | 2026-08-23 | working tree; base `78b57c0d` |
| Real-corpus calibration: 1,000 profiles, split, interval coverage, FDR, identity agreement | Operator-supplied corpus through `scripts/build_v6_calibration_artifacts.py`, followed by review | No real calibration corpus or generated production artifacts supplied | blocked | 2026-08-23 | not applicable |
| Reviewer precision and forbidden-copy review | Dota reviewer fixture review plus generated copy report | Automated forbidden-copy scan is covered; human precision review evidence is absent | blocked | 2026-08-23 | not applicable |
