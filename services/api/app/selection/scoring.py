from __future__ import annotations

from collections.abc import Mapping

from app.hypotheses.models import Hypothesis
from app.selection.models import CandidateMatch, SelectionState


def candidate_base_value(
    candidate: CandidateMatch,
    hypotheses: Mapping[str, Hypothesis],
) -> float:
    reuse = sum(hypotheses[item].priority for item in candidate.hypothesis_ids if item in hypotheses)
    return (
        0.22 * candidate.relevance
        + 0.20 * candidate.contrast_value
        + 0.18 * candidate.comparability
        + 0.14 * candidate.extremeness
        + 0.16 * min(1.0, reuse)
        + 0.10 * (1.0 if candidate.already_available else 0.0)
    )


def marginal_information_gain(
    candidate: CandidateMatch,
    hypotheses: Mapping[str, Hypothesis],
    state: SelectionState,
) -> tuple[float, tuple[tuple[str, str], ...]]:
    newly_supported: list[tuple[str, str]] = []
    information = 0.0
    for hypothesis_id, role in candidate.evidence_roles.items():
        remaining = state.remaining_for(hypothesis_id, role)
        if remaining <= 0:
            continue
        hypothesis = hypotheses[hypothesis_id]
        newly_supported.append((hypothesis_id, role))
        information += hypothesis.priority * (1.0 / remaining)
    if not newly_supported:
        return 0.0, ()

    base = candidate_base_value(candidate, hypotheses)
    redundancy_penalty = min(0.7, len(state.selected) * 0.015)
    cost_penalty = 0.04 * (
        candidate.estimated_detail_cost + candidate.estimated_parse_cost
    )
    return max(0.0, base + information - redundancy_penalty - cost_penalty), tuple(
        newly_supported
    )
