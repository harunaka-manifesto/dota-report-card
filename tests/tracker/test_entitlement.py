from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from app.tracker.entitlement import (
    EntitlementError,
    FakeAppStoreVerifier,
    StoreTransaction,
    apply_notification,
    complete_scope_rebuild,
    fake_digest,
    reconcile_entitlement_scope,
    submit_transaction,
)
from app.tracker.schema import bootstrap, history_operations, profiles, subscriptions
from sqlalchemy import insert, select

from .test_schema import NOW, identity


def transaction(user_id: str, *, token: str = "active", expires: datetime | None = None,
                revoked: datetime | None = None, signed: datetime = NOW) -> StoreTransaction:
    return StoreTransaction(
        original_transaction_id="original-transaction-1", user_id=user_id,
        product_id="tracker.pro.monthly", environment="Sandbox", signed_at=signed,
        expires_at=expires or NOW + timedelta(days=30), revoked_at=revoked,
        auto_renew=True, digest=fake_digest(token),
    )


def ready_bootstrap(database, profile_id: str) -> None:
    with database.begin() as c:
        for mode in ("STANDARD", "TURBO"):
            c.execute(insert(bootstrap).values(
                profile_id=profile_id, mode=mode, search_finished=True,
                discovered_count=0, eligible_count=0, settled_count=0,
                outcome="NO_MATCHES_FOUND", completed_at=NOW,
            ))


def test_purchase_waits_for_free_foundation_and_publishes_only_after_rebuild(database):
    user_id, profile_id = identity(database)
    tx = transaction(user_id)
    verifier = FakeAppStoreVerifier({"transaction:good": tx})
    result = reconcile_entitlement_scope(database, user_id=user_id, now=NOW)
    assert result == {"scope": "FREE", "desired_scope": "FREE", "operation_id": None}
    ready_bootstrap(database, profile_id)
    submit_transaction(database, user_id=user_id, signed_transaction="good", verifier=verifier, now=NOW)
    result = reconcile_entitlement_scope(database, user_id=user_id, now=NOW)
    assert result["desired_scope"] == "PRO" and result["operation_id"]
    with database.connect() as c:
        op = c.execute(select(history_operations).where(
            history_operations.c.id == result["operation_id"]
        )).mappings().one()
        assert op["kind"] == "ENTITLEMENT_REBUILD" and op["target_scope"] == "PRO"
        assert c.execute(select(profiles.c.active_scope, profiles.c.active_revision).where(
            profiles.c.id == profile_id
        )).one() == ("FREE", 0)
    assert complete_scope_rebuild(database, user_id=user_id, operation_id=op["id"], now=NOW) == 1
    with database.connect() as c:
        assert c.execute(select(profiles.c.active_scope, profiles.c.active_revision).where(
            profiles.c.id == profile_id
        )).one() == ("PRO", 1)


def test_refund_notification_switches_scope_and_retains_transaction(database):
    user_id, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    live = transaction(user_id)
    revoked = transaction(user_id, token="refund", signed=NOW + timedelta(days=1), revoked=NOW + timedelta(days=1))
    verifier = FakeAppStoreVerifier({"transaction:purchase": live, "notification:refund": revoked})
    activated = submit_transaction(database, user_id=user_id, signed_transaction="purchase",
                                   verifier=verifier, now=NOW)
    complete_scope_rebuild(database, user_id=user_id, operation_id=activated["operation_id"], now=NOW)
    result = apply_notification(database, signed_notification="refund", verifier=verifier,
                                now=NOW + timedelta(days=1))
    assert result["scope"] == "PRO" and result["desired_scope"] == "FREE"
    assert result["operation_id"]
    complete_scope_rebuild(database, user_id=user_id, operation_id=result["operation_id"],
                           now=NOW + timedelta(days=1))
    with database.connect() as c:
        assert c.execute(select(profiles.c.active_scope).where(profiles.c.id == profile_id)).scalar_one() == "FREE"
        assert c.execute(select(subscriptions.c.state, subscriptions.c.revoked_at).where(
            subscriptions.c.original_transaction_id == live.original_transaction_id
        )).one() == ("REVOKED", revoked.revoked_at)


def test_revoked_scope_cannot_publish_after_store_expiry_and_cached_record_survives(database):
    user_id, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    live = transaction(user_id)
    verifier = FakeAppStoreVerifier({"transaction:purchase": live})
    result = submit_transaction(database, user_id=user_id, signed_transaction="purchase",
                                verifier=verifier, now=NOW)
    activated_operation_id = result["operation_id"]
    assert isinstance(activated_operation_id, str)
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == profile_id).values(active_scope="PRO", active_revision=1))
    expired = transaction(user_id, token="expired", signed=NOW + timedelta(days=30), expires=NOW + timedelta(days=30))
    verifier.transactions["notification:expiry"] = expired
    # Expiry is derived from signed expiration even if no store notification arrives.
    result = submit_transaction(database, user_id=user_id, signed_transaction="purchase",
                                verifier=verifier, now=NOW + timedelta(days=31))
    assert result["desired_scope"] == "FREE" and result["operation_id"]
    with pytest.raises(EntitlementError, match="no longer active"):
        complete_scope_rebuild(database, user_id=user_id, operation_id=activated_operation_id,
                               now=NOW + timedelta(days=31))
    with database.connect() as c:
        assert c.execute(select(subscriptions.c.original_transaction_id).where(
            subscriptions.c.user_id == user_id
        )).scalar_one() == live.original_transaction_id


def test_purchase_rejects_missing_steam_and_foreign_transaction(database):
    user_id, profile_id = identity(database)
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == profile_id).values(active=False))
    verifier = FakeAppStoreVerifier({"transaction:good": transaction(user_id)})
    with pytest.raises(EntitlementError, match="linked Steam"):
        submit_transaction(database, user_id=user_id, signed_transaction="good", verifier=verifier, now=NOW)

    owner, _ = identity(database, account_id=2002)
    tx = transaction(owner)
    verifier.transactions["transaction:foreign"] = tx
    with pytest.raises(EntitlementError, match="does not match session"):
        submit_transaction(database, user_id=user_id, signed_transaction="foreign", verifier=verifier, now=NOW)
