"""Owner decisions on the independent QA doubts (2026-09-25).

Each test drives the real job handlers with only provider HTTP replaced by
deterministic fakes; nothing here reaches a provider.
"""
from __future__ import annotations

from datetime import timedelta

from app.core.config import Settings
from app.tracker.jobs import claim
from app.tracker.rebuild import complete_readmit_job, enqueue_readmissions
from app.tracker.schema import (
    account_matches,
    acquisitions,
    events,
    ingest_jobs,
    matches,
    metric_observations,
    notification_outbox,
)
from sqlalchemy import func, select, update

from .builders import add_match, finalize, history
from .test_schema import identity


def _observations(connection, match_id: int) -> tuple[str, dict]:
    analysis_id = connection.scalar(select(account_matches.c.active_analysis_id).where(
        account_matches.c.match_id == match_id))
    rows = connection.execute(select(metric_observations.c.metric_id, metric_observations.c.baseline_snapshot).where(
        metric_observations.c.analysis_id == analysis_id)).all()
    return analysis_id, dict(rows)


def test_late_replay_readmission_rebuilds_later_comparisons(database):
    """A late replay moves the late match's values into every later match's baseline."""
    _, profile_id = identity(database)
    history(database, profile_id, [0, 1, 2, 3, 4, 5])
    late = add_match(database, profile_id, index=20)
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == late).values(
            evidence_state="REPLAY_UNAVAILABLE", terminal_reason="REPLAY_CHECKS_EXHAUSTED",
            replay_role_assignment=None))
        connection.execute(update(acquisitions).where(acquisitions.c.match_id == late).values(
            state="REPLAY_UNAVAILABLE"))
    assert finalize(database, profile_id, late) == "READY"
    later = add_match(database, profile_id, index=21)
    assert finalize(database, profile_id, later) == "READY"
    with database.connect() as connection:
        later_before, baselines_before = _observations(connection, later)
        events_before = connection.scalar(select(func.count()).select_from(events))
        outbox_before = connection.scalar(select(func.count()).select_from(notification_outbox))

    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == late).values(
            evidence_state="REPLAY_READY", terminal_reason=None))
        connection.execute(update(acquisitions).where(acquisitions.c.match_id == late).values(state="REPLAY_READY"))
        [job_id] = enqueue_readmissions(connection, late)
        job = claim(connection, priority=3)
    assert job["id"] == job_id
    assert complete_readmit_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "READMITTED"

    with database.connect() as connection:
        later_after, baselines_after = _observations(connection, later)
        assert later_after != later_before
        # At least one replay-class baseline now counts the late match's value.
        assert any(baselines_after[metric] != baselines_before[metric] for metric in baselines_before)
        # Retroactive, never celebrated or notified.
        assert connection.scalar(select(func.count()).select_from(events)) == events_before
        assert connection.scalar(select(func.count()).select_from(notification_outbox)) == outbox_before


def _failed_backfill(database, user_id: str, profile_id: str, *, failed_at, error: str = "BACKFILL_PAGE_FAILED",
                     retries: int = 0) -> str:
    from app.tracker.backfill import request_pro_backfill

    with database.begin() as connection:
        job_id = request_pro_backfill(connection, profile_id, ceiling_days=365)
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == job_id).values(
            state="FAILED", attempts=5, last_error=error, run_after=failed_at,
            cursor={"offset": 200, "pages": 1, "request_days": 366, "daily_retries": retries}))
    return job_id


def _job(database, job_id: str) -> dict:
    with database.connect() as connection:
        return dict(connection.execute(select(ingest_jobs).where(ingest_jobs.c.id == job_id)).mappings().one())


def test_failed_pro_backfill_is_retried_daily_while_pro_is_live(database):
    from app.tracker.backfill import DAILY_BACKFILL_RETRIES, retry_failed_pro_backfills
    from app.tracker.entitlement import FakeAppStoreVerifier, submit_transaction

    from .test_entitlement import NOW, ready_bootstrap, transaction

    user_id, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    verifier = FakeAppStoreVerifier({"transaction:pro": transaction(user_id, token="pro")})
    submit_transaction(database, user_id=user_id, signed_transaction="pro", verifier=verifier, now=NOW)
    job_id = _failed_backfill(database, user_id, profile_id, failed_at=NOW - timedelta(hours=2))

    # Not yet a day since the failure: nothing to do.
    with database.begin() as connection:
        assert retry_failed_pro_backfills(connection, now=NOW) == 0
    assert _job(database, job_id)["state"] == "FAILED"

    with database.begin() as connection:
        assert retry_failed_pro_backfills(connection, now=NOW + timedelta(days=1)) == 1
    job = _job(database, job_id)
    assert job["state"] == "PENDING" and job["attempts"] == 0 and job["priority"] == 3
    # The scan resumes at its committed page instead of refetching earlier ones.
    assert job["cursor"]["offset"] == 200 and job["cursor"]["daily_retries"] == 1

    # Hitting the page ceiling is deterministic: retrying would fail the same way.
    with database.begin() as connection:
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == job_id).values(
            state="FAILED", run_after=NOW, last_error="PAGINATION_LIMIT"))
        assert retry_failed_pro_backfills(connection, now=NOW + timedelta(days=5)) == 0

    # The daily ladder is bounded.
    with database.begin() as connection:
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == job_id).values(
            state="FAILED", run_after=NOW, last_error="BACKFILL_PAGE_FAILED",
            cursor={**job["cursor"], "daily_retries": DAILY_BACKFILL_RETRIES}))
        assert retry_failed_pro_backfills(connection, now=NOW + timedelta(days=5)) == 0
    assert _job(database, job_id)["state"] == "FAILED"


def test_failed_pro_backfill_is_not_retried_without_pro(database):
    from app.tracker.backfill import retry_failed_pro_backfills

    from .test_entitlement import NOW, ready_bootstrap

    _, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    # No live subscription: a Free user never spends provider budget on Pro history.
    job_id = _failed_backfill(database, "", profile_id, failed_at=NOW - timedelta(days=2))
    with database.begin() as connection:
        assert retry_failed_pro_backfills(connection, now=NOW) == 0
    assert _job(database, job_id)["state"] == "FAILED"


def test_worker_beat_schedules_the_daily_backfill_retry():
    from app.tracker.worker import create_worker_app

    app = create_worker_app(Settings())
    assert app.conf.beat_schedule["tracker-backfill-retry"]["task"] == "tracker.retry_backfills"
    assert "tracker.retry_backfills" in app.tasks

