from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.dna.confidence import ConfidenceLabel
from app.dna.features.models import FeatureEvidence

DimensionKey = Literal[
    "breadth",
    "role",
    "adaptability",
    "activity",
    "orientation",
    "resilience",
    "endurance",
    "rhythm",
]


@dataclass(frozen=True, slots=True)
class DimensionResult:
    key: DimensionKey
    status: Literal["available", "limited", "unavailable"]
    score: float | None
    centered_score: float | None
    label: str | None
    confidence: ConfidenceLabel
    confidence_score: float
    sample_size: int
    effective_sample_size: float
    coverage: float
    evidence: tuple[FeatureEvidence, ...] = ()
    confounders: tuple[str, ...] = ()
    missing_reasons: tuple[str, ...] = ()
    copy: dict[str, Any] | None = None
    methodology_version: str = "dna-scoring-1.0.0"
    source_match_ids: tuple[int, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "status": self.status,
            "score": round(self.score, 6) if self.score is not None else None,
            "centered_score": round(self.centered_score, 6)
            if self.centered_score is not None
            else None,
            "label": self.label,
            "confidence": self.confidence,
            "confidence_score": round(self.confidence_score, 6),
            "sample_size": self.sample_size,
            "effective_sample_size": round(self.effective_sample_size, 6),
            "coverage": round(self.coverage, 6),
            "evidence": [item.as_dict() for item in self.evidence],
            "confounders": list(self.confounders),
            "missing_reasons": list(self.missing_reasons),
            "copy": self.copy,
            "methodology_version": self.methodology_version,
            "source_match_ids": list(self.source_match_ids),
        }
