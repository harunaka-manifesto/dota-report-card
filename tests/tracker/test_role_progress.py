"""Role charts from retained, production-translated match evidence; no provider I/O."""
from __future__ import annotations

import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo

import httpx
import pytest
from app.tracker import activity, finalization, mobile_api, rebuild
from app.tracker.entitlement import (
    FakeAppStoreVerifier,
    reconcile_entitlement_scope,
    submit_transaction,
)
from app.tracker.metrics import metric_ids
from app.tracker.mobile_api import ProgressWindow, _progress_start, _progress_unit
from app.tracker.rebuild import run_methodology_rebuild, run_scope_rebuild
from app.tracker.role_correction import correct_role
from app.tracker.schema import (
    account_matches,
    analyses,
    matches,
    metric_observations,
    positions,
    profiles,
    provider_calls,
)
from sqlalchemy import event, func, select, update

from .builders import add_match, finalize
from .test_entitlement import ready_bootstrap, transaction
from .test_mobile_golden import FORBIDDEN, Normalizer
from .test_mobile_inventory import _linked_client

NOW = datetime(2026, 10, 3, 12, tzinfo=UTC)
LINKED = datetime(2024, 1, 1, tzinfo=UTC)
STACKS = "support.camps_stacked.v1"
GOLDEN = Path(__file__).parents[1] / "fixtures/tracker/role-metric-history-v1"


@pytest.fixture(autouse=True)
def fixed_clock(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return NOW.astimezone(tz) if tz is not None else NOW.replace(tzinfo=None)
    monkeypatch.setattr(mobile_api, "datetime", Clock)


def _client(database, subject="role-charts", account_id=1001):
    client, headers, profile_id = _linked_client(database, subject, account_id)
    with database.begin() as connection:
        connection.execute(update(profiles).where(profiles.c.id == profile_id).values(original_linked_at=LINKED))
    ready_bootstrap(database, profile_id)
    return client, headers, profile_id


def _match(database, profile_id, index, *, at=NOW - timedelta(hours=1), role="SUPPORT", turbo=False,
           origin="LIVE", bonus=0, edit=None, account_id=1001, ready=True):
    with database.connect() as connection:
        linked = connection.scalar(select(profiles.c.original_linked_at).where(profiles.c.id == profile_id))
    match_id = add_match(database, profile_id, index=index, role=role, turbo=turbo, origin=origin,
        stack_bonus=bonus, offset_days=(at - linked).total_seconds() / 86400,
        account_id=account_id, keep_role=True, edit=edit)
    if ready:
        assert finalize(database, profile_id, match_id) == "READY"
    return match_id


def _get(client, headers, role="SUPPORT", **params):
    return client.get(f"/progress/roles/{role}", headers=headers,
        params={"mode": "STANDARD", "window": "ALL_TIME", "time_zone": "UTC", **params})


def _metric(body, ident=STACKS):
    return next(metric for metric in body["metrics"] if metric["metric_id"] == ident)


def _golden(name, body):
    observed = Normalizer()(body)
    assert not FORBIDDEN.search(json.dumps(observed))
    path = GOLDEN / f"{name}.json"
    if not path.exists() and os.getenv("TRACKER_WRITE_MISSING_GOLDEN") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(observed, indent=2, sort_keys=True) + "\n")
    assert json.loads(path.read_text()) == observed


def test_trailing_windows_and_dst_bounds():
    today = date(2026, 10, 3)
    assert [_progress_start(today, window) for window in ProgressWindow] == [
        date(2026, 9, 27), date(2026, 9, 4), date(2025, 10, 4), None]
    start, end = activity.utc_bounds(date(2026, 3, 8), date(2026, 3, 8), ZoneInfo("America/New_York"))
    assert end - start == timedelta(hours=23)
    assert {_progress_unit(ident) for role in ("CARRY", "MID", "OFFLANE", "SUPPORT")
            for ident in metric_ids(role)} == {"GOLD", "COUNT", "FRACTION", "COUNT_PER_10_MINUTES"}


@pytest.mark.parametrize("role", ["CARRY", "MID", "OFFLANE", "SUPPORT"])
def test_four_metrics_modes_and_provider_free_read(database, monkeypatch, role):
    client, headers, profile_id = _client(database)
    _match(database, profile_id, 0, role=role)
    _match(database, profile_id, 1, role=role, turbo=True, at=NOW - timedelta(minutes=30))
    _match(database, profile_id, 2, role=role, at=NOW, ready=False)
    with database.connect() as connection:
        calls = connection.scalar(select(func.count()).select_from(provider_calls))

    def forbidden(*args, **kwargs):
        raise AssertionError("A chart read must not reach a provider")
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden)
    # TestClient uses an in-process transport; external HTTP transports are blocked.
    for mode in ("STANDARD", "TURBO"):
        response = _get(client, headers, role, mode=mode)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["state"] == "AVAILABLE" and body["selected_window_match_count"] == 1
        assert [metric["metric_id"] for metric in body["metrics"]] == list(metric_ids(role))
        assert all(len(metric["points"]) == 1 for metric in body["metrics"])
        assert all(metric["points"][0]["match_ref"] == body["metrics"][0]["points"][0]["match_ref"]
                   for metric in body["metrics"])
        assert all(metric["measured_count"] + metric["unavailable_count"] == 1 for metric in body["metrics"])
        _golden(f"{role.lower()}-{mode.lower()}", body)
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(provider_calls)) == calls
    old = client.get("/progress", headers=headers, params={"mode": "STANDARD", "role": role,
                     "metric_id": metric_ids(role)[0]}).json()
    assert set(old) == {"mode", "role", "metric_id", "points", "personal_best", "trend"}


def test_empty_states_validation_and_isolation(database):
    client, headers, profile_id = _client(database)
    unstarted = _get(client, headers).json()
    assert unstarted["state"] == "UNSTARTED" and unstarted["start_date"] is None
    _golden("unstarted", unstarted)
    assert _get(client, {}).status_code == 401
    for params in ({"time_zone": "posixrules"}, {"time_zone": "Mars"}):
        assert _get(client, headers, **params).json()["code"] == "TIME_ZONE_INVALID"
    for params in ({"limit": 0}, {"limit": 501}, {"window": "MONTH"}, {"mode": "ALL"}):
        assert _get(client, headers, **params).status_code == 422
    assert _get(client, headers, "UNKNOWN").status_code == 422
    _match(database, profile_id, 0, at=NOW - timedelta(days=50))
    empty = _get(client, headers, window="LAST_7_DAYS").json()
    assert empty["state"] == "AVAILABLE" and empty["selected_window_match_count"] == 0
    assert all(not metric["points"] and metric["latest"] is None for metric in empty["metrics"])
    _golden("empty-window", empty)
    other, other_headers, other_profile = _client(database, "other", account_id=2002)
    assert _get(other, other_headers).json()["state"] == "UNSTARTED"
    with database.begin() as connection:
        connection.execute(update(profiles).where(profiles.c.id == other_profile).values(active=False))
    unlinked = _get(other, other_headers).json()
    assert unlinked["state"] == "STEAM_LINK_REQUIRED"
    _golden("unlinked", unlinked)
    with database.begin() as connection:
        connection.execute(update(profiles).where(profiles.c.id == profile_id).values(active=False))
    assert _get(client, headers).json()["state"] == "STEAM_LINK_REQUIRED"


def test_local_boundaries_are_inclusive_and_calendar_gap_is_not_zero(database):
    client, headers, profile_id = _client(database)
    zone = ZoneInfo("Asia/Tokyo")
    today = NOW.astimezone(zone).date()
    for index, window in enumerate(list(ProgressWindow)[:3]):
        start = _progress_start(today, window)
        lower, _ = activity.utc_bounds(start, today, zone)
        _match(database, profile_id, index * 2, at=lower - timedelta(seconds=1))
        _match(database, profile_id, index * 2 + 1, at=lower)
    # All six were finalized in ingestion order; the read orders by actual match time.
    for window, expected in zip(list(ProgressWindow)[:3], (1, 3, 5), strict=True):
        body = _get(client, headers, window=window.value, time_zone=zone.key).json()
        assert body["selected_window_match_count"] == expected
        assert len(_metric(body)["points"]) == expected
        assert body["start_date"] == _progress_start(today, window).isoformat()


def test_zero_na_rates_and_latest_are_independent_of_page(database):
    client, headers, profile_id = _client(database)
    def no_stacks(payload):
        payload["players"][0]["camps_stacked_t"] = [0] * len(payload["players"][0]["camps_stacked_t"])
    _match(database, profile_id, 0, at=NOW - timedelta(hours=3), edit=no_stacks)
    _match(database, profile_id, 1, at=NOW - timedelta(hours=2), bonus=5)
    def missing_stacks(payload):
        payload["players"][0].pop("camps_stacked_t", None)
    _match(database, profile_id, 2, at=NOW - timedelta(hours=1), edit=missing_stacks)
    first = _get(client, headers, limit=1).json()
    metric = _metric(first)
    assert metric["measured_count"] == 2 and metric["unavailable_count"] == 1
    assert metric["points"][0]["state"] == "NOT_AVAILABLE"
    assert metric["points"][0]["comparison_value"] is None and metric["points"][0]["unavailable_reason"]
    assert metric["latest"]["comparison_value"] == 9
    second = _get(client, headers, limit=1, cursor=first["next_cursor"]).json()
    third = _get(client, headers, limit=1, cursor=second["next_cursor"]).json()
    assert _metric(third)["points"][0]["comparison_value"] == 0
    assert _metric(third)["points"][0]["state"] == "MEASURED"
    assert _metric(third)["latest"] == metric["latest"]
    assert third["next_cursor"] is None
    wards = _metric(first, "support.observer_wards_placed.v1")
    assert wards["unit"] == "COUNT_PER_10_MINUTES"
    assert wards["latest"]["raw_value"] != wards["latest"]["comparison_value"]
    _golden("na-and-latest", first)


def test_negative_gold_advantage_and_fraction_units(database):
    client, headers, profile_id = _client(database)
    def losing_lane(payload):
        payload["players"][0]["gold_t"] = [0] * len(payload["players"][0]["gold_t"])
    match_id = _match(database, profile_id, 0, role="OFFLANE", edit=losing_lane, ready=False)
    with database.begin() as connection:
        assignment = connection.execute(select(positions.c.evidence_profile, positions.c.version,
            positions.c.inputs_digest).where(positions.c.match_id == match_id,
                                            positions.c.evidence_profile == "REPLAY")).mappings().first()
        assert assignment is not None
        connection.execute(update(account_matches).where(account_matches.c.match_id == match_id).values(
            role_assignment=dict(assignment)))
    assert finalize(database, profile_id, match_id) == "READY"
    body = _get(client, headers, "OFFLANE").json()
    lane = _metric(body, "offlane.lane_net_worth_advantage_at_10.v1")
    assert lane["unit"] == "GOLD" and lane["latest"]["comparison_value"] < 0
    share = _metric(body, "offlane.fight_presence.v1")
    assert share["unit"] == "FRACTION" and 0 <= share["latest"]["comparison_value"] <= 1


def test_paging_ties_cursor_binding_and_conditional_get(database):
    client, headers, profile_id = _client(database)
    for index in range(5):
        _match(database, profile_id, index, bonus=index)
    first = _get(client, headers, limit=2)
    body = first.json()
    assert body["selected_window_match_count"] == 5
    tag = first.headers["ETag"]
    assert _get(client, {**headers, "If-None-Match": tag}, limit=2).status_code == 304
    seen = [point["match_ref"] for point in _metric(body)["points"]]
    cursor = body["next_cursor"]
    for role, params in (("CARRY", {}), ("SUPPORT", {"mode": "TURBO"}),
                         ("SUPPORT", {"time_zone": "Asia/Tokyo"}),
                         ("SUPPORT", {"window": "LAST_7_DAYS"})):
        assert _get(client, headers, role, cursor=cursor, **params).json()["code"] == "CURSOR_INVALID"
    assert _get(client, headers, cursor=cursor + "x").json()["code"] == "CURSOR_INVALID"
    assert _get(client, headers, cursor="é.forged").json()["code"] == "CURSOR_INVALID"
    other, other_headers, _ = _client(database, "other", account_id=2002)
    assert _get(other, other_headers, cursor=cursor).json()["code"] == "CURSOR_INVALID"
    while body["next_cursor"]:
        body = _get(client, headers, limit=2, cursor=body["next_cursor"]).json()
        assert body["selected_window_match_count"] == 5
        seen = [point["match_ref"] for point in _metric(body)["points"]] + seen
    assert len(seen) == len(set(seen)) == 5
    with database.connect() as connection:
        expected = list(connection.scalars(select(account_matches.c.public_ref).where(
            account_matches.c.profile_id == profile_id).order_by(account_matches.c.provider_started_at,
                                                               account_matches.c.match_id)))
    assert seen == expected
    # A late recovered older match invalidates the pagination snapshot.
    _match(database, profile_id, 10, at=NOW - timedelta(days=3), origin="RECOVERY")
    assert _get(client, headers, cursor=cursor).json()["code"] == "CURSOR_INVALID"
    assert _get(client, {**headers, "If-None-Match": tag}, limit=2).status_code == 200


def test_calendar_filters_preserve_canonical_context_and_pb(database):
    client, headers, profile_id = _client(database)
    for index in range(16):
        _match(database, profile_id, index, at=NOW - timedelta(days=40 - index * 2), bonus=50 - index)
    bodies = [_get(client, headers, window=window.value).json() for window in ProgressWindow]
    contexts = [{metric["metric_id"]: (metric["baseline"], metric["trend"], metric["personal_best"])
                 for metric in body["metrics"]} for body in bodies]
    assert all(context == contexts[0] for context in contexts)
    stacked = _metric(bodies[0])
    assert stacked["baseline"]["state"] == "READY"
    assert stacked["trend"] == {"state": None, "reason": "CALIBRATION_UNAVAILABLE", "point_count": 10}
    assert stacked["personal_best"] is not None and stacked["latest"] is None
    _golden("canonical-context-empty-window", bodies[0])


def test_scope_rebuilds_change_visibility_without_deleting_history(database):
    client, headers, profile_id = _client(database)
    with database.begin() as connection:
        connection.execute(update(profiles).where(profiles.c.id == profile_id).values(
            original_linked_at=NOW - timedelta(days=7)))
    _match(database, profile_id, 0, at=NOW - timedelta(days=8), origin="BOOTSTRAP")
    _match(database, profile_id, 1, at=NOW - timedelta(days=4))
    _match(database, profile_id, 2, at=NOW - timedelta(days=20), origin="HISTORICAL")
    free = _get(client, headers, limit=1).json()
    assert free["scope"] == "FREE" and free["selected_window_match_count"] == 2
    with database.connect() as connection:
        owner = connection.scalar(select(profiles.c.user_id).where(profiles.c.id == profile_id))
    tx = transaction(owner, expires=NOW + timedelta(days=1))
    outcome = submit_transaction(database, user_id=owner, signed_transaction="active",
        verifier=FakeAppStoreVerifier({"transaction:active": tx}), now=NOW)
    assert _get(client, headers).json()["selected_window_match_count"] == 2
    with database.begin() as connection:
        assert run_scope_rebuild(connection, profile_id=profile_id,
            operation_id=outcome["operation_id"], now=NOW) == "COMPLETE"
    pro = _get(client, headers, limit=1).json()
    assert pro["scope"] == "PRO" and pro["selected_window_match_count"] == 3
    assert _get(client, headers, cursor=free["next_cursor"]).json()["code"] == "CURSOR_INVALID"
    expiry = reconcile_entitlement_scope(database, user_id=owner, now=NOW + timedelta(days=2))
    with database.begin() as connection:
        assert run_scope_rebuild(connection, profile_id=profile_id,
            operation_id=expiry["operation_id"], now=NOW + timedelta(days=2)) == "COMPLETE"
    restored = _get(client, headers).json()
    assert restored["scope"] == "FREE" and restored["selected_window_match_count"] == 2
    assert _get(client, headers, cursor=pro["next_cursor"]).json()["code"] == "CURSOR_INVALID"
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(account_matches)) == 3


def test_role_correction_rebuild_and_metric_version_gates(database, monkeypatch):
    client, headers, profile_id = _client(database)
    first = _match(database, profile_id, 0, at=NOW - timedelta(hours=2))
    _match(database, profile_id, 1, at=NOW - timedelta(hours=1))
    cursor = _get(client, headers, limit=1).json()["next_cursor"]
    with database.begin() as connection:
        correct_role(connection, profile_id=profile_id, match_id=first, role="OFFLANE", expected_role_revision=0)
    assert _get(client, headers).json()["selected_window_match_count"] == 1
    assert _get(client, headers, "OFFLANE").json()["selected_window_match_count"] == 1
    assert _get(client, headers, cursor=cursor).json()["code"] == "CURSOR_INVALID"
    for module in (mobile_api, finalization, rebuild):
        monkeypatch.setattr(module, "ANALYSIS_VERSION", "tracker-chart-test-bump")
    rebuilding = _get(client, headers, "OFFLANE").json()
    assert rebuilding["state"] == "REBUILDING" and rebuilding["selected_window_match_count"] is None
    assert all(not metric["points"] and metric["latest"] is None for metric in rebuilding["metrics"])
    _golden("rebuilding", rebuilding)
    with database.begin() as connection:
        assert run_methodology_rebuild(connection, profile_id=profile_id) > 0
    assert _get(client, headers, "OFFLANE").json()["state"] == "AVAILABLE"
    with database.begin() as connection:
        active = connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == first))
        # Analyses/observations are immutable. Build a separate historical-version
        # fixture instead of mutating persisted evidence.
        previous = dict(connection.execute(select(analyses).where(analyses.c.id == active)).mappings().one())
        previous.update(id=str(uuid4()), inputs_digest=uuid4().hex)
        connection.execute(analyses.insert().values(**previous))
        for row in connection.execute(select(metric_observations).where(
                metric_observations.c.analysis_id == active)).mappings():
            observation = {**dict(row), "analysis_id": previous["id"], "metric_version": "v0"}
            connection.execute(metric_observations.insert().values(**observation))
        connection.execute(update(account_matches).where(account_matches.c.match_id == first).values(
            active_analysis_id=previous["id"]))
    assert _get(client, headers, "OFFLANE").json()["state"] == "REBUILDING"


def test_read_is_one_repeatable_snapshot_across_scope_switch(database):
    client, headers, profile_id = _client(database)
    _match(database, profile_id, 0)
    _match(database, profile_id, 1, at=LINKED - timedelta(days=1), origin="HISTORICAL")
    switched = False

    def switch_after_profile(connection, cursor, statement, parameters, context, executemany):
        nonlocal switched
        if not switched and statement.startswith("SELECT tracker_profiles."):
            switched = True
            with database.begin() as writer:
                writer.execute(update(profiles).where(profiles.c.id == profile_id).values(
                    active_scope="PRO", active_revision=1))
    event.listen(database, "after_cursor_execute", switch_after_profile)
    try:
        body = _get(client, headers).json()
    finally:
        event.remove(database, "after_cursor_execute", switch_after_profile)
    assert switched and body["scope"] == "FREE" and body["selected_window_match_count"] == 1
    fresh = _get(client, headers).json()
    assert fresh["scope"] == "PRO" and fresh["selected_window_match_count"] == 2


def test_summary_only_matches_keep_summary_metrics_and_exclude_ineligible_matches(database):
    client, headers, profile_id = _client(database)
    match_id = _match(database, profile_id, 0, role="CARRY", ready=False,
                      edit=lambda payload: payload.__setitem__("version", None))
    with database.begin() as connection:
        connection.execute(update(matches).where(matches.c.match_id == match_id).values(
            evidence_state="REPLAY_UNAVAILABLE", terminal_reason="REPLAY_CHECKS_EXHAUSTED",
            replay_terminal_at=NOW))
    assert finalize(database, profile_id, match_id) == "READY"
    _match(database, profile_id, 1, role="CARRY",
           edit=lambda payload: payload["players"][0].__setitem__("leaver_status", 1))
    body = _get(client, headers, "CARRY").json()
    assert body["selected_window_match_count"] == 1
    for ident in ("carry.last_hits_at_10.v1", "carry.net_worth_at_20.v1"):
        metric = _metric(body, ident)
        assert metric["unavailable_count"] == 1 and metric["latest"] is None
        assert metric["points"][0]["comparison_value"] is None
    for ident in ("carry.hero_damage_share.v1", "carry.tower_damage_share.v1"):
        assert _metric(body, ident)["measured_count"] == 1


def test_local_midnight_invalidates_resolved_window_cursor(database, monkeypatch):
    client, headers, profile_id = _client(database)
    _match(database, profile_id, 0, at=NOW - timedelta(hours=2))
    _match(database, profile_id, 1, at=NOW - timedelta(hours=1))
    cursor = _get(client, headers, limit=1, window="LAST_7_DAYS").json()["next_cursor"]
    class Tomorrow(datetime):
        @classmethod
        def now(cls, tz=None):
            return (NOW + timedelta(days=1)).astimezone(tz)
    monkeypatch.setattr(mobile_api, "datetime", Tomorrow)
    assert _get(client, headers, cursor=cursor, window="LAST_7_DAYS").json()["code"] == "CURSOR_INVALID"
