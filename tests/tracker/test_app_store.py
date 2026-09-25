from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from app.core.config import Settings
from app.tracker.app_store import (
    INTERMEDIATE_MARKER,
    LEAF_MARKER,
    AppStoreJwsVerifier,
)
from app.tracker.entitlement import EntitlementError
from app.tracker.mobile_api import create_mobile_app
from app.tracker.schema import history_operations, subscriptions
from app.tracker.store_api import create_store_app
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from fastapi.testclient import TestClient
from sqlalchemy import select

from .test_entitlement import ready_bootstrap

BUNDLE = "com.example.tracker"
NOW = datetime.now(UTC).replace(microsecond=0)


def _certificate(name, key, issuer_name, issuer_key, *, ca, marker=None, not_after=None):
    builder = (x509.CertificateBuilder()
               .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
               .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_name)]))
               .public_key(key.public_key()).serial_number(x509.random_serial_number())
               .not_valid_before(NOW - timedelta(days=1))
               .not_valid_after(not_after or NOW + timedelta(days=365))
               .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True))
    if marker is not None:
        builder = builder.add_extension(x509.UnrecognizedExtension(marker, b"\x05\x00"), critical=False)
    return builder.sign(issuer_key, hashes.SHA256())


class Chain:
    def __init__(self, *, leaf_marker=True, leaf_not_after=None):
        self.root_key = ec.generate_private_key(ec.SECP256R1())
        self.intermediate_key = ec.generate_private_key(ec.SECP256R1())
        self.leaf_key = ec.generate_private_key(ec.SECP256R1())
        self.root = _certificate("Test Root", self.root_key, "Test Root", self.root_key, ca=True)
        self.intermediate = _certificate("Test WWDR", self.intermediate_key, "Test Root", self.root_key,
                                         ca=True, marker=INTERMEDIATE_MARKER)
        self.leaf = _certificate("Test Signing", self.leaf_key, "Test WWDR", self.intermediate_key,
                                 ca=False, marker=LEAF_MARKER if leaf_marker else None,
                                 not_after=leaf_not_after)

    def root_der(self) -> bytes:
        return self.root.public_bytes(serialization.Encoding.DER)

    def sign(self, claims: dict) -> str:
        x5c = [base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode()
               for cert in (self.leaf, self.intermediate, self.root)]
        return jwt.encode(claims, self.leaf_key, algorithm="ES256", headers={"x5c": x5c})


def _ms(value: datetime) -> int:
    return int(value.timestamp() * 1000)


def transaction_claims(user_id: str | None, **overrides) -> dict:
    claims = {
        "bundleId": BUNDLE, "environment": "Sandbox", "originalTransactionId": "2000000001",
        "transactionId": "2000000002", "productId": "tracker.pro.monthly",
        "signedDate": _ms(NOW), "expiresDate": _ms(NOW + timedelta(days=30)),
    }
    if user_id is not None:
        claims["appAccountToken"] = user_id
    claims.update(overrides)
    return claims


def verifier(chain: Chain) -> AppStoreJwsVerifier:
    return AppStoreJwsVerifier(root_certificates=[chain.root_der()], bundle_id=BUNDLE)


def test_verifier_accepts_pinned_chain_and_maps_transaction():
    chain = Chain()
    tx = verifier(chain).verify_transaction(chain.sign(transaction_claims("user-1")))
    assert tx.user_id == "user-1" and tx.original_transaction_id == "2000000001"
    assert tx.environment == "Sandbox" and tx.revoked_at is None and len(tx.digest) == 64


@pytest.mark.parametrize("mutation", ["other_root", "bundle", "tamper", "marker", "expired_leaf", "alg"])
def test_verifier_rejects_untrusted_or_mismatched_payloads(mutation):
    chain = Chain(leaf_marker=mutation != "marker",
                  leaf_not_after=NOW - timedelta(seconds=1) if mutation == "expired_leaf" else None)
    trusted = Chain() if mutation == "other_root" else chain
    claims = transaction_claims("user-1", bundleId="com.other" if mutation == "bundle" else BUNDLE)
    token = chain.sign(claims)
    if mutation == "tamper":
        header, body, signature = token.split(".")
        forged = jwt.utils.base64url_encode(b'{"bundleId":"%s","environment":"Sandbox"}' % BUNDLE.encode()).decode()
        token = ".".join((header, forged, signature))
    if mutation == "alg":
        token = jwt.encode(claims, "secret-value-long-enough-for-hmac", algorithm="HS256",
                           headers={"x5c": jwt.get_unverified_header(token)["x5c"]})
    with pytest.raises(EntitlementError):
        verifier(trusted).verify_transaction(token)


def test_notification_requires_verified_nested_transaction_and_matching_renewal():
    chain = Chain()
    signed_tx = chain.sign(transaction_claims(None, revocationDate=_ms(NOW)))
    renewal = chain.sign({"originalTransactionId": "2000000001", "autoRenewStatus": 0,
                          "signedDate": _ms(NOW)})
    note = chain.sign({"notificationType": "REFUND", "signedDate": _ms(NOW),
                       "data": {"bundleId": BUNDLE, "signedTransactionInfo": signed_tx,
                                "signedRenewalInfo": renewal}})
    verified = verifier(chain).verify_notification_payload(note)
    assert verified.notification_type == "REFUND"
    assert verified.transaction.revoked_at is not None and verified.transaction.auto_renew is False
    foreign = Chain().sign(transaction_claims(None))
    bad = chain.sign({"notificationType": "DID_RENEW", "signedDate": _ms(NOW),
                      "data": {"bundleId": BUNDLE, "signedTransactionInfo": foreign}})
    with pytest.raises(EntitlementError):
        verifier(chain).verify_notification(bad)


def _session(database):
    from app.tracker.authentication import VerifiedIdentity, create_user_session
    from app.tracker.schema import dota_accounts, profiles

    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", "store-user", None,
    ))
    with database.begin() as connection:
        connection.execute(dota_accounts.insert().values(account_id=4242))
        connection.execute(profiles.insert().values(
            id="store-profile", user_id=user_id, account_id=4242, active=True,
            original_linked_at=NOW - timedelta(days=1),
        ))
    return user_id, {"Authorization": f"Bearer {tokens.access_token}"}


def test_mobile_submission_and_server_notification_drive_scope_operations(database):
    chain = Chain()
    store = verifier(chain)
    user_id, headers = _session(database)
    ready_bootstrap(database, "store-profile")
    mobile = TestClient(create_mobile_app(Settings(), database=database, store_verifier=store))
    assert mobile.get("/subscription", headers=headers).json() == {
        "billing_state": "NONE", "expires_at": None, "auto_renew": None, "scope": "FREE",
        "scope_revision": 0, "scope_change": "NONE", "target_scope": None,
    }
    signed = chain.sign(transaction_claims(user_id))
    missing_key = mobile.post("/subscription/transactions", headers=headers,
                              json={"signed_transaction": signed})
    assert missing_key.status_code == 422
    response = mobile.post("/subscription/transactions",
                           headers={**headers, "Idempotency-Key": "store-key-1"},
                           json={"signed_transaction": signed})
    assert response.status_code == 200, response.text
    view = response.json()
    assert view["billing_state"] == "ACTIVE" and view["scope"] == "FREE"
    assert view["scope_change"] == "PENDING" and view["target_scope"] == "PRO"
    replay = mobile.post("/subscription/transactions",
                         headers={**headers, "Idempotency-Key": "store-key-1"},
                         json={"signed_transaction": signed})
    assert replay.status_code == 200 and replay.json() == view
    foreign = chain.sign(transaction_claims("someone-else", originalTransactionId="2000000009"))
    rejected = mobile.post("/subscription/transactions",
                           headers={**headers, "Idempotency-Key": "store-key-2"},
                           json={"signed_transaction": foreign})
    assert rejected.status_code == 409 and rejected.json()["code"] == "TRANSACTION_OWNED_ELSEWHERE"

    webhook = TestClient(create_store_app(Settings(), database=database, verifier=store))
    assert webhook.post("/app-store/notifications", json={"signedPayload": "x" * 30}).status_code == 400
    refund_tx = chain.sign(transaction_claims(None, signedDate=_ms(NOW + timedelta(minutes=1)),
                                              revocationDate=_ms(NOW - timedelta(seconds=5))))
    note = chain.sign({"notificationType": "REFUND", "signedDate": _ms(NOW + timedelta(minutes=1)),
                       "data": {"bundleId": BUNDLE, "signedTransactionInfo": refund_tx}})
    applied = webhook.post("/app-store/notifications", json={"signedPayload": note})
    assert applied.status_code == 200 and applied.json() == {"applied": True}
    with database.connect() as connection:
        assert connection.scalar(select(subscriptions.c.state)) == "REVOKED"
        states = dict(connection.execute(select(history_operations.c.target_scope,
                                                history_operations.c.state)).all())
    assert states == {"PRO": "CANCELLED"}
    after = mobile.get("/subscription", headers=headers).json()
    assert after["billing_state"] == "REVOKED" and after["scope"] == "FREE"
    assert after["scope_change"] == "NONE"
    unknown = chain.sign({"notificationType": "DID_RENEW", "signedDate": _ms(NOW),
                          "data": {"bundleId": BUNDLE, "signedTransactionInfo": chain.sign(
                              transaction_claims(None, originalTransactionId="2999"))}})
    assert webhook.post("/app-store/notifications", json={"signedPayload": unknown}).json() == {"applied": False}


def test_store_routes_fail_closed_without_configured_verifier(database):
    _, headers = _session(database)
    mobile = TestClient(create_mobile_app(Settings(), database=database))
    response = mobile.post("/subscription/transactions",
                           headers={**headers, "Idempotency-Key": "store-key-1"},
                           json={"signed_transaction": "x" * 30})
    assert response.status_code == 503 and response.json()["code"] == "STORE_UNAVAILABLE"
    webhook = TestClient(create_store_app(Settings(), database=database))
    assert webhook.post("/app-store/notifications", json={"signedPayload": "x" * 30}).status_code == 503
    assert "/app-store/notifications" not in str(mobile.get("/openapi.json").json()["paths"])
