"""Second batch of acceptance-rule evidence from the traceability audit."""
from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.tracker import finalization, history, rebuild
from app.tracker.account_lifecycle import (
    AccountLifecycleError,
    request_account_deletion,
    switch_preflight,
    switch_steam_profile,
)
from app.tracker.backfill import backfill_page, request_access_recovery
from app.tracker.bootstrap import settle_bootstrap
from app.tracker.context import (
    ContextInput,
    DraftPlayer,
    HeroLevel,
    MetricParameters,
    ParameterSet,
    evaluate,
)
from app.tracker.insights import _attach_optional_history
from app.tracker.jobs import claim
from app.tracker.rebuild import (
    RebuildUnavailable,
    complete_methodology_job,
    enqueue_methodology_rebuilds,
)
from app.tracker.schema import (
    account_matches,
    bootstrap,
    coverage,
    devices,
    events,
    history_operations,
    ingest_jobs,
    matches,
    notification_outbox,
    profile_states,
    profiles,
    users,
)
from sqlalchemy import func, select, update

from .builders import add_match, finalize
from .builders import history as build_history
from .test_contract_rules import _client
from .test_mobile_golden import OPENAPI
from .test_provider_transport import gate_for

# Words that would signal a verdict, score or ranking the product forbids.
VERDICT_FIELDS = re.compile(r"score|grade|rating|percentile|rank|verdict|composite|win_?rate|streak|kda",
                            re.IGNORECASE)


def test_mobile_contract_has_no_score_grade_percentile_or_composite_fields():
    schema = json.loads(OPENAPI.read_text())
    names: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            names.extend(node.get("properties", {}).keys())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
    walk(schema)
    offending = sorted({name for name in names if VERDICT_FIELDS.search(name)})
    assert offending == []
    components = schema["components"]["schemas"]
    assert "trend" not in components["MatchDetailView"]["properties"]
    assert set(components["ProgressView"]["properties"]) == {
        "mode", "role", "metric_id", "points", "personal_best", "trend"}
    assert not {"won", "result"} & set(components["ProgressPoint"]["properties"])


def test_insight_copy_never_claims_causes_or_judges_teammates():
    source = open(finalization.__file__.replace("finalization.py", "insights.py")).read()
    literals = [node for node in re.findall(r'f?"([^"\n]{12,})"', source) if " " in node]
    forbidden = re.compile(r"\bbecause\b|\bcaused\b|\bthanks to\b|\bfault\b|\bteammates?\b|\bcarried\b|"
                           r"\bfed\b|\bthrew\b|\bblame", re.IGNORECASE)
    assert [text for text in literals if forbidden.search(text)] == []


def test_history_lines_state_n_and_respect_the_sample_gate():
    match = {"bucket": "STANDARD", "startDateTime": 10_000, "matchId": 999, "major_patch": "7.40"}

    def rows(count):
        return {"observations": [{"metric": "STACKS", "bucket": "STANDARD", "role": "MID", "item": None,
                                  "patch": None, "value": value, "startDateTime": 100 + value, "matchId": value + 1}
                                 for value in range(count)]}
    below = {"candidate_id": "ENEMY_STACKING", "slots": {"enemy": 99}, "history_line": None}
    _attach_optional_history(match, {}, rows(9), [below])
    assert below["history_line"] is None
    above = {"candidate_id": "ENEMY_STACKING", "slots": {"enemy": 99}, "history_line": None}
    _attach_optional_history(match, {}, rows(25), [above])
    assert above["history_line"] and "25" in above["history_line"]


def _context(**changes):
    players = (DraftPlayer(1, 1, "SAFE_LANE", True), DraftPlayer(2, 2, "MID_LANE", True),
               DraftPlayer(3, 3, "OFF_LANE", True), DraftPlayer(4, 4, "SAFE_LANE", True),
               DraftPlayer(5, 5, "OFF_LANE", True), DraftPlayer(11, 1, "SAFE_LANE", False),
               DraftPlayer(12, 2, "MID_LANE", False), DraftPlayer(13, 3, "OFF_LANE", False),
               DraftPlayer(14, 4, "SAFE_LANE", False), DraftPlayer(15, 5, "OFF_LANE", False))
    values = dict(metric_id="carry.net_worth_at_20.v1", role="CARRY", mode="STANDARD", hero_id=1, position=1,
                  lane="SAFE_LANE", is_radiant=True, players=players, comparison_value=12000.0,
                  baseline=10000.0, prior_count=5, prior_hero_levels=(0.0, 0.0, 0.0),
                  prior_lane_scores=(0.0, 0.0, 0.0))
    values.update(changes)
    return ContextInput(**values)


def _params(metric):
    return ParameterSet(
        version="test-only-context-v1", validated=True, opponent_coverage=0.99, cs_slope_regression_passed=True,
        hero_levels={(1, 1, metric): HeroLevel(100.0, 500), (4, 4, "support.healing.v1"): HeroLevel(5.0, 500)},
        opponent_effects={(1, 13): 1.0, (1, 15): 1.0}, role_slopes={"CARRY": 1.0, "MID": 1.0, "OFFLANE": 1.0},
        lane_thresholds={"CARRY": (-2.0, 2.0)},
        metrics={metric: MetricParameters(1000.0, 0.35, 0.0, 0.0),
                 "support.healing.v1": MetricParameters(10.0, 0.35, 0.0, 0.0)})


def test_class_b_adjusts_hero_only_class_d_never_and_lane_label_is_standard_core_only():
    b = evaluate(_context(), _params("carry.net_worth_at_20.v1"))
    assert b.context_class == "B" and b.delta_hero == 100.0 and b.delta_lane == 0
    d = evaluate(_context(metric_id="carry.dead_time.v1", comparison_value=0.1, baseline=0.12),
                 _params("carry.dead_time.v1"))
    assert d.context_class == "D" and d.delta_hero == d.delta_lane == 0
    assert d.performance_state in {"ABOVE", "IN_LINE", "BELOW"}
    turbo = evaluate(_context(mode="TURBO"), _params("carry.net_worth_at_20.v1"))
    assert turbo.lane_context == "UNAVAILABLE" and turbo.delta_hero == 0
    support = evaluate(_context(metric_id="support.healing.v1", role="SUPPORT", hero_id=4, position=4,
                                comparison_value=80.0, baseline=70.0), _params("support.healing.v1"))
    assert support.lane_context == "UNAVAILABLE"
    # A difficult lane may lower the expectation but never flips the label into the state.
    difficult = evaluate(_context(comparison_value=5000.0), _params("carry.net_worth_at_20.v1"))
    assert difficult.performance_state == "BELOW"


def test_retry_is_refused_for_ready_matches_including_replay_unavailable(database):
    client, headers, profile_id, _ = _client(database)
    [match_id] = build_history(database, profile_id, [0])
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == match_id).values(
            evidence_state="REPLAY_UNAVAILABLE", terminal_reason="REPLAY_CHECKS_EXHAUSTED"))
    [row] = client.get("/history", headers=headers).json()["matches"]
    refused = client.post(f"/matches/{row['ref']}/retry", headers={**headers, "Idempotency-Key": "retry-ready-1"})
    assert refused.status_code == 409 and refused.json()["code"] == "RETRY_NOT_AVAILABLE"


def test_offlane_objective_involvement_is_diagnostic_and_correction_available_on_old_matches(database):
    client, headers, profile_id, _ = _client(database)
    for index, (role, days) in enumerate([("OFFLANE", 1), ("SUPPORT", 20)]):
        assert finalize(database, profile_id, add_match(database, profile_id, index=index, role=role,
                                                         keep_role=True, offset_days=days)) == "READY"
    rows = client.get("/history", headers=headers).json()["matches"]
    details = {row["role"]: client.get(f"/matches/{row['ref']}", headers=headers).json() for row in rows}
    objective = next(m for m in details["OFFLANE"]["metrics"] if m["metric_id"] == "offlane.objective_involvement.v1")
    assert objective["diagnostic_only"] is True and objective["performance_state"] is None
    assert all(detail["correction_available"] for detail in details.values())


def test_stage_one_facts_are_unchanged_after_ready(database):
    client, headers, profile_id, _ = _client(database)
    match_id = add_match(database, profile_id, index=1)
    with database.begin() as connection:
        connection.execute(update(account_matches).where(account_matches.c.match_id == match_id)
                           .values(lifecycle="WAITING_FOR_PROVIDER"))
    [row] = client.get("/history", headers=headers).json()["matches"]
    stage_one = client.get(f"/matches/{row['ref']}", headers=headers).json()
    with database.begin() as connection:
        connection.execute(update(account_matches).where(account_matches.c.match_id == match_id)
                           .values(lifecycle="ANALYZING"))
    assert finalize(database, profile_id, match_id) == "READY"
    ready = client.get(f"/matches/{row['ref']}", headers=headers).json()
    for key in ("players", "started_at", "duration_seconds", "won", "mode", "ref"):
        assert ready[key] == stage_one[key]


def test_bootstrap_origin_replay_unavailable_match_is_ready_counted_and_quiet(database):
    client, headers, profile_id, user_id = _client(database)
    with database.begin() as connection:
        connection.execute(update(users).values(notifications_enabled=True))
        connection.execute(devices.insert().values(id=str(uuid4()), user_id=user_id, push_token="token",
                                                   permission="GRANTED",
                                                   last_active_at=datetime.now(UTC) - timedelta(hours=3)))
    match_id = add_match(database, profile_id, index=1, origin="BOOTSTRAP", offset_days=-2)
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == match_id).values(
            evidence_state="REPLAY_UNAVAILABLE", terminal_reason="HISTORICAL_REPLAY_ABSENT", replay_role_assignment=None))
    assert finalize(database, profile_id, match_id) == "READY"
    [row] = client.get("/history", headers=headers).json()["matches"]
    detail = client.get(f"/matches/{row['ref']}", headers=headers).json()
    assert detail["progression"] == "STANDARD"
    assert any(m["state"] == "NOT_AVAILABLE" for m in detail["metrics"])
    assert all(m["raw_value"] != 0 or m["state"] == "MEASURED" for m in detail["metrics"])
    with database.begin() as connection:
        connection.execute(update(bootstrap).values(completed_at=None, outcome=None, settled_count=0,
                                                    discovered_count=0, eligible_count=0))
        settle_bootstrap(connection, profile_id)
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "BOOTSTRAP_COMPLETED")) == 1
        # Completion is in-app only: nothing waits in the push outbox for a later permission grant.
        assert connection.scalar(select(func.count()).select_from(notification_outbox)) == 0
        assert connection.scalar(select(profile_states.c.cause).where(
            profile_states.c.mode == "STANDARD")) == "IMPORT"


async def test_access_recovery_scan_queues_only_post_link_unheld_matches(database, redis_client):
    import httpx

    _, _, profile_id, _ = _client(database, linked=datetime(2026, 9, 1, tzinfo=UTC))
    held = build_history(database, profile_id, [0], offset_days=[2])
    with database.begin() as connection:
        job_id = request_access_recovery(connection, profile_id, episode="1")
        assert request_access_recovery(connection, profile_id, episode="1") == job_id
        job = claim(connection, priority=3)
    stamp = lambda days: int((datetime(2026, 9, 1, tzinfo=UTC) + timedelta(days=days)).timestamp())  # noqa: E731
    page = [{"match_id": 501, "start_time": stamp(5), "game_mode": 22},
            {"match_id": held[0], "start_time": stamp(2), "game_mode": 22},
            {"match_id": 502, "start_time": stamp(-3), "game_mode": 22}]
    outcome = await backfill_page(database, gate_for(redis_client, "opendota"), Settings(), job_id=job_id,
                                  lease_token=job["lease_token"],
                                  transport=httpx.MockTransport(lambda request: httpx.Response(200, json=page)))
    assert outcome == "DEFERRED" or outcome == "COMPLETE"
    with database.connect() as connection:
        batches = connection.execute(select(ingest_jobs.c.payload).where(
            ingest_jobs.c.job_type == "HISTORICAL_BATCH")).scalars().all()
        linked = connection.scalar(select(profiles.c.original_linked_at))
    assert [batch["match_ids"] for batch in batches] == [[501]] and batches[0]["origin"] == "RECOVERY"
    assert linked == datetime(2026, 9, 1, tzinfo=UTC)


def test_profile_and_progress_agree_buckets_stay_separate_and_gaps_are_absent(database):
    client, headers, profile_id, _ = _client(database)
    build_history(database, profile_id, [0, 1, 2, 3, 4, 6])
    turbo = add_match(database, profile_id, index=30, turbo=True)
    assert finalize(database, profile_id, turbo) == "READY"
    with database.begin() as connection:
        connection.execute(coverage.insert().values(
            id=str(uuid4()), profile_id=profile_id, mode="STANDARD", evidence_class="SUMMARY",
            start_at=datetime(2026, 1, 1, tzinfo=UTC), end_at=datetime(2026, 6, 1, tzinfo=UTC), state="GAP",
            reason="SOURCE_MISSING"))
        from app.tracker.profile import publish_profile_checkpoint

        publish_profile_checkpoint(connection, profile_id=profile_id, cause="PLAY")
    standard = client.get("/profile?mode=STANDARD", headers=headers).json()
    turbo_view = client.get("/profile?mode=TURBO", headers=headers).json()
    assert standard["header"]["eligible_count"] == 6 and turbo_view["header"]["eligible_count"] == 1
    # A GAP is never presented as known history: the earliest known point is after it.
    assert standard["coverage"]["earliest_known_at"] >= "2026-08"
    progress = client.get("/progress", params={"mode": "STANDARD", "role": "SUPPORT",
                                               "metric_id": "support.camps_stacked.v1"}, headers=headers).json()
    profile_pb = next(pb for pb in standard["personal_bests"] if pb["metric_id"] == "support.camps_stacked.v1")
    assert profile_pb["value"] == progress["personal_best"]["value"] and profile_pb["match_ref"] == progress["personal_best"]["match_ref"]
    assert all(pb["metric_id"] != "support.camps_stacked.v1" or pb["value"] < 10
               for pb in turbo_view["personal_bests"])


def test_progress_readiness_is_per_metric_inactivity_neutral_and_filters_validate(database):
    client, headers, profile_id, _ = _client(database)
    build_history(database, profile_id, [0, 1, 2, 3, 4, 5, 6], offset_days=[1, 2, 3, 4, 5, 205, 206])
    params = {"mode": "STANDARD", "role": "SUPPORT"}
    stacked = client.get("/progress", params={**params, "metric_id": "support.camps_stacked.v1"}, headers=headers).json()
    denial = client.get("/progress", params={**params, "metric_id": "support.vision_denial.v1"}, headers=headers).json()
    assert len(stacked["points"]) == 7 and denial["points"] == [] and denial["personal_best"] is None
    # A 200-day break contributes nothing: the sixth point still uses all five priors.
    assert stacked["points"][5]["prior_count"] == 5 and stacked["points"][5]["baseline_value"] == 6.0
    assert client.get("/progress", params={**params, "metric_id": "carry.dead_time.v1"},
                      headers=headers).json()["code"] == "METRIC_INVALID"
    unstarted = client.get("/progress", params={"mode": "STANDARD", "role": "CARRY",
                                                "metric_id": "carry.dead_time.v1"}, headers=headers).json()
    assert unstarted["points"] == [] and unstarted["personal_best"] is None
    assert unstarted["trend"]["state"] == "INSUFFICIENT_HISTORY"
    turbo = client.get("/progress", params={"mode": "TURBO", "role": "SUPPORT",
                                            "metric_id": "support.camps_stacked.v1"}, headers=headers).json()
    assert turbo["points"] == []


def test_baseline_version_bump_rebuilds_once_and_a_failed_migration_keeps_prior_state(database, monkeypatch):
    _, _, profile_id, _ = _client(database)
    ids = build_history(database, profile_id, [0, 1, 2])
    with database.connect() as connection:
        before = dict(connection.execute(select(account_matches.c.match_id, account_matches.c.active_analysis_id)).all())
    for module in (finalization, rebuild, history):
        monkeypatch.setattr(module, "BASELINE_VERSION", "rolling-median-20-v2-test")
    with database.begin() as connection:
        assert enqueue_methodology_rebuilds(connection) == 1
        job = claim(connection, priority=3)

    def unavailable(connection, link):
        raise RebuildUnavailable("retained source missing")
    monkeypatch.setattr(rebuild, "rebuild_inputs", unavailable)
    with pytest.raises(RebuildUnavailable):
        complete_methodology_job(database, job_id=job["id"], lease_token=job["lease_token"])
    with database.connect() as connection:
        assert dict(connection.execute(select(account_matches.c.match_id,
                                              account_matches.c.active_analysis_id)).all()) == before
    monkeypatch.undo()
    for module in (finalization, rebuild, history):
        monkeypatch.setattr(module, "BASELINE_VERSION", "rolling-median-20-v2-test")
    with database.begin() as connection:
        assert rebuild.run_methodology_rebuild(connection, profile_id=profile_id) == len(ids)
        assert rebuild.run_methodology_rebuild(connection, profile_id=profile_id) == 0


def test_switch_blocks_on_rebuild_only_and_reports_invalid_target(database):
    _, _, profile_id, user_id = _client(database)
    with database.begin() as connection:
        connection.execute(history_operations.insert().values(
            id=str(uuid4()), profile_id=profile_id, kind="ENTITLEMENT_REBUILD", state="PENDING",
            target_scope="PRO", target_revision=1, dependency_scope={}, created_at=func.now(),
            dedup_key=f"rebuild-only:{profile_id}"))
    assert switch_preflight(database, user_id=user_id)["cause"] == "HISTORICAL_WORK_RUNNING"
    with pytest.raises(AccountLifecycleError, match="INVALID_TARGET"):
        switch_steam_profile(database, user_id=user_id, verified_target_account_id=0)


def test_deleted_account_releases_steam_identity_for_a_new_link(database):
    from app.tracker.authentication import VerifiedIdentity, create_user_session

    _, _, _, user_id = _client(database)
    request_account_deletion(database, user_id=user_id)
    new_user, _ = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", "relinker", None))
    with database.begin() as connection:
        connection.execute(profiles.insert().values(id="relinked", user_id=new_user, account_id=1001, active=True,
                                                    original_linked_at=datetime.now(UTC)))
        assert connection.scalar(select(func.count()).select_from(profiles).where(
            profiles.c.account_id == 1001, profiles.c.active.is_(True))) == 1


def test_scope_expiry_reverts_pb_as_a_scope_change_not_a_loss(database):
    from app.tracker.entitlement import (
        FakeAppStoreVerifier,
        apply_notification,
        reconcile_entitlement_scope,
        submit_transaction,
    )
    from app.tracker.rebuild import complete_scope_rebuild_job

    from .test_entitlement import NOW, ready_bootstrap, transaction
    from .test_schema import identity

    user_id, profile_id = identity(database)
    ready_bootstrap(database, profile_id)
    build_history(database, profile_id, [0, 1, 2, 3, 4, 20], origin="HISTORICAL",
                  offset_days=[-10, -9, -8, -7, -6, -5])
    build_history(database, profile_id, [0, 1, 2, 3, 4, 5], start=20)
    verifier = FakeAppStoreVerifier({
        "transaction:pro": transaction(user_id, token="pro"),
        "notification:refund": transaction(user_id, token="refund", signed=NOW + timedelta(days=1),
                                           revoked=NOW + timedelta(days=1))})
    submit_transaction(database, user_id=user_id, signed_transaction="pro", verifier=verifier, now=NOW)
    reconcile_entitlement_scope(database, user_id=user_id, now=NOW)

    def run_scope():
        with database.begin() as connection:
            connection.execute(update(ingest_jobs).where(ingest_jobs.c.job_type == "SCOPE_REBUILD",
                                                         ingest_jobs.c.state == "PENDING")
                               .values(run_after=func.clock_timestamp() - timedelta(days=1)))
            job = claim(connection, priority=3)
        assert complete_scope_rebuild_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "COMPLETE"

    from app.tracker.schema import personal_bests

    run_scope()
    with database.connect() as connection:
        pro_best = connection.scalar(select(personal_bests.c.comparison_value).where(
            personal_bests.c.revision == 1, personal_bests.c.metric_id == "support.camps_stacked.v1"))
    apply_notification(database, signed_notification="refund", verifier=verifier, now=NOW + timedelta(days=1))
    run_scope()
    with database.connect() as connection:
        free_best = connection.scalar(select(personal_bests.c.comparison_value).where(
            personal_bests.c.revision == 2, personal_bests.c.metric_id == "support.camps_stacked.v1"))
        scope_events = connection.execute(select(events.c.payload).where(
            events.c.kind == "SCOPE_CHANGED").order_by(events.c.created_at)).scalars().all()
        negative = connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind.notin_(("SCOPE_CHANGED", "NEW_PB", "MATCH_READY"))))
    assert pro_best == 24.0 and free_best < pro_best
    assert [event["scope"] for event in scope_events] == ["PRO", "FREE"]
    assert negative == 0  # no downgrade or loss event exists; the change is a scope change


def test_other_bucket_and_turbo_pb_are_isolated_from_unresolved_standard_work(database):
    _, _, profile_id, _ = _client(database)
    pending = add_match(database, profile_id, index=1)
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == pending).values(
            evidence_state="REPLAY_PENDING"))
    assert finalize(database, profile_id, pending) == "WAITING_FOR_PROVIDER"
    turbo_ids = [add_match(database, profile_id, index=10 + i, turbo=True, stack_bonus=i) for i in range(7)]
    for match_id in turbo_ids:
        assert finalize(database, profile_id, match_id) == "READY"
    with database.connect() as connection:
        from app.tracker.schema import personal_bests

        modes = set(connection.scalars(select(personal_bests.c.mode)))
    assert modes == {"TURBO"}


def test_pre_finalization_refinement_creates_no_events_or_assertions(database):
    from app.tracker.linking import complete_role_job
    from app.tracker.schema import role_assertions

    from .test_role_refinement import prepare_refinement

    _, jobs = prepare_refinement(database)
    for job in jobs:
        assert complete_role_job(database, job_id=job["id"], lease_token=job["lease_token"]) == "COMPLETE"
    with database.connect() as connection:
        # A classifier rerun is not a correction: no assertion, event or analysis.
        assert connection.scalar(select(func.count()).select_from(events)) == 0
        assert connection.scalar(select(func.count()).select_from(role_assertions)) == 0
        assert connection.scalar(select(func.count()).select_from(account_matches).where(
            account_matches.c.active_analysis_id.is_not(None))) == 0


def test_history_filters_never_change_canonical_values(database):
    client, headers, profile_id, _ = _client(database)
    build_history(database, profile_id, [0, 1])
    all_rows = client.get("/history", headers=headers).json()["matches"]
    filtered = client.get("/history?mode=STANDARD&role=SUPPORT", headers=headers).json()["matches"]
    assert {row["ref"]: row for row in filtered} == {row["ref"]: row for row in all_rows}
    for row in filtered:
        assert client.get(f"/matches/{row['ref']}", headers=headers).json() == \
            client.get(f"/matches/{row['ref']}", headers=headers).json()
    empty = client.get("/history?mode=TURBO", headers=headers).json()
    assert empty == {"matches": [], "next_cursor": None}
    with database.connect() as connection:
        # Account emptiness is reported by /bootstrap; an empty filter result is only a filter result.
        assert connection.scalar(select(bootstrap.c.outcome).where(bootstrap.c.mode == "STANDARD")) == "NO_MATCHES_FOUND"


def test_logout_and_new_session_leave_bootstrap_work_intact(database):
    from app.tracker.authentication import (
        VerifiedIdentity,
        create_user_session,
        revoke_access_session,
    )
    from app.tracker.bootstrap import request_bootstrap_search

    client, headers, profile_id, _ = _client(database)
    with database.begin() as connection:
        connection.execute(update(bootstrap).values(completed_at=None, outcome=None, search_finished=False))
        job_id = request_bootstrap_search(connection, profile_id)
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == job_id).values(cursor={"offset": 200, "pages": 1}))
    revoke_access_session(database, headers["Authorization"].split()[1])
    assert client.get("/bootstrap", headers=headers).status_code == 401
    _, tokens = create_user_session(database, VerifiedIdentity("google", "https://accounts.google.com",
                                                               "rules-owner", None))
    again = client.get("/bootstrap", headers={"Authorization": f"Bearer {tokens.access_token}"}).json()
    assert {mode["status"] for mode in again["modes"]} == {"SEARCHING"}
    with database.connect() as connection:
        job = connection.execute(select(ingest_jobs).where(ingest_jobs.c.id == job_id)).mappings().one()
    assert job["state"] == "PENDING" and job["cursor"] == {"offset": 200, "pages": 1}


async def test_bootstrap_under_pro_scope_is_identical_work_to_free(database, redis_client):
    import httpx
    from app.tracker import bootstrap as search

    from .test_schema import NOW, identity

    def stamp(days):
        return int((NOW + timedelta(days=days)).timestamp())
    page = [{"match_id": 11, "start_time": stamp(-1), "game_mode": 22},
            {"match_id": 12, "start_time": stamp(-2), "game_mode": 23}]
    produced = []
    for account_id, scope in ((1001, "FREE"), (2002, "PRO")):
        _, profile_id = identity(database, account_id)
        with database.begin() as connection:
            connection.execute(update(profiles).where(profiles.c.id == profile_id).values(active_scope=scope))
            job_id = search.request_bootstrap_search(connection, profile_id)
            connection.execute(update(ingest_jobs).where(ingest_jobs.c.state == "PENDING").values(
                run_after=func.clock_timestamp() + timedelta(days=1)))
            connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == job_id).values(
                run_after=func.clock_timestamp()))
            job = claim(connection, priority=3)
        def handler(request):
            return httpx.Response(200, json=page if request.url.params["offset"] == "0" else [])
        for _ in range(3):
            outcome = await search.search_bootstrap_page(
                database, gate_for(redis_client, "opendota"), Settings(), job_id=job_id,
                lease_token=job["lease_token"], transport=httpx.MockTransport(handler))
            if outcome == "COMPLETE":
                break
            with database.begin() as connection:
                connection.execute(update(ingest_jobs).where(ingest_jobs.c.id == job_id).values(
                    run_after=func.clock_timestamp() - timedelta(days=2)))
                job = claim(connection, priority=3)
        with database.connect() as connection:
            produced.append(sorted((row.job_type, row.priority, json.dumps(row.payload, sort_keys=True))
                                   for row in connection.execute(select(ingest_jobs).where(
                                       ingest_jobs.c.profile_id == profile_id,
                                       ingest_jobs.c.job_type == "HISTORICAL_BATCH"))))
    assert produced[0] == produced[1] and produced[0]


def test_role_correction_recomputes_context_terms_for_the_new_role(database, monkeypatch):
    from app.tracker import finalization as final
    from app.tracker.role_correction import correct_role
    from app.tracker.schema import metric_observations, parameter_sets

    parameters = ParameterSet(
        version="test-only-context-v2", validated=True, opponent_coverage=0.99, cs_slope_regression_passed=True,
        hero_levels={(123, 3, "offlane.net_worth_at_10.v1"): HeroLevel(2000.0, 500)}, opponent_effects={},
        role_slopes={"CARRY": 1.0, "MID": 1.0, "OFFLANE": 1.0}, lane_thresholds={"OFFLANE": (-2.0, 2.0)},
        metrics={"offlane.net_worth_at_10.v1": MetricParameters(500.0, 0.35, 0.0, 0.0)})
    with database.begin() as connection:
        connection.execute(parameter_sets.insert().values(
            version=parameters.version, kind="CONTEXT_POPULATION", digest="1" * 64, status="TEST_ONLY",
            parameters={"test_only": True}, provenance={"fixture": "test-only"}, created_at=func.now()))
    monkeypatch.setattr(final, "current_context_parameters", lambda connection: parameters)
    _, _, profile_id, _ = _client(database)
    [match_id] = build_history(database, profile_id, [0])
    with database.begin() as connection:
        correct_role(connection, profile_id=profile_id, match_id=match_id, role="OFFLANE", expected_role_revision=0)
        rows = {row.metric_id: row for row in connection.execute(select(metric_observations).join(
            account_matches, account_matches.c.active_analysis_id == metric_observations.c.analysis_id).where(
            account_matches.c.match_id == match_id))}
    assert set(rows) == {"offlane.fight_presence.v1", "offlane.lane_net_worth_advantage_at_10.v1",
                         "offlane.net_worth_at_10.v1", "offlane.objective_involvement.v1"}
    assert rows["offlane.net_worth_at_10.v1"].parameter_set_version == parameters.version
    assert rows["offlane.net_worth_at_10.v1"].context_h == 2000.0
    # Metrics the retained source cannot support stay reasoned N/A under the new role.
    assert any(row.raw_value is None and row.unavailable_reason for row in rows.values())


def test_switch_keeps_pro_on_the_account_and_backfills_only_the_new_profile(database, monkeypatch):
    from app.tracker.entitlement import FakeAppStoreVerifier, submit_transaction

    from .test_entitlement import NOW, transaction

    monkeypatch.setenv("TRACKER_PRO_HISTORY_DAYS", "365")
    _, _, old_profile, user_id = _client(database)
    build_history(database, old_profile, [0, 1])
    verifier = FakeAppStoreVerifier({"transaction:pro": transaction(user_id, token="pro")})
    submit_transaction(database, user_id=user_id, signed_transaction="pro", verifier=verifier, now=NOW)
    with database.begin() as connection:
        connection.execute(update(ingest_jobs).where(ingest_jobs.c.profile_id == old_profile).values(state="COMPLETE"))
        connection.execute(update(history_operations).values(state="CANCELLED"))
    switch_steam_profile(database, user_id=user_id, verified_target_account_id=4004)
    with database.begin() as connection:
        new_profile = connection.scalar(select(profiles.c.id).where(profiles.c.active.is_(True)))
        connection.execute(update(bootstrap).where(bootstrap.c.profile_id == new_profile).values(
            search_finished=True, outcome="NO_MATCHES_FOUND", completed_at=func.now()))
        from app.tracker.entitlement import reconcile_bootstrap_entitlement

        operation = reconcile_bootstrap_entitlement(connection, profile_id=new_profile, now=NOW)
        backfills = connection.execute(select(ingest_jobs.c.profile_id).where(
            ingest_jobs.c.job_type == "PRO_BACKFILL", ingest_jobs.c.state == "PENDING")).scalars().all()
        old_links = connection.scalar(select(func.count()).select_from(account_matches).where(
            account_matches.c.profile_id == old_profile))
    assert operation and backfills == [new_profile]
    assert old_links == 2  # archived Pro-era history stays with its own profile


def test_match_detail_cards_render_in_engine_order_with_no_reordering(database, monkeypatch):
    """match_detail#11.16: cards render in engine order; no client reordering, merging or padding."""
    engine_cards = [
        {"candidate_id": "ZULU_CARD", "tier": "A", "family": "Zulu Family", "band": 2, "level": 2.1,
         "rank_class": 2, "slots": {"value": 1}, "enrichments": [], "copy": "zulu copy"},
        {"candidate_id": "ALPHA_CARD", "tier": "B", "family": "Alpha Family", "band": 1, "level": 1.2,
         "rank_class": 1, "slots": {"value": 2}, "enrichments": [], "copy": "alpha copy"},
        {"candidate_id": "MIKE_CARD", "tier": "A", "family": "Mike Family", "band": 3, "level": 3.0,
         "rank_class": 3, "slots": {"value": 3}, "enrichments": [], "copy": "mike copy"},
    ]
    monkeypatch.setattr(finalization, "evaluate_insights", lambda *args, **kwargs: {
        "status": "EVALUATED", "contract_version": finalization.INSIGHT_CONTRACT_VERSION, "cards": engine_cards,
    })
    client, headers, profile_id, _ = _client(database)
    build_history(database, profile_id, [0])
    ref = client.get("/history", headers=headers).json()["matches"][0]["ref"]
    detail = client.get(f"/matches/{ref}", headers=headers).json()
    assert [card["template_id"] for card in detail["insights"]["cards"]] == \
        [card["candidate_id"] for card in engine_cards]
    assert len(detail["insights"]["cards"]) == len(engine_cards)
