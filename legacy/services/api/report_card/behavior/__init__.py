"""Tier-agnostic behavioral semantics for Free and future Deep reports.

The package owns the meaning of observations after ingestion.  It deliberately
does not import an OpenDota transport client: orchestration supplies typed
evidence, and the semantic layers only calculate from that evidence.
"""

from report_card.behavior.models import (
    BehaviorAnalysisResult,
    BehaviorQualitySummary,
    DimensionSummary,
    ElementResult,
    PatternActionEvidence,
    PatternResult,
)
from report_card.behavior.presentation import PatternPresentationPayload


def __getattr__(name: str):
    if name == "analyze_behavior":
        from report_card.behavior.service import analyze_behavior

        return analyze_behavior
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BehaviorAnalysisResult",
    "BehaviorQualitySummary",
    "DimensionSummary",
    "ElementResult",
    "PatternActionEvidence",
    "PatternResult",
    "PatternPresentationPayload",
    "analyze_behavior",
]
