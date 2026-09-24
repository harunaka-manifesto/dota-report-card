"""Database-owned scheduling and leases. Celery deliveries only wake a worker."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, Engine, and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from app.tracker.evidence import canonical_json
from app.tracker.schema import ingest_jobs, profiles, users


class StaleJob(Exception):
    """The lease or its user/profile generation no longer authorizes writes."""


def enqueue(
    connection: Connection, *, dedup_key: str, job_type: str, priority: int,
    payload: dict[str, Any], run_after: datetime | None = None,
    match_id: int | None = None, account_id: int | None = None,
    profile_id: str | None = None,
) -> str:
    if type(priority) is not int or priority not in range(4):
        raise ValueError("Invalid job priority")
    if not dedup_key or len(dedup_key) > 240 or not job_type or len(job_type) > 64:
        raise ValueError("Invalid job identity")
    if run_after is not None and run_after.utcoffset() is None:
        raise ValueError("Job schedule must have a timezone")
    canonical_json(payload)
    values: dict[str, Any] = {}
    if profile_id is not None:
        profile = connection.execute(select(profiles).where(profiles.c.id == profile_id)).mappings().one()
        user = connection.execute(select(users).where(users.c.id == profile["user_id"])).mappings().one()
        if not profile["active"] or user["state"] != "ACTIVE":
            raise StaleJob("Inactive job owner")
        if account_id is not None and account_id != profile["account_id"]:
            raise ValueError("Job account does not match its profile")
        account_id = profile["account_id"]
        values.update(user_id=user["id"], user_generation=user["generation"], profile_id=profile_id, profile_generation=profile["generation"])
    job_id = str(uuid4())
    saved = connection.execute(insert(ingest_jobs).values(
        id=job_id, dedup_key=dedup_key, job_type=job_type, priority=priority,
        payload=payload, run_after=run_after or func.now(), created_at=func.now(),
        match_id=match_id, account_id=account_id, **values,
    ).on_conflict_do_nothing(index_elements=[ingest_jobs.c.dedup_key]).returning(ingest_jobs.c.id)).scalar_one_or_none()
    if saved is not None:
        return saved
    existing = connection.execute(select(ingest_jobs).where(ingest_jobs.c.dedup_key == dedup_key)).mappings().one()
    if any(existing[key] != value for key, value in {
        "job_type": job_type, "match_id": match_id, "account_id": account_id,
        "profile_id": profile_id, "payload": payload, **values,
    }.items()):
        raise ValueError("Job dedup key reused for different work")
    return existing["id"]


def claim(connection: Connection, *, priority: int, lease_seconds: int = 120, paused: bool = False) -> dict[str, Any] | None:
    if type(priority) is not int or priority not in range(4) or type(lease_seconds) is not int or lease_seconds < 1:
        raise ValueError("Invalid claim policy")
    if paused:
        return None
    now = connection.execute(select(func.clock_timestamp())).scalar_one()
    row = connection.execute(select(ingest_jobs).where(
        ingest_jobs.c.priority == priority,
        or_(
            and_(ingest_jobs.c.state == "PENDING", ingest_jobs.c.run_after <= now),
            and_(ingest_jobs.c.state == "RUNNING", ingest_jobs.c.lease_until <= now),
        ),
    ).order_by(ingest_jobs.c.run_after, ingest_jobs.c.created_at, ingest_jobs.c.id).with_for_update(skip_locked=True).limit(1)).mappings().first()
    if row is None:
        return None
    return dict(connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == row["id"]).values(
        state="RUNNING", lease_token=str(uuid4()), lease_until=now + timedelta(seconds=lease_seconds),
        attempts=ingest_jobs.c.attempts + 1,
    ).returning(ingest_jobs)).mappings().one())


@contextmanager
def authorized_job(database: Engine, job_id: str, lease_token: str) -> Iterator[tuple[Connection, dict[str, Any]]]:
    """Publish effects and finish/checkpoint work inside this fenced transaction.

    Lock order is user, profile, job. Deletion/switching must use the same order.
    Provider I/O must happen outside this transaction; late results may be stored
    as shared evidence but cannot publish private effects after this guard fails.
    """
    with database.begin() as connection:
        before = connection.execute(select(ingest_jobs).where(ingest_jobs.c.id == job_id)).mappings().first()
        if before is None:
            raise StaleJob("Job no longer exists")
        if before["user_id"] is not None:
            user = connection.execute(select(users).where(users.c.id == before["user_id"]).with_for_update()).mappings().first()
            if user is None or user["state"] != "ACTIVE" or user["generation"] != before["user_generation"]:
                raise StaleJob("User generation changed")
        if before["profile_id"] is not None:
            profile = connection.execute(select(profiles).where(profiles.c.id == before["profile_id"]).with_for_update()).mappings().first()
            if profile is None or not profile["active"] or profile["generation"] != before["profile_generation"]:
                raise StaleJob("Profile generation changed")
        row = connection.execute(select(ingest_jobs).where(ingest_jobs.c.id == job_id).with_for_update()).mappings().first()
        now = connection.execute(select(func.clock_timestamp())).scalar_one()
        if row is None or row["state"] != "RUNNING" or row["lease_token"] != lease_token or row["lease_until"] <= now:
            raise StaleJob("Job lease lost")
        yield connection, dict(row)


def finish(connection: Connection, job: dict[str, Any]) -> None:
    connection.execute(ingest_jobs.update().where(
        ingest_jobs.c.id == job["id"], ingest_jobs.c.lease_token == job["lease_token"],
        ingest_jobs.c.state == "RUNNING",
    ).values(state="COMPLETE", lease_token=None, lease_until=None, last_error=None))


def reschedule(
    connection: Connection, job: dict[str, Any], *, delay_seconds: float,
    error: str, cursor: dict[str, Any] | None = None, failure: bool = True,
    max_attempts: int = 5,
) -> None:
    if delay_seconds < 0 or len(error) > 64 or max_attempts < 1:
        raise ValueError("Invalid retry policy")
    values: dict[str, Any] = dict(
        state="FAILED" if failure and job["attempts"] >= max_attempts else "PENDING",
        run_after=func.clock_timestamp() + timedelta(seconds=delay_seconds),
        lease_token=None, lease_until=None, last_error=error,
    )
    if cursor is not None:
        canonical_json(cursor)
        values["cursor"] = cursor
    if failure and job["priority"] < 2:
        values["priority"] = 2
    if not failure:
        values["attempts"] = max(0, job["attempts"] - 1)
    connection.execute(ingest_jobs.update().where(
        ingest_jobs.c.id == job["id"], ingest_jobs.c.lease_token == job["lease_token"],
        ingest_jobs.c.state == "RUNNING",
    ).values(**values))
