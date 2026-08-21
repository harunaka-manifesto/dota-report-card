"""Hero history synthesis kept separate from the Elements/Patterns model."""

from app.hero_portfolio.models import (
    ChoiceOption,
    CommonThreadResult,
    HeroEligibility,
    HeroExceptionResult,
    HeroMirrorResult,
    HeroPortfolioResult,
    PoolEvolutionResult,
)


def __getattr__(name: str):
    if name == "analyze_hero_portfolio":
        from app.hero_portfolio.service import analyze_hero_portfolio

        return analyze_hero_portfolio
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ChoiceOption",
    "CommonThreadResult",
    "HeroEligibility",
    "HeroExceptionResult",
    "HeroMirrorResult",
    "HeroPortfolioResult",
    "PoolEvolutionResult",
    "analyze_hero_portfolio",
]
