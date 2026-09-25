"""Deterministic orchestration for the independent Hero Portfolio stage."""

from __future__ import annotations

from collections.abc import Sequence

from app.ingestion.summary_normalize import NormalizedSummaryMatch

from report_card.behavior.models import BehaviorAnalysisResult
from report_card.hero_portfolio.common_thread import compute_common_thread
from report_card.hero_portfolio.eligibility import build_hero_eligibility
from report_card.hero_portfolio.evolution import compute_pool_evolution
from report_card.hero_portfolio.exception import compute_hero_exception
from report_card.hero_portfolio.mirror import compute_hero_mirror
from report_card.hero_portfolio.models import HeroPortfolioResult
from report_card.hero_portfolio.version import HERO_PORTFOLIO_VERSION
from report_card.heroes.knowledge import HeroKnowledgeProvider
from report_card.heroes.taxonomy import HeroTaxonomy


def analyze_hero_portfolio(
    matches: Sequence[NormalizedSummaryMatch],
    *,
    hero_taxonomy: HeroTaxonomy,
    behavior: BehaviorAnalysisResult | None = None,
    hero_knowledge: HeroKnowledgeProvider | None = None,
    report_seed: str | None = None,
) -> HeroPortfolioResult:
    """Build all portfolio insights from summary history and reviewed taxonomy.

    ``behavior`` is accepted for orchestration compatibility and future
    evidence-aware copy, but no Element score is used as a substitute for
    hero-level history in the current portfolio calculations.
    """

    del behavior
    eligibility = build_hero_eligibility(
        matches, hero_taxonomy, hero_knowledge=hero_knowledge
    )
    return HeroPortfolioResult(
        common_thread=compute_common_thread(
            matches,
            hero_taxonomy,
            eligibility,
            report_seed=report_seed,
            hero_knowledge=hero_knowledge,
        ),
        exception=compute_hero_exception(
            matches,
            hero_taxonomy,
            eligibility,
            report_seed=report_seed,
            hero_knowledge=hero_knowledge,
        ),
        evolution=compute_pool_evolution(matches, hero_taxonomy, hero_knowledge),
        hero_mirror=compute_hero_mirror(
            matches, hero_taxonomy, eligibility, hero_knowledge=hero_knowledge
        ),
        version=HERO_PORTFOLIO_VERSION,
        eligibility=eligibility,
    )


__all__ = ["analyze_hero_portfolio"]
