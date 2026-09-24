"""Materialize one retained STRATZ batch under a profile-fenced transaction."""
from __future__ import annotations

import hashlib
from typing import Any

import httpx
from sqlalchemy import Connection, Engine, func, select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings
from app.core.errors import StratzRateLimited
from app.stratz.client import StratzClient
from app.stratz.queries import GET_TRACKER_MATCH_BATCH
from app.tracker.evidence import canonical_json
from app.tracker.jobs import authorized_job, enqueue, finish, reschedule
from app.tracker.linking import enqueue_role_refinements
from app.tracker.materialization import materialize_snapshot
from app.tracker.normalization import InvalidEvidence, replay_available, stratz_summary
from app.tracker.provider_control import ProviderDeferred, ProviderGate
from app.tracker.provider_transport import ControlledTransport
from app.tracker.schema import (
    acquisitions,
    match_players,
    matches,
    profiles,
    provider_calls,
    snapshots,
    users,
)


def enqueue_historical_batch(connection: Connection, *, profile_id: str, match_ids: list[int], origin: str) -> str:
    if origin not in {"BOOTSTRAP", "HISTORICAL", "RECOVERY"} or not 1 <= len(match_ids) <= 50:
        raise ValueError("Invalid historical batch")
    ids = sorted(set(match_ids))
    if len(ids) != len(match_ids) or any(type(value) is not int or not 0 < value < 2**63 for value in ids):
        raise ValueError("Historical batch needs distinct match IDs")
    owner = connection.execute(select(profiles.c.generation, users.c.generation.label("user_generation")).join(
        users, users.c.id == profiles.c.user_id,
    ).where(profiles.c.id == profile_id)).mappings().one()
    digest = hashlib.sha256(canonical_json(ids)).hexdigest()[:24]
    return enqueue(connection, dedup_key=f"historical:{profile_id}:{owner['generation']}:{owner['user_generation']}:{origin}:{digest}",
                   job_type="HISTORICAL_BATCH", priority=3, profile_id=profile_id,
                   payload={"match_ids": ids, "origin": origin})


def materialize_historical_batch(connection: Connection, *, snapshot_id: str, profile_id: str,
                                 requested_ids: list[int], origin: str) -> dict[int, str]:
    """Consume a recorded response; caller holds the current profile/job fence.

    A missing row is a source-specific absence, never evidence the match did not
    exist. This step does not decide that every replay route has been exhausted.
    """
    if origin not in {"BOOTSTRAP", "HISTORICAL", "RECOVERY"} or not requested_ids or len(requested_ids) > 50:
        raise ValueError("Invalid historical batch")
    if any(type(match_id) is not int or not 0 < match_id < 2**63 for match_id in requested_ids) or len(set(requested_ids)) != len(requested_ids):
        raise ValueError("Historical batch needs distinct match IDs")
    owner = connection.execute(select(profiles.c.account_id, profiles.c.generation, users.c.generation.label("user_generation")).join(
        users, users.c.id == profiles.c.user_id,
    ).where(profiles.c.id == profile_id, profiles.c.active.is_(True), users.c.state == "ACTIVE")).mappings().one()
    source = connection.execute(select(snapshots).where(snapshots.c.id == snapshot_id)).mappings().one()
    if (source["provider"] != "stratz" or source["operation"] != GET_TRACKER_MATCH_BATCH.name
            or source["operation_version"] not in {"1.0.0", GET_TRACKER_MATCH_BATCH.version}
            or source["schema_version"] != "raw-1"):
        raise InvalidEvidence("Unsupported historical snapshot")
    payload = source["payload"]
    player = payload.get("data", {}).get("player") if isinstance(payload, dict) else None
    rows = player.get("matches") if isinstance(player, dict) else None
    if not isinstance(payload, dict) or payload.get("errors") or not isinstance(rows, list) or len(rows) > len(requested_ids):
        raise InvalidEvidence("Malformed historical batch")
    by_id: dict[int, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or type(row.get("id")) is not int or row["id"] not in requested_ids or row["id"] in by_id:
            raise InvalidEvidence("Unexpected or duplicate historical match")
        by_id[row["id"]] = row
    results = {}
    for match_id in requested_ids:
        if match_id not in by_id:
            if connection.scalar(select(matches.c.match_id).where(matches.c.match_id == match_id)) is not None:
                connection.execute(insert(acquisitions).values(
                    match_id=match_id, provider="stratz", operation=GET_TRACKER_MATCH_BATCH.name,
                    operation_version=source["operation_version"], state="SOURCE_MISSING", attempts=1,
                    terminal_reason="NOT_RETURNED_IN_BATCH", snapshot_id=snapshot_id,
                ).on_conflict_do_nothing())
            results[match_id] = "SOURCE_MISSING"
            continue
        try:
            with connection.begin_nested():
                row = by_id[match_id]
                summary = stratz_summary(row)
                roster = [p for p in summary["players"] if p["account_id"] == owner["account_id"]]
                if len(roster) != 1:
                    raise InvalidEvidence("Historical match does not establish tracked roster membership")
                projected = materialize_snapshot(connection, snapshot_id=snapshot_id, match_id=match_id)
                match = connection.execute(select(matches).where(matches.c.match_id == match_id).with_for_update()).mappings().one()
                slot = roster[0]["player_slot"]
                canonical_id = connection.scalar(select(match_players.c.account_id).where(
                    match_players.c.match_id == match_id, match_players.c.player_slot == slot,
                ))
                if canonical_id != owner["account_id"] or f"players.{slot}.account_id" in match["quarantined_fields"]:
                    raise InvalidEvidence("Historical identity disagrees with canonical roster")
                parsed = replay_available(row, "stratz")
                if parsed and match["evidence_state"] not in {"REPLAY_READY"}:
                    connection.execute(matches.update().where(matches.c.match_id == match_id).values(
                        evidence_state="REPLAY_READY", replay_terminal_at=source["fetched_at"],
                        replay_role_assignment=projected["role_assignment"], terminal_reason=None,
                    ))
                    if projected["role_assignment"] is not None:
                        enqueue_role_refinements(connection, match_id, projected["role_assignment"])
                acquired = dict(
                    operation_version=source["operation_version"], state="REPLAY_READY" if parsed else "SUMMARY_ONLY",
                    attempts=1, terminal_reason=None, snapshot_id=snapshot_id,
                )
                connection.execute(insert(acquisitions).values(
                    match_id=match_id, provider="stratz", operation=GET_TRACKER_MATCH_BATCH.name, **acquired,
                ).on_conflict_do_update(
                    index_elements=[acquisitions.c.match_id, acquisitions.c.provider, acquisitions.c.operation],
                    set_=acquired, where=acquisitions.c.state != "REPLAY_READY",
                ))
                enqueue(connection, dedup_key=f"link:{profile_id}:{owner['generation']}:{owner['user_generation']}:{match_id}:{origin}",
                        job_type="LINK_MATCH", priority=3, payload={"origin": origin}, match_id=match_id, profile_id=profile_id)
                results[match_id] = "REPLAY_READY" if parsed else "SUMMARY_ONLY"
        except InvalidEvidence:
            # Isolate one invalid source row so valid matches in the batch settle.
            connection.execute(insert(matches).values(match_id=match_id, discovered_at=func.now()).on_conflict_do_nothing())
            invalid = dict(operation_version=source["operation_version"], state="INVALID_SOURCE",
                           attempts=1, terminal_reason="INVALID_HISTORICAL_ROW", snapshot_id=snapshot_id)
            connection.execute(insert(acquisitions).values(
                match_id=match_id, provider="stratz", operation=GET_TRACKER_MATCH_BATCH.name, **invalid,
            ).on_conflict_do_update(
                index_elements=[acquisitions.c.match_id, acquisitions.c.provider, acquisitions.c.operation],
                set_=invalid, where=acquisitions.c.state != "REPLAY_READY",
            ))
            results[match_id] = "INVALID_SOURCE"
    return results


async def acquire_historical_batch(database: Engine, gate: ProviderGate, settings: Settings, *,
                                   job_id: str, lease_token: str,
                                   transport: httpx.AsyncBaseTransport | None = None) -> str:
    """One bounded provider read, recoverable from its durably recorded response."""
    if gate.provider != "stratz":
        raise ValueError("Historical acquisition requires STRATZ admission")
    with authorized_job(database, job_id, lease_token) as (connection, job):
        ids, origin = job["payload"].get("match_ids"), job["payload"].get("origin")
        if job["job_type"] != "HISTORICAL_BATCH" or job["profile_id"] is None or not isinstance(ids, list):
            raise ValueError("Expected private historical batch job")
        if origin not in {"BOOTSTRAP", "HISTORICAL", "RECOVERY"} or not 1 <= len(ids) <= 50:
            raise ValueError("Invalid historical job payload")
        if any(type(value) is not int or not 0 < value < 2**63 for value in ids) or len(set(ids)) != len(ids):
            raise ValueError("Invalid historical job match IDs")
        snapshot_id = connection.scalar(select(snapshots.c.id).join(
            provider_calls, provider_calls.c.snapshot_id == snapshots.c.id,
        ).where(
            provider_calls.c.job_id == job_id, provider_calls.c.provider == "stratz",
            provider_calls.c.operation == GET_TRACKER_MATCH_BATCH.name,
            provider_calls.c.account_id == job["account_id"],
            provider_calls.c.status == 200, snapshots.c.payload.is_not(None),
        ).order_by(provider_calls.c.called_at.desc()).limit(1))
    if snapshot_id is None:
        def before_send() -> None:
            # A stale worker may not issue a request after its generation/lease expires.
            with authorized_job(database, job_id, lease_token):
                pass

        controlled = ControlledTransport(gate, database, transport=transport, before_send=before_send, job_id=job_id)
        try:
            async with httpx.AsyncClient(transport=controlled) as http:
                await StratzClient(settings, http_client=http).get_tracker_match_batch(job["account_id"], ids)
        except ProviderDeferred as exc:
            with authorized_job(database, job_id, lease_token) as (connection, current):
                reschedule(connection, current, delay_seconds=exc.delay, error=exc.reason, failure=False)
            return "DEFERRED"
        except StratzRateLimited:
            with authorized_job(database, job_id, lease_token) as (connection, current):
                reschedule(connection, current, delay_seconds=30, error="RATE_LIMITED", failure=False)
            return "DEFERRED"
        with authorized_job(database, job_id, lease_token) as (connection, _):
            snapshot_id = connection.scalar(select(snapshots.c.id).join(
                provider_calls, provider_calls.c.snapshot_id == snapshots.c.id,
            ).where(
                provider_calls.c.job_id == job_id, provider_calls.c.provider == "stratz",
                provider_calls.c.operation == GET_TRACKER_MATCH_BATCH.name,
                provider_calls.c.account_id == job["account_id"], provider_calls.c.status == 200,
            ).order_by(provider_calls.c.called_at.desc()).limit(1))
            if snapshot_id is None:
                raise InvalidEvidence("Historical response was not retained")
    with authorized_job(database, job_id, lease_token) as (connection, current):
        materialize_historical_batch(connection, snapshot_id=snapshot_id, profile_id=job["profile_id"],
                                     requested_ids=ids, origin=origin)
        finish(connection, current)
    return "COMPLETE"
