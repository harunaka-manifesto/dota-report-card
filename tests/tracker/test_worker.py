import asyncio
import os
import time
from datetime import timedelta

import httpx
import pytest
from app.core.config import Settings
from app.tracker.acquisition import enqueue_fresh_summary
from app.tracker.jobs import enqueue
from app.tracker.linking import enqueue_roster_links
from app.tracker.provider_control import ProviderGate
from app.tracker.schema import account_matches, ingest_jobs
from app.tracker.worker import WorkerPolicy, admission, create_worker_app, queue_metrics, run_one
from celery import signals
from celery.contrib.testing.worker import start_worker
from sqlalchemy import func, select

from .test_schema import MATCH_ID, identity, summary


def policy_for(redis_client):
    redis, namespace = redis_client
    for provider in ('opendota', 'stratz'):
        ProviderGate(redis, namespace=namespace, provider=provider).observe({'x-ratelimit-limit-minute': '1000', 'x-ratelimit-remaining-minute': '1000'}, status=200)
    return WorkerPolicy(namespace=namespace)


def test_backpressure_checks_before_claim_and_reduces_p2_share(database, redis_client):
    redis, namespace = redis_client
    policy = policy_for(redis_client)
    assert admission(database, redis, 3, policy) is None
    redis.set(f'{namespace}:pause:p3', '1')
    assert admission(database, redis, 3, policy) == 'OPERATOR_PAUSED'
    assert admission(database, redis, 0, policy) is None
    redis.delete(f'{namespace}:pause:p3')
    with database.begin() as c:
        enqueue(c, dedup_key='due-replay', job_type='REPLAY', priority=1, payload={})
        enqueue(c, dedup_key='backfill', job_type='BACKFILL', priority=3, payload={})
    policy = policy.model_copy(update={'p1_depth_limit': 1})
    assert admission(database, redis, 3, policy) == 'P1_DEPTH'
    assert admission(database, redis, 2, policy) is None
    assert admission(database, redis, 2, policy) == 'P2_REDUCED_SHARE'
    assert asyncio.run(run_one(database, redis, Settings(), priority=3, policy=policy)) == 'P1_DEPTH'
    with database.connect() as c:
        assert set(c.scalars(select(ingest_jobs.c.state))) == {'PENDING'}


def test_due_age_excludes_future_schedule_and_quota_pauses_backfills(database, redis_client):
    redis, namespace = redis_client
    policy = policy_for(redis_client)
    with database.begin() as c:
        enqueue(c, dedup_key='future', job_type='REPLAY', priority=1, payload={}, run_after=c.scalar(select(func.clock_timestamp())) + timedelta(hours=1))
    assert queue_metrics(database)[1]['depth'] == 0
    assert admission(database, redis, 3, policy) is None
    with database.begin() as c:
        c.execute(ingest_jobs.update().values(run_after=func.clock_timestamp() - timedelta(seconds=61)))
    assert queue_metrics(database)[1]['oldest_seconds'] >= 61
    assert admission(database, redis, 3, policy) == 'P1_AGE'
    with database.begin() as c:
        c.execute(ingest_jobs.update().values(state='COMPLETE'))
    gate = ProviderGate(redis, namespace=namespace, provider='opendota')
    gate.observe({'x-ratelimit-limit-minute': '1000', 'x-ratelimit-remaining-minute': '100'}, status=200)
    assert admission(database, redis, 3, policy) == 'PROVIDER_BUDGET'
    assert admission(database, redis, 1, policy) is None


async def test_worker_routes_summary_and_link_without_other_lane_claim(database, redis_client):
    from .test_materialization import raw

    identity(database, 1001)
    redis, _ = redis_client
    policy = policy_for(redis_client)
    with database.begin() as c:
        enqueue_fresh_summary(c, MATCH_ID)
        enqueue(c, dedup_key='bulk', job_type='BACKFILL', priority=3, payload={})
    payload = raw()
    payload['match_id'] = MATCH_ID
    payload['players'][0]['account_id'] = 1001
    transport = httpx.MockTransport(lambda _: httpx.Response(200, json=payload))
    assert await run_one(database, redis, Settings(), priority=0, policy=policy, transport=transport) == 'COMPLETE'
    assert await run_one(database, redis, Settings(), priority=0, policy=policy) == 'COMPLETE'
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(account_matches)) == 1
        assert c.scalar(select(ingest_jobs.c.state).where(ingest_jobs.c.dedup_key == 'bulk')) == 'PENDING'
        assert c.scalar(select(ingest_jobs.c.priority).where(ingest_jobs.c.job_type == 'REPLAY')) == 1


def test_celery_redis_delivery_executes_database_job_and_duplicate_is_idle(database, redis_client, monkeypatch):
    identity(database, 1001)
    summary(database)
    summary(database, MATCH_ID + 1)
    redis, namespace = redis_client
    monkeypatch.setenv('TRACKER_NAMESPACE', namespace)
    policy_for(redis_client)
    with database.begin() as c:
        job_id = enqueue_roster_links(c, match_id=MATCH_ID, origin='LIVE')[0]
        enqueue_roster_links(c, match_id=MATCH_ID + 1, origin='LIVE')
    settings = Settings(database_url=database.url.render_as_string(hide_password=False), redis_url=os.environ['TEST_REDIS_URL'])
    app = create_worker_app(settings)
    queue = namespace + ':p0'
    app.conf.broker_transport_options = {'visibility_timeout': 300, 'global_keyprefix': namespace + ':'}
    assert app.conf.worker_prefetch_multiplier == 1
    assert app.conf.task_acks_late and app.conf.task_reject_on_worker_lost
    assert {entry['options']['queue'] for entry in app.conf.beat_schedule.values()} == {f'tracker-p{p}' for p in range(4)}
    outcomes = []

    def completed(sender=None, retval=None, **kwargs):
        if sender is not None and sender.name == 'tracker.wake':
            outcomes.append(retval)

    signals.task_postrun.connect(completed, weak=False)
    try:
        with start_worker(app, pool='solo', concurrency=1, queues=[queue], perform_ping_check=False, shutdown_timeout=10):
            app.send_task('tracker.wake', args=[0], queue=queue)
            app.send_task('tracker.wake', args=[0], queue=queue)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                with database.connect() as c:
                    if c.scalar(select(ingest_jobs.c.state).where(ingest_jobs.c.id == job_id)) == 'COMPLETE' and len(outcomes) == 3:
                        break
                time.sleep(0.05)
            else:
                pytest.fail('Celery did not execute the database job')
            assert outcomes == ['COMPLETE', 'COMPLETE', 'IDLE']
            with database.connect() as c:
                assert c.scalar(select(func.count()).select_from(account_matches)) == 2
                assert c.scalar(select(func.count()).select_from(ingest_jobs).where(ingest_jobs.c.job_type == 'REPLAY')) == 2
    finally:
        signals.task_postrun.disconnect(completed)
        app.close()


async def test_p3_manual_pause_resumes_stored_work_without_provider_calls(database, redis_client):
    identity(database, 1001)
    summary(database)
    redis, namespace = redis_client
    policy = policy_for(redis_client)
    with database.begin() as c:
        job_id = enqueue_roster_links(c, match_id=MATCH_ID, origin='HISTORICAL')[0]
    redis.set(f'{namespace}:pause:p3', '1')
    assert await run_one(database, redis, Settings(), priority=3, policy=policy) == 'OPERATOR_PAUSED'
    with database.connect() as c:
        assert c.scalar(select(ingest_jobs.c.attempts).where(ingest_jobs.c.id == job_id)) == 0
        assert c.scalar(select(func.count()).select_from(account_matches)) == 0
    redis.delete(f'{namespace}:pause:p3')
    assert await run_one(database, redis, Settings(), priority=3, policy=policy) == 'COMPLETE'
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(account_matches)) == 1
        assert c.scalar(select(func.count()).select_from(ingest_jobs)) == 1


def test_backpressure_observes_exhausted_read_lane_before_total_budget(redis_client):
    redis, namespace = redis_client
    gate = ProviderGate(redis, namespace=namespace, provider='opendota')
    gate.observe({'x-ratelimit-limit-minute': '100', 'x-ratelimit-remaining-minute': '100'}, status=200)
    for _ in range(10):
        gate.acquire()
    # Ten reads use 10% total but 20% of the separate 50-unit read lane.
    assert 0.18 < gate.utilization() <= 0.2
