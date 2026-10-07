"""Railway deploy-entrypoint shim.

The Railway worker service is configured (outside this repo, in the Railway
dashboard) to run ``celery -A app.workers.tasks.celery_app ...``. That command
string is a fixed deploy entrypoint, so this module keeps it importable and
re-exports the tracker's Celery application. Tracker workers are normally
started per priority lane (``make tracker-worker PRIORITY=n``), which uses
``app.tracker.worker:celery_app`` directly; both names are the same object.
"""

from __future__ import annotations

from app.tracker.worker import celery_app

__all__ = ["celery_app"]
