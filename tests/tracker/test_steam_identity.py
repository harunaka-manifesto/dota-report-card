from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs

import httpx
import pytest
from app.tracker.schema import bootstrap, dota_accounts, ingest_jobs, profiles, users
from app.tracker.steam_identity import (
    OPENID_NS,
    STEAM_ENDPOINT,
    HttpSteamAssertionVerifier,
    RedisNonceStore,
    SteamLinkError,
    attach_verified_steam_profile,
    complete_steam_link,
    complete_steam_switch,
    start_steam_link,
    start_steam_switch,
    verify_steam_assertion,
)
from sqlalchemy import insert, select

NOW = datetime(2026, 9, 25, 0, 0, tzinfo=UTC)
STEAM_ID = "76561197960265828"
RETURN_TO = "https://api.example.test/v1/tracker/steam/callback?state=opaque"


class FakeVerifier:
    def __init__(self, valid: bool = True) -> None:
        self.valid = valid
        self.calls = 0

    def verify(self, fields: dict[str, str]) -> bool:
        self.calls += 1
        return self.valid


class FakeNonces:
    def __init__(self) -> None:
        self.used: set[str] = set()

    def consume(self, nonce: str) -> bool:
        if nonce in self.used:
            return False
        self.used.add(nonce)
        return True


def assertion(**overrides: str) -> dict[str, str]:
    fields = {
        "openid.ns": OPENID_NS,
        "openid.mode": "id_res",
        "openid.op_endpoint": STEAM_ENDPOINT,
        "openid.return_to": RETURN_TO,
        "openid.claimed_id": f"https://steamcommunity.com/openid/id/{STEAM_ID}",
        "openid.identity": f"https://steamcommunity.com/openid/id/{STEAM_ID}",
        "openid.response_nonce": "2026-09-25T00:00:00Zunique",
        "openid.signed": "op_endpoint,claimed_id,identity,return_to,response_nonce",
        "openid.sig": "opaque-signature",
    }
    fields.update(overrides)
    return fields


def test_steam_assertion_requires_server_verification_and_nonce_consumption() -> None:
    verifier, nonces = FakeVerifier(), FakeNonces()
    fields = assertion()
    account_id = verify_steam_assertion(
        fields, expected_return_to=RETURN_TO, verifier=verifier, nonces=nonces, now=NOW,
    )
    assert account_id == 100
    assert verifier.calls == 1
    with pytest.raises(SteamLinkError, match="invalid, expired, or already used"):
        verify_steam_assertion(
            fields, expected_return_to=RETURN_TO, verifier=verifier, nonces=nonces, now=NOW,
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"openid.return_to": "https://attacker.test/callback"},
        {"openid.op_endpoint": "https://attacker.test/openid"},
        {"openid.identity": "https://steamcommunity.com/openid/id/76561197960265999"},
        {"openid.response_nonce": "2026-09-24T23:00:00Zstale"},
    ],
)
def test_steam_assertion_rejects_unbound_or_stale_fields(changes: dict[str, str]) -> None:
    verifier = FakeVerifier()
    with pytest.raises(SteamLinkError):
        verify_steam_assertion(
            assertion(**changes), expected_return_to=RETURN_TO, verifier=verifier,
            nonces=FakeNonces(), now=NOW,
        )
    assert verifier.calls == 0


def test_steam_openid_http_adapter_posts_to_fixed_endpoint() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, text="ns:" + OPENID_NS + "\nis_valid:true\n")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert HttpSteamAssertionVerifier(client).verify(assertion())
    assert str(seen[0].url) == STEAM_ENDPOINT
    form = parse_qs(seen[0].content.decode())
    assert form["openid.mode"] == ["check_authentication"]
    assert form["openid.sig"] == ["opaque-signature"]


def test_verified_link_creates_only_first_active_profile(database) -> None:
    user_id = "steam-link-user"
    with database.begin() as connection:
        connection.execute(insert(users).values(id=user_id, created_at=NOW))
    profile_id = attach_verified_steam_profile(database, user_id=user_id, account_id=100, now=NOW)
    with database.connect() as connection:
        profile = connection.execute(select(profiles).where(profiles.c.id == profile_id)).mappings().one()
        assert profile["user_id"] == user_id and profile["active"]
        assert profile["original_linked_at"] == NOW
        assert connection.scalar(select(dota_accounts.c.account_id).where(dota_accounts.c.account_id == 100)) == 100
    with pytest.raises(SteamLinkError, match="already linked"):
        attach_verified_steam_profile(database, user_id=user_id, account_id=101, now=NOW)


def test_verified_steam_identity_cannot_be_claimed_twice(database) -> None:
    first, second = "steam-link-first", "steam-link-second"
    with database.begin() as connection:
        connection.execute(insert(users), [
            {"id": first, "created_at": NOW}, {"id": second, "created_at": NOW},
        ])
    attach_verified_steam_profile(database, user_id=first, account_id=100, now=NOW)
    with pytest.raises(SteamLinkError, match="already linked to another"):
        attach_verified_steam_profile(database, user_id=second, account_id=100, now=NOW)


def test_redis_nonce_is_durable_and_one_use(redis_client) -> None:
    redis, namespace = redis_client
    store = RedisNonceStore(redis, namespace=namespace)
    assert store.consume("openid-nonce-once")
    assert not store.consume("openid-nonce-once")


def test_link_challenge_binds_user_callback_and_enqueues_bootstrap(database, redis_client) -> None:
    redis, namespace = redis_client
    user_id = "steam-link-start-user"
    with database.begin() as connection:
        connection.execute(insert(users).values(id=user_id, created_at=NOW))
    challenge = start_steam_link(
        database,
        redis,
        user_id=user_id,
        callback_url="https://api.example.test/v1/tracker/steam/callback",
        namespace=namespace,
    )
    assert challenge.state in challenge.return_to
    assert STEAM_ENDPOINT in challenge.authorization_url
    assert "openid.mode=checkid_setup" in challenge.authorization_url
    fields = assertion(**{"openid.return_to": challenge.return_to})
    fields["state"] = challenge.state
    verifier = FakeVerifier()
    profile_id = complete_steam_link(
        database, redis, user_id=user_id, callback_fields=fields,
        verifier=verifier, namespace=namespace, now=NOW,
    )
    assert verifier.calls == 1
    with database.connect() as connection:
        assert connection.scalar(select(bootstrap.c.profile_id).where(bootstrap.c.profile_id == profile_id)) == profile_id
        assert connection.scalar(select(ingest_jobs.c.job_type).where(
            ingest_jobs.c.profile_id == profile_id,
            ingest_jobs.c.job_type == "BOOTSTRAP_SEARCH",
        )) == "BOOTSTRAP_SEARCH"
    with pytest.raises(SteamLinkError, match="invalid or expired"):
        complete_steam_link(
            database, redis, user_id=user_id, callback_fields=fields,
            verifier=verifier, namespace=namespace, now=NOW,
        )
    assert verifier.calls == 1


def test_switch_challenge_is_distinct_and_archives_only_after_verified_assertion(database, redis_client) -> None:
    from .test_schema import identity

    redis, namespace = redis_client
    user_id, old_profile = identity(database, account_id=200)
    challenge = start_steam_switch(
        database, redis, user_id=user_id,
        callback_url="https://api.example.test/mobile/v1/steam/switch/callback",
        namespace=namespace,
    )
    fields = assertion(**{"openid.return_to": challenge.return_to})
    fields["state"] = challenge.state
    verifier = FakeVerifier()
    with pytest.raises(SteamLinkError, match="challenge"):
        complete_steam_link(database, redis, user_id=user_id, callback_fields=fields,
                            verifier=verifier, namespace=namespace, now=NOW)
    assert verifier.calls == 0
    new_profile = complete_steam_switch(database, redis, user_id=user_id,
                                        callback_fields=fields, verifier=verifier,
                                        namespace=namespace, now=NOW)
    assert verifier.calls == 1 and new_profile != old_profile
    with database.connect() as connection:
        assert connection.scalar(select(profiles.c.active).where(profiles.c.id == old_profile)) is False
        assert connection.scalar(select(profiles.c.account_id).where(profiles.c.id == new_profile)) == 100
    with pytest.raises(SteamLinkError, match="challenge"):
        complete_steam_switch(database, redis, user_id=user_id,
                              callback_fields=fields, verifier=verifier,
                              namespace=namespace, now=NOW)
