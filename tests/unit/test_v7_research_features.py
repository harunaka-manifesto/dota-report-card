from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from scripts.v7_research.corpus import ReservedSplitAccess
from scripts.v7_research.features import (
    COMFORT_POOL_SIZE,
    EXTRACTORS,
    LAYOFF_SECONDS,
    Opportunity,
    PlayerFrame,
    base_ctx,
    duration_bucket,
    extract,
    hero_novelty,
    layoff_return,
    load_frames,
    own_lane_result,
    per_ten_minutes,
    post_loss_hero_switch,
    post_loss_next_outcome,
    post_loss_session_continuation,
    progress,
    session_drift_outcome,
    state_responsive_participation,
    transfer_outcome,
    warmup_first_match,
)
from scripts.v7_research.registry import FAMILIES, FAMILY_BY_NAME

HOUR = 3600


def row(index: int = 0, **overrides: Any) -> dict[str, Any]:
    start = 1_000_000 + index * 3_000
    base: dict[str, Any] = {
        "match_id": 1_000 + index,
        "started_at": start,
        "ended_at": start + 1_800,
        "duration_seconds": 1_800,
        "game_mode_native": "ALL_PICK_RANKED",
        "lobby_type_native": "RANKED",
        "leaver_status_native": "NONE",
        "position_native": "POSITION_3",
        "role_native": "CORE",
        "lane_native": "OFF_LANE",
        "hero_id": 5,
        "game_version_id": 182,
        "is_radiant": True,
        "is_victory": True,
        "kills": 4,
        "deaths": 3,
        "assists": 7,
        "enum_failure": False,
    }
    base.update(overrides)
    return base


def frame(rows: list[dict[str, Any]], parsed: dict[int, dict[str, Any]] | None = None) -> PlayerFrame:
    return PlayerFrame(
        pseudonym="v7p_test",
        split="DISCOVERY",
        completeness="complete",
        rows=rows,
        parsed=parsed or {},
    )


# ---------------------------------------------------------------------------
# forbidden-split gate
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("split", ["CALIBRATION_RESERVED", "SEALED_VALIDATION"])
def test_discovery_loader_cannot_reach_a_reserved_split(tmp_path, split: str) -> None:
    from scripts.v7_research.corpus import CorpusPaths

    with pytest.raises(ReservedSplitAccess):
        load_frames(CorpusPaths(tmp_path), frozenset({split}))


def test_discovery_loader_rejects_a_reserved_split_even_when_mixed_with_discovery(tmp_path) -> None:
    from scripts.v7_research.corpus import CorpusPaths

    with pytest.raises(ReservedSplitAccess):
        load_frames(CorpusPaths(tmp_path), frozenset({"DISCOVERY", "SEALED_VALIDATION"}))


# ---------------------------------------------------------------------------
# determinism and registry coherence
# ---------------------------------------------------------------------------


def test_every_registered_family_has_an_extractor() -> None:
    for family in FAMILIES:
        assert family.name in EXTRACTORS


def test_every_extractor_is_registered() -> None:
    for name in EXTRACTORS:
        assert name in FAMILY_BY_NAME


def test_contrast_families_declare_both_arms() -> None:
    for family in FAMILIES:
        if family.arm_family:
            assert family.treated and family.control
            assert family.treated != family.control
        else:
            assert family.treated is None and family.control is None


def test_extractors_are_deterministic() -> None:
    rows = [row(index, is_victory=index % 3 != 0, hero_id=index % 7) for index in range(120)]
    candidate = frame(rows)
    for name in EXTRACTORS:
        first = extract(name, candidate)
        second = extract(name, candidate)
        assert first == second, name


def test_unknown_family_raises() -> None:
    with pytest.raises(KeyError):
        extract("not_a_family", frame([row(0)]))


# ---------------------------------------------------------------------------
# mode-stratum handling
# ---------------------------------------------------------------------------


def test_duration_bucket_is_mode_relative_not_wall_clock() -> None:
    # 1,400 s is a long Turbo game and a short standard game; a single
    # wall-clock cut would make the bucket a proxy for the mode.
    turbo = row(duration_seconds=1_400, game_mode_native="TURBO")
    standard = row(duration_seconds=1_400, game_mode_native="ALL_PICK_RANKED")
    assert duration_bucket(turbo) == "D1"
    assert duration_bucket(standard) == "D0"


def test_base_context_always_carries_mode() -> None:
    for mode in ("TURBO", "ALL_PICK_RANKED", "SINGLE_DRAFT"):
        assert ("mode", "TURBO" if mode == "TURBO" else "STANDARD") in base_ctx(
            row(game_mode_native=mode)
        )


def test_extractors_pool_turbo_and_standard() -> None:
    rows = [
        row(index, game_mode_native="TURBO" if index % 2 else "ALL_PICK_RANKED", duration_seconds=1_200 if index % 2 else 2_400)
        for index in range(80)
    ]
    opportunities = post_loss_next_outcome(frame(rows))
    modes = {dict(opportunity.ctx)["mode"] for opportunity in opportunities}
    assert modes == {"TURBO", "STANDARD"}


def test_progress_is_normalised_so_turbo_and_standard_are_comparable() -> None:
    turbo = row(duration_seconds=1_200, game_mode_native="TURBO")
    standard = row(duration_seconds=2_400)
    assert progress(600, turbo) == pytest.approx(0.5)
    assert progress(1_200, standard) == pytest.approx(0.5)


def test_per_ten_minutes_scales_by_duration() -> None:
    assert per_ten_minutes(6, row(duration_seconds=1_200)) == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# opportunity-definition edge cases
# ---------------------------------------------------------------------------


def test_transitions_do_not_cross_a_session_boundary() -> None:
    first = row(0)
    second = row(1, started_at=first["ended_at"] + 4 * HOUR, ended_at=first["ended_at"] + 4 * HOUR + 1_800)
    assert post_loss_next_outcome(frame([first, second])) == []


def test_transitions_are_produced_inside_a_session() -> None:
    rows = [row(0), row(1)]
    assert len(post_loss_next_outcome(frame(rows))) == 1


def test_a_single_match_produces_no_transition_and_no_drift() -> None:
    single = frame([row(0)])
    assert post_loss_next_outcome(single) == []
    assert session_drift_outcome(single) == []


def test_session_drift_needs_four_matches_and_drops_the_odd_middle() -> None:
    assert session_drift_outcome(frame([row(index) for index in range(3)])) == []
    five = session_drift_outcome(frame([row(index) for index in range(5)]))
    assert len(five) == 4
    assert sum(1 for opportunity in five if opportunity.arm == "early") == 2
    assert sum(1 for opportunity in five if opportunity.arm == "late") == 2


def test_session_continuation_drops_the_right_censored_final_match() -> None:
    rows = [row(index) for index in range(4)]
    opportunities = post_loss_session_continuation(frame(rows))
    assert len(opportunities) == len(rows) - 1
    assert [opportunity.value for opportunity in opportunities] == [1.0, 1.0, 1.0]


def test_session_continuation_marks_a_session_end_as_a_stop() -> None:
    rows = [row(0), row(1)]
    rows.append(row(2, started_at=rows[1]["ended_at"] + 5 * HOUR, ended_at=rows[1]["ended_at"] + 5 * HOUR + 1_800))
    opportunities = post_loss_session_continuation(frame(rows))
    # Two opportunities: index 0 continued, index 1 stopped. Index 2 is censored.
    assert [opportunity.value for opportunity in opportunities] == [1.0, 0.0]


def test_warmup_needs_three_matches_and_marks_exactly_one_first() -> None:
    assert warmup_first_match(frame([row(0), row(1)])) == []
    opportunities = warmup_first_match(frame([row(index) for index in range(4)]))
    assert sum(1 for opportunity in opportunities if opportunity.arm == "first") == 1
    assert sum(1 for opportunity in opportunities if opportunity.arm == "later") == 3


def test_layoff_drops_the_ambiguous_middle_gap() -> None:
    first = row(0)
    middle = row(1, started_at=first["ended_at"] + 6 * HOUR, ended_at=first["ended_at"] + 6 * HOUR + 1_800)
    late = row(2, started_at=middle["ended_at"] + LAYOFF_SECONDS + 60, ended_at=middle["ended_at"] + LAYOFF_SECONDS + 1_860)
    arms = [opportunity.arm for opportunity in layoff_return(frame([first, middle, late]))]
    assert arms == ["return"]


def test_hero_switch_reads_the_next_match_not_the_current_one() -> None:
    rows = [row(0, hero_id=1, is_victory=False), row(1, hero_id=2)]
    opportunities = post_loss_hero_switch(frame(rows))
    assert opportunities[0].value == 1.0
    assert opportunities[0].arm == "loss"


def test_comfort_pool_is_built_only_from_strictly_prior_matches() -> None:
    # 60 matches on hero 1, then one match on a hero never played before: it
    # must be labelled "stretch", which is impossible if the pool peeked ahead.
    rows = [row(index, hero_id=1) for index in range(60)]
    rows.append(row(60, hero_id=99))
    arms = [opportunity.arm for opportunity in transfer_outcome(frame(rows))]
    assert arms[-1] == "stretch"
    assert set(arms[:-1]) == {"comfort"}


def test_comfort_pool_size_is_respected() -> None:
    rows: list[dict[str, Any]] = []
    for index in range(60):
        rows.append(row(index, hero_id=index % 8))
    rows.append(row(60, hero_id=0))
    opportunities = transfer_outcome(frame(rows))
    assert opportunities
    assert COMFORT_POOL_SIZE == 5


def test_hero_novelty_uses_a_warmup_and_a_thirty_day_memory() -> None:
    rows = [row(index, hero_id=1) for index in range(40)]
    opportunities = hero_novelty(frame(rows))
    assert len(opportunities) == 10
    assert all(opportunity.value == 0.0 for opportunity in opportunities)


# ---------------------------------------------------------------------------
# parsed-side edge cases
# ---------------------------------------------------------------------------


def parsed_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "match_id": 1_000,
        "duration_seconds": 1_800,
        "is_radiant": True,
        "is_victory": True,
        "lane_native": "SAFE_LANE",
        "position_native": "POSITION_1",
        "role_native": "CORE",
        "top_lane_outcome_native": "RADIANT_VICTORY",
        "mid_lane_outcome_native": "TIE",
        "bottom_lane_outcome_native": "DIRE_VICTORY",
        "radiant_networth_leads": [0] * 31,
        "radiant_kills": [1] * 31,
        "dire_kills": [1] * 31,
        "stats": {"kill_events": [], "assist_events": [], "item_purchases": []},
    }
    base.update(overrides)
    return base


def test_own_lane_result_maps_side_to_the_right_lane() -> None:
    # Radiant safe lane is the bottom lane, which Dire won here.
    assert own_lane_result(parsed_row(lane_native="SAFE_LANE", is_radiant=True)) == "lost"
    # Dire safe lane is the top lane, which Radiant won here.
    assert own_lane_result(parsed_row(lane_native="SAFE_LANE", is_radiant=False)) == "lost"
    assert own_lane_result(parsed_row(lane_native="OFF_LANE", is_radiant=True)) == "won"


def test_own_lane_result_returns_none_for_a_tie_or_an_unmapped_lane() -> None:
    assert own_lane_result(parsed_row(lane_native="MID_LANE")) is None
    assert own_lane_result(parsed_row(lane_native="JUNGLE")) is None
    assert own_lane_result(parsed_row(lane_native=None)) is None


def test_state_responsive_participation_needs_both_states_in_one_match() -> None:
    flat = parsed_row(radiant_networth_leads=[0] * 31)
    assert state_responsive_participation(frame([row(0)], {1_000: flat})) == []


def test_state_responsive_participation_is_a_within_match_contrast() -> None:
    lead = [-8_000] * 10 + [8_000] * 21
    parsed = parsed_row(
        radiant_networth_leads=lead,
        stats={
            "kill_events": [{"time": 120}, {"time": 240}],
            "assist_events": [{"time": 60}],
            "item_purchases": [],
        },
    )
    opportunities = state_responsive_participation(frame([row(0)], {1_000: parsed}))
    assert {opportunity.arm for opportunity in opportunities} == {"behind", "ahead"}
    behind = next(o for o in opportunities if o.arm == "behind")
    ahead = next(o for o in opportunities if o.arm == "ahead")
    assert behind.value == pytest.approx(3 / 10)
    assert ahead.value == pytest.approx(0.0)


def test_dire_orientation_flips_the_state(monkeypatch) -> None:
    lead = [-8_000] * 10 + [8_000] * 21
    parsed = parsed_row(
        radiant_networth_leads=lead,
        is_radiant=False,
        stats={"kill_events": [{"time": 120}], "assist_events": [], "item_purchases": []},
    )
    opportunities = state_responsive_participation(frame([row(0, is_radiant=False)], {1_000: parsed}))
    behind = next(o for o in opportunities if o.arm == "behind")
    # From Dire's point of view the first ten minutes are AHEAD, so the event
    # at minute two must not land in the behind arm.
    assert behind.value == pytest.approx(0.0)


def test_parsed_rows_without_a_product_context_history_row_are_dropped() -> None:
    parsed = parsed_row(match_id=9_999)
    empty = frame([], {9_999: parsed})
    assert state_responsive_participation(empty) == []


def test_opportunity_is_hashable_and_frozen() -> None:
    opportunity = Opportunity(1.0, (("mode", "TURBO"),), "loss")
    assert hash(opportunity)
    with pytest.raises(dataclasses.FrozenInstanceError):
        opportunity.value = 2.0  # type: ignore[misc]
