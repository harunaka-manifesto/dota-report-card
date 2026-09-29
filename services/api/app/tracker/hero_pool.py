"""Per-role hero pool (hero_pool/SSOT.md).

Each role shows its most played heroes over trailing 7, 30 and 365 local days; the value is the
number of READY Standard and Turbo matches. Presentation only: nothing here feeds baselines,
mastery, claims or any progression state.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Final, Literal

from app.tracker.activity import ROLES

CONTRACT: Final[Literal["hero-pool-v1"]] = "hero-pool-v1"
WINDOWS = (("LAST_7_DAYS", 7), ("LAST_30_DAYS", 30), ("LAST_365_DAYS", 365))
TOP_N = 10  # owner decision 2026-09-29


def window_starts(today: date) -> list[date]:
    """First local day of each window, in WINDOWS order; every window ends today inclusive."""
    return [today - timedelta(days=days - 1) for _, days in WINDOWS]


def build_roles(rows: Iterable[tuple[str, int, int, int, int, datetime]], today: date) -> list[dict]:
    """Every role x window, heroes ranked by matches, then latest play, then hero id.

    Rows are (role, hero_id, n7, n30, n365, last_played_at) per role and hero. Totals sum all
    heroes; only the hero list is cut to TOP_N.
    """
    by_role: dict[str, list[tuple[int, tuple[int, int, int], datetime]]] = defaultdict(list)
    for role, hero_id, n7, n30, n365, last_played_at in rows:
        if role in ROLES:
            by_role[role].append((hero_id, (n7, n30, n365), last_played_at))
    starts = window_starts(today)
    roles = []
    for role in ROLES:
        windows = []
        for index, (name, _) in enumerate(WINDOWS):
            ranked = sorted(((hero_id, counts[index], last) for hero_id, counts, last in by_role[role]
                             if counts[index] > 0), key=lambda item: (-item[1], -item[2].timestamp(), item[0]))
            windows.append({"window": name, "start_date": starts[index], "end_date": today,
                            "total_matches": sum(item[1] for item in ranked),
                            "heroes": [{"hero_id": hero_id, "matches": matches}
                                       for hero_id, matches, _ in ranked[:TOP_N]]})
        roles.append({"role": role, "windows": windows})
    return roles
