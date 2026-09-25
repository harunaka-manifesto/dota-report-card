from __future__ import annotations

import math
import random

import pytest
from report_card.player_analysis_v7.research.ranking import (
    RANKING_MODEL_VERSION,
    Interval,
    PlayerDimension,
    PopulationObservation,
    RankedFinding,
    ShrunkEstimate,
    direction_of,
    population_parameters,
    rank_player,
    reliability,
    score,
    select_stratified,
    shrunk_estimate,
    z,
)

# Regression anchors from docs/evidence/v7-finding-ranking-model-2026-09-05.md
# section 3. The published table rounds tau/SE/D to 3-4 significant figures,
# so reproduction is checked to within 1e-3 rather than exact equality against
# the rounded 3-decimal headline figure.
DURATION_TEMPO_R = 0.973
POST_LOSS_SESSION_CONTINUATION_R = 0.713
SIDE_SENSITIVITY_R = 0.108


# ---------------------------------------------------------------------------
# version marker
# ---------------------------------------------------------------------------


def test_ranking_model_version_is_a_nonempty_string() -> None:
    assert isinstance(RANKING_MODEL_VERSION, str)
    assert RANKING_MODEL_VERSION


# ---------------------------------------------------------------------------
# 2.1 z
# ---------------------------------------------------------------------------


def test_z_is_position_in_population_standard_deviations() -> None:
    assert z(1.5, 1.0, 0.5) == pytest.approx(1.0)
    assert z(0.5, 1.0, 0.5) == pytest.approx(-1.0)
    assert z(1.0, 1.0, 0.5) == pytest.approx(0.0)


@pytest.mark.parametrize("tau", [0.0, -1.0])
def test_z_guards_non_positive_tau(tau: float) -> None:
    assert z(5.0, 1.0, tau) == 0.0


# ---------------------------------------------------------------------------
# direction
# ---------------------------------------------------------------------------


def test_direction_labels() -> None:
    assert direction_of(2.0) == "positive"
    assert direction_of(-2.0) == "negative"
    assert direction_of(0.0) == "neutral"


# ---------------------------------------------------------------------------
# 2.2 reliability
# ---------------------------------------------------------------------------


def test_reliability_reproduces_duration_tempo_anchor() -> None:
    r = reliability(se=0.0097, tau=0.0944, dependence_inflation=2.56)
    assert r == pytest.approx(DURATION_TEMPO_R, abs=1e-3)


def test_reliability_reproduces_post_loss_session_continuation_anchor() -> None:
    r = reliability(se=0.0377, tau=0.0977, dependence_inflation=2.70)
    assert r == pytest.approx(POST_LOSS_SESSION_CONTINUATION_R, abs=1e-3)


def test_reliability_is_near_zero_on_the_side_sensitivity_negative_control() -> None:
    # side_sensitivity: no real between-player signal (tau small relative to
    # SE). The spec's own published figure for this exact family is a
    # dependence-corrected r = 0.108; the tau/SE/D that produced it were not
    # given verbatim in this task, so this test picks representative inputs
    # with the same tau << SE shape and checks the qualitative property the
    # spec asserts: reliability collapses toward zero, well under the
    # SIDE_SENSITIVITY_R reference, rather than pinning an exact value.
    r = reliability(se=0.09, tau=0.03, dependence_inflation=1.2)
    assert r < SIDE_SENSITIVITY_R
    assert r < 0.15


def test_reliability_is_zero_when_tau_is_zero() -> None:
    assert reliability(se=0.05, tau=0.0, dependence_inflation=2.0) == 0.0


def test_reliability_approaches_one_when_se_is_tiny() -> None:
    assert reliability(se=1e-9, tau=1.0, dependence_inflation=1.0) == pytest.approx(1.0, abs=1e-6)


def test_reliability_is_clamped_to_unit_interval() -> None:
    assert 0.0 <= reliability(se=0.0, tau=1.0, dependence_inflation=1.0) <= 1.0
    assert 0.0 <= reliability(se=1e6, tau=1e-6, dependence_inflation=1.0) <= 1.0


def test_ignoring_dependence_inflation_overstates_reliability() -> None:
    naive = reliability(se=0.0097, tau=0.0944, dependence_inflation=1.0)
    corrected = reliability(se=0.0097, tau=0.0944, dependence_inflation=2.56)
    assert naive > corrected
    # matches the spec's own worked table: naive 0.989, corrected 0.973
    assert naive == pytest.approx(0.989, abs=1e-3)


# ---------------------------------------------------------------------------
# 2.3 score
# ---------------------------------------------------------------------------


def test_score_is_a_magnitude_regardless_of_sign_of_z() -> None:
    positive = score(2.0, 0.5)
    negative = score(-2.0, 0.5)
    assert positive == negative == pytest.approx(1.0)


def test_score_is_zero_when_reliability_is_zero() -> None:
    assert score(100.0, 0.0) == 0.0


def test_score_is_zero_when_z_is_zero() -> None:
    assert score(0.0, 0.9) == 0.0


def test_low_reliability_dimension_cannot_reach_top_of_list_on_noise() -> None:
    # A dimension with a huge raw z but negligible reliability (tau -> 0,
    # relatively) must not outscore a modest, well-measured dimension.
    noisy_z = z(delta_hat=10.0, mu=0.0, tau=0.05)
    noisy_r = reliability(se=5.0, tau=0.05, dependence_inflation=1.0)
    noisy_score = score(noisy_z, noisy_r)

    modest_z = z(delta_hat=1.0, mu=0.0, tau=1.0)
    modest_r = reliability(se=0.1, tau=1.0, dependence_inflation=1.0)
    modest_score = score(modest_z, modest_r)

    assert noisy_r < 0.01
    assert noisy_score < modest_score


# ---------------------------------------------------------------------------
# 2.2 shrunk_estimate
# ---------------------------------------------------------------------------


def test_shrunk_estimate_is_a_weighted_average_toward_the_population_mean() -> None:
    estimate = shrunk_estimate(delta_hat=2.0, mu=0.0, reliability_value=0.25, tau=1.0)
    assert estimate.point == pytest.approx(0.5)


def test_shrunk_estimate_at_full_reliability_recovers_delta_hat() -> None:
    estimate = shrunk_estimate(delta_hat=3.0, mu=0.0, reliability_value=1.0, tau=1.0)
    assert estimate.point == pytest.approx(3.0)
    assert estimate.interval.lower == pytest.approx(3.0)
    assert estimate.interval.upper == pytest.approx(3.0)


def test_shrunk_estimate_at_zero_reliability_recovers_the_population_mean() -> None:
    estimate = shrunk_estimate(delta_hat=3.0, mu=1.0, reliability_value=0.0, tau=2.0)
    assert estimate.point == pytest.approx(1.0)
    # posterior variance collapses to the full prior variance at r=0
    assert estimate.interval.upper - estimate.point == pytest.approx(1.959964 * 2.0)


def test_shrunk_estimate_interval_is_symmetric_and_documents_its_coverage() -> None:
    estimate = shrunk_estimate(delta_hat=2.0, mu=0.0, reliability_value=0.5, tau=1.0)
    assert estimate.interval.coverage == pytest.approx(0.95)
    span_below = estimate.point - estimate.interval.lower
    span_above = estimate.interval.upper - estimate.point
    assert span_below == pytest.approx(span_above)
    assert isinstance(estimate, ShrunkEstimate)
    assert isinstance(estimate.interval, Interval)


# ---------------------------------------------------------------------------
# 5. rank_player
# ---------------------------------------------------------------------------


def _dimension(
    key: str,
    section: str,
    delta_hat: float,
    se: float,
    tau: float,
    mu: float = 0.0,
    dependence_inflation: float = 1.5,
    sample_size: int = 400,
) -> PlayerDimension:
    return PlayerDimension(
        key=key,
        section=section,
        delta_hat=delta_hat,
        se=se,
        sample_size=sample_size,
        mu=mu,
        tau=tau,
        dependence_inflation=dependence_inflation,
    )


def test_rank_player_sorts_by_descending_score() -> None:
    dims = [
        _dimension("weak", "what_costs_you", delta_hat=0.5, se=0.5, tau=0.05),
        _dimension("strong", "what_is_good", delta_hat=3.0, se=0.05, tau=1.0),
        _dimension("mid", "loss_response", delta_hat=1.5, se=0.2, tau=0.8),
    ]
    ranked = rank_player(dims)
    assert [f.key for f in ranked] == sorted(
        [f.key for f in ranked], key=lambda k: -next(r.score for r in ranked if r.key == k)
    )
    scores = [f.score for f in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rank_player_carries_all_required_fields() -> None:
    dims = [_dimension("hero_novelty", "what_is_good", delta_hat=1.0, se=0.1, tau=0.5)]
    (finding,) = rank_player(dims)
    assert isinstance(finding, RankedFinding)
    assert finding.key == "hero_novelty"
    assert finding.section == "what_is_good"
    assert finding.direction in {"positive", "negative", "neutral"}
    assert finding.sample_size == 400
    assert isinstance(finding.shrunk_estimate, ShrunkEstimate)


def test_rank_player_on_empty_input_returns_empty_list() -> None:
    assert rank_player([]) == []


def test_rank_player_on_single_dimension() -> None:
    dims = [_dimension("only", "what_is_good", delta_hat=1.0, se=0.1, tau=0.5)]
    ranked = rank_player(dims)
    assert len(ranked) == 1
    assert ranked[0].key == "only"


def test_rank_player_ties_break_by_key_ascending_deterministically() -> None:
    dims = [
        _dimension("zulu", "s", delta_hat=1.0, se=0.1, tau=1.0),
        _dimension("alpha", "s", delta_hat=1.0, se=0.1, tau=1.0),
    ]
    ranked = rank_player(dims)
    assert [f.key for f in ranked] == ["alpha", "zulu"]
    # order-independence: reversing the input does not change the outcome
    reversed_ranked = rank_player(list(reversed(dims)))
    assert [f.key for f in reversed_ranked] == ["alpha", "zulu"]


# ---------------------------------------------------------------------------
# 6. select_stratified
# ---------------------------------------------------------------------------


def _finding(key: str, section: str, s: float) -> RankedFinding:
    estimate = ShrunkEstimate(point=0.0, interval=Interval(0.0, 0.0, 0.95))
    return RankedFinding(
        key=key,
        section=section,
        direction="positive",
        z=1.0,
        reliability=1.0,
        score=s,
        shrunk_estimate=estimate,
        sample_size=100,
    )


def test_select_stratified_fills_every_section_before_doubling_up() -> None:
    ranked = [
        _finding("a1", "A", 0.9),
        _finding("a2", "A", 0.8),
        _finding("a3", "A", 0.7),
        _finding("b1", "B", 0.1),
    ]
    selected = select_stratified(ranked, sections=["A", "B", "C"], slots=2)
    keys = {f.key for f in selected}
    # B's only Finding must be included even though every A Finding outscores
    # it, because slots (2) matches the section count that has candidates.
    assert "b1" in keys
    assert "a1" in keys
    assert len(selected) == 2


def test_select_stratified_fills_remaining_slots_globally_by_score() -> None:
    ranked = [
        _finding("a1", "A", 0.9),
        _finding("a2", "A", 0.8),
        _finding("a3", "A", 0.7),
        _finding("b1", "B", 0.1),
    ]
    selected = select_stratified(ranked, sections=["A", "B"], slots=3)
    keys = [f.key for f in selected]
    assert set(keys) == {"a1", "b1", "a2"}


def test_select_stratified_more_sections_than_slots() -> None:
    ranked = [
        _finding("a1", "A", 0.9),
        _finding("b1", "B", 0.8),
        _finding("c1", "C", 0.7),
    ]
    selected = select_stratified(ranked, sections=["A", "B", "C"], slots=1)
    assert len(selected) == 1
    assert selected[0].key == "a1"


def test_select_stratified_more_slots_than_dimensions() -> None:
    ranked = [_finding("a1", "A", 0.9), _finding("b1", "B", 0.5)]
    selected = select_stratified(ranked, sections=["A", "B", "C"], slots=10)
    assert len(selected) == 2
    assert {f.key for f in selected} == {"a1", "b1"}


def test_select_stratified_on_empty_input() -> None:
    assert select_stratified([], sections=["A", "B"], slots=3) == []


def test_select_stratified_zero_slots() -> None:
    ranked = [_finding("a1", "A", 0.9)]
    assert select_stratified(ranked, sections=["A"], slots=0) == []


def test_select_stratified_is_stable_across_input_orderings() -> None:
    ranked = [
        _finding("a1", "A", 0.9),
        _finding("a2", "A", 0.8),
        _finding("b1", "B", 0.85),
        _finding("b2", "B", 0.2),
    ]
    forward = select_stratified(ranked, sections=["A", "B"], slots=3)
    backward = select_stratified(list(reversed(ranked)), sections=["A", "B"], slots=3)
    assert [f.key for f in forward] == [f.key for f in backward]


def test_select_stratified_tie_break_prefers_earlier_section_in_phase_one() -> None:
    ranked = [_finding("zulu", "A", 0.5), _finding("alpha", "B", 0.5)]
    # Both candidates tie on score. Phase 1 walks `sections` in the order
    # given, so with a single slot the section listed first wins, regardless
    # of the key. This is deterministic (a function of `sections`, not of
    # input order or a coin flip), but callers should list sections in their
    # own priority order to get the tie-break they want.
    selected = select_stratified(ranked, sections=["A", "B"], slots=1)
    assert len(selected) == 1
    assert selected[0].key == "zulu"

    selected_reordered = select_stratified(ranked, sections=["B", "A"], slots=1)
    assert selected_reordered[0].key == "alpha"


def test_select_stratified_phase_two_tie_break_is_key_ascending() -> None:
    # Once every section has its slot, phase 2 falls back to the same
    # (score desc, key asc) order as rank_player.
    ranked = [_finding("zulu", "A", 0.5), _finding("alpha", "A", 0.5)]
    selected = select_stratified(ranked, sections=["A"], slots=2)
    assert [f.key for f in selected] == ["alpha", "zulu"]


# ---------------------------------------------------------------------------
# 7. population_parameters
# ---------------------------------------------------------------------------


def test_population_parameters_recovers_a_known_tau_from_simulated_data() -> None:
    rng = random.Random(20260905)
    true_mu = 0.4
    true_tau = 0.2
    se = 0.05
    dependence_inflation = 1.0
    observations = []
    for _ in range(4000):
        true_delta = rng.gauss(true_mu, true_tau)
        measured = rng.gauss(true_delta, se * math.sqrt(dependence_inflation))
        observations.append(PopulationObservation(measured, se, dependence_inflation))

    mu, tau = population_parameters(observations)
    assert mu == pytest.approx(true_mu, abs=0.02)
    assert tau == pytest.approx(true_tau, abs=0.02)


def test_population_parameters_clamps_to_zero_when_measurement_error_dominates() -> None:
    # All players cluster tightly (no real between-player spread) but each
    # measurement carries large SE * D — the naive sd(delta_hat) is small,
    # but even that small variance must not exceed what measurement error
    # alone explains without being clamped to a floor of zero.
    observations = [
        PopulationObservation(delta_hat=0.0001, se=1.0, dependence_inflation=2.0),
        PopulationObservation(delta_hat=-0.0001, se=1.0, dependence_inflation=2.0),
        PopulationObservation(delta_hat=0.0002, se=1.0, dependence_inflation=2.0),
    ]
    mu, tau = population_parameters(observations)
    assert tau == 0.0
    assert mu == pytest.approx(0.0, abs=1e-3)


def test_population_parameters_on_empty_input_returns_nan() -> None:
    mu, tau = population_parameters([])
    assert math.isnan(mu)
    assert math.isnan(tau)


def test_population_parameters_on_single_observation() -> None:
    mu, tau = population_parameters([PopulationObservation(1.0, 0.1, 1.0)])
    assert mu == pytest.approx(1.0)
    assert tau == 0.0


# ---------------------------------------------------------------------------
# end-to-end: the negative control cannot reach the top of a player's list
# ---------------------------------------------------------------------------


def test_side_sensitivity_style_dimension_is_outranked_by_real_signal() -> None:
    dims = [
        _dimension(
            "side_sensitivity",
            "what_costs_you",
            delta_hat=0.2,  # a few SEs from zero, plausible for this SE...
            se=0.09,
            tau=0.03,  # ...but on a dimension with almost no population spread
            dependence_inflation=1.2,
        ),
        _dimension(
            "duration_tempo",
            "what_is_good",
            delta_hat=0.15,
            se=0.0097,
            tau=0.0944,
            dependence_inflation=2.56,
        ),
    ]
    ranked = rank_player(dims)
    assert ranked[0].key == "duration_tempo"
    assert ranked[-1].key == "side_sensitivity"
    assert ranked[-1].reliability < 0.15


# ---------------------------------------------------------------------------
# Regression anchors against the published tournament output
# ---------------------------------------------------------------------------


def test_reliability_reproduces_every_published_family() -> None:
    """Anchor the implementation to the real measured variance components.

    Two hand-picked values can drift into agreement by luck; all thirteen
    families cannot. The inputs are read from the committed tournament output
    at full precision, so this also guards against someone silently editing
    that artefact.
    """

    import json
    from pathlib import Path

    payload = json.loads(
        (
            Path(__file__).resolve().parents[3]
            / "docs/evidence/v7-statistical-tournament-discovery-2026-09-03.json"
        ).read_text(encoding="utf-8")
    )
    expected = {
        "duration_tempo": 0.9734,
        "purchase_tempo": 0.9228,
        "position_flexibility": 0.9006,
        "fight_timing_centroid": 0.8512,
        "post_loss_session_continuation": 0.7131,
        "hero_novelty": 0.6883,
        "post_loss_hero_switch": 0.6720,
        "post_loss_requeue_latency": 0.6460,
        "lead_retention": 0.5364,
        "transfer_risk": 0.2913,
        "transfer_activity": 0.2813,
        "lane_recovery_participation": 0.2684,
        # The negative control: a Finding built on which side of the map the
        # player was assigned, which nobody controls. It must collapse.
        "side_sensitivity": 0.1075,
    }
    seen = 0
    for evaluation in payload["evaluations"]:
        family = evaluation["family"]
        if family not in expected:
            continue
        seen += 1
        got = reliability(
            evaluation["se_median"],
            evaluation["tau"],
            evaluation["variance_ratio"].get("100") or 1.0,
        )
        assert got == pytest.approx(expected[family], abs=5e-5), family
    assert seen == len(expected)


def test_the_negative_control_cannot_outrank_a_measured_dimension() -> None:
    """Reliability, not effect size, is what stops noise reaching the top.

    The control is given a much larger raw z than the well-measured dimension
    and must still lose, because almost none of its deviation is real.
    """

    control = score(z_value=3.0, reliability_value=0.1075)
    measured = score(z_value=1.0, reliability_value=0.9734)
    assert control < measured
