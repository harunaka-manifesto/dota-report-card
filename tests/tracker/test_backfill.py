"""Pro backfill is same-kind P3 work; activation waits for it; resubscription reuses it."""
from __future__ import annotations

from datetime import timedelta

import httpx
from app.core.config import Settings
from app.tracker.backfill import backfill_page
from app.tracker.entitlement import (
    FakeAppStoreVerifier,
    apply_notification,
    reconcile_entitlement_scope,
    submit_transaction,
)
from app.tracker.jobs import claim
from app.tracker.rebuild import complete_scope_rebuild_job
from app.tracker.schema import (
    account_matches,
    ingest_jobs,
    profiles,
    provider_calls,
)
from sqlalchemy import func, select, update

from .builders import add_match, finalize, history
from .test_entitlement import NOW, ready_bootstrap, transaction
from .test_provider_transport import gate_for
from .test_schema import identity


def _claim(database, job_type):
    with database.begin() as connection:
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.job_type == job_type,
                                                     ingest_jobs.c.state == "PENDING")
                           .values(run_after=func.clock_timestamp() - timedelta(days=1)))
        job = claim(connection, priority=3)
    assert job is not None and job["job_type"] == job_type, job
    return job


async def test_purchase_backfills_only_unheld_pre_link_history_and_activation_waits(database, redis_client, monkeypatch):
    monkeypatch.setenv("TRACKER_PRO_HISTORY_DAYS", "365")
    user_id, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    held = history(database, profile_id, [0], origin="BOOTSTRAP", offset_days=[-3])
    verifier = FakeAppStoreVerifier({
        "transaction:pro": transaction(user_id, token="pro"),
        "notification:expire": transaction(user_id, token="expire", signed=NOW + timedelta(days=1),
                                           revoked=NOW + timedelta(days=1)),
        "notification:renew": transaction(user_id, token="renew", signed=NOW + timedelta(days=2),
                                          expires=NOW + timedelta(days=60)),
    })
    submit_transaction(database, user_id=user_id, signed_transaction="pro", verifier=verifier, now=NOW)
    reconcile_entitlement_scope(database, user_id=user_id, now=NOW)

    scope = _claim(database, "SCOPE_REBUILD")
    assert complete_scope_rebuild_job(database, job_id=scope["id"], lease_token=scope["lease_token"]) == "WAITING_FOR_HISTORY"
    with database.connect() as connection:
        assert connection.execute(select(profiles.c.active_scope)).scalar_one() == "FREE"

    def stamp(days):
        return int((NOW + timedelta(days=days)).timestamp())
    page = [
        {"match_id": 77, "start_time": stamp(1), "game_mode": 22},        # post-link: Free history
        {"match_id": held[0], "start_time": stamp(-3), "game_mode": 22},  # already held
        {"match_id": 78, "start_time": stamp(-40), "game_mode": 23},
        {"match_id": 79, "start_time": stamp(-41), "game_mode": 2},       # unsupported mode
        {"match_id": 80, "start_time": stamp(-200), "game_mode": 22},
        {"match_id": 81, "start_time": stamp(-500), "game_mode": 22},     # beyond the ceiling
    ]
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.params["significant"] == "0"
        return httpx.Response(200, json=page)

    job = _claim(database, "PRO_BACKFILL")
    outcome = await backfill_page(database, gate_for(redis_client, "opendota"), Settings(), job_id=job["id"],
                                  lease_token=job["lease_token"], transport=httpx.MockTransport(handler))
    assert outcome == "COMPLETE" and len(calls) == 1
    with database.connect() as connection:
        batches = connection.execute(select(ingest_jobs.c.payload).where(
            ingest_jobs.c.job_type == "HISTORICAL_BATCH")).scalars().all()
    assert [batch["match_ids"] for batch in batches] == [[78, 80]]
    assert all(batch["origin"] == "HISTORICAL" for batch in batches)

    # Acquisition still pending → activation keeps waiting on the coherent Free state.
    scope = _claim(database, "SCOPE_REBUILD")
    assert complete_scope_rebuild_job(database, job_id=scope["id"], lease_token=scope["lease_token"]) == "WAITING_FOR_HISTORY"
    with database.begin() as connection:
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.job_type == "HISTORICAL_BATCH")
                           .values(state="COMPLETE"))
    scope = _claim(database, "SCOPE_REBUILD")
    assert complete_scope_rebuild_job(database, job_id=scope["id"], lease_token=scope["lease_token"]) == "COMPLETE"
    with database.connect() as connection:
        assert connection.execute(select(profiles.c.active_scope)).scalar_one() == "PRO"
        calls_after_activation = connection.scalar(select(func.count()).select_from(provider_calls))

    apply_notification(database, signed_notification="expire", verifier=verifier, now=NOW + timedelta(days=1))
    scope = _claim(database, "SCOPE_REBUILD")
    assert complete_scope_rebuild_job(database, job_id=scope["id"], lease_token=scope["lease_token"]) == "COMPLETE"
    apply_notification(database, signed_notification="renew", verifier=verifier, now=NOW + timedelta(days=2))
    with database.connect() as connection:
        # Resubscription reuses the completed backfill: no second scan is queued.
        assert connection.scalar(select(func.count()).select_from(ingest_jobs).where(
            ingest_jobs.c.job_type == "PRO_BACKFILL")) == 1
    scope = _claim(database, "SCOPE_REBUILD")
    assert complete_scope_rebuild_job(database, job_id=scope["id"], lease_token=scope["lease_token"]) == "COMPLETE"
    with database.connect() as connection:
        assert connection.execute(select(profiles.c.active_scope, profiles.c.active_revision)).one() == ("PRO", 3)
        assert connection.scalar(select(func.count()).select_from(provider_calls)) == calls_after_activation


def test_live_match_never_waits_on_imported_history(database):
    _, profile_id = identity(database)
    pending_import = add_match(database, profile_id, index=1, origin="HISTORICAL", offset_days=-5)
    live = add_match(database, profile_id, index=2, offset_days=1)
    assert finalize(database, profile_id, live) == "READY"
    with database.connect() as connection:
        assert connection.scalar(select(account_matches.c.lifecycle).where(
            account_matches.c.match_id == pending_import)) == "ANALYZING"
