"""Evidence receipts shared by Elements, Patterns, and public reports."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

EvidenceValue = float | int | str | bool | None


@dataclass(frozen=True, slots=True)
class BehaviorEvidence:
    """A private, replayable receipt for one semantic result.

    ``source_match_ids`` intentionally remains an internal field.  Public
    projections call :meth:`as_public_dict`, which strips it at the boundary.
    """

    key: str
    value: EvidenceValue
    unit: str
    denominator: int
    coverage: float = 1.0
    confidence_score: float = 0.0
    comparison: str | None = None
    source_match_ids: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if self.denominator < 0:
            raise ValueError(f"Evidence denominator cannot be negative: {self.key}")
        if not 0.0 <= self.coverage <= 1.0:
            raise ValueError(f"Evidence coverage must be within [0, 1]: {self.key}")
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError(f"Evidence confidence must be within [0, 1]: {self.key}")

    def as_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "value": self.value,
            "unit": self.unit,
            "denominator": self.denominator,
            "coverage": round(self.coverage, 6),
            "confidence_score": round(self.confidence_score, 6),
            "comparison": self.comparison,
            "source_match_ids": list(self.source_match_ids),
        }

    def as_public_dict(self) -> dict[str, Any]:
        value = self.as_dict()
        value.pop("source_match_ids", None)
        return value


def public_receipt_value(evidence: BehaviorEvidence) -> str:
    """Format a short receipt value without leaking private identifiers."""

    value = evidence.value
    if value is None:
        return "Not available"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float):
        if evidence.unit in {"share", "rate", "fraction"}:
            return f"{value:.0%}"
        if evidence.unit in {"delta", "rate_delta", "proxy_delta"}:
            return f"{value:+.2f}"
        return f"{value:.2f}"
    return str(value)
