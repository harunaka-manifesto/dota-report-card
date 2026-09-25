"""Pro historical backfill: more P3 work of the same kind (settings §5.0 E-3).

A purchase requests one profile-generation-scoped scan of the account's
Turbo-inclusive history before the original link date, bounded by a configured
depth ceiling. Each page journals nothing new; it only queues the same
historical batches bootstrap uses (origin HISTORICAL) for matches this profile
does not already hold. Resubscription reuses the completed job for the profile
generation, so retained coverage is never refetched (E-4).

The Pro depth ceiling is an open owner decision (goal §1.4). With no configured
ceiling no backfill is requested and activation proceeds from retained data.
"""
from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import Connection, Engine, func, select

from app.core.config import Settings
from app.core.errors import OpenDotaRateLimited, OpenDotaUnavailable
from app.opendota.client import OpenDotaClient
from app.tracker.historical import enqueue_historical_batch
from app.tracker.jobs import StaleJob, authorized_job, enqueue, finish, reschedule
from app.tracker.provider_control import ProviderDeferred, ProviderGate
from app.tracker.provider_transport import ControlledTransport
from app.tracker.schema import account_matches, ingest_jobs, profiles, users
from app.tracker.sync import _saved_page

HISTORICAL_WORK = ("PRO_BACKFILL", "ACCESS_RECOVERY", "HISTORICAL_BATCH", "HISTORICAL_SUMMARY")
SCANS = {"PRO_BACKFILL": ("PRE_LINK", "HISTORICAL"), "ACCESS_RECOVERY": ("POST_LINK", "RECOVERY")}


def pro_history_days() -> int | None:
    value = os.getenv("TRACKER_PRO_HISTORY_DAYS")
    if not value:
        return None
    days = int(value)
    if days < 1:
        raise ValueError("TRACKER_PRO_HISTORY_DAYS must be positive")
    return days


def request_pro_backfill(connection: Connection, profile_id: str, *, ceiling_days: int | None) -> str | None:
    if ceiling_days is None:
        return None
    owner = connection.execute(select(profiles.c.generation, users.c.generation.label("user_generation")).join(
        users, users.c.id == profiles.c.user_id).where(profiles.c.id == profile_id)).mappings().one()
    return enqueue(connection, dedup_key=f"pro-backfill:{profile_id}:{owner['generation']}:{owner['user_generation']}",
                   job_type="PRO_BACKFILL", priority=3, profile_id=profile_id,
                   payload={"ceiling_days": ceiling_days})


def request_access_recovery(connection: Connection, profile_id: str, *, episode: str) -> str:
    """Recover eligible post-link history once data access is restored (onboarding §8).

    The window is anchored to the original link date, never a later one.
    """
    owner = connection.execute(select(profiles.c.generation, profiles.c.original_linked_at,
                                      users.c.generation.label("user_generation")).join(
        users, users.c.id == profiles.c.user_id).where(profiles.c.id == profile_id)).mappings().one()
    now = connection.execute(select(func.clock_timestamp())).scalar_one()
    days = max(1, (now - owner["original_linked_at"]).days + 1)
    return enqueue(connection, dedup_key=f"access-recovery:{profile_id}:{owner['generation']}:{episode}",
                   job_type="ACCESS_RECOVERY", priority=3, profile_id=profile_id,
                   payload={"ceiling_days": days})


def historical_work_pending(connection: Connection, profile_id: str) -> bool:
    """Acquisition or analysis of pre-link history is still settling."""
    job = connection.scalar(select(ingest_jobs.c.id).where(
        ingest_jobs.c.profile_id == profile_id, ingest_jobs.c.job_type.in_(HISTORICAL_WORK),
        ingest_jobs.c.state.in_(("PENDING", "RUNNING")),
    ).limit(1))
    link = connection.scalar(select(account_matches.c.match_id).where(
        account_matches.c.profile_id == profile_id, account_matches.c.origin == "HISTORICAL",
        account_matches.c.lifecycle.in_(("WAITING_FOR_PROVIDER", "ANALYZING", "WAITING_FOR_PRIOR_MATCH")),
    ).limit(1))
    return job is not None or link is not None


def _publish_page(connection: Connection, job: dict[str, Any], snapshot: dict[str, Any], *,
                  max_pages: int) -> str:
    rows = snapshot["payload"]
    if not isinstance(rows, list) or len(rows) > 200:
        raise ValueError("Invalid backfill history page")
    linked_at = connection.scalar(select(profiles.c.original_linked_at).where(
        profiles.c.id == job["profile_id"]).with_for_update())
    if linked_at is None:
        raise StaleJob("Backfill profile vanished")
    window, origin = SCANS[job["job_type"]]
    floor = job["created_at"] - timedelta(days=job["payload"]["ceiling_days"])
    cursor = dict(job["cursor"] or {})
    held = set(connection.scalars(select(account_matches.c.match_id).where(
        account_matches.c.profile_id == job["profile_id"])))
    wanted: list[int] = []
    crossed_floor = False
    for raw in rows:
        if not isinstance(raw, dict) or type(raw.get("match_id")) is not int or not 0 < raw["match_id"] < 2**63:
            raise ValueError("Invalid backfill history item")
        timestamp = raw.get("start_time")
        if type(timestamp) is not int or not 0 < timestamp <= 253402300799:
            continue
        started_at = datetime.fromtimestamp(timestamp, UTC)
        if started_at < floor:
            crossed_floor = True
            continue
        game_mode = raw.get("game_mode")
        supported = type(game_mode) is int and game_mode in (1, 22, 23)
        in_window = started_at < linked_at if window == "PRE_LINK" else started_at >= linked_at
        if in_window and supported and raw["match_id"] not in held:
            wanted.append(raw["match_id"])
    for start in range(0, len(wanted), 50):
        enqueue_historical_batch(connection, profile_id=job["profile_id"], match_ids=wanted[start:start + 50],
                                 origin=origin)
    pages = cursor.get("pages", 0) + 1
    next_cursor = {"offset": cursor.get("offset", 0) + len(rows), "pages": pages,
                   "request_days": cursor["request_days"], "queued": cursor.get("queued", 0) + len(wanted)}
    if not rows or crossed_floor:
        connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == job["id"]).values(cursor=next_cursor))
        finish(connection, job)
        return "COMPLETE"
    if pages >= max_pages:
        reschedule(connection, job, delay_seconds=0, error="PAGINATION_LIMIT", cursor=next_cursor, max_attempts=1)
        return "FAILED"
    reschedule(connection, job, delay_seconds=0, error="NEXT_PAGE", cursor=next_cursor, failure=False)
    return "DEFERRED"


async def backfill_page(database: Engine, gate: ProviderGate, settings: Settings, *, job_id: str, lease_token: str,
                        transport: httpx.AsyncBaseTransport | None = None, max_pages: int = 200,
                        max_attempts: int = 5) -> str:
    with authorized_job(database, job_id, lease_token) as (connection, job):
        if job["job_type"] not in SCANS or job["profile_id"] is None:
            raise ValueError("Expected profile history scan work")
        cursor = dict(job["cursor"] or {})
        days = cursor.get("request_days", int(job["payload"]["ceiling_days"]) + 1)
        offset = cursor.get("offset", 0)
        request = httpx.Request("GET", f"{settings.opendota_base_url.rstrip('/')}/players/{job['account_id']}/matches",
                                params={"significant": 0, "limit": 200, "offset": offset, "date": days})
        subject = hashlib.sha256(request.url.raw_path + request.content).hexdigest()
        snapshot = _saved_page(connection, job_id, subject)
        if snapshot is None and cursor.get("request_lease_token") == lease_token:
            return "RUNNING"
    try:
        if snapshot is None:
            def before_send() -> None:
                with authorized_job(database, job_id, lease_token) as (connection, current):
                    if dict(current["cursor"] or {}) != cursor:
                        raise ProviderDeferred("BACKFILL_STEP_ALREADY_CLAIMED", 0.1)
                    connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(
                        cursor={**cursor, "request_days": days, "request_lease_token": lease_token}))

            controlled = ControlledTransport(gate, database, transport=transport, before_send=before_send, job_id=job_id)
            try:
                async with httpx.AsyncClient(transport=controlled) as http:
                    await OpenDotaClient(settings, http_client=http).get_history_page(job["account_id"], offset=offset, days=days)
            except OpenDotaUnavailable:
                with database.connect() as connection:
                    if _saved_page(connection, job_id, subject) is None:
                        raise
            with database.connect() as connection:
                snapshot = _saved_page(connection, job_id, subject)
            if snapshot is None:
                raise RuntimeError("Missing backfill history evidence")
        with authorized_job(database, job_id, lease_token) as (connection, current):
            current["cursor"] = {**(current["cursor"] or {}), "request_days": days}
            return _publish_page(connection, current, snapshot, max_pages=max_pages)
    except StaleJob:
        raise
    except Exception as exc:
        if isinstance(exc, ProviderDeferred) and exc.reason == "BACKFILL_STEP_ALREADY_CLAIMED":
            return "RUNNING"
        deferred = isinstance(exc, (ProviderDeferred, OpenDotaRateLimited))
        reason = exc.reason if isinstance(exc, ProviderDeferred) else "RATE_LIMITED" if isinstance(exc, OpenDotaRateLimited) else "BACKFILL_PAGE_FAILED"
        delay = exc.delay if isinstance(exc, ProviderDeferred) else 30
        with authorized_job(database, job_id, lease_token) as (connection, current):
            reschedule(connection, current, delay_seconds=delay, error=reason, failure=not deferred, max_attempts=max_attempts)
        return "DEFERRED" if deferred or current["attempts"] < max_attempts else "FAILED"

