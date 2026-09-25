"""Opt-in live provider smoke through the real tracker worker path.

Never runs in ordinary CI. `RUN_LIVE_TRACKER_SMOKE=1` enables the OpenDota
fresh path; `RUN_LIVE_STRATZ=1` additionally enables one STRATZ historical
batch. STRATZ tokens are IP-bound: run it only from a machine whose address
no deployed service shares the token with. Each test stops at a hard call
budget and records every call in `tracker_provider_calls`.
"""
from __future__ import annotations

import os
from collections import Counter
from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import Settings
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.historical import enqueue_historical_batch
from app.tracker.mobile_api import create_mobile_app
from app.tracker.provider_control import ProviderGate
from app.tracker.schema import (
    account_discoveries,
    account_matches,
    acquisitions,
    dota_accounts,
    ingest_jobs,
    matches,
    profiles,
    provider_calls,
    sync_state,
)
from app.tracker.worker import WorkerPolicy, run_one
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select

from .test_entitlement import ready_bootstrap

pytestmark = pytest.mark.live

# The repository's existing public test/evidence account (tests/live).
ACCOUNT = int(os.getenv("TRACKER_LIVE_ACCOUNT_ID", "193875165"))
OPENDOTA_BUDGET = 8
STOPS = {"IDLE", "OPERATOR_PAUSED", "PROVIDER_BUDGET", "P1_DEPTH", "P1_AGE", "P2_REDUCED_SHARE", "RUNNING"}


def _live_settings() -> Settings:
    if os.getenv("RUN_LIVE_TRACKER_SMOKE") != "1":
        pytest.skip("Live tracker smoke is opt-in and never runs in ordinary CI.")
    key = os.getenv("OPENDOTA_API_KEY")
    if not key:
        pytest.skip("OPENDOTA_API_KEY is required for live tracker smoke")
    return Settings(opendota_source="live", opendota_api_key=key,
                    stratz_api_token=os.getenv("STRATZ_API_TOKEN") or os.getenv("STRATZ_API_KEY") or None)


def _owner(database, subject: str, linked_at: datetime) -> tuple[str, str]:
    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", subject, None))
    profile_id = f"live-{subject}"
    with database.begin() as connection:
        connection.execute(insert(dota_accounts).values(account_id=ACCOUNT))
        connection.execute(profiles.insert().values(id=profile_id, user_id=user_id, account_id=ACCOUNT,
                                                    active=True, original_linked_at=linked_at))
    ready_bootstrap(database, profile_id)
    return profile_id, tokens.access_token


def _calls(database, provider: str) -> list[dict]:
    with database.connect() as connection:
        return [dict(row) for row in connection.execute(select(provider_calls).where(
            provider_calls.c.provider == provider).order_by(provider_calls.c.id)).mappings()]


async def test_live_opendota_fresh_path_discovers_and_materializes(database, redis_client):
    settings = _live_settings()
    redis, namespace = redis_client
    policy = WorkerPolicy(namespace=namespace)
    days = int(os.getenv("TRACKER_LIVE_LINK_DAYS", "30"))
    profile_id, token = _owner(database, "opendota", datetime.now(UTC) - timedelta(days=days))
    client = TestClient(create_mobile_app(settings, database=database))
    response = client.post("/sync", headers={"Authorization": f"Bearer {token}", "Idempotency-Key": "live-sync-1"})
    assert response.status_code in {200, 202}, response.text

    outcomes = []
    for _ in range(40):
        results = []
        # P0-P2 only: replay processing waits 360 s and is not requested here.
        for priority in range(3):
            if len(_calls(database, "opendota")) >= OPENDOTA_BUDGET:
                break
            results.append(await run_one(database, redis, settings, priority=priority, policy=policy))
        outcomes.extend(results)
        if len(results) < 3 or all(result in STOPS for result in results):
            break

    with database.connect() as connection:
        state = connection.execute(select(sync_state.c.state, sync_state.c.blocked_reason).where(
            sync_state.c.account_id == ACCOUNT)).one()
    # Budget spent: open the shared breaker so only provider-free work (links) proceeds.
    gate = ProviderGate(redis, namespace=namespace, provider="opendota")
    for _ in range(10):
        gate.observe({}, status=503)
    spent = len(_calls(database, "opendota"))
    for _ in range(80):
        if await run_one(database, redis, settings, priority=0, policy=policy) in STOPS:
            break
    assert len(_calls(database, "opendota")) == spent

    calls = _calls(database, "opendota")
    print(f"\nopendota calls={len(calls)} statuses={[c['status'] for c in calls]} "
          f"operations={[c['operation'] for c in calls]} outcomes={outcomes}")
    assert 1 <= len(calls) <= OPENDOTA_BUDGET
    assert all(call["status"] == 200 for call in calls)
    with database.connect() as connection:
        history = [c for c in calls if c["operation"] == "history"]
        assert history, "the foreground sync read no history page"
        found = connection.execute(select(matches.c.match_id, matches.c.evidence_state, matches.c.mode)).all()
        links = connection.execute(select(account_matches.c.match_id, account_matches.c.lifecycle,
                                          account_matches.c.effective_role).where(
            account_matches.c.profile_id == profile_id)).all()
        journal = connection.execute(select(account_discoveries.c.outcome, account_discoveries.c.reason,
                                            func.count()).group_by(account_discoveries.c.outcome,
                                                                   account_discoveries.c.reason)).all()
        summaries = connection.scalar(select(func.count()).select_from(ingest_jobs).where(
            ingest_jobs.c.job_type == "SUMMARY", ingest_jobs.c.state == "COMPLETE"))
    print(f"journal={[tuple(row) for row in journal]}")
    print(f"sync={tuple(state)} matches={[tuple(m) for m in found]} links={[tuple(link) for link in links]}")
    assert state.state in {"UP_TO_DATE", "CHECKING"}
    # Every summary actually fetched was materialized and linked to the owner.
    fetched = {c["match_id"] for c in calls if c["operation"] == "match"}
    materialized = {m.match_id for m in found if m.evidence_state != "DISCOVERED"}
    assert fetched <= materialized and summaries >= len(fetched)
    assert fetched <= {link.match_id for link in links}


async def test_live_stratz_historical_batch_settles_every_match(database, redis_client):
    settings = _live_settings()
    if os.getenv("RUN_LIVE_STRATZ") != "1" or not settings.stratz_api_token:
        pytest.skip("Live STRATZ is opt-in separately (IP-bound token).")
    redis, namespace = redis_client
    policy = WorkerPolicy(namespace=namespace)
    import httpx
    from app.opendota.client import OpenDotaClient
    from app.tracker.provider_transport import ControlledTransport

    # Through the controlled transport, as production foreground work observes OpenDota's window.
    opendota_gate = ProviderGate(redis, namespace=namespace, provider="opendota")
    async with httpx.AsyncClient(transport=ControlledTransport(opendota_gate, database)) as http:
        rows = await OpenDotaClient(settings, http_client=http).get_history_page(ACCOUNT, offset=0, days=30)
    size = int(os.getenv("TRACKER_LIVE_STRATZ_BATCH", "5"))
    ids = sorted({row["match_id"] for row in rows if row.get("game_mode") in (1, 22, 23)})[-size:]
    assert ids, "no recent supported matches for the live account"
    profile_id, _ = _owner(database, "stratz", datetime.now(UTC))
    with database.begin() as connection:
        enqueue_historical_batch(connection, profile_id=profile_id, match_ids=ids, origin="HISTORICAL")

    outcomes = []
    for _ in range(6):
        if len(_calls(database, "stratz")) >= 2:
            break
        outcome = await run_one(database, redis, settings, priority=3, policy=policy)
        outcomes.append(outcome)
        if outcome in STOPS:
            break
    calls = _calls(database, "stratz")
    with database.connect() as connection:
        states = dict(connection.execute(select(matches.c.match_id, matches.c.evidence_state).where(
            matches.c.match_id.in_(ids))).all())
        batch = connection.execute(select(ingest_jobs.c.state, ingest_jobs.c.last_error).where(
            ingest_jobs.c.job_type == "HISTORICAL_BATCH")).one()
        fallback = set(connection.scalars(select(ingest_jobs.c.match_id).where(
            ingest_jobs.c.job_type == "HISTORICAL_SUMMARY")))
        acquired = connection.execute(select(acquisitions.c.match_id, acquisitions.c.state,
                                             acquisitions.c.terminal_reason).where(
            acquisitions.c.provider == "stratz")).all()
    print(f"\nstratz calls={len(calls)} statuses={[c['status'] for c in calls]} "
          f"units={[(c['rate_units'], c['billed_units']) for c in calls]} outcomes={outcomes} "
          f"batch={tuple(batch)} states={Counter(states.values())} fallback={len(fallback)} "
          f"stratz_acquisitions={Counter((row.state, row.terminal_reason) for row in acquired)}")
    assert 1 <= len(calls) <= 2 and all(call["status"] == 200 for call in calls)
    assert batch.state == "COMPLETE", batch
    assert set(states) == set(ids)
    # Each match is settled by the batch or handed to the per-match summary route.
    assert all(state in {"REPLAY_READY", "REPLAY_UNAVAILABLE", "SUMMARY_READY"} or match_id in fallback
               for match_id, state in states.items()), states


async def test_live_opendota_match_reaches_ready_and_reads_back(database, redis_client):
    """One real match: summary → replay request/poll → ordered finalization → mobile read."""
    import asyncio

    from .test_e2e_matrix import _due

    settings = _live_settings()
    redis, namespace = redis_client
    policy = WorkerPolicy(namespace=namespace)
    profile_id, token = _owner(database, "ready", datetime.now(UTC) - timedelta(days=30))
    headers = {"Authorization": f"Bearer {token}"}
    client = TestClient(create_mobile_app(settings, database=database))
    assert client.post("/sync", headers={**headers, "Idempotency-Key": "live-ready-1"}).status_code in {200, 202}
    # History pages only: hold summaries back until the sync job completes.
    for _ in range(4):
        with database.begin() as connection:
            connection.execute(ingest_jobs.update().where(ingest_jobs.c.job_type == "SUMMARY",
                                                          ingest_jobs.c.state == "PENDING")
                               .values(run_after=func.clock_timestamp() + timedelta(hours=1)))
        await run_one(database, redis, settings, priority=0, policy=policy)
        with database.connect() as connection:
            if connection.scalar(select(ingest_jobs.c.state).where(ingest_jobs.c.job_type == "SYNC")) == "COMPLETE":
                break
    # Keep one match: the oldest accepted one is the likeliest to be parsed already.
    with database.begin() as connection:
        chosen = connection.scalar(select(func.min(ingest_jobs.c.match_id)).where(ingest_jobs.c.job_type == "SUMMARY"))
        connection.execute(ingest_jobs.update().where(ingest_jobs.c.job_type == "SUMMARY",
                                                      ingest_jobs.c.match_id != chosen).values(state="COMPLETE"))

    deadline = asyncio.get_running_loop().time() + 420
    lifecycle = None
    while asyncio.get_running_loop().time() < deadline and len(_calls(database, "opendota")) < 20:
        _due(database)
        for priority in range(3):
            for _ in range(10):
                if await run_one(database, redis, settings, priority=priority, policy=policy) in STOPS:
                    break
        with database.connect() as connection:
            lifecycle = connection.scalar(select(account_matches.c.lifecycle).where(
                account_matches.c.profile_id == profile_id, account_matches.c.match_id == chosen))
        if lifecycle in {"READY", "UNAVAILABLE"}:
            break
        await asyncio.sleep(20)

    calls = _calls(database, "opendota")
    with database.connect() as connection:
        evidence = connection.scalar(select(matches.c.evidence_state).where(matches.c.match_id == chosen))
    print(f"\nready: calls={len(calls)} ops={Counter((c['operation'], c['status']) for c in calls)} "
          f"rate={sum(c['rate_units'] for c in calls)} billed={sum(c['billed_units'] for c in calls)} "
          f"evidence={evidence} lifecycle={lifecycle} "
          f"matches_touched={len({c['match_id'] for c in calls if c['match_id']})}")
    assert {c["match_id"] for c in calls if c["match_id"]} == {chosen}
    assert sum(c["operation"] == "request_replay" for c in calls) <= 1
    assert lifecycle == "READY", (evidence, lifecycle)
    listed = client.get("/history", headers=headers).json()["matches"]
    row = next(row for row in listed if row["lifecycle"] == "READY")
    detail = client.get(f"/matches/{row['ref']}", headers=headers).json()
    print(f"detail: facts={detail['facts']} performance={detail['performance']} metrics={len(detail['metrics'])}")
    assert detail["facts"] == "AVAILABLE" and len(detail["players"]) == 10
