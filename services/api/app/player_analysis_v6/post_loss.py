"""Native summary-only Post-Loss Response calculations."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .baselines import BaselineResolver
from .context_adjustment import adjusted_value_for_match, match_context, match_field, match_hero_id
from .metrics import death_exposure_per_ten_minutes, involvement_per_minute
from .statistics import clustered_bootstrap
from .thresholds import DEFAULT_THRESHOLDS, MetricThreshold, threshold_for


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _session(match: Any, index: int) -> str:
    value = _get(match, "session_id")
    return str(value) if value not in (None, "") else f"session-{index + 1}"


def _ordered(matches: Sequence[Any]) -> tuple[Any, ...]:
    return tuple(
        sorted(
            matches,
            key=lambda item: (
                _get(item, "started_at", _get(item, "start_time")) is None,
                _get(item, "started_at", _get(item, "start_time")) or 0,
                _get(item, "session_index") is None,
                _get(item, "session_index") or 0,
                _get(item, "match_id", 0),
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class PostLossTransition:
    previous: Any
    current: Any
    session_id: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "previous_match_id": _get(self.previous, "match_id"),
            "current_match_id": _get(self.current, "match_id"),
            "session_id": self.session_id,
        }


def build_post_loss_transitions(matches: Sequence[Any]) -> tuple[PostLossTransition, ...]:
    """Build only adjacent loss→next-match transitions inside one session."""

    groups: dict[str, list[Any]] = defaultdict(list)
    for index, match in enumerate(matches):
        groups[_session(match, index)].append(match)
    transitions: list[PostLossTransition] = []
    for session_id, rows in groups.items():
        ordered = _ordered(rows)
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if _get(previous, "won") is False and _get(current, "won") is not None:
                transitions.append(PostLossTransition(previous, current, session_id))
    return tuple(transitions)


def _same_comparable_context(left: Any, right: Any, level: int, *, taxonomy_by_hero: Mapping[Any, Any] | None) -> bool:
    a, b = match_context(left, taxonomy_by_hero=taxonomy_by_hero), match_context(right, taxonomy_by_hero=taxonomy_by_hero)
    if level == 0:
        return a.patch == b.patch and a.lane_context == b.lane_context and a.hero_function == b.hero_function
    if level == 1:
        return a.patch == b.patch and a.lane_context == b.lane_context
    if level == 2:
        return a.patch == b.patch
    return True


def _metric(match: Any, key: str, resolver: BaselineResolver | None, taxonomy: Mapping[Any, Any] | None) -> float | None:
    if key == "outcome":
        value = match_field(match, "won")
        return None if value is None else (1.0 if bool(value) else 0.0)
    if key == "activity":
        raw = involvement_per_minute(match_field(match, "kills"), match_field(match, "assists"), match_field(match, "duration_seconds", match_field(match, "duration")))
        value, _ = adjusted_value_for_match(match, "involvement_per_minute", raw, baseline_resolver=resolver, taxonomy_by_hero=taxonomy)
        return value
    raw_deaths = death_exposure_per_ten_minutes(match_field(match, "deaths"), match_field(match, "duration_seconds", match_field(match, "duration")))
    value, _ = adjusted_value_for_match(match, "death_exposure_per_ten", raw_deaths, baseline_resolver=resolver, taxonomy_by_hero=taxonomy)
    return None if value is None else -value


@dataclass(frozen=True, slots=True)
class PostLossResult:
    transitions: tuple[PostLossTransition, ...]
    control_matches: tuple[Any, ...]
    component_deltas: Mapping[str, float | None]
    component_directions: Mapping[str, str]
    familiarity_delta: float | None
    tempo_delta: float | None
    comparable_coverage: float
    qualifying_sessions: int
    direction: str
    available: bool
    component_intervals: Mapping[str, tuple[float, float] | None] = field(default_factory=dict)
    component_bootstrap_replicates: Mapping[str, tuple[float, ...]] = field(default_factory=dict)
    support_bootstrap_replicates: Mapping[str, tuple[float, ...]] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "transition_count": len(self.transitions),
            "qualifying_sessions": self.qualifying_sessions,
            "component_deltas": dict(self.component_deltas),
            "component_directions": dict(self.component_directions),
            "familiarity_delta": self.familiarity_delta,
            "tempo_delta": self.tempo_delta,
            "comparable_coverage": self.comparable_coverage,
            "direction": self.direction,
            "available": self.available,
            "component_intervals": {key: list(value) if value else None for key, value in (self.component_intervals or {}).items()},
            "component_bootstrap_replicates": {key: list(value) for key, value in (self.component_bootstrap_replicates or {}).items()},
            "support_bootstrap_replicates": {key: list(value) for key, value in (self.support_bootstrap_replicates or {}).items()},
            "limitations": list(self.limitations),
            "transition_refs": [f"post_loss:{_get(item.current, 'match_id')}" for item in self.transitions],
        }


def compute_post_loss_response(
    matches: Sequence[Any],
    *,
    baseline_resolver: BaselineResolver | None = None,
    taxonomy_by_hero: Mapping[Any, Any] | None = None,
    core_heroes: set[Any] | None = None,
    thresholds: Mapping[str, MetricThreshold] | None = None,
    bootstrap_iterations: int = 2_000,
    seed: int = 0,
) -> PostLossResult:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    transitions = build_post_loss_transitions(matches)
    after_loss = [item.current for item in transitions]
    transition_ids = {id(item.current) for item in transitions}
    controls: list[Any] = []
    pairs: list[tuple[Any, Any, str]] = []
    comparable = 0
    for target in after_loss:
        for candidate in matches:
            if id(candidate) in transition_ids:
                continue
            if any(_same_comparable_context(target, candidate, level, taxonomy_by_hero=taxonomy_by_hero) for level in range(4)):
                controls.append(candidate)
                pairs.append((target, candidate, _session(target, 0)))
                comparable += 1
                break
    coverage = comparable / len(after_loss) if after_loss else 0.0
    components: dict[str, float | None] = {}
    directions: dict[str, str] = {}
    for key in ("outcome", "activity", "survival"):
        left = [_metric(item, key, baseline_resolver, taxonomy_by_hero) for item in after_loss]
        right = [_metric(item, key, baseline_resolver, taxonomy_by_hero) for item in controls]
        left_values = [float(value) for value in left if value is not None]
        right_values = [float(value) for value in right if value is not None]
        delta = (sum(left_values) / len(left_values) - sum(right_values) / len(right_values)) if left_values and right_values else None
        components[key] = delta
        directions[key] = threshold_for(f"post_loss_{key}_delta", thresholds).direction(delta)
    # Familiarity is based on frozen core membership; it is descriptive support,
    # not a recency-weighted identity input.
    if core_heroes:
        after_share = sum(match_hero_id(item) in core_heroes for item in after_loss) / len(after_loss) if after_loss else None
        control_share = sum(match_hero_id(item) in core_heroes for item in controls) / len(controls) if controls else None
        familiarity = after_share - control_share if after_share is not None and control_share is not None else None
    else:
        familiarity = None
    tempo = components.get("activity")
    confident_positive = sum(value == "positive" for value in directions.values())
    confident_negative = sum(value == "negative" for value in directions.values())
    if confident_positive >= 2 and confident_negative == 0:
        direction = "positive"
    elif confident_negative >= 2 and confident_positive == 0:
        direction = "negative"
    elif confident_positive and confident_negative:
        direction = "mixed"
    elif confident_positive + confident_negative < 2:
        direction = "unknown"
    else:
        direction = "mixed"
    sessions = {_session(item.current, index) for index, item in enumerate(transitions)}
    component_intervals: dict[str, tuple[float, float] | None] = {}
    component_replicates: dict[str, tuple[float, ...]] = {}
    for index, key in enumerate(("outcome", "activity", "survival")):
        def pair_estimator(rows: Sequence[tuple[Any, Any, str]], key: str = key) -> float:
            values: list[float] = []
            for after, control, _session_id in rows:
                left, right = _metric(after, key, baseline_resolver, taxonomy_by_hero), _metric(control, key, baseline_resolver, taxonomy_by_hero)
                if left is not None and right is not None:
                    values.append(left - right)
            return sum(values) / len(values) if values else float("nan")
        boot = clustered_bootstrap(pairs, [item[2] for item in pairs], estimator=pair_estimator, iterations=bootstrap_iterations, seed=seed + index)
        component_intervals[key] = boot.interval
        component_replicates[key] = boot.replicates
    support_replicates: dict[str, tuple[float, ...]] = {}
    if core_heroes:
        def familiarity_estimator(rows: Sequence[tuple[Any, Any, str]]) -> float:
            if not rows:
                return float("nan")
            return sum((match_hero_id(after) in core_heroes) - (match_hero_id(control) in core_heroes) for after, control, _session_id in rows) / len(rows)
        familiarity_boot = clustered_bootstrap(pairs, [item[2] for item in pairs], estimator=familiarity_estimator, iterations=bootstrap_iterations, seed=seed + 10)
        support_replicates["familiarity"] = familiarity_boot.replicates
    def tempo_estimator(rows: Sequence[tuple[Any, Any, str]]) -> float:
        values: list[float] = []
        for after, control, _session_id in rows:
            left, right = _metric(after, "activity", baseline_resolver, taxonomy_by_hero), _metric(control, "activity", baseline_resolver, taxonomy_by_hero)
            if left is not None and right is not None:
                values.append(left - right)
        return sum(values) / len(values) if values else float("nan")
    tempo_boot = clustered_bootstrap(pairs, [item[2] for item in pairs], estimator=tempo_estimator, iterations=bootstrap_iterations, seed=seed + 11)
    support_replicates["tempo"] = tempo_boot.replicates
    limitations: list[str] = []
    if len(transitions) < 30:
        limitations.append("requires at least 30 same-session post-loss transitions")
    if len(sessions) < 12:
        limitations.append("requires at least 12 independent sessions with a transition")
    if coverage < 0.50:
        limitations.append("comparable-context coverage below 50%")
    usable_components = sum(value is not None for value in components.values())
    if usable_components < 2:
        limitations.append("fewer than two usable response components")
    return PostLossResult(
        transitions,
        tuple(controls),
        components,
        directions,
        familiarity,
        tempo,
        coverage,
        len(sessions),
        direction,
        not limitations,
        component_intervals,
        component_replicates,
        support_replicates,
        tuple(limitations),
    )


post_loss_transitions = build_post_loss_transitions
calculate_post_loss_response = compute_post_loss_response


__all__ = [
    "PostLossTransition",
    "PostLossResult",
    "build_post_loss_transitions",
    "compute_post_loss_response",
    "post_loss_transitions",
    "calculate_post_loss_response",
]
