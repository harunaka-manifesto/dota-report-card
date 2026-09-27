from datetime import timedelta

from app.tracker.finalization import (
    _metric_conflict,
    complete_finalization_job,
    enqueue_finalization,
)
from app.tracker.jobs import claim, enqueue
from app.tracker.materialization import materialize_snapshot
from app.tracker.metrics import metric_ids
from app.tracker.mobile_api import (
    _carry_context_view,
    _core_fights_view,
    _item_timings_view,
    _match_view,
    _mid_context_view,
    _offlane_context_view,
)
from app.tracker.role_correction import correct_role
from app.tracker.schema import (
    account_matches,
    analyses,
    coverage,
    events,
    insight_results,
    matches,
    metric_observations,
    provider_calls,
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
        frozen = c.scalar(select(analyses.c.result))["item_timings"]
        assert frozen["state"] == "AVAILABLE"
        assert frozen["contract_version"] == "item-timings-v1"
        assert frozen["items"] == sorted(
            frozen["items"], key=lambda item: (item["purchase_time_seconds"], item["item_id"]),
        )
        insight = c.execute(select(insight_results)).mappings().one()
        # insights.CONTRACT_VERSION is fixed regardless of subpatch; item cards
        # are gated separately, upstream in finalization's item timing lookup.
        assert insight["contract_version"] == "post-match-insights 2.0.0"
        assert isinstance(insight["cards"], list) and len(insight["cards"]) <= 3
        projected = _match_view(c, link).model_dump()
        assert projected["insights"] == {
            "state": "AVAILABLE", "contract_version": "post-match-insights 2.0.0",
            "reason": None, "cards": [],
        }
        assert c.scalar(select(func.count()).select_from(events)) == 1
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
        assert c.scalar(select(func.count()).select_from(insight_results)) == 1
        assert c.scalar(select(func.count()).select_from(metric_observations)) == metric_count
        assert c.scalar(select(func.count()).select_from(events)) == 1


def test_offlane_match_detail_is_pending_then_reads_frozen_context(database):
    profile_id = _ready_link(database)
    with database.begin() as connection:
        connection.execute(account_matches.update().values(effective_role="OFFLANE"))
        link = connection.execute(select(account_matches)).mappings().one()
        pending = _offlane_context_view(connection, link)
        assert pending is not None
        assert pending.net_worth.state == pending.xp.state == pending.fights.state == "PENDING"
    assert _run(database, profile_id) == "READY"
    with database.begin() as connection:
        correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                     role="OFFLANE", expected_role_revision=0)
    with database.connect() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        view = _offlane_context_view(connection, link)
        persisted = connection.scalar(select(analyses.c.result).where(
            analyses.c.id == link["active_analysis_id"],
        ))["offlane_context"]
        assert view is not None and view.model_dump() == persisted
        assert view.fights.state == "AVAILABLE" and len(view.fights.segments) == 19
        assert view.fights.segments[0].death_trade == "UNFAVORABLE"


def test_carry_match_detail_reads_frozen_graphs_and_rebuilds_after_role_correction(database):
    profile_id = _ready_link(database)
    with database.connect() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        pending = _carry_context_view(connection, link)
        assert pending is not None
        assert pending.net_worth.state == pending.hero_damage.state == "PENDING"
    assert _run(database, profile_id) == "READY"
    with database.begin() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        if link["effective_role"] != "CARRY":
            correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                         role="CARRY", expected_role_revision=link["role_revision"])
    with database.connect() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        view = _carry_context_view(connection, link)
        assert view is not None
        stored = connection.scalar(select(analyses.c.result).where(
            analyses.c.id == link["active_analysis_id"],
        ))["carry_context"]
        assert view.model_dump() == stored
        assert view.net_worth.state == view.hero_damage.state == "AVAILABLE"
        assert view.enemy_key_items.state == view.you_kills.state == view.enemy_carry_kills.state == "AVAILABLE"
        assert _item_timings_view(connection, link).items
        assert connection.scalar(select(func.count()).select_from(provider_calls)) == 0
    with database.begin() as connection:
        revision = connection.scalar(select(account_matches.c.role_revision))
        correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                     role="MID", expected_role_revision=revision)
        link = connection.execute(select(account_matches)).mappings().one()
        assert _carry_context_view(connection, link) is None
    with database.begin() as connection:
        correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                     role="CARRY", expected_role_revision=revision + 1)
        link = connection.execute(select(account_matches)).mappings().one()
        restored = _carry_context_view(connection, link)
        assert restored is not None and restored.model_dump() == view.model_dump()
        assert connection.scalar(select(func.count()).select_from(provider_calls)) == 0


def test_core_fights_and_mid_context_survive_role_correction_without_provider_calls(database):
    profile_id = _ready_link(database)
    with database.connect() as connection:
        link = connection.execute(select(account_matches)).mappings().one()
        assert _core_fights_view(connection, link).state == "PENDING"
    assert _run(database, profile_id) == "READY"
    for role in ("CARRY", "MID", "OFFLANE", "SUPPORT"):
        with database.begin() as connection:
            link = connection.execute(select(account_matches)).mappings().one()
            if link["effective_role"] != role:
                correct_role(connection, profile_id=profile_id, match_id=MATCH_ID,
                             role=role, expected_role_revision=link["role_revision"])
        with database.connect() as connection:
            link = connection.execute(select(account_matches)).mappings().one()
            result = connection.scalar(select(analyses.c.result).where(
                analyses.c.id == link["active_analysis_id"],
            ))
            fights = _core_fights_view(connection, link)
            mid = _mid_context_view(connection, link)
            if role == "SUPPORT":
                assert fights is None and mid is None
                assert result["core_fights"] is None and result["mid_context"] is None
            else:
                assert fights.model_dump() == result["core_fights"]
                assert fights.state == "AVAILABLE" and len(fights.segments) == 19
                assert fights.segments[-1].start_seconds > 900
                if role == "MID":
                    assert mid.model_dump() == result["mid_context"]
                    assert mid.net_worth.state == "AVAILABLE"
                    assert mid.net_worth.points
                else:
                    assert mid is None and result["mid_context"] is None
            assert connection.scalar(select(func.count()).select_from(provider_calls)) == 0


def test_old_offlane_context_remains_a_safe_unavailable_view():
    class OldAnalysis:
        def scalar(self, _query):
            return {"offlane_context": {"contract_version": "offlane-context-v1"}}

    view = _offlane_context_view(OldAnalysis(), {
        "effective_role": "OFFLANE", "active_analysis_id": "old",
    })
    assert view is not None
    assert view.fights.state == "UNAVAILABLE" and view.fights.reason == "ANALYSIS_VERSION"


def test_old_core_graphs_remain_safe_unavailable_views():
    class OldAnalysis:
        def scalar(self, _query):
            return {}

    row = {"effective_role": "MID", "active_analysis_id": "old", "lifecycle": "READY"}
    assert _mid_context_view(OldAnalysis(), row).net_worth.reason == "ANALYSIS_VERSION"
    assert _core_fights_view(OldAnalysis(), row).reason == "ANALYSIS_VERSION"


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


def test_ambiguous_integrity_withholds_insight_cards(database):
    profile_id = _ready_link(database)
    with database.begin() as c:
        c.execute(matches.update().where(matches.c.match_id == MATCH_ID).values(
            quarantined_fields=["mode"],
        ))
    assert _run(database, profile_id) == "READY"
    with database.connect() as c:
        link = c.execute(select(account_matches)).mappings().one()
        assert link["progression"] == "NONE"
        view = _match_view(c, link)
        assert view.insights.state == "UNAVAILABLE"
        assert view.insights.reason == "PROGRESSION"
        assert view.insights.cards == []


def test_disputed_source_withholds_insight_cards_without_blocking_ready(database):
    profile_id = _ready_link(database)
    with database.begin() as c:
        c.execute(matches.update().where(matches.c.match_id == MATCH_ID).values(
            quarantined_fields=["players.0.series.net_worth.420"],
        ))
    assert _run(database, profile_id) == "READY"
    with database.connect() as c:
        link = c.execute(select(account_matches)).mappings().one()
        assert link["progression"] == "STANDARD"
        assert _match_view(c, link).insights.reason == "SOURCE_DISAGREEMENT"


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
