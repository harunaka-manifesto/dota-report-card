"""Deterministic orchestration for the independent Hero Portfolio stage."""

from __future__ import annotations

from collections.abc import Sequence

from app.behavior.models import BehaviorAnalysisResult
from app.hero_portfolio.common_thread import compute_common_thread
from app.hero_portfolio.eligibility import build_hero_eligibility
from app.hero_portfolio.evolution import compute_pool_evolution
from app.hero_portfolio.exception import compute_hero_exception
from app.hero_portfolio.mirror import compute_hero_mirror
from app.hero_portfolio.models import HeroPortfolioResult
from app.hero_portfolio.version import HERO_PORTFOLIO_VERSION
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch


def analyze_hero_portfolio(
    matches: Sequence[NormalizedSummaryMatch],
    *,
    hero_taxonomy: HeroTaxonomy,
    behavior: BehaviorAnalysisResult | None = None,
    report_seed: str | None = None,
) -> HeroPortfolioResult:
    """Build all portfolio insights from summary history and reviewed taxonomy.

    ``behavior`` is accepted for orchestration compatibility and future
    evidence-aware copy, but no Element score is used as a substitute for
    hero-level history in the current portfolio calculations.
    """

    del behavior
    eligibility = build_hero_eligibility(matches, hero_taxonomy)
    return HeroPortfolioResult(
        common_thread=compute_common_thread(matches, hero_taxonomy, eligibility, report_seed=report_seed),
        exception=compute_hero_exception(matches, hero_taxonomy, eligibility, report_seed=report_seed),
        evolution=compute_pool_evolution(matches, hero_taxonomy),
        hero_mirror=compute_hero_mirror(matches, hero_taxonomy, eligibility),
        version=HERO_PORTFOLIO_VERSION,
        eligibility=eligibility,
    )


__all__ = ["analyze_hero_portfolio"]
