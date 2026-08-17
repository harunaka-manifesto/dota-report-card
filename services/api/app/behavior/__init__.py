"""Tier-agnostic behavioral semantics for Free and future Deep reports.

The package owns the meaning of observations after ingestion.  It deliberately
does not import an OpenDota transport client: orchestration supplies typed
evidence, and the semantic layers only calculate from that evidence.
"""

from app.behavior.models import (
    BehaviorAnalysisResult,
    BehaviorQualitySummary,
    ContextArchetypeResult,
    DimensionSummary,
    ElementResult,
    PatternResult,
)
from app.behavior.service import analyze_behavior

__all__ = [
    "BehaviorAnalysisResult",
    "BehaviorQualitySummary",
    "ContextArchetypeResult",
    "DimensionSummary",
    "ElementResult",
    "PatternResult",
    "analyze_behavior",
]
