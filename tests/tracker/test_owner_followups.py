"""Owner decisions on the independent QA doubts (2026-09-25).

Each test drives the real job handlers with only provider HTTP replaced by
deterministic fakes; nothing here reaches a provider.
"""
from __future__ import annotations

from app.tracker.jobs import claim
from app.tracker.rebuild import complete_readmit_job, enqueue_readmissions
from app.tracker.schema import account_matches, acquisitions, events, matches, metric_observations, notification_outbox
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
