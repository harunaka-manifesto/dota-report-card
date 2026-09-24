"""Server-side Steam OpenID 2.0 verification and verified profile attachment."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

import httpx
from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert

from app.tracker.schema import dota_accounts, profiles, users

OPENID_NS = "http://specs.openid.net/auth/2.0"
STEAM_ENDPOINT = "https://steamcommunity.com/openid/login"
STEAM_ID_BASE = 76561197960265728


class SteamLinkError(ValueError):
    pass


class AssertionVerifier(Protocol):
    def verify(self, fields: dict[str, str]) -> bool: ...


class NonceStore(Protocol):
    def consume(self, nonce: str) -> bool: ...


class HttpSteamAssertionVerifier:
    """Ask Steam to validate the complete assertion; endpoint is fixed."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=5.0)

    def verify(self, fields: dict[str, str]) -> bool:
        response = self._client.post(
            STEAM_ENDPOINT,
            data={**fields, "openid.mode": "check_authentication"},
        )
        response.raise_for_status()
        values = {
            key: line[len(key) + 1 :]
            for line in response.text.splitlines()
            for key in ("ns", "is_valid")
            if line.startswith(key + ":")
        }
        return values.get("ns") == OPENID_NS and values.get("is_valid") == "true"


def verify_steam_assertion(
    fields: dict[str, str],
    *,
    expected_return_to: str,
    verifier: AssertionVerifier,
    nonces: NonceStore,
    now: datetime | None = None,
) -> int:
    """Return the verified Dota account id; reject malformed, stale and replayed callbacks."""

    if not isinstance(fields, dict) or len(fields) > 40 or any(
        not isinstance(k, str) or not isinstance(v, str) or len(k) > 100 or len(v) > 2048
        for k, v in fields.items()
    ):
        raise SteamLinkError("malformed Steam assertion")
    claimed = fields.get("openid.claimed_id", "")
    identity = fields.get("openid.identity")
    prefix = "https://steamcommunity.com/openid/id/"
    steam_id = claimed.removeprefix(prefix)
    nonce = fields.get("openid.response_nonce", "")
    try:
        nonce_time = datetime.strptime(nonce[:20], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise SteamLinkError("invalid Steam assertion nonce") from exc
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise SteamLinkError("verification time must include a timezone")
    age = current.astimezone(UTC) - nonce_time
    if (
        fields.get("openid.ns") != OPENID_NS
        or fields.get("openid.mode") != "id_res"
        or fields.get("openid.op_endpoint") != STEAM_ENDPOINT
        or fields.get("openid.return_to") != expected_return_to
        or not expected_return_to.startswith("https://")
        or identity != claimed
        or len(steam_id) != 17
        or not steam_id.isascii()
        or not steam_id.isdigit()
        or not steam_id.startswith("7656119")
        or len(nonce) <= 20
        or age < timedelta(seconds=-60)
        or age > timedelta(minutes=5)
        or not verifier.verify(fields)
        or not nonces.consume(nonce)
    ):
        raise SteamLinkError("Steam assertion is invalid, expired, or already used")
    account_id = int(steam_id) - STEAM_ID_BASE
    if not 0 < account_id <= 4_294_967_295:
        raise SteamLinkError("Steam identity is outside the supported Dota account range")
    return account_id


def attach_verified_steam_profile(
    engine: Engine,
    *,
    user_id: str,
    account_id: int,
    now: datetime | None = None,
) -> str:
    """Create the first active profile for a user; switching stays in its own flow."""

    if type(account_id) is not int or not 0 < account_id <= 4_294_967_295:
        raise SteamLinkError("invalid Dota account id")
    linked_at = now or datetime.now(UTC)
    profile_id = str(uuid4())
    with engine.begin() as connection:
        owner = connection.execute(
            select(users.c.state).where(users.c.id == user_id).with_for_update()
        ).scalar_one_or_none()
        if owner != "ACTIVE":
            raise SteamLinkError("account is unavailable")
        if connection.execute(
            select(profiles.c.id).where(profiles.c.user_id == user_id, profiles.c.active.is_(True))
        ).first():
            raise SteamLinkError("Steam profile already linked; use the switch flow")
        if connection.execute(
            select(profiles.c.id).where(profiles.c.account_id == account_id, profiles.c.active.is_(True))
        ).first():
            raise SteamLinkError("Steam identity is already linked to another account")
        connection.execute(
            insert(dota_accounts).values(account_id=account_id).on_conflict_do_nothing()
        )
        connection.execute(
            insert(profiles).values(
                id=profile_id,
                user_id=user_id,
                account_id=account_id,
                active=True,
                original_linked_at=linked_at,
                active_scope="FREE",
            )
        )
    return profile_id
