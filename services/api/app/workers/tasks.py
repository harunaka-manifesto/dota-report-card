"""Railway deploy-entrypoint shim.

The Railway worker service is configured (outside this repo, in the Railway
dashboard) to run ``celery -A app.workers.tasks.celery_app worker ...``. That
command string cannot change as part of this relocation, so this module keeps
``app.workers.tasks`` importable and re-exports the real Celery app and task
functions, which now live in ``report_card.workers.tasks`` (the legacy
report-card package is only reachable from the deprecated /v1 API and this
worker entrypoint, never from ``app.tracker``). Celery task names stay
``dota_report_card.*`` — unchanged by the relocation.
"""

from __future__ import annotations

from report_card.workers.tasks import *  # noqa: F401,F403
from report_card.workers.tasks import (
    _close_runner,
    celery_app,
    configure_service,
    purge_expired_task,
    release_identity_task,
    run_analysis_task,
    validate_worker_dependencies,
)

__all__ = [
    "_close_runner",
    "celery_app",
    "configure_service",
    "purge_expired_task",
    "release_identity_task",
    "run_analysis_task",
    "validate_worker_dependencies",
]
