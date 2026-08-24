from __future__ import annotations

import asyncio
from collections.abc import Iterable
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.analysis.service import AnalysisService
from app.analysis.source import AnalysisSource, FixtureOpenDotaSource
from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.metrics import record_metric
from app.core.security import RateLimiter
from app.features.models import MatchFeature
from app.identity.steam import SteamWebResolver
from app.opendota.cache import RedisCache
from app.opendota.client import OpenDotaClient
from app.opendota.parse_client import OpenDotaParseClient
from app.storage.repository import InMemoryRepository, SqlAlchemyRepository


def create_app(
    settings: Settings | None = None,
    *,
    source: Any | None = None,
    repository: Any | None = None,
    cohort_population: Iterable[MatchFeature] = (),
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, (settings.opendota_api_key, settings.steam_api_key))
    if source is None:
        source = (
            FixtureOpenDotaSource(settings.effective_fixture_dir)
            if settings.opendota_source == "fixture"
            else OpenDotaClient(settings)
        )
    if repository is None:
        repository = (
            SqlAlchemyRepository(settings)
            if settings.effective_storage_backend == "database"
            else InMemoryRepository(
                report_retention_days=settings.effective_report_retention_days,
                interaction_retention_days=settings.effective_report_interaction_retention_days,
            )
        )
    identity_resolver = (
        SteamWebResolver(
            settings.steam_api_key,
            base_url=settings.steam_resolver_base_url,
            cache=(
                RedisCache(settings.redis_url, prefix="dota:steam")
                if settings.app_env == "production"
                else None
            ),
        )
        if settings.steam_api_key
        else None
    )
    parse_transport = OpenDotaParseClient(settings) if isinstance(source, OpenDotaClient) else None
    service = AnalysisService(
        cast(AnalysisSource, source),
        repository=repository,
        settings=settings,
        cohort_population=cohort_population,
        identity_resolver=identity_resolver,
        parse_transport=parse_transport,
    )
    def app_readiness() -> dict[str, Any]:
        return _readiness_payload(settings, repository, service)
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> Any:
        if settings.app_env == "production":
            readiness = app_readiness()
            if readiness["postgres"] != "ready" or readiness["redis"] != "ready" or readiness["artifacts"] != "ready":
                raise RuntimeError(f"production dependencies are not ready: {readiness}")
        if hasattr(repository, "purge_expired"):
            repository.purge_expired()
        retention_task = asyncio.create_task(_retention_loop(repository)) if hasattr(repository, "purge_expired") else None
        if isinstance(source, OpenDotaClient):
            await source.__aenter__()
        if parse_transport is not None:
            await parse_transport.__aenter__()
        try:
            yield
        finally:
            if retention_task is not None:
                retention_task.cancel()
                try:
                    await retention_task
                except asyncio.CancelledError:
                    pass
            await service.shutdown()
            if isinstance(source, OpenDotaClient):
                await source.aclose()
            if parse_transport is not None:
                await parse_transport.aclose()
            if identity_resolver is not None:
                await identity_resolver.aclose()

    app = FastAPI(
        title="OpenDota Insight System",
        version="1.0.0",
        description="Deterministic, evidence-backed player reports.",
        lifespan=lifespan,
    )
    app.state.analysis_service = service
    app.state.settings = settings
    app.state.readiness = app_readiness
    app.state.rate_limiter = RateLimiter(
        redis_url=settings.redis_url if settings.app_env == "production" else None
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "Accept", "Authorization", "If-Match"],
        expose_headers=["ETag"],
    )

    from app.workers.tasks import configure_service

    configure_service(service)

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": exc.code, "message": exc.message},
        )

    @app.get("/health")
    async def root_health() -> dict[str, str]:
        return _health_response(app_readiness())

    @app.get("/health/live")
    async def root_liveness() -> dict[str, str]:
        return {"status": "ok", "api": "ok"}

    @app.get("/health/ready")
    async def root_readiness() -> JSONResponse:
        payload = app_readiness()
        return JSONResponse(_health_response(payload), status_code=200 if payload["ready"] else 503)

    app.include_router(router)
    return app


async def _retention_loop(repository: Any) -> None:
    """Keep report/raw-payload retention enforced after process startup."""

    while True:
        await asyncio.sleep(3600)
        try:
            deleted = repository.purge_expired()
            record_metric("retention.purged", value=deleted)
        except Exception:
            record_metric("retention.failed")


def _readiness_payload(settings: Settings, repository: Any, service: AnalysisService) -> dict[str, Any]:
    postgres = "not_configured"
    if settings.effective_storage_backend == "database":
        try:
            checker = getattr(repository, "check_ready", None)
            if checker is None:
                raise RuntimeError("database repository has no schema readiness check")
            checker()
            postgres = "ready"
        except Exception:
            postgres = "unavailable"
    redis_status = "not_configured"
    worker = "in_process"
    if settings.effective_analysis_execution_backend == "celery":
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
        try:
            from app.workers.tasks import celery_app

            worker = "ready" if celery_app.control.inspect(timeout=0.3).ping() else "unavailable"
        except Exception:
            worker = "unavailable"
    artifacts = "ready"
    if settings.free_dna_v61_enabled and not service.v61_supporting_artifacts:
        artifacts = "fixture" if settings.app_env != "production" else "unavailable"
    auth = "not_required"
    if settings.free_dna_v61_enabled:
        auth = "ready" if service.v61_supporting_artifacts.get("production_beta_authorization") else (
            "not_required" if settings.app_env != "production" else "unavailable"
        )
    ready = (
        postgres != "unavailable"
        and redis_status != "unavailable"
        and worker != "unavailable"
        and artifacts in {"ready", "fixture"}
        and auth in {"ready", "not_required"}
    )
    return {
        "ready": ready,
        "api": "ok",
        "postgres": postgres,
        "redis": redis_status,
        "worker": worker,
        "auth": auth,
        "source": settings.opendota_source,
        "artifacts": artifacts,
    }


def _health_response(payload: dict[str, Any]) -> dict[str, str]:
    return {
        "status": "ok" if payload["ready"] else "not_ready",
        "api": str(payload["api"]),
        "postgres": str(payload["postgres"]),
        "redis": str(payload["redis"]),
        "worker": str(payload["worker"]),
        "artifacts": str(payload["artifacts"]),
        "auth": str(payload["auth"]),
        "source": str(payload["source"]),
    }


app = create_app()
