from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class SummaryMatchFeature:
    """The deliberately small Stage 1 contract.

    Values absent from the player-history response remain ``None``.  The
    summary path must never turn unavailable economy or K/D/A fields into
    zeros because that would make missing data look like a player behavior.
    """

    match_id: int
    start_time: int | None
    duration_seconds: int
    hero_id: int | None
    side: str
    won: bool
    kills: int | None = None
    deaths: int | None = None
    assists: int | None = None
    game_mode: int | None = None
    lobby_type: int | None = None
    average_rank: int | None = None
    party_size: int | None = None
    parser_version_hint: int | None = None
    gold_per_min: float | None = None
    xp_per_min: float | None = None
    lane_role: int | None = None
    session_id: str | None = None
    session_index: int | None = None
    source_index: int = 0
    account_id: int | None = None
    hero_variant: int | None = None
    lane: int | None = None
    is_roaming: bool | None = None
    role_hint: str | None = None
    role_confidence: float | None = None
    patch: str | None = None
    skill_bracket: int | None = None
    region: int | None = None
    leaver_status: int | None = None
    ended_at: int | None = None

    @property
    def duration_minutes(self) -> float:
        return self.duration_seconds / 60.0

    @property
    def duration_bucket(self) -> str:
        if self.duration_seconds < 30 * 60:
            return "short"
        if self.duration_seconds <= 45 * 60:
            return "medium"
        return "long"

    @property
    def summary_families(self) -> frozenset[str]:
        families = {"summary", "outcome"}
        if self.hero_id is not None:
            families.add("hero_pool")
        if self.lane_role is not None:
            families.add("role")
        if self.gold_per_min is not None or self.xp_per_min is not None:
            families.add("economy")
        return frozenset(families)

    def as_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "start_time": self.start_time,
            "duration_seconds": self.duration_seconds,
            "hero_id": self.hero_id,
            "side": self.side,
            "won": self.won,
            "kills": self.kills,
            "deaths": self.deaths,
            "assists": self.assists,
            "game_mode": self.game_mode,
            "lobby_type": self.lobby_type,
            "average_rank": self.average_rank,
            "party_size": self.party_size,
            "parser_version_hint": self.parser_version_hint,
            "gold_per_min": self.gold_per_min,
            "xp_per_min": self.xp_per_min,
            "lane_role": self.lane_role,
            "session_id": self.session_id,
            "session_index": self.session_index,
            "source_index": self.source_index,
            "account_id": self.account_id,
            "hero_variant": self.hero_variant,
            "lane": self.lane,
            "is_roaming": self.is_roaming,
            "role_hint": self.role_hint,
            "role_confidence": self.role_confidence,
            "patch": self.patch,
            "skill_bracket": self.skill_bracket,
            "region": self.region,
            "leaver_status": self.leaver_status,
            "ended_at": self.ended_at,
        }


@dataclass(frozen=True, slots=True)
class PlayerSession:
    session_id: str
    match_ids: tuple[int, ...]
    start_time: int | None
    end_time: int | None

    @property
    def match_count(self) -> int:
        return len(self.match_ids)

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "match_ids": list(self.match_ids),
            "start_time": self.start_time,
            "end_time": self.end_time,
            "match_count": self.match_count,
        }


@dataclass(frozen=True, slots=True)
class SummaryFeatureSet:
    matches: tuple[SummaryMatchFeature, ...]
    sessions: tuple[PlayerSession, ...] = field(default_factory=tuple)

    @property
    def ordered_matches(self) -> tuple[SummaryMatchFeature, ...]:
        return tuple(
            sorted(
                self.matches,
                key=lambda item: (item.start_time is not None, item.start_time or 0, item.match_id),
                reverse=True,
            )
        )

    @property
    def summary_coverage(self) -> float:
        if not self.matches:
            return 0.0
        guaranteed = (
            "match_id",
            "start_time",
            "duration_seconds",
            "hero_id",
            "side",
            "won",
        )
        values = []
        for match in self.matches:
            available = sum(getattr(match, name) is not None for name in guaranteed)
            values.append(available / len(guaranteed))
        return sum(values) / len(values)

    @property
    def win_rate(self) -> float | None:
        return _rate(self.matches)

    @property
    def distinct_heroes(self) -> int:
        return len({match.hero_id for match in self.matches if match.hero_id is not None})

    @property
    def hero_counts(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for match in self.matches:
            if match.hero_id is not None:
                counts[match.hero_id] = counts.get(match.hero_id, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

    def as_dict(self) -> dict[str, Any]:
        return {
            "matches": [match.as_dict() for match in self.ordered_matches],
            "sessions": [session.as_dict() for session in self.sessions],
            "summary_coverage": round(self.summary_coverage, 4),
            "win_rate": self.win_rate,
            "distinct_heroes": self.distinct_heroes,
        }


def _rate(matches: tuple[SummaryMatchFeature, ...]) -> float | None:
    known = [match.won for match in matches]
    return sum(known) / len(known) if known else None
