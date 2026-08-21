"""Immutable intermediate features for the Free DNA scorers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.dna.sessions import Session
from app.ingestion.summary_normalize import NormalizedSummaryMatch

FEATURE_VERSION = "dna-features-5.0.0"


def _median(values: Any) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    return ordered[middle] if len(ordered) % 2 else (ordered[middle - 1] + ordered[middle]) / 2


def _quantile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    position = (len(values) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _quantiles(values: tuple[int, ...]) -> dict[str, float]:
    ordered = [float(value) for value in sorted(values)]
    return {
        "p25": round(_quantile(ordered, 0.25), 6),
        "p50": round(_quantile(ordered, 0.50), 6),
        "p75": round(_quantile(ordered, 0.75), 6),
    }


@dataclass(frozen=True, slots=True)
class FeatureEvidence:
    key: str
    value: float | int | str
    unit: str
    denominator: int
    source_match_ids: tuple[int, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "unit": self.unit,
            "denominator": self.denominator,
            "source_match_ids": list(self.source_match_ids),
        }


@dataclass(frozen=True, slots=True)
class DnaFeatureSet:
    matches: tuple[NormalizedSummaryMatch, ...]
    sessions: tuple[Session, ...]
    feature_version: str = FEATURE_VERSION
    sample_size: int = 0
    hero_counts: dict[int, int] = field(default_factory=dict)
    hero_entropy: float = 0.0
    normalized_hero_entropy: float = 0.0
    effective_hero_count: float = 0.0
    top_hero_shares: dict[int, float] = field(default_factory=dict)
    role_counts: dict[str, int] = field(default_factory=dict)
    role_coverage: float = 0.0
    role_entropy: float = 0.0
    normalized_role_entropy: float = 0.0
    dominant_role: str | None = None
    familiar_heroes: frozenset[int] = frozenset()
    activity_by_match: dict[int, float] = field(default_factory=dict)
    orientation_by_match: dict[int, float] = field(default_factory=dict)
    performance_by_match: dict[int, float] = field(default_factory=dict)
    role_performance: dict[str, tuple[float, ...]] = field(default_factory=dict)
    familiar_performance: tuple[float, ...] = ()
    off_pool_performance: tuple[float, ...] = ()
    transitions_after_win: tuple[float, ...] = ()
    transitions_after_loss: tuple[float, ...] = ()
    transitions_after_two_losses: tuple[float, ...] = ()
    endurance_by_position: dict[int, tuple[float, ...]] = field(default_factory=dict)
    session_lengths: tuple[int, ...] = ()
    session_durations: tuple[int, ...] = ()
    source_match_ids: tuple[int, ...] = ()
    dated_match_ids: tuple[int, ...] = ()
    role_match_ids: tuple[int, ...] = ()
    activity_match_ids: tuple[int, ...] = ()
    orientation_match_ids: tuple[int, ...] = ()
    familiar_match_ids: tuple[int, ...] = ()
    off_pool_match_ids: tuple[int, ...] = ()
    familiar_roles: frozenset[str] = frozenset()
    session_sensitivity: dict[int, tuple[tuple[int, ...], ...]] = field(default_factory=dict)
    session_sensitivity_scores: dict[int, dict[str, float | None]] = field(default_factory=dict)
    weights_by_match: dict[int, float] = field(default_factory=dict)
    session_weights: dict[str, float] = field(default_factory=dict)
    effective_sample_size: float = 0.0
    recency_half_life_days: float = 180.0
    recency_weighting_version: str = "recency-weighting-5.0.0"
    performance_proxy_version: str = "performance-proxy-5.0.0"
    window_start: int | None = None
    window_end: int | None = None
    left_censored_session_count: int = 0
    right_censored_session_count: int = 0

    @property
    def dated_coverage(self) -> float:
        return len(self.dated_match_ids) / self.sample_size if self.sample_size else 0.0

    @property
    def overall_win_rate(self) -> float | None:
        values = [item.won for item in self.matches if item.won is not None]
        return sum(values) / len(values) if values else None

    @property
    def unique_hero_count(self) -> int:
        return len(self.hero_counts)

    @property
    def dominant_role_share(self) -> float:
        if not self.role_counts or not self.role_match_ids:
            return 0.0
        return max(self.role_counts.values()) / len(self.role_match_ids)

    @property
    def top_3_share(self) -> float:
        return self.top_hero_shares.get(3, 0.0)

    @property
    def top_5_share(self) -> float:
        return self.top_hero_shares.get(5, 0.0)

    @property
    def top_10_share(self) -> float:
        return self.top_hero_shares.get(10, 0.0)

    @property
    def activity_median(self) -> float | None:
        return _median(self.activity_by_match.values())

    @property
    def activity_iqr(self) -> float:
        values = sorted(float(value) for value in self.activity_by_match.values())
        if len(values) < 2:
            return 0.0
        return _quantile(values, 0.75) - _quantile(values, 0.25)

    @property
    def aggregate_kill_share(self) -> float | None:
        kills = sum(
            item.kills or 0
            for item in self.matches
            if item.match_id in self.orientation_by_match
        )
        assists = sum(
            item.assists or 0
            for item in self.matches
            if item.match_id in self.orientation_by_match
        )
        return kills / (kills + assists) if kills + assists else None

    @property
    def zero_involvement_rate(self) -> float:
        rows = [
            item for item in self.matches
            if item.kills is not None and item.assists is not None
        ]
        return (
            sum((item.kills or 0) + (item.assists or 0) == 0 for item in rows) / len(rows)
            if rows
            else 0.0
        )

    @property
    def session_length_quantiles(self) -> dict[str, float]:
        return _quantiles(self.session_lengths)

    @property
    def session_duration_quantiles(self) -> dict[str, float]:
        return _quantiles(self.session_durations)

    @property
    def coverage(self) -> dict[str, float]:
        return {
            "overall": 1.0 if self.sample_size else 0.0,
            "dated": self.dated_coverage,
            "role": self.role_coverage,
            "activity": len(self.activity_match_ids) / self.sample_size if self.sample_size else 0.0,
            "orientation": len(self.orientation_match_ids) / self.sample_size if self.sample_size else 0.0,
        }

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature_version": self.feature_version,
            "sample_size": self.sample_size,
            "coverage": {key: round(value, 6) for key, value in self.coverage.items()},
            "unique_hero_count": self.unique_hero_count,
            "hero_counts": {str(key): value for key, value in self.hero_counts.items()},
            "hero_entropy": round(self.hero_entropy, 6),
            "normalized_hero_entropy": round(self.normalized_hero_entropy, 6),
            "effective_hero_count": round(self.effective_hero_count, 6),
            "top_hero_shares": {str(key): round(value, 6) for key, value in self.top_hero_shares.items()},
            "role_counts": dict(self.role_counts),
            "role_coverage": round(self.role_coverage, 6),
            "normalized_role_entropy": round(self.normalized_role_entropy, 6),
            "dominant_role": self.dominant_role,
            "dominant_role_share": round(self.dominant_role_share, 6),
            "familiar_roles": sorted(self.familiar_roles),
            "familiar_heroes": sorted(self.familiar_heroes),
            "transition_counts": {
                "after_win": len(self.transitions_after_win),
                "after_loss": len(self.transitions_after_loss),
                "after_two_losses": len(self.transitions_after_two_losses),
            },
            "endurance_counts": {str(key): len(value) for key, value in self.endurance_by_position.items()},
            "session_lengths": list(self.session_lengths),
            "session_durations": list(self.session_durations),
            "session_length_quantiles": self.session_length_quantiles,
            "session_duration_quantiles": self.session_duration_quantiles,
            "session_sensitivity": {
                str(gap): [list(group) for group in groups]
                for gap, groups in self.session_sensitivity.items()
            },
            "session_sensitivity_scores": {
                str(gap): {
                    key: round(value, 6) if value is not None else None
                    for key, value in scores.items()
                }
                for gap, scores in self.session_sensitivity_scores.items()
            },
            "source_match_ids": list(self.source_match_ids),
            "effective_sample_size": round(self.effective_sample_size, 6),
            "recency_half_life_days": self.recency_half_life_days,
            "recency_weighting_version": self.recency_weighting_version,
            "performance_proxy_version": self.performance_proxy_version,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "left_censored_session_count": self.left_censored_session_count,
            "right_censored_session_count": self.right_censored_session_count,
        }
