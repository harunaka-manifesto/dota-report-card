from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from app.tracker.jobs import StaleJob, authorized_job, claim, enqueue, finish, reschedule
from app.tracker.schema import ingest_jobs, users
from sqlalchemy import func, select

from .test_schema import identity


def test_parallel_enqueue_and_claim_are_durable_and_priority_isolated(database):
    barrier = Barrier(2)

    def write(_):
        with database.begin() as c:
            barrier.wait(timeout=5)
            return enqueue(c, dedup_key="summary:8", job_type="SUMMARY", priority=1, payload={"match_id": 8})

    with ThreadPoolExecutor(2) as pool:
        a, b = list(pool.map(write, range(2)))
    assert a == b
    with database.begin() as c:
        enqueue(c, dedup_key="history:42", job_type="HISTORY", priority=3, payload={})
        assert claim(c, priority=0) is None
        assert claim(c, priority=3, paused=True) is None
        enqueue(c, dedup_key="summary:9", job_type="SUMMARY", priority=1, payload={"match_id": 9})
    barrier.reset()

    def take(_):
        with database.begin() as c:
            row = claim(c, priority=1)
            barrier.wait(timeout=5)
            return row

    with ThreadPoolExecutor(2) as pool:
        claims = list(pool.map(take, range(2)))
    assert len({r["id"] for r in claims}) == 2
    assert all(r["attempts"] == 1 and r["priority"] == 1 for r in claims)


def test_expired_lease_reclaimed_old_worker_cannot_publish(database):
    with database.begin() as c:
        job_id = enqueue(c, dedup_key="one", job_type="SUMMARY", priority=1, payload={})
        old = claim(c, priority=1)
    with database.begin() as c:
        c.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(lease_until=func.clock_timestamp() - timedelta(seconds=1)))
        new = claim(c, priority=1)
    assert new["lease_token"] != old["lease_token"]
    with pytest.raises(StaleJob):
        with authorized_job(database, job_id, old["lease_token"]):
            pytest.fail("A stale worker reached its publication transaction")
    with authorized_job(database, job_id, new["lease_token"]) as (c, job):
        finish(c, job)
    with database.begin() as c:
        assert claim(c, priority=1) is None
        assert c.execute(select(ingest_jobs.c.state)).scalar_one() == "COMPLETE"


def test_deletion_generation_fences_late_private_publication(database):
    user_id, profile_id = identity(database)
    with database.begin() as c:
        job_id = enqueue(c, dedup_key="import:profile", job_type="HISTORY", priority=3, payload={}, profile_id=profile_id)
        job = claim(c, priority=3)
    with database.begin() as c:
        c.execute(users.update().where(users.c.id == user_id).values(state="DELETION_PENDING", generation=users.c.generation + 1))
    with pytest.raises(StaleJob, match="generation"):
        with authorized_job(database, job_id, job["lease_token"]):
            pytest.fail("Deleted generation authorized private effects")


def test_checkpoint_survives_redelivery_and_failures_are_bounded(database):
    with database.begin() as c:
        job_id = enqueue(c, dedup_key="history", job_type="HISTORY", priority=3, payload={})
        job = claim(c, priority=3)
    with authorized_job(database, job_id, job["lease_token"]) as (c, row):
        reschedule(c, row, delay_seconds=0, error="QUOTA", cursor={"offset": 50, "page_size": 25}, failure=False)
    with database.begin() as c:
        resumed = claim(c, priority=3)
        assert resumed["attempts"] == 1
        assert resumed["cursor"] == {"offset": 50, "page_size": 25}
    with authorized_job(database, job_id, resumed["lease_token"]) as (c, row):
        reschedule(c, row, delay_seconds=0, error="TIMEOUT", max_attempts=1)
    with database.begin() as c:
        assert claim(c, priority=3) is None
        assert c.execute(select(ingest_jobs.c.state)).scalar_one() == "FAILED"
        with pytest.raises(ValueError, match="different work"):
            enqueue(c, dedup_key="history", job_type="HISTORY", priority=3, payload={"different": True})
