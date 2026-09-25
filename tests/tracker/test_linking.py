from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from app.tracker.jobs import StaleJob, claim, enqueue
from app.tracker.linking import complete_link_job, enqueue_roster_links
from app.tracker.materialization import materialize_snapshot
from app.tracker.normalization import InvalidEvidence
from app.tracker.schema import account_matches, ingest_jobs, matches, profiles, users
from sqlalchemy import func, select

from .test_materialization import MATCH_ID, raw, save
from .test_schema import identity


def prepare(database):
    owners = [identity(database, account_id) for account_id in (1001, 1002)]
    payload = raw()
    payload["version"] = None
    for slot, account_id in enumerate((1001, 1002)):
        payload["players"][slot]["account_id"] = account_id
    with database.begin() as c:
        snapshot_id = save(c, payload)
        materialize_snapshot(c, snapshot_id=snapshot_id, match_id=MATCH_ID)
    link_before_match(database)
    return owners


def link_before_match(database):
    # A LIVE link is only for matches played on or after the link date.
    with database.begin() as c:
        started = c.scalar(select(matches.c.started_at).where(matches.c.match_id == MATCH_ID))
        c.execute(profiles.update().values(original_linked_at=started - timedelta(days=1)))


def test_two_users_one_match_schedule_one_replay_with_zero_provider_work(database):
    owners = prepare(database)
    with database.begin() as c:
        c.execute(profiles.update().where(profiles.c.id == owners[1][1]).values(active_scope="PRO"))
        ids = enqueue_roster_links(c, match_id=MATCH_ID, origin="LIVE")
        assert len(ids) == 2
        assert enqueue_roster_links(c, match_id=MATCH_ID, origin="LIVE") == ids
        jobs = [claim(c, priority=0), claim(c, priority=0)]

    def run(job):
        return complete_link_job(database, job_id=job["id"], lease_token=job["lease_token"], replay_delay_seconds=360)

    with ThreadPoolExecutor(2) as pool:
        replay_ids = list(pool.map(run, jobs))
    assert replay_ids[0] == replay_ids[1]
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(account_matches)) == 2
        replay = c.execute(select(ingest_jobs).where(ingest_jobs.c.job_type == "REPLAY")).mappings().one()
        match = c.execute(select(matches)).mappings().one()
        assert replay["run_after"] == match["started_at"] + timedelta(seconds=match["duration_seconds"] + 360)
        assert replay["priority"] == 1 and replay["profile_id"] is None and replay["account_id"] is None
        assert match["evidence_state"] == "REPLAY_PENDING"
        assert c.scalars(select(account_matches.c.lifecycle)).all() == ["WAITING_FOR_PROVIDER", "WAITING_FOR_PROVIDER"]
        assert c.scalar(select(func.count()).select_from(ingest_jobs).where(ingest_jobs.c.state == "COMPLETE")) == 2


def test_switch_and_deletion_fence_claimed_links(database):
    owners = prepare(database)
    with database.begin() as c:
        enqueue_roster_links(c, match_id=MATCH_ID, origin="LIVE")
        jobs = [claim(c, priority=0), claim(c, priority=0)]
    with database.begin() as c:
        c.execute(users.update().where(users.c.id == owners[0][0]).values(state="DELETION_PENDING", generation=users.c.generation + 1))
        c.execute(profiles.update().where(profiles.c.id == owners[1][1]).values(active=False, generation=profiles.c.generation + 1))
    for job in jobs:
        with pytest.raises(StaleJob):
            complete_link_job(database, job_id=job["id"], lease_token=job["lease_token"], replay_delay_seconds=360)
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(account_matches)) == 0
        assert c.scalar(select(func.count()).select_from(ingest_jobs).where(ingest_jobs.c.job_type == "REPLAY")) == 0


def test_history_link_does_not_enqueue_fresh_processing_or_rewrite_existing_link(database):
    prepare(database)
    with database.begin() as c:
        enqueue_roster_links(c, match_id=MATCH_ID, origin="HISTORICAL")
        jobs = [claim(c, priority=3), claim(c, priority=3)]
    for job in jobs:
        assert complete_link_job(database, job_id=job["id"], lease_token=job["lease_token"], replay_delay_seconds=360) is None
    with database.begin() as c:
        assert c.scalar(select(func.count()).select_from(ingest_jobs).where(ingest_jobs.c.job_type == "REPLAY")) == 0
        c.execute(account_matches.update().values(effective_role="MID", role_revision=4))
        c.execute(matches.update().values(evidence_state="REPLAY_UNAVAILABLE", terminal_reason="REPLAY_EXPIRED"))
        enqueue_roster_links(c, match_id=MATCH_ID, origin="LIVE")
        job = claim(c, priority=0)
    assert complete_link_job(database, job_id=job["id"], lease_token=job["lease_token"], replay_delay_seconds=360) is None
    with database.connect() as c:
        links = c.execute(select(account_matches)).mappings().all()
        assert all(link["origin"] == "HISTORICAL" and link["effective_role"] == "MID" and link["role_revision"] == 4 for link in links)


def test_absent_or_conflicting_account_identity_never_authorizes_link(database):
    owners = prepare(database)
    _, absent_profile = identity(database, 1003)
    link_before_match(database)
    with database.begin() as c:
        enqueue(c, dedup_key="absent", job_type="LINK_MATCH", priority=0, payload={"origin": "LIVE"}, match_id=MATCH_ID, profile_id=absent_profile)
        c.execute(matches.update().values(quarantined_fields=["players.0.account_id"]))
        enqueue(c, dedup_key="conflicting", job_type="LINK_MATCH", priority=0, payload={"origin": "LIVE"}, match_id=MATCH_ID, profile_id=owners[0][1])
        jobs = [claim(c, priority=0), claim(c, priority=0)]
    for job in jobs:
        with pytest.raises(InvalidEvidence):
            complete_link_job(database, job_id=job["id"], lease_token=job["lease_token"], replay_delay_seconds=360)
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(account_matches)) == 0
