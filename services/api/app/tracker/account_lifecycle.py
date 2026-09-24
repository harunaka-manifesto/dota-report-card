"""Account-scoped Steam switching and deletion fences."""
from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import Connection, Engine, delete, false, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.tracker.bootstrap import request_bootstrap_search
from app.tracker.schema import (
    devices,
    dota_accounts,
    history_operations,
    idempotency_keys,
    identities,
    ingest_jobs,
    notification_outbox,
    profiles,
    sessions,
    switches,
    users,
)

SWITCH_COOLDOWN = timedelta(days=90)
_HISTORICAL_JOB_TYPES = ("BOOTSTRAP_SEARCH", "HISTORICAL_BATCH", "HISTORICAL_SUMMARY")


class AccountLifecycleError(ValueError):
    """A lifecycle operation is blocked by a stable, user-presentable cause."""

    def __init__(self, cause: str, *, days_remaining: int = 0) -> None:
        self.cause = cause
        self.days_remaining = days_remaining
        super().__init__(cause)


def _switch_block(
    connection: Connection, *, user_id: str, target_account_id: int, now: datetime,
) -> tuple[str | None, int, str | None]:
    user = connection.execute(select(users).where(users.c.id == user_id)).mappings().first()
    if user is None or user["state"] != "ACTIVE":
        return "ACCOUNT_UNAVAILABLE", 0, None
    active = connection.execute(select(profiles).where(
        profiles.c.user_id == user_id, profiles.c.active.is_(True),
    )).mappings().first()
    if active is None:
        return "NO_ACTIVE_STEAM_PROFILE", 0, None
    owner = connection.execute(select(profiles.c.user_id).where(
        profiles.c.account_id == target_account_id, profiles.c.active.is_(True),
    )).scalar_one_or_none()
    if owner is not None and owner != user_id:
        return "TARGET_OWNED_BY_ANOTHER_ACCOUNT", 0, active["id"]
    prior = connection.execute(select(profiles.c.id).where(
        profiles.c.user_id == user_id, profiles.c.account_id == target_account_id,
    )).scalar_one_or_none()
    if prior is not None:
        # tracker_profiles currently has UNIQUE(user_id, account_id); reusing an
        # archived profile would expose its old analytical history as new state.
        return "ARCHIVED_TARGET_REQUIRES_PROFILE_VERSIONING", 0, active["id"]
    last_switch = connection.execute(select(func.max(switches.c.completed_at)).where(
        switches.c.user_id == user_id,
    )).scalar_one()
    if last_switch is not None:
        remaining = (last_switch + SWITCH_COOLDOWN - now).total_seconds()
        if remaining > 0:
            return "SWITCH_COOLDOWN", math.ceil(remaining / 86400), active["id"]
    operation = connection.execute(select(history_operations.c.id).where(
        history_operations.c.profile_id == active["id"],
        history_operations.c.state.in_(("PENDING", "RUNNING")),
    ).limit(1)).scalar_one_or_none()
    job = connection.execute(select(ingest_jobs.c.id).where(
        ingest_jobs.c.profile_id == active["id"],
        ingest_jobs.c.job_type.in_(_HISTORICAL_JOB_TYPES),
        ingest_jobs.c.state.in_(("PENDING", "RUNNING")),
    ).limit(1)).scalar_one_or_none()
    if operation is not None or job is not None:
        return "HISTORICAL_WORK_RUNNING", 0, active["id"]
    return None, 0, active["id"]


def switch_preflight(
    engine: Engine, *, user_id: str, verified_target_account_id: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return exact switch block and remaining cooldown days.

    The caller must pass only an account ID derived from a verified Steam
    OpenID assertion; this function does not treat client claims as proof.
    """
    if type(verified_target_account_id) is not int or not 0 < verified_target_account_id <= 4_294_967_295:
        raise AccountLifecycleError("INVALID_TARGET")
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("Lifecycle time must include a timezone")
    with engine.connect() as connection:
        cause, days, profile_id = _switch_block(
            connection, user_id=user_id, target_account_id=verified_target_account_id,
            now=current.astimezone(UTC),
        )
    return {"available": cause is None, "cause": cause, "days_remaining": days,
            "active_profile_id": profile_id}


def switch_steam_profile(
    engine: Engine, *, user_id: str, verified_target_account_id: int,
    now: datetime | None = None,
) -> str:
    """Archive the active profile and begin a fresh Free bootstrap atomically."""
    if type(verified_target_account_id) is not int or not 0 < verified_target_account_id <= 4_294_967_295:
        raise AccountLifecycleError("INVALID_TARGET")
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("Lifecycle time must include a timezone")
    profile_id = str(uuid4())
    switch_id = str(uuid4())
    with engine.begin() as connection:
        user = connection.execute(select(users).where(users.c.id == user_id).with_for_update()).mappings().first()
        if user is None or user["state"] != "ACTIVE":
            raise AccountLifecycleError("ACCOUNT_UNAVAILABLE")
        active_id = connection.execute(select(profiles.c.id).where(
            profiles.c.user_id == user_id, profiles.c.active.is_(True),
        ).with_for_update()).scalar_one_or_none()
        # Serialize competing switches to the same target Steam identity.
        connection.execute(insert(dota_accounts).values(
            account_id=verified_target_account_id,
        ).on_conflict_do_nothing())
        connection.execute(select(dota_accounts.c.account_id).where(
            dota_accounts.c.account_id == verified_target_account_id,
        ).with_for_update()).scalar_one()
        cause, days, checked_active_id = _switch_block(
            connection, user_id=user_id, target_account_id=verified_target_account_id,
            now=current.astimezone(UTC),
        )
        if cause is not None:
            raise AccountLifecycleError(cause, days_remaining=days)
        if active_id != checked_active_id:
            raise AccountLifecycleError("ACTIVE_PROFILE_CHANGED")

        # Lock and cancel work only after user/profile locks, matching authorized_job.
        connection.execute(select(ingest_jobs.c.id).where(
            ingest_jobs.c.profile_id == active_id,
            ingest_jobs.c.state.in_(("PENDING", "RUNNING")),
        ).order_by(ingest_jobs.c.id).with_for_update()).all()
        connection.execute(update(ingest_jobs).where(
            ingest_jobs.c.profile_id == active_id,
            ingest_jobs.c.state.in_(("PENDING", "RUNNING")),
        ).values(state="CANCELLED", lease_token=None, lease_until=None))
        connection.execute(update(notification_outbox).where(
            notification_outbox.c.profile_id == active_id,
            notification_outbox.c.state == "PENDING",
        ).values(state="CANCELLED"))
        stamp = connection.execute(select(func.clock_timestamp())).scalar_one()
        previous = connection.execute(update(profiles).where(
            profiles.c.id == active_id, profiles.c.active.is_(True),
        ).values(active=False, archived_at=stamp, generation=profiles.c.generation + 1).returning(
            profiles.c.id,
        )).scalar_one_or_none()
        if previous is None:
            raise AccountLifecycleError("ACTIVE_PROFILE_CHANGED")
        connection.execute(profiles.insert().values(
            id=profile_id, user_id=user_id, account_id=verified_target_account_id,
            active=True, original_linked_at=current.astimezone(UTC), active_scope="FREE",
        ))
        connection.execute(switches.insert().values(
            id=switch_id, user_id=user_id, previous_profile_id=active_id,
            next_profile_id=profile_id, completed_at=stamp,
            dedup_key=f"steam-switch:{switch_id}",
        ))
        request_bootstrap_search(connection, profile_id)
    return profile_id


def request_account_deletion(engine: Engine, *, user_id: str) -> dict[str, Any]:
    """Immediately fence an account and remove its private profiles and credentials.

    Canonical matches remain shared. Subscription records remain for the
    unresolved store-renewal/legal retention decision; no cancellation API is
    claimed here.
    """
    with engine.begin() as connection:
        user = connection.execute(select(users).where(users.c.id == user_id).with_for_update()).mappings().first()
        if user is None:
            raise AccountLifecycleError("ACCOUNT_NOT_FOUND")
        if user["state"] == "DELETION_PENDING":
            return {"state": "DELETION_PENDING", "generation": user["generation"],
                    "policy_gates": ["SUBSCRIPTION_NON_RENEWAL", "SHARED_CANONICAL_RETENTION"]}

        generation = user["generation"] + 1
        stamp = connection.execute(select(func.clock_timestamp())).scalar_one()
        connection.execute(users.update().where(users.c.id == user_id).values(
            state="DELETION_PENDING", generation=generation, deletion_requested_at=stamp,
            notifications_enabled=False,
        ))
        profile_ids = list(connection.scalars(select(profiles.c.id).where(
            profiles.c.user_id == user_id,
        ).order_by(profiles.c.id).with_for_update()))
        owned_jobs = or_(
            ingest_jobs.c.user_id == user_id,
            ingest_jobs.c.profile_id.in_(profile_ids) if profile_ids else false(),
        )
        connection.execute(select(ingest_jobs.c.id).where(
            owned_jobs, ingest_jobs.c.state.in_(("PENDING", "RUNNING")),
        ).order_by(ingest_jobs.c.id).with_for_update()).all()
        connection.execute(update(ingest_jobs).where(
            owned_jobs, ingest_jobs.c.state.in_(("PENDING", "RUNNING")),
        ).values(state="CANCELLED", lease_token=None, lease_until=None))
        # Drop external identity/session access and all profile-scoped data.
        connection.execute(delete(identities).where(identities.c.user_id == user_id))
        connection.execute(delete(sessions).where(sessions.c.user_id == user_id))
        connection.execute(delete(devices).where(devices.c.user_id == user_id))
        connection.execute(delete(idempotency_keys).where(idempotency_keys.c.user_id == user_id))
        connection.execute(delete(notification_outbox).where(notification_outbox.c.user_id == user_id))
        if profile_ids:
            connection.execute(delete(profiles).where(profiles.c.id.in_(profile_ids)))
        return {"state": "DELETION_PENDING", "generation": generation,
                "policy_gates": ["SUBSCRIPTION_NON_RENEWAL", "SHARED_CANONICAL_RETENTION"]}
