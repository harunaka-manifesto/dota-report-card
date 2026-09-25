"""The Pass-2 observation series must reconstruct the Pass-2 census exactly.

``pass2_features`` produces one number per player; ``pass2_observations``
produces the series that number summarises. If the two ever disagree, the
ranking model is standing on a different quantity from the one the census
published, so the tests here pin the agreement rather than re-deriving each
dimension's arithmetic a second time.
"""

from __future__ import annotations

import statistics
from typing import Any

import pytest
from report_card.player_analysis_v7.research.pass2_features import (
    FEATURE_REGISTRY,
    MIN_OBSERVATIONS,
)
from report_card.player_analysis_v7.research.pass2_features import (
    closer_vs_comeback as census_closer_vs_comeback,
)
from report_card.player_analysis_v7.research.pass2_features import (
    deaths_alone_share as census_deaths_alone_share,
)
from report_card.player_analysis_v7.research.pass2_features import (
    lane_to_map as census_lane_to_map,
)
from report_card.player_analysis_v7.research.pass2_features import (
    spike_usage as census_spike_usage,
)
from report_card.player_analysis_v7.research.pass2_observations import (
    ARM_AHEAD,
    ARM_BEHIND,
    ARM_LOST_LANE,
    ARM_WON_LANE,
    OBSERVATION_REGISTRY,
    chronological,
    closer_vs_comeback,
    deaths_alone_share,
    fight_conversion,
    lane_to_map,
    lane_vs_jungle_share,
    pass2_ctx,
    spike_usage,
    vision_coverage,
)

from legacy.tests.unit.test_v7_research_pass2_features import REAL_ITEM_ID, row, rows

# --------------------------------------------------------------------------
# registry shape
# --------------------------------------------------------------------------


def test_registry_covers_exactly_the_census_dimensions() -> None:
    assert set(OBSERVATION_REGISTRY) == set(FEATURE_REGISTRY)


def test_registry_sections_agree_with_the_census() -> None:
    for key, dimension in OBSERVATION_REGISTRY.items():
        assert dimension.section == FEATURE_REGISTRY[key].report_section


def test_contrast_dimensions_declare_both_arms() -> None:
    for dimension in OBSERVATION_REGISTRY.values():
        if dimension.arm_family:
            assert dimension.treated and dimension.control
            assert dimension.treated != dimension.control
        else:
            assert dimension.treated is None and dimension.control is None


def test_arm_family_flag_agrees_with_the_census_contrast_flag() -> None:
    for key, dimension in OBSERVATION_REGISTRY.items():
        assert dimension.arm_family == FEATURE_REGISTRY[key].is_contrast


# --------------------------------------------------------------------------
# context
# --------------------------------------------------------------------------


def test_pass2_ctx_reads_hero_and_side_from_self() -> None:
    ctx = dict(pass2_ctx(row(self={"hero_id": 47, "is_radiant": False})))
    assert ctx["hero"] == "47"
    assert ctx["side"] == "D"


def test_pass2_ctx_carries_the_parsed_linked_factors() -> None:
    ctx = dict(pass2_ctx(row(self={"position_native": "POSITION_1", "lane_native": "SAFE_LANE"})))
    assert ctx["position"] == "POSITION_1"
    assert ctx["lane"] == "SAFE_LANE"


def test_pass2_context_does_not_map_unknown_side_or_hero_to_known_levels() -> None:
    ctx = dict(pass2_ctx(row(self={"hero_id": None, "is_radiant": None})))
    assert ctx["hero"] == "UNKNOWN"
    assert ctx["side"] == "UNKNOWN"
    assert vision_coverage(
        [row(self={"hero_id": None, "is_radiant": None, "events": {"wards": []}})]
    ) == []


def test_chronological_orders_oldest_first() -> None:
    unordered = [
        row(match_id=3, started_at=300),
        row(match_id=1, started_at=100),
        row(match_id=2, started_at=200),
    ]
    assert [r["match_id"] for r in chronological(unordered)] == [1, 2, 3]


def test_chronological_breaks_ties_on_match_id() -> None:
    tied = [row(match_id=9, started_at=100), row(match_id=4, started_at=100)]
    assert [r["match_id"] for r in chronological(tied)] == [4, 9]


# --------------------------------------------------------------------------
# series reconstructs the census
# --------------------------------------------------------------------------


def test_deaths_alone_share_series_mean_is_the_census_value() -> None:
    death_rows = rows(MIN_OBSERVATIONS + 3, self={"events": {"death_events": [{"time": 180}]}})
    series = deaths_alone_share(death_rows)
    census = census_deaths_alone_share(death_rows)
    assert census is not None
    assert len(series) == census.primary.observations
    assert statistics.fmean(o.value for o in series) == pytest.approx(census.primary.value)


def _spike_row(match_id: int, gap: int) -> dict[str, Any]:
    return row(
        match_id=match_id,
        self={
            "events": {
                "item_purchases": [{"item_id": REAL_ITEM_ID, "time": 600}],
                "kill_events": [{"time": 600 + gap}],
                "assist_events": [],
            }
        },
    )


def test_spike_usage_series_median_is_the_census_value() -> None:
    """The census reports the median gap; the ranking pipeline takes the mean
    of the same series. Both must be computable from the series alone."""

    gaps = [30, 60, 90, 120, 150, 600]
    spike_rows = [_spike_row(i, gap) for i, gap in enumerate(gaps)]
    series = spike_usage(spike_rows)
    census = census_spike_usage(spike_rows)
    assert census is not None
    assert len(series) == census.primary.observations
    assert statistics.median(o.value for o in series) == pytest.approx(census.primary.value)
    assert statistics.fmean(o.value for o in series) != pytest.approx(census.primary.value)


def _lane_row(match_id: int, *, won: bool, net_worth: int) -> dict[str, Any]:
    return row(
        match_id=match_id,
        mid_lane_outcome_native="RADIANT_VICTORY" if won else "DIRE_VICTORY",
        self={
            "is_radiant": True,
            "lane_native": "MID_LANE",
            "trajectories": {"networth_per_minute": [net_worth] * 32},
        },
    )


def test_lane_to_map_arm_means_are_the_census_contrast() -> None:
    lane_rows = [_lane_row(i, won=True, net_worth=9_000) for i in range(MIN_OBSERVATIONS)]
    lane_rows += [_lane_row(100 + i, won=False, net_worth=6_000) for i in range(MIN_OBSERVATIONS)]
    series = lane_to_map(lane_rows)
    census = census_lane_to_map(lane_rows)
    assert census is not None and census.secondary is not None
    won = [o.value for o in series if o.arm == ARM_WON_LANE]
    lost = [o.value for o in series if o.arm == ARM_LOST_LANE]
    assert len(won) == census.primary.observations
    assert len(lost) == census.secondary.observations
    assert statistics.fmean(won) == pytest.approx(census.primary.value)
    assert statistics.fmean(lost) == pytest.approx(census.secondary.value)


def _swing_row(match_id: int, *, ahead: bool, behind: bool, won: bool) -> dict[str, Any]:
    leads = [0] * 31
    if ahead:
        leads[10] = 20_000
    if behind:
        leads[20] = -20_000
    return row(
        match_id=match_id,
        radiant_networth_leads=leads,
        self={"is_radiant": True, "is_victory": won},
    )


def test_closer_vs_comeback_arm_means_are_the_census_contrast() -> None:
    swing_rows = [
        _swing_row(i, ahead=True, behind=False, won=i % 2 == 0) for i in range(MIN_OBSERVATIONS)
    ]
    swing_rows += [
        _swing_row(100 + i, ahead=False, behind=True, won=i == 0) for i in range(MIN_OBSERVATIONS)
    ]
    series = closer_vs_comeback(swing_rows)
    census = census_closer_vs_comeback(swing_rows)
    assert census is not None and census.secondary is not None
    ahead = [o.value for o in series if o.arm == ARM_AHEAD]
    behind = [o.value for o in series if o.arm == ARM_BEHIND]
    assert len(ahead) == census.primary.observations
    assert len(behind) == census.secondary.observations
    assert statistics.fmean(ahead) == pytest.approx(census.primary.value)
    assert statistics.fmean(behind) == pytest.approx(census.secondary.value)


def test_closer_vs_comeback_counts_one_match_in_both_arms() -> None:
    both = [_swing_row(i, ahead=True, behind=True, won=True) for i in range(3)]
    series = closer_vs_comeback(both)
    assert len(series) == 6
    assert sum(1 for o in series if o.arm == ARM_AHEAD) == 3
    assert sum(1 for o in series if o.arm == ARM_BEHIND) == 3


def test_vision_coverage_is_empty_for_a_player_who_never_wards() -> None:
    assert vision_coverage(rows(MIN_OBSERVATIONS + 5)) == []


def test_vision_coverage_includes_zero_coverage_matches_once_the_player_wards() -> None:
    warded = row(
        match_id=0,
        self={"events": {"wards": [{"time": 60, "type": 0}]}},
    )
    series = vision_coverage([warded, *(row(match_id=i) for i in (1, 2, 3))])
    assert len(series) == 4
    assert series[0].value > 0.0
    assert all(o.value == 0.0 for o in series[1:])


def test_vision_coverage_omits_an_explicitly_unavailable_ward_stream() -> None:
    warded = rows(
        MIN_OBSERVATIONS,
        self={"events": {"wards": [{"time": 60, "type": 0}]}},
    )
    unavailable = row(match_id=99, self={"events": {"wards": None}})
    series = vision_coverage([*warded, unavailable])
    assert len(series) == MIN_OBSERVATIONS


def test_fight_conversion_omits_an_explicitly_unavailable_tower_stream() -> None:
    candidate = row(
        radiant_kills=[0, 0, 2] + [0] * 28,
        dire_kills=[0] * 31,
        tower_deaths=None,
        self={"is_radiant": True},
    )
    assert fight_conversion([candidate]) == []


def test_lane_vs_jungle_share_omits_a_missing_component() -> None:
    candidate = row(
        self={
            "farm_distribution": {
                "creep_location": None,
                "neutral_location": [{"gold": 100}],
            }
        }
    )
    assert lane_vs_jungle_share([candidate]) == []
