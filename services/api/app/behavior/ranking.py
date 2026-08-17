"""Deterministic story selection for the full Element and Pattern results."""

from __future__ import annotations

from collections.abc import Sequence

from app.behavior.models import ElementHighlight, ElementResult, PatternResult


def rank_element_highlights(
    elements: Sequence[ElementResult],
    *,
    limit: int = 3,
) -> tuple[ElementHighlight, ...]:
    """Choose the clearest non-redundant Element signals for the Free story."""

    candidates = [item for item in elements if item.score is not None and item.status != "unavailable"]
    selected: list[ElementResult] = []
    remaining = list(candidates)
    while remaining and len(selected) < max(0, limit):
        ranked = []
        selected_dimensions = {item.dimension_key for item in selected}
        for item in remaining:
            extremity = abs((item.score or 0.5) - 0.5) * 2.0
            evidence = item.confidence_score * item.coverage * item.quality
            novelty = 1.0 if item.dimension_key not in selected_dimensions else 0.72
            score = 0.55 * extremity + 0.30 * evidence + 0.15 * novelty
            ranked.append((score, extremity, evidence, item))
        _, _, _, winner = max(
            ranked,
            key=lambda value: (
                value[0], value[1], value[2], value[3].key,
            ),
        )
        remaining.remove(winner)
        selected.append(winner)
    return tuple(
        ElementHighlight(
            element_key=item.key,
            rank=index,
            display_reason=_element_reason(item),
        )
        for index, item in enumerate(selected, start=1)
    )


def rank_pattern_highlights(
    patterns: Sequence[PatternResult],
    *,
    limit: int = 3,
) -> tuple[PatternResult, ...]:
    """Greedily select strong Patterns while preserving family diversity."""

    candidates = [
        item
        for item in patterns
        if item.status == "qualified"
        and item.confidence_score >= 0.45
        and item.evidence_coverage >= 0.35
    ]
    selected: list[PatternResult] = []
    remaining = list(candidates)
    while remaining and len(selected) < max(0, limit):
        selected_families = {item.family for item in selected}
        ranked = []
        for item in remaining:
            novelty = 1.0 if item.family not in selected_families else 0.35
            tier_bonus = 0.05 if item.tier == "A" else 0.0
            score = item.strength * item.confidence_score * item.evidence_coverage
            score = score * (0.78 + 0.22 * novelty) + tier_bonus
            ranked.append((score, item))
        _, winner = max(
            ranked,
            key=lambda value: (
                value[0],
                value[1].tier == "A",
                value[1].strength,
                value[1].key,
            ),
        )
        remaining.remove(winner)
        selected.append(winner)
    return tuple(selected)


def select_top_element_keys(elements: Sequence[ElementResult], *, limit: int = 3) -> tuple[str, ...]:
    return tuple(item.element_key for item in rank_element_highlights(elements, limit=limit))


def select_top_pattern_keys(patterns: Sequence[PatternResult], *, limit: int = 3) -> tuple[str, ...]:
    return tuple(item.key for item in rank_pattern_highlights(patterns, limit=limit))


def _element_reason(item: ElementResult) -> str:
    if item.zone:
        return f"{item.zone} signal with {item.confidence} confidence"
    return f"{item.confidence} confidence signal"


# Short aliases keep the selector discoverable for callers that use the plan's
# vocabulary rather than the implementation-specific ``rank_*`` names.
select_top_elements = rank_element_highlights
select_top_patterns = rank_pattern_highlights


__all__ = [
    "rank_element_highlights",
    "rank_pattern_highlights",
    "select_top_element_keys",
    "select_top_pattern_keys",
    "select_top_elements",
    "select_top_patterns",
]
