from datetime import UTC, datetime
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.jobs import StaleJob, authorized_job, claim, enqueue
from app.tracker.materialization import materialize_snapshot
from app.tracker.mobile_api import _cursor, create_mobile_app
from app.tracker.schema import (
    account_matches,
    dota_accounts,
    idempotency_keys,
    identities,
    matches,
    profiles,
    provider_calls,
    role_assertions,
)
from app.tracker.steam_identity import STEAM_ID_BASE
from fastapi.testclient import TestClient
from sqlalchemy import select

from .test_finalization import _ready_link, _run
from .test_materialization import MATCH_ID, raw, save
from .test_steam_identity import FakeVerifier, assertion


def _client(database, subject: str):
    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", subject, None,
    ))
    app = create_mobile_app(Settings(), database=database)
    return TestClient(app), {"Authorization": f"Bearer {tokens.access_token}"}, user_id


def test_mobile_account_requires_session_and_keeps_identity_private(database):
    client, headers, _ = _client(database, "mobile-user")
    denied = client.get("/account")
    assert denied.status_code == 401
    assert denied.headers["content-type"] == "application/problem+json"
    account = client.get("/account", headers=headers)
    assert account.status_code == 200
    assert account.json() == {
        "state": "ACTIVE", "steam_linked": False, "scope": "FREE", "revision": 0,
        "identity_methods": ["google"],
    }
    assert "user_id" not in account.text and "subject" not in account.text
    bootstrap = client.get("/bootstrap", headers=headers).json()
    assert {row["mode"]: row["outcome"] for row in bootstrap["modes"]} == {
        "STANDARD": "NO_STEAM_LINKED", "TURBO": "NO_STEAM_LINKED",
    }


def test_mobile_deletion_revokes_session_and_fences_running_private_work(database):
    client, headers, owner = _client(database, "mobile-delete-owner")
    other_client, other_headers, _ = _client(database, "mobile-delete-other")
    with database.begin() as connection:
        connection.execute(dota_accounts.insert().values(account_id=1337))
        connection.execute(profiles.insert().values(
            id="mobile-delete-profile", user_id=owner, account_id=1337,
            active=True, original_linked_at=datetime.now(UTC),
        ))
        job_id = enqueue(connection, dedup_key="mobile-delete-running", job_type="LINK_MATCH",
                         priority=0, profile_id="mobile-delete-profile", payload={})
        job = claim(connection, priority=0)
        assert job is not None and job["id"] == job_id
    deleted = client.delete("/account", headers=headers)
    assert deleted.status_code == 200 and deleted.json() == {"state": "DELETION_PENDING"}
    assert client.get("/account", headers=headers).status_code == 401
    assert other_client.get("/account", headers=other_headers).status_code == 200
    with database.connect() as connection:
        assert connection.scalar(select(profiles.c.id).where(profiles.c.user_id == owner)) is None
    with pytest.raises(StaleJob):
        with authorized_job(database, job_id, job["lease_token"]):
            pytest.fail("deleted account job published")


def test_mobile_match_ref_is_opaque_and_cannot_cross_accounts(database):
    owner_client, owner_headers, owner_id = _client(database, "match-owner")
    other_client, other_headers, _ = _client(database, "other-user")
    with database.begin() as c:
        c.execute(dota_accounts.insert().values(account_id=1001))
        c.execute(profiles.insert().values(id="profile-mobile-owner", user_id=owner_id,
            account_id=1001, active=True, original_linked_at=datetime(2020, 1, 1, tzinfo=UTC)))
        payload = raw()
        payload["players"][0]["account_id"] = 1001
        snapshot_id = save(c, payload)
        materialize_snapshot(c, snapshot_id=snapshot_id, match_id=MATCH_ID)
        match = c.execute(select(matches).where(matches.c.match_id == MATCH_ID)).mappings().one()
        c.execute(account_matches.insert().values(profile_id="profile-mobile-owner", match_id=MATCH_ID,
            account_id=1001, player_slot=0, lifecycle="WAITING_FOR_PROVIDER", mode=match["mode"],
            effective_role="CARRY", provider_started_at=match["started_at"],
            provider_source_match_id=MATCH_ID, origin="LIVE"))
        public_ref = c.scalar(select(account_matches.c.public_ref))
    assert public_ref and str(MATCH_ID) not in public_ref
    owned = owner_client.get(f"/matches/{public_ref}", headers=owner_headers)
    assert owned.status_code == 200
    body = owned.json()
    assert body["ref"] == public_ref
    assert body["facts"] == "AVAILABLE" and body["performance"] == "PENDING"
    assert len(body["players"]) == 10 and body["metrics"] == []
    assert str(MATCH_ID) not in owned.text and "account_id" not in owned.text
    hidden = other_client.get(f"/matches/{public_ref}", headers=other_headers)
    assert hidden.status_code == 404
    history = owner_client.get("/history?mode=STANDARD", headers=owner_headers)
    assert history.status_code == 200 and history.json()["matches"][0]["ref"] == public_ref
    assert other_client.get("/history?mode=STANDARD", headers=other_headers).json()["matches"] == []
    home = owner_client.get("/home?mode=STANDARD&time_zone=Asia/Jakarta", headers=owner_headers)
    assert home.status_code == 200 and home.json()["last_matches"][0]["ref"] == public_ref
    assert home.json()["focus"] == home.json()["challenge"] == {"state": "UNAVAILABLE", "reason": "NOT_CONTRACTED"}
    assert owner_client.get("/home?mode=STANDARD&time_zone=Not_A_Zone", headers=owner_headers).status_code == 400
    cursor = _cursor("profile-mobile-owner", public_ref, "STANDARD", None, 0)
    assert owner_client.get("/history", params={"mode": "STANDARD", "cursor": cursor}, headers=owner_headers).json()["matches"] == []
    assert owner_client.get("/history", params={"mode": "TURBO", "cursor": cursor}, headers=owner_headers).status_code == 400
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == "profile-mobile-owner").values(
            original_linked_at=datetime.now(UTC)))
        c.execute(account_matches.update().values(origin="HISTORICAL"))
    assert owner_client.get(f"/matches/{public_ref}", headers=owner_headers).status_code == 404
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == "profile-mobile-owner").values(active_scope="PRO"))
    assert owner_client.get(f"/matches/{public_ref}", headers=owner_headers).status_code == 200


def test_mobile_role_edit_is_scoped_idempotent_and_source_backed(database):
    profile_id = _ready_link(database)
    assert _run(database, profile_id) == "READY"
    with database.begin() as connection:
        owner = connection.scalar(select(profiles.c.user_id).where(profiles.c.id == profile_id))
        started_at = connection.scalar(select(account_matches.c.provider_started_at).where(
            account_matches.c.profile_id == profile_id,
        ))
        connection.execute(profiles.update().where(profiles.c.id == profile_id).values(
            original_linked_at=started_at,
        ))
        connection.execute(identities.insert().values(
            id=str(uuid4()), user_id=owner, issuer="https://accounts.google.com",
            subject="mobile-role-owner", verified_at=datetime.now(UTC),
        ))
    client, headers, authenticated_owner = _client(database, "mobile-role-owner")
    assert authenticated_owner == owner
    other, other_headers, _ = _client(database, "mobile-role-other")
    with database.connect() as connection:
        row = connection.execute(select(account_matches).where(
            account_matches.c.profile_id == profile_id,
        )).mappings().one()
        ref = row["public_ref"]
        next_role = "MID" if row["effective_role"] != "MID" else "CARRY"
        calls_before = connection.scalar(select(provider_calls.c.id).limit(1))
    detail = client.get(f"/matches/{ref}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["role_revision"] == 0
    assert detail.json()["correction_available"] is True
    assert other.get(f"/matches/{ref}", headers=other_headers).status_code == 404
    request_headers = {**headers, "Idempotency-Key": "role-edit-local-001"}
    body = {"role": next_role, "expected_role_revision": 0}
    changed = client.post(f"/matches/{ref}/role", json=body, headers=request_headers)
    assert changed.status_code == 200
    assert changed.json() == {"role": next_role, "role_revision": 1,
                              "rebuilt": True, "rebuilt_match_count": 1}
    assert client.post(f"/matches/{ref}/role", json=body, headers=request_headers).json() == changed.json()
    assert other.post(f"/matches/{ref}/role", json=body,
                      headers={**other_headers, "Idempotency-Key": "role-edit-other-001"}).status_code == 404
    assert client.post(f"/matches/{ref}/role", json=body,
                       headers={**headers, "Idempotency-Key": "role-edit-stale-002"}).status_code == 409
    assert client.get(f"/matches/{ref}", headers=headers).json()["role"] == next_role
    with database.connect() as connection:
        assert connection.scalar(select(provider_calls.c.id).limit(1)) == calls_before
        assert connection.scalar(select(role_assertions.c.revision)) == 1


def test_mobile_openapi_is_separate_and_uses_closed_enums(database):
    schema = create_mobile_app(Settings(), database=database).openapi()
    assert "/matches/{match_ref}" in schema["paths"]
    assert "Role" in schema["components"]["schemas"]
    text = str(schema).lower()
    for forbidden in ("opendota", "stratz", "replay parse", "quota", "rate limit"):
        assert forbidden not in text


def test_mobile_sync_request_is_idempotent_and_scoped(database):
    client, headers, owner = _client(database, "sync-user")
    headers = {**headers, "Idempotency-Key": "sync-key-0001"}
    assert client.post("/sync", headers=headers).status_code == 409
    with database.begin() as c:
        c.execute(dota_accounts.insert().values(account_id=1002))
        c.execute(profiles.insert().values(id="profile-sync", user_id=owner,
            account_id=1002, active=True, original_linked_at=datetime.now(UTC)))
    first = client.post("/sync", headers=headers)
    second = client.post("/sync", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json() == {"accepted": True}
    with database.connect() as c:
        assert c.scalar(select(idempotency_keys.c.key).where(
            idempotency_keys.c.user_id == owner,
            idempotency_keys.c.operation == "SYNC",
        )) == "sync-key-0001"


def test_mobile_identity_attach_reuses_key_and_rejects_conflicting_body(database, monkeypatch):
    client, headers, owner = _client(database, "identity-user")
    app = client.app
    app.state.audiences = {"apple": {"test.app"}}
    monkeypatch.setattr("app.tracker.mobile_api.verify_identity_token", lambda token, *_: VerifiedIdentity(
        "apple", "https://appleid.apple.com", token, None,
    ))
    headers = {**headers, "Idempotency-Key": "identity-key-0001"}
    first = client.post("/account/identities/apple", json={"identity_token": "a" * 20}, headers=headers)
    assert first.status_code == 200 and first.json()["methods"] == ["apple", "google"]
    assert client.post("/account/identities/apple", json={"identity_token": "a" * 20}, headers=headers).json() == first.json()
    collision = client.post("/account/identities/apple", json={"identity_token": "b" * 20}, headers=headers)
    assert collision.status_code == 409 and collision.json()["code"] == "IDEMPOTENCY_CONFLICT"
    with database.connect() as c:
        assert c.scalar(select(identities.c.subject).where(
            identities.c.user_id == owner, identities.c.issuer == "https://appleid.apple.com"
        )) == "a" * 20


def test_mobile_steam_switch_requires_verified_challenge_and_is_idempotent(database, redis_client):
    redis, _ = redis_client
    owner, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", "mobile-switch-user", None,
    ))
    with database.begin() as c:
        c.execute(dota_accounts.insert().values(account_id=200))
        c.execute(profiles.insert().values(id="mobile-switch-old", user_id=owner, account_id=200,
            active=True, original_linked_at=datetime.now(UTC)))
    app = create_mobile_app(Settings(), database=database, redis=redis,
                            steam_callback_url="https://api.example.test/mobile/v1/steam/callback")
    app.state.steam_verifier = FakeVerifier()
    client = TestClient(app)
    headers = {"Authorization": f"Bearer {tokens.access_token}", "Idempotency-Key": "switch-start-001"}
    assert client.get("/account/steam-switch/preflight", headers=headers).json()["available"] is True
    started = client.post("/account/steam-switch/start", headers=headers)
    assert started.status_code == 200
    assert client.post("/account/steam-switch/start", headers=headers).json() == started.json()
    callback = started.json()
    nonce = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ") + "unique"
    fields = assertion(**{
        "openid.return_to": "https://api.example.test/mobile/v1/steam/callback?state=" + callback["state"],
        "openid.response_nonce": nonce,
        "openid.claimed_id": f"https://steamcommunity.com/openid/id/{STEAM_ID_BASE + 100}",
        "openid.identity": f"https://steamcommunity.com/openid/id/{STEAM_ID_BASE + 100}",
    })
    fields["state"] = callback["state"]
    headers["Idempotency-Key"] = "switch-complete-001"
    completed = client.post("/account/steam-switch/complete", json={"fields": fields}, headers=headers)
    assert completed.status_code == 200 and completed.json() == {"linked": True}
    assert client.post("/account/steam-switch/complete", json={"fields": fields}, headers=headers).json() == completed.json()
    with database.connect() as c:
        assert c.scalar(select(profiles.c.active).where(profiles.c.id == "mobile-switch-old")) is False
        assert c.scalar(select(profiles.c.account_id).where(profiles.c.user_id == owner,
            profiles.c.active.is_(True))) == 100
