"""SSOT acceptance rules that the traceability audit found untested or partial."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.core.config import Settings
from app.tracker.account_lifecycle import (
    AccountLifecycleError,
    switch_preflight,
    switch_steam_profile,
)
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.backfill import backfill_page, request_pro_backfill
from app.tracker.jobs import claim
from app.tracker.mobile_api import create_mobile_app
from app.tracker.profile import _tier, publish_profile_checkpoint
from app.tracker.role_correction import correct_role
from app.tracker.schema import (
    account_matches,
    dota_accounts,
    events,
    ingest_jobs,
    personal_bests,
    profile_states,
    profiles,
    provider_calls,
)
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select, update

from .builders import add_match, finalize, history
from .test_entitlement import ready_bootstrap
from .test_provider_transport import gate_for

ROW_FIELDS = {"ref", "mode", "started_at", "duration_seconds", "hero_id", "won", "role", "lifecycle",
              "progression", "progression_reason", "has_insight_cards", "owns_personal_best"}


def _client(database, subject="rules-owner", *, account_id=1001, linked=None):
    user_id, tokens = create_user_session(database, VerifiedIdentity(
        "google", "https://accounts.google.com", subject, None))
    profile_id = f"rules-{subject}"
    with database.begin() as connection:
        connection.execute(insert(dota_accounts).values(account_id=account_id))
        connection.execute(profiles.insert().values(
            id=profile_id, user_id=user_id, account_id=account_id, active=True,
            original_linked_at=linked or datetime(2026, 9, 1, tzinfo=UTC)))
    ready_bootstrap(database, profile_id)
    return (TestClient(create_mobile_app(Settings(), database=database)),
            {"Authorization": f"Bearer {tokens.access_token}"}, profile_id, user_id)


def _unsupported(payload):
    payload["game_mode"] = 2  # captains draft: retained but not a progression bucket


def test_history_rows_are_identity_only_and_every_retained_match_is_listed(database):
    client, headers, profile_id, _ = _client(database)
    history(database, profile_id, [0, 1])
    unsupported = add_match(database, profile_id, index=5, edit=_unsupported)
    assert finalize(database, profile_id, unsupported) == "READY"
    pending = add_match(database, profile_id, index=6)
    with database.begin() as connection:
        connection.execute(update(account_matches).where(account_matches.c.match_id == pending)
                           .values(lifecycle="WAITING_FOR_PROVIDER"))
    # Admitted later but played earlier: it takes its true chronological slot.
    late = add_match(database, profile_id, index=40, origin="BOOTSTRAP", offset_days=0.5)
    assert finalize(database, profile_id, late) == "READY"

    rows = client.get("/history", headers=headers).json()["matches"]
    assert all(set(row) == ROW_FIELDS for row in rows)
    assert [row["started_at"] for row in rows] == sorted((row["started_at"] for row in rows), reverse=True)
    by_life = {row["lifecycle"] for row in rows}
    assert by_life == {"READY", "WAITING_FOR_DATA"}
    assert any(row["mode"] is None and row["progression"] == "NONE" and row["progression_reason"] for row in rows)
    assert len(rows) == 5
    standard = client.get("/history?mode=STANDARD", headers=headers).json()["matches"]
    assert len(standard) == 4 and all(row["mode"] == "STANDARD" for row in standard)
    # A still-processing match stays listed under a role filter.
    support = client.get("/history?mode=STANDARD&role=SUPPORT", headers=headers).json()["matches"]
    assert any(row["lifecycle"] == "WAITING_FOR_DATA" for row in support)
    # Every row, including unsupported and processing ones, opens Match Detail.
    for row in rows:
        assert client.get(f"/matches/{row['ref']}", headers=headers).status_code == 200
    paged = client.get("/history?limit=2", headers=headers).json()
    after = client.get("/history", params={"limit": 2, "cursor": paged["next_cursor"]}, headers=headers).json()
    assert [row["ref"] for row in paged["matches"] + after["matches"]] == [row["ref"] for row in rows[:4]]


def test_home_last_five_spans_buckets_today_and_four_metric_named_role_summaries(database):
    now = datetime.now(UTC)
    # Anchor on UTC midnight so the day buckets hold at any time of day.
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    client, headers, profile_id, _ = _client(database, linked=midnight - timedelta(days=3))
    history(database, profile_id, [0], offset_days=[1])
    turbo = add_match(database, profile_id, index=2, turbo=True, offset_days=2)
    assert finalize(database, profile_id, turbo) == "READY"
    unsupported = add_match(database, profile_id, index=3, edit=_unsupported, offset_days=2.5)
    assert finalize(database, profile_id, unsupported) == "READY"
    today = add_match(database, profile_id, index=4, offset_days=3 + (now - midnight) / timedelta(days=2))
    with database.begin() as connection:
        connection.execute(update(account_matches).where(account_matches.c.match_id == today)
                           .values(lifecycle="WAITING_FOR_PROVIDER"))
    home = client.get("/home?mode=STANDARD&time_zone=UTC", headers=headers).json()
    assert [entry["mode"] for entry in home["last_matches"]] == ["STANDARD", None, "TURBO", "STANDARD"]
    assert home["last_matches"][1]["progression"] == "NONE" and home["last_matches"][1]["progression_reason"]
    assert home["last_matches"][0]["lifecycle"] == "WAITING_FOR_DATA"
    assert [entry["lifecycle"] for entry in home["today_matches"]] == ["WAITING_FOR_DATA"]
    summaries = {summary["role"]: summary for summary in home["role_summaries"]}
    assert set(summaries) == {"CARRY", "MID", "OFFLANE", "SUPPORT"}
    assert summaries["CARRY"]["state"] == "UNSTARTED" and summaries["CARRY"]["last_played_at"] is None
    assert summaries["SUPPORT"]["state"] == "ACTIVE"
    assert {metric["state"] for metric in summaries["SUPPORT"]["metrics"]} == {"INSUFFICIENT_HISTORY"}
    for summary in summaries.values():
        assert set(summary) == {"role", "state", "last_played_at", "metrics"}  # no composite verdict
    for entry in home["last_matches"]:
        assert not {"metrics", "insights", "performance", "lane_context"} & set(entry)
    unauthenticated = client.get("/home?mode=STANDARD&time_zone=UTC")
    assert unauthenticated.status_code == 401
    # The acknowledged entry keeps its place and updates in place once analysis persists.
    ref = home["today_matches"][0]["ref"]
    with database.begin() as connection:
        connection.execute(update(account_matches).where(account_matches.c.match_id == today)
                           .values(lifecycle="ANALYZING"))
    assert finalize(database, profile_id, today) == "READY"
    again = client.get("/home?mode=STANDARD&time_zone=UTC", headers=headers).json()
    assert [(entry["ref"], entry["lifecycle"]) for entry in again["today_matches"]] == [(ref, "READY")]
    assert again["last_matches"][0]["ref"] == ref


def test_pb_ownership_is_distinct_from_celebration_and_progress_pb_has_context(database):
    client, headers, profile_id, _ = _client(database)
    ids = history(database, profile_id, [0, 1, 2, 3, 4, 6, 9])
    metric = "support.camps_stacked.v1"
    rows = {row["ref"]: row for row in client.get("/history?mode=STANDARD", headers=headers).json()["matches"]}
    details = {ref: client.get(f"/matches/{ref}", headers=headers).json() for ref in rows}
    celebrated = [ref for ref, detail in details.items() if metric in detail["celebrated_personal_best"]]
    owners = [ref for ref, detail in details.items() if metric in detail["owns_personal_best"]]
    assert len(celebrated) == 2 and len(owners) == 1
    earlier = next(ref for ref in celebrated if ref not in owners)
    assert metric not in details[earlier]["owns_personal_best"]  # celebrated once, no longer owns
    assert rows[owners[0]]["owns_personal_best"] is True and rows[earlier]["owns_personal_best"] is False
    progress = client.get("/progress", params={"mode": "STANDARD", "role": "SUPPORT", "metric_id": metric},
                          headers=headers).json()
    # Progress carries observations, baselines, trend and PB only: no matchup or adjustment.
    assert set(progress) == {"mode", "role", "metric_id", "points", "personal_best", "trend"}
    assert all(set(point) == {"match_ref", "started_at", "value", "baseline_value", "prior_count"}
               for point in progress["points"])
    best = progress["personal_best"]
    assert best["match_ref"] == owners[0] and best["value"] == 13.0
    assert best["hero_id"] == 123 and best["achieved_at"]
    assert ids


def test_raw_higher_but_lower_comparison_value_is_not_a_personal_best(database):
    _, _, profile_id, _ = _client(database)
    history(database, profile_id, [0, 0, 0, 0, 0, 0])

    def longer_but_more_healing(payload):
        payload["players"][0]["hero_healing"] = 600   # raw above every prior 490
        payload["duration"] = 5000                    # per-10-minute rate below them
    later = add_match(database, profile_id, index=20, edit=longer_but_more_healing)
    assert finalize(database, profile_id, later) == "READY"
    with database.connect() as connection:
        owner = connection.execute(select(personal_bests.c.comparison_value, personal_bests.c.analysis_id).where(
            personal_bests.c.metric_id == "support.healing.v1")).one()
        later_analysis = connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == later))
        assert owner.analysis_id != later_analysis
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "NEW_PB", events.c.payload["metric_id"].astext == "support.healing.v1")) == 0


def test_import_that_beats_the_record_updates_pb_silently_without_celebration(database):
    _, _, profile_id, _ = _client(database)
    history(database, profile_id, [0, 1, 2, 3, 4, 5])
    imported = add_match(database, profile_id, index=30, origin="BOOTSTRAP", stack_bonus=50, offset_days=10)
    assert finalize(database, profile_id, imported) == "READY"
    with database.connect() as connection:
        owner = connection.scalar(select(personal_bests.c.analysis_id).where(
            personal_bests.c.metric_id == "support.camps_stacked.v1"))
        assert owner == connection.scalar(select(account_matches.c.active_analysis_id).where(
            account_matches.c.match_id == imported))
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind.in_(("NEW_PB", "MATCH_READY")),
            events.c.payload["match_id"].astext == str(imported))) == 0


def test_role_tiers_hold_within_three_points_and_fallback_lines():
    assert _tier(0.18, False, "REGULAR") == "REGULAR"      # inside the ±3 pp band
    assert _tier(0.16, False, "REGULAR") == "OCCASIONAL"   # left the band
    assert _tier(0.49, True, "ANCHOR") == "ANCHOR"
    assert _tier(0.46, True, "ANCHOR") == "REGULAR"
    assert _tier(0.04, False, None) == "RARE"
    assert _tier(0.55, False, "ANCHOR") == "REGULAR"       # only the top role can be Anchor


def test_profile_withholds_role_shape_with_unassigned_matches_and_uses_mixed_fallback(database):
    _, _, profile_id, _ = _client(database)
    for index, role in enumerate(["CARRY", "MID", "OFFLANE", "SUPPORT"] * 3):
        match_id = add_match(database, profile_id, index=index, role=role, keep_role=True)
        assert finalize(database, profile_id, match_id) == "READY"
    for index in range(20, 24):
        match_id = add_match(database, profile_id, index=index, role=None, keep_role=True)
        assert finalize(database, profile_id, match_id) == "UNAVAILABLE"
    with database.begin() as connection:
        publish_profile_checkpoint(connection, profile_id=profile_id, cause="PLAY")
        state = connection.scalar(select(profile_states.c.state).where(profile_states.c.mode == "STANDARD"))
    assert state["identity"] == {"template_id": "BIT_OF_EVERYTHING", "slots": {}, "confirmed": False}
    assert state["unassigned_count"] == 4 and state["role_shape_withheld"] == "UNASSIGNED_ROLES"
    assert [row["count"] for row in state["role_map"]] == [3, 3, 3, 3]


def test_role_correction_republishes_profile_at_its_checkpoint(database):
    client, headers, profile_id, _ = _client(database)
    ids = history(database, profile_id, list(range(10)))
    before = client.get("/profile?mode=STANDARD", headers=headers).json()
    assert [row["count"] for row in before["role_map"]] == [0, 0, 0, 10]
    with database.begin() as connection:
        correct_role(connection, profile_id=profile_id, match_id=ids[2], role="MID", expected_role_revision=0)
        cause = connection.scalar(select(profile_states.c.cause).where(profile_states.c.mode == "STANDARD"))
    assert cause == "ROLE_CORRECTION"
    after = client.get("/profile?mode=STANDARD", headers=headers).json()
    assert [row["count"] for row in after["role_map"]] == [0, 1, 0, 9]
    # No confirmed identity exists yet, so no change receipt is fabricated.
    assert after["changes"] == []


async def test_blocked_access_defers_historical_work_and_keeps_pro(database, redis_client):
    _, _, profile_id, _ = _client(database)
    with database.begin() as connection:
        connection.execute(update(profiles).values(active_scope="PRO", active_revision=1))
        job_id = request_pro_backfill(connection, profile_id, ceiling_days=365)
        connection.execute(update(dota_accounts).values(visibility="BLOCKED"))
        job = claim(connection, priority=3)
    assert job["id"] == job_id
    outcome = await backfill_page(database, gate_for(redis_client, "opendota"), Settings(), job_id=job_id,
                                  lease_token=job["lease_token"])
    assert outcome == "BLOCKED"
    with database.connect() as connection:
        row = connection.execute(select(ingest_jobs).where(ingest_jobs.c.id == job_id)).mappings().one()
        assert row["state"] == "PENDING" and row["last_error"] == "DATA_ACCESS_BLOCKED" and row["attempts"] == 0
        assert connection.execute(select(profiles.c.active_scope, profiles.c.active)).one() == ("PRO", True)
        assert connection.scalar(select(func.count()).select_from(provider_calls)) == 0


def test_failed_switch_never_starts_the_cooldown_and_success_isolates_old_state(database):
    client, headers, profile_id, user_id = _client(database)
    other_client, other_headers, _, _ = _client(database, "rules-other", account_id=3003)
    history(database, profile_id, [0, 1])
    with pytest.raises(AccountLifecycleError, match="TARGET_OWNED_BY_ANOTHER_ACCOUNT"):
        switch_steam_profile(database, user_id=user_id, verified_target_account_id=3003)
    assert switch_preflight(database, user_id=user_id)["available"] is True
    switch_steam_profile(database, user_id=user_id, verified_target_account_id=4004)
    assert switch_preflight(database, user_id=user_id)["cause"] == "SWITCH_COOLDOWN"
    assert client.get("/history", headers=headers).json()["matches"] == []
    assert client.get("/profile?mode=STANDARD", headers=headers).json()["state"] == "NOT_READY"
    progress = client.get("/progress", params={"mode": "STANDARD", "role": "SUPPORT",
                                               "metric_id": "support.camps_stacked.v1"}, headers=headers).json()
    assert progress["points"] == [] and progress["personal_best"] is None
    assert client.get("/account", headers=headers).json()["scope"] == "FREE"
    assert other_client.get("/history", headers=other_headers).status_code == 200


def test_match_detail_terminal_zero_card_and_ineligible_states(database):
    from scripts.tracker_seed_demo import seed_demo

    persona = seed_demo(database)["match_states"]
    client = TestClient(create_mobile_app(Settings(), database=database))
    headers = {"Authorization": f"Bearer {persona['access_token']}"}
    details = [client.get(f"/matches/{row['ref']}", headers=headers).json()
               for row in client.get("/history", headers=headers).json()["matches"]]
    by_life = {}
    for detail in details:
        by_life.setdefault(detail["lifecycle"], []).append(detail)
    for failed in by_life["UNAVAILABLE"] + by_life["ACTION_REQUIRED"]:
        # No endless pending section: failures state a terminal outcome.
        assert failed["performance"] == "UNAVAILABLE" and failed["insights"]["state"] == "UNAVAILABLE"
    for waiting in by_life["WAITING_FOR_DATA"] + by_life["WAITING_FOR_PRIOR_MATCH"]:
        assert waiting["facts"] == "AVAILABLE" and waiting["performance"] == "PENDING"
    ready = by_life["READY"]
    no_replay = next(d for d in ready if d["progression"] == "STANDARD")
    assert no_replay["insights"] == {"state": "AVAILABLE", "contract_version": no_replay["insights"]["contract_version"],
                                     "reason": None, "cards": []}
    ineligible = next(d for d in ready if d["progression"] == "NONE")
    assert ineligible["progression_reason"] == "SHORT_OR_INVALID_DURATION"
    assert ineligible["metrics"] and all(
        metric["baseline_state"] == "NOT_AVAILABLE" and metric["baseline_value"] is None
        and metric["performance_state"] is None for metric in ineligible["metrics"])
