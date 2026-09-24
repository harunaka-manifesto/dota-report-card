"""P3 OpenDota summary fallback when a historical deep source lacks a match."""
from __future__ import annotations

from typing import Any

import httpx
from sqlalchemy import Connection, Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings
from app.core.errors import OpenDotaRateLimited, ProfileUnavailable
from app.opendota.client import OpenDotaClient
from app.tracker.acquisition import stored_match_snapshot
from app.tracker.jobs import StaleJob, authorized_job, enqueue, finish, reschedule
from app.tracker.materialization import materialize_snapshot
from app.tracker.normalization import InvalidEvidence
from app.tracker.provider_control import ProviderDeferred, ProviderGate
from app.tracker.provider_transport import ControlledTransport
from app.tracker.schema import acquisitions, ingest_jobs, match_players, matches, profiles, users


def enqueue_historical_summary(connection: Connection, *, profile_id: str, match_id: int, origin: str) -> str:
    if origin not in {"BOOTSTRAP", "HISTORICAL", "RECOVERY"} or type(match_id) is not int or not 0 < match_id < 2**63:
        raise ValueError("Invalid historical summary request")
    owner = connection.execute(select(profiles.c.generation, users.c.generation.label("user_generation")).join(
        users, users.c.id == profiles.c.user_id,
    ).where(profiles.c.id == profile_id)).mappings().one()
    connection.execute(insert(matches).values(match_id=match_id, discovered_at=func.clock_timestamp()).on_conflict_do_nothing())
    return enqueue(connection, dedup_key=f"historical-summary:{profile_id}:{owner['generation']}:{owner['user_generation']}:{match_id}:{origin}",
                   job_type="HISTORICAL_SUMMARY", priority=3, profile_id=profile_id, match_id=match_id,
                   payload={"origin": origin})


def _link_owner(connection: Connection, job: dict[str, Any], origin: str) -> None:
    profile = connection.execute(select(profiles.c.account_id).where(profiles.c.id == job["profile_id"])).mappings().one()
    match = connection.execute(select(matches.c.quarantined_fields).where(matches.c.match_id == job["match_id"])).mappings().one()
    slots = list(connection.scalars(select(match_players.c.player_slot).where(
        match_players.c.match_id == job["match_id"], match_players.c.account_id == profile["account_id"],
    )))
    if len(slots) != 1 or f"players.{slots[0]}.account_id" in match["quarantined_fields"]:
        raise InvalidEvidence("Historical summary does not prove tracked roster membership")
    enqueue(connection, dedup_key=f"link:{job['profile_id']}:{job['profile_generation']}:{job['user_generation']}:{job['match_id']}:{origin}",
            job_type="LINK_MATCH", priority=3, match_id=job["match_id"], profile_id=job["profile_id"], payload={"origin": origin})


async def acquire_historical_summary(database: Engine, gate: ProviderGate, settings: Settings, *, job_id: str, lease_token: str,
                                     transport: httpx.AsyncBaseTransport | None = None, max_attempts: int = 5) -> str:
    if gate.provider != "opendota" or type(max_attempts) is not int or max_attempts < 1:
        raise ValueError("Invalid historical summary policy")
    with authorized_job(database, job_id, lease_token) as (connection, job):
        origin = job["payload"].get("origin")
        if job["job_type"] != "HISTORICAL_SUMMARY" or job["profile_id"] is None or job["match_id"] is None or origin not in {"BOOTSTRAP", "HISTORICAL", "RECOVERY"}:
            raise ValueError("Expected private historical summary job")
        state = connection.scalar(select(matches.c.evidence_state).where(matches.c.match_id == job["match_id"]))
        if state != "DISCOVERED":
            _link_owner(connection, job, origin)
            finish(connection, job)
            return "COMPLETE"
        snapshot_id = stored_match_snapshot(connection, job["match_id"])
        cursor = dict(job["cursor"] or {})
        if snapshot_id is None and cursor.get("request_lease_token") == lease_token:
            return "RUNNING"
    try:
        if snapshot_id is None:
            def before_send() -> None:
                with authorized_job(database, job_id, lease_token) as (connection, current):
                    if dict(current["cursor"] or {}) != cursor:
                        raise ProviderDeferred("HISTORICAL_SUMMARY_STEP_ALREADY_CLAIMED", 0.1)
                    connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(
                        cursor={**cursor, "request_lease_token": lease_token},
                    ))

            controlled = ControlledTransport(gate, database, transport=transport, before_send=before_send, job_id=job_id)
            async with httpx.AsyncClient(transport=controlled) as http:
                await OpenDotaClient(settings, http_client=http).refresh_match(job["match_id"])
            with database.connect() as connection:
                snapshot_id = stored_match_snapshot(connection, job["match_id"])
            if snapshot_id is None:
                raise InvalidEvidence("Historical summary response was not retained")
        with authorized_job(database, job_id, lease_token) as (connection, current):
            materialize_snapshot(connection, snapshot_id=snapshot_id, match_id=job["match_id"])
            _link_owner(connection, current, origin)
            connection.execute(insert(acquisitions).values(
                match_id=job["match_id"], provider="opendota", operation="match",
                operation_version="1", state="COMPLETE", attempts=1, snapshot_id=snapshot_id,
            ).on_conflict_do_nothing())
            finish(connection, current)
        return "COMPLETE"
    except StaleJob:
        raise
    except Exception as exc:
        if isinstance(exc, ProviderDeferred) and exc.reason == "HISTORICAL_SUMMARY_STEP_ALREADY_CLAIMED":
            return "RUNNING"
        with authorized_job(database, job_id, lease_token) as (connection, current):
            if isinstance(exc, ProfileUnavailable):
                connection.execute(insert(acquisitions).values(
                    match_id=job["match_id"], provider="opendota", operation="match",
                    operation_version="1", state="SOURCE_MISSING", attempts=1, terminal_reason="HTTP_404",
                ).on_conflict_do_nothing())
                finish(connection, current)
                return "SOURCE_MISSING"
            deferred = isinstance(exc, (ProviderDeferred, OpenDotaRateLimited))
            reason = exc.reason if isinstance(exc, ProviderDeferred) else "RATE_LIMITED" if isinstance(exc, OpenDotaRateLimited) else "HISTORICAL_SUMMARY_FAILED"
            delay = exc.delay if isinstance(exc, ProviderDeferred) else 30
            reschedule(connection, current, delay_seconds=delay, error=reason, failure=not deferred, max_attempts=max_attempts)
            return "DEFERRED" if deferred or current["attempts"] < max_attempts else "FAILED"
