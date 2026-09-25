"""READY-only logical notifications, coalesced in the account outbox."""

from __future__ import annotations

from collections.abc import Callable
from datetime import timedelta
from typing import Protocol
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


DELIVERED = "DELIVERED"
INVALID_TOKEN = "INVALID_TOKEN"
RETRY = "RETRY"
FOREGROUND_SECONDS = 60
MAX_AGE_SECONDS = 3600


class PushTransport(Protocol):
    """Platform push adapter. APNs needs HTTP/2 and deployment credentials; the
    repository ships only this interface and the deterministic fake."""

    def send(self, token: str, payload: dict[str, object], collapse_id: str) -> str: ...


class FakePushTransport:
    def __init__(self, results: dict[str, str] | None = None) -> None:
        self.results = results or {}
        self.sent: list[tuple[str, dict[str, object], str]] = []

    def send(self, token: str, payload: dict[str, object], collapse_id: str) -> str:
        self.sent.append((token, payload, collapse_id))
        return self.results.get(token, DELIVERED)


def deliver_pending(connection: Connection,
                    send: PushTransport | Callable[[str, dict[str, object], str], object]) -> int:
    """Send one pending bundle with a stable collapse key; returns devices reached.

    Suppressed without sending when: the account/profile generation moved, the
    user disabled notifications, no granted token remains, a device reported
    foreground activity recently (the app updates directly, best effort), or
    the bundle is too old to be relevant. Invalid tokens are cleared. None of
    this touches processing or readiness.
    """
    now = connection.execute(select(func.clock_timestamp())).scalar_one()
    connection.execute(notification_outbox.update().where(
        notification_outbox.c.state == "PENDING",
        notification_outbox.c.created_at < now - timedelta(seconds=MAX_AGE_SECONDS),
    ).values(state="CANCELLED"))
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
    device_rows = connection.execute(select(devices.c.id, devices.c.push_token, devices.c.last_active_at).where(
        devices.c.user_id == row["user_id"], devices.c.permission == "GRANTED",
        devices.c.push_token.is_not(None), devices.c.push_token != "",
    )).mappings().all()
    foreground = connection.scalar(select(devices.c.id).where(
        devices.c.user_id == row["user_id"],
        devices.c.last_active_at >= now - timedelta(seconds=FOREGROUND_SECONDS),
    ).limit(1)) is not None
    if (user["state"] != "ACTIVE" or user["generation"] != row["user_generation"] or not user["notifications_enabled"]
            or not profile["active"] or not device_rows or foreground):
        connection.execute(notification_outbox.update().where(
            notification_outbox.c.id == row["id"],
        ).values(state="SUPPRESSED"))
        return 0
    reached = 0
    retry = False
    for device in {item["push_token"]: item for item in device_rows}.values():
        sender = send.send if hasattr(send, "send") else send
        outcome = sender(device["push_token"], row["payload"], row["dedup_key"]) or DELIVERED
        if outcome == INVALID_TOKEN:
            connection.execute(devices.update().where(devices.c.id == device["id"]).values(push_token=None))
        elif outcome == RETRY:
            retry = True
        else:
            reached += 1
    if retry and not reached:
        return 0  # stays PENDING; the stable collapse key dedupes a later resend
    connection.execute(notification_outbox.update().where(
        notification_outbox.c.id == row["id"],
    ).values(state="SENT" if reached else "SUPPRESSED", sent_at=func.clock_timestamp() if reached else None))
    return reached


def transport_from_environment() -> PushTransport | None:
    """No production push adapter is configured in this repository (APNs credentials
    and an HTTP/2 client are deployment prerequisites)."""
    return None
