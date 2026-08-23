from __future__ import annotations

from collections.abc import Iterable

from app.hypotheses.models import Hypothesis
from app.selection.models import (
    CandidateMatch,
    EvidenceNeed,
    SelectedMatch,
    SelectionPlan,
    SelectionState,
)
from app.selection.scoring import marginal_information_gain


def plan_selection(
    hypotheses: Iterable[Hypothesis],
    candidates: Iterable[CandidateMatch],
    *,
    max_deep_matches: int = 25,
    max_parse_requests: int = 0,
    max_data_cost: float = 50.0,
    min_marginal_information_gain: float = 0.05,
    parse_min_marginal_information_gain: float = 0.10,
    prefer_cached: bool = False,
) -> SelectionPlan:
    hypothesis_map = {item.hypothesis_id: item for item in hypotheses}
    candidate_list = tuple(candidates)
    needs = {
        (hypothesis.hypothesis_id, group): EvidenceNeed(
            hypothesis_id=hypothesis.hypothesis_id,
            group=group,
            target=target,
        )
        for hypothesis in hypothesis_map.values()
        for group, target in hypothesis.evidence_targets.items()
    }
    state = SelectionState(needs=needs)
    stopping_reason = "no_candidates"

    while len(state.selected) < max(0, max_deep_matches):
        scored: list[tuple[float, CandidateMatch, tuple[tuple[str, str], ...]]] = []
        for candidate in candidate_list:
            if candidate.match_id in state.selected_ids:
                continue
            candidate_cost = candidate.estimated_detail_cost + candidate.estimated_parse_cost
            if state.estimated_cost + candidate_cost > max_data_cost:
                continue
            if candidate.estimated_parse_cost and state.parse_requests >= max_parse_requests:
                continue
            score, newly_supported = marginal_information_gain(candidate, hypothesis_map, state)
            threshold = (
                parse_min_marginal_information_gain
                if candidate.estimated_parse_cost and not candidate.already_available
                else min_marginal_information_gain
            )
            if score >= threshold and newly_supported:
                scored.append((score, candidate, newly_supported))
        if not scored:
            stopping_reason = _stopping_reason(
                state,
                candidate_list,
                max_deep_matches,
                max_data_cost,
                max_parse_requests,
            )
            break
        score, candidate, newly_supported = max(
            scored,
            key=lambda item: (
                1 if prefer_cached and item[1].already_available else 0,
                item[0],
                len(item[2]),
                candidate_reuse(item[1]),
                -item[1].match_id,
            ),
        )
        parse_required = bool(candidate.estimated_parse_cost and not candidate.already_available)
        selected = SelectedMatch(
            candidate=candidate,
            selection_order=len(state.selected) + 1,
            score=score,
            marginal_gain=score,
            newly_supported_needs=newly_supported,
            reason=_reason(candidate, newly_supported),
            parse_required=parse_required,
        )
        state.add(selected)
    else:
        stopping_reason = "max_deep_matches"

    if len(state.selected) >= max_deep_matches:
        stopping_reason = "max_deep_matches"
    abstention_reason = None
    if stopping_reason in {
        "no_candidates",
        "marginal_gain_exhausted",
        "max_data_cost",
        "max_parse_requests",
    }:
        abstention_reason = {
            "no_candidates": "No candidate evidence matched the diagnostic question.",
            "marginal_gain_exhausted": "Remaining candidates did not clear the information-gain threshold.",
            "max_data_cost": "The Deep data-cost ceiling was reached before sufficiency.",
            "max_parse_requests": "The Deep parse-request ceiling was reached before sufficiency.",
        }[stopping_reason]
    return SelectionPlan(
        candidates=candidate_list,
        selected=tuple(state.selected),
        needs=tuple(sorted(state.needs.values(), key=lambda item: (item.hypothesis_id, item.group))),
        stopping_reason=stopping_reason,
        abstention_reason=abstention_reason,
    )


def candidate_reuse(candidate: CandidateMatch) -> int:
    return len(candidate.hypothesis_ids)


def _reason(candidate: CandidateMatch, newly_supported: tuple[tuple[str, str], ...]) -> str:
    support = ", ".join(f"{hypothesis_id}:{group}" for hypothesis_id, group in newly_supported)
    availability = "already available" if candidate.already_available else "requires a detail read"
    return f"Supports {support}; {availability}."


def _stopping_reason(
    state: SelectionState,
    candidates: tuple[CandidateMatch, ...],
    max_deep_matches: int,
    max_data_cost: float,
    max_parse_requests: int,
) -> str:
    if len(state.selected) >= max_deep_matches:
        return "max_deep_matches"
    if state.estimated_cost >= max_data_cost:
        return "max_data_cost"
    if max_parse_requests >= 0 and state.parse_requests >= max_parse_requests and any(
        candidate.estimated_parse_cost and not candidate.already_available
        for candidate in candidates
    ):
        return "max_parse_requests"
    if not candidates:
        return "no_candidates"
    if all(candidate.match_id in state.selected_ids for candidate in candidates):
        return "evidence_sufficient"
    return "marginal_gain_exhausted"
