from __future__ import annotations

from app.core.config import Settings
from app.main import create_app
from fastapi.testclient import TestClient

UNREACHABLE = Settings(
    database_url="postgresql+psycopg://nobody:nothing@127.0.0.1:1/none?connect_timeout=1",
    redis_url="redis://127.0.0.1:1/0",
)


def test_composition_root_serves_health_and_mounts_only_tracker_surfaces() -> None:
    app = create_app(UNREACHABLE)
    mounts = {getattr(route, "path", "") for route in app.routes}
    assert {"/mobile/v1", "/store", "/internal/tracker"} <= mounts
    assert not any(path.startswith("/v1") for path in mounts)
    client = TestClient(app)
    assert client.get("/health/live").json() == {"status": "ok", "api": "ok"}
    ready = client.get("/health/ready")
    assert ready.status_code == 503
    assert ready.json()["postgres"] == ready.json()["redis"] == "unavailable"
    assert client.get("/v1/reports/anything").status_code == 404


def test_railway_worker_entrypoint_is_the_tracker_celery_app() -> None:
    from app.tracker.worker import celery_app as tracker_celery_app
    from app.workers.tasks import celery_app

    assert celery_app is tracker_celery_app
