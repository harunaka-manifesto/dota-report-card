"""Dedicated Celery priority lanes; PostgreSQL owns all scheduling and leases."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx
from celery import Celery
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from redis import Redis
from sqlalchemy import Engine, and_, func, or_, select

from app.core.config import Settings, get_settings
from app.storage.database import check_database_revision, create_database_engine
from app.tracker.acquisition import acquire_fresh_summary
from app.tracker.historical import acquire_historical_batch
from app.tracker.jobs import StaleJob, authorized_job, claim, reschedule
from app.tracker.linking import complete_link_job, complete_role_job
from app.tracker.provider_control import ProviderGate
from app.tracker.replay_acquisition import acquire_fresh_replay
from app.tracker.schema import ingest_jobs
from app.tracker.sync import sync_account_page


class WorkerPolicy(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TRACKER_")
    namespace: str = Field(default="tracker", min_length=1)
    p1_depth_limit: int = Field(default=100, ge=1)
    p1_age_seconds: int = Field(default=60, ge=1)
    quota_utilization_limit: float = Field(default=0.8, gt=0, lt=1)
    p2_pressure_interval_seconds: int = Field(default=5, ge=1)
    replay_delay_seconds: int = Field(default=360, ge=1)


def queue_metrics(database: Engine) -> dict[int, dict[str, float | int]]:
    """Due work only: a scheduled replay wait is not a queue-latency incident."""
    with database.connect() as connection:
        now = connection.execute(select(func.clock_timestamp())).scalar_one()
        rows = connection.execute(select(ingest_jobs.c.priority, func.count(), func.min(ingest_jobs.c.run_after)).where(
            or_(and_(ingest_jobs.c.state == "PENDING", ingest_jobs.c.run_after <= now), ingest_jobs.c.state == "RUNNING"),
        ).group_by(ingest_jobs.c.priority)).all()
    result: dict[int, dict[str, float | int]] = {p: {"depth": 0, "oldest_seconds": 0.0} for p in range(4)}
    for priority, count, oldest in rows:
        result[priority] = {"depth": count, "oldest_seconds": max(0.0, (now - oldest).total_seconds())}
    return result


def admission(database: Engine, redis: Redis, priority: int, policy: WorkerPolicy) -> str | None:
    if type(priority) is not int or priority not in range(4):
        raise ValueError("Invalid worker priority")
    if priority < 2:
        return None
    if priority == 3 and redis.get(f"{policy.namespace}:pause:p3"):
        return "OPERATOR_PAUSED"
    p1 = queue_metrics(database)[1]
    reason = "P1_DEPTH" if p1["depth"] >= policy.p1_depth_limit else "P1_AGE" if p1["oldest_seconds"] >= policy.p1_age_seconds else None
    if reason is None:
        for provider in ("opendota", "stratz"):
            utilization = ProviderGate(redis, namespace=policy.namespace, provider=provider).utilization()
            if utilization is None or utilization >= policy.quota_utilization_limit:
                reason = "PROVIDER_BUDGET"
                break
    if priority == 3:
        return reason
    if reason and not redis.set(f"{policy.namespace}:p2-pressure-slot", "1", nx=True, ex=policy.p2_pressure_interval_seconds):
        return "P2_REDUCED_SHARE"
    return None


async def run_one(database: Engine, redis: Redis, settings: Settings, *, priority: int, policy: WorkerPolicy,
                  transport: httpx.AsyncBaseTransport | None = None) -> str:
    reason = admission(database, redis, priority, policy)
    if reason:
        return reason
    with database.begin() as connection:
        job = claim(connection, priority=priority)
    if job is None:
        return "IDLE"
    args: dict[str, Any] = dict(job_id=job["id"], lease_token=job["lease_token"])
    gate = ProviderGate(redis, namespace=policy.namespace, provider="opendota")
    try:
        if job["job_type"] == "ROLE_REFRESH":
            return complete_role_job(database, **args)
        if job["job_type"] == "LINK_MATCH":
            complete_link_job(database, **args, replay_delay_seconds=policy.replay_delay_seconds)
            return "COMPLETE"
        if job["job_type"] == "SYNC":
            return await sync_account_page(database, gate, settings, **args, transport=transport)
        if job["job_type"] == "SUMMARY":
            return await acquire_fresh_summary(database, gate, settings, **args, transport=transport)
        if job["job_type"] == "REPLAY":
            return await acquire_fresh_replay(database, gate, settings, **args, transport=transport)
        if job["job_type"] == "HISTORICAL_BATCH":
            historical_gate = ProviderGate(redis, namespace=policy.namespace, provider="stratz")
            return await acquire_historical_batch(database, historical_gate, settings, **args, transport=transport)
        raise ValueError("Unsupported tracker job type")
    except StaleJob:
        return "STALE"
    except Exception:
        # Persist handler failures; broker retries are not a second scheduler.
        try:
            with authorized_job(database, **args) as (connection, current):
                reschedule(connection, current, delay_seconds=30, error="WORKER_FAILED")
        except StaleJob:
            return "STALE"
        return "FAILED" if job["attempts"] >= 5 else "DEFERRED"


def create_worker_app(settings: Settings) -> Celery:
    app = Celery("dota-tracker", broker=settings.redis_url)
    app.conf.update(
        task_default_queue="tracker-control", task_serializer="json", accept_content=["json"],
        task_acks_late=True, task_reject_on_worker_lost=True, worker_prefetch_multiplier=1,
        task_ignore_result=True, task_create_missing_queues=True,
        task_soft_time_limit=90, task_time_limit=110,
        broker_transport_options={"visibility_timeout": 300},
        beat_schedule={f"tracker-wake-p{p}": {"task": "tracker.wake", "schedule": 5.0,
                       "args": [p], "options": {"queue": f"tracker-p{p}", "expires": 10}} for p in range(4)},
    )

    @app.task(name="tracker.wake", shared=False, bind=True)
    def wake(task: Any, priority: int) -> str:
        # One bounded step, no provider polling loops or long broker countdowns.
        database = create_database_engine(settings)
        redis = Redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=2)
        try:
            check_database_revision(database)
            result = asyncio.run(run_one(database, redis, settings, priority=priority, policy=WorkerPolicy()))
            logging.getLogger(__name__).info("tracker_worker priority=%s outcome=%s", priority, result)
            if result in {"COMPLETE", "DEFERRED", "FAILED"}:
                with database.connect() as connection:
                    due = connection.scalar(select(ingest_jobs.c.id).where(
                        ingest_jobs.c.priority == priority, ingest_jobs.c.state == "PENDING",
                        ingest_jobs.c.run_after <= func.clock_timestamp(),
                    ).limit(1))
                if due is not None:
                    app.send_task("tracker.wake", args=[priority], queue=task.request.delivery_info.get("routing_key") or f"tracker-p{priority}", expires=10)
            return result
        finally:
            redis.close()
            database.dispose()

    return app


celery_app = create_worker_app(get_settings())
