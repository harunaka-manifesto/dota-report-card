from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.tracker.account_lifecycle import (
    AccountLifecycleError,
    request_account_deletion,
    switch_preflight,
    switch_steam_profile,
)
from app.tracker.jobs import StaleJob, authorized_job, claim, enqueue
from app.tracker.schema import (
    bootstrap,
    devices,
    events,
    identities,
    ingest_jobs,
    matches,
    profiles,
    sessions,
    subscriptions,
    switches,
    users,
)
from sqlalchemy import func, insert, select, update

from .test_schema import NOW, identity, summary


def test_switch_archives_fences_jobs_and_starts_fresh_bootstrap(database):
    user_id, old_profile = identity(database)
    current = datetime.now(UTC)
    with database.begin() as connection:
        job_id = enqueue(connection, dedup_key="live-before-switch", job_type="LINK_MATCH",
                         priority=0, payload={}, profile_id=old_profile)
        connection.execute(insert(subscriptions).values(
            original_transaction_id="tx-switch", user_id=user_id, product_id="pro",
            environment="Sandbox", state="ACTIVE", signed_at=NOW,
            expires_at=NOW + timedelta(days=30), auto_renew=True,
            verification_digest="a" * 64,
        ))

    new_profile = switch_steam_profile(
        database, user_id=user_id, verified_target_account_id=2002, now=current,
    )
    with database.connect() as connection:
        old = connection.execute(select(profiles).where(profiles.c.id == old_profile)).mappings().one()
        new = connection.execute(select(profiles).where(profiles.c.id == new_profile)).mappings().one()
        assert old["active"] is False and old["archived_at"] is not None
        assert new["active"] is True and new["active_scope"] == "FREE"
        assert new["original_linked_at"] == current
        assert connection.execute(select(bootstrap.c.mode).where(
            bootstrap.c.profile_id == new_profile,
        )).scalars().all() == ["STANDARD", "TURBO"]
        assert connection.execute(select(ingest_jobs.c.state).where(
            ingest_jobs.c.id == job_id,
        )).scalar_one() == "CANCELLED"
        assert connection.execute(select(subscriptions.c.auto_renew).where(
            subscriptions.c.user_id == user_id,
        )).scalar_one() is True
        assert connection.execute(select(switches.c.id).where(
            switches.c.user_id == user_id,
        )).scalar_one()
    with pytest.raises(StaleJob):
        with authorized_job(database, job_id, "stale-token"):
            pytest.fail("switched profile job was allowed to publish")


def test_switch_preflight_reports_cooldown_history_and_owned_target(database):
    user_id, _ = identity(database, account_id=1001)
    other_user, _ = identity(database, account_id=3003)
    current = datetime.now(UTC)
    switch_steam_profile(database, user_id=user_id, verified_target_account_id=2002, now=current)
    owned = switch_preflight(database, user_id=user_id, verified_target_account_id=3003,
                             now=current + timedelta(days=20))
    assert owned["cause"] == "TARGET_OWNED_BY_ANOTHER_ACCOUNT"
    result = switch_preflight(database, user_id=user_id, verified_target_account_id=4004,
                              now=current + timedelta(days=20))
    assert result["cause"] == "SWITCH_COOLDOWN"
    with database.connect() as connection:
        completed_at = connection.execute(select(switches.c.completed_at).where(
            switches.c.user_id == user_id,
        )).scalar_one()
    assert result["days_remaining"] == math.ceil(
        (completed_at + timedelta(days=90) - (current + timedelta(days=20))).total_seconds() / 86400
    )
    assert result["active_profile_id"]
    with database.begin() as connection:
        owner_profile = connection.execute(select(profiles.c.id).where(
            profiles.c.user_id == other_user, profiles.c.active.is_(True),
        )).scalar_one()
        enqueue(connection, dedup_key="pending-historical", job_type="HISTORICAL_BATCH",
                priority=3, payload={"origin": "HISTORICAL"}, profile_id=owner_profile)
    result = switch_preflight(database, user_id=other_user, verified_target_account_id=4004,
                              now=current + timedelta(days=100))
    assert result["cause"] == "HISTORICAL_WORK_RUNNING"
    with pytest.raises(AccountLifecycleError, match="HISTORICAL_WORK_RUNNING"):
        switch_steam_profile(database, user_id=other_user,
                             verified_target_account_id=4004, now=current + timedelta(days=100))


def test_switch_back_to_archived_identity_creates_new_isolated_profile(database):
    user_id, original_profile = identity(database, account_id=1001)
    current = datetime.now(UTC)
    switch_steam_profile(database, user_id=user_id, verified_target_account_id=2002, now=current)
    assert switch_preflight(database, user_id=user_id, verified_target_account_id=1001,
                            now=current + timedelta(days=91))["cause"] == "HISTORICAL_WORK_RUNNING"
    with database.begin() as connection:
        active_id = connection.scalar(select(profiles.c.id).where(
            profiles.c.user_id == user_id, profiles.c.active.is_(True),
        ))
        connection.execute(update(ingest_jobs).where(
            ingest_jobs.c.job_type == "BOOTSTRAP_SEARCH", ingest_jobs.c.user_id == user_id,
        ).values(state="COMPLETE"))
        connection.execute(update(bootstrap).where(
            bootstrap.c.profile_id == active_id,
        ).values(search_finished=True, completed_at=func.clock_timestamp(), outcome="NO_MATCHES_FOUND"))
    result = switch_preflight(database, user_id=user_id, verified_target_account_id=1001,
                              now=current + timedelta(days=91))
    assert result["available"] is True
    relinked = switch_steam_profile(database, user_id=user_id,
                                   verified_target_account_id=1001, now=current + timedelta(days=91))
    assert relinked != original_profile
    with database.connect() as connection:
        versions = connection.execute(select(profiles.c.id, profiles.c.active).where(
            profiles.c.user_id == user_id, profiles.c.account_id == 1001,
        )).all()
        assert set(versions) == {(original_profile, False), (relinked, True)}
        assert connection.execute(select(bootstrap.c.mode).where(
            bootstrap.c.profile_id == relinked,
        )).scalars().all() == ["STANDARD", "TURBO"]


def test_deletion_immediately_fences_and_removes_private_profile_state(database):
    user_id, profile_id = identity(database)
    summary(database)
    with database.begin() as connection:
        connection.execute(insert(events).values(
            id=str(uuid4()), profile_id=profile_id, kind="MATCH_READY",
            dedup_key="private-event", payload={}, created_at=NOW,
        ))
        connection.execute(insert(identities).values(
            id=str(uuid4()), user_id=user_id, issuer="https://issuer", subject="subject",
            verified_at=NOW,
        ))
        connection.execute(insert(sessions).values(
            id=str(uuid4()), user_id=user_id, family_id=str(uuid4()), refresh_hash="r" * 64,
            access_hash="a" * 64, user_generation=1, created_at=NOW,
            access_expires_at=NOW + timedelta(hours=1), expires_at=NOW + timedelta(days=1),
        ))
        connection.execute(insert(devices).values(
            id=str(uuid4()), user_id=user_id, permission="GRANTED", last_active_at=NOW,
        ))
        job_id = enqueue(connection, dedup_key="delete-fence", job_type="LINK_MATCH",
                         priority=0, payload={}, profile_id=profile_id)
        user_job_id = str(uuid4())
        connection.execute(insert(ingest_jobs).values(
            id=user_job_id, dedup_key="delete-user-only", job_type="ACCOUNT_TASK",
            priority=2, user_id=user_id, user_generation=1, payload={},
            run_after=NOW, created_at=NOW,
        ))
        job = claim(connection, priority=0)
        assert job["id"] == job_id

    result = request_account_deletion(database, user_id=user_id)
    assert result["state"] == "DELETION_PENDING"
    with database.connect() as connection:
        user = connection.execute(select(users).where(users.c.id == user_id)).mappings().one()
        assert user["generation"] == 2 and user["deletion_requested_at"] is not None
        assert connection.execute(select(profiles.c.id).where(
            profiles.c.user_id == user_id,
        )).first() is None
        assert connection.execute(select(identities.c.id).where(
            identities.c.user_id == user_id,
        )).first() is None
        assert connection.execute(select(sessions.c.id).where(
            sessions.c.user_id == user_id,
        )).first() is None
        assert connection.execute(select(devices.c.id).where(
            devices.c.user_id == user_id,
        )).first() is None
        assert connection.execute(select(events.c.id).where(
            events.c.profile_id == profile_id,
        )).first() is None
        assert connection.execute(select(matches.c.match_id)).scalar_one() == 9_000_000_001
        assert connection.execute(select(ingest_jobs.c.state).where(
            ingest_jobs.c.id == user_job_id,
        )).scalar_one() == "CANCELLED"
    with pytest.raises(StaleJob):
        with authorized_job(database, job_id, job["lease_token"]):
            pytest.fail("deletion-pending account job was allowed to publish")
    assert request_account_deletion(database, user_id=user_id)["generation"] == 2
