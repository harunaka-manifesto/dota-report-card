from datetime import UTC, datetime, timedelta

import pytest
from app.tracker.trend import TrendPoint, evaluate


def points(values):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [TrendPoint(i + 1, start + timedelta(days=i), value) for i, value in enumerate(values)]


def test_trend_requires_ten_measured_baseline_points_and_approved_calibration():
    metric = "carry.last_hits_at_10.v1"
    rows = points([float(i) for i in range(10)])
    assert evaluate(metric, rows[:-1])["state"] == "INSUFFICIENT_HISTORY"
    assert evaluate(metric, rows[:-1] + points([None])[-1:])["point_count"] == 9
    assert evaluate(metric, rows)["state"] is None
    assert evaluate(metric, rows)["reason"] == "UNCALIBRATED"
    test_only = {"version": "test", "status": "TEST_ONLY", "thresholds": {metric: 2.0}}
    assert evaluate(metric, rows, calibration=test_only)["state"] is None
    below_floor = {"version": "test", "status": "APPROVED", "thresholds": {metric: 1.0}}
    assert evaluate(metric, rows, calibration=below_floor)["state"] is None
    assert evaluate(metric, rows, calibration={**below_floor, "thresholds": {metric: 2.0}})["state"] == "IMPROVING"


def test_trend_uses_latest_ten_and_metric_polarity():
    metric = "carry.dead_time.v1"
    calibration = {"version": "test", "status": "APPROVED", "thresholds": {metric: 0.1}}
    rows = points([99.0, *[1 - i / 20 for i in range(10)]])
    result = evaluate(metric, rows, calibration=calibration)
    assert result["state"] == "IMPROVING"
    assert result["source_match_ids"] == list(range(2, 12))
    assert evaluate(metric, points([1.0] * 10), calibration=calibration)["state"] == "STABLE"
    assert evaluate(metric, points([i / 10 for i in range(10)]), calibration=calibration)["state"] == "DECLINING"


def test_trend_rejects_duplicate_or_nonfinite_source():
    rows = points([0.0] * 10)
    with pytest.raises(ValueError):
        evaluate("carry.dead_time.v1", [*rows, rows[0]])
    with pytest.raises(ValueError):
        evaluate("carry.dead_time.v1", points([float("nan"), *([0.0] * 9)]))
