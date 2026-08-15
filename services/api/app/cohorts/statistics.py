from __future__ import annotations

from collections.abc import Iterable
from math import erf, log, sqrt
from statistics import median


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 1.0)
    proportion = successes / total
    denominator = 1 + z**2 / total
    centre = proportion + z**2 / (2 * total)
    margin = z * sqrt((proportion * (1 - proportion) + z**2 / (4 * total)) / total)
    return (max(0.0, (centre - margin) / denominator), min(1.0, (centre + margin) / denominator))


def normal_interval(values: Iterable[float], z: float = 1.96) -> tuple[float, float]:
    numbers = list(values)
    if not numbers:
        return (0.0, 0.0)
    centre = sum(numbers) / len(numbers)
    if len(numbers) < 2:
        return (centre, centre)
    mean = centre
    variance = sum((value - mean) ** 2 for value in numbers) / (len(numbers) - 1)
    margin = z * sqrt(variance / len(numbers))
    return (centre - margin, centre + margin)


def median_mad(values: Iterable[float]) -> tuple[float, float]:
    numbers = list(values)
    if not numbers:
        return (0.0, 0.0)
    centre = median(numbers)
    mad = median(abs(value - centre) for value in numbers)
    return centre, mad


def robust_effect(player_values: Iterable[float], cohort_values: Iterable[float]) -> float:
    player_centre, player_mad = median_mad(player_values)
    cohort_centre, cohort_mad = median_mad(cohort_values)
    scale = max(1.4826 * cohort_mad, 1.4826 * player_mad, 1e-9)
    return (player_centre - cohort_centre) / scale


def log_odds_ratio(
    player_successes: int, player_total: int, cohort_successes: int, cohort_total: int
) -> float:
    # Haldane-Anscombe correction keeps sparse cells finite.
    a = player_successes + 0.5
    b = player_total - player_successes + 0.5
    c = cohort_successes + 0.5
    d = cohort_total - cohort_successes + 0.5
    return log((a / b) / (c / d))


def benjamini_hochberg(p_values: Iterable[float]) -> list[float]:
    values = list(p_values)
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    adjusted = [1.0] * len(values)
    running = 1.0
    for rank, (index, value) in reversed(list(enumerate(indexed, start=1))):
        running = min(running, value * len(values) / rank)
        adjusted[index] = min(1.0, running)
    return adjusted


def normal_two_sided_p(value: float) -> float:
    return 1.0 - erf(abs(value) / sqrt(2))


def confidence_from_interval(interval: tuple[float, float], null: float = 0.0) -> str:
    if interval[0] <= null <= interval[1]:
        return "low"
    width = interval[1] - interval[0]
    if width < 0.25:
        return "high"
    return "moderate"
