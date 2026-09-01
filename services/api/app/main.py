from __future__ import annotations

import asyncio
from collections.abc import Iterable
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.analysis.service import AnalysisService
from app.analysis.source import FixtureOpenDotaSource, OpenDotaAnalysisSource
from app.api.routes import router
from app.core.cache import RedisCache
from app.core.config import Settings, get_settings, validate_runtime_configuration
from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.metrics import record_metric
from app.core.release import build_release_identity
from app.core.security import RateLimiter
from app.features.models import MatchFeature
from app.identity.steam import SteamWebResolver
from app.opendota.client import OpenDotaClient
from app.opendota.parse_client import OpenDotaParseClient
from app.providers import build_v7_provider
from app.storage.repository import InMemoryRepository, SqlAlchemyRepository


def create_app(
    settings: Settings | None = None,
    *,
    source: Any | None = None,
    repository: Any | None = None,
    cohort_population: Iterable[MatchFeature] = (),
) -> FastAPI:
    settings = settings or get_settings()
    validate_runtime_configuration(settings)
    configure_logging(
        settings.log_level,
        (settings.opendota_api_key, settings.steam_api_key, settings.stratz_api_token),
    )
    if source is None:
        source = (
            FixtureOpenDotaSource(settings.effective_fixture_dir)
            if settings.opendota_source == "fixture"
            else OpenDotaClient(settings)
        )
    if settings.app_env == "production" and isinstance(source, FixtureOpenDotaSource):
        raise ValueError("fixture OpenDota source is not allowed in production")
    # V7 has its own provider seam; the existing AnalysisService remains the
    # OpenDota/V6.1 runtime until a V7 assembler is introduced.
    v7_provider = build_v7_provider(settings)
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
        cast(OpenDotaAnalysisSource, source),
        repository=repository,
        settings=settings,
        cohort_population=cohort_population,
        identity_resolver=identity_resolver,
        parse_transport=parse_transport,
    )
    def app_readiness() -> dict[str, Any]:
        return _readiness_payload(settings, repository, service)
    def app_release() -> dict[str, Any]:
        return _release_payload(settings, repository, service)
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
            if v7_provider is not None:
                await v7_provider.aclose()
            if identity_resolver is not None:
                await identity_resolver.aclose()

    app = FastAPI(
        title="OpenDota Insight System",
        version="1.0.0",
        description="Deterministic, evidence-backed player reports.",
        lifespan=lifespan,
    )
    app.state.analysis_service = service
    app.state.v7_provider = v7_provider
    app.state.data_provider = settings.data_provider
    app.state.settings = settings
    app.state.readiness = app_readiness
    app.state.release_identity = app_release
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

    @app.get("/health/release")
    async def root_release() -> dict[str, Any]:
        return app_release()

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


def _release_payload(settings: Settings, repository: Any, service: AnalysisService) -> dict[str, Any]:
    return {
        "release": build_release_identity(
            settings,
            artifact_checksums=service.v61_artifact_checksums,
            artifact_manifest=service.v61_supporting_artifacts.get("manifest"),
            authorization_checksum=service.v61_authorization_checksum,
            db_revision=_current_database_revision(repository),
        )
    }


def _current_database_revision(repository: Any) -> str | None:
    checker = getattr(repository, "current_revision", None)
    if checker is None:
        return None
    try:
        value = checker()
    except Exception:
        return None
    return str(value) if value is not None else None


def _worker_release_identity() -> tuple[str, dict[str, Any] | None]:
    try:
        from app.workers.tasks import celery_app

        if not celery_app.control.inspect(timeout=0.3).ping():
            return "unavailable", None
        result = celery_app.send_task("dota_report_card.release_identity")
        value = result.get(timeout=0.5)
        if not isinstance(value, dict):
            return "unavailable", None
        return "ready", value
    except Exception:
        return "unavailable", None


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
    worker_release: dict[str, Any] | None = None
    release_parity = "not_required"
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
        worker, worker_release = _worker_release_identity()
        if worker == "ready":
            api_release = _release_payload(settings, repository, service)["release"]
            release_parity = "match" if worker_release == api_release else "mismatch"
        else:
            release_parity = "unavailable"
    artifacts = "ready"
    if settings.free_dna_v61_enabled and not service.v61_supporting_artifacts:
        artifacts = "fixture" if settings.app_env != "production" else "unavailable"
    auth = "not_required"
    if settings.free_dna_v61_enabled:
        auth = "ready" if service.v61_supporting_artifacts.get("production_beta_authorization") else (
            "not_required" if settings.app_env != "production" else "unavailable"
        )
    release = _release_payload(settings, repository, service)["release"]
    ready = (
        postgres != "unavailable"
        and redis_status != "unavailable"
        and worker != "unavailable"
        and artifacts in ({"ready"} if settings.app_env == "production" else {"ready", "fixture"})
        and auth in {"ready", "not_required"}
        and release_parity in {"not_required", "match"}
        and (settings.app_env != "production" or settings.opendota_source == "live")
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
        "release": release,
        "worker_release": worker_release,
        "release_parity": release_parity,
    }


def _health_response(payload: dict[str, Any]) -> dict[str, Any]:
    response: dict[str, Any] = {
        "status": "ok" if payload["ready"] else "not_ready",
        "api": str(payload["api"]),
        "postgres": str(payload["postgres"]),
        "redis": str(payload["redis"]),
        "worker": str(payload["worker"]),
        "artifacts": str(payload["artifacts"]),
        "auth": str(payload["auth"]),
        "source": str(payload["source"]),
    }
    if "release" in payload:
        response["release"] = payload["release"]
        response["worker_release"] = payload.get("worker_release")
        response["release_parity"] = str(payload.get("release_parity", "not_required"))
    return response


app = create_app()
