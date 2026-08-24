"""Deterministic family/branch hierarchical error-control helpers."""

from __future__ import annotations

from collections.abc import Mapping

from app.player_analysis_v6.constants import FDR_Q, FINDING_FAMILY_KEYS
from app.player_analysis_v6.family_statistics import benjamini_hochberg_five


def _benjamini_hochberg(values: Mapping[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    count = len(ordered)
    adjusted: dict[str, float] = {}
    running = 1.0
    for reverse_index, (key, value) in enumerate(reversed(ordered), start=1):
        rank = count - reverse_index + 1
        running = min(running, float(value) * count / max(rank, 1))
        adjusted[key] = max(0.0, min(1.0, running))
    return adjusted


def hierarchical_qualification(
    family_p_values: Mapping[str, float | None],
    branch_p_values: Mapping[str, Mapping[str, float | None]],
    *,
    q: float = FDR_Q,
) -> dict[str, dict[str, object]]:
    if set(family_p_values) != set(FINDING_FAMILY_KEYS):
        raise ValueError("hierarchical qualification requires exactly five family roots")
    family_q = benjamini_hochberg_five(family_p_values)
    result: dict[str, dict[str, object]] = {}
    for family in FINDING_FAMILY_KEYS:
        qualified = family_q[family] <= q
        finite = {
            key: float(value)
            for key, value in branch_p_values.get(family, {}).items()
            if value is not None and 0 <= float(value) <= 1
        }
        branch_q = _benjamini_hochberg(finite) if qualified and finite else {
            key: 1.0 for key in finite
        }
        result[family] = {
            "raw_p_value": family_p_values[family],
            "adjusted_q_value": family_q[family],
            "qualified": qualified,
            "branches": {
                key: {
                    "raw_p_value": finite[key],
                    "adjusted_q_value": branch_q[key],
                    "qualified": qualified and branch_q[key] <= q,
                }
                for key in sorted(finite)
            },
        }
    return result


__all__ = ["hierarchical_qualification"]
