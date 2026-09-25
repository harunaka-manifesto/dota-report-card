"""Pure descriptive story projections for the Free DNA V6.1 report.

The story population is supplied by the caller.  This module deliberately
does not select matches, run statistical analysis, or write report schemas.  It
only turns retained story rows into deterministic, public-safe facts.  Match
IDs may be used inside tie-breaks, but they never leave this module.
"""

from __future__ import annotations

import calendar
import math
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal, TypedDict, cast

StoryState = Literal["available", "degraded", "omitted", "not_ready"]
HistoryCompleteness = Literal["complete", "possibly_truncated", "unknown"]
StatKey = Literal["kills", "assists", "deaths"]

DURATION_SUM_COVERAGE_THRESHOLD = 0.95
RANK_POINTS_PER_MATCH = 25
MIN_RANKED_MATCHES = 10
MIN_BUSY_DAY_MATCHES = 3
LONGEST_MATCH_THRESHOLD_SECONDS = 3_600
MIN_HERO_ERA_MATCHES = 3
MIN_NON_SPARSE_MONTHS = 6

RANKED_MODE_LOBBY_TUPLES = frozenset({(22, 7), (2, 7)})


class StoryModule(TypedDict):
    """The common state boundary consumed by later schema/wiring work."""

    state: StoryState
    reason: str | None
    copy_variant: str | None
    data: dict[str, Any] | None


StoryModules = dict[str, StoryModule]
Row = Any

# Keep this list local to the pure builder.  The API schema intentionally owns
# the public validation model; importing it here would make the aggregation
# layer depend on Pydantic and would couple deterministic facts to transport
# concerns.
STORY_MODULE_KEYS = (
    "hello",
    "match_count",
    "hours_in_matches",
    "rank_points",
    "busiest_week",
    "busiest_day",
    "longest_match",
    "wins_bridge",
    "win_summary",
    "winning_streak",
    "top_win_heroes",
    "losing_streak",
    "top_loss_heroes",
    "hero_pool",
    "hero_eras",
    "hero_era_payoff",
    "kills",
    "assists",
    "deaths",
    "element_distinctiveness",
    "archetype",
    "card_collage",
    "final_identity_card",
    "deep",
)


def _module(
    state: StoryState,
    data: dict[str, Any] | None = None,
    *,
    reason: str | None = None,
    copy_variant: str | None = None,
) -> StoryModule:
    if state in {"available", "degraded"} and data is None:
        raise ValueError(f"{state} story modules require data")
    if state == "available" and reason is not None:
        raise ValueError("available story modules cannot carry an omission reason")
    if state == "degraded" and not reason:
        raise ValueError("degraded story modules require a reason")
    if state == "omitted" and data is not None:
        raise ValueError("omitted story modules must have null data")
    if state in {"omitted", "not_ready"} and not reason:
        raise ValueError(f"{state} story modules require a reason")
    return {
        "state": state,
        "reason": reason,
        "copy_variant": copy_variant,
        "data": data,
    }


def _get(value: Row, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _field(value: Row, key: str, default: Any = None) -> Any:
    result = _get(value, key)
    if result is not None:
        return result
    aliases = {"start_time": "started_at", "started_at": "start_time", "duration_seconds": "duration"}
    alias = aliases.get(key)
    return _get(value, alias, default) if alias is not None else default


def _int(value: Any, *, minimum: int | None = None) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if isinstance(value, float) and (not math.isfinite(value) or value != parsed):
        return None
    if minimum is not None and parsed < minimum:
        return None
    return parsed


def _timestamp(row: Row) -> int | None:
    return _int(_field(row, "started_at"))


def _duration(row: Row) -> int | None:
    return _int(_field(row, "duration_seconds"), minimum=0)


def _hero_id(row: Row) -> int | None:
    return _int(_field(row, "hero_id"), minimum=1)


def _outcome(row: Row) -> bool | None:
    value = _field(row, "won")
    if isinstance(value, bool):
        return value
    if value in (0, 1):
        return bool(value)
    return None


def _outcome_label(row: Row) -> Literal["win", "loss"] | None:
    value = _outcome(row)
    return "win" if value is True else "loss" if value is False else None


def _stat(row: Row, key: str) -> int | None:
    return _int(_field(row, key), minimum=0)


def _descending(value: int | None) -> int:
    return -(value if value is not None else -1)


def _internal_id(row: Row, index: int) -> int:
    """Return a private deterministic tie-break value."""

    return _int(_field(row, "match_id"), minimum=1) or index


def _dated_rows(rows: Sequence[Row]) -> list[tuple[int, Row]]:
    dated = [
        (index, row)
        for index, row in enumerate(rows)
        if (timestamp := _timestamp(row)) is not None and _date_string(timestamp) is not None
    ]
    return sorted(dated, key=lambda item: (_timestamp(item[1]) or 0, _internal_id(item[1], item[0])))


def _utc_date(timestamp: int) -> date:
    return datetime.fromtimestamp(timestamp, tz=UTC).date()


def _date_string(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    try:
        return _utc_date(timestamp).isoformat()
    except (OverflowError, OSError, ValueError):
        return None


def _safe_hero_name(hero_id: int | None, hero_metadata: Mapping[Any, Any] | None) -> str | None:
    if hero_id is None or hero_metadata is None:
        return None
    entry = hero_metadata.get(hero_id)
    if entry is None:
        entry = hero_metadata.get(str(hero_id))
    if entry is None:
        return None
    if isinstance(entry, str):
        return entry.strip() or None
    if isinstance(entry, Mapping):
        values = (
            entry.get("display_name"),
            entry.get("name"),
            entry.get("localized_name"),
            entry.get("hero_name"),
        )
    else:
        values = (
            getattr(entry, "display_name", None),
            getattr(entry, "name", None),
            getattr(entry, "localized_name", None),
            getattr(entry, "hero_name", None),
        )
    return next((str(value).strip() for value in values if value not in (None, "") and str(value).strip()), None)


def _hero_ref(hero_id: int | None, hero_metadata: Mapping[Any, Any] | None) -> dict[str, Any]:
    return {"hero_id": hero_id, "hero_name": _safe_hero_name(hero_id, hero_metadata)}


def format_duration(seconds: int) -> str:
    """Format seconds without exposing a locale-dependent duration string."""

    minutes, remainder = divmod(max(0, int(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m"
    return f"{remainder}s"


def _rounded_duration(seconds: int) -> tuple[int | float, Literal["minutes", "hours"]]:
    if seconds < 3_600:
        return (int(math.floor(seconds / 60 + 0.5)), "minutes")
    hours = seconds / 3_600
    if hours <= 10:
        return (math.floor(hours * 10 + 0.5) / 10, "hours")
    return (int(math.floor(hours + 0.5)), "hours")


def _coverage(known: int, denominator: int) -> dict[str, int | float]:
    ratio = known / denominator if denominator else 0.0
    # Keep the mathematical fraction rather than a display-rounded value;
    # the strict payload validator recomputes this ratio with a tight
    # tolerance and the frontend does not own coverage rounding.
    return {"numerator": known, "denominator": denominator, "ratio": ratio}


def _duration_projection(
    rows: Sequence[tuple[int, Row]],
    *,
    include_partial: bool,
) -> tuple[dict[str, Any] | None, bool]:
    denominator = len(rows)
    durations = [(index, row, _duration(row)) for index, row in rows]
    known = [value for _index, _row, value in durations if value is not None]
    coverage = _coverage(len(known), denominator)
    ratio = len(known) / denominator if denominator else 0.0
    reliable = bool(denominator and ratio >= DURATION_SUM_COVERAGE_THRESHOLD)
    if not known:
        return (
            {
                "total_duration_seconds": None,
                "display_value": None,
                "display_unit": None,
                "coverage_numerator": coverage["numerator"],
                "coverage_denominator": coverage["denominator"],
                "coverage_ratio": coverage["ratio"],
                "hours_available": False,
            },
            reliable,
        )
    if not reliable:
        # The raw partial sum remains useful for diagnostics, but the strict
        # public contract marks the display unavailable whenever coverage is
        # below the reliability threshold.  In particular, do not pair a
        # numeric display with ``hours_available=False``.
        return (
            {
                "total_duration_seconds": sum(known) if include_partial else None,
                "display_value": None,
                "display_unit": None,
                "coverage_numerator": coverage["numerator"],
                "coverage_denominator": coverage["denominator"],
                "coverage_ratio": coverage["ratio"],
                "hours_available": False,
            },
            reliable,
        )
    total = sum(known)
    display_value, display_unit = _rounded_duration(total)
    return (
        {
            "total_duration_seconds": total,
            "display_value": display_value,
            "display_unit": display_unit,
            "coverage_numerator": coverage["numerator"],
            "coverage_denominator": coverage["denominator"],
            "coverage_ratio": coverage["ratio"],
            "hours_available": reliable,
        },
        reliable,
    )


def build_hours_module(rows: Sequence[Row]) -> StoryModule:
    """Aggregate total match duration using the 95% sum reliability rule."""

    dated = _dated_rows(rows)
    if not dated:
        return _module("omitted", reason="no_dated_matches", copy_variant="unavailable")
    projection, reliable = _duration_projection(dated, include_partial=False)
    if not reliable:
        return _module(
            "omitted",
            reason="duration_coverage_below_threshold",
            copy_variant="unavailable",
        )
    if projection is None or projection["total_duration_seconds"] is None:
        return _module("omitted", reason="duration_unavailable", copy_variant="unavailable")
    return _module(
        "available",
        projection,
        copy_variant=str(projection["display_unit"]),
    )


def _period_key(day: date) -> tuple[int, int]:
    iso = day.isocalendar()
    return int(iso.year), int(iso.week)


def _period_bounds(day: date) -> tuple[date, date]:
    start = day - timedelta(days=day.weekday())
    return start, start + timedelta(days=6)


def _select_group(groups: Mapping[Any, list[tuple[int, Row]]]) -> tuple[Any, list[tuple[int, Row]]]:
    return max(
        groups.items(),
        key=lambda item: (
            len(item[1]),
            max((_timestamp(row) or 0) for _index, row in item[1]),
            -min(_internal_id(row, index) for index, row in item[1]),
        ),
    )


def build_busiest_week_module(rows: Sequence[Row]) -> StoryModule:
    dated = _dated_rows(rows)
    if not dated:
        return _module("omitted", reason="no_dated_matches", copy_variant="unavailable")
    groups: dict[tuple[int, int], list[tuple[int, Row]]] = defaultdict(list)
    for item in dated:
        groups[_period_key(_utc_date(_timestamp(item[1]) or 0))].append(item)
    _key, selected = _select_group(groups)
    representative = _utc_date(_timestamp(selected[0][1]) or 0)
    period_start, period_end = _period_bounds(representative)
    duration_data, reliable = _duration_projection(selected, include_partial=False)
    period_duration = {
        key: value
        for key, value in (duration_data or {}).items()
        if key in {"total_duration_seconds", "display_value", "display_unit", "hours_available"}
    }
    data: dict[str, Any] = {
        "period_kind": "iso_calendar_week",
        "date_start": period_start.isoformat(),
        "date_end": period_end.isoformat(),
        "match_count": len(selected),
        **period_duration,
    }
    return _module(
        "available" if reliable else "degraded",
        data,
        reason=None if reliable else "duration_coverage_below_threshold",
        copy_variant="hours" if reliable and duration_data and duration_data.get("hours_available") else "match_count",
    )


def _selected_longest(
    rows: Sequence[Row],
) -> tuple[int, Row] | None:
    dated = _dated_rows(rows)
    if not dated or any(_duration(row) is None for _index, row in dated):
        return None
    return max(
        dated,
        key=lambda item: (
            _duration(item[1]) or 0,
            _timestamp(item[1]) or 0,
            -_internal_id(item[1], item[0]),
        ),
    )


def build_longest_match_module(
    rows: Sequence[Row],
    *,
    hero_metadata: Mapping[Any, Any] | None = None,
    busiest_day: str | None = None,
) -> StoryModule:
    dated = _dated_rows(rows)
    if not dated:
        return _module("omitted", reason="no_dated_matches", copy_variant="unavailable")
    if any(_duration(row) is None for _index, row in dated):
        return _module("omitted", reason="duration_coverage_below_threshold", copy_variant="unavailable")
    selected = _selected_longest(rows)
    if selected is None:
        return _module("omitted", reason="duration_unavailable", copy_variant="unavailable")
    _index, row = selected
    duration = _duration(row)
    hero_id = _hero_id(row)
    hero_name = _safe_hero_name(hero_id, hero_metadata)
    if duration is None or hero_id is None or hero_name is None:
        return _module("omitted", reason="hero_metadata_unavailable", copy_variant="unavailable")
    day = _date_string(_timestamp(row))
    outcome = _outcome_label(row)
    if day is None or outcome is None:
        return _module("omitted", reason="outcome_unavailable", copy_variant="unavailable")
    data = {
        **_hero_ref(hero_id, hero_metadata),
        "duration_seconds": duration,
        "formatted_duration": format_duration(duration),
        "date": day,
        "outcome": outcome,
        "kills": _stat(row, "kills"),
        "deaths": _stat(row, "deaths"),
        "assists": _stat(row, "assists"),
        "refused_to_end": duration >= LONGEST_MATCH_THRESHOLD_SECONDS,
        "on_busiest_day": day == busiest_day if busiest_day is not None else False,
    }
    return _module(
        "available",
        data,
        copy_variant="refused_to_end" if data["refused_to_end"] else "standard",
    )


def build_busiest_day_module(
    rows: Sequence[Row],
    *,
    busiest_week: StoryModule | None = None,
    longest_match: StoryModule | None = None,
) -> StoryModule:
    dated = _dated_rows(rows)
    if not dated:
        return _module("omitted", reason="no_dated_matches", copy_variant="unavailable")
    groups: dict[date, list[tuple[int, Row]]] = defaultdict(list)
    for item in dated:
        groups[_utc_date(_timestamp(item[1]) or 0)].append(item)
    _day, selected = _select_group(groups)
    if len(selected) < MIN_BUSY_DAY_MATCHES:
        return _module("omitted", reason="fewer_than_three_matches", copy_variant="unavailable")
    selected_day = _day
    duration_data, reliable = _duration_projection(selected, include_partial=False)
    period_duration = {
        key: value
        for key, value in (duration_data or {}).items()
        if key in {"total_duration_seconds", "display_value", "display_unit", "hours_available"}
    }
    week_start, week_end = _period_bounds(selected_day)
    week_data = busiest_week.get("data") if busiest_week else None
    if isinstance(week_data, Mapping):
        week_start = _parse_date(week_data.get("date_start")) or week_start
        week_end = _parse_date(week_data.get("date_end")) or week_end
    longest_day = None
    longest_data = longest_match.get("data") if longest_match else None
    if isinstance(longest_data, Mapping):
        longest_day = longest_data.get("date")
    data: dict[str, Any] = {
        "date": selected_day.isoformat(),
        "match_count": len(selected),
        "inside_busiest_week": week_start <= selected_day <= week_end,
        "also_longest_match_day": longest_day == selected_day.isoformat(),
        **period_duration,
    }
    return _module(
        "available" if reliable else "degraded",
        data,
        reason=None if reliable else "duration_coverage_below_threshold",
        copy_variant="hours" if reliable and duration_data and duration_data.get("hours_available") else "match_count",
    )


def build_rank_points_module(
    rows: Sequence[Row],
    *,
    mode_map_valid: bool = True,
) -> StoryModule:
    if not mode_map_valid:
        return _module("omitted", reason="invalid_mode_map", copy_variant="unavailable")
    ranked: list[Row] = []
    for row in rows:
        mode = _int(_field(row, "game_mode"))
        lobby = _int(_field(row, "lobby_type"))
        if mode is None or lobby is None or (mode, lobby) not in RANKED_MODE_LOBBY_TUPLES:
            continue
        if _outcome(row) is not None:
            ranked.append(row)
    if not ranked:
        return _module("omitted", reason="no_ranked_matches", copy_variant="unavailable")
    wins = sum(_outcome(row) is True for row in ranked)
    losses = sum(_outcome(row) is False for row in ranked)
    ranked_count = wins + losses
    if ranked_count < MIN_RANKED_MATCHES:
        return _module("omitted", reason="fewer_than_ten_ranked_matches", copy_variant="unavailable")
    delta = wins - losses
    direction: Literal["positive", "negative", "zero"] = "positive" if delta > 0 else "negative" if delta < 0 else "zero"
    data = {
        "points_absolute": abs(delta * RANK_POINTS_PER_MATCH),
        "direction": direction,
        "ranked_matches": ranked_count,
        "ranked_wins": wins,
        "ranked_losses": losses,
        "points_per_match": RANK_POINTS_PER_MATCH,
        "classification_reliable": True,
        "formula_version": "rank-points-story-1.0.0",
    }
    return _module("available", data, copy_variant=direction)


def _hero_totals(
    rows: Sequence[Row],
    *,
    value_key: str,
    exclude_hero_id: int | None = None,
) -> list[dict[str, Any]]:
    totals: Counter[int] = Counter()
    matches: Counter[int] = Counter()
    latest: dict[int, int] = {}
    for _index, row in enumerate(rows):
        hero_id = _hero_id(row)
        if value_key == "wins":
            value = 1 if _outcome(row) is True else None
        elif value_key == "losses":
            value = 1 if _outcome(row) is False else None
        else:
            value = _stat(row, value_key)
        if hero_id is None or value is None or hero_id == exclude_hero_id:
            continue
        matches[hero_id] += 1
        totals[hero_id] += value
        latest[hero_id] = max(latest.get(hero_id, 0), _timestamp(row) or 0)
    return [
        {
            "hero_id": hero_id,
            "total": total,
            "matches": matches[hero_id],
            "latest": latest.get(hero_id, 0),
        }
        for hero_id, total in sorted(
            totals.items(), key=lambda item: (-item[1], -latest.get(item[0], 0), item[0])
        )
        if total > 0
    ]


def _hero_rank_rows(
    rows: Sequence[Row],
    *,
    value_key: str,
    output_value_key: str,
    hero_metadata: Mapping[Any, Any] | None,
    exclude_hero_id: int | None = None,
    match_rows: Sequence[Row] | None = None,
) -> list[dict[str, Any]]:
    totals = _hero_totals(rows, value_key=value_key, exclude_hero_id=exclude_hero_id)
    if not totals:
        return []
    # A missing name for the actual leading hero cannot be repaired in the
    # presentation layer.  Leave the module unavailable rather than changing
    # the ranking to make a named row appear.
    if _safe_hero_name(cast(int, totals[0]["hero_id"]), hero_metadata) is None:
        return []
    all_matches: Counter[int] = Counter()
    for row in match_rows if match_rows is not None else rows:
        hero_id = _hero_id(row)
        if hero_id is not None and hero_id != exclude_hero_id:
            all_matches[hero_id] += 1
    result: list[dict[str, Any]] = []
    for rank, item in enumerate(totals[:3], start=1):
        hero_id = cast(int, item["hero_id"])
        name = _safe_hero_name(hero_id, hero_metadata)
        if name is None:
            # Do not leave a rank gap that a strict consumer could mistake for
            # a complete top-three ranking.  The actual leading row was
            # checked above; a later unknown row ends the safe prefix.
            break
        result.append(
            {
                "rank": rank,
                "hero_id": hero_id,
                "hero_name": name,
                output_value_key: item["total"],
                "matches": all_matches.get(hero_id, item["matches"]),
            }
        )
    return result


def _winningest_day(rows: Sequence[Row]) -> dict[str, Any] | None:
    groups: dict[date, list[tuple[int, Row]]] = defaultdict(list)
    for index, row in _dated_rows(rows):
        if _outcome(row) is True:
            groups[_utc_date(_timestamp(row) or 0)].append((index, row))
    if not groups:
        return None
    selected_day, selected = _select_group(groups)
    return {"date": selected_day.isoformat(), "daily_wins": len(selected)}


def build_wins_bridge_module(rows: Sequence[Row]) -> StoryModule:
    wins = sum(_outcome(row) is True for row in rows)
    return _module("available", {"wins": wins}, copy_variant="zero" if wins == 0 else "wins")


def build_win_summary_module(rows: Sequence[Row]) -> StoryModule:
    wins = sum(_outcome(row) is True for row in rows)
    return _module(
        "available",
        {"wins": wins, "winningest_day": _winningest_day(rows)},
        copy_variant="zero" if wins == 0 else "one" if wins == 1 else "many",
    )


def _streaks(rows: Sequence[Row], outcome: bool) -> list[tuple[int, int, int]]:
    ordered = [(index, row) for index, row in _dated_rows(rows) if _outcome(row) is not None]
    runs: list[tuple[int, int, int]] = []
    start: int | None = None
    for position, (_index, row) in enumerate(ordered):
        if _outcome(row) is outcome:
            if start is None:
                start = position
            continue
        if start is not None:
            runs.append((start, position - 1, position - start))
            start = None
    if start is not None:
        runs.append((start, len(ordered) - 1, len(ordered) - start))
    return runs


def _best_streak(rows: Sequence[Row], outcome: bool) -> tuple[list[tuple[int, Row]], tuple[int, int, int]] | None:
    ordered = [(index, row) for index, row in _dated_rows(rows) if _outcome(row) is not None]
    runs = _streaks(rows, outcome)
    if not runs:
        return None
    selected = max(
        runs,
        key=lambda run: (
            run[2],
            _timestamp(ordered[run[1]][1]) or 0,
            _timestamp(ordered[run[0]][1]) or 0,
        ),
    )
    return [ordered[position] for position in range(selected[0], selected[1] + 1)], selected


def _match_observation(row: Row, hero_metadata: Mapping[Any, Any] | None) -> dict[str, Any]:
    hero_id = _hero_id(row)
    return {
        **_hero_ref(hero_id, hero_metadata),
        "date": _date_string(_timestamp(row)),
        "outcome": _outcome_label(row),
        "kills": _stat(row, "kills"),
        "deaths": _stat(row, "deaths"),
        "assists": _stat(row, "assists"),
        "duration_seconds": _duration(row),
    }


def build_winning_streak_module(
    rows: Sequence[Row],
    *,
    hero_metadata: Mapping[Any, Any] | None = None,
) -> StoryModule:
    best = _best_streak(rows, True)
    if best is None:
        return _module("omitted", reason="no_wins", copy_variant="unavailable")
    selected, _run = best
    return _module(
        "available",
        {
            "length": len(selected),
            "start_date": _date_string(_timestamp(selected[0][1])),
            "end_date": _date_string(_timestamp(selected[-1][1])),
        },
        copy_variant="single_win" if len(selected) == 1 else "streak",
    )


def _history_is_complete(value: HistoryCompleteness | bool) -> bool:
    return value is True or value == "complete"


def build_losing_streak_module(
    rows: Sequence[Row],
    *,
    hero_metadata: Mapping[Any, Any] | None = None,
    history_completeness: HistoryCompleteness | bool = "complete",
) -> StoryModule:
    best = _best_streak(rows, False)
    if best is None:
        return _module("omitted", reason="no_losses", copy_variant="unavailable")
    selected, run = best
    ordered = [(index, row) for index, row in _dated_rows(rows) if _outcome(row) is not None]
    end_position = run[1]
    breaker: dict[str, Any] | None = None
    if end_position + 1 < len(ordered):
        breaker = _match_observation(ordered[end_position + 1][1], hero_metadata)
        if (
            breaker["hero_id"] is None
            or breaker["hero_name"] is None
            or breaker["date"] is None
            or breaker["outcome"] is None
        ):
            return _module("omitted", reason="hero_metadata_unavailable", copy_variant="unavailable")
        terminal_state = "broken_by_win"
    else:
        terminal_state = "observation_ended" if _history_is_complete(history_completeness) else "history_boundary"
    return _module(
        "available",
        {
            "length": len(selected),
            "start_date": _date_string(_timestamp(selected[0][1])),
            "end_date": _date_string(_timestamp(selected[-1][1])),
            "terminal_state": terminal_state,
            "breaker": breaker,
        },
        copy_variant=terminal_state,
    )


def build_top_win_heroes_module(
    rows: Sequence[Row],
    *,
    hero_metadata: Mapping[Any, Any] | None = None,
) -> StoryModule:
    wins = sum(_outcome(row) is True for row in rows)
    if wins == 0:
        return _module("omitted", reason="no_wins", copy_variant="unavailable")
    hero_rows = _hero_rank_rows(
        rows,
        value_key="wins",
        output_value_key="wins",
        hero_metadata=hero_metadata,
        match_rows=rows,
    )
    if not hero_rows:
        return _module("omitted", reason="hero_metadata_unavailable", copy_variant="unavailable")
    return _module("available", {"rows": hero_rows}, copy_variant="ranked")


def _loss_rows(rows: Sequence[Row]) -> list[Row]:
    return [row for row in rows if _outcome(row) is False]


def build_top_loss_heroes_module(
    rows: Sequence[Row],
    *,
    hero_metadata: Mapping[Any, Any] | None = None,
    breaker_hero_id: int | None = None,
) -> StoryModule:
    losses = _loss_rows(rows)
    if not losses:
        return _module("omitted", reason="no_losses", copy_variant="unavailable")
    hero_rows = _hero_rank_rows(
        losses,
        value_key="losses",
        output_value_key="losses",
        hero_metadata=hero_metadata,
        exclude_hero_id=breaker_hero_id,
        match_rows=rows,
    )
    if not hero_rows:
        return _module("omitted", reason="hero_metadata_unavailable", copy_variant="unavailable")
    daily: dict[date, list[Row]] = defaultdict(list)
    for row in losses:
        timestamp = _timestamp(row)
        if timestamp is not None:
            daily[_utc_date(timestamp)].append(row)
    roughest_day = None
    if daily:
        day, values = max(
            daily.items(),
            key=lambda item: (
                len(item[1]),
                item[0].toordinal(),
                -min(_internal_id(row, index) for index, row in enumerate(item[1])),
            ),
        )
        roughest_day = {"date": day.isoformat(), "daily_losses": len(values)}
    return _module(
        "available",
        {
            "breaker_exists": breaker_hero_id is not None,
            "rows": hero_rows,
            "roughest_day": roughest_day,
        },
        copy_variant="ranked",
    )


def _hero_match_counts(rows: Sequence[Row]) -> list[dict[str, Any]]:
    counts: Counter[int] = Counter()
    latest: dict[int, int] = {}
    for row in rows:
        hero_id = _hero_id(row)
        if hero_id is None:
            continue
        counts[hero_id] += 1
        latest[hero_id] = max(latest.get(hero_id, 0), _timestamp(row) or 0)
    return [
        {"hero_id": hero_id, "matches": count, "latest": latest.get(hero_id, 0)}
        for hero_id, count in sorted(counts.items(), key=lambda item: (-item[1], -latest.get(item[0], 0), item[0]))
    ]


def build_hero_pool_module(
    rows: Sequence[Row],
    *,
    hero_metadata: Mapping[Any, Any] | None = None,
) -> StoryModule:
    counts = _hero_match_counts(rows)
    if not counts:
        return _module("omitted", reason="no_hero_data", copy_variant="unavailable")
    selected = counts[:5]
    if any(_safe_hero_name(cast(int, item["hero_id"]), hero_metadata) is None for item in selected):
        return _module("omitted", reason="hero_metadata_unavailable", copy_variant="unavailable")
    total = sum(item["matches"] for item in counts)
    top_matches = sum(item["matches"] for item in selected)
    share = top_matches / total if total else 0.0
    band: Literal["concentrated", "broad"] | None = "concentrated" if share >= 0.75 else "broad" if share <= 0.50 else None
    heroes = [
        {
            "rank": rank,
            **_hero_ref(cast(int, item["hero_id"]), hero_metadata),
            "matches": item["matches"],
            "share": round(item["matches"] / total, 6) if total else 0.0,
        }
        for rank, item in enumerate(selected, start=1)
    ]
    return _module(
        "available",
        {
            "heroes": heroes,
            "total_matches": total,
            "top_five_share": round(share, 6),
            "concentration_band": band,
        },
        copy_variant=band or "neutral",
    )


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _month_start(day: date) -> date:
    return date(day.year, day.month, 1)


def _next_month(day: date) -> date:
    return date(day.year + (day.month == 12), 1 if day.month == 12 else day.month + 1, 1)


def _window_dates(
    rows: Sequence[Row],
    *,
    window_start: int | None,
    window_end: int | None,
) -> tuple[date, date] | None:
    dated_values = [
        timestamp
        for _index, row in _dated_rows(rows)
        if (timestamp := _timestamp(row)) is not None
    ]
    if not dated_values:
        return None
    start_timestamp = window_start if window_start is not None else min(dated_values)
    end_timestamp = window_end if window_end is not None else max(dated_values)
    try:
        start = _utc_date(int(start_timestamp))
        end = _utc_date(int(end_timestamp))
    except (TypeError, ValueError, OverflowError, OSError):
        return None
    return (start, end) if start <= end else None


def _era_top_heroes(
    period_rows: Sequence[tuple[int, Row]],
    *,
    hero_metadata: Mapping[Any, Any] | None,
) -> list[dict[str, Any]]:
    counts: Counter[int] = Counter()
    latest: dict[int, int] = {}
    for _index, row in period_rows:
        hero_id = _hero_id(row)
        if hero_id is None:
            continue
        counts[hero_id] += 1
        latest[hero_id] = max(latest.get(hero_id, 0), _timestamp(row) or 0)
    result: list[dict[str, Any]] = []
    for rank, (hero_id, count) in enumerate(
        sorted(counts.items(), key=lambda item: (-item[1], -latest.get(item[0], 0), item[0]))[:5],
        start=1,
    ):
        result.append(
            {
                "rank": rank,
                **_hero_ref(hero_id, hero_metadata),
                "matches": count,
            }
        )
    return result


def _period_row(
    period_id: str,
    period_kind: Literal["calendar_month", "third"],
    period_start: date,
    period_end: date,
    period_rows: Sequence[tuple[int, Row]],
    *,
    hero_metadata: Mapping[Any, Any] | None,
) -> dict[str, Any]:
    top_heroes = _era_top_heroes(period_rows, hero_metadata=hero_metadata)
    return {
        "id": period_id,
        "period_kind": period_kind,
        "date_start": period_start.isoformat(),
        "date_end": period_end.isoformat(),
        "match_count": len(period_rows),
        "empty": not period_rows,
        "sparse": len(period_rows) < MIN_HERO_ERA_MATCHES,
        "top_heroes": top_heroes,
    }


def _monthly_eras(
    dated: Sequence[tuple[int, Row]],
    start: date,
    end: date,
    *,
    hero_metadata: Mapping[Any, Any] | None,
) -> list[dict[str, Any]]:
    periods: list[dict[str, Any]] = []
    month = _month_start(start)
    while month <= end:
        month_end = date(month.year, month.month, calendar.monthrange(month.year, month.month)[1])
        period_start, period_end = max(start, month), min(end, month_end)
        period_rows = [
            item
            for item in dated
            if period_start <= _utc_date(_timestamp(item[1]) or 0) <= period_end
        ]
        periods.append(
            _period_row(
                f"{month.year:04d}-{month.month:02d}",
                "calendar_month",
                period_start,
                period_end,
                period_rows,
                hero_metadata=hero_metadata,
            )
        )
        month = _next_month(month)
    return periods


def _third_eras(
    dated: Sequence[tuple[int, Row]],
    start: date,
    end: date,
    *,
    hero_metadata: Mapping[Any, Any] | None,
) -> list[dict[str, Any]]:
    span_days = (end - start).days + 1
    base, remainder = divmod(span_days, 3)
    sizes = [base + (index < remainder) for index in range(3)]
    periods: list[dict[str, Any]] = []
    offset = 0
    for index in range(3):
        if offset >= span_days or sizes[index] == 0:
            period_start = period_end = end
            period_rows = []
        else:
            period_start = start + timedelta(days=offset)
            period_end = min(end, period_start + timedelta(days=sizes[index] - 1))
            period_rows = [
                item
                for item in dated
                if period_start <= _utc_date(_timestamp(item[1]) or 0) <= period_end
            ]
        offset += sizes[index]
        periods.append(
            _period_row(
                f"third-{index + 1}",
                "third",
                period_start,
                period_end,
                period_rows,
                hero_metadata=hero_metadata,
            )
        )
    return periods


def build_hero_eras_module(
    rows: Sequence[Row],
    *,
    hero_metadata: Mapping[Any, Any] | None = None,
    window_start: int | None = None,
    window_end: int | None = None,
) -> StoryModule:
    dated = _dated_rows(rows)
    bounds = _window_dates(rows, window_start=window_start, window_end=window_end)
    if not dated or bounds is None:
        return _module("omitted", reason="no_dated_matches", copy_variant="unavailable")
    start, end = bounds
    dated = [
        item
        for item in dated
        if start <= _utc_date(_timestamp(item[1]) or 0) <= end
    ]
    if not dated:
        return _module("omitted", reason="no_matches_in_window", copy_variant="unavailable")
    monthly = _monthly_eras(dated, start, end, hero_metadata=hero_metadata)
    non_sparse_months = sum(not period["sparse"] for period in monthly)
    fallback = non_sparse_months < MIN_NON_SPARSE_MONTHS
    periods = _third_eras(dated, start, end, hero_metadata=hero_metadata) if fallback else monthly
    # A named era row is required to represent the actual ranking.  Dropping
    # an unknown hero would silently promote a lower-ranked hero, so fail
    # closed for the whole era module instead.
    if any(
        period["match_count"]
        and any(row.get("hero_name") is None for row in period["top_heroes"])
        for period in periods
    ):
        return _module("omitted", reason="hero_metadata_unavailable", copy_variant="unavailable")
    data = {
        "period_kind": "third" if fallback else "calendar_month",
        "sparse_fallback": fallback,
        "periods": periods,
    }
    return _module("available", data, copy_variant="sparse_fallback" if fallback else "calendar_month")


def _era_rows(data: Mapping[str, Any] | StoryModule) -> Sequence[Mapping[str, Any]]:
    candidate: Any = data.get("data") if "data" in data else data
    if not isinstance(candidate, Mapping):
        return ()
    periods = candidate.get("periods")
    return tuple(period for period in periods if isinstance(period, Mapping)) if isinstance(periods, Sequence) else ()


def build_hero_era_payoff_module(
    eras: StoryModule | Mapping[str, Any],
    *,
    hero_metadata: Mapping[Any, Any] | None = None,
) -> StoryModule:
    periods = [period for period in _era_rows(eras) if not bool(period.get("sparse"))]
    if not periods:
        return _module("omitted", reason="all_periods_sparse", copy_variant="unavailable")
    appearances: Counter[int] = Counter()
    latest: dict[int, int] = {}
    top_sets: list[set[int]] = []
    top_rows_by_period: list[list[Mapping[str, Any]]] = []
    for period in periods:
        raw_rows = period.get("top_heroes")
        top_rows = [row for row in raw_rows if isinstance(row, Mapping)] if isinstance(raw_rows, Sequence) else []
        top_rows_by_period.append(top_rows)
        top_ids = {hero_id for row in top_rows if (hero_id := _int(row.get("hero_id"), minimum=1)) is not None}
        top_sets.append(top_ids)
        period_ordinal = _parse_date(str(period.get("date_end")))
        ordinal = period_ordinal.toordinal() if period_ordinal else 0
        for row in top_rows:
            hero_id = _int(row.get("hero_id"), minimum=1)
            if hero_id is not None:
                appearances[hero_id] += 1
                latest[hero_id] = max(latest.get(hero_id, 0), ordinal)
    persistence = None
    if appearances:
        hero_id, count = max(appearances.items(), key=lambda item: (item[1], latest.get(item[0], 0), -item[0]))
        persistence = {
            "hero": _hero_ref(hero_id, hero_metadata),
            "top_five_periods": count,
        }
    takeover = None
    for index in range(1, len(periods) - 1):
        current_rows = top_rows_by_period[index]
        next_rows = top_rows_by_period[index + 1]
        if not current_rows or not next_rows:
            continue
        hero_id = _int(current_rows[0].get("hero_id"), minimum=1)
        next_hero_id = _int(next_rows[0].get("hero_id"), minimum=1)
        if hero_id is None or hero_id != next_hero_id or hero_id in top_sets[index - 1]:
            continue
        takeover = {
            "hero": _hero_ref(hero_id, hero_metadata),
            "period": periods[index].get("id"),
        }
        break
    steady_pool = len(top_sets) > 1 and all(value == top_sets[0] for value in top_sets[1:])
    return _module(
        "available",
        {"persistence": persistence, "takeover": takeover, "steady_pool": steady_pool},
        copy_variant="takeover" if takeover else "persistence" if persistence else "steady",
    )


def _stat_match_row(
    row: Row,
    *,
    stat_key: StatKey,
    hero_metadata: Mapping[Any, Any] | None,
    rank: int,
) -> dict[str, Any]:
    hero_id = _hero_id(row)
    return {
        "rank": rank,
        **_hero_ref(hero_id, hero_metadata),
        "date": _date_string(_timestamp(row)),
        "outcome": _outcome_label(row),
        "kills": _stat(row, "kills"),
        "deaths": _stat(row, "deaths"),
        "assists": _stat(row, "assists"),
        "duration_seconds": _duration(row),
        "stat_value": _stat(row, stat_key),
    }


def build_stat_module(
    rows: Sequence[Row],
    stat_key: StatKey,
    *,
    hero_metadata: Mapping[Any, Any] | None = None,
) -> StoryModule:
    total = sum(value or 0 for row in rows if (value := _stat(row, stat_key)) is not None)
    hero_totals = _hero_totals(rows, value_key=stat_key)
    leading_hero = None
    if hero_totals:
        hero_id = cast(int, hero_totals[0]["hero_id"])
        if _safe_hero_name(hero_id, hero_metadata) is not None:
            leading_hero = {
                **_hero_ref(hero_id, hero_metadata),
                "total": hero_totals[0]["total"],
            }
    # The individual rows belong to the leading hero.  Page 22/23/24 copy names
    # that hero ("The three games where {Hero} really got involved"), so rows
    # drawn from the whole roster would contradict the sentence introducing
    # them.  Without a leading hero there is no such sentence and no rows.
    leading_hero_id = leading_hero["hero_id"] if leading_hero else None
    candidates = [
        (index, row)
        for index, row in enumerate(rows)
        if leading_hero_id is not None
        and _hero_id(row) == leading_hero_id
        and (_stat(row, stat_key) or 0) > 0
        and _date_string(_timestamp(row)) is not None
        and _outcome_label(row) is not None
        and all(_stat(row, key) is not None for key in ("kills", "deaths", "assists"))
        and _duration(row) is not None
    ]
    candidates.sort(
        key=lambda item: (
            _descending(_stat(item[1], stat_key)),
            _descending(_duration(item[1])),
            _descending(_timestamp(item[1])),
            _internal_id(item[1], item[0]),
        )
    )
    individuals = [
        _stat_match_row(row, stat_key=stat_key, hero_metadata=hero_metadata, rank=rank)
        for rank, (_index, row) in enumerate(candidates[:3], start=1)
    ]
    return _module(
        "available",
        {"total": total, "leading_hero": leading_hero, "individuals": individuals},
        copy_variant="zero" if total == 0 else "available",
    )


def build_kills_module(rows: Sequence[Row], *, hero_metadata: Mapping[Any, Any] | None = None) -> StoryModule:
    return build_stat_module(rows, "kills", hero_metadata=hero_metadata)


def build_assists_module(rows: Sequence[Row], *, hero_metadata: Mapping[Any, Any] | None = None) -> StoryModule:
    return build_stat_module(rows, "assists", hero_metadata=hero_metadata)


def build_deaths_module(rows: Sequence[Row], *, hero_metadata: Mapping[Any, Any] | None = None) -> StoryModule:
    return build_stat_module(rows, "deaths", hero_metadata=hero_metadata)


def _display_name(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value or None


def _build_hello_module(
    rows: Sequence[Row],
    *,
    display_name: str | None,
    window_start: int | None,
    window_end: int | None,
    history_completeness: HistoryCompleteness | bool,
) -> StoryModule:
    dated = _dated_rows(rows)
    bounds = _window_dates(rows, window_start=window_start, window_end=window_end)
    if not dated or bounds is None:
        return _module("omitted", reason="no_dated_matches", copy_variant="unavailable")
    observed_from = _date_string(_timestamp(dated[0][1]))
    observed_to = _date_string(_timestamp(dated[-1][1]))
    if observed_from is None or observed_to is None:
        return _module("omitted", reason="no_observed_dates", copy_variant="unavailable")
    start, end = bounds
    observed_start = _parse_date(observed_from)
    observed_end = _parse_date(observed_to)
    if observed_start is None or observed_end is None:
        return _module("omitted", reason="no_observed_dates", copy_variant="unavailable")
    short_history = (
        (observed_end - observed_start).days + 1 < 335
        or not _history_is_complete(history_completeness)
    )
    safe_display_name = _display_name(display_name)
    return _module(
        "available",
        {
            "display_name": safe_display_name,
            "requested_window_days": 365,
            "window_start": start.isoformat(),
            "window_end": end.isoformat(),
            "observed_from": observed_from,
            "observed_to": observed_to,
            "history_materially_short": short_history,
        },
        copy_variant=("named" if safe_display_name else "anonymous")
        + ("_short" if short_history else "_full"),
    )


def _build_match_count_module(rows: Sequence[Row]) -> StoryModule:
    match_count = len(rows)
    if match_count < 30:
        return _module("omitted", reason="fewer_than_thirty_matches", copy_variant="unavailable")
    return _module(
        "available",
        {
            "match_count": match_count,
            "volume_variant": "limited" if match_count < 60 else "normal",
        },
        copy_variant="limited" if match_count < 60 else "normal",
    )


def _build_deferred_modules(*, deep_available: bool) -> dict[str, StoryModule]:
    """Return interface-only modules whose computation belongs elsewhere.

    These entries are deliberately emitted by the complete builder so callers
    never infer a missing key to mean an old payload or an accidental partial
    aggregation.  Their nullable data follows the same state boundary as the
    computed facts, while Death Context is intentionally not represented.
    """

    return {
        "element_distinctiveness": _module(
            "not_ready",
            reason="analytical_release_required",
            copy_variant="not_ready",
        ),
        "archetype": _module(
            "not_ready",
            {
                "production_ready": False,
                "name": None,
                "description": None,
                "evidence_anchors": [],
                "recap_available": False,
                "share_card_available": False,
            },
            reason="archetype_not_ready",
            copy_variant="not_ready",
        ),
        # Card membership depends on the final page/finding projection, so it
        # is intentionally left to the payload assembly layer.
        "card_collage": _module(
            "omitted",
            reason="card_manifest_not_ready",
            copy_variant="unavailable",
        ),
        "final_identity_card": _module(
            "not_ready",
            reason="archetype_not_ready",
            copy_variant="not_ready",
        ),
        "deep": (
            _module("available", {"available": True}, copy_variant="available")
            if deep_available
            else _module(
                "degraded",
                {"available": False},
                reason="deep_unavailable",
                copy_variant="unavailable",
            )
        ),
    }


def build_story_modules(
    rows: Sequence[Row],
    *,
    hero_metadata: Mapping[Any, Any] | None = None,
    window_start: int | None = None,
    window_end: int | None = None,
    history_completeness: HistoryCompleteness | bool = "complete",
    mode_map_valid: bool = True,
    display_name: str | None = None,
    deep_available: bool = False,
) -> StoryModules:
    """Build the complete typed story module map.

    The fact modules are computed from the supplied story rows.  Interface
    modules remain explicit and unavailable until their separately owned
    analytical or assembly inputs exist.  No finding slots, page manifest, or
    Death Context entry is produced here.
    """

    rows = tuple(rows)
    hello = _build_hello_module(
        rows,
        display_name=display_name,
        window_start=window_start,
        window_end=window_end,
        history_completeness=history_completeness,
    )
    match_count = _build_match_count_module(rows)
    hours = build_hours_module(rows)
    week = build_busiest_week_module(rows)
    longest = build_longest_match_module(rows, hero_metadata=hero_metadata)
    day = build_busiest_day_module(rows, busiest_week=week, longest_match=longest)
    longest_data = longest.get("data")
    day_data = day.get("data")
    if longest.get("state") == "available" and isinstance(longest_data, dict):
        longest = build_longest_match_module(
            rows,
            hero_metadata=hero_metadata,
            busiest_day=day_data.get("date") if isinstance(day_data, dict) else None,
        )
    eras = build_hero_eras_module(
        rows,
        hero_metadata=hero_metadata,
        window_start=window_start,
        window_end=window_end,
    )
    winning_streak = build_winning_streak_module(rows, hero_metadata=hero_metadata)
    losing_streak = build_losing_streak_module(
        rows,
        hero_metadata=hero_metadata,
        history_completeness=history_completeness,
    )
    breaker_hero_id = None
    losing_data = losing_streak.get("data")
    if isinstance(losing_data, dict) and isinstance(losing_data.get("breaker"), Mapping):
        breaker_data = losing_data.get("breaker")
        if isinstance(breaker_data, Mapping):
            breaker_hero_id = _int(breaker_data.get("hero_id"), minimum=1)
    modules: StoryModules = {
        "hello": hello,
        "match_count": match_count,
        "hours_in_matches": hours,
        "rank_points": build_rank_points_module(rows, mode_map_valid=mode_map_valid),
        "busiest_week": week,
        "busiest_day": day,
        "longest_match": longest,
        "wins_bridge": build_wins_bridge_module(rows),
        "win_summary": build_win_summary_module(rows),
        "winning_streak": winning_streak,
        "top_win_heroes": build_top_win_heroes_module(rows, hero_metadata=hero_metadata),
        "losing_streak": losing_streak,
        "top_loss_heroes": build_top_loss_heroes_module(
            rows,
            hero_metadata=hero_metadata,
            breaker_hero_id=breaker_hero_id,
        ),
        "hero_pool": build_hero_pool_module(rows, hero_metadata=hero_metadata),
        "hero_eras": eras,
        "hero_era_payoff": build_hero_era_payoff_module(
            eras,
            hero_metadata=hero_metadata,
        ),
        "kills": build_kills_module(rows, hero_metadata=hero_metadata),
        "assists": build_assists_module(rows, hero_metadata=hero_metadata),
        "deaths": build_deaths_module(rows, hero_metadata=hero_metadata),
    }
    modules.update(_build_deferred_modules(deep_available=deep_available))
    return modules

__all__ = [
    "DURATION_SUM_COVERAGE_THRESHOLD",
    "HistoryCompleteness",
    "LONGEST_MATCH_THRESHOLD_SECONDS",
    "MIN_BUSY_DAY_MATCHES",
    "MIN_HERO_ERA_MATCHES",
    "MIN_NON_SPARSE_MONTHS",
    "MIN_RANKED_MATCHES",
    "RANK_POINTS_PER_MATCH",
    "RANKED_MODE_LOBBY_TUPLES",
    "STORY_MODULE_KEYS",
    "StoryModule",
    "StoryModules",
    "StoryState",
    "build_assists_module",
    "build_busiest_day_module",
    "build_busiest_week_module",
    "build_deaths_module",
    "build_hero_era_payoff_module",
    "build_hero_eras_module",
    "build_hero_pool_module",
    "build_hours_module",
    "build_kills_module",
    "build_longest_match_module",
    "build_losing_streak_module",
    "build_rank_points_module",
    "build_stat_module",
    "build_story_modules",
    "build_top_loss_heroes_module",
    "build_top_win_heroes_module",
    "build_win_summary_module",
    "build_winning_streak_module",
    "build_wins_bridge_module",
    "format_duration",
]
