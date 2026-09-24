"""Bounded fresh replay submission/polling with durable intent and raw recovery."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx
from redis.exceptions import LockNotOwnedError
from sqlalchemy import Connection, Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings
from app.core.errors import OpenDotaRateLimited, OpenDotaUnavailable, ProfileUnavailable
from app.opendota.client import OpenDotaClient
from app.opendota.parse_client import OpenDotaParseClient
from app.tracker.acquisition import stored_match_snapshot
from app.tracker.jobs import StaleJob, authorized_job, finish, reschedule
from app.tracker.materialization import materialize_snapshot
from app.tracker.normalization import InvalidEvidence, opendota_summary
from app.tracker.provider_control import ProviderDeferred, ProviderGate
from app.tracker.provider_transport import ControlledTransport
from app.tracker.schema import acquisitions, ingest_jobs, matches, provider_calls, snapshots


@dataclass(frozen=True)
class ReplayPolicy:
    minimum_age_seconds: int = 360
    processing_window_seconds: int = 60 * 86400
    poll_delays: tuple[int, ...] = (60, 120, 300, 600, 1200)
    max_elapsed_seconds: int = 7200
    retry_seconds: int = 30
    max_failures: int = 5

    def __post_init__(self) -> None:
        values = (self.minimum_age_seconds, self.processing_window_seconds, self.max_elapsed_seconds, self.retry_seconds, self.max_failures, *self.poll_delays)
        if not self.poll_delays or any(type(v) is not int or v < 1 for v in values) or self.processing_window_seconds <= self.minimum_age_seconds:
            raise ValueError("Invalid bounded replay policy")


def _request_time(connection: Connection, match_id: int) -> None:
    called_at = connection.scalar(select(func.min(provider_calls.c.called_at)).where(
        provider_calls.c.provider == "opendota", provider_calls.c.operation == "request_replay",
        provider_calls.c.match_id == match_id,
    ))
    if called_at is not None:
        connection.execute(matches.update().where(matches.c.match_id == match_id, matches.c.replay_requested_at.is_(None)).values(replay_requested_at=called_at))


def _terminal(connection: Connection, job: dict[str, Any], *, snapshot_id: str | None = None, reason: str | None = None) -> None:
    match = connection.execute(select(matches).where(matches.c.match_id == job["match_id"]).with_for_update()).mappings().one()
    if match["evidence_state"] not in {"REPLAY_READY", "REPLAY_UNAVAILABLE"}:
        if snapshot_id is not None:
            materialize_snapshot(connection, snapshot_id=snapshot_id, match_id=job["match_id"])
        _request_time(connection, job["match_id"])
        state = "REPLAY_READY" if snapshot_id is not None else "REPLAY_UNAVAILABLE"
        connection.execute(matches.update().where(matches.c.match_id == job["match_id"]).values(
            evidence_state=state, terminal_reason=reason, replay_terminal_at=func.clock_timestamp(),
        ))
        calls = connection.scalar(select(func.count()).select_from(provider_calls).where(
            provider_calls.c.provider == "opendota", provider_calls.c.match_id == job["match_id"],
            provider_calls.c.operation.in_(("match", "request_replay")), provider_calls.c.called_at >= job["created_at"],
        ))
        values = dict(operation_version="1", state=state, snapshot_id=snapshot_id, terminal_reason=reason, attempts=calls)
        connection.execute(insert(acquisitions).values(
            match_id=job["match_id"], provider="opendota", operation="replay_enrichment", **values,
        ).on_conflict_do_update(index_elements=[acquisitions.c.match_id, acquisitions.c.provider, acquisitions.c.operation], set_=values))
    # Evidence terminality never writes private READY or sends a notification.
    finish(connection, job)


async def acquire_fresh_replay(
    database: Engine, gate: ProviderGate, settings: Settings, *, job_id: str, lease_token: str,
    policy: ReplayPolicy = ReplayPolicy(), transport: httpx.AsyncBaseTransport | None = None,
) -> str:
    if gate.provider != "opendota":
        raise ValueError("Fresh replay requires the fresh provider")
    with authorized_job(database, job_id, lease_token) as (_, job):
        if job["job_type"] != "REPLAY" or job["match_id"] is None or job["profile_id"] is not None or job["dedup_key"] != f"replay:{job['match_id']}":
            raise ValueError("Expected shared replay work")
    lock = gate.redis.lock(f"{gate.key}:replay:{job['match_id']}", timeout=60, blocking=False, thread_local=False)
    acquired = False
    try:
        acquired = await asyncio.to_thread(lock.acquire)
        if not acquired:
            return "RUNNING"
        with authorized_job(database, job_id, lease_token) as (connection, current):
            match = connection.execute(select(matches).where(matches.c.match_id == job["match_id"]).with_for_update()).mappings().one()
            if match["evidence_state"] in {"REPLAY_READY", "REPLAY_UNAVAILABLE"}:
                finish(connection, current)
                return "COMPLETE"
            if match["evidence_state"] == "DISCOVERED":
                raise InvalidEvidence("Replay requires a complete summary")
            snapshot_id = stored_match_snapshot(connection, job["match_id"], replay_only=True)
            if snapshot_id is not None:
                _terminal(connection, current, snapshot_id=snapshot_id)
                return "COMPLETE"
            now = connection.execute(select(func.clock_timestamp())).scalar_one()
            if (now - current["created_at"]).total_seconds() > policy.max_elapsed_seconds:
                _terminal(connection, current, reason="REPLAY_WAIT_EXPIRED")
                return "COMPLETE"
            age = (now - match["started_at"] - timedelta(seconds=match["duration_seconds"])).total_seconds()
            if age > policy.processing_window_seconds:
                _terminal(connection, current, reason="OUTSIDE_PROCESSING_WINDOW")
                return "COMPLETE"
            if age < policy.minimum_age_seconds:
                raise ProviderDeferred("REPLAY_TOO_EARLY", policy.minimum_age_seconds - age)
            cursor = dict(current["cursor"] or {})
            if cursor.get("step_lease_token") == lease_token:
                return "RUNNING"
            # A stored receipt is enough to avoid resubmitting after a lost cursor.
            receipt = connection.scalar(select(snapshots.c.id).where(
                snapshots.c.provider == "opendota", snapshots.c.operation == "request_replay",
                snapshots.c.subject == f"match:{job['match_id']}",
            ).limit(1))
            submitted = cursor.get("submitted", False) or receipt is not None
            polls = cursor.get("polls", 0)
            if type(polls) is not int or polls < 0:
                raise InvalidEvidence("Invalid replay cursor")
            _request_time(connection, job["match_id"])
            if polls >= len(policy.poll_delays):
                _terminal(connection, current, reason="REPLAY_CHECKS_EXHAUSTED")
                return "COMPLETE"
            if cursor.get("next_poll_at"):
                remaining = (datetime.fromisoformat(cursor["next_poll_at"]) - now).total_seconds()
                if remaining > 0:
                    raise ProviderDeferred("REPLAY_POLL_SCHEDULED", remaining)

        next_delay = policy.poll_delays[min(polls + int(submitted), len(policy.poll_delays) - 1)]

        def before_send() -> None:
            # Admission already succeeded. Commit intent before any physical I/O.
            # ponytail: one submission; uncertain intent polls rather than resubmits.
            # Add explicit reconciled resubmission only if measured recovery needs it.
            with authorized_job(database, job_id, lease_token) as (connection, latest):
                if dict(latest["cursor"] or {}) != cursor:
                    raise ProviderDeferred("REPLAY_STEP_ALREADY_CLAIMED", 0.1)
                stamp = connection.execute(select(func.clock_timestamp())).scalar_one()
                next_cursor = {
                    "submitted": True, "polls": polls + int(submitted), "step_lease_token": lease_token,
                    "next_poll_at": (stamp + timedelta(seconds=next_delay)).isoformat(),
                }
                connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(cursor=next_cursor))
                changed = connection.execute(matches.update().where(
                    matches.c.match_id == job["match_id"],
                    matches.c.evidence_state.in_(("SUMMARY_READY", "REPLAY_PENDING")),
                ).values(evidence_state="REPLAY_PENDING"))
                if changed.rowcount != 1:
                    raise ProviderDeferred("EVIDENCE_CHANGED", 0.1)

        controlled = ControlledTransport(gate, database, transport=transport, before_send=before_send, job_id=job_id, recovery=job["priority"] == 2 and job["attempts"] > 1)
        async with httpx.AsyncClient(transport=controlled) as http:
            if not submitted:
                await OpenDotaParseClient(settings, http_client=http).request_parse(job["match_id"])
            else:
                payload = await OpenDotaClient(settings, http_client=http).refresh_match(job["match_id"])
                opendota_summary(payload)
        with authorized_job(database, job_id, lease_token) as (connection, current):
            _request_time(connection, job["match_id"])
            snapshot_id = stored_match_snapshot(connection, job["match_id"], replay_only=True)
            if snapshot_id is not None:
                _terminal(connection, current, snapshot_id=snapshot_id)
                return "COMPLETE"
            if current["cursor"]["polls"] >= len(policy.poll_delays):
                _terminal(connection, current, reason="REPLAY_CHECKS_EXHAUSTED")
                return "COMPLETE"
            remaining = max(0, (datetime.fromisoformat(current["cursor"]["next_poll_at"]) - connection.execute(select(func.clock_timestamp())).scalar_one()).total_seconds())
            reschedule(connection, current, delay_seconds=remaining, error="AWAITING_REPLAY", failure=False)
        return "DEFERRED"
    except StaleJob:
        raise
    except Exception as exc:
        with authorized_job(database, job_id, lease_token) as (connection, current):
            _request_time(connection, job["match_id"])
            if isinstance(exc, ProviderDeferred):
                if exc.reason == "REPLAY_STEP_ALREADY_CLAIMED":
                    return "RUNNING"
                reschedule(connection, current, delay_seconds=exc.delay, error=exc.reason, failure=False)
            elif isinstance(exc, OpenDotaRateLimited):
                reschedule(connection, current, delay_seconds=policy.retry_seconds, error="RATE_LIMITED", failure=False,
                           cursor={} if not submitted else {**current["cursor"], "polls": polls})
            else:
                source_error = isinstance(exc, (OpenDotaUnavailable, ProfileUnavailable, httpx.TransportError))
                if source_error and current["attempts"] >= policy.max_failures:
                    _terminal(connection, current, reason="SOURCE_UNAVAILABLE")
                    return "COMPLETE"
                reschedule(connection, current, delay_seconds=policy.retry_seconds,
                           error="SOURCE_UNAVAILABLE" if source_error else "REPLAY_INTERNAL_FAILURE",
                           max_attempts=policy.max_failures)
                if current["attempts"] >= policy.max_failures:
                    return "FAILED"
        return "DEFERRED"
    finally:
        if acquired:
            try:
                await asyncio.to_thread(lock.release)
            except LockNotOwnedError:
                pass
