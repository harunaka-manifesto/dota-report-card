from __future__ import annotations

from collections.abc import Iterable, Mapping

from app.features.summary_models import SummaryFeatureSet, SummaryMatchFeature
from app.hypotheses.models import Hypothesis
from app.selection.models import CandidateMatch


def generate_candidate_matches(
    hypotheses: Iterable[Hypothesis],
    feature_set: SummaryFeatureSet,
    *,
    available_families_by_match: Mapping[int, frozenset[str]] | None = None,
    detail_cost_units: float = 1.0,
    parse_cost_units: float = 0.0,
) -> list[CandidateMatch]:
    """Create a merged search space; selection happens globally later."""

    available_families_by_match = available_families_by_match or {}
    hypothesis_map = {item.hypothesis_id: item for item in hypotheses}
    hypotheses = tuple(hypothesis_map.values())
    merged: dict[int, dict[str, object]] = {}
    for hypothesis in hypotheses:
        definitions = (
            ("positive", hypothesis.positive_definition),
            ("negative", hypothesis.negative_definition),
            ("control", hypothesis.control_definition),
        )
        for role, predicate in definitions:
            for feature in feature_set.matches:
                if not predicate.matches(feature):
                    continue
                entry = merged.setdefault(
                    feature.match_id,
                    {
                        "feature": feature,
                        "hypothesis_ids": set(),
                        "evidence_roles": {},
                    },
                )
                hypothesis_ids = entry["hypothesis_ids"]
                evidence_roles = entry["evidence_roles"]
                assert isinstance(hypothesis_ids, set)
                assert isinstance(evidence_roles, dict)
                hypothesis_ids.add(hypothesis.hypothesis_id)
                evidence_roles[hypothesis.hypothesis_id] = role

    candidates: list[CandidateMatch] = []
    for match_id, entry in merged.items():
        feature_value = entry["feature"]
        hypothesis_ids = entry["hypothesis_ids"]
        evidence_roles = entry["evidence_roles"]
        assert isinstance(feature_value, SummaryMatchFeature)
        assert isinstance(hypothesis_ids, set)
        assert isinstance(evidence_roles, dict)
        feature = feature_value
        available = frozenset(
            set(feature.summary_families)
            | set(available_families_by_match.get(match_id, frozenset()))
        )
        required = {
            family
            for hypothesis_id in hypothesis_ids
            for family in hypothesis_map[hypothesis_id].required_data_families
        }
        already_sufficient = bool(required) and required.issubset(available)
        candidates.append(
            CandidateMatch(
                match_id=match_id,
                feature=feature,
                hypothesis_ids=tuple(sorted(hypothesis_ids)),
                evidence_roles=dict(sorted(evidence_roles.items())),
                relevance=_relevance(feature),
                contrast_value=_contrast(feature),
                comparability=_comparability(feature),
                extremeness=_extremeness(feature),
                parser_version_hint=feature.parser_version_hint,
                available_families=available,
                already_available=already_sufficient,
                estimated_detail_cost=0.0 if already_sufficient else detail_cost_units,
                estimated_parse_cost=0.0 if already_sufficient else parse_cost_units,
                metadata={"missing_data_families": sorted(required - available)},
            )
        )
    return sorted(candidates, key=lambda item: (-item.relevance, item.match_id))


def _relevance(feature: SummaryMatchFeature) -> float:
    value = 0.5
    if feature.hero_id is not None:
        value += 0.1
    if feature.session_index is not None:
        value += 0.1
    if feature.duration_bucket in {"long", "short"}:
        value += 0.1
    return min(1.0, value)


def _contrast(feature: SummaryMatchFeature) -> float:
    value = 0.5
    if feature.won:
        value += 0.1
    if feature.deaths is not None and feature.deaths >= 6:
        value += 0.25
    return min(1.0, value)


def _comparability(feature: SummaryMatchFeature) -> float:
    available = sum(
        item is not None
        for item in (feature.lane_role, feature.average_rank, feature.party_size, feature.start_time)
    )
    return min(1.0, 0.4 + available * 0.15)


def _extremeness(feature: SummaryMatchFeature) -> float:
    if feature.deaths is None:
        return 0.4
    return min(1.0, 0.4 + feature.deaths / 12)
