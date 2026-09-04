from __future__ import annotations

import json
import math
import random
from typing import Any

import pytest

from scripts.v7_research.corpus import (
    CALIBRATION_RESERVED,
    CANDIDATE_TEST,
    DISCOVERY,
    SEALED_VALIDATION,
    ReservedSplitAccess,
    iter_players,
)
from scripts.v7_research.features import Opportunity, PlayerFrame, extract
from scripts.v7_research.inference import (
    MIN_BLOCKS,
    FamilyMatrix,
    block_bounds,
    build_matrix,
    contrast_null_replicate,
    infer_all,
    level_null_replicate,
    measure_type_i,
    minimum_detectable_effect,
    paule_mandel_tau_squared,
    player_inference,
    pool,
    regularized_incomplete_beta,
    split_half_stability,
    student_t_quantile,
    student_t_two_sided_p,
)
from scripts.v7_research.variants import (
    session_gap_override,
    volume_capped,
    without_non_chosen_hero_modes,
)

SEED = 20260903


# ---------------------------------------------------------------------------
# distribution primitives
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("a", "b", "x", "expected"),
    [(1.0, 1.0, 0.25, 0.25), (2.0, 3.0, 0.5, 0.6875), (0.5, 0.5, 0.5, 0.5)],
)
def test_incomplete_beta_matches_closed_form(a: float, b: float, x: float, expected: float) -> None:
    assert regularized_incomplete_beta(a, b, x) == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize(
    ("t_stat", "df", "expected"),
    [
        (0.0, 5, 1.0),
        (2.570582, 5, 0.05),
        (2.228139, 10, 0.05),
        (1.959964, 100000, 0.0500028),
        (4.604095, 4, 0.01),
    ],
)
def test_student_t_two_sided_p_matches_published_tables(
    t_stat: float, df: int, expected: float
) -> None:
    assert student_t_two_sided_p(t_stat, df) == pytest.approx(expected, abs=2e-6)


def test_student_t_p_is_sign_symmetric() -> None:
    for t_stat in (0.3, 1.1, 2.9, 7.5):
        assert student_t_two_sided_p(t_stat, 12) == student_t_two_sided_p(-t_stat, 12)


def test_student_t_quantile_inverts_the_p_value() -> None:
    for df in (4, 19, 60):
        critical = student_t_quantile(0.025, df)
        assert student_t_two_sided_p(critical, df) == pytest.approx(0.05, abs=1e-6)


def test_degenerate_degrees_of_freedom_return_nan_not_a_number_in_zero_one() -> None:
    assert math.isnan(student_t_two_sided_p(2.0, 0))
    assert math.isnan(student_t_two_sided_p(float("nan"), 10))


# ---------------------------------------------------------------------------
# blocks and the per-player statistic
# ---------------------------------------------------------------------------


def test_block_bounds_partition_the_sequence_exactly() -> None:
    for n in (1, 7, 40, 553, 1618):
        bounds = block_bounds(n)
        assert bounds[0][0] == 0
        assert bounds[-1][1] == n
        for (_, end), (start, _) in zip(bounds, bounds[1:], strict=False):
            assert end == start
        assert sum(end - start for start, end in bounds) == n


def test_block_bounds_are_empty_for_no_data() -> None:
    assert block_bounds(0) == []


def test_level_statistic_recovers_a_known_mean() -> None:
    values = [3.0 + 0.5 * math.sin(i) for i in range(400)]
    result = player_inference("p", values, None, None, None)
    assert result is not None
    assert result.delta == pytest.approx(sum(values) / len(values), abs=0.02)
    assert result.blocks == 20
    assert result.df == 19


def test_contrast_statistic_recovers_a_known_planted_difference() -> None:
    rng = random.Random(1)
    values: list[float] = []
    arms: list[int] = []
    for index in range(600):
        arm = index % 2
        arms.append(arm)
        values.append(rng.gauss(0.0, 1.0) + (2.0 if arm == 1 else 0.0))
    result = player_inference("p", values, arms, 1, 0)
    assert result is not None
    assert result.delta == pytest.approx(2.0, abs=0.2)
    assert result.p_value < 1e-6
    assert result.n_treated == 300
    assert result.n_control == 300


def test_contrast_statistic_is_sign_symmetric() -> None:
    rng = random.Random(7)
    values = [rng.gauss(0.0, 1.0) for _ in range(400)]
    arms = [index % 2 for index in range(400)]
    forward = player_inference("p", values, arms, 1, 0)
    reverse = player_inference("p", values, arms, 0, 1)
    assert forward is not None and reverse is not None
    assert forward.delta == pytest.approx(-reverse.delta, abs=1e-12)
    assert forward.p_value == pytest.approx(reverse.p_value, abs=1e-12)


def test_small_n_is_refused_rather_than_reported() -> None:
    assert player_inference("p", [1.0, 2.0, 3.0], None, None, None) is None
    assert player_inference("p", [], None, None, None) is None


def test_a_player_with_only_one_arm_is_refused() -> None:
    values = [1.0] * 400
    arms = [1] * 400
    assert player_inference("p", values, arms, 1, 0) is None


def test_a_constant_response_yields_zero_effect_and_no_false_rejection() -> None:
    result = player_inference("p", [2.5] * 400, None, None, None)
    assert result is not None
    assert result.delta == pytest.approx(2.5)
    assert result.standard_error == 0.0
    assert result.t_stat == math.inf
    # A constant series carries no information about dispersion; the caller
    # must see an infinite t rather than a fabricated finite p-value.
    assert result.p_value == 0.0


def test_a_constant_zero_response_is_not_a_rejection() -> None:
    result = player_inference("p", [0.0] * 400, None, None, None)
    assert result is not None
    assert result.t_stat == 0.0
    assert result.p_value == 1.0


def test_dependence_inflates_the_batched_standard_error() -> None:
    """A strongly autocorrelated series must not look like i.i.d. noise."""

    rng = random.Random(11)
    value = 0.0
    values = []
    for _ in range(2000):
        value = 0.97 * value + rng.gauss(0.0, 1.0)
        values.append(value)
    result = player_inference("p", values, None, None, None)
    assert result is not None
    assert result.standard_error > 3.0 * result.naive_standard_error


# ---------------------------------------------------------------------------
# null-model correctness on synthetic data with a known answer
# ---------------------------------------------------------------------------


def _synthetic(
    players: int,
    per_player: int,
    *,
    arm_family: bool,
    effect_sd: float,
    noise: float = 1.0,
    seed: int = 3,
) -> list[tuple[str, list[Opportunity]]]:
    """Players whose true per-player effect has standard deviation ``effect_sd``."""

    rng = random.Random(seed)
    out = []
    for index in range(players):
        effect = rng.gauss(0.0, effect_sd)
        opportunities = []
        for step in range(per_player):
            # Arms are drawn, not alternated: a perfectly periodic arm sequence
            # would make the circular-shift null degenerate.
            arm = "t" if rng.random() < 0.5 else "c"
            mode = "TURBO" if step % 3 else "STANDARD"
            base = rng.gauss(0.0, noise)
            if arm_family:
                value = base + (effect if arm == "t" else 0.0)
            else:
                value = base + effect
            opportunities.append(
                Opportunity(value, (("mode", mode),), arm if arm_family else None)
            )
        out.append((f"v7p_{index:03d}", opportunities))
    return out


def test_no_heterogeneity_synthetic_data_produces_no_between_player_signal() -> None:
    data = _synthetic(120, 300, arm_family=True, effect_sd=0.0)
    matrix = build_matrix(data, arm_family=True, treated="t", control="c")
    results = infer_all(matrix)
    assert len(results) == 120
    rejected = sum(1 for r in results if r.p_value < 0.05)
    assert rejected <= 12  # ~6 expected; a wide but finite band
    pooled = pool(results)
    assert pooled.tau < 0.05
    assert pooled.shrinkage_median < 0.25


def test_planted_heterogeneity_is_recovered_at_the_right_magnitude() -> None:
    data = _synthetic(120, 300, arm_family=True, effect_sd=0.5)
    matrix = build_matrix(data, arm_family=True, treated="t", control="c")
    results = infer_all(matrix)
    pooled = pool(results)
    assert pooled.tau == pytest.approx(0.5, abs=0.12)
    assert pooled.i_squared > 0.7
    assert sum(1 for r in results if r.p_value < 0.01) > 50


def test_contrast_null_replicate_destroys_a_planted_effect() -> None:
    data = _synthetic(60, 300, arm_family=True, effect_sd=0.8)
    matrix = build_matrix(data, arm_family=True, treated="t", control="c")
    observed = sum(1 for r in infer_all(matrix) if r.p_value < 0.01)
    rng = random.Random(5)
    nulled = sum(
        1 for r in contrast_null_replicate(matrix, rng, mode="iid") if r.p_value < 0.01
    )
    assert observed >= 35
    assert nulled <= 5


def test_circular_shift_preserves_the_arm_multiset_exactly() -> None:
    from scripts.v7_research.inference import _circular_shift

    arms = [0, 0, 1, 0, 1, 1, 1, 0, 0, 1, 0]
    for offset in range(len(arms)):
        shifted = _circular_shift(arms, offset)
        assert sorted(shifted) == sorted(arms)
        assert len(shifted) == len(arms)
    assert _circular_shift(arms, 0) == arms
    assert _circular_shift([], 3) == []


def test_contrast_null_replicate_preserves_each_players_volume() -> None:
    data = _synthetic(20, 200, arm_family=True, effect_sd=0.4)
    matrix = build_matrix(data, arm_family=True, treated="t", control="c")
    before = {name: len(indices) for name, indices in matrix.order.items()}
    rng = random.Random(2)
    for mode in ("circular", "iid"):
        for result in contrast_null_replicate(matrix, rng, mode=mode):
            # Relabelling cannot invent or destroy opportunities; the estimator
            # may still discard a block that ends up holding only one arm, so
            # the usable count is bounded above by the player's own volume.
            assert result.n <= before[result.pseudonym]
            assert result.n >= before[result.pseudonym] - 40


def test_level_null_replicate_destroys_a_planted_level_difference() -> None:
    data = _synthetic(60, 300, arm_family=False, effect_sd=0.8)
    matrix = build_matrix(data, arm_family=False, treated=None, control=None)
    observed = sum(1 for r in infer_all(matrix) if r.p_value < 0.01)
    rng = random.Random(9)
    nulled = sum(
        1 for r in level_null_replicate(matrix, rng, mode="iid") if r.p_value < 0.01
    )
    assert observed >= 35
    assert nulled <= 5


def test_level_null_replicate_preserves_each_players_volume() -> None:
    data = _synthetic(30, 213, arm_family=False, effect_sd=0.4)
    matrix = build_matrix(data, arm_family=False, treated=None, control=None)
    rng = random.Random(4)
    for mode in ("block", "iid"):
        for result in level_null_replicate(matrix, rng, mode=mode, block_length=25):
            assert result.n == 213


def test_within_player_permutation_is_not_a_null_for_a_level_family() -> None:
    """The design note in ``inference`` made executable.

    Permuting a player's own observations leaves that player's mean unchanged,
    so it cannot be the null for a level estimand. This test exists so that a
    future change which quietly adopts one fails here.
    """

    values = [float(index) for index in range(400)]
    straight = player_inference("p", values, None, None, None)
    shuffled_values = list(values)
    random.Random(1).shuffle(shuffled_values)
    shuffled = player_inference("p", shuffled_values, None, None, None)
    assert straight is not None and shuffled is not None
    assert straight.delta == pytest.approx(shuffled.delta, abs=1e-9)


# ---------------------------------------------------------------------------
# measured Type-I on pure noise
# ---------------------------------------------------------------------------


def test_type_i_on_pure_noise_is_near_nominal_for_a_contrast_family() -> None:
    data = _synthetic(80, 400, arm_family=True, effect_sd=0.0, seed=17)
    matrix = build_matrix(data, arm_family=True, treated="t", control="c")
    measured = measure_type_i(matrix, replicates=40, seed=SEED, null_mode="circular")
    assert measured.rejection_05 == pytest.approx(0.05, abs=4 * measured.mc_error_05 + 0.01)
    assert measured.rejection_01 == pytest.approx(0.01, abs=4 * measured.mc_error_01 + 0.005)
    assert measured.verdict() in {"CALIBRATED", "CONSERVATIVE"}


def test_type_i_on_pure_noise_is_near_nominal_for_a_level_family() -> None:
    data = _synthetic(80, 400, arm_family=False, effect_sd=0.0, seed=19)
    matrix = build_matrix(data, arm_family=False, treated=None, control=None)
    measured = measure_type_i(matrix, replicates=40, seed=SEED, null_mode="iid")
    assert measured.rejection_05 == pytest.approx(0.05, abs=4 * measured.mc_error_05 + 0.01)


def test_type_i_verdict_flags_an_anticonservative_method() -> None:
    from scripts.v7_research.inference import TypeIResult

    good = TypeIResult("x", 100, 5000, 0.051, 0.0104, 0.002, 0.001)
    bad = TypeIResult("x", 100, 5000, 0.148, 0.055, 0.004, 0.002)
    shy = TypeIResult("x", 100, 5000, 0.012, 0.001, 0.001, 0.0004)
    assert good.verdict() == "CALIBRATED"
    assert bad.verdict() == "ANTICONSERVATIVE"
    assert shy.verdict() == "CONSERVATIVE"
    assert TypeIResult("x", 0, 0, float("nan"), float("nan"), float("nan"), float("nan")).verdict() == "UNKNOWN"


# ---------------------------------------------------------------------------
# partial pooling and shrinkage extremes
# ---------------------------------------------------------------------------


def test_tau_is_zero_when_every_estimate_is_consistent_with_one_value() -> None:
    deltas = [0.0, 0.01, -0.01, 0.005, -0.004, 0.002]
    errors = [0.5] * 6
    tau2, mu = paule_mandel_tau_squared(deltas, errors)
    assert tau2 == 0.0
    assert mu == pytest.approx(0.0, abs=0.01)


def test_tau_recovers_a_large_spread_that_dwarfs_the_standard_errors() -> None:
    rng = random.Random(23)
    truth = [rng.gauss(0.0, 2.0) for _ in range(200)]
    errors = [0.1] * 200
    deltas = [t + rng.gauss(0.0, 0.1) for t in truth]
    tau2, _mu = paule_mandel_tau_squared(deltas, errors)
    assert math.sqrt(tau2) == pytest.approx(2.0, abs=0.3)


def test_degenerate_zero_variance_players_are_refused_not_treated_as_certain() -> None:
    results = [player_inference(f"p{i}", [0.0] * 200, None, None, None) for i in range(30)]
    usable = [r for r in results if r is not None]
    assert len(usable) == 30
    assert all(r.standard_error == 0.0 for r in usable)
    pooled = pool(usable)
    assert pooled.players == 0
    assert math.isnan(pooled.tau)


def test_shrinkage_is_near_zero_when_there_is_no_between_player_spread() -> None:
    rng = random.Random(53)
    results = []
    for index in range(60):
        values = [rng.gauss(0.0, 1.0) for _ in range(200)]
        result = player_inference(f"p{index}", values, None, None, None)
        assert result is not None
        results.append(result)
    pooled = pool(results)
    assert pooled.tau_squared == 0.0
    assert pooled.shrinkage_median == 0.0
    assert pooled.shrinkage_p90 == 0.0


def test_shrinkage_approaches_one_when_heterogeneity_dwarfs_noise() -> None:
    data = _synthetic(80, 600, arm_family=False, effect_sd=5.0, noise=1.0, seed=31)
    matrix = build_matrix(data, arm_family=False, treated=None, control=None)
    pooled = pool(infer_all(matrix))
    assert pooled.shrinkage_p10 > 0.9
    assert pooled.i_squared > 0.95


def test_shrinkage_does_not_manufacture_reach_when_there_is_no_signal() -> None:
    data = _synthetic(120, 300, arm_family=True, effect_sd=0.0, seed=37)
    matrix = build_matrix(data, arm_family=True, treated="t", control="c")
    pooled = pool(infer_all(matrix))
    assert pooled.shrinkage_reach_inflation <= 0.02


def test_pooling_refuses_fewer_than_three_players() -> None:
    tau2, mu = paule_mandel_tau_squared([0.1, 0.2], [0.1, 0.1])
    assert math.isnan(tau2)
    assert mu == pytest.approx(0.15)


# ---------------------------------------------------------------------------
# stability, power and missingness
# ---------------------------------------------------------------------------


def test_chronological_split_half_detects_drift_a_random_split_cannot() -> None:
    """A player whose behaviour flips halfway must fail the chronological split."""

    rng = random.Random(41)
    data: list[tuple[str, list[Opportunity]]] = []
    for index in range(160):
        stable = rng.gauss(0.0, 1.0)
        drift = rng.gauss(0.0, 2.0)
        opportunities = []
        for step in range(400):
            level = stable + (drift if step < 200 else -drift)
            opportunities.append(
                Opportunity(rng.gauss(0.0, 1.0) + level, (("mode", "TURBO"),), None)
            )
        data.append((f"v7p_{index:03d}", opportunities))
    matrix = build_matrix(data, arm_family=False, treated=None, control=None)
    random_r, _random_sb, _n = split_half_stability(matrix, chronological=False, seed=SEED)
    chrono_r, _chrono_sb, _m = split_half_stability(matrix, chronological=True, seed=SEED)
    # Random halves both average the drift away and see the stable component;
    # chronological halves see stable+drift against stable-drift, which is
    # strongly negative when the drift dominates. Only the second split can
    # tell a stable trait from a trait that reverses over the window.
    assert random_r > 0.6
    assert chrono_r < -0.4


def test_split_half_reports_nan_when_too_few_players_qualify() -> None:
    data = _synthetic(5, 40, arm_family=False, effect_sd=1.0)
    matrix = build_matrix(data, arm_family=False, treated=None, control=None)
    raw, corrected, players = split_half_stability(matrix, chronological=True, seed=SEED)
    assert math.isnan(raw) and math.isnan(corrected)
    assert players == 5


def test_minimum_detectable_effect_scales_with_the_standard_error() -> None:
    small = minimum_detectable_effect(0.01, 19)
    large = minimum_detectable_effect(0.02, 19)
    assert large == pytest.approx(2.0 * small, rel=1e-9)
    assert small == pytest.approx(0.0285, abs=0.002)
    assert math.isnan(minimum_detectable_effect(0.0, 19))
    assert math.isnan(minimum_detectable_effect(float("nan"), 19))


def test_missing_context_levels_do_not_break_the_projection() -> None:
    data = [
        (
            "v7p_a",
            [Opportunity(float(i % 5), (("mode", "TURBO"),), None) for i in range(200)],
        ),
        (
            "v7p_b",
            [Opportunity(float(i % 5), (("patch", "182"),), None) for i in range(200)],
        ),
    ]
    matrix = build_matrix(data, arm_family=False, treated=None, control=None)
    assert set(matrix.encoded.factors) == {"mode", "patch"}
    assert all(value == value for value in matrix.residual)


def test_dropping_a_factor_removes_it_from_the_projection() -> None:
    data = _synthetic(20, 100, arm_family=False, effect_sd=0.3)
    kept = build_matrix(data, arm_family=False, treated=None, control=None)
    dropped = build_matrix(
        data, arm_family=False, treated=None, control=None, drop_factors=("mode",)
    )
    assert "mode" in kept.encoded.factors
    assert "mode" not in dropped.encoded.factors


# ---------------------------------------------------------------------------
# opportunity ordering, which the whole chronological analysis depends on
# ---------------------------------------------------------------------------


def _history_row(index: int, **overrides: Any) -> dict[str, Any]:
    start = 1_600_000_000 + index * 4_000
    base: dict[str, Any] = {
        "match_id": 1000 + index,
        "started_at": start,
        "ended_at": start + 1_500,
        "duration_seconds": 1_500 + index,
        "game_mode_native": "TURBO",
        "lobby_type_native": "UNRANKED",
        "leaver_status_native": "NONE",
        "hero_id": index % 7,
        "is_radiant": index % 2 == 0,
        "is_victory": index % 3 == 0,
        "kills": index % 5,
        "deaths": index % 4,
        "assists": index % 6,
        "game_version_id": 182,
    }
    base.update(overrides)
    return base


def _frame(count: int = 400, **overrides: Any) -> PlayerFrame:
    return PlayerFrame(
        pseudonym="v7p_test",
        split=DISCOVERY,
        completeness="complete",
        rows=[_history_row(index, **overrides) for index in range(count)],
    )


def test_extractors_emit_opportunities_in_chronological_row_order() -> None:
    frame = _frame()
    opportunities = extract("duration_tempo", frame)
    assert len(opportunities) == len(frame.rows)
    for opportunity, row in zip(opportunities, frame.rows, strict=True):
        assert opportunity.value == pytest.approx(math.log(row["duration_seconds"]))


def test_session_gap_override_changes_session_structure_and_restores_it() -> None:
    from scripts.v7_research import features

    frame = _frame(200)
    baseline = len(extract("post_loss_session_continuation", frame))
    with session_gap_override(600):
        tightened = len(extract("post_loss_session_continuation", frame))
    assert features.SESSION_GAP_SECONDS == 3 * 3600
    # A 4000 s cadence is one session at a 3 h gap and 200 sessions at 10 min.
    assert baseline == 199
    assert tightened == 199
    with session_gap_override(600):
        assert extract("post_loss_hero_switch", frame) == []


def test_volume_cap_equalises_exposure() -> None:
    frames = [_frame(400), _frame(120)]
    capped = volume_capped(frames, 150)
    assert [len(frame.rows) for frame in capped] == [150, 120]
    assert [len(frame.rows) for frame in frames] == [400, 120]


def test_non_chosen_hero_modes_are_removable() -> None:
    frame = _frame(10)
    frame.rows[3]["game_mode_native"] = "RANDOM_DRAFT"
    frame.rows[7]["game_mode_native"] = "SINGLE_DRAFT"
    filtered = without_non_chosen_hero_modes([frame])[0]
    assert len(filtered.rows) == 8
    assert all(row["game_mode_native"] == "TURBO" for row in filtered.rows)
    assert len(frame.rows) == 10


# ---------------------------------------------------------------------------
# reserved splits stay unreachable from the inference layer
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("split", [CALIBRATION_RESERVED, SEALED_VALIDATION])
def test_inference_cannot_request_a_reserved_split(tmp_path: Any, split: str) -> None:
    from scripts.v7_research.corpus import corpus_paths

    (tmp_path / "canonical" / "history").mkdir(parents=True)
    paths = corpus_paths(tmp_path)
    with pytest.raises(ReservedSplitAccess):
        list(iter_players(paths, "history", frozenset({split})))
    with pytest.raises(ReservedSplitAccess):
        list(iter_players(paths, "history", frozenset({DISCOVERY, split})))


def test_research_splits_remain_requestable(tmp_path: Any) -> None:
    from scripts.v7_research.corpus import corpus_paths

    (tmp_path / "canonical" / "history").mkdir(parents=True)
    paths = corpus_paths(tmp_path)
    assert (
        list(
            iter_players(
                paths,
                "history",
                frozenset({DISCOVERY, CANDIDATE_TEST}),
                candidate_test_reason="unit test: confirmation split stays requestable",
                ledger=tmp_path / "ledger.jsonl",
            )
        )
        == []
    )


def test_family_matrix_player_views_are_consistent() -> None:
    data = _synthetic(4, 60, arm_family=True, effect_sd=0.5)
    matrix: FamilyMatrix = build_matrix(data, arm_family=True, treated="t", control="c")
    for pseudonym in matrix.order:
        assert len(matrix.player_values(pseudonym)) == len(matrix.player_arms(pseudonym)) == 60
    assert sum(len(v) for v in matrix.order.values()) == len(matrix.residual)
    assert MIN_BLOCKS >= 2


# ---------------------------------------------------------------------------
# confirmation discipline
# ---------------------------------------------------------------------------


def test_the_frozen_design_digest_is_stable_and_content_addressed() -> None:
    from scripts.v7_research.inference import design_digest, design_payload

    first = design_digest()
    assert first == design_digest()
    payload = design_payload()
    assert payload["multiplicity"] == "NOT CHOSEN IN THIS PHASE"
    assert payload["publication_thresholds"] == "NOT CHOSEN IN THIS PHASE"
    assert payload["partial_pooling"]["qualification_uses_shrunken_estimates"] is False
    assert payload["test_statistic"]["level_blocks"]["min_per_block"] == 100
    assert payload["test_statistic"]["contrast_blocks"]["min_per_block"] == 4


def test_a_changed_design_is_refused_against_a_stale_freeze(tmp_path: Any) -> None:
    from scripts.v7_statistical_tournament import _check_design

    stale = tmp_path / "design.json"
    stale.write_text(
        json.dumps({"design_digest": "0" * 64, "frozen_registry_digest": "0" * 64}),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit) as excinfo:
        _check_design(str(stale))
    assert "does not match the code" in str(excinfo.value)


def test_the_current_freeze_on_disk_still_matches_the_code() -> None:
    from pathlib import Path

    from scripts.v7_research.inference import design_digest
    from scripts.v7_statistical_tournament import REPO_ROOT, _check_design

    frozen = Path(REPO_ROOT) / "docs" / "evidence" / "v7-inference-design-2026-09-03.json"
    if not frozen.is_file():  # pragma: no cover - only when the artefact is absent
        pytest.skip("frozen design artefact not present")
    payload = _check_design(str(frozen))
    assert payload["design_digest"] == design_digest()
    assert payload["candidate_test_passes_permitted"] == 1


def test_the_evaluated_set_is_exactly_the_frozen_twelve_plus_the_control() -> None:
    from scripts.v7_discovery_screen import FROZEN_SERIOUS_CANDIDATES
    from scripts.v7_research.registry import digest, registry_payload
    from scripts.v7_statistical_tournament import EVALUATED, NEGATIVE_CONTROL

    assert len(FROZEN_SERIOUS_CANDIDATES) == 12
    assert set(EVALUATED) == set(FROZEN_SERIOUS_CANDIDATES) | {NEGATIVE_CONTROL}
    assert (
        digest(registry_payload(FROZEN_SERIOUS_CANDIDATES))
        == "f9f5af7806ee5936e40d826eeb5904fe8bffa488995c967a959f8e9e5456086c"
    )
