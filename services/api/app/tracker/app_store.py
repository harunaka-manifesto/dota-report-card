"""App Store JWS signature-chain verification behind `AppStoreVerifier`.

Apple signs transactions, renewal info and Server Notifications V2 as ES256
JWS values whose `x5c` header carries leaf, intermediate and root certificates.
This adapter accepts a payload only when that chain terminates in a root the
operator pinned by configuration, every certificate is valid at the signing
time, each link is signed by its parent and the Apple marker extensions are
present. It performs no network I/O (no OCSP); revocation checking is an
operational follow-up recorded in the implementation ledger.

Production verification requires the Apple Root CA G3 certificate and the
app's bundle identifier supplied by deployment configuration. Tests use a
locally generated chain; no claim of verified production Apple traffic follows.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import jwt
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from app.tracker.entitlement import EntitlementError, StoreTransaction

# Apple marker extensions: leaf (receipt signing) and WWDR intermediate.
LEAF_MARKER = x509.ObjectIdentifier("1.2.840.113635.100.6.11.1")
INTERMEDIATE_MARKER = x509.ObjectIdentifier("1.2.840.113635.100.6.2.1")
ENVIRONMENTS = {"Production", "Sandbox", "Xcode"}


@dataclass(frozen=True, slots=True)
class VerifiedNotification:
    notification_type: str
    subtype: str | None
    transaction: StoreTransaction


def _b64(value: str) -> bytes:
    return base64.b64decode(value + "=" * (-len(value) % 4))


def _ms(value: Any, field: str, *, required: bool = True) -> datetime | None:
    if value is None and not required:
        return None
    if type(value) is not int or value <= 0:
        raise EntitlementError(f"signed payload field {field} is invalid")
    return datetime.fromtimestamp(value / 1000, UTC)


class AppStoreJwsVerifier:
    def __init__(self, *, root_certificates: list[bytes], bundle_id: str,
                 environments: frozenset[str] = frozenset(ENVIRONMENTS),
                 require_markers: bool = True) -> None:
        if not root_certificates or not bundle_id:
            raise ValueError("A pinned root certificate and bundle identifier are required")
        self._roots = [x509.load_der_x509_certificate(der) if not der.startswith(b"-----")
                       else x509.load_pem_x509_certificate(der) for der in root_certificates]
        self._root_fingerprints = {root.fingerprint(hashes.SHA256()) for root in self._roots}
        self.bundle_id = bundle_id
        self.environments = environments
        self.require_markers = require_markers

    # -- chain -----------------------------------------------------------------
    def _verified_claims(self, token: str) -> dict[str, Any]:
        if not isinstance(token, str) or token.count(".") != 2 or len(token) > 64_000:
            raise EntitlementError("signed payload is malformed")
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise EntitlementError("signed payload header is malformed") from exc
        chain = header.get("x5c")
        if header.get("alg") != "ES256" or not isinstance(chain, list) or len(chain) != 3:
            raise EntitlementError("signed payload must carry an ES256 three-certificate chain")
        try:
            leaf, intermediate, root = (x509.load_der_x509_certificate(_b64(item)) for item in chain)
        except (TypeError, ValueError) as exc:
            raise EntitlementError("signed payload certificate chain is malformed") from exc
        if root.fingerprint(hashes.SHA256()) not in self._root_fingerprints:
            raise EntitlementError("certificate chain does not end in a pinned root")
        try:
            unverified = json.loads(_b64(token.split(".")[1]))
        except ValueError as exc:
            raise EntitlementError("signed payload body is malformed") from exc
        signed_at = unverified.get("signedDate")
        when = _ms(signed_at, "signedDate") if signed_at is not None else datetime.now(UTC)
        assert when is not None
        for child, parent in ((leaf, intermediate), (intermediate, root)):
            if not child.not_valid_before_utc <= when <= child.not_valid_after_utc:
                raise EntitlementError("certificate was not valid at signing time")
            key = parent.public_key()
            if not isinstance(key, ec.EllipticCurvePublicKey) or child.signature_hash_algorithm is None:
                raise EntitlementError("certificate chain uses an unsupported key")
            try:
                key.verify(child.signature, child.tbs_certificate_bytes,
                           ec.ECDSA(child.signature_hash_algorithm))
            except InvalidSignature as exc:
                raise EntitlementError("certificate chain signature is invalid") from exc
            if child.issuer != parent.subject:
                raise EntitlementError("certificate chain issuer mismatch")
        try:
            constraints = intermediate.extensions.get_extension_for_class(x509.BasicConstraints).value
        except x509.ExtensionNotFound as exc:
            raise EntitlementError("intermediate certificate is not a CA") from exc
        if not constraints.ca:
            raise EntitlementError("intermediate certificate is not a CA")
        if self.require_markers:
            for certificate, marker in ((leaf, LEAF_MARKER), (intermediate, INTERMEDIATE_MARKER)):
                try:
                    certificate.extensions.get_extension_for_oid(marker)
                except x509.ExtensionNotFound as exc:
                    raise EntitlementError("certificate lacks the store marker extension") from exc
        leaf_key = leaf.public_key()
        if not isinstance(leaf_key, ec.EllipticCurvePublicKey):
            raise EntitlementError("signing certificate uses an unsupported key")
        try:
            claims = jwt.decode(token, key=leaf_key, algorithms=["ES256"],
                                options={"verify_aud": False, "verify_exp": False,
                                         "verify_iat": False, "verify_nbf": False})
        except jwt.PyJWTError as exc:
            raise EntitlementError("signed payload signature is invalid") from exc
        if not isinstance(claims, dict):
            raise EntitlementError("signed payload body is malformed")
        return claims

    # -- payload mapping ---------------------------------------------------------
    def _transaction(self, claims: dict[str, Any], renewal: dict[str, Any] | None,
                     token: str) -> StoreTransaction:
        import hashlib

        if claims.get("bundleId") != self.bundle_id:
            raise EntitlementError("transaction belongs to another app")
        environment = claims.get("environment")
        if environment not in self.environments:
            raise EntitlementError("transaction environment is not accepted")
        original = claims.get("originalTransactionId")
        product = claims.get("productId")
        if not isinstance(original, str) or not isinstance(product, str):
            raise EntitlementError("transaction identity is missing")
        account = claims.get("appAccountToken")
        auto_renew = renewal.get("autoRenewStatus") if renewal else None
        signed_at = _ms(claims.get("signedDate"), "signedDate")
        expires_at = _ms(claims.get("expiresDate"), "expiresDate")
        assert signed_at is not None and expires_at is not None
        return StoreTransaction(
            original_transaction_id=original, user_id=account if isinstance(account, str) else None,
            product_id=product, environment=environment, signed_at=signed_at,
            expires_at=expires_at,
            revoked_at=_ms(claims.get("revocationDate"), "revocationDate", required=False),
            auto_renew=None if auto_renew is None else auto_renew == 1,
            digest=hashlib.sha256(token.encode()).hexdigest(),
        )

    def verify_transaction(self, signed_transaction: str) -> StoreTransaction:
        claims = self._verified_claims(signed_transaction)
        return self._transaction(claims, None, signed_transaction)

    def verify_notification_payload(self, signed_notification: str) -> VerifiedNotification:
        claims = self._verified_claims(signed_notification)
        data = claims.get("data")
        kind = claims.get("notificationType")
        if not isinstance(data, dict) or not isinstance(kind, str):
            raise EntitlementError("notification has no transaction data")
        if data.get("bundleId") != self.bundle_id:
            raise EntitlementError("notification belongs to another app")
        signed_transaction = data.get("signedTransactionInfo")
        if not isinstance(signed_transaction, str):
            raise EntitlementError("notification has no signed transaction")
        transaction = self._verified_claims(signed_transaction)
        renewal_token = data.get("signedRenewalInfo")
        renewal = self._verified_claims(renewal_token) if isinstance(renewal_token, str) else None
        if renewal is not None and renewal.get("originalTransactionId") != transaction.get("originalTransactionId"):
            raise EntitlementError("renewal info does not match the transaction")
        subtype = claims.get("subtype")
        return VerifiedNotification(kind, subtype if isinstance(subtype, str) else None,
                                    self._transaction(transaction, renewal, signed_notification))

    def verify_notification(self, signed_notification: str) -> StoreTransaction:
        return self.verify_notification_payload(signed_notification).transaction


def verifier_from_environment() -> AppStoreJwsVerifier | None:
    """Build the verifier only when both deployment inputs are configured."""
    import os
    from pathlib import Path

    root_path = os.getenv("TRACKER_APP_STORE_ROOT_CERT_PATH")
    bundle_id = os.getenv("TRACKER_APP_STORE_BUNDLE_ID")
    if not root_path or not bundle_id:
        return None
    environments = frozenset(
        value.strip() for value in os.getenv("TRACKER_APP_STORE_ENVIRONMENTS", "Production").split(",")
        if value.strip() in ENVIRONMENTS
    )
    return AppStoreJwsVerifier(root_certificates=[Path(root_path).read_bytes()], bundle_id=bundle_id,
                               environments=environments or frozenset({"Production"}))
