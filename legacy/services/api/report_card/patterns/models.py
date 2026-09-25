from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class PatternEvidence:
    metric: str
    value: float | None
    baseline: float | None
    unit: str
    numerator: float | None = None
    denominator: int = 0
    source_match_ids: tuple[int, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "metric": self.metric,
            "value": self.value,
            "baseline": self.baseline,
            "unit": self.unit,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "source_match_ids": list(self.source_match_ids),
        }


@dataclass(frozen=True, slots=True)
class PatternCandidate:
    pattern_id: str
    subject: dict[str, Any]
    statement: str
    effect_size: float
    sample_size: int
    stability: float
    actionability: float
    summary_confidence: float
    unexplained: bool
    category: str = "context"
    baseline_value: float | None = None
    unit: str = "difference"
    source_match_ids: tuple[int, ...] = ()
    evidence: tuple[PatternEvidence, ...] = ()
    confounders: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def strength(self) -> float:
        return min(1.0, abs(self.effect_size))

    @property
    def priority(self) -> float:
        return (
            self.strength
            * max(0.0, min(1.0, self.summary_confidence))
            * max(0.0, min(1.0, self.actionability))
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "subject": dict(self.subject),
            "statement": self.statement,
            "effect_size": round(self.effect_size, 6),
            "sample_size": self.sample_size,
            "stability": round(self.stability, 4),
            "actionability": round(self.actionability, 4),
            "summary_confidence": round(self.summary_confidence, 4),
            "priority": round(self.priority, 4),
            "unexplained": self.unexplained,
            "category": self.category,
            "baseline_value": self.baseline_value,
            "unit": self.unit,
            "source_match_ids": list(self.source_match_ids),
            "evidence": [item.as_dict() for item in self.evidence],
            "confounders": list(self.confounders),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class PatternPriority:
    pattern_id: str
    score: float
    reason: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "score": round(self.score, 4),
            "reason": self.reason,
        }
