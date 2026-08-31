"""V6.1 family/branch multiplicity procedures.

The fixture helpers remain offline-only. Production requires the complete
session-cluster evidence produced by the runtime estimator path.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Mapping, Sequence
from typing import Any

from app.player_analysis_v6.constants import FINDING_FAMILY_KEYS

from .semantic_outcomes import SEMANTIC_OUTCOME_CATALOG

_TRANSFER_COMPONENTS = ("outcome", "activity", "survival")


def _empirical_two_sided_p(samples: list[float], null: float = 0.0) -> float:
    if not samples:
        raise ValueError("production bootstrap evidence cannot be empty")
    if not all(math.isfinite(value) for value in samples):
        raise ValueError("production bootstrap evidence must be finite")
    observed = abs(statistics.fmean(samples) - null)
    extreme = sum(abs(value - null) >= observed for value in samples)
    return (extreme + 1) / (len(samples) + 1)


def _production_p(samples: Sequence[float]) -> float:
    """Return a fail-closed p-value for unsupported runtime evidence."""

    if isinstance(samples, (str, bytes)) or not isinstance(samples, Sequence) or not samples:
        return 1.0
    try:
        values = [float(value) for value in samples]
    except (TypeError, ValueError):
        return 1.0
    if not all(math.isfinite(value) for value in values):
        return 1.0
    return _empirical_two_sided_p(values)


def _bounded_p(effect: float, opportunities: int, *, scale: float) -> float:
    if opportunities < 12 or scale <= 0:
        return 1.0
    statistic = opportunities * (effect / scale) ** 2
    return max(1e-12, min(1.0, math.exp(-0.5 * statistic)))


def _equivalence_p(effect: float, opportunities: int, *, rope: float) -> float:
    if opportunities < 12 or abs(effect) >= rope:
        return 1.0
    standard_error = rope * math.sqrt(12 / opportunities)
    z_value = (rope - abs(effect)) / max(standard_error, 1e-9)
    return max(1e-12, min(1.0, math.exp(-0.5 * z_value**2)))


def _transfer_component_vector(
    deltas: Mapping[str, Any] | None,
    ropes: Mapping[str, Any],
) -> dict[str, float] | None:
    if not isinstance(deltas, Mapping):
        return None
    vector: dict[str, float] = {}
    for component in _TRANSFER_COMPONENTS:
        value = deltas.get(component)
        rope = ropes.get(component)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            or isinstance(rope, bool)
            or not isinstance(rope, (int, float))
            or not math.isfinite(float(rope))
            or float(rope) <= 0
        ):
            return None
        vector[component] = float(value)
    return vector


def _transfer_max_statistic(
    deltas: Mapping[str, Any] | None,
    ropes: Mapping[str, Any],
) -> float | None:
    vector = _transfer_component_vector(deltas, ropes)
    if vector is None:
        return None
    return max(abs(vector[component]) / float(ropes[component]) for component in _TRANSFER_COMPONENTS)


def _transfer_component_bootstrap_p(
    *,
    point_deltas: Mapping[str, Any] | None,
    samples: Mapping[str, Sequence[Any]] | None,
    ropes: Mapping[str, Any],
) -> float:
    point = _transfer_component_vector(point_deltas, ropes)
    if point is None or not isinstance(samples, Mapping):
        return 1.0
    component_samples: dict[str, tuple[float, ...]] = {}
    for component in _TRANSFER_COMPONENTS:
        values = samples.get(component)
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
            return 1.0
        try:
            parsed = tuple(float(value) for value in values)
        except (TypeError, ValueError):
            return 1.0
        if not all(math.isfinite(value) for value in parsed):
            return 1.0
        component_samples[component] = parsed
    lengths = {len(values) for values in component_samples.values()}
    if len(lengths) != 1:
        return 1.0
    observed = _transfer_max_statistic(point, ropes)
    if observed is None:
        return 1.0
    null_statistics = []
    for values in zip(*(component_samples[component] for component in _TRANSFER_COMPONENTS), strict=True):
        null_statistics.append(
            max(
                abs(value - point[component]) / float(ropes[component])
                for component, value in zip(_TRANSFER_COMPONENTS, values, strict=True)
            )
        )
    return (1 + sum(statistic >= observed for statistic in null_statistics)) / (
        len(null_statistics) + 1
    )


def _bootstrap_departure_p(point: float, samples: Sequence[float]) -> float:
    """Return a null-centered two-sided bootstrap departure p-value."""

    if (
        isinstance(point, bool)
        or not isinstance(point, (int, float))
        or not math.isfinite(float(point))
        or isinstance(samples, (str, bytes))
        or not isinstance(samples, Sequence)
        or not samples
    ):
        return 1.0
    try:
        point_value = float(point)
        values = tuple(float(value) for value in samples)
    except (TypeError, ValueError):
        return 1.0
    if not all(math.isfinite(value) for value in values):
        return 1.0
    residuals = tuple(value - point_value for value in values)
    observed = abs(point_value)
    return (1 + sum(abs(residual) >= observed for residual in residuals)) / (len(values) + 1)


def _bootstrap_equivalence_p(point: float, samples: Sequence[float], rope: float) -> float:
    """Return a two-boundary bootstrap TOST p-value for ROPE equivalence."""

    if (
        isinstance(point, bool)
        or not isinstance(point, (int, float))
        or not math.isfinite(float(point))
        or isinstance(rope, bool)
        or not isinstance(rope, (int, float))
        or not math.isfinite(float(rope))
        or float(rope) <= 0
        or isinstance(samples, (str, bytes))
        or not isinstance(samples, Sequence)
        or not samples
    ):
        return 1.0
    try:
        point_value = float(point)
        rope_value = float(rope)
        values = tuple(float(value) for value in samples)
    except (TypeError, ValueError):
        return 1.0
    if not all(math.isfinite(value) for value in values):
        return 1.0
    residuals = tuple(value - point_value for value in values)
    lower_p = (1 + sum(residual >= point_value + rope_value for residual in residuals)) / (
        len(residuals) + 1
    )
    upper_p = (1 + sum(residual <= point_value - rope_value for residual in residuals)) / (
        len(residuals) + 1
    )
    return max(lower_p, upper_p)


def _simes_p(p_values: Sequence[float]) -> float:
    """Return a fail-closed Simes combination of p-values."""

    if isinstance(p_values, (str, bytes)) or not isinstance(p_values, Sequence) or not p_values:
        return 1.0
    if any(isinstance(value, bool) for value in p_values):
        return 1.0
    try:
        values = tuple(float(value) for value in p_values)
    except (TypeError, ValueError):
        return 1.0
    if any(
        isinstance(value, bool)
        or not math.isfinite(value)
        or value < 0.0
        or value > 1.0
        for value in values
    ):
        return 1.0
    ordered = sorted(values)
    return min(
        1.0,
        min(len(ordered) * value / rank for rank, value in enumerate(ordered, start=1)),
    )


_TRANSFER_UNSUPPORTED_BRANCH_P_VALUES = {
    "clean_transfer": 1.0,
    "results_stop_first": 1.0,
    "expression_stops_first": 1.0,
    "involvement_boundary": 1.0,
    "exposure_boundary": 1.0,
    "localized_function_bottleneck": 1.0,
    "no_transfer": 1.0,
}


def _unsupported_transfer_branch_p_values() -> dict[str, float]:
    return dict(_TRANSFER_UNSUPPORTED_BRANCH_P_VALUES)


def _transfer_branch_bootstrap_p_values(
    point_deltas: Mapping[str, Any] | None,
    samples: Mapping[str, Sequence[Any]] | None,
    ropes: Mapping[str, Any],
) -> dict[str, float]:
    """Return claim-aligned transfer branch p-values from component draws."""

    components = _TRANSFER_COMPONENTS
    point = _transfer_component_vector(point_deltas, ropes)
    if point is None or not isinstance(samples, Mapping):
        return _unsupported_transfer_branch_p_values()
    parsed_samples: dict[str, tuple[float, ...]] = {}
    for component in components:
        values = samples.get(component)
        if (
            isinstance(values, (str, bytes))
            or not isinstance(values, Sequence)
            or not values
        ):
            return _unsupported_transfer_branch_p_values()
        try:
            parsed = tuple(float(value) for value in values)
        except (TypeError, ValueError):
            return _unsupported_transfer_branch_p_values()
        if not all(math.isfinite(value) for value in parsed):
            return _unsupported_transfer_branch_p_values()
        parsed_samples[component] = parsed
    if len({len(values) for values in parsed_samples.values()}) != 1:
        return _unsupported_transfer_branch_p_values()

    departure = {
        component: _bootstrap_departure_p(point[component], parsed_samples[component])
        for component in components
    }
    equivalence = {
        component: _bootstrap_equivalence_p(
            point[component],
            parsed_samples[component],
            float(ropes[component]),
        )
        for component in components
    }
    return {
        "clean_transfer": max(equivalence.values()),
        "results_stop_first": max(
            departure["outcome"], equivalence["activity"], equivalence["survival"]
        ),
        "expression_stops_first": max(
            equivalence["outcome"],
            min(1.0, 2.0 * min(departure["activity"], departure["survival"])),
        ),
        "involvement_boundary": max(departure["activity"], equivalence["survival"]),
        "exposure_boundary": max(equivalence["activity"], departure["survival"]),
        "localized_function_bottleneck": 1.0,
        "no_transfer": _transfer_component_bootstrap_p(
            point_deltas=point,
            samples=parsed_samples,
            ropes=ropes,
        ),
    }


def _valid_transfer_bootstrap_evidence(
    point_deltas: Mapping[str, Any] | None,
    samples: Mapping[str, Sequence[Any]] | None,
    ropes: Mapping[str, Any],
) -> bool:
    if _transfer_component_vector(point_deltas, ropes) is None or not isinstance(samples, Mapping):
        return False
    lengths = set()
    for component in _TRANSFER_COMPONENTS:
        values = samples.get(component)
        if isinstance(values, (str, bytes)) or not isinstance(values, Sequence) or not values:
            return False
        try:
            parsed = tuple(float(value) for value in values)
        except (TypeError, ValueError):
            return False
        if not all(math.isfinite(value) for value in parsed):
            return False
        lengths.add(len(parsed))
    return len(lengths) == 1


def _transfer_family_bootstrap_p(branch_p_values: Mapping[str, Any] | None) -> float:
    """Return the Simes omnibus p-value across all seven transfer branches."""

    expected = {
        "clean_transfer",
        "results_stop_first",
        "expression_stops_first",
        "involvement_boundary",
        "exposure_boundary",
        "localized_function_bottleneck",
        "no_transfer",
    }
    if not isinstance(branch_p_values, Mapping) or set(branch_p_values) != expected:
        return 1.0
    return _simes_p(tuple(branch_p_values.values()))


_POST_LOSS_STATE_KEYS = ("win", "one_loss", "two_plus_losses")
_POST_LOSS_BRANCH_P_KEYS = (
    "one_loss_runback",
    "two_loss_switch",
    "result_shaped_pool",
    "result_invariant_response",
    "adjustment_without_recovery",
)


def _ordered_post_loss_statistic(states: Mapping[str, Any] | None) -> float | None:
    """Calculate the ordered post-loss contrast, ignoring ``win_streak``."""

    if not isinstance(states, Mapping):
        return None
    available: list[tuple[float, float]] = []
    for state in _POST_LOSS_STATE_KEYS:
        if state not in states or states[state] is None:
            continue
        entry = states[state]
        if isinstance(entry, (str, bytes)) or not isinstance(entry, Sequence) or len(entry) != 2:
            return None
        mean, weight = entry
        if (
            isinstance(mean, bool)
            or not isinstance(mean, (int, float))
            or not math.isfinite(float(mean))
            or isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(float(weight))
            or float(weight) <= 0
        ):
            return None
        available.append((float(mean), float(weight)))
    if len(available) < 2:
        return None
    if len(available) == 2:
        return abs(available[1][0] - available[0][0])

    total_weight = sum(weight for _, weight in available)
    x_mean = sum(index * weight for index, (_, weight) in enumerate(available)) / total_weight
    y_mean = sum(mean * weight for mean, weight in available) / total_weight
    denominator = sum(
        weight * (index - x_mean) ** 2
        for index, (_, weight) in enumerate(available)
    )
    if denominator <= 0:
        return None
    slope = sum(
        weight * (index - x_mean) * (mean - y_mean)
        for index, (mean, weight) in enumerate(available)
    ) / denominator
    return abs(slope)


def _post_loss_metric_evidence(
    point_stats: Mapping[str, Any] | None,
    sample_stats: Mapping[str, Sequence[Any]] | None,
) -> tuple[dict[str, float], dict[str, tuple[float, ...]]] | None:
    if not isinstance(point_stats, Mapping) or not isinstance(sample_stats, Mapping):
        return None
    metric_keys = ("one_loss_departure", "two_loss_switch", "trend")
    if "trend" in point_stats:
        point: dict[str, float] = {}
        samples: dict[str, tuple[float, ...]] = {}
        for key in metric_keys:
            if key not in point_stats or key not in sample_stats:
                if key == "trend":
                    return None
                if (
                    key in point_stats
                    and point_stats[key] is not None
                ) or (
                    key in sample_stats
                    and sample_stats[key] not in (None, [])
                ):
                    return None
                continue
            value = point_stats[key]
            raw_samples = sample_stats[key]
            if (
                value is None
                or isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
                or isinstance(raw_samples, (str, bytes))
                or not isinstance(raw_samples, Sequence)
                or not raw_samples
            ):
                if key == "trend":
                    return None
                if value is None:
                    continue
                return None
            try:
                parsed = tuple(float(item) for item in raw_samples if item is not None)
            except (TypeError, ValueError):
                if key == "trend":
                    return None
                return None
            if not parsed or not all(math.isfinite(item) for item in parsed):
                if key == "trend":
                    return None
                if not parsed:
                    continue
                return None
            point[key] = float(value)
            samples[key] = parsed
        return (point, samples) if "trend" in point else None

    state_point: dict[str, tuple[float, float]] = {}
    state_samples: dict[str, tuple[float, ...]] = {}
    for state in _POST_LOSS_STATE_KEYS:
        entry = point_stats.get(state)
        if entry is None:
            continue
        if isinstance(entry, (str, bytes)) or not isinstance(entry, Sequence) or len(entry) != 2:
            return None
        mean, weight = entry
        if (
            isinstance(mean, bool)
            or not isinstance(mean, (int, float))
            or not math.isfinite(float(mean))
            or isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(float(weight))
            or float(weight) <= 0
        ):
            return None
        state_raw_samples: Any = sample_stats.get(state)
        if (
            isinstance(state_raw_samples, (str, bytes))
            or not isinstance(state_raw_samples, Sequence)
            or not state_raw_samples
        ):
            return None
        try:
            parsed = tuple(float(item) for item in state_raw_samples)
        except (TypeError, ValueError):
            return None
        if not all(math.isfinite(item) for item in parsed):
            return None
        state_point[state] = (float(mean), float(weight))
        state_samples[state] = parsed
    if len(state_point) < 2 or len({len(values) for values in state_samples.values()}) != 1:
        return None
    ordered_states = [state for state in _POST_LOSS_STATE_KEYS if state in state_point]
    point_metrics: dict[str, float] = {}
    if "win" in state_point and "one_loss" in state_point:
        point_metrics["one_loss_departure"] = abs(state_point["one_loss"][0] - state_point["win"][0])
    if "one_loss" in state_point and "two_plus_losses" in state_point:
        point_metrics["two_loss_switch"] = abs(
            state_point["two_plus_losses"][0] - state_point["one_loss"][0]
        )
    trend = _ordered_post_loss_statistic(state_point)
    if trend is None:
        return None
    point_metrics["trend"] = trend
    sample_metrics: dict[str, list[float]] = {key: [] for key in point_metrics}
    for index in range(len(next(iter(state_samples.values())))):
        draw = {state: state_samples[state][index] for state in ordered_states}
        if "win" in draw and "one_loss" in draw:
            sample_metrics["one_loss_departure"].append(abs(draw["one_loss"] - draw["win"]))
        if "one_loss" in draw and "two_plus_losses" in draw:
            sample_metrics["two_loss_switch"].append(
                abs(draw["two_plus_losses"] - draw["one_loss"])
            )
        trend = _ordered_post_loss_statistic({state: (draw[state], 1.0) for state in ordered_states})
        if trend is not None:
            sample_metrics["trend"].append(trend)
    return point_metrics, {key: tuple(value) for key, value in sample_metrics.items()}


def _post_loss_branch_bootstrap_p_values(
    point_stats: Mapping[str, Any] | None,
    sample_stats: Mapping[str, Sequence[Any]] | None,
    rope: float = 0.08,
) -> dict[str, float]:
    """Compose post-loss branch p-values from adjacent state evidence."""

    unsupported = {key: 1.0 for key in _POST_LOSS_BRANCH_P_KEYS}
    if isinstance(rope, bool) or not isinstance(rope, (int, float)) or not math.isfinite(float(rope)) or float(rope) <= 0:
        return unsupported
    evidence = _post_loss_metric_evidence(point_stats, sample_stats)
    if evidence is None:
        return unsupported
    point, samples = evidence
    departure = {
        key: _bootstrap_departure_p(point[key], samples[key])
        for key in point
    }
    equivalence = [
        _bootstrap_equivalence_p(point[key], samples[key], float(rope))
        for key in ("one_loss_departure", "two_loss_switch")
        if key in point
    ]
    return {
        "one_loss_runback": departure.get("one_loss_departure", 1.0),
        "two_loss_switch": departure.get("two_loss_switch", 1.0),
        "result_shaped_pool": departure["trend"],
        "result_invariant_response": max(equivalence, default=1.0),
        "adjustment_without_recovery": 1.0,
    }


def _post_loss_family_bootstrap_p(
    point_stats: Mapping[str, Any] | None,
    sample_stats: Mapping[str, Sequence[Any]] | None,
) -> float:
    """Return the post-loss family p-value from the ordered trend departure."""

    evidence = _post_loss_metric_evidence(point_stats, sample_stats)
    if evidence is None:
        return 1.0
    point, samples = evidence
    return _bootstrap_departure_p(point["trend"], samples["trend"])


def v61_family_p_values(
    *,
    portfolio_shape: Mapping[str, Any],
    transfer: Mapping[str, Any],
    result_response: Mapping[str, Any],
    session_curve: Mapping[str, Any],
    involvement: Mapping[str, Any],
    death_exposure: Mapping[str, Any],
) -> dict[str, float]:
    hero_jsd = float(portfolio_shape.get("hero_jsd_first_to_last", 0.0))
    job_jsd = float(portfolio_shape.get("job_jsd_first_to_last", 0.0))
    pool_effect = abs(hero_jsd - job_jsd)
    pool_p = _bounded_p(pool_effect, int(portfolio_shape.get("match_count", 0)), scale=0.12)

    reliable = transfer.get("bands", {}).get("reliable_stretch", {})
    transfer_deltas = [
        abs(float(value))
        for value in reliable.get("component_deltas", {}).values()
        if value is not None
    ]
    transfer_p = _bounded_p(
        max(transfer_deltas, default=0.0),
        int(reliable.get("match_count", 0)),
        scale=0.10,
    )

    states = result_response.get("states", {})
    movements = [
        float(state["mean_distance_movement"])
        for state in states.values()
        if state.get("available") and state.get("mean_distance_movement") is not None
    ]
    response_effect = max(movements, default=0.0) - min(movements, default=0.0)
    response_opportunities = sum(
        int(state.get("opportunities", 0)) for state in states.values() if state.get("available")
    )
    response_p = _bounded_p(response_effect, response_opportunities, scale=0.12)

    positions = session_curve.get("positions", {})
    position_rates = [
        float(position["result_rate"])
        for position in positions.values()
        if position.get("available") and position.get("result_rate") is not None
    ]
    session_effect = max(position_rates, default=0.0) - min(position_rates, default=0.0)
    session_opportunities = sum(
        int(position.get("sessions", 0)) for position in positions.values() if position.get("available")
    )
    session_p = _bounded_p(session_effect, session_opportunities, scale=0.15)
    expression_effects = []
    if involvement.get("estimate") is not None:
        expression_effects.append(abs(float(involvement["estimate"])) / 0.08)
    if death_exposure.get("estimate") is not None:
        expression_effects.append(abs(float(death_exposure["estimate"])) / 0.35)
    combat_opportunities = min(
        int(involvement.get("matches", 0)),
        int(death_exposure.get("matches", 0)),
    )
    combat_p = _bounded_p(
        max(expression_effects, default=0.0),
        combat_opportunities,
        scale=1.0,
    )
    return {
        "pool_shape": pool_p,
        "transfer": transfer_p,
        "post_loss_response": response_p,
        "combat_expression": combat_p,
        "session_drift": session_p,
    }


def v61_branch_p_values(
    *,
    portfolio_shape: Mapping[str, Any],
    transfer: Mapping[str, Any],
    result_response: Mapping[str, Any],
    session_curve: Mapping[str, Any],
    involvement: Mapping[str, Any],
    death_exposure: Mapping[str, Any],
) -> dict[str, dict[str, float]]:
    """Return one predeclared fixture statistic for every public branch."""

    values: dict[str, dict[str, float]] = {
        definition.family_key: {}
        for definition in SEMANTIC_OUTCOME_CATALOG
        if definition.rollout_status == "public_candidate"
    }
    for definition in SEMANTIC_OUTCOME_CATALOG:
        if definition.rollout_status == "public_candidate":
            values[definition.family_key][definition.semantic_outcome_key] = 1.0

    pool_n = int(portfolio_shape.get("match_count", 0))
    top_one = float(portfolio_shape.get("top_shares", {}).get("top_1", 0.0))
    hero_count = float(portfolio_shape.get("shannon_effective_heroes", 0.0))
    job_count = float(portfolio_shape.get("shannon_effective_jobs", 0.0))
    hero_jsd = float(portfolio_shape.get("hero_jsd_first_to_last", 0.0))
    job_jsd = float(portfolio_shape.get("job_jsd_first_to_last", 0.0))
    values["pool_shape"].update(
        {
            "hidden_center": _bounded_p(max(0.0, top_one - 0.25), pool_n, scale=0.10),
            "names_wide_jobs_narrow": _bounded_p(
                max(0.0, hero_count - job_count), pool_n, scale=1.0
            ),
            "names_narrow_jobs_wide": _bounded_p(
                max(0.0, job_count - hero_count), pool_n, scale=1.0
            ),
            "names_changed_jobs_held": max(
                _bounded_p(hero_jsd, pool_n, scale=0.10),
                _equivalence_p(job_jsd, pool_n, rope=0.06),
            ),
        }
    )
    if not portfolio_shape.get("taxonomy_sensitivity", {}).get("stable"):
        for key in (
            "names_wide_jobs_narrow",
            "names_narrow_jobs_wide",
            "names_changed_jobs_held",
        ):
            values["pool_shape"][key] = 1.0

    reliable = transfer.get("bands", {}).get("reliable_stretch", {})
    transfer_n = int(reliable.get("match_count", 0))
    deltas = reliable.get("component_deltas", {})
    outcome = float(deltas.get("outcome") or 0.0)
    activity = float(deltas.get("activity") or 0.0)
    survival = float(deltas.get("survival") or 0.0)
    reliable_equivalence = reliable.get("equivalent", {})
    outcome_eq = (
        _equivalence_p(outcome, transfer_n, rope=0.08)
        if reliable_equivalence.get("outcome")
        else 1.0
    )
    activity_eq = (
        _equivalence_p(activity, transfer_n, rope=0.08)
        if reliable_equivalence.get("activity")
        else 1.0
    )
    survival_eq = (
        _equivalence_p(survival, transfer_n, rope=0.35)
        if reliable_equivalence.get("survival")
        else 1.0
    )
    values["transfer"].update(
        {
            "clean_transfer": max(outcome_eq, activity_eq, survival_eq),
            "results_stop_first": max(
                _bounded_p(abs(outcome), transfer_n, scale=0.08),
                activity_eq,
                survival_eq,
            ),
            "expression_stops_first": max(
                outcome_eq,
                min(
                    _bounded_p(abs(activity), transfer_n, scale=0.08),
                    _bounded_p(abs(survival), transfer_n, scale=0.35),
                ),
            ),
            "involvement_boundary": _bounded_p(abs(activity), transfer_n, scale=0.08),
            "exposure_boundary": _bounded_p(abs(survival), transfer_n, scale=0.35),
            "localized_function_bottleneck": 1.0,
        }
    )

    states = result_response.get("states", {})
    one = states.get("one_loss", {})
    two = states.get("two_plus_losses", {})
    wins = states.get("win", {})
    response_n = sum(int(item.get("opportunities", 0)) for item in states.values())
    one_move = float(one.get("mean_distance_movement") or 0.0)
    two_move = float(two.get("mean_distance_movement") or 0.0)
    win_move = float(wins.get("mean_distance_movement") or 0.0)
    state_span = max(one_move, two_move, win_move) - min(one_move, two_move, win_move)
    response_intervals = [
        item["movement_interval"]
        for item in (one, two, wins)
        if item.get("available") and item.get("movement_interval") is not None
    ]
    equivalence_supported = bool(
        len(response_intervals) >= 2
        and max(float(interval[1]) for interval in response_intervals)
        - min(float(interval[0]) for interval in response_intervals)
        <= 0.08
    )
    values["post_loss_response"].update(
        {
            "one_loss_runback": _bounded_p(abs(one_move), int(one.get("opportunities", 0)), scale=0.10),
            "two_loss_switch": _bounded_p(abs(two_move - one_move), response_n, scale=0.10),
            "result_shaped_pool": _bounded_p(state_span, response_n, scale=0.10),
            "result_invariant_response": (
                _equivalence_p(state_span, response_n, rope=0.08)
                if equivalence_supported
                else 1.0
            ),
            "adjustment_without_recovery": 1.0,
        }
    )

    combat_n = min(int(involvement.get("matches", 0)), int(death_exposure.get("matches", 0)))
    involvement_effect = float(involvement.get("estimate") or 0.0)
    exposure_effect = float(death_exposure.get("estimate") or 0.0)
    involvement_interval = involvement.get("interval")
    exposure_interval = death_exposure.get("interval")
    involvement_eq = (
        _equivalence_p(involvement_effect, combat_n, rope=0.08)
        if involvement_interval is not None
        and float(involvement_interval[0]) >= -0.08
        and float(involvement_interval[1]) <= 0.08
        else 1.0
    )
    exposure_eq = (
        _equivalence_p(exposure_effect, combat_n, rope=0.35)
        if exposure_interval is not None
        and float(exposure_interval[0]) >= -0.35
        and float(exposure_interval[1]) <= 0.35
        else 1.0
    )
    values["combat_expression"].update(
        {
            "involvement_holds_exposure_moves": max(
                involvement_eq,
                _bounded_p(abs(exposure_effect), combat_n, scale=0.35),
            ),
            "exposure_holds_involvement_moves": max(
                exposure_eq,
                _bounded_p(abs(involvement_effect), combat_n, scale=0.08),
            ),
            "same_expression_different_results": 1.0,
            "different_expression_same_results": 1.0,
            "localized_variance": min(
                _bounded_p(abs(involvement_effect), combat_n, scale=0.08),
                _bounded_p(abs(exposure_effect), combat_n, scale=0.35),
            ),
        }
    )

    positions = session_curve.get("positions", {})
    rates = {
        key: float(item["result_rate"])
        for key, item in positions.items()
        if item.get("available") and item.get("result_rate") is not None
    }
    session_n = sum(int(item.get("sessions", 0)) for item in positions.values())
    opening_effect = abs(rates.get("g1", 0.0) - rates.get("g2", rates.get("g1", 0.0)))
    span = max(rates.values(), default=0.0) - min(rates.values(), default=0.0)
    values["session_drift"].update(
        {
            "opening_game_signature": _bounded_p(opening_effect, session_n, scale=0.12),
            "gradual_session_drift": _bounded_p(span, session_n, scale=0.15),
            "predeclared_breakpoint": _bounded_p(span, session_n, scale=0.15),
            "selection_only_drift": 1.0,
            "bounded_stopping_response": 1.0,
        }
    )
    return values


def v61_production_family_branch_p_values(
    *,
    semantic_calibration: Mapping[str, Any],
    bootstrap_family_samples: Mapping[str, Sequence[float]] | None = None,
    bootstrap_branch_samples: Mapping[str, Mapping[str, Sequence[float]]] | None = None,
    bootstrap_transfer_components: Mapping[str, Sequence[float]] | None = None,
    transfer_point: Mapping[str, Any] | None = None,
    transfer_ropes: Mapping[str, Any] | None = None,
    bootstrap_post_loss_point: Mapping[str, Any] | None = None,
    bootstrap_post_loss_samples: Mapping[str, Sequence[Any]] | None = None,
) -> tuple[dict[str, float], dict[str, dict[str, float]]]:
    """Return artifact-driven omnibus/branch p-values for production mode.

    Missing registry shape is a configuration error. Empty or invalid runtime
    evidence is unsupported data and returns ``p=1`` so the hierarchy
    suppresses the affected family and branches.
    """

    if semantic_calibration.get("branch_procedure") != "qualified-family-bh":
        raise ValueError("V6.1 production semantic calibration procedure mismatch")
    public = [
        definition
        for definition in SEMANTIC_OUTCOME_CATALOG
        if definition.rollout_status == "public_candidate"
    ]
    if not isinstance(bootstrap_family_samples, Mapping):
        raise ValueError("V6.1 production family bootstrap evidence is required")
    if not isinstance(bootstrap_branch_samples, Mapping):
        raise ValueError("V6.1 production branch bootstrap evidence is required")
    family_samples = dict(bootstrap_family_samples)
    branch_samples = dict(bootstrap_branch_samples)
    if set(family_samples) != set(FINDING_FAMILY_KEYS):
        raise ValueError("V6.1 production family evidence must cover exactly five family roots")
    if set(branch_samples) != set(FINDING_FAMILY_KEYS):
        raise ValueError("V6.1 production branch evidence must cover exactly five family roots")
    expected_branches = {
        family: {
            definition.semantic_outcome_key
            for definition in public
            if definition.family_key == family
        }
        for family in FINDING_FAMILY_KEYS
    }
    for family in FINDING_FAMILY_KEYS:
        samples = family_samples[family]
        if isinstance(samples, (str, bytes)) or not isinstance(samples, Sequence):
            raise ValueError(f"V6.1 production family evidence is missing for {family}")
        branches = branch_samples[family]
        if not isinstance(branches, Mapping) or set(branches) != expected_branches[family]:
            raise ValueError(f"V6.1 production branch registry is incomplete for {family}")
        for branch, branch_samples_for_key in branches.items():
            if (
                isinstance(branch_samples_for_key, (str, bytes))
                or not isinstance(branch_samples_for_key, Sequence)
            ):
                raise ValueError(f"V6.1 production branch evidence is missing for {branch}")
    family_values = {
        family: _production_p(family_samples[family])
        for family in FINDING_FAMILY_KEYS
    }
    branch_values: dict[str, dict[str, float]] = {family: {} for family in FINDING_FAMILY_KEYS}
    for definition in public:
        sample = branch_samples[definition.family_key][definition.semantic_outcome_key]
        branch_values[definition.family_key][definition.semantic_outcome_key] = _production_p(sample)

    if (
        bootstrap_transfer_components is not None
        and transfer_point is not None
        and transfer_ropes is not None
        and _valid_transfer_bootstrap_evidence(
            transfer_point,
            bootstrap_transfer_components,
            transfer_ropes,
        )
    ):
        transfer_branches = _transfer_branch_bootstrap_p_values(
            transfer_point,
            bootstrap_transfer_components,
            transfer_ropes,
        )
        family_values["transfer"] = _transfer_family_bootstrap_p(transfer_branches)
        for branch in expected_branches["transfer"]:
            if branch in transfer_branches:
                branch_values["transfer"][branch] = transfer_branches[branch]

    post_loss_evidence = _post_loss_metric_evidence(
        bootstrap_post_loss_point,
        bootstrap_post_loss_samples,
    )
    if post_loss_evidence is not None:
        family_values["post_loss_response"] = _post_loss_family_bootstrap_p(
            bootstrap_post_loss_point,
            bootstrap_post_loss_samples,
        )
        post_loss_branches = _post_loss_branch_bootstrap_p_values(
            bootstrap_post_loss_point,
            bootstrap_post_loss_samples,
        )
        for branch in expected_branches["post_loss_response"]:
            if branch in post_loss_branches:
                branch_values["post_loss_response"][branch] = post_loss_branches[branch]
    return family_values, branch_values


__all__ = [
    "v61_branch_p_values",
    "v61_family_p_values",
    "v61_production_family_branch_p_values",
]
