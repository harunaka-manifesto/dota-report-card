"""App Store entitlement intake and revision-fenced scope changes.

JWS chain validation is deliberately supplied by an adapter. This module ships
only the deterministic fake used by tests; it does not claim Apple production
verification.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import Connection, Engine, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from app.tracker.schema import (
    account_matches,
    bootstrap,
    history_operations,
    matches,
    profiles,
    subscriptions,
    users,
)


class EntitlementError(ValueError):
    """A verified store update cannot be safely applied to this account."""


@dataclass(frozen=True, slots=True)
class StoreTransaction:
    original_transaction_id: str
    user_id: str | None
    product_id: str
    environment: str
    signed_at: datetime
    expires_at: datetime
    revoked_at: datetime | None
    auto_renew: bool | None
    digest: str


class AppStoreVerifier(Protocol):
    def verify_transaction(self, signed_transaction: str) -> StoreTransaction: ...

    def verify_notification(self, signed_notification: str) -> StoreTransaction: ...


class FakeAppStoreVerifier:
    """Deterministic test adapter keyed by opaque fake signed values."""

    def __init__(self, transactions: dict[str, StoreTransaction]) -> None:
        self.transactions = transactions

    def verify_transaction(self, signed_transaction: str) -> StoreTransaction:
        try:
            return self.transactions["transaction:" + signed_transaction]
        except KeyError as exc:
            raise EntitlementError("invalid signed transaction") from exc

    def verify_notification(self, signed_notification: str) -> StoreTransaction:
        try:
            return self.transactions["notification:" + signed_notification]
        except KeyError as exc:
            raise EntitlementError("invalid signed notification") from exc


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise EntitlementError("store timestamps must include a timezone")
    return value.astimezone(UTC)


def _desired_scope(connection, user_id: str, now: datetime) -> str:
    live = connection.execute(select(subscriptions.c.original_transaction_id).where(
        subscriptions.c.user_id == user_id,
        subscriptions.c.expires_at > now,
        or_(subscriptions.c.revoked_at.is_(None), subscriptions.c.revoked_at > now),
    ).limit(1)).first()
    return "PRO" if live else "FREE"


def _gated_scope(connection, profile: Any, now: datetime) -> str:
    """Store-desired scope, withheld at FREE until both Free bootstrap modes settle."""
    if _desired_scope(connection, profile["user_id"], now) != "PRO":
        return "FREE"
    settled = connection.execute(select(bootstrap.c.mode).where(
        bootstrap.c.profile_id == profile["id"], bootstrap.c.mode.in_(("STANDARD", "TURBO")),
        bootstrap.c.completed_at.is_not(None),
    )).scalars().all()
    return "PRO" if set(settled) == {"STANDARD", "TURBO"} else "FREE"


def _request_scope_change(connection, *, profile: Any, target: str, now: datetime,
                          reason: str) -> str | None:
    current = connection.execute(select(history_operations).where(
        history_operations.c.profile_id == profile["id"],
        history_operations.c.state.in_(("PENDING", "RUNNING")),
    ).with_for_update()).mappings().first()
    if current and current["target_scope"] != target:
        connection.execute(update(history_operations).where(
            history_operations.c.id == current["id"]
        ).values(state="CANCELLED", completed_at=now))
    if profile["active_scope"] == target:
        return None
    if current and current["target_scope"] == target:
        return current["id"]
    operation_id = str(uuid4())
    cutoff = connection.execute(select(matches.c.started_at, matches.c.match_id).select_from(
        account_matches.join(matches, account_matches.c.match_id == matches.c.match_id)
    ).where(account_matches.c.profile_id == profile["id"], account_matches.c.lifecycle == "READY")
      .order_by(matches.c.started_at.desc(), matches.c.match_id.desc()).limit(1)).first()
    connection.execute(history_operations.insert().values(
        id=operation_id, profile_id=profile["id"], kind="ENTITLEMENT_REBUILD", state="PENDING",
        target_scope=target, target_revision=profile["active_revision"] + 1,
        cutoff_started_at=cutoff.started_at if cutoff else None,
        cutoff_match_id=cutoff.match_id if cutoff else None,
        cursor=None, dependency_scope={"reason": reason, "requested_at": now.isoformat()},
        created_at=now, completed_at=None,
        dedup_key=f"entitlement:{profile['id']}:{profile['active_revision'] + 1}:{target}:{operation_id}",
    ))
    from app.tracker.backfill import pro_history_days, request_pro_backfill
    from app.tracker.rebuild import enqueue_scope_rebuild

    if target == "PRO":
        # Same-kind P3 acquisition; one per profile generation, reused on resubscription.
        request_pro_backfill(connection, profile["id"], ceiling_days=pro_history_days())
    enqueue_scope_rebuild(connection, profile_id=profile["id"], operation_id=operation_id)
    return operation_id


def _apply(engine: Engine, tx: StoreTransaction, *, now: datetime) -> dict[str, object]:
    now, signed_at, expires_at = _utc(now), _utc(tx.signed_at), _utc(tx.expires_at)
    user_id = tx.user_id
    if not user_id:
        raise EntitlementError("transaction is not bound to an app account")
    if (not tx.original_transaction_id or len(tx.original_transaction_id) > 128
            or not tx.product_id or len(tx.product_id) > 128
            or tx.environment not in {"Production", "Sandbox", "Xcode"}
            or len(tx.digest) != 64 or any(c not in "0123456789abcdef" for c in tx.digest.lower())
            or expires_at <= signed_at):
        raise EntitlementError("verified transaction fields are invalid")
    revoked_at = _utc(tx.revoked_at) if tx.revoked_at else None
    with engine.begin() as connection:
        user = connection.execute(select(users).where(users.c.id == user_id).with_for_update()).mappings().first()
        if user is None or user["state"] != "ACTIVE":
            raise EntitlementError("account unavailable")
        profile = connection.execute(select(profiles).where(
            profiles.c.user_id == user_id, profiles.c.active.is_(True),
        ).with_for_update()).mappings().first()
        if profile is None:
            raise EntitlementError("a linked Steam account is required")
        existing = connection.execute(select(subscriptions).where(
            subscriptions.c.original_transaction_id == tx.original_transaction_id,
        ).with_for_update()).mappings().first()
        if existing and existing["user_id"] != user_id:
            raise EntitlementError("store transaction belongs to another account")
        # Older signed renewals/notifications cannot roll subscription state back.
        if existing and signed_at < existing["signed_at"]:
            desired = _gated_scope(connection, profile, now)
            return {"scope": profile["active_scope"], "operation_id": _request_scope_change(
                connection, profile=profile, target=desired, now=now, reason="STORE_UPDATE"
            ), "stale": True}
        values = dict(
            user_id=user_id, product_id=tx.product_id, environment=tx.environment,
            state="REVOKED" if revoked_at and revoked_at <= now else (
                "ACTIVE" if expires_at > now else "EXPIRED"
            ),
            signed_at=signed_at, expires_at=expires_at, revoked_at=revoked_at,
            auto_renew=tx.auto_renew, verification_digest=tx.digest.lower(),
        )
        stored = connection.execute(insert(subscriptions).values(
            original_transaction_id=tx.original_transaction_id, **values,
        ).on_conflict_do_update(
            index_elements=[subscriptions.c.original_transaction_id],
            set_=values,
            where=subscriptions.c.user_id == user_id,
        ).returning(subscriptions.c.original_transaction_id)).scalar_one_or_none()
        if stored is None:
            raise EntitlementError("store transaction belongs to another account")
        target = _gated_scope(connection, profile, now)
        operation_id = _request_scope_change(
            connection, profile=profile, target=target, now=now,
            reason="STORE_REVOKED" if target == "FREE" else "STORE_ACTIVE",
        )
        return {"scope": profile["active_scope"], "desired_scope": target,
                "operation_id": operation_id, "stale": False}


def submit_transaction(engine: Engine, *, user_id: str, signed_transaction: str,
                       verifier: AppStoreVerifier, now: datetime | None = None) -> dict[str, object]:
    tx = verifier.verify_transaction(signed_transaction)
    if tx.user_id is not None and tx.user_id != user_id:
        raise EntitlementError("transaction account does not match session")
    return _apply(engine, replace(tx, user_id=user_id), now=now or datetime.now(UTC))


def apply_notification(engine: Engine, *, signed_notification: str,
                       verifier: AppStoreVerifier, now: datetime | None = None) -> dict[str, object]:
    tx = verifier.verify_notification(signed_notification)
    # The signed Apple payload identifies the store transaction, not our app
    # account. Bind it only through a transaction already attached to a user.
    with engine.connect() as connection:
        owner = connection.execute(select(subscriptions.c.user_id).where(
            subscriptions.c.original_transaction_id == tx.original_transaction_id,
        )).scalar_one_or_none()
    if owner is None:
        raise EntitlementError("notification transaction is not attached to an account")
    tx = replace(tx, user_id=owner)
    return _apply(engine, tx, now=now or datetime.now(UTC))


def reconcile_entitlement_scope(engine: Engine, *, user_id: str,
                                now: datetime | None = None) -> dict[str, object]:
    """Queue a scope rebuild after purchases or when a Free foundation settles."""
    current = _utc(now or datetime.now(UTC))
    with engine.begin() as connection:
        user = connection.execute(select(users).where(users.c.id == user_id).with_for_update()).mappings().first()
        if user is None or user["state"] != "ACTIVE":
            raise EntitlementError("account unavailable")
        profile = connection.execute(select(profiles).where(
            profiles.c.user_id == user_id, profiles.c.active.is_(True),
        ).with_for_update()).mappings().first()
        if profile is None:
            raise EntitlementError("a linked Steam account is required")
        target = _gated_scope(connection, profile, current)
        operation_id = _request_scope_change(
            connection, profile=profile, target=target, now=current,
            reason="ENTITLEMENT_RECONCILE",
        )
        return {"scope": profile["active_scope"], "desired_scope": target,
                "operation_id": operation_id}


def reconcile_bootstrap_entitlement(connection: Connection, *, profile_id: str,
                                    now: datetime) -> str | None:
    """Queue a pending purchase once both Free mode settlements are coherent.

    Called inside bootstrap's profile-locked transaction, after terminality.
    """
    profile = connection.execute(select(profiles).where(
        profiles.c.id == profile_id, profiles.c.active.is_(True),
    ).with_for_update()).mappings().one_or_none()
    if profile is None or _desired_scope(connection, profile["user_id"], _utc(now)) != "PRO":
        return None
    return _request_scope_change(connection, profile=profile, target="PRO", now=now,
                                 reason="FREE_FOUNDATION_COMPLETE")


def complete_scope_rebuild(engine: Engine, *, user_id: str, operation_id: str,
                           now: datetime | None = None) -> int:
    """Replay retained history under the operation's scope and publish atomically.

    The worker path (`rebuild.complete_scope_rebuild_job`) and this direct call
    share `rebuild.run_scope_rebuild`; both publish scope, revision and every
    derived pointer in one transaction.
    """
    from app.tracker.rebuild import run_scope_rebuild

    current = _utc(now or datetime.now(UTC))
    with engine.begin() as connection:
        user = connection.execute(select(users.c.state).where(users.c.id == user_id).with_for_update()).scalar_one_or_none()
        if user != "ACTIVE":
            raise EntitlementError("account unavailable")
        profile = connection.execute(select(profiles).where(
            profiles.c.user_id == user_id, profiles.c.active.is_(True),
        ).with_for_update()).mappings().one_or_none()
        if profile is None:
            raise EntitlementError("scope rebuild is no longer active")
        operation = connection.execute(select(history_operations.c.state).where(
            history_operations.c.id == operation_id,
            history_operations.c.profile_id == profile["id"],
        )).scalar_one_or_none()
        if operation is None:
            raise EntitlementError("scope rebuild not found")
        outcome = run_scope_rebuild(connection, profile_id=profile["id"], operation_id=operation_id,
                                    now=current)
        revision = connection.scalar(select(profiles.c.active_revision).where(profiles.c.id == profile["id"]))
    if outcome == "WAITING_FOR_HISTORY":
        raise EntitlementError("scope rebuild is waiting for historical acquisition")
    if outcome != "COMPLETE":
        raise EntitlementError("scope transaction is no longer active")
    return int(revision or 0)


def fake_digest(token: str) -> str:
    """Stable digest helper for tests, never used as signature verification."""
    return hashlib.sha256(token.encode()).hexdigest()
