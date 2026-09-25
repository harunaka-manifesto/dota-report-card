"""The single summary-only performance proxy shared by comparative Elements."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import exp
from statistics import median

from app.ingestion.summary_normalize import NormalizedSummaryMatch

PERFORMANCE_PROXY_VERSION = "performance-proxy-5.0.0"
MIN_PERFORMANCE_DURATION_SECONDS = 600


@dataclass(frozen=True, slots=True)
class PerformanceProxyObservation:
    value: float
    outcome_component: float
    activity_component: float
    survival_component: float

    def as_dict(self) -> dict[str, float | str]:
        return {
            "version": PERFORMANCE_PROXY_VERSION,
            "value": round(self.value, 6),
            "outcome_component": round(self.outcome_component, 6),
            "activity_component": round(self.activity_component, 6),
            "survival_component": round(self.survival_component, 6),
        }


def activity_rate(match: NormalizedSummaryMatch) -> float | None:
    if (
        match.duration_seconds is None
        or match.duration_seconds < MIN_PERFORMANCE_DURATION_SECONDS
        or match.kills is None
        or match.assists is None
    ):
        return None
    minutes = max(match.duration_seconds / 60.0, 1.0 / 60.0)
    return (match.kills + match.assists) / minutes


def death_rate(match: NormalizedSummaryMatch) -> float | None:
    if (
        match.duration_seconds is None
        or match.duration_seconds < MIN_PERFORMANCE_DURATION_SECONDS
        or match.deaths is None
    ):
        return None
    ten_minute_units = max(match.duration_seconds / 600.0, 1.0 / 60.0)
    return match.deaths / ten_minute_units


def performance_proxy(
    match: NormalizedSummaryMatch,
    *,
    activity_center: float = 0.0,
    activity_scale: float = 1.0,
    death_center: float = 0.0,
    death_scale: float = 1.0,
) -> PerformanceProxyObservation | None:
    """Calculate a bounded, inspectable proxy from summary fields only.

    Outcome is deliberately a component rather than the whole measure.  K/D/A
    rates are duration-normalized and robust to zero kills, assists, or deaths;
    short/abnormal matches return no observation instead of a neutral guess.
    """

    if match.won is None or match.duration_seconds is None or match.duration_seconds < MIN_PERFORMANCE_DURATION_SECONDS:
        return None
    activity = activity_rate(match)
    deaths = death_rate(match)
    activity_component = (
        _sigmoid((activity - activity_center) / max(abs(activity_scale), 1e-6))
        if activity is not None
        else 0.5
    )
    survival_component = (
        _sigmoid((death_center - deaths) / max(abs(death_scale), 1e-6))
        if deaths is not None
        else 0.5
    )
    outcome_component = 1.0 if match.won else 0.0
    value = 0.50 * outcome_component + 0.30 * activity_component + 0.20 * survival_component
    return PerformanceProxyObservation(
        value=max(0.0, min(1.0, value)),
        outcome_component=outcome_component,
        activity_component=activity_component,
        survival_component=survival_component,
    )


def build_performance_map(matches: Iterable[NormalizedSummaryMatch]) -> tuple[dict[int, float], dict[int, PerformanceProxyObservation]]:
    rows = tuple(matches)
    activity_by_id = {
        item.match_id: value
        for item in rows
        if (value := activity_rate(item)) is not None
    }
    death_by_id = {
        item.match_id: value
        for item in rows
        if (value := death_rate(item)) is not None
    }
    observations: dict[int, PerformanceProxyObservation] = {}
    values: dict[int, float] = {}
    for item in rows:
        # Leave the expected row out of the robust centering/scaling step.  A
        # target match may be measured by its own outcome/KDA, but it must not
        # influence the comparison distribution used to interpret that value.
        activities = [value for match_id, value in activity_by_id.items() if match_id != item.match_id]
        deaths = [value for match_id, value in death_by_id.items() if match_id != item.match_id]
        observation = performance_proxy(
            item,
            activity_center=median(activities) if activities else 0.0,
            activity_scale=_mad(activities) or 1.0,
            death_center=median(deaths) if deaths else 0.0,
            death_scale=_mad(deaths) or 1.0,
        )
        if observation is not None:
            observations[item.match_id] = observation
            values[item.match_id] = observation.value
    return values, observations


def _mad(values: list[float]) -> float:
    if not values:
        return 0.0
    centre = median(values)
    return median([abs(value - centre) for value in values])


def _sigmoid(value: float) -> float:
    bounded = max(-12.0, min(12.0, value))
    return 1.0 / (1.0 + exp(-bounded))


__all__ = [
    "PERFORMANCE_PROXY_VERSION",
    "MIN_PERFORMANCE_DURATION_SECONDS",
    "PerformanceProxyObservation",
    "activity_rate",
    "death_rate",
    "performance_proxy",
    "build_performance_map",
]
