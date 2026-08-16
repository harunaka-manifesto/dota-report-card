# Free DNA finding-led QA

This checklist covers the finding-led revision described in
`docs/free-dna-finding-system.md`. It treats the attached implementation plan
as the product specification and records the repository evidence separately
from manual release checks.

## Automated acceptance matrix

| Area | Evidence | Status |
|---|---|---|
| Free cost boundary | `test_free_cache_miss_never_calls_match_details_or_parse_requests`; source request ledger remains profile + history only. | Pass |
| Shared population | Finding context asserts its eligible count equals both normalized summary features and DNA rows. | Pass |
| Deterministic signals/rules | `test_free_findings_signals.py`, `test_free_findings_rules.py`, and replay equality assertions. | Pass |
| Ranking/conflicts/story | `test_free_findings_ranking.py`, `test_free_findings_conflicts.py`, and `test_free_story_selection.py`. | Pass |
| Copy safety | Versioned catalog validation plus `test_free_findings_copy.py`; no causal/psychological/diagnostic claim lint violations. | Pass |
| Public privacy/schema | v2 Pydantic validation, recursive private-key checks, and SVG identifier checks in `test_free_dna_contract.py`. | Pass |
| v1 compatibility | v1 schema classes and legacy renderer remain available; v2 dispatch is explicit in the report route. | Pass |
| Story interaction | Chromium Playwright coverage opens the reveal, finding disclosure, identity/exposed/strength shares, DNA X-ray, and methodology dialog. | Pass |
| Deep Scan preservation | Existing Deep Scan tests remain separate; Free never invokes detail or replay boundaries. | Pass |

## Fixture-backed result

The 35-row fixture completes as a limited-history v2 report and publishes
multiple receipt-backed findings, including a strength, a contradiction, and a
behavior experiment candidate. The report contains the reveal, finding pages,
identity card, DNA X-ray, and Deep Scan handoff; an experiment page is included
when its finding clears the main-story confidence/selection gate. The report
validator rejects account IDs, raw rows, source match IDs, legacy payloads, and
unresolved story references.

## Local verification commands

```bash
uv run pytest -q
uv run ruff check services/api tests
uv run mypy services/api/app
npm run typecheck --prefix apps/web
npm run lint --prefix apps/web
cd apps/web && ./node_modules/.bin/playwright test tests/e2e/report.spec.ts --project=chromium --reporter=line
```

The live OpenDota smoke remains opt-in and is not required for the deterministic
fixture suite. It should be run with a controlled key before production to
verify provider rate-limit, retry, and latency behavior.

## Manual release checks

- Test VoiceOver/NVDA through the finding disclosure, experiment page, share
  selector, methodology dialog, and error boundaries.
- Review identity, exposed-finding, and strength SVG cards at their target
  social dimensions; confirm downloaded/native-shared cards contain no
  identifier-shaped text.
- Exercise keyboard navigation and hash/session resume on a narrow viewport,
  at 200% zoom, and with reduced motion.
- Run the production-like PostgreSQL/Redis/Celery path and verify immutable
  report retention/purge behavior across process restarts.
- Review finding distributions and suppression rates on an approved sample;
  synthetic fixtures prove deterministic behavior, not scientific calibration.
