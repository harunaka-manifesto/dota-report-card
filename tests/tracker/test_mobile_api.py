from datetime import UTC, datetime

from app.core.config import Settings
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.materialization import materialize_snapshot
from app.tracker.mobile_api import _cursor, create_mobile_app
from app.tracker.schema import (
    account_matches,
    dota_accounts,
    idempotency_keys,
    identities,
    matches,
    profiles,
)
from fastapi.testclient import TestClient
from sqlalchemy import select

from .test_materialization import MATCH_ID, raw, save


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
    assert home.json()["focus"] == home.json()["challenge"] == "UNAVAILABLE"
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
