"""Server-side Steam OpenID 2.0 verification and verified profile attachment."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import uuid4

import httpx
from sqlalchemy import Engine, select
from sqlalchemy.dialects.postgresql import insert

from app.tracker.bootstrap import request_bootstrap_search
from app.tracker.schema import dota_accounts, profiles, users

OPENID_NS = "http://specs.openid.net/auth/2.0"
STEAM_ENDPOINT = "https://steamcommunity.com/openid/login"
STEAM_ID_BASE = 76561197960265728
CHALLENGE_TTL_SECONDS = 600


class RedisLike(Protocol):
    def set(self, name: str, value: str, ex: int | None = None, nx: bool = False) -> object: ...
    def getdel(self, name: str) -> str | bytes | None: ...


class SteamLinkError(ValueError):
    pass


class AssertionVerifier(Protocol):
    def verify(self, fields: dict[str, str]) -> bool: ...


class NonceStore(Protocol):
    def consume(self, nonce: str) -> bool: ...


class RedisNonceStore:
    """One-use, cross-worker nonce fence with a bounded Redis lifetime."""

    def __init__(self, redis: RedisLike, *, namespace: str = "tracker") -> None:
        self.redis = redis
        self.namespace = namespace

    def consume(self, nonce: str) -> bool:
        digest = hashlib.sha256(nonce.encode("utf-8")).hexdigest()
        return bool(self.redis.set(
            f"{self.namespace}:steam-openid:nonce:{digest}", "1", ex=CHALLENGE_TTL_SECONDS, nx=True
        ))


class SteamLinkChallengeStore:
    """Persists opaque state -> authenticated owner + exact callback URL."""

    def __init__(self, redis: RedisLike, *, namespace: str = "tracker") -> None:
        self.redis = redis
        self.namespace = namespace

    def create(self, *, state: str, user_id: str, return_to: str) -> bool:
        payload = json.dumps({"user_id": user_id, "return_to": return_to}, separators=(",", ":"))
        return bool(self.redis.set(self._key(state), payload, ex=CHALLENGE_TTL_SECONDS, nx=True))

    def consume(self, state: str, *, user_id: str) -> str:
        value = self.redis.getdel(self._key(state))
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        try:
            challenge = json.loads(value) if isinstance(value, str) else None
        except (TypeError, json.JSONDecodeError) as exc:
            raise SteamLinkError("Steam link challenge is invalid or expired") from exc
        if (
            not isinstance(challenge, dict)
            or challenge.get("user_id") != user_id
            or not isinstance(challenge.get("return_to"), str)
        ):
            raise SteamLinkError("Steam link challenge is invalid or expired")
        return challenge["return_to"]

    def _key(self, state: str) -> str:
        digest = hashlib.sha256(state.encode("utf-8")).hexdigest()
        return f"{self.namespace}:steam-openid:state:{digest}"


@dataclass(frozen=True, slots=True)
class SteamLinkStart:
    state: str
    authorization_url: str
    return_to: str


def start_steam_link(
    engine: Engine,
    redis: RedisLike,
    *,
    user_id: str,
    callback_url: str,
    namespace: str = "tracker",
) -> SteamLinkStart:
    """Create an authenticated, short-lived challenge and Steam redirect URL."""

    parsed = urlsplit(callback_url)
    if (
        not user_id
        or len(user_id) > 200
        or parsed.scheme != "https"
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise SteamLinkError("Steam callback URL must be a trusted HTTPS URL")
    with engine.connect() as connection:
        active = connection.scalar(select(users.c.id).where(users.c.id == user_id, users.c.state == "ACTIVE"))
    if active is None:
        raise SteamLinkError("account is unavailable")
    challenge_store = SteamLinkChallengeStore(redis, namespace=namespace)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    if "state" in query:
        raise SteamLinkError("callback URL cannot provide its own state")
    state = secrets.token_urlsafe(32)
    return_to = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode({**query, "state": state}), ""))
    if not challenge_store.create(state=state, user_id=user_id, return_to=return_to):
        raise SteamLinkError("could not create Steam link challenge")
    params = {
        "openid.ns": OPENID_NS,
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": f"{parsed.scheme}://{parsed.netloc}/",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return SteamLinkStart(state, f"{STEAM_ENDPOINT}?{urlencode(params)}", return_to)


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


def complete_steam_link(
    engine: Engine,
    redis: RedisLike,
    *,
    user_id: str,
    callback_fields: dict[str, str],
    verifier: AssertionVerifier,
    namespace: str = "tracker",
    now: datetime | None = None,
) -> str:
    """Consume the user-bound callback state, verify with Steam, then link and enqueue bootstrap."""

    state = callback_fields.get("state")
    if not isinstance(state, str) or not 32 <= len(state) <= 128:
        raise SteamLinkError("Steam link challenge is invalid or expired")
    callback = SteamLinkChallengeStore(redis, namespace=namespace).consume(state, user_id=user_id)
    openid_fields = {key: value for key, value in callback_fields.items() if key.startswith("openid.")}
    account_id = verify_steam_assertion(
        openid_fields,
        expected_return_to=callback,
        verifier=verifier,
        nonces=RedisNonceStore(redis, namespace=namespace),
        now=now,
    )
    return attach_verified_steam_profile(engine, user_id=user_id, account_id=account_id, now=now)


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
        request_bootstrap_search(connection, profile_id)
    return profile_id
