"""Tracker account authentication primitives, isolated from legacy report auth."""

from __future__ import annotations

import hashlib
import json
import secrets
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import uuid4

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from jwt.algorithms import RSAAlgorithm
from sqlalchemy import Engine, delete, select, update
from sqlalchemy.dialects.postgresql import insert

from app.tracker.schema import identities, sessions, users

ISSUERS = {
    "apple": ("https://appleid.apple.com", "https://appleid.apple.com/auth/keys"),
    "google": ("https://accounts.google.com", "https://www.googleapis.com/oauth2/v3/certs"),
}


class AuthenticationError(ValueError):
    pass


class IdentityCollision(AuthenticationError):
    """The verified identity is already attached to another account."""

    recovery_path = "/account/recovery"


class InvalidRefreshToken(AuthenticationError):
    pass


class RefreshTokenReuse(InvalidRefreshToken):
    pass


class JwksSource(Protocol):
    def keys(self, provider: str, *, refresh: bool = False) -> list[dict[str, object]]: ...


class HttpJwksSource:
    """Fetch only the fixed Apple and Google key endpoints, caching for one hour."""

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, list[dict[str, object]]]] = {}

    def keys(self, provider: str, *, refresh: bool = False) -> list[dict[str, object]]:
        try:
            endpoint = ISSUERS[provider][1]
        except KeyError as exc:
            raise AuthenticationError("unsupported identity provider") from exc
        cached = self._cache.get(provider)
        if not refresh and cached and cached[0] > time.monotonic():
            return cached[1]
        response = httpx.get(endpoint, timeout=5.0)
        response.raise_for_status()
        keys = response.json().get("keys")
        if not isinstance(keys, list):
            raise AuthenticationError("provider returned invalid signing keys")
        self._cache[provider] = (time.monotonic() + 3600, keys)
        return keys


@dataclass(frozen=True, slots=True)
class VerifiedIdentity:
    provider: str
    issuer: str
    subject: str
    email: str | None


def verify_identity_token(
    token: str,
    provider: str,
    audiences: set[str],
    jwks: JwksSource,
    *,
    now: datetime | None = None,
) -> VerifiedIdentity:
    """Verify Apple/Google RS256 ID tokens; no claims are trusted before signature check."""

    if provider not in ISSUERS or not audiences:
        raise AuthenticationError("unsupported identity provider or missing audience")
    if not isinstance(token, str) or len(token) > 16_384:
        raise AuthenticationError("malformed identity token")
    issuer, _ = ISSUERS[provider]
    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise AuthenticationError("malformed identity token") from exc
    kid = header.get("kid")
    if header.get("alg") != "RS256" or not isinstance(kid, str):
        raise AuthenticationError("unsupported identity token signing key")
    key = next((candidate for candidate in jwks.keys(provider) if candidate.get("kid") == kid), None)
    if key is None:
        key = next(
            (candidate for candidate in jwks.keys(provider, refresh=True) if candidate.get("kid") == kid),
            None,
        )
    if key is None or key.get("kty") != "RSA" or key.get("alg", "RS256") != "RS256" or key.get("use", "sig") != "sig":
        raise AuthenticationError("invalid identity token signature")
    try:
        public_key = RSAAlgorithm.from_jwk(json.dumps(key))
        if not isinstance(public_key, RSAPublicKey) or public_key.key_size < 2048:
            raise AuthenticationError("identity signing key is too short")
        payload = jwt.decode(
            token, public_key, algorithms=["RS256"], audience=list(audiences), issuer=issuer,
            options={"verify_exp": False, "verify_nbf": False, "verify_iat": False,
                     "require": ["exp", "iat", "sub"]},
        )
    except (jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
        raise AuthenticationError("invalid identity token signature or claims") from exc

    current = (now or datetime.now(UTC)).timestamp()
    audience = payload.get("aud")
    if isinstance(audience, str):
        audience_values = {audience}
    elif isinstance(audience, list) and all(isinstance(value, str) for value in audience):
        audience_values = set(audience)
    else:
        audience_values = set()
    authorized_party = payload.get("azp")
    expires_value, not_before_value, issued_value = payload.get("exp"), payload.get("nbf", 0), payload.get("iat")
    if (
        isinstance(expires_value, bool)
        or not isinstance(expires_value, (int, float))
        or isinstance(not_before_value, bool)
        or not isinstance(not_before_value, (int, float))
        or isinstance(issued_value, bool)
        or not isinstance(issued_value, (int, float))
    ):
        raise AuthenticationError("identity token lacks valid timestamps")
    try:
        expires = float(expires_value)
        not_before = float(not_before_value)
        issued = float(issued_value)
    except (TypeError, ValueError) as exc:
        raise AuthenticationError("identity token lacks valid timestamps") from exc
    if (
        payload.get("iss") != issuer
        or not audiences.intersection(audience_values)
        or (authorized_party is not None and authorized_party not in audiences)
        or expires <= current
        or not_before > current
        or issued > current + 60
        or expires <= issued
        or not isinstance(payload.get("sub"), str)
        or not payload["sub"]
    ):
        raise AuthenticationError("identity token claims are invalid")
    email = payload.get("email")
    return VerifiedIdentity(provider, issuer, str(payload["sub"]), email if isinstance(email, str) else None)


class EmailSender(Protocol):
    def send_sign_in_code(self, email: str, code: str) -> None: ...


class FakeEmailSender:
    """Test adapter; production delivery must provide an EmailSender implementation."""

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send_sign_in_code(self, email: str, code: str) -> None:
        self.messages.append((email, code))


def login_with_identity_token(
    engine: Engine,
    token: str,
    provider: str,
    audiences: set[str],
    jwks: JwksSource,
    *,
    now: datetime | None = None,
    access_ttl: timedelta = timedelta(minutes=15),
    refresh_ttl: timedelta = timedelta(days=30),
) -> tuple[str, SessionTokens]:
    identity = verify_identity_token(token, provider, audiences, jwks, now=now)
    return create_user_session(
        engine, identity, now=now, access_ttl=access_ttl, refresh_ttl=refresh_ttl
    )


def attach_identity(engine: Engine, user_id: str, identity: VerifiedIdentity) -> str:
    """Attach a verified identity, refusing account merging on collision."""

    with engine.begin() as connection:
        target = connection.execute(
            select(users.c.state).where(users.c.id == user_id)
        ).scalar_one_or_none()
        if target != "ACTIVE":
            raise AuthenticationError("account is unavailable")
        owner = connection.execute(
            select(identities.c.user_id).where(
                identities.c.issuer == identity.issuer,
                identities.c.subject == identity.subject,
            )
        ).scalar_one_or_none()
        if owner is not None and owner != user_id:
            raise IdentityCollision("identity already belongs to another account")
        connection.execute(
            insert(identities).values(
                id=str(uuid4()),
                user_id=user_id,
                issuer=identity.issuer,
                subject=identity.subject,
                verified_at=datetime.now(UTC),
            ).on_conflict_do_nothing(index_elements=[identities.c.issuer, identities.c.subject])
        )
        owner = connection.execute(
            select(identities.c.user_id).where(
                identities.c.issuer == identity.issuer,
                identities.c.subject == identity.subject,
            )
        ).scalar_one()
        if owner != user_id:
            raise IdentityCollision("identity already belongs to another account")
    return user_id


@dataclass(frozen=True, slots=True)
class SessionTokens:
    session_id: str
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    expires_at: datetime


def _token() -> str:
    return secrets.token_urlsafe(32)


def _token_hash(token: str) -> str:
    if not isinstance(token, str) or len(token) > 512 or not token.isascii():
        raise AuthenticationError("invalid session token")
    return hashlib.sha256(token.encode("ascii")).hexdigest()


def _session_values(
    user_id: str,
    generation: int,
    family_id: str,
    now: datetime,
    access_ttl: timedelta,
    refresh_ttl: timedelta,
) -> tuple[SessionTokens, dict[str, object]]:
    access, refresh = _token(), _token()
    session_id = str(uuid4())
    access_expires, expires = now + access_ttl, now + refresh_ttl
    tokens = SessionTokens(session_id, access, refresh, access_expires, expires)
    row = {
        "id": session_id,
        "user_id": user_id,
        "family_id": family_id,
        "refresh_hash": _token_hash(refresh),
        "access_hash": _token_hash(access),
        "user_generation": generation,
        "created_at": now,
        "access_expires_at": access_expires,
        "expires_at": expires,
    }
    return tokens, row


def create_user_session(
    engine: Engine,
    identity: VerifiedIdentity,
    *,
    now: datetime | None = None,
    access_ttl: timedelta = timedelta(minutes=15),
    refresh_ttl: timedelta = timedelta(days=30),
) -> tuple[str, SessionTokens]:
    """Create an account on first verified login and issue opaque backend tokens."""

    current = now or datetime.now(UTC)
    user_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(users.insert().values(id=user_id, created_at=current))
        connection.execute(
            insert(identities).values(
                id=str(uuid4()), user_id=user_id, issuer=identity.issuer,
                subject=identity.subject, verified_at=current,
            ).on_conflict_do_nothing(index_elements=[identities.c.issuer, identities.c.subject])
        )
        owner = connection.execute(
            select(identities.c.user_id).where(
                identities.c.issuer == identity.issuer,
                identities.c.subject == identity.subject,
            )
        ).scalar_one()
        if owner != user_id:
            connection.execute(delete(users).where(users.c.id == user_id))
            user_id = owner
        user = connection.execute(select(users).where(users.c.id == user_id)).mappings().one()
        if user["state"] != "ACTIVE":
            raise AuthenticationError("account is unavailable")
        tokens, session_row = _session_values(
            user_id, user["generation"], str(uuid4()), current, access_ttl, refresh_ttl
        )
        connection.execute(sessions.insert().values(**session_row))
    return user_id, tokens


def rotate_refresh_token(
    engine: Engine,
    refresh_token: str,
    *,
    now: datetime | None = None,
    access_ttl: timedelta = timedelta(minutes=15),
    refresh_ttl: timedelta = timedelta(days=30),
) -> SessionTokens:
    current = now or datetime.now(UTC)
    failure: type[InvalidRefreshToken] | None = None
    result: SessionTokens | None = None
    with engine.begin() as connection:
        old = connection.execute(
            select(sessions).where(sessions.c.refresh_hash == _token_hash(refresh_token)).with_for_update()
        ).mappings().one_or_none()
        if old is None:
            failure = InvalidRefreshToken
        elif old["revoked_at"] is not None or old["replaced_by"] is not None:
            connection.execute(
                update(sessions).where(
                    sessions.c.family_id == old["family_id"], sessions.c.revoked_at.is_(None)
                ).values(revoked_at=current)
            )
            failure = RefreshTokenReuse
        elif old["expires_at"] <= current:
            connection.execute(
                update(sessions).where(
                    sessions.c.family_id == old["family_id"], sessions.c.revoked_at.is_(None)
                ).values(revoked_at=current)
            )
            failure = InvalidRefreshToken
        else:
            user = connection.execute(select(users).where(users.c.id == old["user_id"])).mappings().one()
            if user["state"] != "ACTIVE" or user["generation"] != old["user_generation"]:
                connection.execute(
                    update(sessions).where(
                        sessions.c.family_id == old["family_id"], sessions.c.revoked_at.is_(None)
                    ).values(revoked_at=current)
                )
                failure = InvalidRefreshToken
            else:
                result, row = _session_values(
                    old["user_id"], old["user_generation"], old["family_id"],
                    current, access_ttl, refresh_ttl,
                )
                connection.execute(
                    update(sessions).where(sessions.c.id == old["id"]).values(
                        revoked_at=current, replaced_by=result.session_id
                    )
                )
                connection.execute(sessions.insert().values(**row))
    if failure:
        raise failure("refresh token is invalid or has already been used")
    assert result is not None
    return result


def authenticate_access_token(engine: Engine, token: str, *, now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    with engine.connect() as connection:
        row = connection.execute(
            select(sessions.c.user_id, sessions.c.access_expires_at, sessions.c.revoked_at,
                   sessions.c.user_generation, users.c.generation, users.c.state)
            .join(users, users.c.id == sessions.c.user_id)
            .where(sessions.c.access_hash == _token_hash(token))
        ).one_or_none()
    if row is None or row.revoked_at is not None or row.access_expires_at <= current:
        raise AuthenticationError("access token is invalid or expired")
    if row.state != "ACTIVE" or row.user_generation != row.generation:
        raise AuthenticationError("account session is no longer active")
    return row.user_id
