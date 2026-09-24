from datetime import UTC, datetime

import pytest
from app.stratz.queries import GET_TRACKER_MATCH_BATCH
from app.tracker.evidence import save_snapshot
from app.tracker.historical import materialize_historical_batch
from app.tracker.normalization import InvalidEvidence
from app.tracker.schema import acquisitions, derived_features, ingest_jobs, match_players, matches
from sqlalchemy import func, select

from .test_materialization import MATCH_ID, raw
from .test_schema import identity


def batch_snapshot(connection, rows):
    return save_snapshot(connection, provider='stratz', operation=GET_TRACKER_MATCH_BATCH.name,
        operation_version=GET_TRACKER_MATCH_BATCH.version, schema_version='raw-1',
        subject='batch:test', fetched_at=datetime.now(UTC),
        payload={'data': {'player': {'matches': rows}}})


def test_retained_batch_materializes_replay_links_and_source_absence_once(database):
    _, profile_id = identity(database)
    payload = raw('stratz')
    payload['players'][0]['steamAccountId'] = 1001
    with database.begin() as c:
        for match_id in (MATCH_ID, MATCH_ID+1):
            c.execute(matches.insert().values(match_id=match_id, discovered_at=func.now()))
        snapshot_id = batch_snapshot(c, [payload])
        expected = {MATCH_ID: 'REPLAY_READY', MATCH_ID+1: 'SOURCE_MISSING'}
        for _ in range(2):
            assert materialize_historical_batch(c, snapshot_id=snapshot_id, profile_id=profile_id,
                requested_ids=[MATCH_ID, MATCH_ID+1], origin='BOOTSTRAP') == expected
        assert c.scalar(select(func.count()).select_from(derived_features)) == 10
        assert c.scalar(select(func.count()).select_from(match_players)) == 10
        assert c.scalar(select(func.count()).select_from(ingest_jobs)) == 1
        assert c.scalar(select(matches.c.evidence_state).where(matches.c.match_id == MATCH_ID)) == 'REPLAY_READY'
        assert c.scalar(select(matches.c.evidence_state).where(matches.c.match_id == MATCH_ID+1)) == 'DISCOVERED'
        states = dict(c.execute(select(acquisitions.c.match_id, acquisitions.c.state)).all())
        assert states == expected
        recovered = raw('stratz')
        recovered['id'] = MATCH_ID+1
        recovered['players'][0]['steamAccountId'] = 1001
        later_id = batch_snapshot(c, [payload, recovered])
        assert materialize_historical_batch(c, snapshot_id=later_id, profile_id=profile_id,
            requested_ids=[MATCH_ID, MATCH_ID+1], origin='BOOTSTRAP')[MATCH_ID+1] == 'REPLAY_READY'
        assert c.scalar(select(acquisitions.c.state).where(acquisitions.c.match_id == MATCH_ID+1)) == 'REPLAY_READY'
        assert c.scalar(select(func.count()).select_from(ingest_jobs)) == 2


def test_batch_rejects_unrequested_duplicate_and_unproven_roster(database):
    _, profile_id = identity(database)
    payload = raw('stratz')
    with database.begin() as c:
        c.execute(matches.insert().values(match_id=MATCH_ID, discovered_at=func.now()))
        bad_ids = batch_snapshot(c, [payload, payload])
        unproven = batch_snapshot(c, [payload])
        with pytest.raises(InvalidEvidence, match='duplicate'):
            materialize_historical_batch(c, snapshot_id=bad_ids, profile_id=profile_id,
                requested_ids=[MATCH_ID, MATCH_ID+1], origin='HISTORICAL')
        assert materialize_historical_batch(c, snapshot_id=unproven, profile_id=profile_id,
            requested_ids=[MATCH_ID], origin='HISTORICAL') == {MATCH_ID: 'INVALID_SOURCE'}
        assert c.scalar(select(func.count()).select_from(derived_features)) == 0
        assert c.scalar(select(func.count()).select_from(ingest_jobs)) == 0


def test_bad_row_does_not_discard_valid_sibling(database):
    _, profile_id = identity(database)
    good = raw('stratz')
    good['players'][0]['steamAccountId'] = 1001
    malformed = {'id': MATCH_ID+1, 'players': []}
    with database.begin() as c:
        for match_id in (MATCH_ID, MATCH_ID+1):
            c.execute(matches.insert().values(match_id=match_id, discovered_at=func.now()))
        snapshot_id = batch_snapshot(c, [good, malformed])
        assert materialize_historical_batch(c, snapshot_id=snapshot_id, profile_id=profile_id,
            requested_ids=[MATCH_ID, MATCH_ID+1], origin='BOOTSTRAP') == {
                MATCH_ID: 'REPLAY_READY', MATCH_ID+1: 'INVALID_SOURCE'}
        assert c.scalar(select(func.count()).select_from(derived_features)) == 10
        assert c.scalar(select(func.count()).select_from(ingest_jobs)) == 1
        assert c.scalar(select(acquisitions.c.state).where(acquisitions.c.match_id == MATCH_ID+1)) == 'INVALID_SOURCE'


async def test_worker_fetches_one_bounded_batch_and_recovers_stored_response(database, redis_client):
    import httpx
    from app.core.config import Settings
    from app.tracker.historical import enqueue_historical_batch
    from app.tracker.provider_control import ProviderGate
    from app.tracker.schema import provider_calls
    from app.tracker.worker import run_one

    from .test_worker import policy_for

    _, profile_id = identity(database)
    payload = raw('stratz')
    payload['players'][0]['steamAccountId'] = 1001
    redis, namespace = redis_client
    policy = policy_for(redis_client)
    with database.begin() as c:
        for match_id in (MATCH_ID, MATCH_ID+1):
            c.execute(matches.insert().values(match_id=match_id, discovered_at=func.now()))
        first = enqueue_historical_batch(c, profile_id=profile_id, match_ids=[MATCH_ID], origin='BOOTSTRAP')
        assert first == enqueue_historical_batch(c, profile_id=profile_id, match_ids=[MATCH_ID], origin='BOOTSTRAP')
    requests = []

    def response(request):
        requests.append(request)
        return httpx.Response(200, json={'data': {'player': {'matches': [payload]}}},
            headers={'x-ratelimit-limit-minute': '1000', 'x-ratelimit-remaining-minute': '999'})

    settings = Settings(stratz_api_token='test-only')
    assert await run_one(database, redis, settings, priority=3, policy=policy,
        transport=httpx.MockTransport(response)) == 'COMPLETE'
    assert len(requests) == 1
    with database.begin() as c:
        assert c.scalar(select(ingest_jobs.c.state).where(ingest_jobs.c.id == first)) == 'COMPLETE'
        assert c.scalar(select(func.count()).select_from(provider_calls).where(provider_calls.c.job_id == first)) == 1
        second = enqueue_historical_batch(c, profile_id=profile_id, match_ids=[MATCH_ID+1], origin='HISTORICAL')
        recovered = raw('stratz')
        recovered['id'] = MATCH_ID+1
        recovered['players'][0]['steamAccountId'] = 1001
        snapshot_id = batch_snapshot(c, [recovered])
        c.execute(provider_calls.insert().values(provider='stratz', operation=GET_TRACKER_MATCH_BATCH.name,
            operation_version=GET_TRACKER_MATCH_BATCH.version, account_id=1001, job_id=second,
            snapshot_id=snapshot_id, request_subject='test', status=200, latency_ms=1,
            billed_units=1, rate_units=1, called_at=datetime.now(UTC)))
    no_refetch = httpx.MockTransport(lambda _: pytest.fail('stored response refetched'))
    # The first batch's queued link runs before the second batch.
    assert await run_one(database, redis, settings, priority=3, policy=policy,
        transport=no_refetch) == 'COMPLETE'
    assert await run_one(database, redis, settings, priority=3, policy=policy,
        transport=no_refetch) == 'COMPLETE'
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(provider_calls).where(provider_calls.c.job_id == second)) == 1
        assert c.scalar(select(matches.c.evidence_state).where(matches.c.match_id == MATCH_ID+1)) == 'REPLAY_READY'
    assert ProviderGate(redis, namespace=namespace, provider='stratz').utilization() is not None


async def test_rate_limited_batch_keeps_p3_retry_without_consuming_attempt(database, redis_client):
    import httpx
    from app.core.config import Settings
    from app.tracker.historical import enqueue_historical_batch
    from app.tracker.worker import run_one

    from .test_worker import policy_for

    _, profile_id = identity(database)
    redis, _ = redis_client
    policy = policy_for(redis_client)
    with database.begin() as c:
        job_id = enqueue_historical_batch(c, profile_id=profile_id, match_ids=[MATCH_ID], origin='BOOTSTRAP')
    assert await run_one(database, redis, Settings(stratz_api_token='test-only'), priority=3, policy=policy,
        transport=httpx.MockTransport(lambda _: httpx.Response(429))) == 'DEFERRED'
    with database.connect() as c:
        job = c.execute(select(ingest_jobs).where(ingest_jobs.c.id == job_id)).mappings().one()
        assert (job['state'], job['priority'], job['attempts'], job['last_error']) == ('PENDING', 3, 0, 'RATE_LIMITED')
