"""Read-only tracker operations surface, isolated from mobile and legacy APIs."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import Engine, distinct, func, select

from app.core.config import Settings
from app.storage.database import create_database_engine
from app.tracker.schema import account_matches, coverage, ingest_jobs, matches, provider_calls


class QueueView(BaseModel):
    priority: int
    depth: int
    oldest_seconds: float
    failed: int


class ProviderView(BaseModel):
    name: str
    operation: str
    calls: int
    unique_matches: int
    errors: int
    rate_limited: int
    billed_units: int
    rate_units: int


class CoverageView(BaseModel):
    mode: str
    capability: str
    state: str
    intervals: int


class LatencyView(BaseModel):
    stage: str
    count: int
    p50_seconds: float | None
    p90_seconds: float | None
    p99_seconds: float | None


class OperationsView(BaseModel):
    queues: list[QueueView]
    providers: list[ProviderView]
    coverage: list[CoverageView]
    latency: list[LatencyView]


def create_operations_app(settings: Settings, *, database: Engine | None = None,
                          token: str | None = None) -> FastAPI:
    app = FastAPI(title="Tracker Operations", version="1.0.0")
    app.state.database = database

    def authorize(header: Annotated[str | None, Header(alias="X-Tracker-Operations-Token")] = None) -> None:
        if not token:
            raise HTTPException(503, "operations auth is not configured")
        if not header or not hmac.compare_digest(header, token):
            raise HTTPException(401, "operations auth required")

    @app.get("/summary", response_model=OperationsView, dependencies=[Depends(authorize)])
    async def summary(request: Request) -> OperationsView:
        from app.tracker.worker import queue_metrics

        engine = app.state.database
        if engine is None:
            engine = create_database_engine(settings)
            app.state.database = engine
        depth = queue_metrics(engine)
        with engine.connect() as connection:
            failed = dict(connection.execute(select(
                ingest_jobs.c.priority, func.count(),
            ).where(ingest_jobs.c.state == "FAILED").group_by(ingest_jobs.c.priority)).all())
            calls = connection.execute(select(
                provider_calls.c.provider, provider_calls.c.operation,
                func.count(), func.count(distinct(provider_calls.c.match_id)),
                func.count().filter(provider_calls.c.failure_code.is_not(None)),
                func.count().filter(provider_calls.c.status == 429),
                func.coalesce(func.sum(provider_calls.c.billed_units), 0),
                func.coalesce(func.sum(provider_calls.c.rate_units), 0),
            ).group_by(provider_calls.c.provider, provider_calls.c.operation)).all()
            spans = connection.execute(select(
                coverage.c.mode, coverage.c.evidence_class, coverage.c.state, func.count(),
            ).group_by(coverage.c.mode, coverage.c.evidence_class, coverage.c.state)).all()
            summary_time = func.extract("epoch", matches.c.summary_ready_at - matches.c.discovered_at)
            replay_time = func.extract("epoch", matches.c.replay_terminal_at - matches.c.summary_ready_at)
            analysis_time = (func.extract("epoch", account_matches.c.finalized_at - matches.c.started_at)
                             - matches.c.duration_seconds)
            latencies = []
            for label, source, table in (
                ("SUMMARY", summary_time, matches),
                ("DETAILED", replay_time, matches),
                ("ANALYSIS", analysis_time, account_matches.join(matches)),
            ):
                row = connection.execute(select(
                    func.count(source),
                    func.percentile_cont(0.5).within_group(source),
                    func.percentile_cont(0.9).within_group(source),
                    func.percentile_cont(0.99).within_group(source),
                ).select_from(table).where(source.is_not(None))).one()
                latencies.append(LatencyView(stage=label, count=row[0],
                    p50_seconds=float(row[1]) if row[1] is not None else None,
                    p90_seconds=float(row[2]) if row[2] is not None else None,
                    p99_seconds=float(row[3]) if row[3] is not None else None))
        return OperationsView(
            queues=[QueueView(priority=p, depth=int(depth[p]["depth"]),
                              oldest_seconds=float(depth[p]["oldest_seconds"]),
                              failed=failed.get(p, 0)) for p in range(4)],
            providers=[ProviderView(name=name, operation=operation, calls=count,
                                    unique_matches=unique, errors=errors, rate_limited=limited,
                                    billed_units=billed, rate_units=units)
                       for name, operation, count, unique, errors, limited, billed, units in calls],
            coverage=[CoverageView(mode=mode, capability=capability, state=state, intervals=count)
                      for mode, capability, state, count in spans],
            latency=latencies,
        )

    return app
