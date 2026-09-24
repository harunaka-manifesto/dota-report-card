"""Generation-fenced account links and one shared fresh replay job per match."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import Connection, Engine, select
from sqlalchemy.dialects.postgresql import insert

from app.tracker.jobs import authorized_job, enqueue, finish
from app.tracker.normalization import InvalidEvidence
from app.tracker.roles import persist_summary_positions
from app.tracker.schema import account_matches, match_players, matches, profiles, users

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
            effective_role=role["role"], failure_stage=None if role["role"] else "ROLE_CLASSIFICATION",
            failure_reason=None if role["role"] else role["reason"],
            provider_started_at=match["started_at"], provider_source_match_id=job["match_id"], origin=origin,
        ).on_conflict_do_nothing())
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
