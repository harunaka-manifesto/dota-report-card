"""Generation-fenced account links and one shared fresh replay job per match."""
from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import Connection, Engine, select
from sqlalchemy.dialects.postgresql import insert

from app.tracker.jobs import authorized_job, enqueue, finish
from app.tracker.normalization import InvalidEvidence
from app.tracker.roles import FARM_FIELDS, ROLES, persist_summary_positions
from app.tracker.schema import (
    account_matches,
    match_players,
    matches,
    positions,
    profiles,
    role_assertions,
    users,
)

ORIGINS = {"LIVE", "BOOTSTRAP", "HISTORICAL", "RECOVERY"}


def enqueue_roster_links(connection: Connection, *, match_id: int, origin: str) -> list[str]:
    """Fan out stored evidence to active owners, never to provider requests.

    This can run beside global materialization. Each private publication gets its
    own job/generation guard; a switch after this read invalidates that job.
    """
    if origin not in ORIGINS:
        raise ValueError("Invalid match origin")
    owners = connection.execute(select(profiles.c.id, profiles.c.generation, users.c.generation.label("user_generation")).join(
        users, users.c.id == profiles.c.user_id,
    ).where(
        profiles.c.active.is_(True), users.c.state == "ACTIVE",
        profiles.c.account_id.in_(select(match_players.c.account_id).where(match_players.c.match_id == match_id)),
    ).order_by(profiles.c.id)).mappings()
    return [enqueue(
        connection, dedup_key=f"link:{owner['id']}:{owner['generation']}:{owner['user_generation']}:{match_id}:{origin}",
        job_type="LINK_MATCH", priority=0 if origin == "LIVE" else 3,
        payload={"origin": origin}, match_id=match_id, profile_id=owner["id"],
    ) for owner in owners]


def complete_link_job(database: Engine, *, job_id: str, lease_token: str, replay_delay_seconds: int) -> str | None:
    """Attach verified roster membership, enqueue shared fresh work, finish atomically.

    Delay is explicit operational policy measured from match end. Historical
    acquisition uses its separate route; this function never schedules fresh
    processing for a bootstrap/history link. It never finalizes analysis.
    """
    if type(replay_delay_seconds) is not int or replay_delay_seconds < 1:
        raise ValueError("Replay availability delay must be positive")
    with authorized_job(database, job_id, lease_token) as (connection, job):
        origin = job["payload"].get("origin")
        if job["job_type"] != "LINK_MATCH" or job["profile_id"] is None or origin not in ORIGINS:
            raise ValueError("Expected a profile match-link job")
        match = connection.execute(select(matches).where(matches.c.match_id == job["match_id"]).with_for_update()).mappings().one()
        if match["evidence_state"] == "DISCOVERED":
            raise InvalidEvidence("A complete summary is required before linking")
        roster = connection.execute(select(match_players).where(
            match_players.c.match_id == job["match_id"], match_players.c.account_id == job["account_id"],
        )).mappings().all()
        if len(roster) != 1:
            raise InvalidEvidence("Account must occur exactly once in the canonical roster")
        player = roster[0]
        if f"players.{player['player_slot']}.account_id" in match["quarantined_fields"]:
            raise InvalidEvidence("Conflicting account identity cannot authorize a link")
        assignment = persist_summary_positions(connection, job["match_id"])
        role = next(row for row in assignment["players"] if row["player_slot"] == player["player_slot"])
        connection.execute(insert(account_matches).values(
            profile_id=job["profile_id"], match_id=job["match_id"], account_id=job["account_id"],
            player_slot=player["player_slot"], lifecycle="ANALYZING" if role["role"] else "UNAVAILABLE", mode=match["mode"],
            role_assignment={k: assignment[k] for k in ("version", "inputs_digest", "evidence_profile")},
            effective_role=role["role"], failure_stage=None if role["role"] else "ROLE_CLASSIFICATION",
            failure_reason=None if role["role"] else role["reason"],
            provider_started_at=match["started_at"], provider_source_match_id=job["match_id"], origin=origin,
        ).on_conflict_do_nothing())
        if match["evidence_state"] == "REPLAY_READY" and match["replay_role_assignment"] is not None:
            enqueue_role_refinements(connection, job["match_id"], match["replay_role_assignment"])
        replay_job_id = None
        if origin == "LIVE" and match["evidence_state"] in {"SUMMARY_READY", "REPLAY_PENDING"}:
            replay_job_id = enqueue(
                connection, dedup_key=f"replay:{job['match_id']}", job_type="REPLAY", priority=1,
                match_id=job["match_id"], payload={},
                run_after=match["started_at"] + timedelta(seconds=match["duration_seconds"] + replay_delay_seconds),
            )
            connection.execute(matches.update().where(matches.c.match_id == job["match_id"]).values(evidence_state="REPLAY_PENDING"))
        finish(connection, job)
        return replay_job_id


def enqueue_role_refinements(connection: Connection, match_id: int, assignment: dict[str, Any]) -> None:
    owners = connection.execute(select(profiles.c.id, profiles.c.generation, users.c.generation.label("user_generation")).join(
        users, users.c.id == profiles.c.user_id,
    ).join(account_matches, account_matches.c.profile_id == profiles.c.id).where(
        account_matches.c.match_id == match_id, account_matches.c.finalized_at.is_(None),
        account_matches.c.active_analysis_id.is_(None), profiles.c.active.is_(True), users.c.state == "ACTIVE",
    ).order_by(profiles.c.id)).mappings()
    for owner in owners:
        enqueue(connection, dedup_key=f"role:{owner['id']}:{owner['generation']}:{owner['user_generation']}:{match_id}:{assignment['inputs_digest']}",
                job_type="ROLE_REFRESH", priority=1, match_id=match_id, profile_id=owner["id"], payload=assignment)


def complete_role_job(database: Engine, *, job_id: str, lease_token: str) -> str:
    with authorized_job(database, job_id, lease_token) as (connection, job):
        if job["job_type"] != "ROLE_REFRESH" or job["profile_id"] is None or job["payload"].get("evidence_profile") != "REPLAY":
            raise ValueError("Expected private replay role refinement")
        match = connection.execute(select(matches).where(matches.c.match_id == job["match_id"]).with_for_update()).mappings().one()
        link = connection.execute(select(account_matches).where(account_matches.c.profile_id == job["profile_id"], account_matches.c.match_id == job["match_id"]).with_for_update()).mappings().one()
        if link["finalized_at"] is not None or link["active_analysis_id"] is not None or link["lifecycle"] == "READY":
            finish(connection, job)
            return "FINALIZED_UNCHANGED"
        if f"players.{link['player_slot']}.account_id" in match["quarantined_fields"]:
            finish(connection, job)
            return "IDENTITY_QUARANTINED"
        team_slots = range(5) if link["player_slot"] < 5 else range(5, 10)
        if any(f"players.{slot}.values.{field}" in match["quarantined_fields"] for slot in team_slots for field in FARM_FIELDS):
            finish(connection, job)
            return "ROLE_INPUT_QUARANTINED"
        row = connection.execute(select(positions).where(
            positions.c.match_id == job["match_id"], positions.c.player_slot == link["player_slot"],
            positions.c.evidence_profile == "REPLAY", positions.c.version == job["payload"]["version"],
            positions.c.inputs_digest == job["payload"]["inputs_digest"],
        )).mappings().one()
        if row["position"] is None:
            finish(connection, job)
            return "REFINEMENT_UNAVAILABLE"
        asserted = connection.execute(select(role_assertions).where(role_assertions.c.profile_id == job["profile_id"], role_assertions.c.match_id == job["match_id"]).order_by(role_assertions.c.revision.desc()).limit(1)).mappings().first()
        values: dict[str, Any] = {"role_assignment": job["payload"]}
        if asserted is not None:
            values.update(effective_role=asserted["role"], role_revision=asserted["revision"])
        elif link["role_revision"] == 0 and row["position"] is not None:
            values["effective_role"] = ROLES[row["position"]]
        if (values.get("effective_role") or link["effective_role"]) and link["failure_stage"] == "ROLE_CLASSIFICATION":
            values.update(lifecycle="ANALYZING", failure_stage=None, failure_reason=None)
        connection.execute(account_matches.update().where(account_matches.c.profile_id == job["profile_id"], account_matches.c.match_id == job["match_id"]).values(**values))
        finish(connection, job)
        return "COMPLETE"
