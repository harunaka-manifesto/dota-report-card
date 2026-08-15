from __future__ import annotations

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
from app.features.models import MatchFeature
from app.opendota.client import OpenDotaClient
from app.storage.repository import InMemoryRepository, SqlAlchemyRepository


def create_app(
    settings: Settings | None = None,
    *,
    source: Any | None = None,
    repository: Any | None = None,
    cohort_population: Iterable[MatchFeature] = (),
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, (settings.opendota_api_key,))
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
            else InMemoryRepository()
        )
    service = AnalysisService(
        cast(AnalysisSource, source),
        repository=repository,
        settings=settings,
        cohort_population=cohort_population,
    )
    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> Any:
        if isinstance(source, OpenDotaClient):
            await source.__aenter__()
        try:
            yield
        finally:
            await service.shutdown()
            if isinstance(source, OpenDotaClient):
                await source.aclose()

    app = FastAPI(
        title="OpenDota Insight System",
        version="1.0.0",
        description="Deterministic, evidence-backed player reports.",
        lifespan=lifespan,
    )
    app.state.analysis_service = service
    app.state.settings = settings
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "Accept", "Authorization"],
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
        return {
            "status": "ok",
            "api": "ok",
            "postgres": settings.effective_storage_backend,
            "redis": "configured"
            if settings.effective_analysis_execution_backend == "celery"
            else "not_configured",
            "worker": settings.effective_analysis_execution_backend,
            "source": settings.opendota_source,
        }

    app.include_router(router)
    return app


app = create_app()
