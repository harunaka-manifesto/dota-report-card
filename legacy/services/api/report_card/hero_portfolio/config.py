"""Versioned product-significant thresholds for Hero Portfolio and actions.

These values are intentionally ordinary checked-in constants.  A calibration
change should be visible in review and should change the analysis fingerprint;
the report does not need a runtime configuration service for that guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass

PORTFOLIO_CONFIG_VERSION = "hero-portfolio-config-5.2.0"


@dataclass(frozen=True, slots=True)
class PortfolioAnalysisConfig:
    common_thread_min_matches: int = 3
    exception_min_matches: int = 4
    mirror_min_matches: int = 4
    min_share: float = 0.03
    min_recency: float = 0.20
    sustained_match_threshold: int = 8
    common_thread_min_coverage: float = 0.35
    common_thread_min_margin: float = 0.03
    exception_min_distance: float = 0.32
    exception_min_margin: float = 0.06
    evolution_min_window_size: int = 12
    evolution_max_window_size: int = 24
    evolution_taxonomy_coverage_gate: float = 0.80
    evolution_hero_shift_threshold: float = 0.22
    evolution_toolkit_shift_threshold: float = 0.18
    evolution_core_overlap_threshold: float = 0.35
    mirror_min_independent_reference: int = 12
    mirror_sample_saturation: int = 20
    mirror_min_sample_confidence: float = 0.35
    mirror_min_dimension_coverage: float = 0.75
    mirror_min_final_score: float = 0.55
    mirror_min_runner_up_margin: float = 0.04
    p04_min_core_heroes: int = 2
    p04_max_core_heroes: int = 5
    p04_min_role_relevant_family_coverage: float = 0.60
    p04_max_functional_overlap: float = 0.75
    p04_min_unique_contributions: int = 2
    p04_min_semantic_confidence: float = 0.35
    p04_min_semantic_coverage: float = 0.80
    # Free DNA is bounded by the one-year window, not by a hidden 500-row
    # action slice.  Keep the field as an optional infrastructure guardrail.
    p02_history_limit: int | None = None
    p02_min_rankable_matches: int = 10
    p02_min_action_heroes: int = 5
    p02_reference_core_size: int = 2
    p02_shrinkage_prior: float = 20.0
    p02_recency_floor: float = 0.50


PORTFOLIO_CONFIG = PortfolioAnalysisConfig()


__all__ = ["PORTFOLIO_CONFIG", "PORTFOLIO_CONFIG_VERSION", "PortfolioAnalysisConfig"]
