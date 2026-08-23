from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from app.player_analysis_v6.artifacts import (
    ArtifactValidationError,
    load_context_baseline_artifact,
    validate_context_baseline_artifact,
)
from app.player_analysis_v6.calibration import (
    REQUIRED_THRESHOLD_KEYS,
    load_threshold_artifact,
    validate_threshold_artifact,
)
from app.player_analysis_v6.context_adjustment import adjusted_value_for_match
from app.player_analysis_v6.family_statistics import benjamini_hochberg_five, family_statistics
from app.player_analysis_v6.statistics import clustered_bootstrap

from scripts.build_v6_calibration_artifacts import (
    build_evaluation,
    build_thresholds,
    split_profiles,
)

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "v6"
pytestmark = pytest.mark.calibration


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def test_fixture_artifacts_are_strict_and_complete() -> None:
    baseline = load_context_baseline_artifact(FIXTURES / "context-baseline-2.0.0.fixture.json")
    thresholds = load_threshold_artifact(FIXTURES / "metric-thresholds-6.0.0.fixture.json")
    assert baseline.corpus["mmr_used"] is False
    assert set(thresholds.metrics) == set(REQUIRED_THRESHOLD_KEYS)
    assert all(item.moderate_stability == 0.75 and item.high_stability == 0.90 for item in thresholds.metrics.values())


@pytest.mark.parametrize("bad_key", ["rank", "rank_tier", "mmr", "mmr_bucket"])
def test_baseline_rejects_rank_and_mmr_dimensions(bad_key: str) -> None:
    payload = _load("context-baseline-2.0.0.fixture.json")
    payload["cells"][0][bad_key] = "forbidden"
    with pytest.raises(ArtifactValidationError):
        validate_context_baseline_artifact(payload)


def test_threshold_rejects_mmr_derivation() -> None:
    payload = _load("metric-thresholds-6.0.0.fixture.json")
    payload["derivation"]["mmr_used"] = True
    with pytest.raises(ArtifactValidationError):
        validate_threshold_artifact(payload)


def test_context_adjustment_changes_when_baseline_cell_changes() -> None:
    baseline = load_context_baseline_artifact(FIXTURES / "context-baseline-2.0.0.fixture.json").resolver()
    row = SimpleNamespace(hero_id=1, patch="7.41", role_hint="carry", won=True)
    first, audit = adjusted_value_for_match(row, "involvement_adjusted", 1.0, baseline_resolver=baseline)
    assert first == pytest.approx(0.65)
    assert audit.level == "overall"


def test_bootstrap_uses_varied_session_rows_and_emits_interval() -> None:
    rows = [
        {"session": "a", "value": -1.0},
        {"session": "a", "value": -0.5},
        {"session": "b", "value": 0.5},
        {"session": "b", "value": 1.0},
        {"session": "c", "value": 2.0},
        {"session": "c", "value": 1.5},
    ]
    result = clustered_bootstrap(
        [item["value"] for item in rows],
        [item["session"] for item in rows],
        iterations=200,
        seed=7,
    )
    assert result.independent_sessions == 3
    assert result.interval is not None
    assert len(set(result.replicates)) > 1


def test_bh_always_corrects_exactly_five_slots_and_missing_is_one() -> None:
    raw = {"pool_shape": 0.01, "transfer": 0.02, "post_loss_response": None}
    corrected = benjamini_hochberg_five(raw)
    stats = family_statistics(raw)
    assert tuple(corrected) == ("pool_shape", "transfer", "post_loss_response", "combat_expression", "session_drift")
    assert set(stats) == set(corrected)
    assert corrected["post_loss_response"] == 1.0
    assert corrected["combat_expression"] == 1.0
    assert corrected["session_drift"] == 1.0


def test_calibration_builder_is_player_exclusive_stratified_and_not_release_ready() -> None:
    metric_keys = tuple(REQUIRED_THRESHOLD_KEYS)
    rows: list[dict[str, object]] = []
    for profile_id in range(6):
        for index in range(20):
            session = f"p{profile_id}-s{index // 5}"
            metrics = {
                key: (0.1 * profile_id) + (0.01 * index) + (0.001 * position)
                for position, key in enumerate(metric_keys)
            }
            rows.append({
                "profile_id": profile_id,
                "session_id": session,
                "hero_id": (profile_id + index) % 4,
                "patch": "7.41",
                "hero_function": "carry" if profile_id % 2 else "support",
                "lane_context": "mid" if index % 2 else "safe_lane",
                "region": "fixture-a" if profile_id % 2 else "fixture-b",
                "lobby_type": "ranked",
                "metrics": metrics,
            })

    train, holdout = split_profiles(rows, seed=6000)
    assert train.isdisjoint(holdout)
    assert train | holdout == set(range(6))
    first = build_thresholds(rows, train_profiles=train, holdout_profiles=holdout, seed=6000)
    second = build_thresholds(rows, train_profiles=train, holdout_profiles=holdout, seed=6000)
    assert first["metrics"] == second["metrics"]
    evaluation = build_evaluation(rows, train, holdout, first["metrics"])
    assert evaluation["release_ready"] is False
    assert evaluation["status"] == "external-review-required"
    assert evaluation["gates"]["minimum_profiles"]["passed"] is False
