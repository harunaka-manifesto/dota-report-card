from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.ingestion.coverage import ParseCoverage


@dataclass(frozen=True, slots=True)
class MatchFeature:
    match_id: int
    account_id: int
    start_time: int | None
    hero_id: int | None
    role: int | None
    role_probability: float
    role_method: str
    role_signals: dict[str, float]
    rank_tier: int | None
    patch: str | None
    side: str
    won: bool
    duration_seconds: int
    kills: int
    deaths: int
    assists: int
    last_hits: int
    denies: int
    gold_per_min: float
    xp_per_min: float
    net_worth: float
    gold_spent: float
    hero_damage: float
    tower_damage: float
    hero_healing: float
    obs_placed: int
    sen_placed: int
    party_size: int | None
    item_ids: tuple[int, ...]
    item_timings: tuple[tuple[int, int], ...]
    time_series: tuple[float, ...]
    objective_count: int
    teamfight_count: int
    parsed_coverage: float
    coverage: ParseCoverage
    source_match_ids: tuple[int, ...] = field(default_factory=tuple)
    derived: dict[str, float] = field(default_factory=dict)

    @property
    def duration_minutes(self) -> float:
        return self.duration_seconds / 60.0

    @property
    def impact_score(self) -> float:
        return (
            self.kills
            + self.assists * 0.45
            + self.hero_damage / 1000
            + self.tower_damage / 800
            + self.objective_count * 0.8
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "account_id": self.account_id,
            "start_time": self.start_time,
            "hero_id": self.hero_id,
            "role": self.role,
            "role_probability": self.role_probability,
            "role_method": self.role_method,
            "role_signals": dict(self.role_signals),
            "rank_tier": self.rank_tier,
            "patch": self.patch,
            "side": self.side,
            "won": self.won,
            "duration_seconds": self.duration_seconds,
            "kills": self.kills,
            "deaths": self.deaths,
            "assists": self.assists,
            "last_hits": self.last_hits,
            "denies": self.denies,
            "gold_per_min": self.gold_per_min,
            "xp_per_min": self.xp_per_min,
            "net_worth": self.net_worth,
            "gold_spent": self.gold_spent,
            "hero_damage": self.hero_damage,
            "tower_damage": self.tower_damage,
            "hero_healing": self.hero_healing,
            "obs_placed": self.obs_placed,
            "sen_placed": self.sen_placed,
            "party_size": self.party_size,
            "item_ids": list(self.item_ids),
            "item_timings": [list(item) for item in self.item_timings],
            "time_series": list(self.time_series),
            "objective_count": self.objective_count,
            "teamfight_count": self.teamfight_count,
            "parsed_coverage": self.parsed_coverage,
            "coverage": self.coverage.as_dict(),
            "source_match_ids": list(self.source_match_ids),
            "derived": dict(self.derived),
        }
