"""Resume a private failed match from retained evidence and existing work."""
from __future__ import annotations

from sqlalchemy import Connection, func, select

from .finalization import enqueue_finalization
from .jobs import enqueue
from .schema import account_matches, ingest_jobs, matches, profiles, users


def retry_match(connection: Connection, *, user_id: str, match_ref: str) -> bool:
    """Return whether a failed match was requeued; never request source data here."""
    user = connection.execute(select(users.c.state).where(users.c.id == user_id).with_for_update()).scalar_one_or_none()
    if user != "ACTIVE":
        raise ValueError("ACCOUNT_UNAVAILABLE")
    profile = connection.execute(select(profiles).where(
        profiles.c.user_id == user_id, profiles.c.active.is_(True),
    ).with_for_update()).mappings().one_or_none()
    if profile is None:
        raise ValueError("MATCH_NOT_FOUND")
    link = connection.execute(select(account_matches).where(
        account_matches.c.profile_id == profile["id"], account_matches.c.public_ref == match_ref,
    ).with_for_update()).mappings().one_or_none()
    if link is None:
        raise ValueError("MATCH_NOT_FOUND")
    if profile["active_scope"] != "PRO" and link["origin"] != "BOOTSTRAP" and link["provider_started_at"] < profile["original_linked_at"]:
        raise ValueError("MATCH_NOT_FOUND")
    if link["lifecycle"] not in {"ACTION_REQUIRED", "UNAVAILABLE"}:
        raise ValueError("RETRY_NOT_AVAILABLE")
    evidence_state = connection.scalar(select(matches.c.evidence_state).where(matches.c.match_id == link["match_id"]))
    if evidence_state not in {"REPLAY_READY", "REPLAY_UNAVAILABLE"} and link["origin"] == "LIVE":
        replay_id = enqueue(connection, dedup_key=f"replay:{link['match_id']}", job_type="REPLAY",
                            priority=2, match_id=link["match_id"], payload={})
        replay = connection.execute(select(ingest_jobs).where(ingest_jobs.c.id == replay_id).with_for_update()).mappings().one()
        if replay["state"] in {"FAILED", "COMPLETE"}:
            connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == replay_id).values(
                state="PENDING", priority=2, run_after=func.clock_timestamp(), attempts=0,
                lease_token=None, lease_until=None, last_error=None,
            ))
    job_id = enqueue_finalization(connection, profile_id=profile["id"], match_id=link["match_id"])
    job = connection.execute(select(ingest_jobs).where(ingest_jobs.c.id == job_id).with_for_update()).mappings().one()
    if job["state"] == "RUNNING":
        return False
    connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(
        state="PENDING", priority=0 if link["origin"] == "LIVE" else 3,
        run_after=func.clock_timestamp(), attempts=0, lease_token=None,
        lease_until=None, last_error=None,
    ))
    connection.execute(account_matches.update().where(
        account_matches.c.profile_id == profile["id"], account_matches.c.match_id == link["match_id"],
    ).values(lifecycle="ANALYZING", retrying=True, failure_stage=None, failure_reason=None))
    return True
