from datetime import UTC, datetime
from uuid import uuid4

from app.tracker.notifications import deliver_pending, record_ready
from app.tracker.schema import devices, events, notification_outbox, users
from sqlalchemy import func, select

from .test_schema import identity


def test_ready_events_are_live_only_coalesced_and_never_queued_retroactively(database):
    user_id, profile_id = identity(database)
    with database.begin() as c:
        assert record_ready(c, profile_id=profile_id, match_id=1, origin="BOOTSTRAP") is None
        assert record_ready(c, profile_id=profile_id, match_id=1, origin="LIVE") is not None
        assert record_ready(c, profile_id=profile_id, match_id=1, origin="LIVE") is None
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(events)) == 1
        assert c.scalar(select(func.count()).select_from(notification_outbox)) == 0

    with database.begin() as c:
        c.execute(users.update().where(users.c.id == user_id).values(notifications_enabled=True))
        c.execute(devices.insert().values(id=str(uuid4()), user_id=user_id,
            push_token="fake-push-token", permission="GRANTED", last_active_at=datetime.now(UTC)))
        first = record_ready(c, profile_id=profile_id, match_id=2, origin="LIVE")
        second = record_ready(c, profile_id=profile_id, match_id=3, origin="LIVE")
        assert first and second and first != second
    with database.connect() as c:
        row = c.execute(select(notification_outbox)).mappings().one()
        assert row["event_refs"] == [first, second]
        assert row["payload"] == {"kind": "MATCH_READY", "count": 2}

    sent = []
    with database.begin() as c:
        assert deliver_pending(c, lambda token, payload, key: sent.append((token, payload, key))) == 1
    with database.begin() as c:
        assert deliver_pending(c, lambda *_: None) == 0
    assert sent == [("fake-push-token", {"kind": "MATCH_READY", "count": 2}, f"ready:{profile_id}:2")]
    with database.connect() as c:
        assert c.scalar(select(notification_outbox.c.state)) == "SENT"
        assert c.scalar(select(func.count()).select_from(events)) == 3


def test_permission_revocation_suppresses_pending_without_affecting_events(database):
    user_id, profile_id = identity(database)
    with database.begin() as c:
        c.execute(users.update().where(users.c.id == user_id).values(notifications_enabled=True))
        c.execute(devices.insert().values(id=str(uuid4()), user_id=user_id,
            push_token="fake-push-token", permission="GRANTED", last_active_at=datetime.now(UTC)))
        record_ready(c, profile_id=profile_id, match_id=4, origin="LIVE")
        c.execute(users.update().where(users.c.id == user_id).values(notifications_enabled=False))
    with database.begin() as c:
        assert deliver_pending(c, lambda *_: (_ for _ in ()).throw(AssertionError("send"))) == 0
    with database.connect() as c:
        assert c.scalar(select(notification_outbox.c.state)) == "SUPPRESSED"
        assert c.scalar(select(func.count()).select_from(events)) == 1
