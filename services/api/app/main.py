"""Deploy composition root: ``uvicorn app.main:app``.

Mounts the Dota Tracker sub-applications (``/mobile/v1``, ``/store``,
``/internal/tracker``) and serves process health. All product behaviour lives
in ``app.tracker``; this module only wires it together.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.storage.database import (
    EXPECTED_SCHEMA_REVISION,
    check_database_revision,
    create_database_engine,
)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(
        settings.log_level,
        (settings.opendota_api_key, settings.stratz_api_token),
    )
    engines: list[Engine] = []

    def database() -> Engine:
        if not engines:
            engines.append(create_database_engine(settings))
        return engines[0]

    def readiness() -> dict[str, Any]:
        return _readiness_payload(settings, database)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            for engine in engines:
                engine.dispose()

    app = FastAPI(
        title="Dota Tracker API",
        version="1.0.0",
        description="Dota Tracker backend. The mobile contract is served under /mobile/v1.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.readiness = readiness

    @app.get("/health")
    async def root_health() -> dict[str, str]:
        return _health_response(readiness())

    @app.get("/health/live")
    async def root_liveness() -> dict[str, str]:
        return {"status": "ok", "api": "ok"}

    @app.get("/health/ready")
    async def root_readiness() -> JSONResponse:
        payload = readiness()
        return JSONResponse(_health_response(payload), status_code=200 if payload["ready"] else 503)

    from app.tracker.app_store import verifier_from_environment
    from app.tracker.mobile_api import create_mobile_app

    store_verifier = verifier_from_environment()

    apple_audience = os.getenv("TRACKER_APPLE_AUDIENCE")
    google_audience = os.getenv("TRACKER_GOOGLE_AUDIENCE")
    app.mount("/mobile/v1", create_mobile_app(
        settings,
        audiences={
            "apple": {apple_audience} if apple_audience else set(),
            "google": {google_audience} if google_audience else set(),
        },
        steam_callback_url=os.getenv("TRACKER_STEAM_CALLBACK_URL"),
        store_verifier=store_verifier,
    ))
    from app.tracker.store_api import create_store_app

    app.mount("/store", create_store_app(settings, verifier=store_verifier))
    from app.tracker.operations import create_operations_app

    app.mount("/internal/tracker", create_operations_app(
        settings, token=os.getenv("TRACKER_INTERNAL_TOKEN"),
    ))
    return app


def _readiness_payload(settings: Settings, database: Callable[[], Engine]) -> dict[str, Any]:
    try:
        check_database_revision(database())
        postgres = "ready"
    except Exception:
        postgres = "unavailable"
    try:
        import redis

        redis.Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        ).ping()
        redis_status = "ready"
    except Exception:
        redis_status = "unavailable"
    return {
        "ready": postgres == "ready" and redis_status == "ready",
        "api": "ok",
        "postgres": postgres,
        "redis": redis_status,
        "schema_revision": EXPECTED_SCHEMA_REVISION,
    }


def _health_response(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "status": "ok" if payload["ready"] else "not_ready",
        "api": str(payload["api"]),
        "postgres": str(payload["postgres"]),
        "redis": str(payload["redis"]),
        "schema_revision": str(payload["schema_revision"]),
    }


app = create_app()
