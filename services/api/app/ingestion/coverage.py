from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SUMMARY_FAMILIES = frozenset(
    {
        "summary",
        "role",
        "economy",
        "outcome",
        "hero_pool",
        "inventory",
    }
)
REPLAY_FAMILIES = frozenset(
    {
        "time_series",
        "events",
        "teamfights",
        "objectives",
        "wards",
    }
)


@dataclass(frozen=True, slots=True)
class ParseCoverage:
    by_family: dict[str, float]
    parser_version: int | None = None

    @property
    def summary_coverage(self) -> float:
        return _mean(self.by_family.get(name, 0.0) for name in SUMMARY_FAMILIES)

    @property
    def replay_coverage(self) -> float:
        return _mean(self.by_family.get(name, 0.0) for name in REPLAY_FAMILIES)

    @property
    def parsed(self) -> bool:
        return self.replay_coverage > 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "by_family": dict(sorted(self.by_family.items())),
            "summary_coverage": round(self.summary_coverage, 4),
            "replay_coverage": round(self.replay_coverage, 4),
            "parser_version": self.parser_version,
        }


def coverage_for_match(
    detail: dict[str, Any], target_player: dict[str, Any] | None
) -> ParseCoverage:
    players = detail.get("players") or []
    has_time_series = bool(detail.get("radiant_gold_adv") or detail.get("radiant_xp_adv"))
    has_events = bool(
        detail.get("objectives")
        or (target_player or {}).get("kills_log")
        or (target_player or {}).get("death_log")
        or (target_player or {}).get("deaths_log")
        or (target_player or {}).get("purchase_log")
        or (target_player or {}).get("buyback_log")
    )
    has_teamfights = bool(detail.get("teamfights"))
    has_wards = bool(
        (target_player or {}).get("obs_log")
        or (target_player or {}).get("sen_log")
        or (target_player or {}).get("obs_left_log")
        or (target_player or {}).get("sen_left_log")
    )
    has_inventory = any(
        key in (target_player or {})
        for key in ("item_0", "item_1", "item_2", "item_3", "item_4", "item_5")
    )
    by_family = {
        "summary": 1.0 if target_player else 0.0,
        "role": 1.0
        if target_player and ("lane_role" in target_player or len(players) >= 5)
        else 0.0,
        "economy": 1.0 if target_player and "gold_per_min" in target_player else 0.0,
        "outcome": 1.0 if detail.get("radiant_win") is not None else 0.0,
        "hero_pool": 1.0 if target_player and "hero_id" in target_player else 0.0,
        "inventory": 1.0 if has_inventory else 0.0,
        "time_series": 1.0 if has_time_series else 0.0,
        "events": 1.0 if has_events else 0.0,
        "teamfights": 1.0 if has_teamfights else 0.0,
        "objectives": 1.0 if bool(detail.get("objectives")) else 0.0,
        "wards": 1.0 if has_wards else 0.0,
    }
    return ParseCoverage(by_family=by_family, parser_version=detail.get("version"))


def _mean(values: Any) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0
