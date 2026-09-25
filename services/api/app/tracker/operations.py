"""Read-only tracker operations surface, isolated from mobile and legacy APIs."""

from __future__ import annotations

import hmac
import json
import math
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel
from redis import Redis, RedisError
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


class ProviderControlView(BaseModel):
    name: str
    state: str
    open_seconds: float
    failure_code: str | None


class FailureView(BaseModel):
    source: str
    reason: str
    count: int


class RetryView(BaseModel):
    job_type: str
    attempted: int
    retried: int


class UsageAttributionView(BaseModel):
    provider: str
    operation: str
    job_type: str | None
    priority: int | None
    calls: int
    billed_units: int
    rate_units: int


class OperationsView(BaseModel):
    queues: list[QueueView]
    providers: list[ProviderView]
    coverage: list[CoverageView]
    latency: list[LatencyView]
    provider_control: list[ProviderControlView]
    p3_paused: bool | None
    failures: list[FailureView]
    retries: list[RetryView]
    usage_attribution: list[UsageAttributionView]


def create_operations_app(settings: Settings, *, database: Engine | None = None,
                          token: str | None = None, redis: Redis | None = None) -> FastAPI:
    app = FastAPI(title="Tracker Operations", version="1.0.0")
    app.state.database = database
    app.state.redis = redis

    def authorize(header: Annotated[str | None, Header(alias="X-Tracker-Operations-Token")] = None) -> None:
        if not token:
            raise HTTPException(503, "operations auth is not configured")
        if not header or not hmac.compare_digest(header, token):
            raise HTTPException(401, "operations auth required")

    @app.get("/summary", response_model=OperationsView, dependencies=[Depends(authorize)])
    async def summary(request: Request) -> OperationsView:
        from app.tracker.worker import WorkerPolicy, queue_metrics

        engine = app.state.database
        if engine is None:
            engine = create_database_engine(settings)
            app.state.database = engine
        depth = queue_metrics(engine)
        with engine.connect() as connection:
            failed = dict(connection.execute(select(
                ingest_jobs.c.priority, func.count(),
            ).where(ingest_jobs.c.state == "FAILED").group_by(ingest_jobs.c.priority)).all())
            job_failures = connection.execute(select(
                ingest_jobs.c.job_type, ingest_jobs.c.last_error, func.count(),
            ).where(ingest_jobs.c.last_error.is_not(None)).group_by(
                ingest_jobs.c.job_type, ingest_jobs.c.last_error,
            )).all()
            replay_failures = connection.execute(select(
                matches.c.terminal_reason, func.count(),
            ).where(matches.c.evidence_state == "REPLAY_UNAVAILABLE").group_by(
                matches.c.terminal_reason,
            )).all()
            retry_counts = connection.execute(select(
                ingest_jobs.c.job_type, func.count().filter(ingest_jobs.c.attempts > 0),
                func.count().filter(ingest_jobs.c.attempts > 1),
            ).group_by(ingest_jobs.c.job_type)).all()
            calls = connection.execute(select(
                provider_calls.c.provider, provider_calls.c.operation,
                func.count(), func.count(distinct(provider_calls.c.match_id)),
                func.count().filter(provider_calls.c.failure_code.is_not(None)),
                func.count().filter(provider_calls.c.status == 429),
                func.coalesce(func.sum(provider_calls.c.billed_units), 0),
                func.coalesce(func.sum(provider_calls.c.rate_units), 0),
            ).group_by(provider_calls.c.provider, provider_calls.c.operation)).all()
            usage = connection.execute(select(
                provider_calls.c.provider, provider_calls.c.operation,
                ingest_jobs.c.job_type, ingest_jobs.c.priority, func.count(),
                func.coalesce(func.sum(provider_calls.c.billed_units), 0),
                func.coalesce(func.sum(provider_calls.c.rate_units), 0),
            ).select_from(provider_calls.outerjoin(
                ingest_jobs, provider_calls.c.job_id == ingest_jobs.c.id,
            )).group_by(provider_calls.c.provider, provider_calls.c.operation,
                        ingest_jobs.c.job_type, ingest_jobs.c.priority)).all()
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
        namespace = WorkerPolicy().namespace
        redis_client = app.state.redis
        if redis_client is None:
            redis_client = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1)
            app.state.redis = redis_client
        control: list[ProviderControlView] = []
        p3_paused: bool | None
        try:
            seconds, micros = redis_client.time()
            now = seconds + micros / 1_000_000
            p3_paused = bool(redis_client.get(f"{namespace}:pause:p3"))
            for name in ("opendota", "stratz"):
                raw = redis_client.get(f"{namespace}:provider:{name}")
                state = json.loads(raw) if raw else None
                if not isinstance(state, dict):
                    control.append(ProviderControlView(name=name, state="UNKNOWN", open_seconds=0,
                                                       failure_code=None))
                    continue
                open_until = float(state.get("open_until", 0))
                if not math.isfinite(open_until):
                    raise ValueError("invalid circuit deadline")
                remaining = max(0.0, open_until - now)
                control.append(ProviderControlView(
                    name=name,
                    state="DISABLED" if state.get("disabled") else "OPEN" if remaining else "CLOSED",
                    open_seconds=remaining,
                    failure_code=state.get("failure_code") if isinstance(state.get("failure_code"), str) else None,
                ))
        except (RedisError, ValueError, TypeError):
            p3_paused = None
            control = [ProviderControlView(name=name, state="UNAVAILABLE", open_seconds=0,
                                           failure_code=None) for name in ("opendota", "stratz")]
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
            provider_control=control, p3_paused=p3_paused,
            failures=[FailureView(source=f"JOB:{kind}", reason=reason, count=count)
                      for kind, reason, count in job_failures] + [
                FailureView(source="REPLAY", reason=reason, count=count)
                for reason, count in replay_failures
            ],
            retries=[RetryView(job_type=kind, attempted=attempted, retried=retried)
                     for kind, attempted, retried in retry_counts],
            usage_attribution=[UsageAttributionView(
                provider=provider, operation=operation, job_type=kind, priority=priority,
                calls=count, billed_units=billed, rate_units=units,
            ) for provider, operation, kind, priority, count, billed, units in usage],
        )

    return app
