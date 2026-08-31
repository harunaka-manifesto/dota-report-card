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
_FIXTURE_TRANSFER_ROPES = {"outcome": 0.08, "activity": 0.08, "survival": 0.35}


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


def _fixture_no_transfer_p(transfer: Mapping[str, Any]) -> float:
    if transfer.get("frontier", "core") != "core":
        return 1.0
    reliable = transfer.get("bands", {}).get("reliable_stretch", {})
    if reliable.get("supported") is not True:
        return 1.0
    equivalent = reliable.get("equivalent")
    if not isinstance(equivalent, Mapping) or any(
        not isinstance(equivalent.get(component), bool) for component in _TRANSFER_COMPONENTS
    ):
        return 1.0
    if any(equivalent.values()):
        return 1.0
    statistic = _transfer_max_statistic(
        reliable.get("component_deltas"), _FIXTURE_TRANSFER_ROPES
    )
    if statistic is None or statistic <= 1.0:
        return 1.0
    return _bounded_p(statistic, int(reliable.get("match_count", 0)), scale=1.0)


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
    transfer_statistic = _transfer_max_statistic(
        reliable.get("component_deltas"), _FIXTURE_TRANSFER_ROPES
    )
    transfer_p = _bounded_p(
        transfer_statistic if transfer_statistic is not None else 0.0,
        int(reliable.get("match_count", 0)),
        scale=1.0,
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
    if "bands" in transfer:
        values["transfer"]["no_transfer"] = _fixture_no_transfer_p(transfer)

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
    if (
        bootstrap_transfer_components is not None
        and transfer_point is not None
        and transfer_ropes is not None
    ):
        family_values["transfer"] = _transfer_component_bootstrap_p(
            point_deltas=transfer_point,
            samples=bootstrap_transfer_components,
            ropes=transfer_ropes,
        )
    branch_values: dict[str, dict[str, float]] = {family: {} for family in FINDING_FAMILY_KEYS}
    for definition in public:
        sample = branch_samples[definition.family_key][definition.semantic_outcome_key]
        branch_values[definition.family_key][definition.semantic_outcome_key] = _production_p(sample)
    return family_values, branch_values


__all__ = [
    "v61_branch_p_values",
    "v61_family_p_values",
    "v61_production_family_branch_p_values",
]
