"""Session-position drift calculations for Free DNA v6."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from .baselines import BaselineResolver
from .context_adjustment import adjusted_value_for_match, match_field
from .metrics import death_exposure_per_ten_minutes, involvement_per_minute
from .statistics import clustered_bootstrap
from .thresholds import DEFAULT_THRESHOLDS, MetricThreshold, threshold_for


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _sid(item: Any, index: int) -> str:
    value = _get(item, "session_id")
    return str(value) if value not in (None, "") else f"session-{index + 1}"


def _completed(item: Any, completed_sessions: Mapping[str, bool] | None) -> bool:
    session_id = str(_get(item, "session_id", ""))
    if completed_sessions is not None and session_id in completed_sessions:
        return bool(completed_sessions[session_id])
    value = _get(item, "session_completed", _get(item, "completed"))
    # Completion/censoring evidence is mandatory. Treating missing metadata as
    # completed would turn an interrupted history window into a drift signal.
    return False if value is None else bool(value)


def session_position_buckets(
    matches: Sequence[Any],
    *,
    completed_sessions: Mapping[str, bool] | None = None,
) -> tuple[tuple[str, tuple[Any, ...], tuple[Any, ...]], ...]:
    """Return (session, early, late), excluding the middle match when odd."""

    groups: dict[str, list[Any]] = defaultdict(list)
    for index, item in enumerate(matches):
        if _completed(item, completed_sessions):
            groups[_sid(item, index)].append(item)
    result: list[tuple[str, tuple[Any, ...], tuple[Any, ...]]] = []
    for session_id, rows in groups.items():
        if len(rows) < 4:
            continue
        ordered = sorted(rows, key=lambda item: (_get(item, "started_at", _get(item, "start_time")) or 0, _get(item, "session_index") or 0, _get(item, "match_id", 0)))
        half = len(ordered) // 2
        if len(ordered) % 2:
            early, late = ordered[:half], ordered[half + 1 :]
        else:
            early, late = ordered[:half], ordered[half:]
        if early and late:
            result.append((session_id, tuple(early), tuple(late)))
    return tuple(sorted(result, key=lambda item: item[0]))


def _value(match: Any, key: str, resolver: BaselineResolver | None, taxonomy: Mapping[Any, Any] | None) -> float | None:
    if key == "outcome":
        won = match_field(match, "won")
        return None if won is None else (1.0 if bool(won) else 0.0)
    if key == "activity":
        raw = involvement_per_minute(match_field(match, "kills"), match_field(match, "assists"), match_field(match, "duration_seconds", match_field(match, "duration")))
        value, _ = adjusted_value_for_match(match, "involvement_per_minute", raw, baseline_resolver=resolver, taxonomy_by_hero=taxonomy)
        return value
    raw = death_exposure_per_ten_minutes(match_field(match, "deaths"), match_field(match, "duration_seconds", match_field(match, "duration")))
    value, _ = adjusted_value_for_match(match, "death_exposure_per_ten", raw, baseline_resolver=resolver, taxonomy_by_hero=taxonomy)
    return None if value is None else -value


@dataclass(frozen=True, slots=True)
class SessionDriftResult:
    qualifying_sessions: int
    component_deltas: Mapping[str, float | None]
    component_directions: Mapping[str, str]
    direction: str
    duration_context: Mapping[str, float]
    coverage: float
    available: bool
    component_intervals: Mapping[str, tuple[float, float] | None] = field(default_factory=dict)
    component_bootstrap_replicates: Mapping[str, tuple[float, ...]] = field(default_factory=dict)
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "qualifying_sessions": self.qualifying_sessions,
            "component_deltas": dict(self.component_deltas),
            "component_directions": dict(self.component_directions),
            "direction": self.direction,
            "duration_context": dict(self.duration_context),
            "coverage": self.coverage,
            "available": self.available,
            "component_intervals": {key: list(value) if value else None for key, value in (self.component_intervals or {}).items()},
            "component_bootstrap_replicates": {key: list(value) for key, value in (self.component_bootstrap_replicates or {}).items()},
            "limitations": list(self.limitations),
        }


def compute_session_drift(
    matches: Sequence[Any],
    *,
    baseline_resolver: BaselineResolver | None = None,
    taxonomy_by_hero: Mapping[Any, Any] | None = None,
    completed_sessions: Mapping[str, bool] | None = None,
    thresholds: Mapping[str, MetricThreshold] | None = None,
    bootstrap_iterations: int = 2_000,
    seed: int = 0,
) -> SessionDriftResult:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    buckets = session_position_buckets(matches, completed_sessions=completed_sessions)
    component_rows: dict[str, list[float]] = {"outcome": [], "activity": [], "survival": []}
    session_rows: list[dict[str, Any]] = []
    elapsed_minutes: list[float] = []
    total_session_count = len({str(_get(item, "session_id", index)) for index, item in enumerate(matches)})
    for _session_id, early, late in buckets:
        session_row: dict[str, Any] = {"session_id": _session_id}
        for key in component_rows:
            early_values = [_value(item, key, baseline_resolver, taxonomy_by_hero) for item in early]
            late_values = [_value(item, key, baseline_resolver, taxonomy_by_hero) for item in late]
            left = [float(value) for value in early_values if value is not None]
            right = [float(value) for value in late_values if value is not None]
            if left and right:
                delta = sum(right) / len(right) - sum(left) / len(left)
                component_rows[key].append(delta)
                session_row[key] = delta
        if len(session_row) >= 3:
            session_rows.append(session_row)
        starts = [_get(item, "started_at", _get(item, "start_time")) for item in (*early, *late)]
        starts = [float(value) for value in starts if value is not None]
        if len(starts) >= 2:
            elapsed_minutes.append((max(starts) - min(starts)) / 60.0)
    # Only sessions with at least two supported components qualify for the
    # family. Keep point estimates and bootstrap inputs on that same sample.
    deltas = {
        key: (
            sum(float(row[key]) for row in session_rows if row.get(key) is not None)
            / sum(row.get(key) is not None for row in session_rows)
            if any(row.get(key) is not None for row in session_rows)
            else None
        )
        for key in component_rows
    }
    directions = {key: threshold_for(f"session_drift_{key}_delta", thresholds).direction(value) for key, value in deltas.items()}
    positive = sum(value == "positive" for value in directions.values())
    negative = sum(value == "negative" for value in directions.values())
    if positive >= 2 and negative == 0:
        direction = "rise"
    elif negative >= 2 and positive == 0:
        direction = "fade"
    elif positive and negative:
        direction = "mixed"
    elif positive + negative < 2:
        direction = "unknown"
    else:
        direction = "mixed"
    limitations: list[str] = []
    qualifying_sessions = len(session_rows)
    if qualifying_sessions < 12:
        limitations.append("requires at least 12 completed sessions with four matches")
    if total_session_count and qualifying_sessions / total_session_count < 0.50:
        limitations.append("qualifying-session coverage below 50%")
    if sum(value is not None for value in deltas.values()) < 2:
        limitations.append("fewer than two usable late-minus-early components")
    duration = {
        "session_match_count": sum(len(early) + len(late) for _, early, late in buckets) / len(buckets) if buckets else 0.0,
        "elapsed_session_minutes": sum(elapsed_minutes) / len(elapsed_minutes) if elapsed_minutes else 0.0,
        "qualifying_session_fraction": qualifying_sessions / total_session_count if total_session_count else 0.0,
    }
    component_intervals: dict[str, tuple[float, float] | None] = {}
    component_replicates: dict[str, tuple[float, ...]] = {}
    session_ids = [str(row["session_id"]) for row in session_rows]
    for index, key in enumerate(("outcome", "activity", "survival")):
        def component_estimator(rows: Sequence[Mapping[str, Any]], key: str = key) -> float:
            values = [float(row[key]) for row in rows if row.get(key) is not None]
            return sum(values) / len(values) if values else float("nan")
        boot = clustered_bootstrap(session_rows, session_ids, estimator=component_estimator, iterations=bootstrap_iterations, seed=seed + index)
        component_intervals[key] = boot.interval
        component_replicates[key] = boot.replicates
    return SessionDriftResult(
        qualifying_sessions,
        deltas,
        directions,
        direction,
        duration,
        qualifying_sessions / total_session_count if total_session_count else 0.0,
        not limitations,
        component_intervals,
        component_replicates,
        tuple(limitations),
    )


build_session_position_buckets = session_position_buckets
calculate_session_drift = compute_session_drift


__all__ = [
    "SessionDriftResult",
    "session_position_buckets",
    "build_session_position_buckets",
    "compute_session_drift",
    "calculate_session_drift",
]
