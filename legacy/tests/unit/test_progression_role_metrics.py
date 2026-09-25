from __future__ import annotations

from copy import deepcopy
from typing import Any

import pytest
from app.stratz.deep import normalize_deep_matches
from app.stratz.queries import GET_ROLE_METRIC_MATCH_BATCH
from report_card.progression.role_metrics import (
    EARLY_FIGHT_CUTOFF_SECONDS,
    OBJECTIVE_PROXIMITY_WINDOW_SECONDS,
    ROLE_METRIC_SPECS,
    SUPPORT_CONTROL,
    SUPPORT_HEALING,
    compare_progression,
    is_progression_eligible,
    measure_metric,
    mid_early_fight_presence,
    offlane_objective_involvement,
    previous_role_matches,
    support_camps_stacked,
    support_fight_presence,
    support_healing,
)


def _row(
    *,
    match_id: int = 1,
    started_at: int = 1_700_000_000,
    position: str = "POSITION_4",
    side: bool = True,
    mode: str = "ALL_PICK_RANKED",
    lobby: str = "RANKED",
    hero_healing: int | None = 0,
    duration: Any = 1_800,
    player_slot: int | None = 0,
    all_players: list[dict[str, Any]] | None = None,
    camp_stack: Any = (0, 0, 2),
    own_kills: list[dict[str, Any]] | None = None,
    own_assists: list[dict[str, Any]] | None = None,
    tower_deaths: list[dict[str, Any]] | None = None,
    tower_damage_report: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if all_players is None:
        all_players = [
            {
                "player_slot": slot,
                "is_radiant": slot < 5,
                "kills": 1 if slot == 1 else 0,
                "assists": 0,
                "stats": {"kill_events": [{"time": 100}]},
            }
            for slot in range(10)
        ]
    return {
        "match_id": match_id,
        "started_at": started_at,
        "duration_seconds": duration,
        "game_mode_native": mode,
        "lobby_type_native": lobby,
        "tower_deaths": tower_deaths if tower_deaths is not None else [],
        "all_players": all_players,
        "self": {
            "player_slot": player_slot,
            "is_radiant": side,
            "position_native": position,
            "role_native": "LIGHT_SUPPORT" if position in {"POSITION_4", "POSITION_5"} else "CORE",
            "lane_native": "SAFE_LANE",
            "leaver_status_native": "NONE",
            "hero_healing": hero_healing,
            "kills": 0,
            "assists": 0,
            "trajectories": {"camp_stack": camp_stack},
            "events": {
                "kill_events": own_kills if own_kills is not None else [],
                "assist_events": own_assists if own_assists is not None else [],
            },
            "tower_damage_report": tower_damage_report if tower_damage_report is not None else [],
        },
    }


def _team_rows(*, player_slot: int = 0, player_side: bool = True, kills: tuple[int, ...] = (0, 1, 1, 0, 0), assists: int = 0) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for slot in range(10):
        side = slot < 5
        index = slot if side else slot - 5
        rows.append(
            {
                "player_slot": slot,
                "is_radiant": side,
                "kills": kills[index] if side == player_side else 0,
                "assists": assists if slot == player_slot else 0,
            }
        )
    return rows


def test_healing_uses_hero_healing_and_duration_without_turning_zero_into_na() -> None:
    row = _row(hero_healing=5_420, duration=1_800)
    result = support_healing(row)
    assert result.metric_key == SUPPORT_HEALING
    assert result.raw_value == 5_420
    assert result.normalized_value == pytest.approx(1_806.6666667)
    assert result.status == "measured"

    zero = support_healing(_row(hero_healing=0, duration=900))
    assert zero.status == "measured"
    assert zero.raw_value == 0
    assert zero.normalized_value == 0


@pytest.mark.parametrize("duration", [None, 0, -1, 1_800.0, "1800"])
def test_healing_rejects_missing_or_malformed_duration(duration: Any) -> None:
    result = support_healing(_row(hero_healing=10, duration=duration))
    assert result.status == "unavailable"
    assert result.reason == "missing_or_malformed_duration_seconds"


def test_healing_missing_value_and_role_isolation_are_explicit() -> None:
    missing = support_healing(_row(hero_healing=None))
    assert missing.status == "unavailable"
    assert missing.reason == "missing_or_malformed_hero_healing"
    wrong_role = support_healing(_row(position="POSITION_1", hero_healing=500))
    assert wrong_role.status == "unavailable"
    assert wrong_role.reason == "role_mismatch"


def test_fight_presence_uses_the_player_side_scoreboard_not_radiant_dire_arrays() -> None:
    all_players = _team_rows(kills=(1, 1, 1, 0, 0), assists=1)
    row = _row(all_players=all_players)
    row["radiant_kills"] = [999]
    row["dire_kills"] = [999]
    result = support_fight_presence(row)
    assert result.status == "measured"
    assert result.numerator == 2
    assert result.denominator == 3
    assert result.normalized_value == pytest.approx(2 / 3)

    dire = _row(
        side=False,
        player_slot=5,
        all_players=_team_rows(player_slot=5, player_side=False, kills=(2, 1, 1, 0, 0), assists=1),
    )
    assert support_fight_presence(dire).normalized_value == pytest.approx(3 / 4)


def test_fight_presence_handles_zero_and_zero_involvement_as_different_states() -> None:
    zero_team = support_fight_presence(_row(all_players=_team_rows(kills=(0, 0, 0, 0, 0), assists=0)))
    assert zero_team.status == "unavailable"
    assert zero_team.reason == "zero_credited_team_kills"

    no_involvement = support_fight_presence(_row(all_players=_team_rows(kills=(0, 1, 1, 0, 0), assists=0)))
    assert no_involvement.status == "measured"
    assert no_involvement.raw_value == 0

    full = support_fight_presence(_row(all_players=_team_rows(kills=(3, 0, 0, 0, 0), assists=0)))
    assert full.status == "measured"
    assert full.normalized_value == 1


@pytest.mark.parametrize(
    "mutate,reason",
    [
        (lambda row: row.update(all_players=None), "missing_or_malformed_all_players"),
        (lambda row: row["all_players"].__setitem__(1, {**row["all_players"][1], "player_slot": 0}), "duplicate_all_player_slot"),
        (lambda row: row["all_players"].__setitem__(1, {**row["all_players"][1], "kills": "1"}), "malformed_all_players"),
    ],
)
def test_fight_presence_fails_closed_on_incomplete_scoreboard(mutate, reason: str) -> None:
    row = _row(all_players=_team_rows(kills=(1, 1, 1, 0, 0), assists=1))
    mutate(row)
    result = support_fight_presence(row)
    assert result.status == "unavailable"
    assert result.reason == reason


def test_fight_presence_rejects_impossible_over_100_percent() -> None:
    row = _row(all_players=_team_rows(kills=(1, 0, 0, 0, 0), assists=2))
    result = support_fight_presence(row)
    assert result.status == "unavailable"
    assert result.reason == "involvement_exceeds_credited_team_kills"


def test_camps_stacked_is_the_cumulative_final_value_and_zero_is_real() -> None:
    result = support_camps_stacked(_row(camp_stack=[0, 1, 1, 3]))
    assert result.status == "measured"
    assert result.raw_value == 3
    assert result.normalized_value == 3
    assert support_camps_stacked(_row(camp_stack=[0, 0])).raw_value == 0

    missing = support_camps_stacked(_row(camp_stack=None))
    assert missing.status == "unavailable"
    assert support_camps_stacked(_row(camp_stack=[0, 2, 1])).reason == "non_monotonic_camp_stack"
    assert support_camps_stacked(_row(position="POSITION_2")).reason == "role_mismatch"


def test_mid_early_presence_includes_15m_and_excludes_after_it() -> None:
    all_players = _team_rows(kills=(0, 0, 0, 0, 0), assists=0)
    for player in all_players:
        player["stats"] = {"kill_events": []}
    all_players[0]["stats"]["kill_events"] = [{"time": EARLY_FIGHT_CUTOFF_SECONDS}]
    all_players[1]["stats"]["kill_events"] = [{"time": EARLY_FIGHT_CUTOFF_SECONDS + 1}]
    all_players[2]["stats"]["kill_events"] = [{"time": 899}]
    row = _row(
        position="POSITION_2",
        all_players=all_players,
        own_kills=[{"time": EARLY_FIGHT_CUTOFF_SECONDS}],
        own_assists=[{"time": EARLY_FIGHT_CUTOFF_SECONDS + 1}],
    )
    result = mid_early_fight_presence(row)
    assert result.status == "measured"
    assert result.numerator == 1
    assert result.denominator == 2
    assert result.normalized_value == pytest.approx(0.5)


def test_mid_early_presence_is_n_a_for_zero_opportunity_or_missing_team_events() -> None:
    zero = _row(position="POSITION_2")
    for player in zero["all_players"]:
        player["stats"] = {"kill_events": []}
    assert mid_early_fight_presence(zero).reason == "zero_credited_team_kills_through_15m"

    missing = _row(position="POSITION_2")
    missing["all_players"][0].pop("stats")
    assert mid_early_fight_presence(missing).reason == "missing_team_kill_events"
    assert mid_early_fight_presence(_row(position="POSITION_1")).reason == "role_mismatch"


def test_objective_involvement_uses_specific_damage_or_proximity_and_bounds_result() -> None:
    row = _row(
        position="POSITION_3",
        tower_deaths=[
            {"time": 600, "is_radiant": False, "npc_id": 101},
            {"time": 1_200, "is_radiant": False, "npc_id": 102},
            {"time": 1_800, "is_radiant": True, "npc_id": 999},
        ],
        own_kills=[{"time": 540}],
        own_assists=[],
        tower_damage_report=[{"npc_id": 102, "damage": 1}],
    )
    result = offlane_objective_involvement(row)
    assert result.status == "measured"
    assert result.numerator == 2
    assert result.denominator == 2
    assert 0 <= result.normalized_value <= 1

    scalar_only = deepcopy(row)
    scalar_only["self"]["tower_damage"] = 10_000
    scalar_only["self"]["tower_damage_report"] = None
    assert offlane_objective_involvement(scalar_only).reason == "missing_tower_damage_report"


def test_objective_candidate_windows_are_explicit_and_60s_is_the_default() -> None:
    row = _row(
        position="POSITION_3",
        tower_deaths=[
            {"time": 600, "is_radiant": False, "npc_id": 101},
            {"time": 1_200, "is_radiant": False, "npc_id": 102},
            {"time": 1_800, "is_radiant": False, "npc_id": 103},
        ],
        own_kills=[{"time": 555}, {"time": 1_141}, {"time": 1_711}],
        own_assists=[],
        tower_damage_report=[],
    )
    assert offlane_objective_involvement(row, proximity_window_seconds=45).numerator == 1
    assert offlane_objective_involvement(row, proximity_window_seconds=60).numerator == 2
    assert offlane_objective_involvement(row, proximity_window_seconds=90).numerator == 3
    assert OBJECTIVE_PROXIMITY_WINDOW_SECONDS == 60
    assert offlane_objective_involvement(row).numerator == 2


def test_objective_zero_towers_missing_data_and_role_isolation_are_explicit() -> None:
    no_towers = offlane_objective_involvement(_row(position="POSITION_3", tower_deaths=[]))
    assert no_towers.status == "unavailable"
    assert no_towers.reason == "zero_enemy_towers_destroyed"
    missing_report = _row(position="POSITION_3", tower_deaths=[{"time": 100, "is_radiant": False, "npc_id": 1}])
    missing_report["self"]["tower_damage_report"] = None
    assert offlane_objective_involvement(missing_report).reason == "missing_tower_damage_report"
    assert offlane_objective_involvement(_row(position="POSITION_2")).reason == "role_mismatch"


def test_progression_window_is_role_scoped_bounded_and_excludes_current_and_turbo() -> None:
    current = _row(match_id=100, started_at=2_000_000_000, hero_healing=2_000)
    history = [
        _row(match_id=index, started_at=1_999_999_000 + index, hero_healing=1_000 + index)
        for index in range(1, 7)
    ]
    history.extend(
        [
            _row(match_id=200, started_at=1_999_999_500, position="POSITION_1", hero_healing=9_000),
            _row(match_id=201, started_at=1_999_999_499, mode="TURBO", hero_healing=9_000),
            current,
        ]
    )
    previous = previous_role_matches(history, current, role="support")
    assert len(previous) == 6
    assert all(row["match_id"] != 100 for row in previous)
    assert is_progression_eligible(history[-2]) is False
    future_rows = [
        _row(match_id=300 + index, started_at=2_000_000_001 + index) for index in range(3)
    ]
    assert not previous_role_matches(future_rows, current, role="support")

    comparison = compare_progression(SUPPORT_HEALING, current, history)
    assert comparison.status == "measured"
    assert comparison.eligible_for_progression is True
    assert comparison.reference_match_count == 6
    assert comparison.measured_reference_count == 6
    assert comparison.personal_best is True


def test_progression_requires_five_measured_reference_values_and_turbo_never_compares() -> None:
    current = _row(match_id=100, started_at=2_000_000_000, hero_healing=2_000)
    history = [_row(match_id=index, started_at=1_999_999_000 + index, hero_healing=1_000) for index in range(1, 5)]
    insufficient = compare_progression(SUPPORT_HEALING, current, history)
    assert insufficient.status == "insufficient_history"
    assert insufficient.baseline is None
    assert insufficient.measured_reference_count == 4

    turbo = _row(match_id=101, mode="TURBO", hero_healing=2_000)
    result = compare_progression(SUPPORT_HEALING, turbo, history)
    assert result.measurement.status == "measured"
    assert result.status == "ineligible"
    assert result.reason == "ineligible_progression_context"
    assert is_progression_eligible(_row(mode="SINGLE_DRAFT")) is False


def test_unsupported_control_is_registered_without_a_proxy_implementation() -> None:
    spec = ROLE_METRIC_SPECS[SUPPORT_CONTROL]
    assert spec.supported is False
    result = measure_metric(SUPPORT_CONTROL, _row())
    assert result.status == "unsupported"
    assert "duration" in (result.reason or "")
    assert spec.measure is None


def test_role_metric_query_is_minimal_and_normalizes_its_new_fields() -> None:
    document = GET_ROLE_METRIC_MATCH_BATCH.document
    assert GET_ROLE_METRIC_MATCH_BATCH.version == "1.0.0"
    for field in ("heroHealing", "campStack", "killEvents", "towerDamageReport", "npcId"):
        assert field in document
    assert "actionReport" not in document
    assert "playback" not in document.casefold()

    all_players = [
        {
            "playerSlot": slot,
            "isRadiant": slot < 5,
            "kills": 1 if slot == 1 else 0,
            "assists": 0,
            "stats": {"killEvents": [{"time": 100 + slot}]},
        }
        for slot in range(10)
    ]
    payload = {
        "player": {
            "matches": [
                {
                    "id": 9,
                    "durationSeconds": 1_800,
                    "startDateTime": 1_700_000_000,
                    "gameMode": "ALL_PICK_RANKED",
                    "lobbyType": "RANKED",
                    "towerDeaths": [{"time": 600, "isRadiant": False, "npcId": 101}],
                    "allPlayers": all_players,
                    "players": [
                        {
                            "playerSlot": 0,
                            "isRadiant": True,
                            "position": "POSITION_3",
                            "role": "CORE",
                            "lane": "OFFLANE",
                            "leaverStatus": "NONE",
                            "kills": 0,
                            "assists": 1,
                            "heroHealing": 100,
                            "stats": {
                                "campStack": [0, 1],
                                "killEvents": [{"time": 500}],
                                "assistEvents": [{"time": 550}],
                                "towerDamageReport": [{"npcId": 101, "damage": 20}],
                            },
                        }
                    ],
                }
            ]
        }
    }
    row = normalize_deep_matches(payload, requested_ids=[9])[0]
    assert row["all_players"][0]["kill_events"] == [{"time": 100}]
    assert row["self"]["hero_healing"] == 100
    assert row["self"]["trajectories"]["camp_stack"] == [0, 1]
    assert row["self"]["tower_damage_report"] == [{"npc_id": 101, "damage": 20}]
