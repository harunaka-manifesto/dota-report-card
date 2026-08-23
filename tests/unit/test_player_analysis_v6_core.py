from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.player_analysis_v6 import (
    PUBLIC_ELEMENT_KEYS,
    STORY_BEAT_KEYS,
    BaselineCell,
    BaselineContext,
    BaselineResolver,
    FreeCostLedger,
    InsufficientHistoryError,
    analyze_free_dna_v6,
    benjamini_hochberg,
    build_diagnostic_questions,
    build_share_candidates,
    clustered_bootstrap,
    compare_consistency_signals,
    compare_transfer_signals,
    compute_elements,
    finishing_share,
    qualify_family,
    shannon_effective_count,
)
from app.player_analysis_v6 import post_loss as post_loss_module
from app.player_analysis_v6 import statistics as statistics_module
from app.player_analysis_v6.elements import _transfer_direction
from app.player_analysis_v6.hero_portfolio import load_v6_hero_taxonomy
from app.player_analysis_v6.post_loss import compute_post_loss_response
from app.player_analysis_v6.session_drift import session_position_buckets


def _match(index: int, *, session: int | None = None, hero: int | None = None) -> SimpleNamespace:
    start = 1_700_000_000 + index * 7_200
    return SimpleNamespace(
        match_id=index,
        hero_id=hero or (index % 4) + 1,
        started_at=start,
        duration_seconds=1_800,
        kills=3 + index % 3,
        deaths=2 + index % 2,
        assists=5 + index % 4,
        won=index % 2 == 0,
        role_hint="mid",
        session_id=f"session-{session or index}",
    )


def test_shannon_and_zero_event_formulas() -> None:
    assert shannon_effective_count({"a": 5, "b": 5}) == pytest.approx(2.0)
    assert finishing_share(0, 0) is None
    assert finishing_share(2, 2) == pytest.approx(0.5)


def test_cluster_bootstrap_is_session_clustered_and_deterministic() -> None:
    first = clustered_bootstrap({"s1": [0, 0, 0], "s2": [1, 1, 1]}, iterations=200, seed=4)
    second = clustered_bootstrap({"s1": [0, 0, 0], "s2": [1, 1, 1]}, iterations=200, seed=4)
    assert first == second
    assert first.independent_sessions == 2
    assert first.sample_size == 6


def test_invalid_bca_transform_falls_back_instead_of_inverting_interval() -> None:
    assert statistics_module._bca_probabilities(0.025, -3.0, -0.96) is None
    valid = statistics_module._bca_probabilities(0.025, 0.0, 0.0)
    assert valid == pytest.approx((0.025, 0.975))


def test_baseline_fallback_requires_counts() -> None:
    cells = [
        BaselineCell("patch+hero+lane", patch="7.41", hero_id=1, lane_context="mid", metrics={"m": 5}, match_count=100, distinct_players=50),
        BaselineCell("patch+hero", patch="7.41", hero_id=1, metrics={"m": 7}, match_count=200, distinct_players=50),
    ]
    resolved = BaselineResolver(cells).resolve(BaselineContext("7.41", 1, lane_context="mid"), "m")
    assert resolved.level == "patch+hero"
    assert resolved.value == 7


def test_mixed_transfer_and_consistency_remain_mixed_or_two_of_three() -> None:
    transfer = compare_transfer_signals({"outcome": 0.2, "activity": 0.2, "survival": -0.2})
    assert transfer.direction == "mixed"
    consistency = compare_consistency_signals({"outcome": "stable", "activity": "variable", "death_exposure": "stable"}, usable_sessions=12)
    assert consistency.direction == "stable"


def test_transfer_only_blocks_two_of_three_on_confident_opposition() -> None:
    directions = {"outcome": "positive", "activity": "positive", "survival": "negative"}
    assert _transfer_direction(
        directions,
        {"outcome": "positive", "activity": "positive", "survival": "neutral"},
    ) == "positive"
    assert _transfer_direction(
        directions,
        {"outcome": "positive", "activity": "positive", "survival": "negative"},
    ) == "mixed"


def test_bh_adjustment() -> None:
    assert benjamini_hochberg([0.01, 0.04, 0.2]) == pytest.approx((0.03, 0.06, 0.2))


def test_v6_report_contract_and_free_cost() -> None:
    matches = tuple(_match(index, session=index // 2) for index in range(60))
    report = analyze_free_dna_v6(matches, taxonomy_by_hero={1: ("teamfight",), 2: ("save",), 3: ("push",), 4: ("scaling",)})
    assert tuple(item.key for item in report.elements) == PUBLIC_ELEMENT_KEYS
    assert len(report.findings) == 5
    assert len(report.story) == 9
    assert tuple(item.key for item in report.story) == STORY_BEAT_KEYS
    assert sum(item.published for item in report.findings) <= 3
    assert report.cost == FreeCostLedger(history_reads=1)
    public = report.as_dict()
    assert not any("pos1" in repr(public).lower() for _ in [0])
    assert report.identity.evidence_refs
    story = {item.key: item for item in report.story}
    assert len(story["identity_reveal"].observed["elements"]) == 7
    assert story["pool_prediction"].observed["prediction"]["options"]
    assert story["hero_mirror"].observed["hero_mirror"]["heroes"]


def test_diagnostic_questions_and_share_candidates_are_gated() -> None:
    matches = tuple(_match(index, session=index // 2) for index in range(60))
    report = analyze_free_dna_v6(matches, taxonomy_by_hero={1: ("teamfight",), 2: ("save",), 3: ("push",), 4: ("scaling",)})
    assert len(build_diagnostic_questions(report.findings)) <= 3
    assert len(build_share_candidates(report.identity, report.findings)) == 3


def test_free_history_floor_is_enforced() -> None:
    with pytest.raises(InsufficientHistoryError):
        analyze_free_dna_v6(tuple(_match(index) for index in range(29)))


def test_toolkit_coverage_counts_matches_without_taxonomy() -> None:
    matches = tuple(_match(index, hero=index + 1) for index in range(10))
    elements = {
        item.key: item
        for item in compute_elements(
            matches,
            taxonomy_by_hero={index: ("job",) for index in range(1, 8)},
            bootstrap_iterations=20,
        )
    }
    assert elements["toolkit"].coverage == pytest.approx(0.7)
    assert elements["toolkit"].status == "unavailable"


def test_reviewed_v6_taxonomy_has_functional_jobs_for_the_full_roster() -> None:
    taxonomy = load_v6_hero_taxonomy()
    assert len(taxonomy) == 127
    assert all(item["hero_function"] in item["functional_jobs"] for item in taxonomy.values())


def test_post_loss_controls_use_the_narrowest_available_context() -> None:
    rows = (
        SimpleNamespace(match_id=1, start_time=1, session_id="target", won=False, patch="7.41", role_hint="mid", hero_id=1, duration_seconds=1800, kills=1, assists=1, deaths=1),
        SimpleNamespace(match_id=2, start_time=2, session_id="target", won=True, patch="7.41", role_hint="mid", hero_id=1, duration_seconds=1800, kills=2, assists=2, deaths=1),
        SimpleNamespace(match_id=3, start_time=3, session_id="control-a", won=True, patch="7.40", role_hint="safe_lane", hero_id=2, duration_seconds=1800, kills=2, assists=2, deaths=1),
        SimpleNamespace(match_id=4, start_time=4, session_id="control-b", won=True, patch="7.41", role_hint="mid", hero_id=1, duration_seconds=1800, kills=2, assists=2, deaths=1),
    )
    result = compute_post_loss_response(rows, bootstrap_iterations=20)
    assert result.control_matches[0].match_id == 4


def test_post_loss_metrics_are_precomputed_before_bootstrap(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = (
        SimpleNamespace(match_id=1, start_time=1, session_id="target", won=False, patch="7.41", role_hint="mid", hero_id=1, duration_seconds=1800, kills=1, assists=1, deaths=1),
        SimpleNamespace(match_id=2, start_time=2, session_id="target", won=True, patch="7.41", role_hint="mid", hero_id=1, duration_seconds=1800, kills=2, assists=2, deaths=1),
        SimpleNamespace(match_id=3, start_time=3, session_id="control", won=True, patch="7.41", role_hint="mid", hero_id=1, duration_seconds=1800, kills=2, assists=2, deaths=1),
    )
    original = post_loss_module._metric
    calls = 0

    def counted_metric(*args: object, **kwargs: object) -> float | None:
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(post_loss_module, "_metric", counted_metric)
    compute_post_loss_response(rows, bootstrap_iterations=200)

    # Three component values for both sides of one pair. Bootstrap iteration
    # count must not multiply baseline resolution work.
    assert calls == 6


def test_session_drift_requires_explicit_completion_metadata() -> None:
    rows = tuple(_match(index, session=1) for index in range(4))
    assert session_position_buckets(rows) == ()
    assert len(session_position_buckets(rows, completed_sessions={"session-1": True})) == 1


def test_family_confidence_uses_the_weakest_required_signal() -> None:
    result = qualify_family(
        "combat_expression",
        evidence={
            "involvement": {"value": 0.2, "direction": "positive", "sample_size": 60, "independent_sessions": 12, "coverage": 1.0, "stability": 0.95},
            "death_exposure": {"value": 0.2, "direction": "positive", "sample_size": 60, "independent_sessions": 12, "coverage": 1.0, "stability": 0.60},
        },
        sample_size=60,
        independent_sessions=12,
        p_value=0.001,
        direction="positive",
    )
    assert result.confidence == "descriptive"
    assert result.confidence_score == pytest.approx(0.60)
