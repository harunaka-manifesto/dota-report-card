from __future__ import annotations

from app.insights.models import EvidenceObject


def rank_evidence(evidence: list[EvidenceObject]) -> list[EvidenceObject]:
    published = [item for item in evidence if item.published]
    ordered = sorted(published, key=lambda item: (-item.ivs, item.insight_id))
    selected: list[EvidenceObject] = []
    seen_concepts: set[str] = set()
    for item in ordered:
        # Redundancy control is intentionally concept-level in v1. Different
        # families can still coexist when they explain different concepts.
        if item.concept_id in seen_concepts:
            continue
        seen_concepts.add(item.concept_id)
        selected.append(item)
    suppressed = [item for item in evidence if not item.published]
    return selected + sorted(suppressed, key=lambda item: item.insight_id)
