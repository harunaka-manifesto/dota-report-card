from app.core.config import Settings
from app.tracker.authentication import VerifiedIdentity, attach_identity, create_user_session
from app.tracker.finalization import complete_finalization_job, enqueue_finalization
from app.tracker.jobs import claim, enqueue
from app.tracker.mobile_api import create_mobile_app
from app.tracker.retry import retry_match
from app.tracker.schema import (
    account_matches,
    analyses,
    ingest_jobs,
    matches,
    profiles,
    provider_calls,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from .test_finalization import _ready_link, _run
from .test_materialization import MATCH_ID


def test_manual_retry_reuses_terminal_evidence_and_merges_repeated_work(database):
    profile_id = _ready_link(database)
    with database.begin() as connection:
        owner = connection.scalar(select(profiles.c.user_id).where(profiles.c.id == profile_id))
        ref = connection.scalar(select(account_matches.c.public_ref))
        started = connection.scalar(select(account_matches.c.provider_started_at))
        connection.execute(profiles.update().where(profiles.c.id == profile_id).values(original_linked_at=started))
        connection.execute(account_matches.update().values(
            lifecycle="ACTION_REQUIRED", failure_stage="FINALIZATION", failure_reason="INTERNAL_FAILURE",
        ))
        job_id = enqueue_finalization(connection, profile_id=profile_id, match_id=connection.scalar(select(account_matches.c.match_id)))
        connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == job_id).values(state="FAILED", attempts=5))
        assert retry_match(connection, user_id=owner, match_ref=ref)
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(ingest_jobs)) == 1
        assert connection.scalar(select(func.count()).select_from(provider_calls)) == 0
    with database.begin() as connection:
        job = claim(connection, priority=0)
    assert job is not None
    assert complete_finalization_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "READY"
    with database.connect() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        assert link["lifecycle"] == "READY" and not link["retrying"]
        assert connection.scalar(select(func.count()).select_from(analyses)) == 1
        assert connection.scalar(select(func.count()).select_from(provider_calls)) == 0


def test_manual_retry_reopens_finished_unavailable_job_after_role_evidence(database):
    profile_id = _ready_link(database)
    with database.begin() as connection:
        assignment = connection.scalar(select(matches.c.replay_role_assignment).where(matches.c.match_id == MATCH_ID))
        connection.execute(matches.update().where(matches.c.match_id == MATCH_ID).values(replay_role_assignment=None))
        connection.execute(account_matches.update().values(effective_role=None))
    assert _run(database, profile_id) == "UNAVAILABLE"
    with database.begin() as connection:
        owner = connection.scalar(select(profiles.c.user_id).where(profiles.c.id == profile_id))
        ref = connection.scalar(select(account_matches.c.public_ref))
        started = connection.scalar(select(account_matches.c.provider_started_at))
        connection.execute(profiles.update().where(profiles.c.id == profile_id).values(original_linked_at=started))
        connection.execute(matches.update().where(matches.c.match_id == MATCH_ID).values(replay_role_assignment=assignment))
        assert retry_match(connection, user_id=owner, match_ref=ref)
    with database.begin() as connection:
        job = claim(connection, priority=0)
    assert job is not None
    assert complete_finalization_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "READY"
    with database.connect() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        assert link["effective_role"] is not None and not link["retrying"]


def test_mobile_retry_is_idempotent_and_account_scoped(database):
    profile_id = _ready_link(database)
    with database.begin() as connection:
        owner = connection.scalar(select(profiles.c.user_id).where(profiles.c.id == profile_id))
        ref = connection.scalar(select(account_matches.c.public_ref))
        started = connection.scalar(select(account_matches.c.provider_started_at))
        connection.execute(profiles.update().where(profiles.c.id == profile_id).values(original_linked_at=started))
        connection.execute(account_matches.update().values(
            lifecycle="ACTION_REQUIRED", failure_stage="FINALIZATION", failure_reason="INTERNAL_FAILURE",
        ))
    identity = VerifiedIdentity("google", "https://accounts.google.com", "retry-owner", None)
    attach_identity(database, owner, identity)
    _, tokens = create_user_session(database, identity)
    _, stranger = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", "retry-stranger", None,
    ))
    client = TestClient(create_mobile_app(Settings(), database=database))
    path = f"/matches/{ref}/retry"
    owner_headers = {"Authorization": f"Bearer {tokens.access_token}", "Idempotency-Key": "retry-match-001"}
    stranger_headers = {"Authorization": f"Bearer {stranger.access_token}", "Idempotency-Key": "retry-match-002"}
    assert client.post(path, headers=stranger_headers).status_code == 404
    first = client.post(path, headers=owner_headers)
    assert first.status_code == 200 and first.json() == {"accepted": True}
    assert client.post(path, headers=owner_headers).json() == first.json()
    assert client.post(path, headers={**owner_headers, "Idempotency-Key": "retry-match-003"}).status_code == 409
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(ingest_jobs)) == 1


def test_manual_retry_reopens_failed_shared_replay_before_private_analysis(database):
    profile_id = _ready_link(database)
    with database.begin() as connection:
        owner = connection.scalar(select(profiles.c.user_id).where(profiles.c.id == profile_id))
        ref = connection.scalar(select(account_matches.c.public_ref))
        started = connection.scalar(select(account_matches.c.provider_started_at))
        connection.execute(profiles.update().where(profiles.c.id == profile_id).values(original_linked_at=started))
        connection.execute(matches.update().where(matches.c.match_id == MATCH_ID).values(evidence_state="REPLAY_PENDING"))
        connection.execute(account_matches.update().values(
            lifecycle="UNAVAILABLE", failure_stage="ROLE_CLASSIFICATION", failure_reason="ROLE_UNAVAILABLE",
        ))
        replay_id = enqueue(connection, dedup_key=f"replay:{MATCH_ID}", job_type="REPLAY",
                            priority=1, match_id=MATCH_ID, payload={})
        connection.execute(ingest_jobs.update().where(ingest_jobs.c.id == replay_id).values(state="FAILED", attempts=5))
        assert retry_match(connection, user_id=owner, match_ref=ref)
    with database.connect() as connection:
        replay = connection.execute(select(ingest_jobs).where(ingest_jobs.c.id == replay_id)).mappings().one()
        assert replay["state"] == "PENDING" and replay["priority"] == 2 and replay["attempts"] == 0
        assert connection.scalar(select(func.count()).select_from(ingest_jobs)) == 2
        assert connection.scalar(select(func.count()).select_from(provider_calls)) == 0
