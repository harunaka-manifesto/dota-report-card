import asyncio
from datetime import timedelta

import httpx
import pytest
from app.core.config import Settings
from app.tracker.jobs import StaleJob, claim
from app.tracker.linking import complete_link_job, enqueue_roster_links
from app.tracker.materialization import materialize_snapshot
from app.tracker.replay_acquisition import ReplayPolicy, acquire_fresh_replay
from app.tracker.schema import (
    account_matches,
    acquisitions,
    derived_features,
    ingest_jobs,
    matches,
    provider_calls,
    snapshots,
)
from sqlalchemy import func, select

from .test_materialization import MATCH_ID, raw, save
from .test_provider_transport import gate_for
from .test_schema import identity

POLICY = ReplayPolicy(poll_delays=(1, 2))


def payload(parsed=False):
    value = raw()
    value["players"][0]["account_id"] = 1001
    if not parsed:
        value["version"] = None
    return value


def prepare(database, *, parsed=False):
    identity(database, 1001)
    with database.begin() as c:
        snapshot_id = save(c, payload(parsed))
        materialize_snapshot(c, snapshot_id=snapshot_id, match_id=MATCH_ID)
        enqueue_roster_links(c, match_id=MATCH_ID, origin="LIVE")
        link = claim(c, priority=0)
    complete_link_job(database, job_id=link["id"], lease_token=link["lease_token"], replay_delay_seconds=360)
    with database.begin() as c:
        return claim(c, priority=1)


def due(database):
    with database.begin() as c:
        row = c.execute(select(ingest_jobs).where(ingest_jobs.c.job_type == "REPLAY")).mappings().one()
        cursor = dict(row["cursor"] or {})
        if "next_poll_at" in cursor:
            now = c.execute(select(func.clock_timestamp())).scalar_one()
            cursor["next_poll_at"] = (now - timedelta(seconds=1)).isoformat()
        c.execute(ingest_jobs.update().where(ingest_jobs.c.id == row["id"]).values(run_after=func.clock_timestamp(), cursor=cursor))
        return claim(c, priority=1)


async def run(database, gate, job, handler, policy=POLICY):
    return await acquire_fresh_replay(database, gate, Settings(), job_id=job["id"], lease_token=job["lease_token"], policy=policy, transport=httpx.MockTransport(handler))


async def test_submission_then_replay_preserves_identity_and_never_finalizes_private_state(database, redis_client):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, json={"job": {"jobId": 15}} if request.method == "POST" else payload(True))

    assert await run(database, gate, job, handler) == "DEFERRED"
    with database.connect() as c:
        assert c.scalar(select(matches.c.replay_requested_at)) is not None
        assert c.scalar(select(matches.c.evidence_state)) == "REPLAY_PENDING"
    assert await run(database, gate, due(database), handler) == "COMPLETE"
    with database.connect() as c:
        assert c.scalar(select(matches.c.evidence_state)) == "REPLAY_READY"
        assert c.scalar(select(matches.c.replay_terminal_at)) is not None
        assert c.scalar(select(account_matches.c.lifecycle)) == "ANALYZING"
        assert c.scalar(select(func.count()).select_from(derived_features)) == 20
        assert c.scalar(select(func.sum(provider_calls.c.rate_units))) == 11
        assert c.scalar(select(acquisitions.c.attempts).where(acquisitions.c.operation == "replay_enrichment")) == 2
    assert calls == ["POST", "GET"]


async def test_stored_replay_recovery_makes_no_processing_or_read_request(database, redis_client):
    job = prepare(database, parsed=True)
    gate = gate_for(redis_client, "opendota")

    def forbidden(_):
        pytest.fail("Stored replay was refetched")

    assert await run(database, gate, job, forbidden) == "COMPLETE"
    with database.connect() as c:
        assert c.scalar(select(matches.c.evidence_state)) == "REPLAY_READY"
        assert c.scalar(select(func.count()).select_from(provider_calls)) == 0


async def test_bounded_missing_replay_is_terminal_without_action_required(database, redis_client):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, json={"job": {"jobId": 15}} if request.method == "POST" else payload())

    assert await run(database, gate, job, handler) == "DEFERRED"
    assert await run(database, gate, due(database), handler) == "DEFERRED"
    assert await run(database, gate, due(database), handler) == "COMPLETE"
    with database.connect() as c:
        assert c.scalar(select(matches.c.evidence_state)) == "REPLAY_UNAVAILABLE"
        assert c.scalar(select(matches.c.terminal_reason)) == "REPLAY_CHECKS_EXHAUSTED"
        assert c.scalar(select(account_matches.c.lifecycle)) == "ANALYZING"
        assert c.scalar(select(account_matches.c.finalized_at)) is None
    assert calls == ["POST", "GET", "GET"]


async def test_uncertain_submission_polls_without_resubmitting(database, redis_client):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    calls = []

    def handler(request):
        calls.append(request.method)
        if request.method == "POST":
            raise httpx.ReadTimeout("Response was lost")
        return httpx.Response(200, json=payload(True))

    assert await run(database, gate, job, handler) == "DEFERRED"
    assert await run(database, gate, due(database), handler) == "COMPLETE"
    assert calls == ["POST", "GET"]


async def test_quota_deferral_happens_before_durable_submission_intent(database, redis_client):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    gate.observe({"x-ratelimit-remaining-minute": "0"}, status=200)

    def forbidden(_):
        pytest.fail("Quota exhausted but HTTP attempted")

    assert await run(database, gate, job, forbidden) == "DEFERRED"
    with database.connect() as c:
        current = c.execute(select(ingest_jobs).where(ingest_jobs.c.id == job["id"])).mappings().one()
        assert not current["cursor"] and current["attempts"] == 0
        assert c.scalar(select(matches.c.replay_requested_at)) is None


@pytest.mark.parametrize("young", [True, False])
async def test_replay_age_policy_blocks_processing_without_claiming_valve_horizon(database, redis_client, young):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    with database.begin() as c:
        duration = c.scalar(select(matches.c.duration_seconds))
        c.execute(matches.update().values(started_at=func.clock_timestamp() - timedelta(seconds=duration + (10 if young else POLICY.processing_window_seconds + 1))))

    def forbidden(_):
        pytest.fail("Match outside processing policy was submitted")

    assert await run(database, gate, job, forbidden) == ("DEFERRED" if young else "COMPLETE")
    with database.connect() as c:
        assert c.scalar(select(matches.c.terminal_reason)) == (None if young else "OUTSIDE_PROCESSING_WINDOW")
        assert c.scalar(select(func.count()).select_from(provider_calls)) == 0


async def test_publication_failure_after_replay_success_never_refetches(database, redis_client, monkeypatch):
    from app.tracker import replay_acquisition

    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    with database.begin() as c:
        c.execute(ingest_jobs.update().where(ingest_jobs.c.id == job["id"]).values(cursor={"submitted": True, "polls": 0}))
    calls = []

    def handler(request):
        calls.append(request.method)
        return httpx.Response(200, json=payload(True))

    original = replay_acquisition.materialize_snapshot

    def fail(*args, **kwargs):
        raise RuntimeError("simulated internal failure")

    monkeypatch.setattr(replay_acquisition, "materialize_snapshot", fail)
    assert await run(database, gate, job, handler) == "DEFERRED"
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(snapshots)) == 2
        assert c.scalar(select(matches.c.evidence_state)) == "REPLAY_PENDING"
    monkeypatch.setattr(replay_acquisition, "materialize_snapshot", original)
    assert await run(database, gate, due(database), handler) == "COMPLETE"
    assert calls == ["GET"]


@pytest.mark.parametrize("polling", [True, False])
async def test_429_preserves_poll_budget_and_rejected_submission_can_retry(database, redis_client, polling):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    if polling:
        with database.begin() as c:
            c.execute(ingest_jobs.update().where(ingest_jobs.c.id == job["id"]).values(cursor={"submitted": True, "polls": 0}))
    calls = []

    def handler(request):
        calls.append(request.method)
        if len(calls) == 1:
            return httpx.Response(429, json={"error": "try later"})
        return httpx.Response(200, json=payload(True) if request.method == "GET" else {"job": {"jobId": 15}})

    policy = ReplayPolicy(poll_delays=(1,))
    assert await run(database, gate, job, handler, policy) == "DEFERRED"
    with database.connect() as c:
        current = c.execute(select(ingest_jobs).where(ingest_jobs.c.id == job["id"])).mappings().one()
        assert current["attempts"] == 0
        assert (current["cursor"] or {}).get("polls", 0) == 0
        assert bool((current["cursor"] or {}).get("submitted")) == polling
    # Simulated recovery of this isolated test credential's quota/circuit.
    gate.redis.delete(gate.key)
    gate.observe({"x-ratelimit-limit-minute": "100", "x-ratelimit-remaining-minute": "100"}, status=200)
    assert await run(database, gate, due(database), handler, policy) == ("COMPLETE" if polling else "DEFERRED")
    assert calls == (["GET", "GET"] if polling else ["POST", "POST"])


async def test_elapsed_limit_stops_even_when_quota_never_recovers(database, redis_client):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    gate.observe({"x-ratelimit-remaining-minute": "0"}, status=200)
    with database.begin() as c:
        c.execute(ingest_jobs.update().where(ingest_jobs.c.id == job["id"]).values(created_at=func.clock_timestamp() - timedelta(seconds=POLICY.max_elapsed_seconds + 1)))

    def forbidden(_):
        pytest.fail("Elapsed limit allowed further acquisition")

    assert await run(database, gate, job, forbidden) == "COMPLETE"
    with database.connect() as c:
        assert c.scalar(select(matches.c.terminal_reason)) == "REPLAY_WAIT_EXPIRED"
        assert c.scalar(select(matches.c.evidence_state)) == "REPLAY_UNAVAILABLE"
        assert c.scalar(select(account_matches.c.lifecycle)) == "ANALYZING"


@pytest.mark.parametrize("lose_lock", [False, True])
async def test_duplicate_replay_delivery_never_submits_twice(database, redis_client, lose_lock):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    entered, release = asyncio.Event(), asyncio.Event()
    calls = 0

    async def handler(_):
        nonlocal calls
        calls += 1
        entered.set()
        await release.wait()
        return httpx.Response(200, json={"job": {"jobId": 15}})

    first = asyncio.create_task(run(database, gate, job, handler))
    await asyncio.wait_for(entered.wait(), 3)
    try:
        if lose_lock:
            gate.redis.delete(f"{gate.key}:replay:{MATCH_ID}")
        assert await run(database, gate, job, handler) == "RUNNING"
    finally:
        release.set()
    assert await first == "DEFERRED"
    assert calls == 1


async def test_lost_lease_after_quota_admission_cannot_submit_processing(database, redis_client, monkeypatch):
    job = prepare(database)
    gate = gate_for(redis_client, "opendota")
    original = gate.acquire

    def takeover(**kwargs):
        original(**kwargs)
        with database.begin() as c:
            c.execute(ingest_jobs.update().where(ingest_jobs.c.id == job["id"]).values(lease_until=func.clock_timestamp() - timedelta(seconds=1)))
            assert claim(c, priority=1)["lease_token"] != job["lease_token"]

    monkeypatch.setattr(gate, "acquire", takeover)

    def forbidden(_):
        pytest.fail("Worker submitted after losing its lease")

    with pytest.raises(StaleJob):
        await run(database, gate, job, forbidden)
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(provider_calls)) == 0
        assert not c.scalar(select(ingest_jobs.c.cursor).where(ingest_jobs.c.id == job["id"]))
