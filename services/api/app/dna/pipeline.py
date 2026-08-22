"""Summary-only Free DNA pipeline: Elements → Patterns → Hero Portfolio."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.behavior.elements.service import SummaryBehaviorContext
from app.behavior.models import BehaviorAnalysisResult
from app.behavior.service import analyze_behavior
from app.dna.features.extractor import extract_dna_features
from app.dna.features.models import DnaFeatureSet
from app.dna.recency import DEFAULT_HALF_LIFE_DAYS
from app.dna.sessions import SessionPolicy, SessionResult, infer_sessions
from app.hero_portfolio.models import HeroPortfolioResult
from app.hero_portfolio.service import analyze_hero_portfolio
from app.heroes.taxonomy import HeroTaxonomy, load_default_taxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch

DNA_SCORING_VERSION = "dna-scoring-5.0.0"
StageCallback = Callable[[str, str], None]


@dataclass(frozen=True, slots=True)
class DnaAnalysisResult:
    matches: tuple[NormalizedSummaryMatch, ...]
    sessions: SessionResult
    features: DnaFeatureSet
    behavior: BehaviorAnalysisResult
    hero_portfolio: HeroPortfolioResult
    history_tier: str = "normal"
    # Retain the normalized snapshot used during scoring so report
    # presentation can use the same hero identities and never silently load a
    # different knowledge version during assembly.
    taxonomy: HeroTaxonomy | None = None

    @property
    def overall_confidence(self) -> str:
        return self.behavior.quality.overall_confidence

    @property
    def warnings(self) -> tuple[str, ...]:
        warnings = list(self.behavior.quality.warnings)
        warnings.extend(self.hero_portfolio.common_thread.limitations)
        warnings.extend(self.hero_portfolio.exception.limitations)
        warnings.extend(self.hero_portfolio.evolution.limitations)
        warnings.extend(self.hero_portfolio.hero_mirror.limitations)
        return tuple(dict.fromkeys(warnings))

    def as_dict(self) -> dict[str, Any]:
        return {
            "feature_version": self.features.feature_version,
            "session_version": self.sessions.policy.version,
            "scoring_version": DNA_SCORING_VERSION,
            "features": self.features.as_dict(),
            "sessions": self.sessions.as_dict(),
            "behavior": self.behavior.as_dict(public=False),
            "hero_portfolio": self.hero_portfolio.as_dict(include_private_eligibility=False),
            "overall_confidence": self.overall_confidence,
            "warnings": list(self.warnings),
        }


def analyze_dna(
    matches: tuple[NormalizedSummaryMatch, ...] | list[NormalizedSummaryMatch],
    *,
    session_gap_minutes: int = 90,
    taxonomy: HeroTaxonomy | None = None,
    history_tier: str | None = None,
    report_seed: str | None = None,
    window_start: int | None = None,
    window_end: int | None = None,
    pre_window_anchor: bool = False,
    recency_half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
    on_stage: StageCallback | None = None,
) -> DnaAnalysisResult:
    def stage(name: str, message: str) -> None:
        if on_stage is not None:
            on_stage(name, message)

    policy = SessionPolicy(gap_minutes=max(1, session_gap_minutes))
    stage("session_inference", "Rebuilding your play sessions.")
    sessions = infer_sessions(
        matches,
        policy,
        window_start=window_start,
        window_end=window_end,
        pre_window_anchor=pre_window_anchor,
    )
    stage("hero_features", "Mapping your established hero history.")
    features = extract_dna_features(
        sessions.matches,
        sessions,
        window_start=window_start,
        window_end=window_end,
        recency_half_life_days=recency_half_life_days,
    )
    behavior_taxonomy = taxonomy
    if behavior_taxonomy is None:
        try:
            behavior_taxonomy = load_default_taxonomy()
        except (OSError, TypeError, ValueError):
            behavior_taxonomy = None
    if behavior_taxonomy is None:
        raise ValueError("The reviewed hero taxonomy is required for Free DNA")
    history_kind = history_tier or ("limited" if 30 <= features.sample_size < 60 else "normal")
    context = SummaryBehaviorContext(
        matches=sessions.matches,
        sessions=sessions,
        features=features,
        taxonomy=behavior_taxonomy,
        history_tier=history_kind,
    )
    behavior = analyze_behavior(context, on_stage=stage)
    stage("hero_portfolio", "Comparing the established hero pool and its observable behavior.")
    portfolio = analyze_hero_portfolio(
        sessions.matches,
        hero_taxonomy=behavior_taxonomy,
        behavior=behavior,
        report_seed=report_seed,
    )
    return DnaAnalysisResult(
        matches=sessions.matches,
        sessions=sessions,
        features=features,
        behavior=behavior,
        hero_portfolio=portfolio,
        history_tier=history_kind,
        taxonomy=behavior_taxonomy,
    )
