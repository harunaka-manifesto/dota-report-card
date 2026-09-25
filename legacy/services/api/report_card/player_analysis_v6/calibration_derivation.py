"""Production-parity point estimates for training-only v6 calibration.

This module deliberately computes no intervals. It reuses runtime formula
helpers and recomputes nonlinear metrics for every requested session subset.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .baselines import BaselineResolver
from .context_adjustment import adjust_metric_per_match, match_field, match_hero_id
from .metrics import (
    death_exposure_per_ten_minutes,
    finishing_share,
    involvement_per_minute,
    match_weighted_effective_count,
    robust_dispersion,
    shannon_effective_count,
)
from .post_loss import _metric as _post_loss_metric
from .post_loss import _ordered as _ordered_matches
from .post_loss import _same_comparable_context, build_post_loss_transitions
from .session_drift import _value as _drift_value
from .session_drift import session_position_buckets

METRIC_KEYS = (
    "breadth_effective_count", "toolkit_effective_count", "involvement_adjusted",
    "finishing_adjusted", "death_exposure_adjusted", "transfer_outcome_delta",
    "transfer_activity_delta", "transfer_survival_delta", "consistency_outcome_dispersion",
    "consistency_activity_dispersion", "consistency_death_dispersion", "post_loss_outcome_delta",
    "post_loss_activity_delta", "post_loss_survival_delta", "post_loss_familiarity_delta",
    "post_loss_tempo_delta", "session_drift_outcome_delta", "session_drift_activity_delta",
    "session_drift_survival_delta",
)


@dataclass(frozen=True, slots=True)
class MetricEstimate:
    value: float | None
    usable_count: int
    independent_sessions: int
    coverage: float
    unavailable_reason: str | None = None
    diagnostics: Mapping[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ProfileEstimates:
    metrics: Mapping[str, MetricEstimate]
    session_ids: tuple[str, ...]


def chronological_session_ids(matches: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    starts: dict[str, tuple[int, int]] = {}
    for row in matches:
        sid = str(row["session_id"])
        candidate = (int(row["start_time"]), int(row.get("session_index", 0)))
        starts[sid] = min(starts.get(sid, candidate), candidate)
    return tuple(sorted(starts, key=lambda sid: (*starts[sid], sid)))


def odd_even_session_ids(matches: Sequence[Mapping[str, Any]]) -> tuple[set[str], set[str]]:
    ordered = chronological_session_ids(matches)
    return set(ordered[::2]), set(ordered[1::2])


def _mean(values: Sequence[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _core_and_stretch(matches: Sequence[Mapping[str, Any]]) -> tuple[set[Any], set[Any]]:
    counts = Counter(match_hero_id(row) for row in matches if match_hero_id(row) is not None)
    ordered = sorted(counts, key=lambda hero: (-counts[hero], repr(hero)))
    core: set[Any] = set()
    running = 0
    target = math.ceil(sum(counts.values()) * 0.60)
    for hero in ordered:
        core.add(hero)
        running += counts[hero]
        if running >= target:
            break
    return core, set(counts) - core


def _raw(row: Mapping[str, Any], metric: str) -> float | None:
    if metric == "involvement_adjusted":
        return involvement_per_minute(row.get("kills"), row.get("assists"), row.get("duration_seconds"))
    if metric == "finishing_adjusted":
        return finishing_share(row.get("kills"), row.get("assists"))
    return death_exposure_per_ten_minutes(row.get("deaths"), row.get("duration_seconds"))


def _raw_metric(metric: str) -> Callable[[Any], float | None]:
    def calculate(row: Any) -> float | None:
        return _raw(row, metric)
    return calculate


def derive_profile_estimates(
    matches: Sequence[Mapping[str, Any]],
    *,
    baseline_resolver: BaselineResolver,
    taxonomy_by_hero: Mapping[Any, Any],
    completed_sessions: Mapping[str, bool] | None = None,
) -> ProfileEstimates:
    rows = tuple(sorted(matches, key=lambda row: (int(row["start_time"]), int(row["match_id"]))))
    session_ids = chronological_session_ids(rows)
    session_count = len(session_ids)
    result: dict[str, MetricEstimate] = {}
    hero_counts = Counter(match_hero_id(row) for row in rows if match_hero_id(row) is not None)
    breadth_available = len(rows) >= 30 and bool(hero_counts)
    result["breadth_effective_count"] = MetricEstimate(
        shannon_effective_count(hero_counts) if breadth_available else None,
        sum(hero_counts.values()), session_count, sum(hero_counts.values()) / len(rows) if rows else 0.0,
        None if breadth_available else "requires 30 matches with hero identifiers",
    )
    taxonomy_by_match = {row["match_id"]: taxonomy_by_hero.get(match_hero_id(row)) for row in rows}
    toolkit, taxonomy_coverage = match_weighted_effective_count(taxonomy_by_match)
    toolkit_available = len(rows) >= 30 and toolkit is not None and taxonomy_coverage >= 0.80
    result["toolkit_effective_count"] = MetricEstimate(
        toolkit if toolkit_available else None, sum(value is not None for value in taxonomy_by_match.values()), session_count,
        taxonomy_coverage, None if toolkit_available else "requires 30 matches and 80% taxonomy coverage",
    )
    adjusted: dict[str, Any] = {}
    for metric in ("involvement_adjusted", "finishing_adjusted", "death_exposure_adjusted"):
        series = adjust_metric_per_match(rows, metric, _raw_metric(metric), baseline_resolver=baseline_resolver, taxonomy_by_hero=taxonomy_by_hero)
        adjusted[metric] = series
        eligible = len(series.values) >= 30 and len(set(series.session_ids)) >= 8 and series.coverage >= 0.80
        result[metric] = MetricEstimate(
            _mean(series.values) if eligible else None, len(series.values), len(set(series.session_ids)),
            series.coverage, None if eligible else "scalar sample/session/baseline-coverage gate failed", series.audit(),
        )
    core, stretch = _core_and_stretch(rows)
    series_values = {
        metric: {id(obs.match): obs.adjusted_value for obs in series.observations}
        for metric, series in adjusted.items()
    }
    transfer: dict[str, dict[str, list[float]]] = {"core": defaultdict(list), "stretch": defaultdict(list)}
    for row in rows:
        bucket = "core" if match_hero_id(row) in core else "stretch" if match_hero_id(row) in stretch else ""
        if not bucket:
            continue
        won = match_field(row, "won")
        if won is not None:
            transfer[bucket]["outcome"].append(1.0 if won else 0.0)
        activity = series_values["involvement_adjusted"].get(id(row))
        survival_raw = series_values["death_exposure_adjusted"].get(id(row))
        if activity is not None:
            transfer[bucket]["activity"].append(activity)
        if survival_raw is not None:
            transfer[bucket]["survival"].append(-survival_raw)
    transfer_rows = [row for row in rows if match_hero_id(row) in core | stretch]
    transfer_sessions = len({str(row["session_id"]) for row in transfer_rows})
    usable_core = sum(match_hero_id(row) in core for row in transfer_rows)
    usable_stretch = sum(match_hero_id(row) in stretch for row in transfer_rows)
    comparable = sum(len(transfer[bucket][component]) for bucket in transfer for component in ("activity", "survival"))
    opportunities = 2 * len(transfer_rows)
    transfer_coverage = comparable / opportunities if opportunities else 0.0
    transfer_ok = (
        len(rows) >= 30
        and bool(core)
        and bool(stretch)
        and usable_core >= 10
        and usable_stretch >= 10
        and transfer_sessions >= 8
        and transfer_coverage >= 0.70
    )
    for component in ("outcome", "activity", "survival"):
        left, right = transfer["core"][component], transfer["stretch"][component]
        value = (_mean(right) - _mean(left)) if transfer_ok and left and right else None  # type: ignore[operator]
        result[f"transfer_{component}_delta"] = MetricEstimate(value, min(len(left), len(right)), transfer_sessions, transfer_coverage, None if value is not None else "transfer sample/session/coverage gate failed", {"core_matches": usable_core, "stretch_matches": usable_stretch})
    session_components: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        sid = str(row["session_id"])
        session_components[sid]["outcome"].append(1.0 if row["won"] else 0.0)
        activity = series_values["involvement_adjusted"].get(id(row))
        death = series_values["death_exposure_adjusted"].get(id(row))
        if activity is not None:
            session_components[sid]["activity"].append(activity)
        if death is not None:
            session_components[sid]["death"].append(death)
    for component in ("outcome", "activity", "death"):
        values = [_mean(data[component]) for data in session_components.values() if data[component]]
        clean = [value for value in values if value is not None]
        estimate = robust_dispersion(clean) if len(rows) >= 30 and len(clean) >= 12 else None
        result[f"consistency_{component}_dispersion"] = MetricEstimate(estimate, len(clean), len(clean), len(clean) / session_count if session_count else 0.0, None if estimate is not None else "requires 30 matches and 12 usable sessions")
    transitions = build_post_loss_transitions(rows)
    transition_targets = {id(item.current) for item in transitions}
    triggers = {id(item.previous) for item in transitions}
    candidates = [item for item in _ordered_matches(rows) if id(item) not in transition_targets | triggers]
    pairs: list[tuple[Any, Any]] = []
    for transition in transitions:
        target = transition.current
        control = next((candidate for level in range(4) for candidate in candidates if _same_comparable_context(target, candidate, level, taxonomy_by_hero=taxonomy_by_hero)), None)
        if control is not None:
            pairs.append((target, control))
    coverage = len(pairs) / len(transitions) if transitions else 0.0
    qualifying_sessions = len({item.session_id for item in transitions})
    post_ok = len(transitions) >= 30 and qualifying_sessions >= 12 and coverage >= 0.50
    for component in ("outcome", "activity", "survival"):
        delta_values: list[float] = []
        for after, control in pairs:
            after_value = _post_loss_metric(after, component, baseline_resolver, taxonomy_by_hero)
            control_value = _post_loss_metric(control, component, baseline_resolver, taxonomy_by_hero)
            if after_value is not None and control_value is not None:
                delta_values.append(after_value - control_value)
        value = _mean(delta_values) if post_ok else None
        result[f"post_loss_{component}_delta"] = MetricEstimate(value, len(transitions), qualifying_sessions, coverage, None if value is not None else "post-loss sample/session/coverage gate failed")
    familiarity_values = [(match_hero_id(after) in core) - (match_hero_id(control) in core) for after, control in pairs]
    familiar = _mean(familiarity_values) if post_ok and familiarity_values else None
    result["post_loss_familiarity_delta"] = MetricEstimate(familiar, len(transitions), qualifying_sessions, coverage, None if familiar is not None else "post-loss sample/session/coverage gate failed")
    activity_value = result["post_loss_activity_delta"].value
    result["post_loss_tempo_delta"] = MetricEstimate(activity_value, len(transitions), qualifying_sessions, coverage, result["post_loss_activity_delta"].unavailable_reason)
    buckets = session_position_buckets(rows, completed_sessions=completed_sessions)
    drift_rows: list[dict[str, float | str]] = []
    for sid, early, late in buckets:
        session_row: dict[str, float | str] = {"session_id": sid}
        for component in ("outcome", "activity", "survival"):
            early_raw = [_drift_value(row, component, baseline_resolver, taxonomy_by_hero) for row in early]
            late_raw = [_drift_value(row, component, baseline_resolver, taxonomy_by_hero) for row in late]
            a = [float(value) for value in early_raw if value is not None]
            b = [float(value) for value in late_raw if value is not None]
            if a and b:
                session_row[component] = statistics.fmean(b) - statistics.fmean(a)
        if len(session_row) >= 3:
            drift_rows.append(session_row)
    drift_coverage = len(drift_rows) / session_count if session_count else 0.0
    drift_ok = len(rows) >= 30 and len(drift_rows) >= 12 and drift_coverage >= 0.50
    for component in ("outcome", "activity", "survival"):
        drift_values = [float(row[component]) for row in drift_rows if component in row]
        value = _mean(drift_values) if drift_ok else None
        result[f"session_drift_{component}_delta"] = MetricEstimate(value, len(drift_values), len(drift_rows), drift_coverage, None if value is not None else "session-drift sample/session/coverage gate failed")
    assert set(result) == set(METRIC_KEYS)
    return ProfileEstimates(result, session_ids)


__all__ = ["METRIC_KEYS", "MetricEstimate", "ProfileEstimates", "chronological_session_ids", "derive_profile_estimates", "odd_even_session_ids"]
