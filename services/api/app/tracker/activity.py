"""Per-role activity heatmap (activity/SSOT.md).

A cell is one local calendar day; its value is the number of READY Standard and Turbo
matches in the entitled history. The calendar window is presentation only: nothing here
feeds baselines, trends, mastery or any progression state.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from typing import Final, Literal
from zoneinfo import ZoneInfo

CONTRACT: Final[Literal["activity-heatmap-v1"]] = "activity-heatmap-v1"
LEVELS_VERSION: Final[Literal["heatmap-levels-v1"]] = "heatmap-levels-v1"
ROLES = ("CARRY", "MID", "OFFLANE", "SUPPORT")
SERIES = ("ALL", *ROLES)
FIRST_YEAR = 2011  # Dota 2 public release; earlier years hold no matches.
TRAILING_DAYS = 365
# Minimum matches for levels 1..4 (owner decision 2026-09-29).
LEVEL_FLOORS = (1, 2, 4, 6)


def level_for_count(count: int) -> int:
    return sum(1 for floor in LEVEL_FLOORS if count >= floor)


def resolve_window(today: date, year: int | None) -> tuple[date, date]:
    """Trailing 365 local days ending today, or one calendar year clipped at today."""
    if year is None:
        return today - timedelta(days=TRAILING_DAYS - 1), today
    if not FIRST_YEAR <= year <= today.year:
        raise ValueError("YEAR_INVALID")
    return date(year, 1, 1), min(date(year, 12, 31), today)


def utc_bounds(start: date, end: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    """Half-open UTC range covering local days start..end inclusive, DST-safe."""
    return (datetime.combine(start, time.min, zone).astimezone(UTC),
            datetime.combine(end + timedelta(days=1), time.min, zone).astimezone(UTC))


def build_series(rows: Iterable[tuple[date, str, int]]) -> list[dict]:
    """Sparse ascending day counts for ALL plus each role; ALL is the sum of the roles."""
    counts: dict[str, dict[date, int]] = {name: defaultdict(int) for name in SERIES}
    for day, role, count in rows:
        if role not in ROLES:
            continue
        counts[role][day] += count
        counts["ALL"][day] += count
    return [{
        "role": name,
        "total_matches": sum(counts[name].values()),
        "days": [{"date": day, "count": count, "level": level_for_count(count)}
                 for day, count in sorted(counts[name].items())],
    } for name in SERIES]
