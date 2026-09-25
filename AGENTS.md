# Dota Tracker — Agent Operating Contract

This repository's current product is **Dota Tracker** (native iOS client, elsewhere; this repo
holds the tracker backend). A deprecated but **live-in-production** legacy product, Dota Report
Card / Free DNA, lives entirely under `legacy/`. Read this file before making any change here.

## Where truth lives

| Question | Authoritative source |
|---|---|
| What a tracker feature means | that feature's `docs/tracker/<feature>/SSOT.md` |
| Cross-product rules (identity, lifecycle, metrics, entitlement, versioning) | [`docs/tracker/app_foundation/SSOT.md`](docs/tracker/app_foundation/SSOT.md) |
| How the tracker system behaves (ingestion, providers, storage, scaling) | [`docs/tracker/architecture/README.md`](docs/tracker/architecture/README.md) and its ADRs in `architecture/decisions/` |
| Progress and open owner decisions | [`docs/tracker/architecture/IMPLEMENTATION-LEDGER.md`](docs/tracker/architecture/IMPLEMENTATION-LEDGER.md) |
| Running and verifying the backend | [`docs/tracker/operations/README.md`](docs/tracker/operations/README.md) |
| The mobile API contract | [`docs/tracker/api/README.md`](docs/tracker/api/README.md) |

`docs/tracker/_archive/` is superseded product history — evidence only, never active truth.

## Map of the repository

- **Current (tracker):** `services/api/app/tracker/`, `migrations/versions/0006` onward,
  `tests/tracker/`, `docs/tracker/`.
- **Legacy (live, deprecated report card):** everything under `legacy/` — `legacy/apps/web`
  (Next.js/Vercel), `legacy/services/api/report_card` (the `report_card` Python package),
  `legacy/packages`, `legacy/scripts`, `legacy/tests`, `legacy/infra/runtime-artifacts`,
  `legacy/docs` (including `legacy/docs/agent/*` safety manuals), `legacy/graphify-out`,
  `legacy/research`, `legacy/README.md`, `legacy/ARCHITECTURE.md`.
- **Reusable reference data, not product truth for either product:** `research/`,
  `heroes_metadata/`, `assets/`, `docs/tracker/reference/` (vendor OpenAPI specs), and the
  untracked, private `.local/` corpora. Never read, list, or move `.local/`.
- **Shared runtime, used by BOTH products:** see below.

## Do not use `legacy/` for tracker work

`legacy/` material — V5–V7 analytics, report-era docs, `legacy/graphify-out`, legacy ADRs under
`legacy/docs/decisions/` — is **not** tracker truth. Do not read, cite, or copy from it when
designing or implementing tracker behavior.

Enter `legacy/` only when the task explicitly concerns the live report card, or a change that
could affect it. In that case, read `legacy/AGENTS.md` first — it carries the full legacy
operating contract and production-safety rules.

## Tracker rules

- Tracker code lives in `services/api/app/tracker/` and `migrations/versions/0006+`. It must
  not change legacy tables, routes, persisted reports, or retention.
- Changes that alter ADR 0001–0005 decisions (client boundary, canonical boundary, `match_id`
  as the unit of work, two-stage single finalization, entitlement above data, no runtime LLM,
  new infrastructure, STRATZ on the fresh path) need a new ADR. Routing policy, batch sizes,
  retry ladders, operational thresholds, and worker counts do not.
- Open owner decisions are listed in the ledger. Implement fail-closed behaviour; never invent
  product values.

## Shared code affects the live legacy product

`services/api/app/{core,storage,opendota,stratz,providers,ingestion,identity}`, `app/main.py`
(the composition root that mounts both the tracker and the legacy `/v1` API), the
`app/workers/tasks.py` worker entrypoint shim, `migrations/`, and `infra/` serve **both**
products. A change there can affect the live legacy product even on a tracker-only task. Follow
the production-safety rules below whenever you touch these paths.

## Production safety (binds every agent, because `main` deploys the live legacy product)

- **No deployment without an explicit owner request.** Do not merge to `main`, deploy Vercel
  production, deploy Railway, modify production environment variables, or toggle production
  flags. Return a validated commit and wait.
- **Release gates.** `legacy/tests/` and the legacy import paths (`report_card`, its
  subpackages) are release gates for anything that could reach the live product. A change that
  could affect the legacy product is not safe merely because tracker tests pass.
- **Provider cost protection.** Do not make OpenDota or STRATZ calls solely to validate UI,
  layout, or wiring — for either product. Use stored data, fixtures, and recorded responses.
- **Frozen V6.1 analytical artifacts.** Analytical source SHA `f85e88a277ffb365e76dd6eeac6f5009c7bd0165`
  and frozen artifact bundle digest
  `22206d20b84bf9ee73b93c64177443e1bb585ccdb818c188ac40d9acfcb358f9` must not change outside an
  explicitly authorized analytical release. See
  [`legacy/docs/agent/analytical-release-invariants.md`](legacy/docs/agent/analytical-release-invariants.md).
- **Deploy entrypoints are fixed.** The Railway and Vercel dashboards depend on these paths and
  commands; do not rename or move them: `infra/docker/api.Dockerfile`, `uvicorn app.main:app`,
  `celery -A app.workers.tasks.celery_app`, `alembic upgrade head`, and the Vercel root
  `legacy/apps/web`.

## Required completion report

Every implementation agent MUST return:

    TASK TYPE: ...
    BASE SHA: ...
    NEW SHA: ...
    CHANGED FILES: ...
    BACKEND FILES CHANGED: YES / NO
    ANALYTICAL FILES CHANGED: YES / NO
    PUBLIC REPORT CONTRACT CHANGED: YES / NO
    PERSISTED REPORT COMPATIBILITY TESTED: YES / NO
    PRODUCTION-SHAPED FIXTURE: PASS / FAIL / NOT APPLICABLE
    BROWSER E2E: PASS / FAIL / NOT APPLICABLE
    TYPECHECK: PASS / FAIL / NOT APPLICABLE
    LINT: PASS / FAIL / NOT APPLICABLE
    BUILD: PASS / FAIL / NOT APPLICABLE
    ANALYTICAL BEHAVIOR CHANGED: YES / NO
    HOLDOUT RERUN: YES / NO
    RECALIBRATION: YES / NO
    OPENDOTA QA CALLS: <number>
    DEPLOYED: YES / NO
    SAFE TO MERGE: YES / NO
