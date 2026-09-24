from __future__ import annotations

import hashlib
import json
from datetime import date

import pytest
from app.tracker.context import MetricParameters
from app.tracker.metrics import METRICS
from app.tracker.population_parameters import (
    BuildInput,
    CalibrationMatch,
    HeroStatRow,
    LaneOutcomeRow,
    build_artifact,
    load_parameter_set,
    publish_artifact,
)

SLOPES = {"CARRY": 0.748, "MID": 0.778, "OFFLANE": 0.722}


def build_input(*, opponent_coverage: bool = True, slope_shift: float = 0) -> BuildInput:
    lane_rows = []
    samples = []
    hero_rows = []
    for position, role in ((1, "CARRY"), (2, "MID"), (3, "OFFLANE")):
        # Two own heroes have symmetric +/-5 CS opponent effects. Each own-hero
        # base clears 3,000 matches; each opponent clears the 500-match gate.
        lane_rows.extend((
            LaneOutcomeRow(position, 1, 10, 90_000, 2_000),
            LaneOutcomeRow(position, 1, 11, 110_000, 2_000),
            LaneOutcomeRow(position, 2, 10, 50_000, 2_000),
            LaneOutcomeRow(position, 2, 11, 70_000, 2_000),
        ))
        # Independent calibration points vary the drafted opponent while staying
        # exactly on the frozen role-slope relationship.
        for i in range(100):
            hero = 10 if i % 2 == 0 else 11
            covered_hero = hero if opponent_coverage or hero == 10 else 99
            score = -5 if hero == 10 else 5
            samples.append(CalibrationMatch(role, (covered_hero,), (SLOPES[role] + slope_shift) * score))
        for metric_id in METRICS:
            hero_rows.append(HeroStatRow(1, position, metric_id, 42.0, 500))
    parameters = {metric_id: MetricParameters(10, 0.35, 0, 0.1) for metric_id in METRICS}
    return BuildInput(
        version="2026-09-v1",
        pool_start=date(2026, 8, 1),
        pool_end=date(2026, 9, 12),
        hero_stats=tuple(hero_rows),
        lane_outcomes=tuple(lane_rows),
        calibration_matches=tuple(samples),
        reference_role_slopes=SLOPES,
        maximum_slope_drift=0.02,
        metric_parameters=parameters,
    )


def test_build_uses_documented_effect_formula_and_locks_population_parameters() -> None:
    artifact = build_artifact(build_input())

    assert artifact["opponent_effects"]["1:10"] == -5
    assert artifact["opponent_effects"]["1:11"] == 5
    assert artifact["role_slopes"] == pytest.approx(SLOPES)
    assert artifact["opponent_coverage"] == {"CARRY": 1, "MID": 1, "OFFLANE": 1}
    assert artifact["lane_thresholds"]["Carry"] == [-2.05, 1.52]
    assert artifact["validation"]["passed"] is True
    assert len(artifact["sha256"]) == 64


def test_pool_coverage_slope_drift_and_bad_provider_rows_fail_closed() -> None:
    coverage_limited = build_input(opponent_coverage=False)
    with pytest.raises(ValueError, match="coverage below"):
        build_artifact(coverage_limited)

    with pytest.raises(ValueError, match="slope drift"):
        build_artifact(build_input(slope_shift=0.03))

    invalid_pool = build_input()
    with pytest.raises(ValueError, match="4–8 weeks"):
        build_artifact(BuildInput(**{**invalid_pool.__dict__, "pool_start": date(2026, 9, 1)}))

    invalid_hero_rows = build_input()
    with pytest.raises(ValueError, match="heroStats.stats"):
        bad_row = HeroStatRow(1, 1, next(iter(METRICS)), float("nan"), 500)
        build_artifact(BuildInput(**{**invalid_hero_rows.__dict__,
                                     "hero_stats": (bad_row, *invalid_hero_rows.hero_stats[1:])}))


def test_publish_is_atomic_versioned_and_never_overwrites(tmp_path) -> None:
    artifact = build_artifact(build_input())
    path = publish_artifact(artifact, tmp_path)
    before = path.read_bytes()
    assert json.loads(before)["sha256"] == artifact["sha256"]
    with pytest.raises(FileExistsError):
        publish_artifact(artifact, tmp_path)
    assert path.read_bytes() == before
    unsafe = dict(artifact)
    unsafe["version"] = "../bad"
    unsigned = dict(unsafe)
    del unsigned["sha256"]
    unsafe["sha256"] = hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    with pytest.raises(ValueError, match="validated versioned"):
        publish_artifact(unsafe, tmp_path)
    parameters = load_parameter_set(path)
    assert parameters.validated and parameters.version == "2026-09-v1"
    assert parameters.opponent_effects[(1, 10)] == -5
    assert parameters.hero_levels[(1, 1, "carry.last_hits_at_10.v1")].match_count == 500
    with pytest.raises(ValueError, match="slope drift"):
        build_artifact(build_input(slope_shift=0.03))
    assert path.read_bytes() == before

    tampered = json.loads(before)
    tampered["role_slopes"]["CARRY"] = 0
    path.write_text(json.dumps(tampered))
    with pytest.raises(ValueError, match="integrity"):
        load_parameter_set(path)
    assert sorted(item.name for item in tmp_path.iterdir()) == ["2026-09-v1.json"]
