"""READY-only logical notifications, coalesced in the account outbox."""

from __future__ import annotations

from collections.abc import Callable
from uuid import uuid4

from sqlalchemy import Connection, func, select
from sqlalchemy.dialects.postgresql import insert

from .schema import devices, events, notification_outbox, profiles, users


def record_ready(connection: Connection, *, profile_id: str, match_id: int, origin: str) -> str | None:
    """Publish one live READY event; permission is tested only for push eligibility."""
    if origin != "LIVE":
        return None
    profile = connection.execute(select(profiles.c.user_id).where(
        profiles.c.id == profile_id, profiles.c.active.is_(True),
    )).one_or_none()
    if profile is None:
        return None
    user = connection.execute(select(users).where(users.c.id == profile.user_id).with_for_update()).mappings().one()
    if user["state"] != "ACTIVE":
        return None
    dedup_key = f"ready:{profile_id}:{match_id}"
    event_id = connection.execute(insert(events).values(
        id=str(uuid4()), profile_id=profile_id, kind="MATCH_READY", dedup_key=dedup_key,
        payload={"match_id": match_id}, created_at=func.clock_timestamp(),
    ).on_conflict_do_nothing(index_elements=[events.c.dedup_key]).returning(events.c.id)).scalar_one_or_none()
    if event_id is None:
        return None
    if not user["notifications_enabled"] or connection.scalar(select(devices.c.id).where(
        devices.c.user_id == user["id"], devices.c.permission == "GRANTED",
        devices.c.push_token.is_not(None), devices.c.push_token != "",
    ).limit(1)) is None:
        return event_id
    pending = connection.execute(select(notification_outbox).where(
        notification_outbox.c.user_id == user["id"],
        notification_outbox.c.profile_id == profile_id,
        notification_outbox.c.user_generation == user["generation"],
        notification_outbox.c.state == "PENDING",
    ).order_by(notification_outbox.c.created_at).with_for_update().limit(1)).mappings().first()
    if pending is not None:
        refs = [*pending["event_refs"], event_id]
        connection.execute(notification_outbox.update().where(
            notification_outbox.c.id == pending["id"],
        ).values(event_refs=refs, payload={"kind": "MATCH_READY", "count": len(refs)}))
    else:
        connection.execute(notification_outbox.insert().values(
            id=str(uuid4()), user_id=user["id"], profile_id=profile_id,
            user_generation=user["generation"], dedup_key=dedup_key,
            event_refs=[event_id], payload={"kind": "MATCH_READY", "count": 1},
            state="PENDING", created_at=func.clock_timestamp(),
        ))
    return event_id


def deliver_pending(connection: Connection, send: Callable[[str, dict[str, object], str], None]) -> int:
    """Send a bounded pending bundle with a stable collapse key through an injected transport."""
    candidate = connection.execute(select(notification_outbox.c.id,
        notification_outbox.c.user_id, notification_outbox.c.profile_id).where(
        notification_outbox.c.state == "PENDING",
    ).order_by(notification_outbox.c.created_at).limit(1)).mappings().first()
    if candidate is None:
        return 0
    user = connection.execute(select(users).where(users.c.id == candidate["user_id"]).with_for_update()).mappings().one()
    profile = connection.execute(select(profiles).where(profiles.c.id == candidate["profile_id"]).with_for_update()).mappings().one()
    row = connection.execute(select(notification_outbox).where(
        notification_outbox.c.id == candidate["id"],
        notification_outbox.c.state == "PENDING",
    ).with_for_update(skip_locked=True)).mappings().first()
    if row is None:
        return 0
    tokens = connection.scalars(select(devices.c.push_token).where(
        devices.c.user_id == row["user_id"], devices.c.permission == "GRANTED",
        devices.c.push_token.is_not(None), devices.c.push_token != "",
    )).all()
    if user["state"] != "ACTIVE" or user["generation"] != row["user_generation"] or not user["notifications_enabled"] or not profile["active"] or not tokens:
        connection.execute(notification_outbox.update().where(
            notification_outbox.c.id == row["id"],
        ).values(state="SUPPRESSED"))
        return 0
    for token in set(tokens):
        send(token, row["payload"], row["dedup_key"])
    connection.execute(notification_outbox.update().where(
        notification_outbox.c.id == row["id"],
    ).values(state="SENT", sent_at=func.clock_timestamp()))
    return len(set(tokens))
