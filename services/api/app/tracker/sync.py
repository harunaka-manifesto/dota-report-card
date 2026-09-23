"""Account-scoped foreground discovery; each page commits before its cursor moves."""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import Connection, Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings
from app.core.errors import OpenDotaRateLimited, OpenDotaUnavailable
from app.opendota.client import OpenDotaClient
from app.tracker.acquisition import enqueue_fresh_summary
from app.tracker.jobs import StaleJob, authorized_job, enqueue, finish, reschedule
from app.tracker.linking import enqueue_roster_links
from app.tracker.provider_control import ProviderDeferred, ProviderGate
from app.tracker.provider_transport import ControlledTransport
from app.tracker.schema import (
    account_discoveries,
    ingest_jobs,
    matches,
    provider_calls,
    snapshots,
    sync_state,
)


def request_account_sync(connection: Connection, account_id: int, *, scope_days: int, debounce_seconds: int = 30) -> str | None:
    """Called by authenticated foreground actions, never by a polling timer."""
    if type(account_id) is not int or not 0 < account_id < 2**32 or type(scope_days) is not int or scope_days < 1 or type(debounce_seconds) is not int or debounce_seconds < 0:
        raise ValueError("Invalid sync policy")
    connection.execute(insert(sync_state).values(account_id=account_id, provider="opendota", state="IDLE").on_conflict_do_nothing())
    row = connection.execute(select(sync_state).where(sync_state.c.account_id == account_id, sync_state.c.provider == "opendota").with_for_update()).mappings().one()
    cursor = dict(row["cursor"] or {})
    # Do not lock the job here: workers lock job then sync state.
    active = connection.scalar(select(ingest_jobs.c.state).where(ingest_jobs.c.id == cursor.get("job_id")))
    if active in {"PENDING", "RUNNING"}:
        return cursor["job_id"]
    now = connection.execute(select(func.clock_timestamp())).scalar_one()
    if row["retry_after"] is not None and row["retry_after"] > now:
        return None
    job_id = enqueue(connection, dedup_key=f"sync:{account_id}:{uuid4()}", job_type="SYNC", priority=0, account_id=account_id, payload={"scope_days": scope_days})
    connection.execute(sync_state.update().where(sync_state.c.account_id == account_id, sync_state.c.provider == "opendota").values(
        state="CHECKING", cursor={**cursor, "job_id": job_id}, retry_after=now + timedelta(seconds=debounce_seconds), blocked_reason=None,
    ))
    return job_id


def _saved_page(connection: Connection, job_id: str, subject: str) -> dict[str, Any] | None:
    row = connection.execute(select(snapshots).join(provider_calls, provider_calls.c.snapshot_id == snapshots.c.id).where(
        provider_calls.c.job_id == job_id, provider_calls.c.request_subject == subject,
        provider_calls.c.provider == "opendota", provider_calls.c.operation == "history",
        provider_calls.c.status >= 200, provider_calls.c.status < 300,
    ).order_by(provider_calls.c.id.desc()).limit(1)).mappings().first()
    return dict(row) if row else None


def _publish_page(connection: Connection, job: dict[str, Any], snapshot: dict[str, Any], offset: int, max_pages: int) -> str:
    rows = snapshot["payload"]
    if not isinstance(rows, list) or len(rows) > 200:
        raise ValueError("Invalid history page")
    floor = job["created_at"] - timedelta(days=job["payload"]["scope_days"])
    for index, raw in enumerate(rows):
        row = raw if isinstance(raw, dict) else {}
        match_id = row.get("match_id")
        valid_id = type(match_id) is int and 0 < match_id < 2**63
        source_id = str(match_id) if valid_id else f"invalid:{snapshot['digest']}:{index}"
        started_at = None
        timestamp = row.get("start_time")
        if type(timestamp) is int and 0 < timestamp <= 253402300799:
            started_at = datetime.fromtimestamp(timestamp, UTC)
        reason = "INVALID_MATCH_ID" if not valid_id else "OUTSIDE_SYNC_WINDOW" if started_at is not None and started_at < floor else None
        accepted = reason is None
        if accepted:
            assert isinstance(match_id, int)
            enqueue_fresh_summary(connection, match_id)
            state = connection.scalar(select(matches.c.evidence_state).where(matches.c.match_id == match_id))
            if state != "DISCOVERED":
                enqueue_roster_links(connection, match_id=match_id, origin="LIVE")
        values = dict(snapshot_id=snapshot["id"], match_id=match_id if accepted else None, source_started_at=started_at,
                      outcome="ACCEPTED" if accepted else "REJECTED", reason=reason, recorded_at=func.clock_timestamp())
        connection.execute(insert(account_discoveries).values(account_id=job["account_id"], provider="opendota", source_item_id=source_id, **values).on_conflict_do_update(
            index_elements=[account_discoveries.c.account_id, account_discoveries.c.provider, account_discoveries.c.source_item_id], set_=values,
        ))
    state_row = connection.execute(select(sync_state).where(sync_state.c.account_id == job["account_id"], sync_state.c.provider == "opendota").with_for_update()).mappings().one()
    pages = (job["cursor"] or {}).get("pages", 0) + 1
    complete = not rows
    exhausted = not complete and pages >= max_pages
    values = dict(state="UP_TO_DATE" if complete else "SYNC_ERROR" if exhausted else "CHECKING", last_checked_at=func.clock_timestamp(), failure_count=0,
                  blocked_reason="PAGINATION_LIMIT" if exhausted else None)
    if complete:
        values.update(last_complete_at=func.clock_timestamp(), source_updated_at=job["created_at"], cursor={**(state_row["cursor"] or {}), "complete_through": job["created_at"].isoformat()})
        finish(connection, job)
    elif exhausted:
        connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == job["id"]).values(state="FAILED", lease_token=None, lease_until=None, last_error="PAGINATION_LIMIT", cursor={"offset": offset + len(rows), "pages": pages}))
    else:
        reschedule(connection, job, delay_seconds=0, error="NEXT_PAGE", cursor={"offset": offset + len(rows), "pages": pages}, failure=False)
    connection.execute(sync_state.update().where(sync_state.c.account_id == job["account_id"], sync_state.c.provider == "opendota").values(**values))
    return "COMPLETE" if complete else "FAILED" if exhausted else "DEFERRED"


async def sync_account_page(database: Engine, gate: ProviderGate, settings: Settings, *, job_id: str, lease_token: str,
                            transport: httpx.AsyncBaseTransport | None = None, max_pages: int = 100, max_attempts: int = 5) -> str:
    if gate.provider != "opendota" or type(max_pages) is not int or max_pages < 1 or type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("Invalid sync bounds")
    with authorized_job(database, job_id, lease_token) as (connection, job):
        if job["job_type"] != "SYNC" or job["account_id"] is None or job["profile_id"] is not None:
            raise ValueError("Expected shared account sync")
        cursor = dict(job["cursor"] or {})
        offset = cursor.get("offset", 0)
        # Keep the source window wide enough even after a long interruption.
        age = connection.execute(select(func.clock_timestamp())).scalar_one() - job["created_at"]
        days = cursor.get("request_days", job["payload"]["scope_days"] + max(0, age.days) + 1)
        url = f"{settings.opendota_base_url.rstrip('/')}/players/{job['account_id']}/matches"
        request = httpx.Request("GET", url, params={"significant": 0, "limit": 200, "offset": offset, "date": days})
        subject = hashlib.sha256(request.url.raw_path + request.content).hexdigest()
        snapshot = _saved_page(connection, job_id, subject)
        if snapshot is None and cursor.get("request_lease_token") == lease_token:
            return "RUNNING"
    try:
        if snapshot is None:
            def before_send() -> None:
                with authorized_job(database, job_id, lease_token) as (connection, current):
                    if dict(current["cursor"] or {}) != cursor:
                        raise ProviderDeferred("SYNC_STEP_ALREADY_CLAIMED", 0.1)
                    connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(cursor={**cursor, "request_days": days, "request_lease_token": lease_token}))

            controlled = ControlledTransport(gate, database, transport=transport, before_send=before_send, job_id=job_id)
            try:
                async with httpx.AsyncClient(transport=controlled) as http:
                    await OpenDotaClient(settings, http_client=http).get_history_page(job["account_id"], offset=offset, days=days)
            except OpenDotaUnavailable:
                # A list with invalid items is still journaled item by item below.
                with database.connect() as connection:
                    if _saved_page(connection, job_id, subject) is None:
                        raise
            with database.connect() as connection:
                snapshot = _saved_page(connection, job_id, subject)
            if snapshot is None:
                raise RuntimeError("Missing history evidence")
        with authorized_job(database, job_id, lease_token) as (connection, current):
            return _publish_page(connection, current, snapshot, offset, max_pages)
    except StaleJob:
        raise
    except Exception as exc:
        if isinstance(exc, ProviderDeferred) and exc.reason == "SYNC_STEP_ALREADY_CLAIMED":
            return "RUNNING"
        deferred = isinstance(exc, (ProviderDeferred, OpenDotaRateLimited))
        reason = exc.reason if isinstance(exc, ProviderDeferred) else "RATE_LIMITED" if isinstance(exc, OpenDotaRateLimited) else "SYNC_PAGE_FAILED"
        delay = exc.delay if isinstance(exc, ProviderDeferred) else 30
        with authorized_job(database, job_id, lease_token) as (connection, current):
            reschedule(connection, current, delay_seconds=delay, error=reason, failure=not deferred, max_attempts=max_attempts)
            connection.execute(sync_state.update().where(sync_state.c.account_id == job["account_id"], sync_state.c.provider == "opendota").values(
                state="SYNC_ERROR", blocked_reason=reason, retry_after=func.clock_timestamp() + timedelta(seconds=delay), failure_count=sync_state.c.failure_count + int(not deferred),
            ))
        return "FAILED" if not deferred and current["attempts"] >= max_attempts else "DEFERRED"
