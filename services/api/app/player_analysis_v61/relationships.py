"""Result-state opportunities and direct session-position curves."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from .portfolio_shape import cross_fitted_distance_records


def _get(value: Any, key: str, default: Any = None) -> Any:
    return value.get(key, default) if isinstance(value, Mapping) else getattr(value, key, default)


def _session(value: Any, index: int) -> str:
    raw = _get(value, "session_id")
    return str(raw) if raw not in (None, "") else f"match:{index}"


def _won(value: Any) -> bool | None:
    raw = _get(value, "won")
    return raw if isinstance(raw, bool) else None


def result_response_summary(
    matches: Sequence[Any], taxonomy_by_hero: Mapping[Any, Any] | None
) -> dict[str, Any]:
    records = cross_fitted_distance_records(matches, taxonomy_by_hero)
    distance_by_identity = {id(record.match): record.combined_distance for record in records}
    groups: dict[str, list[Any]] = defaultdict(list)
    for index, match in enumerate(matches):
        groups[_session(match, index)].append(match)
    states: dict[str, list[dict[str, Any]]] = defaultdict(list)
    transition_count = 0
    for session_id, rows in groups.items():
        ordered = sorted(
            rows,
            key=lambda item: (
                _get(item, "started_at", _get(item, "start_time")) or 0,
                _get(item, "session_index") or 0,
                _get(item, "match_id") or 0,
            ),
        )
        loss_run = 0
        win_run = 0
        for previous, current in zip(ordered, ordered[1:], strict=False):
            prior = _won(previous)
            if prior is None:
                continue
            if prior:
                win_run += 1
                loss_run = 0
                state = "win" if win_run == 1 else "win_streak"
            else:
                loss_run += 1
                win_run = 0
                state = "one_loss" if loss_run == 1 else "two_plus_losses"
            previous_distance = distance_by_identity.get(id(previous))
            current_distance = distance_by_identity.get(id(current))
            states[state].append(
                {
                    "session_id": session_id,
                    "same_hero": _get(previous, "hero_id") == _get(current, "hero_id"),
                    "distance_movement": (
                        current_distance - previous_distance
                        if current_distance is not None and previous_distance is not None
                        else None
                    ),
                    "next_won": _won(current),
                }
            )
            transition_count += 1
    public_states: dict[str, Any] = {}
    for state in ("win", "one_loss", "two_plus_losses", "win_streak"):
        rows = states.get(state, [])
        movements_by_session: dict[str, list[float]] = defaultdict(list)
        for row in rows:
            if row["distance_movement"] is not None:
                movements_by_session[str(row["session_id"])].append(
                    float(row["distance_movement"])
                )
        session_movements = [
            sum(items) / len(items) for items in movements_by_session.values()
        ]
        movement_mean = (
            sum(session_movements) / len(session_movements)
            if session_movements
            else None
        )
        movement_variance = (
            sum((value - movement_mean) ** 2 for value in session_movements)
            / (len(session_movements) * (len(session_movements) - 1))
            if movement_mean is not None and len(session_movements) > 1
            else 0.0
        )
        movement_half_width = 1.96 * movement_variance**0.5
        next_results = [bool(row["next_won"]) for row in rows if row["next_won"] is not None]
        public_states[state] = {
            "opportunities": len(rows),
            "sessions": len({str(row["session_id"]) for row in rows}),
            "same_hero_rate": sum(bool(row["same_hero"]) for row in rows) / len(rows) if rows else None,
            "mean_distance_movement": movement_mean,
            "movement_interval": (
                [movement_mean - movement_half_width, movement_mean + movement_half_width]
                if movement_mean is not None
                else None
            ),
            "next_result_rate": sum(next_results) / len(next_results) if next_results else None,
            "available": len(rows) >= 12 and len({str(row["session_id"]) for row in rows}) >= 8,
        }
    return {
        "version": "result-response-opportunities-1.0.0",
        "transition_count": transition_count,
        "states": public_states,
        "control_reuse": 0,
        "cross_session_transitions": 0,
    }


def session_position_curve(
    matches: Sequence[Any], *, completed_sessions: Mapping[str, bool] | None = None
) -> dict[str, Any]:
    positions: dict[str, list[Any]] = defaultdict(list)
    sessions_by_position: dict[str, set[str]] = defaultdict(set)
    groups: dict[str, list[Any]] = defaultdict(list)
    for index, match in enumerate(matches):
        groups[_session(match, index)].append(match)
    censored = 0
    for session_id, rows in groups.items():
        completed = bool(completed_sessions and completed_sessions.get(session_id))
        if not completed:
            censored += 1
            continue
        ordered = sorted(
            rows,
            key=lambda item: (
                _get(item, "started_at", _get(item, "start_time")) or 0,
                _get(item, "session_index") or 0,
                _get(item, "match_id") or 0,
            ),
        )
        for index, match in enumerate(ordered, start=1):
            key = f"g{index}" if index <= 4 else "g5_plus"
            positions[key].append(match)
            sessions_by_position[key].add(session_id)
    result: dict[str, Any] = {}
    for key in ("g1", "g2", "g3", "g4", "g5_plus"):
        rows = positions.get(key, [])
        results = [value for match in rows if (value := _won(match)) is not None]
        hero_counts = Counter(_get(match, "hero_id") for match in rows if _get(match, "hero_id") is not None)
        result[key] = {
            "matches": len(rows),
            "sessions": len(sessions_by_position.get(key, set())),
            "result_rate": sum(results) / len(results) if results else None,
            "hero_count": len(hero_counts),
            "available": len(rows) >= 12 and len(sessions_by_position.get(key, set())) >= 8,
        }
    return {
        "version": "session-position-curve-1.0.0",
        "positions": result,
        "censored_sessions": censored,
        "opportunity_rule": "direct-position-denominators",
    }


__all__ = ["result_response_summary", "session_position_curve"]
