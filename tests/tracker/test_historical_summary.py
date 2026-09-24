from datetime import timedelta

import httpx
from app.core.config import Settings
from app.tracker.historical import enqueue_historical_batch
from app.tracker.historical_summary import enqueue_historical_summary
from app.tracker.schema import (
    account_matches,
    acquisitions,
    bootstrap,
    bootstrap_search_items,
    ingest_jobs,
    matches,
    provider_calls,
)
from app.tracker.worker import run_one
from sqlalchemy import func, select

from .test_materialization import MATCH_ID, raw, save
from .test_schema import NOW, identity
from .test_worker import policy_for


async def test_missing_deep_row_falls_back_to_p3_summary_and_private_bootstrap_link(database, redis_client):
    _, profile_id = identity(database)
    redis, _ = redis_client
    policy = policy_for(redis_client)
    settings = Settings(stratz_api_token='test-only')
    with database.begin() as c:
        c.execute(matches.insert().values(match_id=MATCH_ID, discovered_at=func.now()))
        enqueue_historical_batch(c, profile_id=profile_id, match_ids=[MATCH_ID], origin='BOOTSTRAP')
    assert await run_one(database, redis, settings, priority=3, policy=policy,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={'data': {'player': {'matches': []}}}))) == 'COMPLETE'
    with database.connect() as c:
        jobs = c.execute(select(ingest_jobs.c.job_type, ingest_jobs.c.priority)).all()
        assert ('HISTORICAL_SUMMARY', 3) in jobs
        assert c.scalar(select(acquisitions.c.state).where(acquisitions.c.provider == 'stratz')) == 'SOURCE_MISSING'
    payload = raw()
    payload['players'][0]['account_id'] = 1001
    payload['version'] = None
    assert await run_one(database, redis, settings, priority=3, policy=policy,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))) == 'COMPLETE'
    with database.connect() as c:
        assert c.scalar(select(matches.c.evidence_state).where(matches.c.match_id == MATCH_ID)) == 'SUMMARY_READY'
        assert c.scalar(select(acquisitions.c.state).where(acquisitions.c.provider == 'opendota')) == 'COMPLETE'
        assert c.scalar(select(func.count()).select_from(provider_calls)) == 2
    assert await run_one(database, redis, settings, priority=3, policy=policy) == 'COMPLETE'
    with database.connect() as c:
        link = c.execute(select(account_matches)).mappings().one()
        assert link['profile_id'] == profile_id and link['origin'] == 'BOOTSTRAP'


async def test_summary_404_is_source_gap_without_fabricated_link(database, redis_client):
    _, profile_id = identity(database)
    redis, _ = redis_client
    policy = policy_for(redis_client)
    settings = Settings(stratz_api_token='test-only')
    with database.begin() as c:
        snapshot_id = save(c, {"data": {"player": {"matches": []}}}, "stratz")
        c.execute(bootstrap.insert().values(profile_id=profile_id, mode="STANDARD", search_finished=True, discovered_count=1))
        c.execute(bootstrap.insert().values(profile_id=profile_id, mode="TURBO", search_finished=True))
        c.execute(bootstrap_search_items.insert().values(
            profile_id=profile_id, source_item_id=str(MATCH_ID), snapshot_id=snapshot_id,
            match_id=MATCH_ID, started_at=NOW - timedelta(days=1), mode="STANDARD",
            outcome="CANDIDATE", selected_at=func.now(),
        ))
        c.execute(bootstrap_search_items.insert().values(
            profile_id=profile_id, source_item_id=str(MATCH_ID + 1), snapshot_id=snapshot_id,
            match_id=MATCH_ID + 1, started_at=NOW - timedelta(days=2), mode="STANDARD",
            outcome="CANDIDATE",
        ))
        c.execute(matches.insert().values(match_id=MATCH_ID, discovered_at=func.now()))
        enqueue_historical_batch(c, profile_id=profile_id, match_ids=[MATCH_ID], origin='BOOTSTRAP')
    assert await run_one(database, redis, settings, priority=3, policy=policy,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={'data': {'player': {'matches': []}}}))) == 'COMPLETE'
    assert await run_one(database, redis, settings, priority=3, policy=policy,
        transport=httpx.MockTransport(lambda _: httpx.Response(404))) == 'SOURCE_MISSING'
    with database.connect() as c:
        assert c.scalar(select(acquisitions.c.state).where(acquisitions.c.provider == 'opendota')) == 'SOURCE_MISSING'
        assert c.scalar(select(func.count()).select_from(account_matches)) == 0
        refill = c.execute(select(ingest_jobs).where(
            ingest_jobs.c.job_type == "HISTORICAL_BATCH", ingest_jobs.c.state == "PENDING",
        )).mappings().one()
        assert refill["payload"]["match_ids"] == [MATCH_ID + 1]
        bucket = c.execute(select(bootstrap).where(bootstrap.c.profile_id == profile_id,
            bootstrap.c.mode == "STANDARD")).mappings().one()
        assert (bucket["discovered_count"], bucket["settled_count"], bucket["eligible_count"]) == (2, 1, 0)
        assert c.scalar(select(bootstrap_search_items.c.selected_at).where(
            bootstrap_search_items.c.profile_id == profile_id,
            bootstrap_search_items.c.match_id == MATCH_ID + 1,
        )) is not None


async def test_historical_summary_rejects_unproven_profile_membership(database, redis_client):
    _, profile_id = identity(database)
    redis, _ = redis_client
    with database.begin() as c:
        enqueue_historical_summary(c, profile_id=profile_id, match_id=MATCH_ID, origin='BOOTSTRAP')
    payload = raw()
    payload['players'][0]['account_id'] = 2002
    assert await run_one(database, redis, Settings(), priority=3, policy=policy_for(redis_client),
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))) == 'DEFERRED'
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(account_matches)) == 0
        assert c.scalar(select(matches.c.evidence_state).where(matches.c.match_id == MATCH_ID)) == 'DISCOVERED'


async def test_private_deep_profile_routes_to_summary_without_claiming_empty_history(database, redis_client):
    _, profile_id = identity(database)
    redis, _ = redis_client
    with database.begin() as c:
        enqueue_historical_batch(c, profile_id=profile_id, match_ids=[MATCH_ID], origin='BOOTSTRAP')
    assert await run_one(database, redis, Settings(stratz_api_token='test-only'), priority=3, policy=policy_for(redis_client),
        transport=httpx.MockTransport(lambda _: httpx.Response(200, json={'data': {'player': None}}))) == 'SOURCE_MISSING'
    with database.connect() as c:
        assert c.scalar(select(acquisitions.c.state).where(acquisitions.c.provider == 'stratz')) == 'SOURCE_MISSING'
        assert c.scalar(select(ingest_jobs.c.job_type).where(ingest_jobs.c.state == 'PENDING')) == 'HISTORICAL_SUMMARY'
        assert c.scalar(select(func.count()).select_from(account_matches)) == 0
