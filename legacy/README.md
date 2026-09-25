# Legacy report card

> Not tracker truth.

Dota Report Card / Free DNA: deprecated but **live in production**. Everything under this
directory belongs to that product. Dota Tracker is the current product; its truth lives under
[`docs/tracker/`](../docs/tracker/README.md), never here. Read [`AGENTS.md`](AGENTS.md) before
changing anything in this tree.

## What's here

| Path | Purpose |
|---|---|
| `apps/web/` | Next.js frontend, deployed to Vercel. Renders persisted reports and calls the legacy `/v1` API. |
| `services/api/report_card/` | The `report_card` Python package: report assembly, analysis (V5.2–V7 lineages), storage, providers, workers. See [`services/api/AGENTS.md`](services/api/AGENTS.md). |
| `packages/` | Shared TypeScript packages consumed by `apps/web` (e.g. the generated API client). |
| `scripts/` | Legacy build/release/data scripts (API client generation, DNA catalog, hero taxonomy, copy review). |
| `infra/runtime-artifacts/` | Frozen V6.1 analytical artifacts, copied into the API Docker image. Do not regenerate outside an authorized analytical release. |
| `tests/` | Legacy contract, integration, unit, calibration, and fixture tests. A release gate for anything that could reach the live product. |
| `docs/` | Legacy product, architecture, QA, operations, and agent-safety documentation. Start at [`docs/README.md`](docs/README.md). |
| `research/` | Retained V6.1/V7 research corpora referenced by the legacy analytical code. |
| `graphify-out/` | Generated legacy knowledge graph. Non-authoritative for anything. |
| `ARCHITECTURE.md` | Legacy system architecture (V5.2–V7 lineages, report pipeline). |

`legacy/apps/web/.local/` and any other untracked/private data under `legacy/` are never moved,
read, or cleaned by an agent.

## Deploy coupling

- **Vercel** root directory is `legacy/apps/web`; "include files outside root" stays on because
  `legacy/apps/web` imports `legacy/packages`.
- **Railway** builds `infra/docker/api.Dockerfile`, which `COPY`s `legacy/services` and
  `legacy/infra/runtime-artifacts` into the image alongside the shared `services/` tree. The
  container runs `uvicorn app.main:app`.
- The Celery worker entrypoint is the shim at `app/workers/tasks.py`
  (`celery -A app.workers.tasks.celery_app`), which loads legacy report-worker tasks.

None of these paths or commands may be renamed or moved without updating the Railway/Vercel
dashboard configuration, which this repository does not control.

## Running legacy checks

```bash
make test-contract              # legacy/tests/contract
make test-integration            # tests/integration + legacy/tests/integration
make test-e2e                    # Playwright, legacy/apps/web
make api-client                  # regenerate the generated API client (must produce no diff)
make dna-catalog-check           # legacy/scripts/generate_dna_model_catalog.py --check
make copy-review-catalog-check   # legacy/scripts/generate_copy_review_catalog.py --check
make taxonomy-validate           # legacy/scripts/validate_hero_taxonomy.py
make docs-check                  # scripts/check_docs.py (tracker) + legacy/scripts/check_legacy_docs.py (legacy)
```

## Where to go next

- [`legacy/AGENTS.md`](AGENTS.md) — the full legacy operating contract: production safety,
  persisted-report compatibility, testing and release gates, frozen analytical invariants.
- [`legacy/docs/README.md`](docs/README.md) — the legacy documentation index.
