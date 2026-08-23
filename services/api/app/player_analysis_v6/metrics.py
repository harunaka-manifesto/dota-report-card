"""Summary-only v6 metric formulas and multi-signal comparisons."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .constants import EXPRESSION_VERSION, MIN_CONSISTENCY_SESSIONS


def _finite(value: Any) -> float | None:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def shannon_entropy(counts: Mapping[Any, int | float] | Sequence[int | float]) -> float:
    """Return Shannon entropy using natural logarithms."""

    values = list(counts.values()) if isinstance(counts, Mapping) else list(counts)
    clean = [max(0.0, float(value)) for value in values if _finite(value) is not None]
    total = sum(clean)
    if total <= 0:
        return 0.0
    return -sum((value / total) * math.log(value / total) for value in clean if value > 0)


def shannon_effective_count(counts: Mapping[Any, int | float] | Sequence[int | float]) -> float:
    """Return ``exp(-Σ p ln p)`` (the Shannon effective count)."""

    values = list(counts.values()) if isinstance(counts, Mapping) else list(counts)
    if not any(_finite(value) is not None and float(value) > 0 for value in values):
        return 0.0
    return math.exp(shannon_entropy(values))


effective_hero_count = shannon_effective_count
effective_toolkit_count = shannon_effective_count


def match_weighted_effective_count(
    taxonomy_by_match: Mapping[Any, Any],
    *,
    min_coverage: float = 0.80,
) -> tuple[float | None, float]:
    """Compute toolkit breadth from match-weighted taxonomy labels.

    ``taxonomy_by_match`` maps each match to one taxonomy label or an iterable
    of labels.  A match with multiple labels contributes equally to each of
    those labels.  The result is unavailable when taxonomy coverage is below
    the v6 80% gate.
    """

    counts: dict[str, float] = {}
    total = len(taxonomy_by_match)
    covered = 0
    for raw in taxonomy_by_match.values():
        labels: tuple[str, ...]
        if raw is None:
            continue
        if isinstance(raw, str):
            labels = (raw,)
        elif isinstance(raw, Mapping):
            labels = tuple(str(key) for key, value in raw.items() if value)
        else:
            try:
                labels = tuple(str(item) for item in raw if item is not None)
            except TypeError:
                labels = (str(raw),)
        labels = tuple(dict.fromkeys(label for label in labels if label))
        if not labels:
            continue
        covered += 1
        weight = 1.0 / len(labels)
        for label in labels:
            counts[label] = counts.get(label, 0.0) + weight
    coverage = covered / total if total else 0.0
    return (shannon_effective_count(counts) if coverage >= min_coverage else None), coverage


def involvement_per_minute(kills: Any, assists: Any, duration_seconds: Any) -> float | None:
    k, a, duration = _finite(kills), _finite(assists), _finite(duration_seconds)
    if k is None or a is None or duration is None or duration <= 0:
        return None
    return (max(0.0, k) + max(0.0, a)) / (duration / 60.0)


def finishing_share(kills: Any, assists: Any) -> float | None:
    k, a = _finite(kills), _finite(assists)
    if k is None or a is None or k < 0 or a < 0 or k + a <= 0:
        # A zero-event match carries no information about finishing share.
        return None
    return k / (k + a)


def death_exposure_per_ten_minutes(deaths: Any, duration_seconds: Any) -> float | None:
    d, duration = _finite(deaths), _finite(duration_seconds)
    if d is None or duration is None or duration <= 0 or d < 0:
        return None
    return d / (duration / 60.0) * 10.0


def context_adjusted(value: float | None, baseline: float | None) -> float | None:
    """Return a signed difference from a context baseline.

    Ratios would be unstable near zero and mean different things across the
    seven Elements, so v6 stores the metric's native-unit difference.
    """

    if value is None or baseline is None:
        return None
    return float(value) - float(baseline)


def _signal_direction(value: Any, *, practical_margin: float, lower_is_better: bool = False) -> tuple[str, bool, float | None]:
    """Normalise a signal value into direction, confidence, and delta."""

    if isinstance(value, Mapping):
        if "direction" in value:
            direction = str(value.get("direction", "unknown"))
            confident = bool(value.get("confident", True))
            delta = _finite(value.get("delta", value.get("value")))
            return direction if direction in {"positive", "negative", "neutral", "mixed", "unknown"} else "unknown", confident, delta
        if "delta" in value:
            value = value["delta"]
        elif "stretch" in value and ("familiar" in value or "core" in value):
            value = float(value["stretch"]) - float(value.get("familiar", value.get("core")))
        elif "core" in value and "stretch" in value:
            value = float(value["stretch"]) - float(value["core"])
    if isinstance(value, (tuple, list)) and len(value) == 2:
        left, right = _finite(value[0]), _finite(value[1])
        value = None if left is None or right is None else right - left
    delta = _finite(value)
    if delta is None:
        return "unknown", False, None
    if lower_is_better:
        delta = -delta
    if delta > practical_margin:
        return "positive", True, delta
    if delta < -practical_margin:
        return "negative", True, delta
    return "neutral", True, delta


@dataclass(frozen=True, slots=True)
class MultiSignalComparison:
    direction: Literal["positive", "negative", "mixed", "unknown"]
    component_directions: Mapping[str, str]
    component_deltas: Mapping[str, float | None]
    agreeing_components: tuple[str, ...] = ()
    opposing_components: tuple[str, ...] = ()
    unknown_components: tuple[str, ...] = ()
    confident_components: tuple[str, ...] = ()
    version: str = EXPRESSION_VERSION

    @property
    def agreement_count(self) -> int:
        return len(self.agreeing_components)

    @property
    def mixed(self) -> bool:
        return self.direction == "mixed"

    def as_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "component_directions": dict(self.component_directions),
            "component_deltas": dict(self.component_deltas),
            "agreeing_components": list(self.agreeing_components),
            "opposing_components": list(self.opposing_components),
            "unknown_components": list(self.unknown_components),
            "confident_components": list(self.confident_components),
            "version": self.version,
        }


def compare_multi_signals(
    signals: Mapping[str, Any],
    *,
    practical_margin: float = 0.0,
    lower_is_better: Mapping[str, bool] | None = None,
) -> MultiSignalComparison:
    """Compare three signals without collapsing a conflict into a mean.

    A direction is publishable only when at least two components agree and no
    confidently opposing component exists.  Any confident opposition yields
    ``mixed``; fewer than two usable signals yields ``unknown``.
    """

    lower_is_better = lower_is_better or {}
    directions: dict[str, str] = {}
    deltas: dict[str, float | None] = {}
    confident: set[str] = set()
    for key in ("outcome", "activity", "survival"):
        if key not in signals:
            directions[key], deltas[key] = "unknown", None
            continue
        direction, is_confident, delta = _signal_direction(
            signals[key], practical_margin=practical_margin, lower_is_better=lower_is_better.get(key, False)
        )
        directions[key], deltas[key] = direction, delta
        if is_confident and direction in {"positive", "negative"}:
            confident.add(key)
    positive = tuple(key for key in directions if directions[key] == "positive" and key in confident)
    negative = tuple(key for key in directions if directions[key] == "negative" and key in confident)
    unknown = tuple(key for key in directions if directions[key] in {"unknown", "neutral"} or key not in confident)
    result: Literal["positive", "negative", "mixed", "unknown"]
    agreeing: tuple[str, ...]
    opposing: tuple[str, ...]
    if positive and negative:
        result = "mixed"
        agreeing = positive if len(positive) >= len(negative) else negative
        opposing = negative if agreeing is positive else positive
    elif len(positive) >= 2:
        result, agreeing, opposing = "positive", positive, ()
    elif len(negative) >= 2:
        result, agreeing, opposing = "negative", negative, ()
    else:
        result, agreeing, opposing = ("unknown" if len(confident) == 0 else "mixed"), (), ()
    return MultiSignalComparison(result, directions, deltas, tuple(agreeing), tuple(opposing), unknown, tuple(sorted(confident)))


def compare_transfer_signals(
    signals: Mapping[str, Any] | None = None,
    *,
    outcome: Any = None,
    activity: Any = None,
    survival: Any = None,
    familiar: Mapping[str, Any] | None = None,
    core: Mapping[str, Any] | None = None,
    stretch: Mapping[str, Any] | None = None,
    practical_margin: float = 0.0,
) -> MultiSignalComparison:
    supplied = dict(signals or {})
    reference = familiar or core
    if reference is not None and stretch is not None:
        for component in ("outcome", "activity", "survival"):
            if component not in supplied and component in reference and component in stretch:
                left, right = _finite(reference[component]), _finite(stretch[component])
                supplied[component] = None if left is None or right is None else right - left
    if outcome is not None:
        supplied["outcome"] = outcome
    if activity is not None:
        supplied["activity"] = activity
    if survival is not None:
        supplied["survival"] = survival
    return compare_multi_signals(supplied, practical_margin=practical_margin)


transfer_signal_agreement = compare_transfer_signals
multi_signal_agreement = compare_multi_signals


def robust_mad(values: Sequence[float]) -> float:
    clean = sorted(float(value) for value in values if _finite(value) is not None)
    if not clean:
        return math.nan
    middle = len(clean) // 2
    median = clean[middle] if len(clean) % 2 else (clean[middle - 1] + clean[middle]) / 2
    deviations = sorted(abs(value - median) for value in clean)
    middle = len(deviations) // 2
    return deviations[middle] if len(deviations) % 2 else (deviations[middle - 1] + deviations[middle]) / 2


def robust_dispersion(values: Sequence[float]) -> float | None:
    clean = [float(value) for value in values if _finite(value) is not None]
    if not clean:
        return None
    median = sorted(clean)[len(clean) // 2]
    scale = abs(median)
    mad = robust_mad(clean)
    if not math.isfinite(mad):
        return None
    return mad / scale if scale > 1e-9 else mad


@dataclass(frozen=True, slots=True)
class ConsistencyComparison:
    direction: Literal["stable", "variable", "mixed", "unknown"]
    component_directions: Mapping[str, str]
    component_dispersion: Mapping[str, float | None]
    agreeing_components: tuple[str, ...] = ()
    opposing_components: tuple[str, ...] = ()
    usable_sessions: int = 0
    required_sessions: int = MIN_CONSISTENCY_SESSIONS
    version: str = EXPRESSION_VERSION

    @property
    def qualifies(self) -> bool:
        return self.usable_sessions >= self.required_sessions and self.direction in {"stable", "variable"}

    def as_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "component_directions": dict(self.component_directions),
            "component_dispersion": dict(self.component_dispersion),
            "agreeing_components": list(self.agreeing_components),
            "opposing_components": list(self.opposing_components),
            "usable_sessions": self.usable_sessions,
            "required_sessions": self.required_sessions,
            "qualifies": self.qualifies,
            "version": self.version,
        }


def _component_dispersion(value: Any) -> tuple[str, float | None]:
    if isinstance(value, str):
        lowered = value.lower()
        if lowered in {"stable", "consistent", "low"}:
            return "stable", 0.0
        if lowered in {"variable", "volatile", "high"}:
            return "variable", 1.0
        return "unknown", None
    if isinstance(value, Mapping) and "direction" in value:
        direction = str(value["direction"]).lower()
        return ("stable" if direction in {"stable", "consistent"} else "variable" if direction in {"variable", "volatile"} else "unknown", _finite(value.get("dispersion")))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        dispersion = robust_dispersion([item for item in value if _finite(item) is not None])
        if dispersion is None:
            return "unknown", None
        return ("stable" if dispersion <= 0.10 else "variable"), dispersion
    numeric = _finite(value)
    if numeric is None:
        return "unknown", None
    return ("stable" if numeric <= 0.10 else "variable"), numeric


def compare_consistency_signals(
    signals: Mapping[str, Any] | Sequence[Mapping[str, Any]],
    *,
    usable_sessions: int | None = None,
    required_sessions: int = MIN_CONSISTENCY_SESSIONS,
    practical_margin: float = 0.10,
) -> ConsistencyComparison:
    if not isinstance(signals, Mapping):
        rows = tuple(signals)
        grouped: dict[str, list[Any]] = {"outcome": [], "activity": [], "death_exposure": []}
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            for key in grouped:
                if key in row:
                    grouped[key].append(row[key])
        signals = grouped
        if usable_sessions is None:
            usable_sessions = len(rows)
    directions: dict[str, str] = {}
    dispersions: dict[str, float | None] = {}
    for key in ("outcome", "activity", "death_exposure", "survival"):
        if key not in signals:
            continue
        direction, dispersion = _component_dispersion(signals[key])
        directions[key] = direction
        dispersions[key] = dispersion
    stable: tuple[str, ...] = tuple(key for key, direction in directions.items() if direction == "stable")
    variable: tuple[str, ...] = tuple(key for key, direction in directions.items() if direction == "variable")
    agreeing: tuple[str, ...]
    opposing: tuple[str, ...]
    result: Literal["stable", "variable", "mixed", "unknown"]
    if len(stable) >= 2 and len(variable) == 0:
        result = "stable"
        agreeing, opposing = stable, variable
    elif len(variable) >= 2 and len(stable) == 0:
        result = "variable"
        agreeing, opposing = variable, stable
    elif len(stable) >= 2 and len(variable) < 2:
        result = "stable"
        agreeing, opposing = stable, variable
    elif len(variable) >= 2 and len(stable) < 2:
        result = "variable"
        agreeing, opposing = variable, stable
    else:
        result = "unknown" if not stable and not variable else "mixed"
        agreeing, opposing = (), ()
    session_count = int(usable_sessions if usable_sessions is not None else max((len(value) for value in signals.values() if isinstance(value, Sequence) and not isinstance(value, (str, bytes))), default=0))
    if session_count < required_sessions and result in {"stable", "variable"}:
        result = "unknown"
    return ConsistencyComparison(result, directions, dispersions, tuple(agreeing), tuple(opposing), session_count, required_sessions)


consistency_signal_agreement = compare_consistency_signals
consistency_from_signals = compare_consistency_signals


__all__ = [
    "shannon_entropy",
    "shannon_effective_count",
    "effective_hero_count",
    "effective_toolkit_count",
    "match_weighted_effective_count",
    "involvement_per_minute",
    "finishing_share",
    "death_exposure_per_ten_minutes",
    "context_adjusted",
    "MultiSignalComparison",
    "compare_multi_signals",
    "compare_transfer_signals",
    "transfer_signal_agreement",
    "multi_signal_agreement",
    "robust_mad",
    "robust_dispersion",
    "ConsistencyComparison",
    "compare_consistency_signals",
    "consistency_signal_agreement",
    "consistency_from_signals",
]
