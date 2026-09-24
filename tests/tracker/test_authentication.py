from __future__ import annotations

import base64
import json
import shutil
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from app.tracker.authentication import (
    AuthenticationError,
    FakeEmailSender,
    IdentityCollision,
    RefreshTokenReuse,
    VerifiedIdentity,
    attach_identity,
    authenticate_access_token,
    create_user_session,
    login_with_identity_token,
    revoke_access_session,
    rotate_refresh_token,
    verify_identity_token,
)
from app.tracker.schema import sessions, users
from sqlalchemy import select


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _der_integer(data: bytes) -> int:
    assert data[0] == 0x02
    length = data[1]
    offset = 2
    if length & 0x80:
        count = length & 0x7F
        length = int.from_bytes(data[offset : offset + count], "big")
        offset += count
    return int.from_bytes(data[offset : offset + length], "big")


class LocalJwks:
    def __init__(self, key: dict[str, str]) -> None:
        self.key = key

    def keys(self, provider: str) -> list[dict[str, object]]:
        return [self.key]


@pytest.fixture
def signed_identity_token(tmp_path: Path) -> tuple[dict[str, str], LocalJwks]:
    openssl = shutil.which("openssl")
    if openssl is None:
        pytest.skip("openssl is required to generate a locally signed RSA token")
    private_key = tmp_path / "test-private.pem"
    public_key = tmp_path / "test-public.der"
    subprocess.run(
        [openssl, "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(private_key)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [openssl, "rsa", "-in", str(private_key), "-RSAPublicKey_out", "-outform", "DER", "-out", str(public_key)],
        check=True,
        capture_output=True,
    )
    der = public_key.read_bytes()
    assert der[0] == 0x30
    sequence_length = der[1]
    sequence_offset = 2
    if sequence_length & 0x80:
        count = sequence_length & 0x7F
        sequence_offset += count
    modulus_start = sequence_offset
    assert der[modulus_start] == 0x02
    modulus_length = der[modulus_start + 1]
    modulus_header = 2
    if modulus_length & 0x80:
        count = modulus_length & 0x7F
        modulus_length = int.from_bytes(der[modulus_start + 2 : modulus_start + 2 + count], "big")
        modulus_header += count
    modulus = int.from_bytes(der[modulus_start + modulus_header : modulus_start + modulus_header + modulus_length], "big")
    exponent_offset = modulus_start + modulus_header + modulus_length
    exponent = _der_integer(der[exponent_offset:])
    jwks = LocalJwks({"kid": "local-test-key", "kty": "RSA", "alg": "RS256", "n": _b64(modulus.to_bytes((modulus.bit_length() + 7) // 8, "big")), "e": _b64(exponent.to_bytes((exponent.bit_length() + 7) // 8, "big"))})

    now = datetime(2026, 9, 24, tzinfo=UTC)

    def sign(provider: str, issuer: str) -> str:
        header = _b64(json.dumps({"alg": "RS256", "kid": "local-test-key"}, separators=(",", ":")).encode())
        payload = _b64(json.dumps({"iss": issuer, "aud": "tracker-test", "sub": f"{provider}-user", "email": "player@example.test", "exp": int((now + timedelta(minutes=5)).timestamp()), "iat": int(now.timestamp())}, separators=(",", ":")).encode())
        signing_input = f"{header}.{payload}".encode("ascii")
        signature = subprocess.run(
            [openssl, "dgst", "-sha256", "-sign", str(private_key)],
            input=signing_input,
            check=True,
            capture_output=True,
        ).stdout
        return f"{header}.{payload}.{_b64(signature)}"

    return {
        "google": sign("google", "https://accounts.google.com"),
        "apple": sign("apple", "https://appleid.apple.com"),
    }, jwks


def test_locally_signed_provider_token_is_verified(signed_identity_token) -> None:
    tokens, jwks = signed_identity_token
    for provider, issuer in (("google", "https://accounts.google.com"), ("apple", "https://appleid.apple.com")):
        result = verify_identity_token(
            tokens[provider], provider, {"tracker-test"}, jwks,
            now=datetime(2026, 9, 24, tzinfo=UTC),
        )
        assert result == VerifiedIdentity(provider, issuer, f"{provider}-user", "player@example.test")
    with pytest.raises(AuthenticationError):
        verify_identity_token(tokens["google"], "google", {"other-client"}, jwks, now=datetime(2026, 9, 24, tzinfo=UTC))
    with pytest.raises(AuthenticationError):
        verify_identity_token(tokens["google"], "apple", {"tracker-test"}, jwks, now=datetime(2026, 9, 24, tzinfo=UTC))
    pieces = tokens["google"].split(".")
    signature = pieces[2]
    pieces[2] = signature[:10] + ("A" if signature[10] != "A" else "B") + signature[11:]
    tampered = ".".join(pieces)
    with pytest.raises(AuthenticationError):
        verify_identity_token(tampered, "google", {"tracker-test"}, jwks, now=datetime(2026, 9, 24, tzinfo=UTC))
    with pytest.raises(AuthenticationError):
        verify_identity_token("☃.☃.☃", "google", {"tracker-test"}, jwks)


def test_auth_identity_collision_is_blocked_with_recovery_route(database) -> None:
    identity = VerifiedIdentity("google", "https://accounts.google.com", "one", None)
    owner_id, _ = create_user_session(database, identity)
    other_id = str(uuid4())
    with database.begin() as connection:
        connection.execute(users.insert().values(id=other_id, created_at=datetime.now(UTC)))
    with pytest.raises(IdentityCollision) as error:
        attach_identity(database, other_id, identity)
    assert error.value.recovery_path == "/account/recovery"
    with database.connect() as connection:
        assert connection.execute(select(sessions.c.user_id).where(sessions.c.user_id == owner_id)).first()


def test_verified_login_reuses_existing_account_and_rotates_session(database, signed_identity_token) -> None:
    tokens, jwks = signed_identity_token
    identity = VerifiedIdentity("google", "https://accounts.google.com", "google-user", None)
    user_id, first = create_user_session(database, identity)
    same_user, second = login_with_identity_token(
        database, tokens["google"], "google", {"tracker-test"}, jwks,
        now=datetime(2026, 9, 24, tzinfo=UTC),
    )
    assert same_user == user_id
    assert second.session_id != first.session_id


def test_refresh_rotation_hashes_tokens_and_reuse_revokes_family(database) -> None:
    identity = VerifiedIdentity("apple", "https://appleid.apple.com", "apple-user", None)
    user_id, original = create_user_session(database, identity)
    assert authenticate_access_token(database, original.access_token) == user_id
    with database.connect() as connection:
        stored = connection.execute(select(sessions).where(sessions.c.id == original.session_id)).mappings().one()
    assert stored["refresh_hash"] != original.refresh_token
    assert stored["access_hash"] != original.access_token

    rotated = rotate_refresh_token(database, original.refresh_token)
    assert authenticate_access_token(database, rotated.access_token) == user_id
    with pytest.raises(RefreshTokenReuse):
        rotate_refresh_token(database, original.refresh_token)
    with database.connect() as connection:
        family = connection.execute(select(sessions).where(sessions.c.family_id == stored["family_id"])).mappings().all()
    assert all(row["revoked_at"] is not None for row in family)
    with pytest.raises(AuthenticationError):
        authenticate_access_token(database, rotated.access_token)
    with pytest.raises(AuthenticationError):
        authenticate_access_token(database, "☃")


def test_email_sender_interface_has_a_local_fake() -> None:
    sender = FakeEmailSender()
    sender.send_sign_in_code("player@example.test", "123456")
    assert sender.messages == [("player@example.test", "123456")]


def test_logout_revokes_only_the_presented_session(database) -> None:
    identity = VerifiedIdentity("google", "https://accounts.google.com", "logout-user", None)
    user_id, first = create_user_session(database, identity)
    _, second = create_user_session(database, identity)
    revoke_access_session(database, first.access_token)
    with pytest.raises(AuthenticationError):
        authenticate_access_token(database, first.access_token)
    assert authenticate_access_token(database, second.access_token) == user_id
