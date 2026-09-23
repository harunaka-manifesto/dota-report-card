import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from app.core.config import Settings
from app.tracker import sync
from app.tracker.jobs import claim
from app.tracker.schema import (
    account_discoveries,
    ingest_jobs,
    matches,
    provider_calls,
    snapshots,
    sync_state,
)
from sqlalchemy import func, select

from .test_provider_transport import gate_for
from .test_schema import identity


def trigger(database, account_id=1001):
    with database.begin() as c:
        return sync.request_account_sync(c, account_id, scope_days=30)


def next_page(database, job_id):
    with database.begin() as c:
        # Other P0 summary jobs must not obscure the sync claim in this unit test.
        c.execute(ingest_jobs.update().where(ingest_jobs.c.id != job_id).values(run_after=func.clock_timestamp() + timedelta(days=1)))
        c.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(run_after=func.clock_timestamp()))
        return claim(c, priority=0)


async def run(database, gate, job, handler, **kwargs):
    return await sync.sync_account_page(database, gate, Settings(), job_id=job['id'], lease_token=job['lease_token'], transport=httpx.MockTransport(handler), **kwargs)


def test_concurrent_foreground_triggers_share_one_account_job(database):
    identity(database, 1001)
    with ThreadPoolExecutor(max_workers=4) as pool:
        ids = list(pool.map(lambda _: trigger(database), range(8)))
    assert len(set(ids)) == 1
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(ingest_jobs)) == 1
        assert c.scalar(select(sync_state.c.state)) == 'CHECKING'


async def test_pages_journal_rejections_include_turbo_and_complete_only_at_empty_page(database, redis_client):
    identity(database, 1001)
    job_id = trigger(database)
    gate = gate_for(redis_client, 'opendota')
    now = int(datetime.now(UTC).timestamp())
    pages = [[{'match_id': 9001, 'start_time': now, 'game_mode': 23}, {'match_id': -1}, {'match_id': 9002, 'start_time': now - 40 * 86400}], [{'match_id': 9003}], []]
    offsets = []

    def handler(request):
        assert request.url.params['significant'] == '0'
        offsets.append(int(request.url.params['offset']))
        return httpx.Response(200, json=pages[len(offsets) - 1])

    for expected in ['DEFERRED', 'DEFERRED', 'COMPLETE']:
        assert await run(database, gate, next_page(database, job_id), handler) == expected
        with database.connect() as c:
            assert (c.scalar(select(sync_state.c.source_updated_at)) is not None) == (expected == 'COMPLETE')
    assert offsets == [0, 3, 4]
    with database.connect() as c:
        assert c.scalar(select(sync_state.c.state)) == 'UP_TO_DATE'
        assert set(c.scalars(select(matches.c.match_id))) == {9001, 9003}
        rows = c.execute(select(account_discoveries)).mappings().all()
        assert len(rows) == 4
        assert {r['reason'] for r in rows if r['outcome'] == 'REJECTED'} == {'INVALID_MATCH_ID', 'OUTSIDE_SYNC_WINDOW'}
        assert next(r for r in rows if r['match_id'] == 9003)['source_started_at'] is None
        calls = c.execute(select(provider_calls)).mappings().all()
        assert len(calls) == 3
        assert all(r['account_id'] == 1001 and r['job_id'] == job_id and r['snapshot_id'] for r in calls)
    assert trigger(database) is None  # completed checks are still debounced


async def test_publication_failure_reuses_exact_page_and_atomic_cursor(database, redis_client, monkeypatch):
    identity(database, 1001)
    job_id = trigger(database)
    gate = gate_for(redis_client, 'opendota')
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, json=[{'match_id': 9001}])

    original = sync._publish_page

    def fail(*args):
        original(*args)
        raise RuntimeError('rollback after page publication')

    monkeypatch.setattr(sync, '_publish_page', fail)
    assert await run(database, gate, next_page(database, job_id), handler) == 'DEFERRED'
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(account_discoveries)) == 0
        assert c.scalar(select(func.count()).select_from(snapshots)) == 1
        assert c.scalar(select(sync_state.c.source_updated_at)) is None
    monkeypatch.setattr(sync, '_publish_page', original)
    assert await run(database, gate, next_page(database, job_id), handler) == 'DEFERRED'
    assert len(calls) == 1
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(account_discoveries)) == 1
        assert c.scalar(select(ingest_jobs.c.cursor).where(ingest_jobs.c.id == job_id))['offset'] == 1


async def test_duplicate_delivery_cannot_send_twice(database, redis_client):
    identity(database, 1001)
    job_id = trigger(database)
    job = next_page(database, job_id)
    gate = gate_for(redis_client, 'opendota')
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def handler(request):
        calls.append(request)
        entered.set()
        await release.wait()
        return httpx.Response(200, json=[])

    first = asyncio.create_task(run(database, gate, job, handler))
    await asyncio.wait_for(entered.wait(), 3)
    try:
        assert await run(database, gate, job, handler) == 'RUNNING'
    finally:
        release.set()
    assert await first == 'COMPLETE'
    assert len(calls) == 1


@pytest.mark.parametrize('payload', [[{'match_id': 9001}], {'unexpected': 'object'}])
async def test_bounded_sync_failure_never_advances_complete_boundary(database, redis_client, payload):
    identity(database, 1001)
    job_id = trigger(database)
    gate = gate_for(redis_client, 'opendota')
    assert await run(database, gate, next_page(database, job_id), lambda _: httpx.Response(200, json=payload), max_pages=1, max_attempts=1) == 'FAILED'
    with database.connect() as c:
        assert c.scalar(select(sync_state.c.state)) == 'SYNC_ERROR'
        assert c.scalar(select(sync_state.c.source_updated_at)) is None


async def test_two_accounts_share_summary_work_and_outage_preserves_discoveries(database, redis_client):
    identity(database, 1001)
    identity(database, 1002)
    gate = gate_for(redis_client, 'opendota')
    for account_id in (1001, 1002):
        job_id = trigger(database, account_id)
        assert await run(database, gate, next_page(database, job_id), lambda _: httpx.Response(200, json=[{'match_id': 9001}])) == 'DEFERRED'
    assert await run(database, gate, next_page(database, job_id), lambda _: httpx.Response(503), max_attempts=1) == 'FAILED'
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(account_discoveries)) == 2
        assert c.scalar(select(func.count()).select_from(matches)) == 1
        assert c.scalar(select(func.count()).select_from(ingest_jobs).where(ingest_jobs.c.job_type == 'SUMMARY')) == 1
        assert c.scalar(select(sync_state.c.state).where(sync_state.c.account_id == 1002)) == 'SYNC_ERROR'
