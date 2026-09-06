"""The owner's nine V7 selections, held in place.

Six of the nine were "keep what is already there". A behaviour that matches a
decision by accident is one refactor away from silently violating it, so those
are tested exactly as hard as the ones that changed code.

The last two tests are the ones that matter most: SEALED_VALIDATION stays
unopened, and no reserved split can be read by anything on the analysis path.
"""

from __future__ import annotations

import pytest
from app.player_analysis_v7 import acquisition_policy as acq
from app.player_analysis_v7 import report_contract
from app.player_analysis_v7.research import archetype, ranking, recommendation
from app.player_analysis_v7.research.corpus import (
    CALIBRATION_RESERVED,
    RESERVED_SPLITS,
    SEALED_VALIDATION,
    CorpusPaths,
    ReservedSplitAccess,
    iter_players,
)
from app.player_analysis_v7.research.owner_decisions import (
    CALIBRATION_RESERVED_SPENT,
    CARRIED_FORWARD,
    DECISIONS,
    NEEDS_RESERVED_SPLIT,
    PROVISIONAL,
    SEALED_VALIDATION_APPROVED,
)


def test_all_nine_decisions_are_recorded() -> None:
    assert sorted(DECISIONS) == [f"D{n}" for n in range(1, 10)]


def test_every_decision_names_a_choice_and_a_summary() -> None:
    for decision in DECISIONS.values():
        assert decision.choice
        assert decision.summary.strip()
        assert decision.question.strip()


def test_nothing_still_needs_a_reserved_split() -> None:
    """The owner closed D2 and D7 on DISCOVERY evidence. If a future decision
    reintroduces a claim on CALIBRATION_RESERVED, that is a conversation to
    have deliberately, not a flag someone flips."""

    assert NEEDS_RESERVED_SPLIT == ()
    assert CALIBRATION_RESERVED_SPENT is False


def test_only_the_archetype_special_cut_is_still_provisional() -> None:
    assert set(PROVISIONAL) == {"D6"}
    assert not DECISIONS["D6"].needs_calibration_reserved


def test_d2_drops_the_strength_bands() -> None:
    assert DECISIONS["D2"].choice == "c"
    assert not hasattr(report_contract, "StrengthBand")
    assert not hasattr(report_contract, "default_strength_band")
    assert "strength_band" not in report_contract.Finding.model_fields


def test_d2_keeps_what_replaces_the_band() -> None:
    """Dropping the adjective is only honest if the precise thing survives."""

    fields = report_contract.Finding.model_fields
    assert "direction" in fields
    assert "score" in fields
    assert "estimate" in fields


def test_d2_carries_why_the_bands_were_dropped() -> None:
    carried = " ".join(CARRIED_FORWARD["D2"])
    assert "65.2%" in carried
    assert "within-player" in carried


def test_d7_is_settled_by_the_discovery_sweep() -> None:
    carried = " ".join(CARRIED_FORWARD["D7"])
    assert "0.981966" in carried
    assert "0.982515" in carried


# --------------------------------------------------------------------------
# D1 — floor of three, gate slots four and five
# --------------------------------------------------------------------------


def _finding(key: str, score: float) -> ranking.RankedFinding:
    return ranking.RankedFinding(
        key=key,
        section="what_is_good",
        direction="positive",
        z=1.0,
        reliability=1.0,
        score=score,
        shrunk_estimate=ranking.ShrunkEstimate(
            point=1.0,
            interval=ranking.Interval(lower=0.0, upper=2.0, coverage=0.95),
        ),
        sample_size=100,
    )


def test_d1_floor_is_three() -> None:
    assert DECISIONS["D1"].choice == "c"
    assert ranking.FINDING_FLOOR == 3


def test_d1_keeps_the_floor_however_weak() -> None:
    slate = [_finding(f"d{i}", 0.01) for i in range(5)]
    assert len(ranking.apply_score_gate(slate)) == 3


def test_d1_gates_only_the_slots_above_the_floor() -> None:
    slate = [
        _finding("a", 2.0),
        _finding("b", 1.0),
        _finding("c", 0.5),
        _finding("d", 0.9),
        _finding("e", 0.1),
    ]
    kept = ranking.apply_score_gate(slate)
    assert [f.key for f in kept] == ["a", "b", "c", "d"]


def test_d1_never_shortens_a_slate_already_at_or_under_the_floor() -> None:
    slate = [_finding("a", 0.0), _finding("b", 0.0)]
    assert ranking.apply_score_gate(slate) == slate


def test_d1_does_not_resort_the_slate() -> None:
    """Selection may promote a weak Finding to keep a section from being
    empty; trimming by score and re-taking the top three would undo that."""

    slate = [_finding("strong", 3.0), _finding("promoted", 0.05), _finding("mid", 1.0)]
    kept = ranking.apply_score_gate(slate)
    assert [f.key for f in kept] == ["strong", "promoted", "mid"]


# --------------------------------------------------------------------------
# D3 — the screen stays at 0.95, with its sensitivity carried
# --------------------------------------------------------------------------


def test_d3_screen_cut_is_unchanged() -> None:
    assert DECISIONS["D3"].choice == "a"
    assert recommendation.MODAL_SIGN_SHARE_LIMIT == 0.95


def test_d3_carries_the_last_hits_sensitivity_forward() -> None:
    carried = " ".join(CARRIED_FORWARD["D3"])
    assert "last_hits_at_ten" in carried
    assert "0.9466" in carried


def test_d3_exclusions_are_exactly_the_two_contaminated_dimensions() -> None:
    assert set(recommendation.OUTCOME_CONTAMINATED_EXCLUSIONS) == {
        "fight_conversion",
        "death_clustering",
    }
    assert "last_hits_at_ten" in recommendation.eligible_dimensions()


# --------------------------------------------------------------------------
# D4 — no second reliability cutoff
# --------------------------------------------------------------------------


def test_d4_ranking_has_no_reliability_floor() -> None:
    """Shrinkage is the gate. A weak dimension must still be rankable, so a
    tiny reliability produces a tiny score rather than being dropped."""

    assert DECISIONS["D4"].choice == "a"
    weak = ranking.PlayerDimension(
        key="weak",
        section="what_is_good",
        delta_hat=1.0,
        se=10.0,
        sample_size=100,
        mu=0.0,
        tau=0.1,
        dependence_inflation=1.0,
    )
    ranked = ranking.rank_player([weak])
    assert len(ranked) == 1
    assert 0.0 <= ranked[0].reliability < 0.01
    assert ranked[0].score >= 0.0


# --------------------------------------------------------------------------
# D5 — three tempo levels
# --------------------------------------------------------------------------


def test_d5_keeps_three_tempo_levels() -> None:
    assert DECISIONS["D5"].choice == "a"
    assert archetype.TEMPO_LEVELS == ("early", "mid", "late")
    assert len(archetype.GRID_LABELS) == 18


def test_d5_carries_the_copy_constraint() -> None:
    carried = " ".join(CARRIED_FORWARD["D5"])
    assert "relative" in carried.lower()
    assert "stratum" in carried.lower()


# --------------------------------------------------------------------------
# D6 — both specials ship
# --------------------------------------------------------------------------


def test_d6_ships_both_specials() -> None:
    assert DECISIONS["D6"].choice == "a"
    assert set(archetype.SPECIAL_LABELS.values()) == {"The Lighthouse", "The Closer"}


def test_d6_special_cut_is_refreshed_from_pilot_data_not_a_reserved_split() -> None:
    assert DECISIONS["D6"].provisional
    assert not DECISIONS["D6"].needs_calibration_reserved
    assert "pilot data" in " ".join(CARRIED_FORWARD["D6"])


# --------------------------------------------------------------------------
# D7 — fifteen per arm, provisionally
# --------------------------------------------------------------------------


def test_d7_minimum_per_arm_is_fifteen_and_final() -> None:
    assert DECISIONS["D7"].choice == "a"
    assert recommendation.MIN_PER_ARM == 15
    assert not DECISIONS["D7"].provisional
    assert not DECISIONS["D7"].needs_calibration_reserved


# --------------------------------------------------------------------------
# D9 — full depth, and no fetch on a repeat report
# --------------------------------------------------------------------------


def test_d9_depth_is_identical_for_both_tiers() -> None:
    assert DECISIONS["D9"].choice == "a"
    assert acq.depth_for_tier("free") == acq.depth_for_tier("paid") == acq.FULL_DEPTH_MATCHES
    assert acq.PAID_MAY_ACQUIRE_MORE_THAN_FREE is False


def test_d9_unknown_tier_fails_closed() -> None:
    with pytest.raises(ValueError):
        acq.depth_for_tier("enterprise")


def test_d9_a_repeat_report_makes_no_provider_call() -> None:
    stored = set(range(500))
    repeat = acq.plan("acct", list(range(500)), stored)
    assert repeat.hits_provider is False
    assert repeat.requests_required == 0
    assert repeat.already_stored == 500


def test_d9_only_the_gap_is_fetched_after_new_matches() -> None:
    candidates = list(range(520, 20, -1))  # newest first
    stored = set(range(20, 501))
    result = acq.plan("acct", candidates, stored)
    assert result.match_ids_to_fetch == tuple(range(520, 500, -1))
    assert result.requests_required == acq.requests_for(20)


def test_d9_never_considers_more_than_full_depth() -> None:
    result = acq.plan("acct", list(range(2_000)), set())
    assert len(result.match_ids_to_fetch) == acq.FULL_DEPTH_MATCHES


def test_d9_fetch_order_stays_newest_first() -> None:
    result = acq.plan("acct", [900, 800, 700], set())
    assert result.match_ids_to_fetch == (900, 800, 700)


def test_d9_capacity_is_reported_not_enforced() -> None:
    """Depth is not trimmed to hit a throughput number; the ceiling is a
    consequence of the depth the owner chose."""

    assert acq.reports_per_day() == acq.PROVIDER_LIMITS["day"] // acq.MEASURED_REQUESTS_PER_ACCOUNT
    assert acq.reports_per_day() > 300


def test_d9_states_what_storage_must_guarantee() -> None:
    joined = " ".join(acq.PERSISTENCE_REQUIREMENTS).lower()
    assert "zero provider calls" in joined
    assert "payment" in joined


# --------------------------------------------------------------------------
# D8 — the sealed split stays sealed
# --------------------------------------------------------------------------


def test_d8_sealed_validation_is_not_approved() -> None:
    assert DECISIONS["D8"].choice == "a"
    assert SEALED_VALIDATION_APPROVED is False


@pytest.mark.parametrize("split", [CALIBRATION_RESERVED, SEALED_VALIDATION])
def test_no_reserved_split_can_be_read_through_the_corpus_reader(split: str, tmp_path) -> None:
    with pytest.raises(ReservedSplitAccess):
        list(iter_players(CorpusPaths(tmp_path), "history", frozenset({split})))


def test_both_reserved_splits_are_still_classified_as_reserved() -> None:
    assert RESERVED_SPLITS == frozenset({CALIBRATION_RESERVED, SEALED_VALIDATION})


def _sectioned(key: str, section: str, score: float) -> ranking.RankedFinding:
    return ranking.RankedFinding(
        key=key,
        section=section,
        direction="positive",
        z=1.0,
        reliability=1.0,
        score=score,
        shrunk_estimate=ranking.ShrunkEstimate(
            point=1.0,
            interval=ranking.Interval(lower=0.0, upper=2.0, coverage=0.95),
        ),
        sample_size=100,
    )


def test_d1_protects_a_sections_only_representative_from_the_gate() -> None:
    """``select_stratified`` promotes one Finding per section so no section
    renders empty, then re-sorts by score. Gating on score alone undoes that:
    on DISCOVERY it dropped three-section coverage from 520 players to 290."""

    slate = [
        _sectioned("a", "what_is_good", 3.0),
        _sectioned("b", "what_is_good", 2.0),
        _sectioned("c", "what_is_costing_you", 1.0),
        _sectioned("lonely", "response_to_a_loss", 0.02),
    ]
    kept = ranking.apply_score_gate(slate)
    assert [f.key for f in kept] == ["a", "b", "c", "lonely"]
    assert {f.section for f in kept} == set(ranking.FINDING_SECTIONS)


def test_d1_still_drops_a_weak_duplicate_of_a_covered_section() -> None:
    slate = [
        _sectioned("a", "what_is_good", 3.0),
        _sectioned("b", "what_is_costing_you", 2.0),
        _sectioned("c", "response_to_a_loss", 1.0),
        _sectioned("spare", "what_is_good", 0.02),
    ]
    assert [f.key for f in ranking.apply_score_gate(slate)] == ["a", "b", "c"]


def test_d1_tops_up_to_the_floor_when_sections_do_not_span_three() -> None:
    slate = [_sectioned(f"d{i}", "what_is_good", 0.01) for i in range(5)]
    kept = ranking.apply_score_gate(slate)
    assert len(kept) == ranking.FINDING_FLOOR
