from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from report_card.player_analysis_v7.research.pass2_tables import (
    FIGHT_KILL_THRESHOLD,
    PASS2_SPLIT,
    PASS2_TRAJECTORY_FIELDS,
    actions_per_minute_requires_hidden_skill_proxy_review,
    deaths_alone_share,
    fight_minutes,
    first_ward_time,
    is_pass2_product_context,
    iter_pass2_players,
    lane_vs_jungle_gold,
    level_up_times,
    own_networth_curve,
    own_team_tower_kills,
    team_lead_curve,
    trajectory,
    ward_events,
)


def row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "match_id": 1,
        "duration_seconds": 1_380,
        "game_mode_native": "ALL_PICK_RANKED",
        "lobby_type_native": "RANKED",
        "radiant_kills": [0, 0, 0, 0],
        "dire_kills": [0, 0, 0, 0],
        "radiant_networth_leads": [0, 100, 200, 300],
        "tower_deaths": [],
        "self": {
            "is_radiant": True,
            "leaver_status_native": "NONE",
            "trajectories": {},
            "quarantined_trajectories": {},
            "events": {},
            "farm_distribution": None,
        },
    }
    for key, value in overrides.items():
        if key == "self":
            base["self"] = {**base["self"], **value}
        else:
            base[key] = value
    return base


# --------------------------------------------------------------------------
# trajectory() clipping
# --------------------------------------------------------------------------


def test_trajectory_clips_an_over_long_array() -> None:
    candidate = row(
        duration_seconds=1_350,  # expected_trajectory_length == 24
        self={"trajectories": {"gold_per_minute": list(range(40))}},
    )
    assert trajectory(candidate, "gold_per_minute") == list(range(24))


def test_trajectory_leaves_a_short_array_untouched() -> None:
    candidate = row(
        duration_seconds=1_350,
        self={"trajectories": {"gold_per_minute": [1, 2, 3]}},
    )
    assert trajectory(candidate, "gold_per_minute") == [1, 2, 3]


def test_trajectory_returns_none_when_absent() -> None:
    candidate = row(self={"trajectories": {}})
    assert trajectory(candidate, "gold_per_minute") is None


def test_trajectory_returns_none_without_duration() -> None:
    candidate = row(
        duration_seconds=None,
        self={"trajectories": {"gold_per_minute": [1, 2, 3]}},
    )
    assert trajectory(candidate, "gold_per_minute") is None


def test_trajectory_rejects_level_and_quarantined_fields() -> None:
    candidate = row()
    with pytest.raises(ValueError):
        trajectory(candidate, "level")
    with pytest.raises(ValueError):
        trajectory(candidate, "actions_per_minute")


def test_level_up_times_is_not_clipped_to_a_minute_grid() -> None:
    candidate = row(
        duration_seconds=180,
        self={"trajectories": {"level": [-89, 49, 107, 168, 244, 336, 424, 569]}},
    )
    assert level_up_times(candidate) == [-89, 49, 107, 168, 244, 336, 424, 569]


def test_own_networth_curve_reads_the_networth_field() -> None:
    candidate = row(self={"trajectories": {"networth_per_minute": [0, 500, 1000]}})
    assert own_networth_curve(candidate) == [0, 500, 1000]


# --------------------------------------------------------------------------
# team_lead_curve: Dire sign flip
# --------------------------------------------------------------------------


def test_team_lead_curve_is_flipped_for_a_dire_player() -> None:
    lead = [0, 500, -250, 100]
    radiant = row(duration_seconds=180, radiant_networth_leads=lead, self={"is_radiant": True})
    dire = row(duration_seconds=180, radiant_networth_leads=lead, self={"is_radiant": False})
    assert team_lead_curve(radiant) == [0, 500, -250, 100]
    assert team_lead_curve(dire) == [0, -500, 250, -100]


def test_team_lead_curve_fails_closed_without_a_known_side() -> None:
    candidate = row(duration_seconds=180, radiant_networth_leads=[0, 1], self={"is_radiant": None})
    assert team_lead_curve(candidate) is None


def test_team_lead_curve_is_unavailable_for_nullable_grid_evidence() -> None:
    assert team_lead_curve(
        row(duration_seconds=None, radiant_networth_leads=[0, 1, 2])
    ) is None
    assert team_lead_curve(
        row(duration_seconds=180, radiant_networth_leads=[0, None, 2])
    ) is None


# --------------------------------------------------------------------------
# fight_minutes
# --------------------------------------------------------------------------


def test_fight_minute_threshold_is_two_kills_by_either_side() -> None:
    assert FIGHT_KILL_THRESHOLD == 2
    candidate = row(
        duration_seconds=180,
        radiant_networth_leads=[0, 0, 0, 0],
        radiant_kills=[0, 2, 0, 1],
        dire_kills=[0, 0, 3, 1],
    )
    assert fight_minutes(candidate) == frozenset({1, 2})


def test_fight_minutes_is_unavailable_without_kill_arrays() -> None:
    candidate = row(radiant_kills=None, dire_kills=None)
    assert fight_minutes(candidate) is None


def test_fight_minutes_does_not_pad_short_or_nullable_kill_arrays_with_zero() -> None:
    candidate = row(
        duration_seconds=180,
        radiant_networth_leads=[0, 0, 0, 0],
        radiant_kills=[0, None, 2],
        dire_kills=[0, 0, 0],
    )
    assert fight_minutes(candidate) == frozenset({2})


# --------------------------------------------------------------------------
# deaths_alone_share
# --------------------------------------------------------------------------


def _row_with_deaths(death_times: list[int]) -> dict[str, Any]:
    return row(
        duration_seconds=240,  # expected_trajectory_length == 5
        radiant_networth_leads=[0, 0, 0, 0, 0],
        radiant_kills=[0, 2, 0, 0, 0],  # fight at minute 1
        dire_kills=[0, 0, 0, 0, 0],
        self={"events": {"death_events": [{"time": t} for t in death_times]}},
    )


def test_deaths_alone_share_is_none_with_zero_deaths() -> None:
    assert deaths_alone_share(_row_with_deaths([])) is None


def test_deaths_alone_share_is_one_when_all_deaths_are_alone() -> None:
    # minute 3 and minute 4 have no fight activity
    assert deaths_alone_share(_row_with_deaths([180, 200])) == 1.0


def test_deaths_alone_share_is_zero_when_all_deaths_are_in_fights() -> None:
    # both deaths land in minute 1 (60-119s), which has a 2-kill fight
    assert deaths_alone_share(_row_with_deaths([65, 90])) == 0.0


def test_deaths_alone_share_mixed() -> None:
    # one death in the fight minute, one alone
    assert deaths_alone_share(_row_with_deaths([65, 200])) == pytest.approx(0.5)


def test_deaths_alone_share_is_unavailable_on_missing_time() -> None:
    candidate = row(
        duration_seconds=240,
        radiant_networth_leads=[0, 0, 0, 0, 0],
        radiant_kills=[0, 0, 0, 0, 0],
        dire_kills=[0, 0, 0, 0, 0],
        self={"events": {"death_events": [{"time": None}]}},
    )
    assert deaths_alone_share(candidate) is None


def test_deaths_alone_share_is_unavailable_without_kill_arrays() -> None:
    candidate = _row_with_deaths([180])
    candidate["radiant_kills"] = None
    candidate["dire_kills"] = None
    assert deaths_alone_share(candidate) is None


# --------------------------------------------------------------------------
# own_team_tower_kills
# --------------------------------------------------------------------------


def test_own_team_tower_kills_counts_the_enemy_owned_towers() -> None:
    candidate = row(
        self={"is_radiant": True},
        tower_deaths=[
            {"is_radiant": False},  # dire tower died -> radiant kill
            {"is_radiant": False},  # dire tower died -> radiant kill
            {"is_radiant": True},  # radiant's own tower died -> not our kill
        ],
    )
    assert own_team_tower_kills(candidate) == 2


def test_own_team_tower_kills_for_a_dire_player() -> None:
    candidate = row(
        self={"is_radiant": False},
        tower_deaths=[
            {"is_radiant": True},  # radiant tower died -> dire kill
            {"is_radiant": False},  # dire's own tower died -> not our kill
        ],
    )
    assert own_team_tower_kills(candidate) == 1


def test_own_team_tower_kills_is_none_when_not_recorded() -> None:
    candidate = row(self={"is_radiant": True}, tower_deaths=None)
    assert own_team_tower_kills(candidate) is None


def test_own_team_tower_kills_fails_closed_without_own_side() -> None:
    candidate = row(self={"is_radiant": None}, tower_deaths=[{"is_radiant": True}])
    with pytest.raises(ValueError):
        own_team_tower_kills(candidate)


# --------------------------------------------------------------------------
# lane_vs_jungle_gold
# --------------------------------------------------------------------------


def test_lane_vs_jungle_gold_splits_farm_buckets() -> None:
    candidate = row(
        self={
            "farm_distribution": {
                "creep_location": [{"id": 0, "gold": 1000}, {"id": 1, "gold": 500}],
                "neutral_location": [{"id": 7, "gold": 300}],
            }
        }
    )
    assert lane_vs_jungle_gold(candidate) == (1500, 300)


def test_lane_vs_jungle_gold_is_none_when_farm_not_recorded() -> None:
    candidate = row(self={"farm_distribution": None})
    assert lane_vs_jungle_gold(candidate) is None


def test_lane_vs_jungle_gold_is_none_when_one_component_is_unavailable() -> None:
    candidate = row(
        self={
            "farm_distribution": {
                "creep_location": None,
                "neutral_location": [{"gold": 100}],
            }
        }
    )
    assert lane_vs_jungle_gold(candidate) is None


# --------------------------------------------------------------------------
# wards
# --------------------------------------------------------------------------


def test_first_ward_time_picks_the_earliest() -> None:
    candidate = row(
        self={"events": {"wards": [{"time": 400}, {"time": 120}, {"time": 900}]}}
    )
    assert ward_events(candidate) == [{"time": 400}, {"time": 120}, {"time": 900}]
    assert first_ward_time(candidate) == 120


def test_first_ward_time_is_none_with_no_wards() -> None:
    candidate = row(self={"events": {"wards": []}})
    assert first_ward_time(candidate) is None


def test_ward_events_distinguishes_omitted_legacy_empty_from_explicit_null() -> None:
    assert ward_events(row(self={"events": {}})) == []
    assert ward_events(row(self={"events": {"wards": None}})) is None


# --------------------------------------------------------------------------
# is_pass2_product_context
# --------------------------------------------------------------------------


def test_product_context_reads_leaver_status_from_self() -> None:
    finished = row(self={"leaver_status_native": "NONE"})
    left = row(self={"leaver_status_native": "ABANDONED"})
    assert is_pass2_product_context(finished) is True
    assert is_pass2_product_context(left) is False


def test_product_context_excludes_non_matchmaking_lobbies() -> None:
    candidate = row(lobby_type_native="PRACTICE")
    assert is_pass2_product_context(candidate) is False


# --------------------------------------------------------------------------
# quarantine guard
# --------------------------------------------------------------------------


def test_actions_per_minute_is_not_in_the_ordinary_field_list() -> None:
    assert "actions_per_minute" not in PASS2_TRAJECTORY_FIELDS


def test_actions_per_minute_only_reachable_through_the_named_accessor() -> None:
    candidate = row(self={"quarantined_trajectories": {"actions_per_minute": [10, 20, 30]}})
    assert actions_per_minute_requires_hidden_skill_proxy_review(candidate) == [10, 20, 30]


# --------------------------------------------------------------------------
# fail-closed behaviour on malformed rows
# --------------------------------------------------------------------------


def test_missing_self_block_fails_closed() -> None:
    candidate = {"match_id": 1, "duration_seconds": 100}
    with pytest.raises(ValueError):
        trajectory(candidate, "gold_per_minute")
    with pytest.raises(ValueError):
        own_team_tower_kills(candidate)
    with pytest.raises(ValueError):
        lane_vs_jungle_gold(candidate)


def test_non_mapping_self_block_fails_closed() -> None:
    candidate = row()
    candidate["self"] = ["not", "a", "mapping"]
    with pytest.raises(ValueError):
        trajectory(candidate, "gold_per_minute")


# --------------------------------------------------------------------------
# iter_pass2_players
# --------------------------------------------------------------------------


def test_iter_pass2_players_reads_discovery_documents(tmp_path: Path) -> None:
    document = {
        "schema_version": "pass2/1",
        "account_pseudonym": "acct-1",
        "split": PASS2_SPLIT,
        "source_position": 7,
        "rows": [row(match_id=42)],
    }
    (tmp_path / "v7p_deadbeef.json").write_text(json.dumps(document))
    players = list(iter_pass2_players(tmp_path))
    assert len(players) == 1
    assert players[0]["match_id"] == 42
    assert players[0]["account_pseudonym"] == "acct-1"
    assert players[0]["source_position"] == 7


def test_iter_pass2_players_fails_closed_on_non_discovery_split(tmp_path: Path) -> None:
    document = {
        "schema_version": "pass2/1",
        "account_pseudonym": "acct-1",
        "split": "CANDIDATE_TEST",
        "source_position": 1,
        "rows": [],
    }
    (tmp_path / "v7p_cafebabe.json").write_text(json.dumps(document))
    with pytest.raises(ValueError):
        list(iter_pass2_players(tmp_path))


def test_iter_pass2_players_fails_closed_on_malformed_rows(tmp_path: Path) -> None:
    document = {
        "schema_version": "pass2/1",
        "account_pseudonym": "acct-1",
        "split": PASS2_SPLIT,
        "source_position": 1,
        "rows": ["not-a-row"],
    }
    (tmp_path / "v7p_f00dbabe.json").write_text(json.dumps(document))
    with pytest.raises(ValueError):
        list(iter_pass2_players(tmp_path))
