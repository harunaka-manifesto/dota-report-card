Read `/AGENTS.md` first. These instructions extend the root rules for `services/api`.

# services/api — module map and rules

`services/api/app/tracker/` is the tracker: schema, ingestion pipeline, analysis engines, the
`/mobile/v1` API, and workers. Read its own
[module map](app/tracker/README.md) and the
[tracker architecture](../../docs/tracker/architecture/README.md) before changing it.

`services/api/app/{core,storage,opendota,stratz,providers}` are shared runtime modules the
tracker builds on: settings, logging and redaction, provider errors, caches, the database
engine and schema-revision check, and the OpenDota and STRATZ transports.

`app/main.py` is the deploy composition root (`uvicorn app.main:app`): it serves `/health*` and
mounts `/mobile/v1`, `/store` and `/internal/tracker`. `app/workers/tasks.py` is a fixed Railway
entrypoint shim (`celery -A app.workers.tasks.celery_app`) that re-exports the tracker's Celery
app.

**Never import `app.main` from `app.tracker`.** The composition root depends on the tracker,
never the reverse; this is enforced by
[`tests/tracker/test_architecture_boundaries.py`](../../tests/tracker/test_architecture_boundaries.py).
