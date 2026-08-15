from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.features.summary_models import SummaryMatchFeature

EvidenceRole = str


@dataclass(frozen=True, slots=True)
class CandidateMatch:
    match_id: int
    feature: SummaryMatchFeature
    hypothesis_ids: tuple[str, ...]
    evidence_roles: dict[str, EvidenceRole]
    relevance: float
    contrast_value: float
    comparability: float
    extremeness: float
    parser_version_hint: int | None = None
    available_families: frozenset[str] = frozenset()
    already_available: bool = False
    estimated_detail_cost: float = 1.0
    estimated_parse_cost: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_sufficiently_available(self) -> bool:
        return self.already_available

    def as_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "hypothesis_ids": list(self.hypothesis_ids),
            "evidence_roles": dict(self.evidence_roles),
            "relevance": round(self.relevance, 4),
            "contrast_value": round(self.contrast_value, 4),
            "comparability": round(self.comparability, 4),
            "extremeness": round(self.extremeness, 4),
            "parser_version_hint": self.parser_version_hint,
            "available_families": sorted(self.available_families),
            "already_available": self.already_available,
            "estimated_detail_cost": self.estimated_detail_cost,
            "estimated_parse_cost": self.estimated_parse_cost,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class EvidenceNeed:
    hypothesis_id: str
    group: EvidenceRole
    target: int
    currently_satisfied: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.target - self.currently_satisfied)

    def as_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "group": self.group,
            "target": self.target,
            "currently_satisfied": self.currently_satisfied,
            "remaining": self.remaining,
        }


@dataclass(frozen=True, slots=True)
class SelectedMatch:
    candidate: CandidateMatch
    selection_order: int
    score: float
    marginal_gain: float
    newly_supported_needs: tuple[tuple[str, EvidenceRole], ...]
    reason: str
    parse_required: bool = False

    @property
    def match_id(self) -> int:
        return self.candidate.match_id

    def as_dict(self) -> dict[str, Any]:
        return {
            "match_id": self.match_id,
            "selection_order": self.selection_order,
            "score": round(self.score, 6),
            "marginal_gain": round(self.marginal_gain, 6),
            "newly_supported_needs": [
                {"hypothesis_id": hypothesis_id, "group": group}
                for hypothesis_id, group in self.newly_supported_needs
            ],
            "reason": self.reason,
            "parse_required": self.parse_required,
            "candidate": self.candidate.as_dict(),
        }


@dataclass(frozen=True, slots=True)
class SelectionPlan:
    candidates: tuple[CandidateMatch, ...]
    selected: tuple[SelectedMatch, ...]
    needs: tuple[EvidenceNeed, ...]
    stopping_reason: str

    @property
    def selected_match_ids(self) -> tuple[int, ...]:
        return tuple(item.match_id for item in self.selected)

    @property
    def already_sufficient_count(self) -> int:
        return sum(item.candidate.already_available for item in self.selected)

    def as_dict(self) -> dict[str, Any]:
        return {
            "candidate_matches": len(self.candidates),
            "selected_match_ids": list(self.selected_match_ids),
            "deep_matches_selected": len(self.selected),
            "already_sufficient": self.already_sufficient_count,
            "needs": [need.as_dict() for need in self.needs],
            "selected": [item.as_dict() for item in self.selected],
            "stopping_reason": self.stopping_reason,
        }


@dataclass(slots=True)
class SelectionState:
    needs: dict[tuple[str, EvidenceRole], EvidenceNeed]
    selected_ids: set[int] = field(default_factory=set)
    selected: list[SelectedMatch] = field(default_factory=list)
    estimated_cost: float = 0.0
    parse_requests: int = 0

    def remaining_for(self, hypothesis_id: str, group: EvidenceRole) -> int:
        need = self.needs.get((hypothesis_id, group))
        return need.remaining if need else 0

    def add(self, selected: SelectedMatch) -> None:
        self.selected_ids.add(selected.match_id)
        self.selected.append(selected)
        self.estimated_cost += selected.candidate.estimated_detail_cost
        if selected.parse_required:
            self.parse_requests += 1
        for hypothesis_id, group in selected.newly_supported_needs:
            key = (hypothesis_id, group)
            current = self.needs.get(key)
            if current is not None:
                self.needs[key] = EvidenceNeed(
                    current.hypothesis_id,
                    current.group,
                    current.target,
                    current.currently_satisfied + 1,
                )
