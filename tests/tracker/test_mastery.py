"""Role Mastery awards use finalized, retained tracker facts only."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.tracker.authentication import VerifiedIdentity, create_user_session
from app.tracker.mastery import (
    RULE_VERSION,
    _facts_from_built,
    add_late_bonus,
    award_retained,
    award_xp,
    level_for_xp,
    mastery_state,
    role_total,
)
from app.tracker.metrics import METRICS, metric_ids
from app.tracker.mobile_api import create_mobile_app
from app.tracker.population_parameters import build_artifact, register_parameter_artifact
from app.tracker.rebuild import run_methodology_rebuild
from app.tracker.role_correction import correct_role
from app.tracker.schema import (
    account_matches,
    acquisitions,
    bootstrap,
    bootstrap_search_items,
    events,
    identities,
    mastery_ledger,
    profiles,
    users,
)
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update

from .builders import add_match, finalize, history
from .test_population_parameters import build_input
from .test_schema import identity

RETIRED = ("carry.cs_10_to_20.v1", "carry.dead_time.v1", "mid.level_6_time.v1", "support.healing.v1")


def approved_fixture(database) -> None:
    # This synthetic artifact exists only in the disposable test schema.
    artifact = build_artifact(build_input())
    with database.begin() as connection:
        register_parameter_artifact(connection, artifact, status="APPROVED")


def test_curve_and_award_arithmetic() -> None:
    assert level_for_xp(0) == (None, 0, None)
    assert level_for_xp(100) == (1, 100, 2000)
    assert level_for_xp(7999)[0] == 4
    assert level_for_xp(8000) == (5, 0, 2000)
    assert level_for_xp(469599)[0] == 98
    assert level_for_xp(469600)[0] == 99
    assert level_for_xp(500000)[0] == 99
    assert award_xp("STANDARD", [], []) == 100
    assert award_xp("TURBO", [], []) == 50
    assert award_xp("STANDARD", ["a", "b", "c"], ["x", "y", "z"]) == 160
    assert award_xp("TURBO", ["a", "b", "c"], ["x", "y", "z"]) == 80
    assert award_xp("STANDARD", ["a"], ["x"]) == 130


def test_live_four_roles_retries_and_correction_preserve_award_xp(database) -> None:
    approved_fixture(database)
    user_id, profile_id = identity(database)
    for index, role in enumerate(("CARRY", "MID", "OFFLANE", "SUPPORT")):
        match_id = add_match(database, profile_id, index=index, role=role,
                             turbo=index % 2 == 1, keep_role=True)
        assert finalize(database, profile_id, match_id) == "READY"
    with database.connect() as connection:
        assert {role: role_total(connection, profile_id, role) for role in
                ("CARRY", "MID", "OFFLANE", "SUPPORT")} == {
                    "CARRY": 100, "MID": 50, "OFFLANE": 100, "SUPPORT": 50,
                }
        assert connection.scalar(select(func.count()).select_from(mastery_ledger)) == 4
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "MASTERY_LEVEL")) == 4
    with database.begin() as connection:
        assert award_retained(connection, profile_id=profile_id) == 0
        correct_role(connection, profile_id=profile_id, match_id=match_id,
                     role="CARRY", expected_role_revision=0)
    with database.connect() as connection:
        assert role_total(connection, profile_id, "SUPPORT") == 0
        assert role_total(connection, profile_id, "CARRY") == 150
        assert connection.scalar(select(func.count()).select_from(mastery_ledger)) == 6
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "MASTERY_LEVEL")) == 4
    with database.begin() as connection:
        connection.execute(delete(users).where(users.c.id == user_id))
    with database.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(mastery_ledger)) == 0


def test_pb_requires_five_prior_matches_and_ties_do_not_award(database) -> None:
    approved_fixture(database)
    _, profile_id = identity(database)
    ids = history(database, profile_id, [0, 0, 0, 0, 0, 5, 5])
    with database.connect() as connection:
        rows = connection.execute(select(mastery_ledger.c.match_id, mastery_ledger.c.source).where(
            mastery_ledger.c.profile_id == profile_id,
        ).order_by(mastery_ledger.c.match_id)).all()
        assert [row.source["pb_metric_ids"] for row in rows[:5]] == [[], [], [], [], []]
        assert "support.camps_stacked.v1" in rows[5].source["pb_metric_ids"]
        assert rows[6].source["pb_metric_ids"] == []
        assert rows[5].match_id == ids[5]
        assert rows[6].match_id == ids[6]
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "MASTERY_LEVEL")) == 1


def test_bootstrap_awards_wait_for_both_modes_and_follow_match_chronology(database) -> None:
    approved_fixture(database)
    _, profile_id = identity(database)
    turbo = add_match(database, profile_id, index=0, origin="BOOTSTRAP", role="SUPPORT",
                      turbo=True, offset_days=-2, keep_role=True)
    standard = add_match(database, profile_id, index=1, origin="BOOTSTRAP", role="SUPPORT",
                         offset_days=-1, keep_role=True)
    with database.begin() as connection:
        for mode, match_id in (("STANDARD", standard), ("TURBO", turbo)):
            snapshot_id = connection.scalar(select(acquisitions.c.snapshot_id).where(
                acquisitions.c.match_id == match_id))
            started_at = connection.scalar(select(account_matches.c.provider_started_at).where(
                account_matches.c.profile_id == profile_id, account_matches.c.match_id == match_id))
            connection.execute(bootstrap.insert().values(
                profile_id=profile_id, mode=mode, search_finished=True,
                discovered_count=1, eligible_count=1, settled_count=1,
            ))
            connection.execute(bootstrap_search_items.insert().values(
                profile_id=profile_id, source_item_id=str(match_id), snapshot_id=snapshot_id,
                match_id=match_id, started_at=started_at, mode=mode, outcome="CANDIDATE",
                reason="ELIGIBLE", selected_at=datetime.now(UTC),
            ))
    assert finalize(database, profile_id, standard) == "READY"
    with database.connect() as connection:
        assert role_total(connection, profile_id, "SUPPORT") == 0
    assert finalize(database, profile_id, turbo) == "READY"
    with database.connect() as connection:
        assert role_total(connection, profile_id, "SUPPORT") == 150
        assert list(connection.scalars(select(mastery_ledger.c.match_id).where(
            mastery_ledger.c.profile_id == profile_id,
        ).order_by(mastery_ledger.c.created_at, mastery_ledger.c.id))) == [turbo, standard]
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "MASTERY_LEVEL")) == 0


def test_late_evidence_adds_only_missing_bonus_without_celebration(database) -> None:
    approved_fixture(database)
    _, profile_id = identity(database)
    match_id = add_match(database, profile_id, index=0, role="SUPPORT", keep_role=True)
    assert finalize(database, profile_id, match_id) == "READY"
    with database.begin() as connection:
        before = role_total(connection, profile_id, "SUPPORT")
        stale = {"parameter_set_version": "2026-09-v1", "pb_rows": [],
                 "metric_rows": [{"metric_id": metric, "performance_state": "ABOVE"}
                                 for metric in [*RETIRED, "carry.last_hits_at_10.v1"]]}
        # Retired and other-role metrics can never add evidence to a Support award.
        assert not add_late_bonus(connection, profile_id=profile_id, match_id=match_id, built=stale)
        built = {"parameter_set_version": "2026-09-v1",
                 "metric_rows": [{"metric_id": "support.vision_denial.v1", "performance_state": "ABOVE"}],
                 "pb_rows": []}
        assert add_late_bonus(connection, profile_id=profile_id, match_id=match_id, built=built)
        assert not add_late_bonus(connection, profile_id=profile_id, match_id=match_id, built=built)
    with database.connect() as connection:
        assert role_total(connection, profile_id, "SUPPORT") == before + 10
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "MASTERY_LEVEL")) == 1


def test_calibration_gate_and_hidden_history_api(database, monkeypatch) -> None:
    user_id, profile_id = identity(database, linked_at=datetime(2026, 9, 21, tzinfo=UTC))
    issuer, subject = "https://accounts.google.com", str(uuid4())
    with database.begin() as connection:
        connection.execute(identities.insert().values(
            id=str(uuid4()), user_id=user_id, issuer=issuer, subject=subject,
            verified_at=datetime.now(UTC),
        ))
    _, tokens = create_user_session(database, VerifiedIdentity("google", issuer, subject, None))
    client = TestClient(create_mobile_app(Settings(), database=database))
    headers = {"Authorization": f"Bearer {tokens.access_token}"}
    assert client.get("/mastery", headers=headers).json()["state"] == "CALIBRATION_PENDING"

    hidden = add_match(database, profile_id, index=10, origin="HISTORICAL", role="SUPPORT",
                       offset_days=-3, keep_role=True)
    assert finalize(database, profile_id, hidden) == "READY"
    with database.connect() as connection:
        assert role_total(connection, profile_id, "SUPPORT") == 0
    approved_fixture(database)
    with database.begin() as connection:
        connection.execute(update(profiles).where(profiles.c.id == profile_id).values(active_scope="PRO"))
    assert client.get("/mastery", headers=headers).json()["state"] == "BACKFILLING"
    assert client.get("/mastery/SUPPORT/awards", headers=headers).status_code == 503
    with database.begin() as connection:
        assert run_methodology_rebuild(connection, profile_id=profile_id) == 1
        assert award_retained(connection, profile_id=profile_id) == 0
        connection.execute(update(profiles).where(profiles.c.id == profile_id).values(active_scope="FREE"))
    free = client.get("/mastery", headers=headers)
    assert free.status_code == 200
    assert free.json()["state"] == "AVAILABLE"
    assert free.json()["roles"][-1]["level"] == 1
    assert free.json()["roles"][-1]["total_xp"] is None
    assert client.get("/mastery/SUPPORT/awards", headers=headers).json()["awards"] == []
    monkeypatch.setattr("app.tracker.mobile_api.role_total",
                        lambda _connection, _profile_id, role: 10_000 if role == "SUPPORT" else 0)
    capped = client.get("/mastery", headers=headers).json()["roles"][-1]
    assert capped["level"] == 5 and capped["saved_progress"]
    assert capped["total_xp"] is None and capped["xp_into_level"] is None
    with database.begin() as connection:
        connection.execute(update(profiles).where(profiles.c.id == profile_id).values(
            active_scope="PRO", active_revision=1))
    pro = client.get("/mastery", headers=headers).json()
    assert pro["roles"][-1]["total_xp"] == 10_000
    assert pro["roles"][-1]["level"] == 6
    awards = client.get("/mastery/SUPPORT/awards?limit=1", headers=headers).json()
    assert len(awards["awards"]) == 1
    assert awards["awards"][0]["reason"] == "METHODOLOGY_REBUILD"
    assert awards["awards"][0]["rule_version"] == "role-mastery-v2"
    assert awards["awards"][0]["match_ref"] != str(hidden)
    assert pro["milestones"] == []
    live = add_match(database, profile_id, index=11, role="SUPPORT", offset_days=1, keep_role=True)
    assert finalize(database, profile_id, live) == "READY"
    first = client.get("/mastery/SUPPORT/awards?limit=1", headers=headers).json()
    assert first["next_cursor"] is not None
    second = client.get("/mastery/SUPPORT/awards", headers=headers,
                        params={"limit": 1, "cursor": first["next_cursor"]}).json()
    assert len(second["awards"]) == 1 and second["next_cursor"] is None
    assert {first["awards"][0]["reason"], second["awards"][0]["reason"]} == {
        "LIVE_FINALIZATION", "METHODOLOGY_REBUILD",
    }
    with database.begin() as connection:
        connection.execute(update(profiles).where(profiles.c.id == profile_id).values(
            active_scope="FREE", active_revision=2))
    free_awards = client.get("/mastery/SUPPORT/awards", headers=headers).json()["awards"]
    assert len(free_awards) == 1 and free_awards[0]["reason"] == "LIVE_FINALIZATION"


def _built(states, pbs=()):
    return {"metric_rows": [{"metric_id": metric, "performance_state": state} for metric, state in states],
            "pb_rows": [{"metric_id": metric, "current": SimpleNamespace(match_id=7),
                         "pb": {"state": "READY", "source_match_id": 7}} for metric in pbs]}


@pytest.mark.parametrize("role", ("CARRY", "MID", "OFFLANE", "SUPPORT"))
def test_each_role_earns_from_exactly_its_four_canonical_metrics(role) -> None:
    canonical = metric_ids(role)
    assert len(canonical) == 4 and set(canonical).isdisjoint(RETIRED)

    def xp(states, pbs=(), mode="STANDARD"):
        return award_xp(mode, *_facts_from_built(_built(states, pbs), role))

    # Every metric above and a new PB: the fixed caps bind, so each role's maximum is identical.
    assert xp([(metric, "ABOVE") for metric in canonical], canonical) == 160
    assert xp([(metric, "ABOVE") for metric in canonical], canonical, "TURBO") == 80
    # Positive and negative deltas mixed: only ABOVE is credited; BELOW never subtracts.
    assert xp([(canonical[0], "ABOVE"), (canonical[1], "BELOW"),
               (canonical[2], "IN_LINE"), (canonical[3], "BELOW")]) == 110
    # No positive delta still earns the full base.
    assert xp([(metric, "BELOW") for metric in canonical]) == 100
    # Baseline building everywhere: no bonus, no penalty.
    assert xp([(metric, "NOT_READY") for metric in canonical]) == 100
    # Two metrics N/A (no state, no PB row); the other two can still reach the ABOVE cap.
    assert xp([(canonical[0], "NOT_READY"), (canonical[1], "NOT_READY"),
               (canonical[2], "ABOVE"), (canonical[3], "ABOVE")], canonical[2:]) == 160
    # Retired and other-role IDs are never credited, even from a pre-migration analysis.
    foreign = [*RETIRED, *(metric for metric in METRICS if metric not in canonical)]
    assert _facts_from_built(_built([(metric, "ABOVE") for metric in foreign], foreign), role) == ([], [])


def test_level_pacing_is_base_driven_and_equal_across_roles() -> None:
    # The curve is calibrated on the 100 XP base: twenty base-only Standard matches per early level.
    assert level_for_xp(20 * award_xp("STANDARD", [], [])) == (2, 0, 2000)
    assert level_for_xp(4 * 20 * 100)[0] == 5
    # Bonus caps (two ABOVE, two PB) are independent of registry size, so the fastest
    # possible pace (160/match) is the same for every role now that each has four metrics.
    assert {len(metric_ids(role)) for role in ("CARRY", "MID", "OFFLANE", "SUPPORT")} == {4}
    assert award_xp("STANDARD", ["a", "b", "c", "d"], ["a", "b", "c", "d"]) == 160


def test_retired_metric_mastery_is_rebuilt_under_one_rule_without_celebrations(database, monkeypatch) -> None:
    from app.tracker import finalization

    approved_fixture(database)
    user_id, profile_id = identity(database)
    first = add_match(database, profile_id, index=0, role="SUPPORT", keep_role=True)
    # Simulate an analysis and ledger written before the four-metric registry:
    # a tracker-analysis-6 analysis and a v1 award crediting retired metrics.
    monkeypatch.setattr(finalization, "ANALYSIS_VERSION", "tracker-analysis-6")
    assert finalize(database, profile_id, first) == "READY"
    monkeypatch.undo()
    with database.begin() as connection:
        link = connection.execute(select(account_matches).where(
            account_matches.c.match_id == first)).mappings().one()
        assert connection.scalar(select(func.count()).select_from(mastery_ledger)) == 0
        connection.execute(mastery_ledger.insert().values(
            id=str(uuid4()), profile_id=profile_id, match_id=first, mode="STANDARD", role="SUPPORT",
            kind="AWARD", xp=160, source_analysis_id=link["active_analysis_id"],
            rule_version="role-mastery-v1", dedup_key=f"mastery:award:{profile_id}:{first}",
            source={"reason": "LIVE_FINALIZATION", "base_standard_xp": 100,
                    "above_metric_ids": ["support.healing.v1", "support.vision_denial.v1"],
                    "pb_metric_ids": ["support.healing.v1", "support.camps_stacked.v1"],
                    "analysis_version": "tracker-analysis-6", "baseline_version": "rolling-median-20-v1",
                    "parameter_set_version": "2026-09-v1"},
            created_at=func.now()))
        profile = connection.execute(select(profiles).where(profiles.c.id == profile_id)).mappings().one()
        assert role_total(connection, profile_id, "SUPPORT") == 0
        assert mastery_state(connection, profile) == "BACKFILLING"
    # A later Standard match waits for the migration instead of snapshotting transitional priors;
    # Turbo is a separate chronology and is not blocked by stale Standard history.
    second = add_match(database, profile_id, index=1, role="SUPPORT", keep_role=True)
    turbo = add_match(database, profile_id, index=2, role="SUPPORT", turbo=True, keep_role=True)
    assert finalize(database, profile_id, second) == "READY"
    assert finalize(database, profile_id, turbo) == "READY"
    with database.connect() as connection:
        assert role_total(connection, profile_id, "SUPPORT") == 50
        levels = connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "MASTERY_LEVEL"))
    with database.begin() as connection:
        assert run_methodology_rebuild(connection, profile_id=profile_id) == 2
        assert run_methodology_rebuild(connection, profile_id=profile_id) == 0
        assert award_retained(connection, profile_id=profile_id) == 0
    with database.connect() as connection:
        profile = connection.execute(select(profiles).where(profiles.c.id == profile_id)).mappings().one()
        assert mastery_state(connection, profile) == "AVAILABLE"
        assert role_total(connection, profile_id, "SUPPORT") == 250
        current = connection.execute(select(mastery_ledger).where(
            mastery_ledger.c.rule_version == RULE_VERSION).order_by(mastery_ledger.c.match_id)).mappings().all()
        assert [(row["match_id"], row["xp"], row["source"]["reason"]) for row in current] == [
            (first, 100, "METHODOLOGY_REBUILD"), (second, 100, "METHODOLOGY_REBUILD"),
            (turbo, 50, "LIVE_FINALIZATION")]
        assert all(row["source"]["analysis_version"] == finalization.ANALYSIS_VERSION for row in current)
        credited = {metric for row in current
                    for metric in row["source"]["above_metric_ids"] + row["source"]["pb_metric_ids"]}
        assert credited <= set(metric_ids("SUPPORT"))
        # The v1 row stays as audit history; no level is re-celebrated by the rebuild.
        assert connection.scalar(select(func.count()).select_from(mastery_ledger).where(
            mastery_ledger.c.rule_version == "role-mastery-v1")) == 1
        assert connection.scalar(select(func.count()).select_from(events).where(
            events.c.kind == "MASTERY_LEVEL")) == levels
    with database.begin() as connection:
        connection.execute(update(profiles).where(profiles.c.id == profile_id).values(active_scope="PRO"))
    issuer, subject = "https://accounts.google.com", str(uuid4())
    with database.begin() as connection:
        connection.execute(identities.insert().values(
            id=str(uuid4()), user_id=user_id, issuer=issuer, subject=subject, verified_at=datetime.now(UTC)))
    _, tokens = create_user_session(database, VerifiedIdentity("google", issuer, subject, None))
    client = TestClient(create_mobile_app(Settings(), database=database))
    headers = {"Authorization": f"Bearer {tokens.access_token}"}
    assert client.get("/mastery", headers=headers).json()["roles"][-1]["total_xp"] == 250
    awards = client.get("/mastery/SUPPORT/awards", headers=headers).json()["awards"]
    assert len(awards) == 3 and {award["rule_version"] for award in awards} == {RULE_VERSION}
    assert not {metric for award in awards for metric in award["above_metric_ids"] + award["pb_metric_ids"]
                } & set(RETIRED)
    # A correction moves only current-rule XP; the v1 audit row stays in Support.
    with database.begin() as connection:
        correct_role(connection, profile_id=profile_id, match_id=first, role="CARRY",
                     expected_role_revision=0)
    with database.connect() as connection:
        assert role_total(connection, profile_id, "CARRY") == 100
        assert role_total(connection, profile_id, "SUPPORT") == 150
