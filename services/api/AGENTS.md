Read `/AGENTS.md` first. These instructions extend the root rules for `services/api`.

# services/api — module map and rules

`services/api/app/tracker/` is the tracker: schema, ingestion pipeline, analysis engines, the
`/mobile/v1` API, and workers. Read its own
[module map](app/tracker/README.md) and the
[tracker architecture](../../docs/tracker/architecture/README.md) before changing it.

`services/api/app/{core,storage,opendota,stratz,providers,ingestion,identity}` are shared
modules. They serve the tracker AND the live legacy report-card API mounted from
`legacy/services/api/report_card`. A change here can affect the live production product even on
a tracker-only task — follow the production-safety rules in `/AGENTS.md` and, if the change
could reach the legacy product, `/legacy/AGENTS.md`.

`app/main.py` is the composition root: it mounts the tracker, the `/mobile/v1` API, and the
legacy `/v1` API into one FastAPI app. `app/workers/tasks.py` is the Celery worker entrypoint
shim used by both products' deployments.

**Never import `report_card` from `app.tracker`.** The tracker must not depend on legacy
analytical code; this is enforced by
[`tests/tracker/test_architecture_boundaries.py`](../../tests/tracker/test_architecture_boundaries.py).

Legacy report-card code lives at `legacy/services/api/report_card`. For its rules, see
[`legacy/services/api/AGENTS.md`](../../legacy/services/api/AGENTS.md).
