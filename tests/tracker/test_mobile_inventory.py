"""Profile, shares, settings, changes, data-access recovery and conditional reads."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from app.core.config import Settings
from app.tracker import sync
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.bootstrap import settle_bootstrap
from app.tracker.jobs import claim
from app.tracker.mobile_api import create_mobile_app
from app.tracker.schema import (
    account_discoveries,
    bootstrap,
    dota_accounts,
    ingest_jobs,
    profiles,
    snapshots,
)
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .builders import add_match, finalize, history
from .test_entitlement import ready_bootstrap
from .test_provider_transport import gate_for


def _linked_client(database, subject: str, account_id: int = 1001):
    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", subject, None))
    profile_id = f"profile-{subject}"
    with database.begin() as connection:
        connection.execute(pg_insert(dota_accounts).values(account_id=account_id).on_conflict_do_nothing())
        connection.execute(profiles.insert().values(
            id=profile_id, user_id=user_id, account_id=account_id, active=True,
            original_linked_at=datetime(2026, 9, 21, tzinfo=UTC)))
    client = TestClient(create_mobile_app(Settings(), database=database))
    return client, {"Authorization": f"Bearer {tokens.access_token}"}, profile_id


def test_profile_pb_share_favourite_and_conditional_reads(database):
    client, headers, profile_id = _linked_client(database, "profile-owner")
    other, other_headers, _ = _linked_client(database, "profile-other", account_id=2002)
    ready_bootstrap(database, profile_id)
    history(database, profile_id, [0, 1, 2, 3, 4, 5, 9])

    first = client.get("/profile?mode=STANDARD", headers=headers)
    assert first.status_code == 200
    view = first.json()
    assert view["state"] == "READY" and view["header"]["eligible_count"] == 7
    assert view["identity"] is None  # below 10 matches: no line, never a default archetype
    assert view["claims_state"] == "CALIBRATION_PENDING" and view["claims"] == []
    assert view["right_now_state"] == "CALIBRATION_PENDING"
    assert view["personal_bests_state"] == "READY"
    stacked = next(row for row in view["personal_bests"] if row["metric_id"] == "support.camps_stacked.v1")
    assert stacked["value"] == 13.0 and stacked["role"] == "SUPPORT" and stacked["match_ref"]
    assert view["recent_celebrations"] and len(view["recent_celebrations"]) <= 3
    etag = first.headers["ETag"]
    assert client.get("/profile?mode=STANDARD", headers={**headers, "If-None-Match": etag}).status_code == 304

    pinned = client.post("/profile/favourite-hero?mode=STANDARD",
                         headers={**headers, "Idempotency-Key": "fav-key-1"}, json={"hero_id": 123})
    assert pinned.status_code == 200 and pinned.json()["favourite_hero_id"] == 123
    assert client.get("/profile?mode=STANDARD", headers={**headers, "If-None-Match": etag}).status_code == 200

    unavailable = client.post("/shares", headers={**headers, "Idempotency-Key": "share-key-1"},
                              json={"kind": "PROFILE", "mode": "STANDARD"})
    assert unavailable.status_code == 409
    assert unavailable.json()["code"] == "SHARE_UNAVAILABLE_IDENTITY_UNCONFIRMED" and unavailable.json()["request_id"]
    shared = client.post("/shares", headers={**headers, "Idempotency-Key": "share-key-2"},
                         json={"kind": "PERSONAL_BEST", "mode": "STANDARD", "metric_id": "support.camps_stacked.v1"})
    assert shared.status_code == 200, shared.text
    share = shared.json()
    assert share["value"] == 13.0 and share["label"] == "Camps Stacked"
    assert not {"match_id", "account_id", "profile_id"} & set(share)
    assert client.get(f"/shares/{share['ref']}", headers=headers).json() == share
    image = client.get(f"/shares/{share['ref']}/image.svg", headers=headers)
    assert image.status_code == 200 and image.headers["content-type"].startswith("image/svg+xml")
    assert "Camps Stacked" in image.text and "13" in image.text
    assert other.get(f"/shares/{share['ref']}", headers=other_headers).status_code == 404
    # Immutable: a later record does not alter the generated snapshot.
    later = add_match(database, profile_id, index=50, stack_bonus=20)
    assert finalize(database, profile_id, later) == "READY"
    assert client.get(f"/shares/{share['ref']}", headers=headers).json()["value"] == 13.0


def test_settings_and_changes_feed(database):
    client, headers, profile_id = _linked_client(database, "changes-owner")
    assert client.get("/settings", headers=headers).json() == {"notifications_enabled": False}
    assert client.patch("/settings", headers=headers, json={"notifications_enabled": True}).json() == {
        "notifications_enabled": True}
    ready_bootstrap(database, profile_id)
    history(database, profile_id, [0])
    start = client.get("/changes", headers=headers).json()
    assert start["full_refresh"] is True and start["changed_refs"] == []
    quiet = client.get("/changes", params={"after": start["cursor"]}, headers=headers).json()
    assert quiet["full_refresh"] is False and quiet["changed_refs"] == []
    newer = add_match(database, profile_id, index=5)
    assert finalize(database, profile_id, newer) == "READY"
    moved = client.get("/changes", params={"after": quiet["cursor"]}, headers=headers).json()
    assert moved["full_refresh"] is False and len(moved["changed_refs"]) == 1
    forged = client.get("/changes", params={"after": "1.0.forged"}, headers=headers).json()
    assert forged["full_refresh"] is True


async def test_withdrawn_history_blocks_access_then_confirmation_reanchors_recovery(database, redis_client):
    client, headers, profile_id = _linked_client(database, "access-owner")
    now = datetime.now(UTC)
    with database.begin() as connection:
        snapshot_id = connection.execute(insert(snapshots).values(
            id="access-snapshot", provider="opendota", operation="history", operation_version="1",
            schema_version="raw-1", subject="history", digest="0" * 64, byte_size=2, fetched_at=now,
            payload=[], provenance={}).returning(snapshots.c.id)).scalar_one()
        connection.execute(insert(account_discoveries).values(
            account_id=1001, provider="opendota", source_item_id="555", snapshot_id=snapshot_id,
            source_started_at=now - timedelta(days=2), outcome="ACCEPTED", recorded_at=now))
        connection.execute(insert(bootstrap), [dict(profile_id=profile_id, mode=mode, search_finished=True)
                                               for mode in ("STANDARD", "TURBO")])
        job_id = sync.request_account_sync(connection, 1001, scope_days=30)
        job = claim(connection, priority=0)
    assert job["id"] == job_id
    outcome = await sync.sync_account_page(database, gate_for(redis_client, "opendota"), Settings(),
                                           job_id=job_id, lease_token=job["lease_token"],
                                           transport=httpx.MockTransport(lambda request: httpx.Response(200, json=[])))
    assert outcome == "COMPLETE"
    readiness = client.get("/readiness", headers=headers).json()
    assert readiness["data_access"] == "BLOCKED" and readiness["state"] == "UP_TO_DATE"
    assert client.get("/recovery", headers=headers).json()["data_access"] == "BLOCKED"
    with database.begin() as connection:
        settle_bootstrap(connection, profile_id)
    modes = {row["mode"]: row["outcome"] for row in client.get("/bootstrap", headers=headers).json()["modes"]}
    assert modes == {"STANDARD": "DATA_ACCESS_BLOCKED", "TURBO": "DATA_ACCESS_BLOCKED"}
    assert client.get("/profile?mode=STANDARD", headers=headers).json()["state"] == "DATA_ACCESS_BLOCKED"
    with database.connect() as connection:
        linked_at = connection.scalar(select(profiles.c.original_linked_at))

    confirmed = client.post("/data-access/confirm", headers={**headers, "Idempotency-Key": "access-key-1"})
    assert confirmed.json() == {"recovery": "STARTED"}
    again = client.post("/data-access/confirm", headers={**headers, "Idempotency-Key": "access-key-1"})
    assert again.json() == {"recovery": "STARTED"}
    assert client.post("/data-access/confirm", headers={**headers, "Idempotency-Key": "access-key-2"}).json() == {
        "recovery": "NOT_NEEDED"}
    with database.connect() as connection:
        jobs = dict(connection.execute(select(ingest_jobs.c.job_type, ingest_jobs.c.payload).where(
            ingest_jobs.c.job_type.in_(("ACCESS_RECOVERY", "BOOTSTRAP_SEARCH")))).all())
        assert set(jobs) == {"ACCESS_RECOVERY", "BOOTSTRAP_SEARCH"}
        # The link anchor never moves forward because access was blocked.
        assert connection.scalar(select(profiles.c.original_linked_at)) == linked_at
        assert connection.execute(select(bootstrap.c.outcome)).scalars().all() == [None, None]
    operation = client.get("/history-operation", headers=headers).json()
    assert operation["access_recovery"] == "RUNNING" and operation["data_access"] == "UNKNOWN"
    assert {row["status"] for row in operation["bootstrap"]} == {"SEARCHING"}


def test_match_detail_exposes_role_source_confidence_lane_and_diagnostics(database):
    client, headers, profile_id = _linked_client(database, "detail-owner")
    [match_id] = history(database, profile_id, [0])
    ref = client.get("/history?mode=STANDARD", headers=headers).json()["matches"][0]["ref"]
    detail = client.get(f"/matches/{ref}", headers=headers).json()
    assert detail["role"] == "SUPPORT" and detail["role_source"] == "INFERRED"
    assert detail["role_confidence"] in {"HIGH", "LOW"}
    assert detail["lane_context"] == "UNAVAILABLE"  # no approved parameter set → renders nothing
    assert all(metric["performance_state"] is None for metric in detail["metrics"]
               if metric["state"] == "NOT_AVAILABLE")
    edited = client.post(f"/matches/{ref}/role", headers={**headers, "Idempotency-Key": "role-key-1"},
                         json={"role": "SUPPORT", "expected_role_revision": 0})
    assert edited.status_code == 200
    confirmed = client.get(f"/matches/{ref}", headers=headers).json()
    assert confirmed["role_source"] == "USER_CONFIRMED" and confirmed["role_confidence"] is None
    with database.begin() as connection:
        connection.execute(update(dota_accounts).values(visibility="ACCESSIBLE"))
    assert match_id
