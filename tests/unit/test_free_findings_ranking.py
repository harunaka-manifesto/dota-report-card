from __future__ import annotations

from app.findings.models import FindingCandidate
from app.findings.ranking import rank_findings


def _candidate(
    key: str,
    *,
    priority: float,
    confidence: float,
    status: str = "published",
) -> FindingCandidate:
    return FindingCandidate(
        key=key,
        kind="strength",
        headline=key,
        body=key,
        interpretation=key,
        evidence=(),
        confidence_score=confidence,
        surprise_score=priority,
        specificity_score=priority,
        consequence_score=priority,
        actionability_score=priority,
        shareability_score=priority,
        priority_score=priority,
        experiment=None,
        limitations=(),
        publication_status=status,  # type: ignore[arg-type]
        suppression_reason=None if status == "published" else "test",
        definition_version="test-1.0.0",
    )


def test_ranking_prefers_publishable_value_then_stable_key() -> None:
    ranked = rank_findings(
        [
            _candidate("zeta", priority=0.8, confidence=0.9),
            _candidate("alpha", priority=0.8, confidence=0.9),
            _candidate("suppressed", priority=1.2, confidence=1.0, status="suppressed"),
        ]
    )

    assert [item.key for item in ranked] == ["alpha", "zeta", "suppressed"]

