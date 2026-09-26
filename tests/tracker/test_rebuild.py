"""Rebuilds replay retained evidence deterministically, atomically and idempotently."""
from __future__ import annotations

from datetime import timedelta

from app.tracker import finalization, item_references, rebuild
from app.tracker.context import HeroLevel, MetricParameters, ParameterSet
from app.tracker.entitlement import (
    FakeAppStoreVerifier,
    apply_notification,
    reconcile_entitlement_scope,
    submit_transaction,
)
from app.tracker.jobs import claim
from app.tracker.profile import publish_profile_checkpoint
from app.tracker.rebuild import (
    complete_scope_rebuild_job,
    run_item_insight_rebuild,
    run_methodology_rebuild,
)
from app.tracker.schema import (
    account_matches,
    analyses,
    events,
    history_operations,
    metric_observations,
    parameter_sets,
    personal_bests,
    profile_states,
    profiles,
    provider_calls,
)
from sqlalchemy import func, select, update

from .builders import BASE_MATCH, add_match, finalize, history
from .test_entitlement import NOW, ready_bootstrap, transaction
from .test_schema import identity

METRIC = "support.camps_stacked.v1"
CONTEXT_METRIC = "support.healing.v1"


def _counts(connection):
    return {
        "analyses": connection.scalar(select(func.count()).select_from(analyses)),
        "observations": connection.scalar(select(func.count()).select_from(metric_observations)),
        "events": connection.scalar(select(func.count()).select_from(events).where(events.c.kind != "SCOPE_CHANGED")),
        "provider_calls": connection.scalar(select(func.count()).select_from(provider_calls)),
    }


def _observation(connection, profile_id, match_id, metric=METRIC):
    return connection.execute(select(metric_observations).join(
        account_matches, account_matches.c.active_analysis_id == metric_observations.c.analysis_id,
    ).where(account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id,
            metric_observations.c.metric_id == metric)).mappings().one()


def _cards(connection, match_id):
    from app.tracker.schema import insight_results

    return connection.execute(select(insight_results.c.cards, insight_results.c.contract_version).join(
        account_matches, account_matches.c.active_analysis_id == insight_results.c.analysis_id,
    ).where(account_matches.c.match_id == match_id)).one()


def _pb(connection, profile_id, revision):
    row = connection.execute(select(personal_bests.c.analysis_id, personal_bests.c.comparison_value).where(
        personal_bests.c.profile_id == profile_id, personal_bests.c.revision == revision,
        personal_bests.c.mode == "STANDARD", personal_bests.c.metric_id == METRIC,
    )).one_or_none()
    if row is None:
        return None
    match_id = connection.scalar(select(analyses.c.match_id).where(analyses.c.id == row.analysis_id))
    return match_id, row.comparison_value


def test_late_older_match_cannot_take_newer_pb_or_rolling_window(database):
    _, profile_id = identity(database)
    ids = history(database, profile_id, [0, 1, 2, 3, 4, 5, 50])
    with database.connect() as connection:
        best_before = _pb(connection, profile_id, 0)
    assert best_before[0] == ids[-1]
    # Admitted later but older than the current record holder, with a value
    # that beats every earlier match (as an import or recovery would be).
    late = add_match(database, profile_id, index=40, origin="BOOTSTRAP", stack_bonus=20, offset_days=5.5)
    assert finalize(database, profile_id, late) == "READY"
    with database.connect() as connection:
        assert _pb(connection, profile_id, 0) == best_before
        from app.tracker.schema import baselines

        rolling = connection.scalar(select(baselines.c.snapshot).where(
            baselines.c.profile_id == profile_id, baselines.c.metric_id == METRIC))
        assert rolling["source_match_ids"][-1] == ids[-1] and late in rolling["source_match_ids"]
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "NEW_PB", events.c.payload["match_id"].astext == str(late))) == 0


def test_current_patch_item_rebuild_keeps_old_v1_and_has_no_external_effects(database, monkeypatch):
    _, profile_id = identity(database)
    old = add_match(database, profile_id, index=90, offset_days=-10, origin="HISTORICAL")
    assert finalize(database, profile_id, old) == "READY"
    monkeypatch.setattr(item_references, "CURRENT_PATCH", "7.41g")
    current = add_match(database, profile_id, index=91, offset_days=0, origin="HISTORICAL")
    assert finalize(database, profile_id, current) == "READY"
    with database.connect() as connection:
        old_before = connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == old))
        current_before = connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == current))
        before = _counts(connection)
    monkeypatch.setattr(item_references, "CURRENT_PATCH", "7.41f")
    with database.begin() as connection:
        assert run_item_insight_rebuild(connection, profile_id=profile_id) == 1
    with database.connect() as connection:
        assert connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == old)) == old_before
        assert connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == current)) != current_before
        assert _cards(connection, old)[1] == "post-match-insights 1.0.0"
        assert _cards(connection, current)[1] == "post-match-insights 2.0.0"
        after = _counts(connection)
        assert after["events"] == before["events"]
        assert after["provider_calls"] == before["provider_calls"] == 0
    with database.begin() as connection:
        assert run_item_insight_rebuild(connection, profile_id=profile_id) == 0


def test_scope_rebuild_expands_contracts_and_reuses_identical_analyses(database):
    user_id, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    pre_link = history(database, profile_id, [10, 11, 12, 13, 14, 15], origin="HISTORICAL",
                       offset_days=[-10, -9, -8, -7, -6, -5])
    live = history(database, profile_id, [0, 1], start=10)
    with database.connect() as connection:
        free_obs = _observation(connection, profile_id, live[-1])
        free_analysis = connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == live[-1]))
        before = _counts(connection)
    assert free_obs["baseline_snapshot"]["prior_count"] == 1

    verifier = FakeAppStoreVerifier({
        "transaction:pro": transaction(user_id, token="pro"),
        "notification:refund": transaction(user_id, token="refund", signed=NOW + timedelta(days=1),
                                           revoked=NOW + timedelta(days=1)),
    })
    submit_transaction(database, user_id=user_id, signed_transaction="pro", verifier=verifier, now=NOW)
    operation_id = reconcile_entitlement_scope(database, user_id=user_id, now=NOW)["operation_id"]
    assert operation_id
    with database.connect() as connection:
        # Coherent Free state stays active until the rebuild publishes.
        assert connection.execute(select(profiles.c.active_scope, profiles.c.active_revision)).one() == ("FREE", 0)
    with database.begin() as connection:
        job = claim(connection, priority=3)
    assert job["job_type"] == "SCOPE_REBUILD"
    assert complete_scope_rebuild_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "COMPLETE"

    with database.connect() as connection:
        assert connection.execute(select(profiles.c.active_scope, profiles.c.active_revision)).one() == ("PRO", 1)
        pro_obs = _observation(connection, profile_id, live[-1])
        assert pro_obs["baseline_snapshot"]["prior_count"] == len(pre_link) + 1
        assert set(pro_obs["baseline_snapshot"]["source_match_ids"]) >= set(pre_link)
        assert _pb(connection, profile_id, 1) is not None
        after = _counts(connection)
        assert after["events"] == before["events"] and after["provider_calls"] == before["provider_calls"] == 0
        op = connection.execute(select(history_operations).where(history_operations.c.id == operation_id)).mappings().one()
        assert op["state"] == "COMPLETE" and op["cutoff_match_id"] == live[-1]
        assert connection.scalar(select(func.count()).select_from(events).where(events.c.kind == "SCOPE_CHANGED")) == 1

    # Running the same replay again reuses every analysis identity.
    with database.begin() as connection:
        profile = connection.execute(select(profiles).with_for_update()).mappings().one()
        rebuild.replay_closure(connection, profile=profile, modes=("STANDARD", "TURBO"))
        assert run_methodology_rebuild(connection, profile_id=profile_id) == 0
    with database.connect() as connection:
        assert _counts(connection) == after

    apply_notification(database, signed_notification="refund", verifier=verifier, now=NOW + timedelta(days=1))
    with database.begin() as connection:
        job = claim(connection, priority=3)
    assert complete_scope_rebuild_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "COMPLETE"
    with database.connect() as connection:
        assert connection.execute(select(profiles.c.active_scope, profiles.c.active_revision)).one() == ("FREE", 2)
        # Same inputs and versions → the identical analysis row, not a new one.
        assert connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == live[-1])) == free_analysis
        assert _counts(connection)["analyses"] == after["analyses"]
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind.in_(("NEW_PB", "MATCH_READY")))) == before["events"]


def _test_parameters(version: str) -> ParameterSet:
    return ParameterSet(
        version=version, validated=True, opponent_coverage=0.99, cs_slope_regression_passed=True,
        hero_levels={(123, 4, CONTEXT_METRIC): HeroLevel(40.0, 500),
                     (123, 5, CONTEXT_METRIC): HeroLevel(40.0, 500)}, opponent_effects={},
        role_slopes={"CARRY": 1.0, "MID": 1.0, "OFFLANE": 1.0},
        lane_thresholds={"CARRY": (-2.0, 2.0)},
        metrics={CONTEXT_METRIC: MetricParameters(5.0, 0.35, 0.0, 0.0),
                 METRIC: MetricParameters(1.0, 0.35, 0.0, 0.0)},
    )


def test_parameter_set_change_replays_smallest_bucket_closure_twice_without_effects(database, monkeypatch):
    _, profile_id = identity(database)
    standard = history(database, profile_id, [0, 1, 2, 3, 4, 5, 6])
    with database.connect() as connection:
        assert _observation(connection, profile_id, standard[-1])["parameter_set_version"] is None
        cards_before = _cards(connection, standard[-1])

    parameters = _test_parameters("test-only-context-v1")
    with database.begin() as connection:
        connection.execute(parameter_sets.insert().values(
            version=parameters.version, kind="CONTEXT_POPULATION", digest="0" * 64, status="TEST_ONLY",
            parameters={"test_only": True}, provenance={"fixture": "test-only"}, created_at=func.now()))
    monkeypatch.setattr(finalization, "current_context_parameters", lambda connection: parameters)
    monkeypatch.setattr(rebuild, "current_context_parameters", lambda connection: parameters)
    # Turbo finalizes under the new set; only Standard history is stale.
    turbo = add_match(database, profile_id, index=30, turbo=True)
    assert finalize(database, profile_id, turbo) == "READY"
    with database.connect() as connection:
        turbo_analysis = connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == turbo))
        before = _counts(connection)
    with database.begin() as connection:
        assert run_methodology_rebuild(connection, profile_id=profile_id) == len(standard)
    with database.connect() as connection:
        rebuilt = _counts(connection)
        latest = _observation(connection, profile_id, standard[-1], CONTEXT_METRIC)
        assert latest["parameter_set_version"] == parameters.version
        assert latest["context_h"] == 40.0
        assert latest["performance_state"] in {"ABOVE", "IN_LINE", "BELOW"}
        assert connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == turbo)) == turbo_analysis
        assert rebuilt["analyses"] == before["analyses"] + len(standard)
        assert rebuilt["events"] == before["events"] and rebuilt["provider_calls"] == 0
    with database.begin() as connection:
        assert run_methodology_rebuild(connection, profile_id=profile_id) == 0
    with database.connect() as connection:
        assert _counts(connection) == rebuilt
        # Insight cards never read context terms or lane labels (match detail §10.9).
        assert _cards(connection, standard[-1]) == cards_before


def test_profile_checkpoint_serves_fallback_identity_and_withholds_uncalibrated_claims(database):
    _, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    history(database, profile_id, list(range(12)))
    with database.connect() as connection:
        stored = connection.execute(select(profile_states).where(
            profile_states.c.profile_id == profile_id, profile_states.c.mode == "STANDARD",
        )).mappings().one()
    state = stored["state"]
    assert stored["cause"] == "PLAY" and stored["checkpoint_seq"] == 12
    assert state["identity"] == {"template_id": "MOSTLY_ROLE_SO_FAR", "slots": {"role": "SUPPORT"},
                                 "confirmed": False}
    assert state["header"]["eligible_count"] == 12 and state["header"]["getting_to_know"] is False
    assert [row["count"] for row in state["role_map"]] == [0, 0, 0, 12]
    assert all(row["share"] is None and row["tier"] is None for row in state["role_map"])
    assert state["heroes"][0]["most_played"] == [{"hero_id": 123, "count": 12}]
    assert state["heroes"][0]["tags_state"] == "CALIBRATION_PENDING"
    assert state["claims_state"] == "CALIBRATION_PENDING" and state["claims"] == []
    with database.begin() as connection:
        assert publish_profile_checkpoint(connection, profile_id=profile_id, cause="PLAY",
                                          modes=("STANDARD",)) == []
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "PROFILE_CHANGE")) == 0


def test_profile_keeps_last_checkpoint_while_mode_import_runs(database):
    from app.tracker.schema import bootstrap

    _, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    history(database, profile_id, [0, 1])
    with database.begin() as connection:
        connection.execute(update(bootstrap).where(bootstrap.c.mode == "STANDARD").values(
            completed_at=None, outcome=None, search_finished=False))
        assert publish_profile_checkpoint(connection, profile_id=profile_id, cause="IMPORT") == ["TURBO"]
        stored = connection.scalar(select(profile_states.c.state).where(profile_states.c.mode == "STANDARD"))
    assert stored["header"]["eligible_count"] == 2
    assert BASE_MATCH  # builders stay fixture-only
