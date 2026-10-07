from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.tracker.notifications import (
    INVALID_TOKEN,
    RETRY,
    FakePushTransport,
    deliver_pending,
    record_ready,
)
from app.tracker.schema import account_matches, devices, events, notification_outbox, users
from sqlalchemy import func, select

from .builders import add_match
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
            push_token="fake-push-token", permission="GRANTED",
            last_active_at=datetime.now(UTC) - timedelta(hours=2)))
        first = record_ready(c, profile_id=profile_id, match_id=2, origin="LIVE", achievement_ids=[14, 17])
        second = record_ready(c, profile_id=profile_id, match_id=3, origin="LIVE", achievement_ids=[15, 14])
        assert first and second and first != second
    with database.connect() as c:
        row = c.execute(select(notification_outbox)).mappings().one()
        assert row["event_refs"] == [first, second]
        assert row["payload"] == {
            "kind": "MATCH_READY", "count": 2, "achievement_awards": [14, 17, 15, 14],
            # Each badge once, rarest first; the count is the total across the bundle.
            "achievement_ids": [15, 14, 17], "achievement_count": 4,
            "achievement_top_id": 15, "achievement_more": 3}

    sent = []
    with database.begin() as c:
        assert deliver_pending(c, lambda token, payload, key: sent.append((token, payload, key))) == 1
    with database.begin() as c:
        assert deliver_pending(c, lambda *_: None) == 0
    assert sent == [("fake-push-token", {
        "kind": "MATCH_READY", "count": 2, "achievement_awards": [14, 17, 15, 14],
        "achievement_ids": [15, 14, 17], "achievement_count": 4,
        "achievement_top_id": 15, "achievement_more": 3},
                     f"ready:{profile_id}:2")]
    with database.connect() as c:
        assert c.scalar(select(notification_outbox.c.state)) == "SENT"
        assert c.scalar(select(func.count()).select_from(events)) == 3


def test_single_match_bundle_names_its_match_ref_and_a_coalesced_bundle_does_not(database):
    """B2: a one-match READY push carries the opaque `/matches/{ref}`; a bundle of several does not."""
    user_id, profile_id = identity(database)
    first_match = add_match(database, profile_id, index=1)
    second_match = add_match(database, profile_id, index=2)
    with database.connect() as c:
        refs = dict(c.execute(select(account_matches.c.match_id, account_matches.c.public_ref)).all())
    with database.begin() as c:
        c.execute(users.update().where(users.c.id == user_id).values(notifications_enabled=True))
        c.execute(devices.insert().values(id=str(uuid4()), user_id=user_id,
            push_token="fake-push-token", permission="GRANTED",
            last_active_at=datetime.now(UTC) - timedelta(hours=2)))
        record_ready(c, profile_id=profile_id, match_id=first_match, origin="LIVE", achievement_ids=[14])
    with database.connect() as c:
        single = c.scalar(select(notification_outbox.c.payload))
    assert single == {
        "kind": "MATCH_READY", "count": 1, "achievement_awards": [14], "achievement_ids": [14],
        "achievement_count": 1, "achievement_top_id": 14, "achievement_more": 0,
        "match_ref": refs[first_match]}
    assert str(first_match) not in str(single)

    with database.begin() as c:
        record_ready(c, profile_id=profile_id, match_id=second_match, origin="LIVE")
    with database.connect() as c:
        bundle = c.scalar(select(notification_outbox.c.payload))
    assert bundle["count"] == 2 and "match_ref" not in bundle

    transport = FakePushTransport()
    with database.begin() as c:
        assert deliver_pending(c, transport) == 1
    assert [payload for _, payload, _ in transport.sent] == [bundle]


def test_single_match_push_is_delivered_with_its_match_ref(database):
    user_id, profile_id = identity(database)
    match_id = add_match(database, profile_id, index=1)
    with database.begin() as c:
        c.execute(users.update().where(users.c.id == user_id).values(notifications_enabled=True))
        c.execute(devices.insert().values(id=str(uuid4()), user_id=user_id,
            push_token="fake-push-token", permission="GRANTED",
            last_active_at=datetime.now(UTC) - timedelta(hours=2)))
        record_ready(c, profile_id=profile_id, match_id=match_id, origin="LIVE")
        ref = c.scalar(select(account_matches.c.public_ref).where(account_matches.c.match_id == match_id))
    transport = FakePushTransport()
    with database.begin() as c:
        assert deliver_pending(c, transport) == 1
    [(_, payload, _)] = transport.sent
    assert payload["count"] == 1 and payload["match_ref"] == ref


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


def _device(c, user_id, token, *, minutes_ago=120):
    device_id = str(uuid4())
    c.execute(devices.insert().values(id=device_id, user_id=user_id, push_token=token, permission="GRANTED",
                                      last_active_at=datetime.now(UTC) - timedelta(minutes=minutes_ago)))
    return device_id


def test_foreground_suppresses_and_delivery_handles_invalid_tokens_retries_and_staleness(database):
    user_id, profile_id = identity(database)
    with database.begin() as c:
        c.execute(users.update().where(users.c.id == user_id).values(notifications_enabled=True))
        foreground = _device(c, user_id, "token-foreground", minutes_ago=0)
        record_ready(c, profile_id=profile_id, match_id=10, origin="LIVE")
    transport = FakePushTransport()
    with database.begin() as c:
        assert deliver_pending(c, transport) == 0
    assert transport.sent == []
    with database.begin() as c:
        assert c.scalar(select(notification_outbox.c.state)) == "SUPPRESSED"
        c.execute(devices.delete().where(devices.c.id == foreground))
        stale = _device(c, user_id, "token-stale")
        _device(c, user_id, "token-good")
        record_ready(c, profile_id=profile_id, match_id=11, origin="LIVE")
    transport = FakePushTransport({"token-stale": INVALID_TOKEN, "token-good": RETRY})
    with database.begin() as c:
        assert deliver_pending(c, transport) == 0
    with database.connect() as c:
        assert c.scalar(select(devices.c.push_token).where(devices.c.id == stale)) is None
        assert c.scalar(select(notification_outbox.c.state).where(
            notification_outbox.c.dedup_key == f"ready:{profile_id}:11")) == "PENDING"
    transport = FakePushTransport()
    with database.begin() as c:
        assert deliver_pending(c, transport) == 1
    assert [collapse for _, _, collapse in transport.sent] == [f"ready:{profile_id}:11"]
    with database.begin() as c:
        record_ready(c, profile_id=profile_id, match_id=12, origin="LIVE")
        c.execute(notification_outbox.update().where(notification_outbox.c.state == "PENDING")
                  .values(created_at=datetime.now(UTC) - timedelta(hours=2)))
    with database.begin() as c:
        assert deliver_pending(c, FakePushTransport()) == 0
    with database.connect() as c:
        assert c.scalar(select(notification_outbox.c.state).where(
            notification_outbox.c.dedup_key == f"ready:{profile_id}:12")) == "CANCELLED"
        # Events are untouched by any delivery outcome.
        assert c.scalar(select(func.count()).select_from(events)) == 3
