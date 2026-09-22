import asyncio
from datetime import timedelta

import httpx
import pytest
from app.core.config import Settings
from app.tracker import acquisition
from app.tracker.jobs import StaleJob, claim
from app.tracker.linking import complete_link_job
from app.tracker.schema import (
    account_matches,
    acquisitions,
    ingest_jobs,
    match_players,
    matches,
    provider_calls,
    snapshots,
)
from sqlalchemy import func, select

from .test_materialization import MATCH_ID, raw
from .test_provider_transport import gate_for
from .test_schema import identity


def prepare(database):
    identity(database, 1001)
    with database.begin() as c:
        job_id = acquisition.enqueue_fresh_summary(c, MATCH_ID)
        assert acquisition.enqueue_fresh_summary(c, MATCH_ID) == job_id
        return claim(c, priority=0)


def retry(database):
    with database.begin() as c:
        c.execute(ingest_jobs.update().where(ingest_jobs.c.job_type == "SUMMARY").values(run_after=func.clock_timestamp()))
        return claim(c, priority=0)


async def run(database, gate, job, handler, **kwargs):
    return await acquisition.acquire_fresh_summary(
        database, gate, Settings(), job_id=job["id"], lease_token=job["lease_token"],
        transport=httpx.MockTransport(handler), **kwargs,
    )


async def test_fresh_summary_to_private_link_uses_one_accounted_request(database, redis_client):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    calls = []

    def handler(request):
        calls.append(request)
        payload = raw()
        payload["players"][0]["account_id"] = 1001
        payload["version"] = None
        return httpx.Response(200, json=payload)

    assert await run(database, gate, job, handler) == "COMPLETE"
    with database.begin() as c:
        assert c.scalar(select(matches.c.evidence_state)) == "SUMMARY_READY"
        assert c.scalar(select(func.count()).select_from(match_players)) == 10
        assert c.scalar(select(func.count()).select_from(snapshots)) == 1
        assert c.scalar(select(provider_calls.c.rate_units)) == 1
        acquired = c.execute(select(acquisitions)).mappings().one()
        assert acquired["state"] == "COMPLETE" and acquired["attempts"] == 1
        assert acquired["snapshot_id"] == c.scalar(select(snapshots.c.id))
        link_job = claim(c, priority=0)
    complete_link_job(database, job_id=link_job["id"], lease_token=link_job["lease_token"], replay_delay_seconds=360)
    with database.connect() as c:
        assert c.scalar(select(account_matches.c.account_id)) == 1001
        assert c.scalar(select(matches.c.evidence_state)) == "REPLAY_PENDING"
        assert c.scalar(select(func.count()).select_from(ingest_jobs).where(ingest_jobs.c.job_type == "REPLAY")) == 1
    assert len(calls) == 1


async def test_internal_failure_after_provider_success_reuses_snapshot(database, redis_client, monkeypatch):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=raw())

    original = acquisition.materialize_snapshot

    def fail(*args, **kwargs):
        raise RuntimeError("simulated publication failure")

    monkeypatch.setattr(acquisition, "materialize_snapshot", fail)
    assert await run(database, gate, job, handler) == "DEFERRED"
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(snapshots)) == 1
        assert c.scalar(select(matches.c.evidence_state)) == "DISCOVERED"
        assert c.scalar(select(func.count()).select_from(match_players)) == 0
        assert c.scalar(select(ingest_jobs.c.last_error)) == "INTERNAL_ACQUISITION"
    monkeypatch.setattr(acquisition, "materialize_snapshot", original)
    resumed = retry(database)
    assert await run(database, gate, resumed, handler) == "COMPLETE"
    assert len(calls) == 1


async def test_quota_deferral_has_no_request_or_failure_budget_burn(database, redis_client):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    gate.observe({"x-ratelimit-remaining-minute": "0"}, status=200)

    def forbidden(_):
        pytest.fail("Quota admission allowed network work")

    assert await run(database, gate, job, forbidden) == "DEFERRED"
    with database.connect() as c:
        current = c.execute(select(ingest_jobs)).mappings().one()
        assert current["state"] == "PENDING" and current["attempts"] == 0
        assert current["last_error"] == "QUOTA_EXHAUSTED"
        assert c.scalar(select(func.count()).select_from(provider_calls)) == 0


async def test_malformed_summary_is_bounded_and_never_ready(database, redis_client):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    incomplete = raw()
    incomplete["players"].pop()
    assert await run(database, gate, job, lambda _: httpx.Response(200, json=incomplete), max_attempts=1) == "FAILED"
    with database.connect() as c:
        assert c.scalar(select(matches.c.evidence_state)) == "DISCOVERED"
        assert c.scalar(select(func.count()).select_from(match_players)) == 0
        assert c.scalar(select(ingest_jobs.c.last_error)) == "INVALID_SUMMARY"
        assert c.scalar(select(func.count()).select_from(snapshots)) == 1


async def test_lease_takeover_keeps_raw_but_fences_late_publication(database, redis_client):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    replacement = None
    calls = 0

    def handler(_):
        nonlocal replacement, calls
        calls += 1
        with database.begin() as c:
            c.execute(ingest_jobs.update().where(ingest_jobs.c.id == job["id"]).values(lease_until=func.clock_timestamp() - timedelta(seconds=1)))
            replacement = claim(c, priority=0)
        return httpx.Response(200, json=raw())

    with pytest.raises(StaleJob):
        await run(database, gate, job, handler)
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(snapshots)) == 1
        assert c.scalar(select(func.count()).select_from(match_players)) == 0
    assert await run(database, gate, replacement, handler) == "COMPLETE"
    assert calls == 1


async def test_duplicate_delivery_does_not_invalidate_running_worker(database, redis_client):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    entered, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def handler(_):
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return httpx.Response(200, json=raw())

    first = asyncio.create_task(run(database, gate, job, handler))
    await asyncio.wait_for(entered.wait(), 3)
    try:
        assert await run(database, gate, job, handler) == "RUNNING"
    finally:
        release.set()
    assert await first == "COMPLETE"
    assert calls == 1
    with database.connect() as c:
        assert c.scalar(select(ingest_jobs.c.state).where(ingest_jobs.c.id == job["id"])) == "COMPLETE"
