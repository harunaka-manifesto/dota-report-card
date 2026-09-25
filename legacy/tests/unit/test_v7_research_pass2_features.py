from __future__ import annotations

from typing import Any

import pytest
from report_card.player_analysis_v7.research.pass2_features import (
    DEATH_CLUSTER_WINDOW_SECONDS,
    FEATURE_REGISTRY,
    LEAD_THRESHOLD_GOLD,
    MIN_OBSERVATIONS,
    OBSERVER_WARD_DURATION_SECONDS,
    REPORT_SECTIONS,
    _map_own_lane_to_map_lane,
    closer_vs_comeback,
    death_clustering,
    deaths_alone_share,
    fight_conversion,
    group_rows_by_account,
    lane_to_map,
    lane_vs_jungle_share,
    spike_usage,
    vision_coverage,
)

REAL_ITEM_ID = 1  # Blink Dagger, cost 2250 — a real item per the vocabulary
CONSUMABLE_ITEM_ID = 44  # Tango — excluded by is_real_item


def row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "match_id": 1,
        "duration_seconds": 1_800,  # expected_trajectory_length == 31
        "game_mode_native": "ALL_PICK_RANKED",
        "lobby_type_native": "RANKED",
        "radiant_kills": [0] * 31,
        "dire_kills": [0] * 31,
        "radiant_networth_leads": [0] * 31,
        "tower_deaths": [],
        "bottom_lane_outcome_native": None,
        "mid_lane_outcome_native": None,
        "top_lane_outcome_native": None,
        "account_pseudonym": "acct-1",
        "self": {
            "hero_id": 1,
            "is_radiant": True,
            "is_victory": True,
            "leaver_status_native": "NONE",
            "lane_native": None,
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


def rows(n: int, **overrides: Any) -> list[dict[str, Any]]:
    return [row(match_id=i, **overrides) for i in range(n)]


# --------------------------------------------------------------------------
# registry shape
# --------------------------------------------------------------------------


def test_registry_has_all_eight_dimensions() -> None:
    assert set(FEATURE_REGISTRY) == {
        "deaths_alone_share",
        "fight_conversion",
        "spike_usage",
        "death_clustering",
        "lane_to_map",
        "closer_vs_comeback",
        "vision_coverage",
        "lane_vs_jungle_share",
    }


def test_registry_report_sections_are_valid() -> None:
    for spec in FEATURE_REGISTRY.values():
        assert spec.report_section in REPORT_SECTIONS


def test_group_rows_by_account_fails_closed_without_pseudonym() -> None:
    with pytest.raises(ValueError):
        group_rows_by_account([row(account_pseudonym=None)])


def test_group_rows_by_account_groups_correctly() -> None:
    grouped = group_rows_by_account(
        [row(account_pseudonym="a"), row(account_pseudonym="b"), row(account_pseudonym="a")]
    )
    assert set(grouped) == {"a", "b"}
    assert len(grouped["a"]) == 2
    assert len(grouped["b"]) == 1


# --------------------------------------------------------------------------
# 1. deaths_alone_share
# --------------------------------------------------------------------------


def test_deaths_alone_share_zero_support_is_none() -> None:
    assert deaths_alone_share(rows(MIN_OBSERVATIONS, self={"events": {"death_events": []}})) is None


def test_deaths_alone_share_averages_per_match_values() -> None:
    # each match: one death in minute 3 (alone) -> per-match share 1.0
    death_rows = rows(
        MIN_OBSERVATIONS,
        self={"events": {"death_events": [{"time": 180}]}},
    )
    result = deaths_alone_share(death_rows)
    assert result is not None
    assert result.primary.value == pytest.approx(1.0)
    assert result.primary.observations == MIN_OBSERVATIONS


def test_deaths_alone_share_below_minimum_support_is_none() -> None:
    death_rows = rows(
        MIN_OBSERVATIONS - 1,
        self={"events": {"death_events": [{"time": 180}]}},
    )
    assert deaths_alone_share(death_rows) is None


# --------------------------------------------------------------------------
# 2. fight_conversion
# --------------------------------------------------------------------------


def _fight_conversion_row(*, converts: bool, match_id: int) -> dict[str, Any]:
    radiant_kills = [0] * 31
    dire_kills = [0] * 31
    radiant_kills[5] = 2  # own team (radiant) fight-minute at 5, enemy conceded 0
    tower_deaths = (
        [{"is_radiant": False, "time": 6 * 60 + 10}] if converts else []
    )
    return row(
        match_id=match_id,
        radiant_kills=radiant_kills,
        dire_kills=dire_kills,
        tower_deaths=tower_deaths,
        self={"is_radiant": True},
    )


def test_fight_conversion_counts_converted_and_unconverted() -> None:
    data = [
        _fight_conversion_row(converts=True, match_id=i) for i in range(MIN_OBSERVATIONS)
    ] + [_fight_conversion_row(converts=False, match_id=100 + i) for i in range(MIN_OBSERVATIONS)]
    result = fight_conversion(data)
    assert result is not None
    assert result.primary.observations == 2 * MIN_OBSERVATIONS
    assert result.primary.value == pytest.approx(0.5)


def test_fight_conversion_requires_zero_enemy_kills_that_minute() -> None:
    candidate = row(
        radiant_kills=[0, 0, 2] + [0] * 28,
        dire_kills=[0, 0, 1] + [0] * 28,  # enemy also scored -> not a clean fight
        self={"is_radiant": True},
    )
    result = fight_conversion([candidate] * MIN_OBSERVATIONS)
    assert result is None  # zero qualifying minutes


def test_fight_conversion_below_minimum_support_is_none() -> None:
    data = [_fight_conversion_row(converts=True, match_id=i) for i in range(MIN_OBSERVATIONS - 1)]
    assert fight_conversion(data) is None


def test_fight_conversion_omits_matches_without_tower_evidence() -> None:
    data = [
        _fight_conversion_row(converts=True, match_id=i) | {"tower_deaths": None}
        for i in range(MIN_OBSERVATIONS)
    ]
    assert fight_conversion(data) is None


# --------------------------------------------------------------------------
# 3. spike_usage
# --------------------------------------------------------------------------


def _spike_row(match_id: int, purchase_time: int, event_time: int | None) -> dict[str, Any]:
    events: dict[str, Any] = {
        "item_purchases": [{"item_id": REAL_ITEM_ID, "time": purchase_time}],
    }
    if event_time is not None:
        events["kill_events"] = [{"time": event_time}]
    return row(match_id=match_id, self={"events": events})


def test_spike_usage_ignores_consumables_and_takes_median_gap() -> None:
    data = [
        row(
            match_id=i,
            self={
                "events": {
                    "item_purchases": [
                        {"item_id": CONSUMABLE_ITEM_ID, "time": 0},  # not real, skipped
                        {"item_id": REAL_ITEM_ID, "time": 1_000},
                    ],
                    "kill_events": [{"time": 1_000 + 90}],
                }
            },
        )
        for i in range(MIN_OBSERVATIONS)
    ]
    result = spike_usage(data)
    assert result is not None
    assert result.primary.value == pytest.approx(90.0)
    assert result.primary.observations == MIN_OBSERVATIONS


def test_spike_usage_excludes_matches_with_no_follow_up_event() -> None:
    data = [_spike_row(i, purchase_time=500, event_time=None) for i in range(MIN_OBSERVATIONS)]
    assert spike_usage(data) is None


def test_spike_usage_excludes_matches_with_no_real_item_purchase() -> None:
    data = [
        row(
            match_id=i,
            self={
                "events": {
                    "item_purchases": [{"item_id": CONSUMABLE_ITEM_ID, "time": 0}],
                    "kill_events": [{"time": 500}],
                }
            },
        )
        for i in range(MIN_OBSERVATIONS)
    ]
    assert spike_usage(data) is None


# --------------------------------------------------------------------------
# 4. death_clustering
# --------------------------------------------------------------------------


def test_death_clustering_boundary_is_inclusive() -> None:
    # gap exactly at the boundary counts as clustered
    data = rows(
        MIN_OBSERVATIONS,
        self={
            "events": {
                "death_events": [
                    {"time": 100},
                    {"time": 100 + DEATH_CLUSTER_WINDOW_SECONDS},
                ]
            }
        },
    )
    result = death_clustering(data)
    assert result is not None
    assert result.primary.value == pytest.approx(1.0)


def test_death_clustering_just_over_boundary_is_not_clustered() -> None:
    data = rows(
        MIN_OBSERVATIONS,
        self={
            "events": {
                "death_events": [
                    {"time": 100},
                    {"time": 100 + DEATH_CLUSTER_WINDOW_SECONDS + 1},
                ]
            }
        },
    )
    result = death_clustering(data)
    assert result is not None
    assert result.primary.value == pytest.approx(0.0)


def test_death_clustering_zero_support_is_none() -> None:
    data = rows(MIN_OBSERVATIONS, self={"events": {"death_events": [{"time": 100}]}})
    assert death_clustering(data) is None  # single deaths never produce a gap


# --------------------------------------------------------------------------
# 5. lane_to_map
# --------------------------------------------------------------------------


def test_map_own_lane_side_relative_mapping() -> None:
    assert _map_own_lane_to_map_lane(True, "SAFE_LANE") == "bottom"
    assert _map_own_lane_to_map_lane(False, "SAFE_LANE") == "top"
    assert _map_own_lane_to_map_lane(True, "OFF_LANE") == "top"
    assert _map_own_lane_to_map_lane(False, "OFF_LANE") == "bottom"
    assert _map_own_lane_to_map_lane(True, "MID_LANE") == "mid"
    assert _map_own_lane_to_map_lane(False, "MID_LANE") == "mid"
    assert _map_own_lane_to_map_lane(True, "JUNGLE") is None
    assert _map_own_lane_to_map_lane(True, "ROAMING") is None
    assert _map_own_lane_to_map_lane(True, None) is None


def _lane_row(match_id: int, *, won: bool) -> dict[str, Any]:
    networth = [0] * 31
    networth[20] = 15_000 if won else 8_000
    return row(
        match_id=match_id,
        bottom_lane_outcome_native="RADIANT_VICTORY" if won else "DIRE_VICTORY",
        self={
            "is_radiant": True,
            "lane_native": "SAFE_LANE",
            "trajectories": {"networth_per_minute": networth},
        },
    )


def test_lane_to_map_contrasts_won_vs_not_won() -> None:
    data = [_lane_row(i, won=True) for i in range(MIN_OBSERVATIONS)] + [
        _lane_row(100 + i, won=False) for i in range(MIN_OBSERVATIONS)
    ]
    result = lane_to_map(data)
    assert result is not None
    assert result.primary.value == pytest.approx(15_000)
    assert result.secondary is not None
    assert result.secondary.value == pytest.approx(8_000)


def test_lane_to_map_treats_tie_as_not_won() -> None:
    tie_row = _lane_row(0, won=True)
    tie_row["bottom_lane_outcome_native"] = "TIE"
    data = [_lane_row(i, won=True) for i in range(MIN_OBSERVATIONS)] + [tie_row] * MIN_OBSERVATIONS
    result = lane_to_map(data)
    assert result is not None
    assert result.secondary is not None
    assert result.secondary.value == pytest.approx(15_000)  # the tie rows' net worth


def test_lane_to_map_below_minimum_support_on_either_side_is_none() -> None:
    data = [_lane_row(i, won=True) for i in range(MIN_OBSERVATIONS)] + [
        _lane_row(100 + i, won=False) for i in range(MIN_OBSERVATIONS - 1)
    ]
    assert lane_to_map(data) is None


def test_lane_vs_jungle_share_does_not_fill_missing_lane_gold_with_zero() -> None:
    data = rows(
        MIN_OBSERVATIONS,
        self={
            "farm_distribution": {
                "creep_location": None,
                "neutral_location": [{"gold": 100}],
            }
        },
    )
    assert lane_vs_jungle_share(data) is None


# --------------------------------------------------------------------------
# 6. closer_vs_comeback
# --------------------------------------------------------------------------


def _lead_row(match_id: int, *, lead: int, won: bool) -> dict[str, Any]:
    return row(
        match_id=match_id,
        radiant_networth_leads=[0, lead],
        duration_seconds=120,
        self={"is_radiant": True, "is_victory": won},
    )


def test_closer_vs_comeback_rates() -> None:
    ahead_won = [_lead_row(i, lead=LEAD_THRESHOLD_GOLD, won=True) for i in range(MIN_OBSERVATIONS)]
    ahead_lost = [
        _lead_row(100 + i, lead=LEAD_THRESHOLD_GOLD, won=False) for i in range(MIN_OBSERVATIONS)
    ]
    behind_won = [
        _lead_row(200 + i, lead=-LEAD_THRESHOLD_GOLD, won=True) for i in range(MIN_OBSERVATIONS)
    ]
    result = closer_vs_comeback(ahead_won + ahead_lost + behind_won)
    assert result is not None
    assert result.primary.observations == 2 * MIN_OBSERVATIONS  # all "ahead" matches
    assert result.primary.value == pytest.approx(0.5)
    assert result.secondary is not None
    assert result.secondary.observations == MIN_OBSERVATIONS
    assert result.secondary.value == pytest.approx(1.0)


def test_closer_vs_comeback_below_minimum_support_is_none() -> None:
    ahead_won = [
        _lead_row(i, lead=LEAD_THRESHOLD_GOLD, won=True) for i in range(MIN_OBSERVATIONS - 1)
    ]
    assert closer_vs_comeback(ahead_won) is None


# --------------------------------------------------------------------------
# 7. vision_coverage
# --------------------------------------------------------------------------


def test_vision_coverage_is_none_when_never_warded() -> None:
    data = rows(MIN_OBSERVATIONS, self={"events": {"wards": []}})
    assert vision_coverage(data) is None


def test_vision_coverage_expiry_boundary() -> None:
    # duration 600s -> expected_trajectory_length == 11 (minutes 0..10)
    # a ward placed at time 0 covers minutes 0..5 (360s duration = exactly
    # through the end of minute 5, 300-359s); minute 6 (360-419s) is not covered.
    data = rows(
        MIN_OBSERVATIONS,
        duration_seconds=600,
        self={"events": {"wards": [{"time": 0, "type": 0}]}},
    )
    result = vision_coverage(data)
    assert result is not None
    covered_minutes = OBSERVER_WARD_DURATION_SECONDS // 60  # 6 minutes: 0..5
    assert result.primary.value == pytest.approx(covered_minutes / 11)


def test_vision_coverage_ignores_sentry_wards() -> None:
    data = rows(
        MIN_OBSERVATIONS,
        duration_seconds=600,
        self={"events": {"wards": [{"time": 0, "type": 1}]}},  # sentry only
    )
    assert vision_coverage(data) is None


def test_vision_coverage_omits_unavailable_ward_streams() -> None:
    warded = rows(
        MIN_OBSERVATIONS,
        duration_seconds=600,
        self={"events": {"wards": [{"time": 0, "type": 0}]}},
    )
    unavailable = row(match_id=999, self={"events": {"wards": None}})
    result = vision_coverage([*warded, unavailable])
    assert result is not None
    assert result.primary.observations == MIN_OBSERVATIONS


def test_vision_coverage_includes_zero_coverage_matches_once_player_has_warded() -> None:
    warded = row(
        match_id=0,
        duration_seconds=600,
        self={"events": {"wards": [{"time": 0, "type": 0}]}},
    )
    unwarded = rows(
        MIN_OBSERVATIONS - 1,
        duration_seconds=600,
        self={"events": {"wards": []}},
    )
    result = vision_coverage([warded, *unwarded])
    assert result is not None
    assert result.primary.observations == MIN_OBSERVATIONS


# --------------------------------------------------------------------------
# 8. lane_vs_jungle_share
# --------------------------------------------------------------------------


def test_lane_vs_jungle_share_averages_per_match_shares() -> None:
    data = rows(
        MIN_OBSERVATIONS,
        self={
            "farm_distribution": {
                "creep_location": [{"id": 0, "gold": 3000}],
                "neutral_location": [{"id": 7, "gold": 1000}],
            }
        },
    )
    result = lane_vs_jungle_share(data)
    assert result is not None
    assert result.primary.value == pytest.approx(0.25)


def test_lane_vs_jungle_share_zero_support_is_none() -> None:
    data = rows(MIN_OBSERVATIONS, self={"farm_distribution": None})
    assert lane_vs_jungle_share(data) is None
