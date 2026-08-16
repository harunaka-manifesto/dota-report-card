"""Redundancy, contradiction, and story-slot selection."""

from __future__ import annotations

from collections.abc import Iterable

from app.findings.models import FindingCandidate, StorySelection
from app.findings.ranking import rank_findings

CONFLICT_VERSION = "free-finding-conflicts-1.0.0"

_CONFLICT_PAIRS = {
    frozenset({"broad_pool_narrow_safety_zone", "focused_specialist_identity"}),
    frozenset({"broad_pool_narrow_safety_zone", "role_vs_hero_identity"}),
}


def select_story_findings(candidates: Iterable[FindingCandidate]) -> StorySelection:
    published = [item for item in rank_findings(candidates) if item.publication_status == "published"]
    strong = [item for item in published if item.confidence_score >= 0.60]
    # A limited finding can be a useful fallback, but it should not displace a
    # stronger main-story candidate or become the default share headline.
    story_pool = strong or published[:1]
    selected: list[FindingCandidate] = []
    for candidate in story_pool:
        if _is_hero_centric(candidate) and sum(_is_hero_centric(item) for item in selected) >= 2:
            continue
        if _is_session_finding(candidate) and sum(_is_session_finding(item) for item in selected) >= 1:
            continue
        conflict = next((item for item in selected if _conflict_pair(candidate, item)), None)
        if conflict is not None:
            if not _wins_conflict(candidate, conflict):
                continue
            selected.remove(conflict)
        overlap = len(candidate.concept_tags & {tag for item in selected for tag in item.concept_tags})
        # A strong edge explanation can follow one hero finding, but repeated
        # use of the same concept should not fill the report with synonyms.
        adjusted = candidate.priority_score * (0.72 ** overlap)
        if adjusted < 0.12 and selected:
            continue
        selected.append(candidate)
        if len(selected) >= 6:
            break

    if selected and not any(item.kind == "strength" for item in selected):
        positive = next(
            (
                item
                for item in story_pool
                if item.kind == "strength"
                and not any(_conflicts(item, selected_item) for selected_item in selected)
            ),
            None,
        )
        if positive is not None and len(selected) < 6:
            selected.append(positive)

    thesis = next((item for item in selected if item.kind == "contradiction"), selected[0] if selected else None)
    strength = next((item for item in selected if item.kind == "strength"), None)
    contradiction = next((item for item in selected if item.kind == "contradiction" and item is not thesis), None)
    edge = next((item for item in selected if item.kind == "edge"), None)
    leak = next((item for item in selected if item.kind == "leak"), None)
    experiment = leak or contradiction or edge or thesis
    ordered = _ordered_keys(thesis, strength, contradiction, edge, leak, selected)
    experiment_key = (
        experiment.experiment.key
        if experiment is not None and experiment.experiment is not None
        else None
    )
    return StorySelection(
        thesis_key=thesis.key if thesis else None,
        strength_key=strength.key if strength else None,
        contradiction_key=contradiction.key if contradiction else None,
        edge_key=edge.key if edge else None,
        leak_key=leak.key if leak else None,
        experiment_key=experiment_key,
        ordered_finding_keys=tuple(ordered),
    )


def _conflicts(left: FindingCandidate, right: FindingCandidate) -> bool:
    return left.key == right.key or _conflict_pair(left, right)


def _conflict_pair(left: FindingCandidate, right: FindingCandidate) -> bool:
    return frozenset({left.key, right.key}) in _CONFLICT_PAIRS


def _wins_conflict(candidate: FindingCandidate, existing: FindingCandidate) -> bool:
    candidate_score = (candidate.confidence_score, candidate.priority_score)
    existing_score = (existing.confidence_score, existing.priority_score)
    if candidate_score != existing_score:
        return candidate_score > existing_score
    return candidate.key < existing.key


def _is_hero_centric(candidate: FindingCandidate) -> bool:
    return bool(candidate.concept_tags & {"hero_breadth", "hero_familiarity", "hero_toolkit"})


def _is_session_finding(candidate: FindingCandidate) -> bool:
    return bool(candidate.concept_tags & {"session_endurance", "duration"})


def _ordered_keys(
    thesis: FindingCandidate | None,
    strength: FindingCandidate | None,
    contradiction: FindingCandidate | None,
    edge: FindingCandidate | None,
    leak: FindingCandidate | None,
    selected: list[FindingCandidate],
) -> list[str]:
    ordered: list[str] = []
    for item in (thesis, strength, contradiction, edge, leak):
        if item is not None and item.key not in ordered:
            ordered.append(item.key)
    for item in selected:
        if item.key not in ordered:
            ordered.append(item.key)
    return ordered
