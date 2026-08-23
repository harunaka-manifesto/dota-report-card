"""Family-level p-values and the fixed five-slot BH correction."""

from __future__ import annotations

import math
from collections.abc import Hashable, Mapping, Sequence
from typing import cast

from .constants import FDR_Q, FINDING_FAMILY_KEYS
from .statistics import benjamini_hochberg


def finite_sample_directional_p(
    replicates: Sequence[float],
    *,
    direction: str,
    practical_margin: float = 0.0,
    center: float = 0.0,
) -> float:
    """Return a one-sided finite-sample bootstrap departure p-value."""

    values = [float(value) for value in replicates if math.isfinite(float(value))]
    if not values or direction not in {"positive", "negative"}:
        return 1.0
    if direction == "positive":
        departures = sum(value <= center + practical_margin for value in values)
    else:
        departures = sum(value >= center - practical_margin for value in values)
    return (1.0 + departures) / (len(values) + 1.0)


def population_zone_p_value(
    replicates: Sequence[float],
    *,
    zone: str,
    low_cutoff: float | None = None,
    high_cutoff: float | None = None,
) -> float:
    values = [float(value) for value in replicates if math.isfinite(float(value))]
    if not values:
        return 1.0
    if zone == "high" and high_cutoff is not None:
        count = sum(value <= high_cutoff for value in values)
    elif zone == "low" and low_cutoff is not None:
        count = sum(value >= low_cutoff for value in values)
    else:
        return 1.0
    return (1.0 + count) / (len(values) + 1.0)


def second_smallest_p(values: Sequence[float | None]) -> float:
    usable = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
    return usable[1] if len(usable) >= 2 else 1.0


def family_p_values(
    *,
    pool_shape: float | None = None,
    transfer: Sequence[float | None] = (),
    post_loss_response: Sequence[float | None] = (),
    combat_expression: float | None = None,
    session_drift: Sequence[float | None] = (),
) -> dict[str, float]:
    """Build raw p-values for exactly the five approved family slots."""

    post_values = [float(value) for value in post_loss_response if value is not None and math.isfinite(float(value))]
    post_response_p = second_smallest_p(post_values[:3])
    post_support_p = min(post_values[3:], default=1.0)
    raw = {
        "pool_shape": 1.0 if pool_shape is None else float(pool_shape),
        "transfer": second_smallest_p(transfer),
        "post_loss_response": max(post_response_p, post_support_p),
        "combat_expression": 1.0 if combat_expression is None else float(combat_expression),
        "session_drift": second_smallest_p(session_drift),
    }
    return {family: min(1.0, max(0.0, raw.get(family, 1.0))) for family in FINDING_FAMILY_KEYS}


def benjamini_hochberg_five(raw_p_values: Mapping[str, float | None]) -> dict[str, float]:
    """Run BH across all five slots, treating unavailable tests as p=1."""

    values: dict[str, int | float] = {}
    for family in FINDING_FAMILY_KEYS:
        value = raw_p_values.get(family)
        values[family] = 1.0 if value is None else float(value)
    corrected = benjamini_hochberg(cast(Mapping[Hashable, int | float], values), q=FDR_Q)
    if not isinstance(corrected, dict):
        raise TypeError("BH correction must preserve the mapping shape")
    return {family: float(corrected[family]) for family in FINDING_FAMILY_KEYS}


def family_statistics(raw_p_values: Mapping[str, float | None]) -> dict[str, dict[str, float]]:
    raw: dict[str, float] = {}
    for family in FINDING_FAMILY_KEYS:
        value = raw_p_values.get(family)
        raw[family] = 1.0 if value is None else float(value)
    q_values = benjamini_hochberg_five(raw)
    return {family: {"raw_p_value": raw[family], "adjusted_q_value": q_values[family]} for family in FINDING_FAMILY_KEYS}


__all__ = [
    "finite_sample_directional_p",
    "population_zone_p_value",
    "second_smallest_p",
    "family_p_values",
    "benjamini_hochberg_five",
    "family_statistics",
]
