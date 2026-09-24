"""Fresh summary acquisition: shared work, stored-response recovery, fenced publish."""
from __future__ import annotations

import asyncio
import hashlib
from typing import Any

import httpx
from redis.exceptions import LockNotOwnedError
from sqlalchemy import Connection, Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings
from app.core.errors import OpenDotaRateLimited, OpenDotaUnavailable, ProfileUnavailable
from app.opendota.client import OpenDotaClient
from app.tracker.evidence import canonical_json
from app.tracker.jobs import StaleJob, authorized_job, enqueue, finish, reschedule
from app.tracker.linking import enqueue_roster_links
from app.tracker.materialization import materialize_snapshot
from app.tracker.normalization import InvalidEvidence, opendota_summary, replay_available
from app.tracker.provider_control import ProviderDeferred, ProviderGate
from app.tracker.provider_transport import ControlledTransport
from app.tracker.schema import acquisitions, ingest_jobs, matches, provider_calls, snapshots


def enqueue_fresh_summary(connection: Connection, match_id: int) -> str:
    if type(match_id) is not int or not 0 < match_id < 2**63:
        raise ValueError("Invalid match ID")
    connection.execute(insert(matches).values(match_id=match_id, discovered_at=func.now()).on_conflict_do_nothing())
    return enqueue(connection, dedup_key=f"summary:{match_id}", job_type="SUMMARY", priority=0, payload={}, match_id=match_id)


def stored_match_snapshot(connection: Connection, match_id: int, *, replay_only: bool = False) -> str | None:
    # Query all matching inline responses; a malformed latest response must not
    # hide a valid earlier success or force another billable request.
    rows = connection.execute(select(snapshots.c.id, snapshots.c.payload).where(
        snapshots.c.provider == "opendota", snapshots.c.operation == "match",
        snapshots.c.operation_version == "1", snapshots.c.schema_version == "raw-1",
        snapshots.c.subject == f"match:{match_id}", snapshots.c.payload.is_not(None),
    ).order_by(snapshots.c.fetched_at.desc(), snapshots.c.id)).mappings()
    for row in rows:
        if not isinstance(row["payload"], dict) or row["payload"].get("match_id") != match_id:
            continue
        try:
            opendota_summary(row["payload"])
        except InvalidEvidence:
            continue
        if replay_only and not replay_available(row["payload"], "opendota"):
            continue
        return row["id"]
    return None


async def acquire_fresh_summary(
    database: Engine, gate: ProviderGate, settings: Settings, *, job_id: str, lease_token: str,
    transport: httpx.AsyncBaseTransport | None = None, retry_seconds: int = 30, max_attempts: int = 5,
) -> str:
    """Run one claimed job; quota deferrals and retries are persisted, never slept.

    A successful transport stores raw evidence before returning. Any subsequent
    internal failure retries materialization from that evidence without a fetch.
    The injected transport is for offline tests; admission/accounting always wrap it.
    """
    if gate.provider != "opendota" or type(retry_seconds) is not int or retry_seconds < 1 or type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("Invalid fresh acquisition policy")
    with authorized_job(database, job_id, lease_token) as (_, job):
        if job["job_type"] != "SUMMARY" or job["match_id"] is None or job["profile_id"] is not None or job["dedup_key"] != f"summary:{job['match_id']}":
            raise ValueError("Expected shared summary work")
    lock = gate.redis.lock(f"{gate.key}:summary:{job['match_id']}", timeout=60, blocking=False, thread_local=False)
    acquired = False
    try:
        acquired = await asyncio.to_thread(lock.acquire)
        if not acquired:
            # Duplicate delivery must not reschedule and invalidate the worker
            # already holding this same globally deduplicated job. Its lease
            # remains reclaimable if that worker dies.
            return "RUNNING"
        with authorized_job(database, job_id, lease_token) as (connection, current):
            state = connection.scalar(select(matches.c.evidence_state).where(matches.c.match_id == job["match_id"]))
            if state != "DISCOVERED":
                enqueue_roster_links(connection, match_id=job["match_id"], origin="LIVE")
                finish(connection, current)
                return "COMPLETE"
            snapshot_id = stored_match_snapshot(connection, job["match_id"])
            cursor = dict(current["cursor"] or {})
            if snapshot_id is None and cursor.get("acquisition_lease_token") == lease_token:
                return "RUNNING"
        if snapshot_id is None:
            def before_send() -> None:
                with authorized_job(database, job_id, lease_token) as (connection, latest):
                    if dict(latest["cursor"] or {}) != cursor:
                        raise ProviderDeferred("SUMMARY_STEP_ALREADY_CLAIMED", 0.1)
                    connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(
                        cursor={**cursor, "acquisition_lease_token": lease_token},
                    ))

            controlled = ControlledTransport(gate, database, transport=transport, before_send=before_send, job_id=job_id, recovery=job["priority"] == 2 and job["attempts"] > 1)
            async with httpx.AsyncClient(transport=controlled) as http:
                payload = await OpenDotaClient(settings, http_client=http).refresh_match(job["match_id"])
            opendota_summary(payload)
            digest = hashlib.sha256(canonical_json(payload)).hexdigest()
            with database.connect() as connection:
                snapshot_id = connection.execute(select(snapshots.c.id).where(
                    snapshots.c.provider == "opendota", snapshots.c.operation == "match",
                    snapshots.c.operation_version == "1", snapshots.c.schema_version == "raw-1",
                    snapshots.c.subject == f"match:{job['match_id']}", snapshots.c.digest == digest,
                )).scalar_one()
        with authorized_job(database, job_id, lease_token) as (connection, current):
            materialize_snapshot(connection, snapshot_id=snapshot_id, match_id=job["match_id"])
            enqueue_roster_links(connection, match_id=job["match_id"], origin="LIVE")
            calls = connection.scalar(select(func.count()).select_from(provider_calls).where(
                provider_calls.c.provider == "opendota", provider_calls.c.operation == "match",
                provider_calls.c.match_id == job["match_id"],
            ))
            values: dict[str, Any] = dict(operation_version="1", state="COMPLETE", snapshot_id=snapshot_id, attempts=calls)
            connection.execute(insert(acquisitions).values(
                match_id=job["match_id"], provider="opendota", operation="match", **values,
            ).on_conflict_do_update(index_elements=[acquisitions.c.match_id, acquisitions.c.provider, acquisitions.c.operation], set_=values))
            finish(connection, current)
        return "COMPLETE"
    except StaleJob:
        raise
    except Exception as exc:
        if isinstance(exc, ProviderDeferred):
            if exc.reason == "SUMMARY_STEP_ALREADY_CLAIMED":
                return "RUNNING"
            reason, delay, failure = exc.reason, exc.delay, False
        elif isinstance(exc, OpenDotaRateLimited):
            reason, delay, failure = "RATE_LIMITED", float(retry_seconds), False
        else:
            reason = "INVALID_SUMMARY" if isinstance(exc, InvalidEvidence) else "SOURCE_UNAVAILABLE" if isinstance(exc, (OpenDotaUnavailable, ProfileUnavailable, httpx.TransportError)) else "INTERNAL_ACQUISITION"
            delay, failure = float(retry_seconds), True
        with authorized_job(database, job_id, lease_token) as (connection, current):
            reschedule(connection, current, delay_seconds=delay, error=reason, failure=failure, max_attempts=max_attempts)
            terminal = failure and current["attempts"] >= max_attempts
        return "FAILED" if terminal else "DEFERRED"
    finally:
        if acquired:
            try:
                await asyncio.to_thread(lock.release)
            except LockNotOwnedError:
                # Do not release a newer worker's lock after expiry/takeover.
                pass
