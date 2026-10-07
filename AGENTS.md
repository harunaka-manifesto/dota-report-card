# Dota Tracker — Agent Operating Contract

This repository holds the **Dota Tracker** backend (the native iOS client lives elsewhere). It is
the only product here. Read this file before making any change.

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

- **Tracker:** `services/api/app/tracker/`, `migrations/versions/`, `tests/tracker/`,
  `docs/tracker/`.
- **Shared runtime the tracker builds on:** `services/api/app/{core,storage,opendota,stratz,providers}`,
  the composition root `services/api/app/main.py`, the worker entrypoint shim
  `services/api/app/workers/tasks.py`, `migrations/`, and `infra/`. See
  [`services/api/AGENTS.md`](services/api/AGENTS.md).
- **Reusable reference data, not product truth:** `research/`, `heroes_metadata/`, `assets/`,
  `docs/tracker/reference/` (vendor OpenAPI specs), and the untracked, private `.local/`
  corpora. Never read, list, or move `.local/`.

The former Dota Report Card / Free DNA product was removed on 2026-10-07 (owner decision: it was
never live and had no users). Its history is in Git and in the ledger.

## Tracker rules

- Changes that alter ADR 0001–0005 decisions (client boundary, canonical boundary, `match_id`
  as the unit of work, two-stage single finalization, entitlement above data, no runtime LLM,
  new infrastructure, STRATZ on the fresh path) need a new ADR. Routing policy, batch sizes,
  retry ladders, operational thresholds, and worker counts do not.
- Open owner decisions are listed in the ledger. Implement fail-closed behaviour; never invent
  product values.

## Production safety

- **No deployment without an explicit owner request.** `main` deploys the backend to Railway.
  Do not merge to `main`, deploy Railway, modify production environment variables, or toggle
  production flags. Return a validated commit and wait.
- **Provider cost protection.** Do not make OpenDota or STRATZ calls solely to validate UI,
  layout, or wiring. Use stored data, fixtures, and recorded responses.
- **Deploy entrypoints are fixed.** The Railway dashboard depends on these paths and commands;
  do not rename or move them: `infra/docker/api.Dockerfile`, `uvicorn app.main:app`,
  `celery -A app.workers.tasks.celery_app`, `alembic upgrade head`.

## Required completion report

Every implementation agent MUST return:

    TASK TYPE: ...
    BASE SHA: ...
    NEW SHA: ...
    CHANGED FILES: ...
    BACKEND FILES CHANGED: YES / NO
    PRODUCTION-SHAPED FIXTURE: PASS / FAIL / NOT APPLICABLE
    TYPECHECK: PASS / FAIL / NOT APPLICABLE
    LINT: PASS / FAIL / NOT APPLICABLE
    BUILD: PASS / FAIL / NOT APPLICABLE
    OPENDOTA QA CALLS: <number>
    DEPLOYED: YES / NO
    SAFE TO MERGE: YES / NO
