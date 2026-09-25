import asyncio
import os
import subprocess
import sys
import time
from datetime import timedelta
from uuid import uuid4

import httpx
import pytest
import yaml
from app.core.config import Settings
from app.tracker.acquisition import enqueue_fresh_summary
from app.tracker.jobs import enqueue
from app.tracker.linking import enqueue_roster_links
from app.tracker.provider_control import ProviderGate
from app.tracker.schema import account_matches, ingest_jobs, match_players, profiles
from app.tracker.worker import WorkerPolicy, admission, create_worker_app, queue_metrics, run_one
from celery import signals
from celery.contrib.testing.worker import start_worker
from sqlalchemy import func, select, update

from .conftest import ROOT
from .test_schema import LINKED_AT, MATCH_ID, identity, summary


def policy_for(redis_client):
    redis, namespace = redis_client
    for provider in ('opendota', 'stratz'):
        ProviderGate(redis, namespace=namespace, provider=provider).observe({'x-ratelimit-limit-minute': '1000', 'x-ratelimit-remaining-minute': '1000'}, status=200)
    return WorkerPolicy(namespace=namespace)


def test_compose_tracker_profile_keeps_legacy_worker_and_separates_queues():
    services = yaml.safe_load((ROOT / 'infra/compose.yaml').read_text())['services']
    assert services['worker']['command'] == 'celery -A app.workers.tasks.celery_app worker --loglevel=INFO --concurrency=4'
    assert services['tracker-beat']['profiles'] == ['tracker']
    assert 'app.tracker.worker:celery_app beat' in services['tracker-beat']['command']
    for priority in range(4):
        service = services[f'tracker-p{priority}']
        assert service['profiles'] == ['tracker']
        assert service['command'].count(' -Q ') == 1
        assert f' -Q tracker-p{priority} ' in service['command']
        assert '--concurrency=1' in service['command']
        assert service['depends_on']['migrate']['condition'] == 'service_completed_successfully'


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

    identity(database, 1001, linked_at=LINKED_AT)
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
    identity(database, 1001, linked_at=LINKED_AT)
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


def test_separate_p0_worker_is_not_starved_by_blocked_p3(database, redis_client):
    """Two real Celery processes must keep their database-owned lanes independent."""
    _, p3_profile = identity(database, 1001, linked_at=LINKED_AT)
    identity(database, 1002, linked_at=LINKED_AT)
    summary(database)
    summary(database, MATCH_ID + 1)
    with database.begin() as connection:
        connection.execute(update(match_players).where(
            match_players.c.match_id == MATCH_ID + 1,
            match_players.c.player_slot == 0,
        ).values(account_id=1002))
        p3_job = enqueue_roster_links(connection, match_id=MATCH_ID, origin='HISTORICAL')[0]
        p0_job = enqueue_roster_links(connection, match_id=MATCH_ID + 1, origin='LIVE')[0]
    redis, namespace = redis_client
    policy_for(redis_client)
    suffix = uuid4().hex
    queues = {priority: f'tracker-p{priority}-{suffix}' for priority in (0, 3)}
    settings = Settings(database_url=database.url.render_as_string(hide_password=False),
                        redis_url=os.environ['TEST_REDIS_URL'])
    app = create_worker_app(settings)
    environment = {**os.environ, 'DATABASE_URL': settings.database_url,
                   'REDIS_URL': settings.redis_url, 'TRACKER_NAMESPACE': namespace,
                   'PYTHONPATH': str(ROOT / 'services/api')}
    workers = []

    def start(priority):
        worker = subprocess.Popen([
            sys.executable, '-m', 'celery', '-A', 'app.tracker.worker:celery_app',
            'worker', '-Q', queues[priority], '-n', f'tracker-p{priority}-{suffix}@localhost',
            '--pool=solo', '--concurrency=1', '--without-gossip', '--without-mingle',
            '--without-heartbeat', '--loglevel=WARNING',
        ], cwd=ROOT, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        workers.append(worker)
        return worker

    def wait_for(job_id, state, timeout=15):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with database.connect() as connection:
                if connection.scalar(select(ingest_jobs.c.state).where(ingest_jobs.c.id == job_id)) == state:
                    return True
            time.sleep(0.05)
        return False

    try:
        with database.connect() as blocker:
            transaction = blocker.begin()
            blocker.execute(select(profiles.c.id).where(profiles.c.id == p3_profile).with_for_update()).scalar_one()
            try:
                assert start(3).poll() is None
                app.send_task('tracker.wake', args=[3], queue=queues[3])
                assert wait_for(p3_job, 'RUNNING'), 'P3 worker did not claim its blocked job'
                assert start(0).poll() is None
                app.send_task('tracker.wake', args=[0], queue=queues[0])
                assert wait_for(p0_job, 'COMPLETE'), 'P0 work was starved by P3'
                with database.connect() as connection:
                    assert connection.scalar(select(ingest_jobs.c.state).where(ingest_jobs.c.id == p3_job)) == 'RUNNING'
            finally:
                transaction.rollback()
    finally:
        for worker in workers:
            worker.terminate()
            try:
                worker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)
        app.close()
        leftover = [queue for queue in queues.values() if redis.exists(queue)]
        if leftover:
            redis.delete(*leftover)


async def test_p3_manual_pause_resumes_stored_work_without_provider_calls(database, redis_client):
    identity(database, 1001, linked_at=LINKED_AT)
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
