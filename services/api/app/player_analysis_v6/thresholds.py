"""Metric-specific practical thresholds and confidence gates."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from .constants import ELEMENTS_VERSION, MIN_CONSISTENCY_SESSIONS, MIN_STABLE_SESSIONS

MetricZone = Literal["low", "typical", "high", "unknown"]


@dataclass(frozen=True, slots=True)
class MetricThreshold:
    key: str
    practical_margin: float
    low_cutoff: float | None = None
    high_cutoff: float | None = None
    min_sample: int = 30
    min_sessions: int = 1
    min_coverage: float = 0.0
    moderate_stability: float = 0.75
    high_stability: float = 0.90
    version: str = ELEMENTS_VERSION

    def zone(self, value: float | None, *, baseline: float | None = None) -> MetricZone:
        if value is None:
            return "unknown"
        low = self.low_cutoff
        high = self.high_cutoff
        if baseline is not None:
            low = baseline - self.practical_margin
            high = baseline + self.practical_margin
        if low is not None and value < low:
            return "low"
        if high is not None and value > high:
            return "high"
        return "typical"

    def direction(self, value: float | None, *, baseline: float | None = None) -> str:
        zone = self.zone(value, baseline=baseline)
        return {"low": "negative", "high": "positive", "typical": "neutral", "unknown": "unknown"}[zone]

    def supports_confidence(
        self,
        *,
        sample_size: int,
        independent_sessions: int,
        coverage: float,
        stability: float,
    ) -> str:
        if sample_size < self.min_sample or independent_sessions < self.min_sessions or coverage < self.min_coverage:
            return "descriptive"
        if stability >= self.high_stability:
            return "high"
        if stability >= self.moderate_stability:
            return "moderate"
        return "descriptive"


DEFAULT_THRESHOLDS: Mapping[str, MetricThreshold] = {
    # A practical margin is deliberately metric-specific.  These values are
    # release defaults until held-out calibration freezes a corpus artifact.
    "breadth_effective_count": MetricThreshold("breadth_effective_count", 0.75, min_sample=30, min_sessions=1),
    "toolkit_effective_count": MetricThreshold("toolkit_effective_count", 0.20, min_sample=30, min_sessions=1, min_coverage=0.80),
    "involvement_per_minute": MetricThreshold("involvement_per_minute", 0.08, min_sample=30, min_sessions=8),
    "finishing_share": MetricThreshold("finishing_share", 0.06, min_sample=30, min_sessions=8),
    "death_exposure_per_ten": MetricThreshold("death_exposure_per_ten", 0.35, min_sample=30, min_sessions=8),
    "transfer_agreement": MetricThreshold("transfer_agreement", 0.10, min_sample=30, min_sessions=8),
    "consistency_dispersion": MetricThreshold("consistency_dispersion", 0.10, min_sample=30, min_sessions=MIN_CONSISTENCY_SESSIONS),
    "post_loss_response": MetricThreshold("post_loss_response", 0.10, min_sample=30, min_sessions=MIN_CONSISTENCY_SESSIONS),
    "session_drift": MetricThreshold("session_drift", 0.10, min_sample=30, min_sessions=MIN_CONSISTENCY_SESSIONS),
}


def threshold_for(key: str, thresholds: Mapping[str, MetricThreshold] | None = None) -> MetricThreshold:
    source = thresholds or DEFAULT_THRESHOLDS
    if key in source:
        return source[key]
    # Unknown metrics receive a conservative, explicit threshold rather than
    # silently inheriting an unrelated global boundary.
    return MetricThreshold(key, 0.10, min_sample=30, min_sessions=MIN_STABLE_SESSIONS)


def classify_metric(
    value: float | None,
    *,
    metric: str,
    baseline: float | None = None,
    thresholds: Mapping[str, MetricThreshold] | None = None,
) -> tuple[MetricZone, str]:
    threshold = threshold_for(metric, thresholds)
    zone = threshold.zone(value, baseline=baseline)
    return zone, {"low": "negative", "high": "positive", "typical": "neutral", "unknown": "unknown"}[zone]


__all__ = ["MetricThreshold", "DEFAULT_THRESHOLDS", "threshold_for", "classify_metric"]
