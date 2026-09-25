# V7 repository hygiene audit — 2026-09-01

Status: implementation audit for the V7 staging line. No provider calls,
analytical tuning, holdout inspection, or production deployment occurred.

Base: current `origin/staging` at the start of this task. The audit branch was
created from `2823e339aef270ddb83e18e563c30e95169042ea`.

## Lineage decision

```text
main / production reference
    V6.1 OpenDota lineage, with its existing release gates and artifacts

staging / development
    V7 STRATZ-native provider foundation and future analytical rebuild

older generations
    unsupported as product targets; retained only for active compatibility,
    V6.1 reproducibility, unique evidence, or database history
```

The default V5.2-compatible runtime remains in the tree because the current
application wiring still uses it when V6/V6.1 flags are disabled. V6.0 code is
also retained because V6.1 imports its contracts and assembly helpers. Neither
is a V7 analytical dependency.

## Inventory and disposition

| Surface | Classification | Evidence and disposition |
|---|---|---|
| `services/api/app/behavior/`, `app/dna/`, `app/hero_portfolio/`, legacy report assembly | `KEEP_V61_REPRODUCIBILITY` | Still reachable from the default compatibility runtime and V5.2 persisted-report path. |
| `services/api/app/player_analysis_v6/` and V6 report assembly | `KEEP_V61_REPRODUCIBILITY` | Imported by V6.1 assembly, scripts, validators, and tests. |
| `services/api/app/player_analysis_v61/`, V6.1 artifacts, fixtures, tests | `KEEP_V61_PRODUCTION` | Current V6.1 release/reproducibility boundary. |
| `migrations/`, `alembic/`, migration tests | `KEEP_DATABASE_HISTORY` | Historical migration chain is required; no squashing or deletion. |
| `research/stratz-enrichment/`, V6.1 evidence, unique historical reports | `KEEP_UNIQUE_RESEARCH_EVIDENCE` | Required to explain decisions, provenance, and unresolved semantics. |
| `services/api/app/opendota/cache.py` | `RENAME_OR_REFACTOR` | Generic cache/hash implementation was owned by an OpenDota path; moved to `app/core/cache.py`. |
| `AnalysisSource` protocol | `RENAME_OR_REFACTOR` | Its raw-row contract is OpenDota/V6 legacy behavior; renamed to `OpenDotaAnalysisSource` with a compatibility alias. |
| legacy `assemble_free_dna_report_v4` implementation name | `RENAME_OR_REFACTOR` | The default implementation is the retained V5.2 compatibility path; the truthful name is `assemble_legacy_free_dna_report`. |
| `.github/workflows/v6-quality.yml` | `DELETE_SUPERSEDED` | Duplicated the canonical `qa.yml` backend/web/calibration coverage and used stale V6-only workflow identity. |
| `docs/prompts/stratz/01-luna-max-provider-migration.md` | `DELETE_OBSOLETE_DOC` | Superseded by the V7 STRATZ-native architecture and research/evidence documents; its useful provider facts are already canonicalized. |
| `docs/prompts/stratz/02-opus5-enrichment-research.md` | `DELETE_OBSOLETE_DOC` | Superseded by the committed `research/stratz-enrichment/` reports and the V7 learnings manual. |
| archived V5/V6 docs, V6.1 plans, old fixtures, and legacy tests | `KEEP_UNIQUE_RESEARCH_EVIDENCE` | Each was checked for references or unique contract/release evidence; no safe deletion was established in this pass. |

No runtime code, test, database migration, V6.1 artifact, or public report
fixture was deleted.

## Deletion ledger

| Path | Classification | Why obsolete | Replacement | V6.1 impact | V7 impact |
|---|---|---|---|---|---|
| `.github/workflows/v6-quality.yml` | `DELETE_SUPERSEDED` | Duplicate CI pipeline; `qa.yml` runs the full backend, V7, contract, integration, migration, taxonomy, catalog, docs, web, and browser checks. | `.github/workflows/qa.yml` | Protected by canonical QA coverage. | Removes stale V6 workflow identity; V7 checks remain. |
| `docs/prompts/stratz/01-luna-max-provider-migration.md` | `DELETE_OBSOLETE_DOC` | Required a provider swap preserving V6.1 meaning, which conflicts with the V7 rebuild direction. | `docs/architecture/stratz-v7-provider-contract.md`, `research/stratz-enrichment/`, this audit | None; it was a task prompt, not runtime evidence. | Prevents a compatibility-shim instruction from steering V7. |
| `docs/prompts/stratz/02-opus5-enrichment-research.md` | `DELETE_OBSOLETE_DOC` | Research task prompt is superseded by its committed reports and current learnings. | `research/stratz-enrichment/`, `docs/agent/analytical-learnings-and-gotchas.md` | None; unique conclusions remain in research. | Keeps current V7 evidence canonical. |

## Refactor ledger

| Old surface | New surface | Compatibility treatment |
|---|---|---|
| `app.opendota.cache` | `app.core.cache` | All first-party imports use the provider-neutral core module; no cache behavior changed. |
| `AnalysisSource` | `OpenDotaAnalysisSource` | Existing alias remains for integrations while V7 continues through `HistoryProvider`. |
| `assemble_free_dna_report_v4` | `assemble_legacy_free_dna_report` | Historical v4/v5 import names remain aliases; the service uses the truthful legacy name. |

## Test migration ledger

| Test/surface | Classification | Action | Replacement or retained protection |
|---|---|---|---|
| `tests/unit/test_qa_regressions.py` cache import | provider-neutral current contract | Updated to `app.core.cache`. | Existing TTL behavior test remains unchanged. |
| Existing V5/V6/V6.1 unit, contract, calibration, migration, security, and persisted-report tests | A/B/E current or historical protection | Retained after reachability review. | Existing suite and canonical `qa.yml`. |
| `tests/unit/test_v7_provider_architecture.py` and STRATZ tests | C/D V7/provider contract | Retained. | Provider isolation, native semantics, and credential-free transport tests. |
| Pre-V6.1 tests | F/G candidate | No deletion: runtime or V6.1 evidence dependency was found, or the test protects an active compatibility path. | Deletion is deferred until a narrower V6.1-only runtime boundary exists. |

Offline validation recorded 652 tests collected before the cleanup and 653
after it: the full suite finished with `653 passed, 3 skipped, 2 warnings`.
The one-count increase is the legacy-name compatibility regression test; no
test was deleted.

## Documentation canonicalization

- `README.md` and `ARCHITECTURE.md` now describe V6.1/OpenDota as the maintained
  production/reproducibility reference and V7/STRATZ as staging development.
- `docs/agent/analytical-learnings-and-gotchas.md` is the mandatory analytical
  and engineering gotchas manual.
- `docs/agent/README.md`, root `AGENTS.md`, and `services/api/AGENTS.md` point
  future analytical work to that manual.
- The V5.2 SSOT, V6/V6.1 architecture and release records remain explicitly
  scoped as compatibility, historical, or release evidence rather than V7
  analytical requirements.
- Research references to the deleted STRATZ task prompts were replaced with
  current contract/research references. A repository-wide path search is part
  of final validation.

## Activity and safety

```text
STRATZ calls: 0
OpenDota calls: 0
playback calls: 0
STRATZ_API_TOKEN required: NO
V6.1 analytics changed: NO
V6.1 artifacts changed: NO
holdout inspected: NO
production deployed: NO
main touched: NO
```
