"""V6.1 repairs for expression, Finishing, Transfer, and Consistency."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from app.player_analysis_v6.context_adjustment import (
    adjust_metric_per_match,
    adjusted_value_for_match,
    match_field,
)
from app.player_analysis_v6.metrics import death_exposure_per_ten_minutes, involvement_per_minute

from .portfolio_shape import cross_fitted_distance_records


def _get(value: Any, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, Mapping) else getattr(value, key, default)


def _session(value: Any, index: int) -> str:
    session_id = _get(value, "session_id")
    return str(session_id) if session_id not in (None, "") else f"match:{index}"


def _interval(center: float, variance: float) -> tuple[float, float]:
    half_width = 1.96 * math.sqrt(max(variance, 0.0))
    return max(0.0, center - half_width), min(1.0, center + half_width)


def _normal_interval(center: float, variance: float) -> tuple[float, float]:
    half_width = 1.96 * math.sqrt(max(variance, 0.0))
    return center - half_width, center + half_width


def duration_context_involvement(
    matches: Sequence[Any],
    *,
    baseline_resolver: Any,
    taxonomy_by_hero: Mapping[Any, Any] | None,
) -> dict[str, Any]:
    series = adjust_metric_per_match(
        matches,
        "involvement_per_minute",
        lambda match: involvement_per_minute(
            match_field(match, "kills"),
            match_field(match, "assists"),
            match_field(match, "duration_seconds", match_field(match, "duration")),
        ),
        baseline_resolver=baseline_resolver,
        taxonomy_by_hero=taxonomy_by_hero,
    )
    observations = [item for item in series.observations if item.adjusted_value is not None]
    x_values = [
        math.log(
            max(
                float(
                    match_field(
                        item.match,
                        "duration_seconds",
                        match_field(item.match, "duration", 1_800),
                    )
                    or 1_800
                ),
                600.0,
            )
            / 1_800.0
        )
        for item in observations
    ]
    y_values = [float(item.adjusted_value or 0.0) for item in observations]
    mean_x = sum(x_values) / len(x_values) if x_values else 0.0
    mean_y = sum(y_values) / len(y_values) if y_values else 0.0
    denominator = sum((value - mean_x) ** 2 for value in x_values)
    slope = (
        sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values, strict=True))
        / denominator
        if denominator
        else 0.0
    )
    estimate = mean_y - slope * mean_x
    by_session: dict[str, list[float]] = defaultdict(list)
    for item, x, y in zip(observations, x_values, y_values, strict=True):
        by_session[item.session_id].append(y - slope * x)
    session_means = [sum(values) / len(values) for values in by_session.values()]
    variance = (
        sum((value - estimate) ** 2 for value in session_means)
        / (len(session_means) * (len(session_means) - 1))
        if len(session_means) > 1
        else 0.0
    )
    limitations: list[str] = []
    if series.resolved_count < 30:
        limitations.append("requires at least 30 context-resolved matches")
    if len(by_session) < 8:
        limitations.append("requires at least eight independent sessions")
    if series.coverage < 0.80:
        limitations.append("requires at least 80% context coverage")
    return {
        "estimate": estimate if not limitations else None,
        "interval": list(_normal_interval(estimate, variance)),
        "duration_log_slope": slope,
        "matches": series.resolved_count,
        "sessions": len(by_session),
        "coverage": series.coverage,
        "context_audit": series.audit(),
        "status": "available" if not limitations else "unavailable",
        "limitations": limitations,
        "estimator_version": "involvement-duration-context-2.0.0",
    }


def overdispersed_death_exposure(
    matches: Sequence[Any],
    *,
    baseline_resolver: Any,
    taxonomy_by_hero: Mapping[Any, Any] | None,
) -> dict[str, Any]:
    series = adjust_metric_per_match(
        matches,
        "death_exposure_per_ten",
        lambda match: death_exposure_per_ten_minutes(
            match_field(match, "deaths"),
            match_field(match, "duration_seconds", match_field(match, "duration")),
        ),
        baseline_resolver=baseline_resolver,
        taxonomy_by_hero=taxonomy_by_hero,
    )
    observations = [item for item in series.observations if item.adjusted_value is not None]
    values = [float(item.adjusted_value or 0.0) for item in observations]
    estimate = sum(values) / len(values) if values else 0.0
    raw_values = [float(item.raw_value) for item in observations]
    raw_mean = sum(raw_values) / len(raw_values) if raw_values else 0.0
    raw_variance = (
        sum((value - raw_mean) ** 2 for value in raw_values) / (len(raw_values) - 1)
        if len(raw_values) > 1
        else 0.0
    )
    dispersion = max(1.0, raw_variance / raw_mean) if raw_mean > 0 else 1.0
    by_session: dict[str, list[float]] = defaultdict(list)
    for item in observations:
        by_session[item.session_id].append(float(item.adjusted_value or 0.0))
    session_means = [sum(items) / len(items) for items in by_session.values()]
    cluster_variance = (
        sum((value - estimate) ** 2 for value in session_means)
        / (len(session_means) * (len(session_means) - 1))
        if len(session_means) > 1
        else 0.0
    )
    limitations: list[str] = []
    if series.resolved_count < 30:
        limitations.append("requires at least 30 context-resolved matches")
    if len(by_session) < 8:
        limitations.append("requires at least eight independent sessions")
    if series.coverage < 0.80:
        limitations.append("requires at least 80% context coverage")
    return {
        "estimate": estimate if not limitations else None,
        "interval": list(_normal_interval(estimate, cluster_variance * dispersion)),
        "overdispersion": dispersion,
        "matches": series.resolved_count,
        "sessions": len(by_session),
        "coverage": series.coverage,
        "context_audit": series.audit(),
        "status": "available" if not limitations else "unavailable",
        "limitations": limitations,
        "estimator_version": "death-exposure-overdispersed-2.0.0",
    }


def stabilized_finishing(matches: Sequence[Any]) -> dict[str, Any]:
    kills = 0
    events = 0
    event_matches = 0
    sessions: set[str] = set()
    for index, match in enumerate(matches):
        raw_kills = match_field(match, "kills")
        raw_assists = match_field(match, "assists")
        if not isinstance(raw_kills, (int, float)) or not isinstance(raw_assists, (int, float)):
            continue
        opportunities = max(0, int(raw_kills)) + max(0, int(raw_assists))
        if opportunities <= 0:
            continue
        kills += max(0, int(raw_kills))
        events += opportunities
        event_matches += 1
        sessions.add(_session(match, index))
    # Fixture/synthetic prior. Production promotion requires a frozen training
    # artifact; keeping it explicit prevents thin histories from appearing exact.
    alpha, beta = 2.0, 2.0
    posterior_alpha = alpha + kills
    posterior_beta = beta + events - kills
    total = posterior_alpha + posterior_beta
    center = posterior_alpha / total if total else 0.5
    variance = posterior_alpha * posterior_beta / (total * total * (total + 1)) if total else 0.0
    limitations: list[str] = []
    if events < 100:
        limitations.append("requires at least 100 kills-plus-assists events")
    if event_matches < 30:
        limitations.append("requires at least 30 matches with scoreboard events")
    if len(sessions) < 8:
        limitations.append("requires at least eight independent sessions")
    return {
        "estimate": center if not limitations else None,
        "interval": list(_interval(center, variance)),
        "kills": kills,
        "events": events,
        "event_matches": event_matches,
        "sessions": len(sessions),
        "status": "available" if not limitations else "unavailable",
        "limitations": limitations,
        "estimator_version": "finishing-beta-binomial-1.0.0",
    }


def _outcome(match: Any) -> float | None:
    won = match_field(match, "won")
    return None if won is None else float(bool(won))


def _activity(match: Any, resolver: Any, taxonomy: Mapping[Any, Any] | None) -> float | None:
    raw = involvement_per_minute(
        match_field(match, "kills"),
        match_field(match, "assists"),
        match_field(match, "duration_seconds", match_field(match, "duration")),
    )
    value, _ = adjusted_value_for_match(
        match,
        "involvement_per_minute",
        raw,
        baseline_resolver=resolver,
        taxonomy_by_hero=taxonomy,
    )
    return value


def _survival(match: Any, resolver: Any, taxonomy: Mapping[Any, Any] | None) -> float | None:
    raw = death_exposure_per_ten_minutes(
        match_field(match, "deaths"),
        match_field(match, "duration_seconds", match_field(match, "duration")),
    )
    value, _ = adjusted_value_for_match(
        match,
        "death_exposure_per_ten",
        raw,
        baseline_resolver=resolver,
        taxonomy_by_hero=taxonomy,
    )
    return None if value is None else -value


def continuous_transfer(
    matches: Sequence[Any],
    *,
    baseline_resolver: Any,
    taxonomy_by_hero: Mapping[Any, Any] | None,
) -> dict[str, Any]:
    records = cross_fitted_distance_records(matches, taxonomy_by_hero)
    values: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    values_by_session: dict[str, dict[str, dict[str, list[float]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    sessions_by_band: dict[str, set[str]] = defaultdict(set)
    for index, record in enumerate(records):
        session_id = _session(record.match, index)
        for key, function in (
            ("outcome", _outcome),
            ("activity", lambda match: _activity(match, baseline_resolver, taxonomy_by_hero)),
            ("survival", lambda match: _survival(match, baseline_resolver, taxonomy_by_hero)),
        ):
            value = function(record.match)
            if value is not None:
                values[record.band][key].append(float(value))
                values_by_session[record.band][key][session_id].append(float(value))
        sessions_by_band[record.band].add(session_id)
    core = values.get("core", {})
    margins = {"outcome": 0.08, "activity": 0.08, "survival": 0.35}
    band_results: dict[str, Any] = {}
    frontier = "core"
    subtype = "mixed"
    for band in ("core", "reliable_stretch", "experimental_edge"):
        component_deltas: dict[str, float | None] = {}
        component_intervals: dict[str, list[float] | None] = {}
        equivalent: dict[str, bool] = {}
        for key in ("outcome", "activity", "survival"):
            baseline_values = core.get(key, [])
            candidate_values = values.get(band, {}).get(key, [])
            delta = (
                sum(candidate_values) / len(candidate_values) - sum(baseline_values) / len(baseline_values)
                if baseline_values and candidate_values
                else None
            )
            component_deltas[key] = delta
            core_session_means = [
                sum(items) / len(items)
                for items in values_by_session.get("core", {}).get(key, {}).values()
            ]
            candidate_session_means = [
                sum(items) / len(items)
                for items in values_by_session.get(band, {}).get(key, {}).values()
            ]

            def mean_variance(items: list[float]) -> float:
                if len(items) < 2:
                    return 0.0
                center = sum(items) / len(items)
                return sum((value - center) ** 2 for value in items) / (
                    len(items) * (len(items) - 1)
                )

            interval = (
                _normal_interval(
                    delta,
                    mean_variance(core_session_means)
                    + mean_variance(candidate_session_means),
                )
                if delta is not None and core_session_means and candidate_session_means
                else None
            )
            component_intervals[key] = list(interval) if interval is not None else None
            equivalent[key] = bool(
                interval is not None
                and interval[0] >= -margins[key]
                and interval[1] <= margins[key]
            )
        supported = len(values.get(band, {}).get("outcome", [])) >= 12 and len(sessions_by_band.get(band, set())) >= 6
        all_equivalent = supported and all(equivalent.values())
        if all_equivalent:
            frontier = band
        band_results[band] = {
            "match_count": max((len(items) for items in values.get(band, {}).values()), default=0),
            "sessions": len(sessions_by_band.get(band, set())),
            "component_deltas": component_deltas,
            "component_intervals": component_intervals,
            "equivalent": equivalent,
            "supported": supported,
        }
    reliable = band_results.get("reliable_stretch", {})
    equivalent = reliable.get("equivalent", {})
    if reliable.get("supported"):
        if all(equivalent.values()):
            subtype = "clean_transfer"
        elif equivalent.get("outcome") and not (equivalent.get("activity") and equivalent.get("survival")):
            subtype = "expression_stops_first"
        elif not equivalent.get("outcome") and equivalent.get("activity") and equivalent.get("survival"):
            subtype = "results_stop_first"
        elif not equivalent.get("activity") and equivalent.get("survival"):
            subtype = "involvement_boundary"
        elif equivalent.get("activity") and not equivalent.get("survival"):
            subtype = "exposure_boundary"
    score = {"core": 0.0, "reliable_stretch": 0.5, "experimental_edge": 1.0}[frontier]
    return {
        "estimate": score,
        "frontier": frontier,
        "semantic_subtype": subtype,
        "bands": band_results,
        "cross_fitted": True,
        "status": "available" if len(records) >= 30 else "unavailable",
        "estimator_version": "portfolio-distance-frontier-1.0.0",
    }


def information_weighted_consistency(
    matches: Sequence[Any],
    *,
    baseline_resolver: Any,
    taxonomy_by_hero: Mapping[Any, Any] | None,
) -> dict[str, Any]:
    groups: dict[str, list[Any]] = defaultdict(list)
    for index, match in enumerate(matches):
        groups[_session(match, index)].append(match)
    annual = {
        "outcome": [_outcome(match) for match in matches],
        "activity": [_activity(match, baseline_resolver, taxonomy_by_hero) for match in matches],
        "survival": [_survival(match, baseline_resolver, taxonomy_by_hero) for match in matches],
    }
    centers = {
        key: sum(float(value) for value in items if value is not None) / sum(value is not None for value in items)
        if any(value is not None for value in items)
        else 0.0
        for key, items in annual.items()
    }
    component_variance: dict[str, float] = {}
    precision_mass = 0.0
    for key, center in centers.items():
        weighted: list[tuple[float, float]] = []
        for rows in groups.values():
            function = {
                "outcome": _outcome,
                "activity": lambda match: _activity(match, baseline_resolver, taxonomy_by_hero),
                "survival": lambda match: _survival(match, baseline_resolver, taxonomy_by_hero),
            }[key]
            values = [value for match in rows if (value := function(match)) is not None]
            if not values:
                continue
            weight = len(values) / (len(values) + 4.0)
            shrunk = weight * (sum(values) / len(values)) + (1.0 - weight) * center
            weighted.append((shrunk, weight))
            precision_mass += weight
        denominator = sum(weight for _value, weight in weighted)
        component_variance[key] = (
            sum(weight * (value - center) ** 2 for value, weight in weighted) / denominator
            if denominator
            else 0.0
        )
    scales = {"outcome": 0.25, "activity": 0.04, "survival": 0.80}
    normalized = [min(1.0, component_variance[key] / scales[key]) for key in component_variance]
    score = max(0.0, 1.0 - sum(normalized) / len(normalized)) if normalized else 0.0
    limitations: list[str] = []
    if len(groups) < 12:
        limitations.append("requires at least 12 independent sessions")
    return {
        "estimate": score if not limitations else None,
        "component_variance": component_variance,
        "session_count": len(groups),
        "information_weight": precision_mass,
        "status": "available" if not limitations else "unavailable",
        "limitations": limitations,
        "estimator_version": "consistency-information-weighted-1.0.0",
    }


__all__ = [
    "continuous_transfer",
    "duration_context_involvement",
    "information_weighted_consistency",
    "overdispersed_death_exposure",
    "stabilized_finishing",
]
