"""Public-safe internal models for Hero Portfolio synthesis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

PortfolioStatus = Literal["available", "no_clear_thread", "unavailable"]
ExceptionStatus = Literal["available", "no_clear_exception", "unavailable"]
MirrorStatus = Literal["available", "no_clear_mirror", "unavailable"]


@dataclass(frozen=True, slots=True)
class ChoiceOption:
    key: str
    label: str
    hero_id: int | None = None
    feedback: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "hero_id": self.hero_id,
            "feedback": self.feedback,
        }


@dataclass(frozen=True, slots=True)
class HeroEligibility:
    hero_id: int
    matches: int
    share: float
    recency: float
    coverage: float
    eligible_for_common_thread: bool
    eligible_for_exception: bool
    eligible_for_mirror: bool
    exclusion_reasons: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "matches": self.matches,
            "share": round(self.share, 6),
            "recency": round(self.recency, 6),
            "coverage": round(self.coverage, 6),
            "eligible_for_common_thread": self.eligible_for_common_thread,
            "eligible_for_exception": self.eligible_for_exception,
            "eligible_for_mirror": self.eligible_for_mirror,
            "exclusion_reasons": list(self.exclusion_reasons),
        }


@dataclass(frozen=True, slots=True)
class CommonThreadResult:
    status: PortfolioStatus
    trait_key: str | None
    trait_label: str | None
    weighted_coverage: float
    hero_count: int
    denominator: int
    secondary_traits: tuple[str, ...]
    options: tuple[ChoiceOption, ...]
    correct_option_key: str | None
    confidence_score: float
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "trait_key": self.trait_key,
            "trait_label": self.trait_label,
            "weighted_coverage": round(self.weighted_coverage, 6),
            "hero_count": self.hero_count,
            "denominator": self.denominator,
            "secondary_traits": list(self.secondary_traits),
            "options": [item.as_dict() for item in self.options],
            "correct_option_key": self.correct_option_key,
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class HeroExceptionResult:
    status: ExceptionStatus
    hero_id: int | None
    hero_name: str | None
    pool_traits: tuple[str, ...]
    exception_traits: tuple[str, ...]
    options: tuple[ChoiceOption, ...]
    correct_option_key: str | None
    distance: float | None
    margin: float | None
    confidence_score: float
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "hero_id": self.hero_id,
            "hero_name": self.hero_name,
            "pool_traits": list(self.pool_traits),
            "exception_traits": list(self.exception_traits),
            "options": [item.as_dict() for item in self.options],
            "correct_option_key": self.correct_option_key,
            "distance": round(self.distance, 6) if self.distance is not None else None,
            "margin": round(self.margin, 6) if self.margin is not None else None,
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class PoolEvolutionResult:
    status: Literal["available", "unavailable"]
    variant: str | None
    earlier_hero_ids: tuple[int, ...]
    recent_hero_ids: tuple[int, ...]
    earlier_traits: tuple[str, ...]
    recent_traits: tuple[str, ...]
    hero_distribution_shift: float | None
    toolkit_distribution_shift: float | None
    confidence_score: float
    earlier_sample_size: int = 0
    recent_sample_size: int = 0
    earlier_taxonomy_coverage: float = 0.0
    recent_taxonomy_coverage: float = 0.0
    earlier_start: str | None = None
    earlier_end: str | None = None
    recent_start: str | None = None
    recent_end: str | None = None
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "variant": self.variant,
            "earlier_hero_ids": list(self.earlier_hero_ids),
            "recent_hero_ids": list(self.recent_hero_ids),
            "earlier_traits": list(self.earlier_traits),
            "recent_traits": list(self.recent_traits),
            "hero_distribution_shift": round(self.hero_distribution_shift, 6) if self.hero_distribution_shift is not None else None,
            "toolkit_distribution_shift": round(self.toolkit_distribution_shift, 6) if self.toolkit_distribution_shift is not None else None,
            "confidence_score": round(self.confidence_score, 6),
            "earlier_sample_size": self.earlier_sample_size,
            "recent_sample_size": self.recent_sample_size,
            "earlier_taxonomy_coverage": round(self.earlier_taxonomy_coverage, 6),
            "recent_taxonomy_coverage": round(self.recent_taxonomy_coverage, 6),
            "earlier_start": self.earlier_start,
            "earlier_end": self.earlier_end,
            "recent_start": self.recent_start,
            "recent_end": self.recent_end,
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class HeroMirrorResult:
    status: MirrorStatus
    hero_id: int | None
    hero_name: str | None
    similarity_score: float | None
    runner_up_hero_id: int | None
    margin: float | None
    player_behavior: dict[str, str]
    hero_behavior: dict[str, str]
    confidence_score: float
    limitations: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "hero_id": self.hero_id,
            "hero_name": self.hero_name,
            "similarity_score": round(self.similarity_score, 6) if self.similarity_score is not None else None,
            "runner_up_hero_id": self.runner_up_hero_id,
            "margin": round(self.margin, 6) if self.margin is not None else None,
            "player_behavior": dict(self.player_behavior),
            "hero_behavior": dict(self.hero_behavior),
            "confidence_score": round(self.confidence_score, 6),
            "limitations": list(self.limitations),
        }


@dataclass(frozen=True, slots=True)
class HeroPortfolioResult:
    common_thread: CommonThreadResult
    exception: HeroExceptionResult
    evolution: PoolEvolutionResult
    hero_mirror: HeroMirrorResult
    version: str
    eligibility: tuple[HeroEligibility, ...] = field(default_factory=tuple)

    def as_dict(self, *, include_private_eligibility: bool = False) -> dict[str, Any]:
        value: dict[str, Any] = {
            "common_thread": self.common_thread.as_dict(),
            "exception": self.exception.as_dict(),
            "evolution": self.evolution.as_dict(),
            "hero_mirror": self.hero_mirror.as_dict(),
            "version": self.version,
        }
        if include_private_eligibility:
            value["eligibility"] = [item.as_dict() for item in self.eligibility]
        return value
