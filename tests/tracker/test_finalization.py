from datetime import timedelta

from app.tracker.finalization import (
    _metric_conflict,
    complete_finalization_job,
    enqueue_finalization,
)
from app.tracker.jobs import claim, enqueue
from app.tracker.materialization import materialize_snapshot
from app.tracker.metrics import metric_ids
from app.tracker.schema import (
    account_matches,
    analyses,
    coverage,
    events,
    matches,
    metric_observations,
)
from sqlalchemy import func, select

from .test_materialization import MATCH_ID, raw, save
from .test_schema import identity


def _ready_link(database, *, parsed=True):
    _, profile_id = identity(database)
    payload = raw()
    payload["players"][0]["account_id"] = 1001
    if not parsed:
        payload["version"] = None
    with database.begin() as c:
        snapshot_id = save(c, payload)
        projection = materialize_snapshot(c, snapshot_id=snapshot_id, match_id=MATCH_ID)
        match = c.execute(select(matches).where(matches.c.match_id == MATCH_ID)).mappings().one()
        c.execute(matches.update().where(matches.c.match_id == MATCH_ID).values(
            evidence_state="REPLAY_READY" if parsed else "REPLAY_UNAVAILABLE",
            replay_role_assignment=projection["role_assignment"] if parsed else None,
            terminal_reason=None if parsed else "REPLAY_CHECKS_EXHAUSTED",
            replay_terminal_at=func.clock_timestamp(),
        ))
        c.execute(account_matches.insert().values(
            profile_id=profile_id, match_id=MATCH_ID, account_id=1001, player_slot=0,
            lifecycle="ANALYZING", mode=match["mode"], effective_role="CARRY",
            provider_started_at=match["started_at"], provider_source_match_id=MATCH_ID,
            origin="LIVE",
        ))
    return profile_id


def _run(database, profile_id, match_id=MATCH_ID):
    with database.begin() as c:
        enqueue_finalization(c, profile_id=profile_id, match_id=match_id)
        job = claim(c, priority=0)
    assert job is not None
    return complete_finalization_job(database, job_id=job["id"], lease_token=job["lease_token"])


def test_terminal_analysis_publishes_once_from_retained_source(database):
    profile_id = _ready_link(database)
    assert _run(database, profile_id) == "READY"
    with database.connect() as c:
        link = c.execute(select(account_matches)).mappings().one()
        assert link["lifecycle"] == "READY" and link["active_analysis_id"]
        assert link["progression"] == "STANDARD"
        metric_count = len(metric_ids(link["effective_role"]))
        assert c.scalar(select(func.count()).select_from(metric_observations)) == metric_count
        assert c.scalar(select(func.count()).select_from(analyses)) == 1
        assert c.scalar(select(func.count()).select_from(events)) == 0
        assert dict(c.execute(select(coverage.c.evidence_class, coverage.c.state)).all()) == {
            "SUMMARY": "KNOWN", "REPLAY": "KNOWN",
        }
    with database.begin() as c:
        enqueue(c, dedup_key="duplicate-finalize-attempt", job_type="FINALIZE", priority=0,
                profile_id=profile_id, match_id=MATCH_ID, payload={})
        retry = claim(c, priority=0)
    assert retry is not None
    assert complete_finalization_job(database, job_id=retry["id"], lease_token=retry["lease_token"]) == "ALREADY_READY"
    with database.connect() as c:
        assert c.scalar(select(func.count()).select_from(analyses)) == 1
        assert c.scalar(select(func.count()).select_from(metric_observations)) == metric_count


def test_replay_unavailable_still_finalizes_with_reasoned_na_metrics(database):
    profile_id = _ready_link(database, parsed=False)
    assert _run(database, profile_id) == "READY"
    with database.connect() as c:
        rows = c.execute(select(metric_observations)).mappings().all()
        assert len(rows) == 6
        assert any(row["unavailable_reason"] == "REPLAY_UNAVAILABLE" for row in rows)
        assert all((row["raw_value"] is None) == (row["unavailable_reason"] is not None) for row in rows)
        assert dict(c.execute(select(coverage.c.evidence_class, coverage.c.state)).all()) == {
            "SUMMARY": "KNOWN", "REPLAY": "GAP",
        }


def test_later_same_bucket_waits_for_prior_without_blocking_other_bucket(database):
    profile_id = _ready_link(database)
    with database.begin() as c:
        first = c.execute(select(account_matches)).mappings().one()
        later_id = MATCH_ID + 1
        c.execute(matches.insert().values(match_id=later_id, started_at=first["provider_started_at"] + timedelta(hours=1),
            duration_seconds=1800, mode="STANDARD", radiant_win=True, header={},
            evidence_state="REPLAY_UNAVAILABLE", terminal_reason="REPLAY_EXPIRED",
            discovered_at=first["provider_started_at"], summary_ready_at=first["provider_started_at"]))
        from app.tracker.schema import match_players
        c.execute(match_players.insert(), [dict(match_id=later_id, player_slot=slot, hero_id=slot + 1,
            account_id=1001 if slot == 0 else None, team="RADIANT" if slot < 5 else "DIRE", summary={})
            for slot in range(10)])
        c.execute(account_matches.insert().values(profile_id=profile_id, match_id=later_id, account_id=1001,
            player_slot=0, lifecycle="ANALYZING", mode="STANDARD", effective_role="CARRY",
            provider_started_at=first["provider_started_at"] + timedelta(hours=1),
            provider_source_match_id=later_id, origin="LIVE"))
    assert _run(database, profile_id, later_id) == "WAITING_FOR_PRIOR_MATCH"
    with database.connect() as c:
        assert c.scalar(select(account_matches.c.lifecycle).where(account_matches.c.match_id == later_id)) == "WAITING_FOR_PRIOR_MATCH"
        assert c.scalar(select(func.count()).select_from(analyses)) == 0


def test_unrelated_disagreement_does_not_quarantine_valid_checkpoint():
    metric = "carry.net_worth_at_20.v1"
    assert not _metric_conflict(metric, 0, ["players.0.series.net_worth.420"])
    assert _metric_conflict(metric, 0, ["players.0.series.net_worth.1200"])
    assert not _metric_conflict(metric, 0, ["players.7.series.net_worth.1200"])
