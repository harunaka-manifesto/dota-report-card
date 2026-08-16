"""Editorial-value ranking for deterministic Free findings."""

from __future__ import annotations

from collections.abc import Iterable

from app.findings.models import FindingCandidate

RANKING_VERSION = "free-finding-ranking-1.0.0"


def editorial_value(candidate: FindingCandidate) -> float:
    return (
        0.28 * candidate.surprise_score
        + 0.22 * candidate.specificity_score
        + 0.20 * candidate.consequence_score
        + 0.15 * candidate.actionability_score
        + 0.15 * candidate.shareability_score
    )


def rank_findings(candidates: Iterable[FindingCandidate]) -> tuple[FindingCandidate, ...]:
    """Rank with a stable key tie-breaker and no random editorial state."""

    return tuple(
        sorted(
            candidates,
            key=lambda item: (
                item.publication_status != "published",
                -item.priority_score,
                -item.confidence_score,
                item.key,
            ),
        )
    )
