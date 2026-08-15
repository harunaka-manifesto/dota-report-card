from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from statistics import median
from typing import Any

from app.features.models import MatchFeature

COHORT_LEVELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("hero_role_rank_patch", ("hero_id", "role", "rank_tier", "patch")),
    ("hero_role_rank", ("hero_id", "role", "rank_tier")),
    ("role_rank_patch", ("role", "rank_tier", "patch")),
    ("role_rank", ("role", "rank_tier")),
    ("rank", ("rank_tier",)),
    ("global", ()),
)


@dataclass(frozen=True, slots=True)
class CohortSelection:
    valid: bool
    level: str | None
    dimensions: dict[str, Any]
    sample_size: int
    distinct_players: int
    metrics: dict[str, float]
    suppression_reason: str | None = None
    source: str = "internal_participants"

    @property
    def fallback_level(self) -> str | None:
        return self.level

    def as_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "level": self.level,
            "dimensions": dict(self.dimensions),
            "sample_size": self.sample_size,
            "distinct_players": self.distinct_players,
            "metrics": dict(self.metrics),
            "suppression_reason": self.suppression_reason,
            "source": self.source,
        }


def select_narrowest_cohort(
    player: MatchFeature | Mapping[str, Any],
    population: Iterable[MatchFeature | Mapping[str, Any]],
    *,
    minimum_rows: int = 20,
    minimum_distinct_players: int = 5,
) -> CohortSelection:
    target = _as_mapping(player)
    rows = [_as_mapping(row) for row in population]
    rows = [row for row in rows if row.get("account_id") != target.get("account_id")]
    last_dimensions: dict[str, Any] = {}
    for level, dimensions in COHORT_LEVELS:
        last_dimensions = {dimension: target.get(dimension) for dimension in dimensions}
        candidates = [
            row
            for row in rows
            if all(
                _same_value(row.get(dimension), target.get(dimension)) for dimension in dimensions
            )
        ]
        distinct_players = len(
            {row.get("account_id") for row in candidates if row.get("account_id") is not None}
        )
        if len(candidates) >= minimum_rows and distinct_players >= minimum_distinct_players:
            return CohortSelection(
                valid=True,
                level=level,
                dimensions=last_dimensions,
                sample_size=len(candidates),
                distinct_players=distinct_players,
                metrics=aggregate_metrics(candidates),
            )
    return CohortSelection(
        valid=False,
        level=None,
        dimensions=last_dimensions,
        sample_size=0,
        distinct_players=0,
        metrics={},
        suppression_reason="NO_VALID_COHORT",
    )


def aggregate_metrics(rows: Iterable[MatchFeature | Mapping[str, Any]]) -> dict[str, float]:
    mapped = [_as_mapping(row) for row in rows]
    if not mapped:
        return {}
    return {
        "win_rate": sum(1 for row in mapped if bool(row.get("won"))) / len(mapped),
        "median_gold_per_min": float(median(_numbers(mapped, "gold_per_min"))),
        "median_xp_per_min": float(median(_numbers(mapped, "xp_per_min"))),
        "median_last_hits": float(median(_numbers(mapped, "last_hits"))),
        "median_tower_damage": float(median(_numbers(mapped, "tower_damage"))),
        "median_duration_minutes": float(median(_numbers(mapped, "duration_seconds"))) / 60,
        "median_impact_score": float(median(_impact(row) for row in mapped)),
    }


def _as_mapping(row: MatchFeature | Mapping[str, Any]) -> Mapping[str, Any]:
    if isinstance(row, Mapping):
        return row
    return row.as_dict()


def _same_value(left: Any, right: Any) -> bool:
    return left == right or (left is None and right is None)


def _numbers(rows: list[Mapping[str, Any]], key: str) -> list[float]:
    return [float(row.get(key) or 0) for row in rows]


def _impact(row: Mapping[str, Any]) -> float:
    if "impact_score" in row:
        return float(row["impact_score"])
    return (
        float(row.get("kills") or 0)
        + float(row.get("assists") or 0) * 0.45
        + float(row.get("hero_damage") or 0) / 1000
        + float(row.get("tower_damage") or 0) / 800
        + float(row.get("objective_count") or 0) * 0.8
    )
