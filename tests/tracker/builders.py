"""Fixture-only history builders: retained snapshots in, READY links out.

Every helper materializes the sanitized paired-replay OpenDota specimen under
a synthetic match ID. Nothing here reaches a provider.
"""
from __future__ import annotations

from datetime import timedelta

from app.tracker.finalization import complete_finalization_job, enqueue_finalization
from app.tracker.jobs import claim
from app.tracker.materialization import materialize_snapshot
from app.tracker.schema import account_matches, acquisitions, matches, profiles
from sqlalchemy import func, select

from .test_materialization import raw, save

BASE_MATCH = 9_100_000_000


def add_match(database, profile_id: str, *, index: int, origin: str = "LIVE", role: str = "SUPPORT",
              stack_bonus: int = 0, offset_days: float | None = None, account_id: int = 1001,
              turbo: bool = False) -> int:
    """Store one parsed match at `link date + offset_days` and attach an ANALYZING link."""
    match_id = BASE_MATCH + index
    payload = raw()
    payload["match_id"] = match_id
    with database.connect() as connection:
        linked_at = connection.scalar(select(profiles.c.original_linked_at).where(profiles.c.id == profile_id))
    offset = timedelta(days=index if offset_days is None else offset_days)
    payload["start_time"] = int((linked_at + offset).timestamp())
    payload["players"][0]["account_id"] = account_id
    if turbo:
        payload["game_mode"] = 23
    if stack_bonus:
        # The specimen's slot 0 resolves to Support; camps stacked at 20:00 varies.
        payload["players"][0]["camps_stacked_t"] = [
            value + (stack_bonus if minute >= 20 else 0)
            for minute, value in enumerate(payload["players"][0]["camps_stacked_t"])]
    with database.begin() as connection:
        snapshot_id = save(connection, payload)
        projection = materialize_snapshot(connection, snapshot_id=snapshot_id, match_id=match_id)
        match = connection.execute(select(matches).where(matches.c.match_id == match_id)).mappings().one()
        connection.execute(matches.update().where(matches.c.match_id == match_id).values(
            evidence_state="REPLAY_READY", replay_role_assignment=projection["role_assignment"],
            replay_terminal_at=func.clock_timestamp(),
        ))
        # The acquisition pointer names the parsed source finalization must use.
        connection.execute(acquisitions.insert().values(
            match_id=match_id, provider="opendota", operation="match", operation_version="1",
            state="REPLAY_READY", attempts=1, snapshot_id=snapshot_id,
        ))
        connection.execute(account_matches.insert().values(
            profile_id=profile_id, match_id=match_id, account_id=account_id, player_slot=0,
            lifecycle="ANALYZING", mode=match["mode"], effective_role=role,
            provider_started_at=match["started_at"], provider_source_match_id=match_id, origin=origin,
        ))
    return match_id


def finalize(database, profile_id: str, match_id: int) -> str:
    with database.begin() as connection:
        enqueue_finalization(connection, profile_id=profile_id, match_id=match_id)
        origin = connection.scalar(select(account_matches.c.origin).where(
            account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id))
        job = claim(connection, priority=0 if origin == "LIVE" else 3)
    assert job is not None
    return complete_finalization_job(database, job_id=job["id"], lease_token=job["lease_token"])


def history(database, profile_id: str, bonuses: list[int], *, origin: str = "LIVE", start: int = 0,
            offset_days: list[float] | None = None) -> list[int]:
    ids = []
    for position, bonus in enumerate(bonuses):
        match_id = add_match(database, profile_id, index=start + position, origin=origin,
                             stack_bonus=bonus,
                             offset_days=None if offset_days is None else offset_days[position])
        assert finalize(database, profile_id, match_id) == "READY"
        ids.append(match_id)
    return ids
