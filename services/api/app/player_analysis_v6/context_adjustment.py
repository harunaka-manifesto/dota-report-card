"""Per-match context baseline resolution for Free DNA v6."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from .baselines import BaselineContext, BaselineResolution, BaselineResolver


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def match_field(value: Any, key: str, default: Any = None) -> Any:
    """Read a field from either a summary row or a normalized detail match."""

    direct = _get(value, key)
    if direct is not None:
        return direct
    target = _get(value, "target_participant")
    if target is not None:
        nested = _get(target, key)
        if nested is not None:
            return nested
    aliases = {"start_time": "started_at", "started_at": "start_time"}
    alias = aliases.get(key)
    if alias is not None:
        aliased = _get(value, alias)
        if aliased is not None:
            return aliased
    return default


def match_hero_id(value: Any, default: Any = None) -> Any:
    hero = match_field(value, "hero_id")
    return hero if hero is not None else match_field(value, "target_hero_id", default)


def match_lane_context(value: Any, default: Any = None) -> Any:
    for key in ("lane_context", "role_hint", "role", "lane_role", "lane"):
        candidate = match_field(value, key)
        if candidate is not None:
            return candidate
    return default


def _hero_function(hero_id: Any, taxonomy: Mapping[Any, Any] | None) -> str | None:
    if taxonomy is None:
        return None
    entry = taxonomy.get(hero_id)
    if entry is None:
        return None
    if isinstance(entry, Mapping):
        for key in ("hero_function", "function", "job", "primary_function"):
            value = entry.get(key)
            if value:
                return str(value)
        roles = entry.get("roles") or entry.get("jobs") or entry.get("labels")
    else:
        roles = getattr(entry, "hero_function", None) or getattr(entry, "function", None)
        if roles is None:
            roles = getattr(entry, "roles", None) or getattr(entry, "jobs", None)
    if isinstance(roles, str):
        return roles
    if roles:
        return str(sorted(str(item) for item in roles)[0])
    return None


def match_context(match: Any, *, taxonomy_by_hero: Mapping[Any, Any] | None = None) -> BaselineContext:
    """Derive the literal non-MMR context for one match."""

    hero_id = match_hero_id(match)
    lane = match_lane_context(match)
    return BaselineContext(
        patch=match_field(match, "patch"),
        hero_id=hero_id,
        hero_function=_hero_function(hero_id, taxonomy_by_hero),
        lane_context=str(lane) if lane is not None else None,
    )


@dataclass(frozen=True, slots=True)
class AdjustedObservation:
    match: Any
    raw_value: float
    adjusted_value: float | None
    session_id: str
    context: BaselineContext
    resolution: BaselineResolution | None


@dataclass(frozen=True, slots=True)
class AdjustedMetricSeries:
    metric: str
    observations: tuple[AdjustedObservation, ...]
    raw_count: int
    resolved_count: int
    unresolved_count: int
    coverage: float
    fallback_level_counts: Mapping[str, int]
    baseline_artifact_version: str | None

    @property
    def values(self) -> tuple[float, ...]:
        return tuple(item.adjusted_value for item in self.observations if item.adjusted_value is not None)

    @property
    def session_ids(self) -> tuple[str, ...]:
        return tuple(item.session_id for item in self.observations if item.adjusted_value is not None)

    @property
    def matches(self) -> tuple[Any, ...]:
        return tuple(item.match for item in self.observations if item.adjusted_value is not None)

    def audit(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "raw_count": self.raw_count,
            "resolved_match_count": self.resolved_count,
            "unresolved_count": self.unresolved_count,
            "coverage": self.coverage,
            "fallback_level_counts": dict(self.fallback_level_counts),
            "baseline_artifact_version": self.baseline_artifact_version,
        }


def adjust_metric_per_match(
    matches: Sequence[Any],
    metric: str,
    raw_metric: Callable[[Any], float | None],
    *,
    baseline_resolver: BaselineResolver | None,
    taxonomy_by_hero: Mapping[Any, Any] | None = None,
) -> AdjustedMetricSeries:
    """Subtract a resolved baseline from every usable match independently.

    A missing cell makes only that match unavailable for the metric.  There is
    deliberately no report-wide pseudo-context or hard-coded fallback value.
    """

    observations: list[AdjustedObservation] = []
    raw_count = 0
    resolved_count = 0
    unresolved_count = 0
    fallback_levels: Counter[str] = Counter()
    version: str | None = getattr(baseline_resolver, "version", None)
    for index, match in enumerate(matches):
        raw = raw_metric(match)
        if raw is None:
            continue
        numeric = float(raw)
        if not math.isfinite(numeric):
            continue
        raw_count += 1
        context = match_context(match, taxonomy_by_hero=taxonomy_by_hero)
        session = _get(match, "session_id")
        session_id = str(session) if session not in (None, "") else f"session-{index + 1}"
        resolution: BaselineResolution | None = None
        adjusted: float | None = numeric
        if baseline_resolver is not None:
            resolution = baseline_resolver.resolve(context, metric)
            if not resolution.available:
                aliases = {
                    "involvement_adjusted": "involvement_per_minute",
                    "finishing_adjusted": "finishing_share",
                    "death_exposure_adjusted": "death_exposure_per_ten",
                }
                alias = aliases.get(metric)
                if alias:
                    resolution = baseline_resolver.resolve(context, alias)
            if resolution.available and resolution.value is not None:
                adjusted = numeric - float(resolution.value)
                resolved_count += 1
                if resolution.level:
                    fallback_levels[resolution.level] += 1
            else:
                adjusted = None
                unresolved_count += 1
        else:
            # The pure analytical helpers remain useful in tests/dev when a
            # resolver is intentionally omitted. Production v6 always injects
            # a validated resolver before report assembly.
            resolved_count += 1
            fallback_levels["unadjusted_test_input"] += 1
        observations.append(AdjustedObservation(match, numeric, adjusted, session_id, context, resolution))
    coverage = resolved_count / raw_count if raw_count else 0.0
    return AdjustedMetricSeries(
        metric,
        tuple(observations),
        raw_count,
        resolved_count,
        unresolved_count,
        coverage,
        dict(fallback_levels),
        version,
    )


def adjusted_value_for_match(
    match: Any,
    metric: str,
    raw_value: float | None,
    *,
    baseline_resolver: BaselineResolver | None,
    taxonomy_by_hero: Mapping[Any, Any] | None = None,
) -> tuple[float | None, BaselineResolution | None]:
    """Small single-match seam used by response/drift calculators."""

    if raw_value is None or not math.isfinite(float(raw_value)):
        return None, None
    context = match_context(match, taxonomy_by_hero=taxonomy_by_hero)
    if baseline_resolver is None:
        return float(raw_value), None
    resolution = baseline_resolver.resolve(context, metric)
    if not resolution.available:
        aliases = {
            "involvement_adjusted": "involvement_per_minute",
            "finishing_adjusted": "finishing_share",
            "death_exposure_adjusted": "death_exposure_per_ten",
        }
        alias = aliases.get(metric)
        if alias:
            resolution = baseline_resolver.resolve(context, alias)
    if not resolution.available or resolution.value is None:
        return None, resolution
    return float(raw_value) - float(resolution.value), resolution


__all__ = [
    "AdjustedObservation",
    "AdjustedMetricSeries",
    "match_context",
    "adjust_metric_per_match",
    "adjusted_value_for_match",
    "match_field",
    "match_hero_id",
    "match_lane_context",
]
