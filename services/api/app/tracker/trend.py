"""Metric-level trend over the last ten baseline-at-the-time values."""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import cast

from .metrics import LOWER_IS_BETTER, METRICS

TREND_VERSION = "rolling-baseline-trend-1"

# Measured lower bounds from Context-Adjusted Performance V1 §11. They do not
# choose a product threshold; an approved per-metric artifact must do that.
HERO_MIX_FLOORS = {
    "carry.last_hits_at_10.v1": 1.25,
}


@dataclass(frozen=True)
class TrendPoint:
    match_id: int
    started_at: datetime
    baseline_value: float | None


def evaluate(metric_id: str, points: list[TrendPoint], *, calibration: dict[str, object] | None = None) -> dict[str, object]:
    """Return a nullable state and reason without creating a fifth trend state.

    Points must already belong to one mode, role, metric and methodology. The
    caller enforces that identity when loading persisted observations.
    """
    if metric_id not in METRICS:
        raise ValueError("Unknown metric")
    valid = [point for point in points if point.baseline_value is not None]
    if any(type(point.match_id) is not int or point.match_id <= 0 or point.started_at.tzinfo is None
           or point.baseline_value is not None and (type(point.baseline_value) not in {int, float}
           or not math.isfinite(point.baseline_value)) for point in points):
        raise ValueError("Invalid trend point")
    if len({point.match_id for point in valid}) != len(valid):
        raise ValueError("Duplicate trend point")
    window = sorted(valid, key=lambda point: (point.started_at, point.match_id))[-10:]
    if len(window) < 10:
        return {"version": TREND_VERSION, "state": "INSUFFICIENT_HISTORY", "reason": None,
                "point_count": len(window), "source_match_ids": [point.match_id for point in window]}
    thresholds = calibration.get("thresholds") if calibration else None
    threshold = (thresholds.get(metric_id) if calibration
                 and calibration.get("status") == "APPROVED"
                 and isinstance(calibration.get("version"), str) and calibration["version"]
                 and isinstance(thresholds, dict) else None)
    if (not isinstance(threshold, (int, float)) or isinstance(threshold, bool)
            or not math.isfinite(threshold) or threshold <= 0
            or threshold < HERO_MIX_FLOORS.get(metric_id, 0)):
        return {"version": TREND_VERSION, "state": None, "reason": "UNCALIBRATED",
                "point_count": 10, "source_match_ids": [point.match_id for point in window]}
    drift = cast(float, window[-1].baseline_value) - cast(float, window[0].baseline_value)
    if metric_id in LOWER_IS_BETTER:
        drift = -drift
    state = "IMPROVING" if drift > threshold else "DECLINING" if drift < -threshold else "STABLE"
    return {"version": TREND_VERSION, "state": state, "reason": None,
            "point_count": 10, "source_match_ids": [point.match_id for point in window]}
