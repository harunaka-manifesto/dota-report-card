from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from app.analysis.budget import BudgetState, CostPolicy, DataCostLedger
from app.features.models import MatchFeature
from app.features.summary_models import SummaryFeatureSet
from app.hypotheses.generator import generate_hypotheses
from app.hypotheses.models import Hypothesis
from app.ingestion.eligibility import assess_match
from app.ingestion.normalize import NormalizedMatch, normalize_match
from app.patterns.models import PatternCandidate
from app.selection.candidates import generate_candidate_matches
from app.selection.models import SelectionPlan
from app.selection.planner import plan_selection


class ParseTransport(Protocol):
    async def request_parse(self, match_id: int) -> dict[str, Any]: ...

    async def get_parse_request(self, job_id: str) -> dict[str, Any]: ...


@dataclass(frozen=True, slots=True)
class ParseRequestResult:
    allowed: bool
    match_id: int
    payload: dict[str, Any] | None
    reason: str


@dataclass(frozen=True, slots=True)
class DeepFinding:
    hypothesis_id: str
    status: str
    observation: str
    evidence: dict[str, Any]
    impact: str
    recommendation: str
    confidence: str
    positive_match_ids: tuple[int, ...]
    negative_match_ids: tuple[int, ...]
    control_match_ids: tuple[int, ...]
    data_families_used: tuple[str, ...]
    rejected_alternatives: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "status": self.status,
            "observation": self.observation,
            "evidence": dict(self.evidence),
            "impact": self.impact,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "positive_match_ids": list(self.positive_match_ids),
            "negative_match_ids": list(self.negative_match_ids),
            "control_match_ids": list(self.control_match_ids),
            "data_families_used": list(self.data_families_used),
            "rejected_alternatives": list(self.rejected_alternatives),
        }


class ParseRequestService:
    """Policy/budget boundary above the explicit parse transport."""

    def __init__(
        self,
        transport: ParseTransport,
        *,
        budget: BudgetState,
        ledger: DataCostLedger,
        policy: CostPolicy = CostPolicy(),
    ) -> None:
        self.transport = transport
        self.budget = budget
        self.ledger = ledger
        self.policy = policy

    async def request_parse(
        self,
        match_id: int,
        *,
        hypothesis_ids: tuple[str, ...] = (),
        required_families: tuple[str, ...] = (),
        hypothesis_priority: float = 1.0,
    ) -> ParseRequestResult:
        cost = self.policy.units_for("parse")
        decision = self.budget.can_spend(
            "parse",
            cost,
            hypothesis_priority=hypothesis_priority,
        )
        if not decision.allowed:
            return ParseRequestResult(False, match_id, None, decision.reason)
        payload = await self.transport.request_parse(match_id)
        self.budget.spend("parse", cost)
        self.ledger.record(
            "parse",
            policy=self.policy,
            match_id=match_id,
            units=cost,
            metadata={
                "hypothesis_ids": list(hypothesis_ids),
                "required_families": list(required_families),
            },
        )
        return ParseRequestResult(True, match_id, payload, "PARSE_REQUESTED")

    async def get_parse_status(self, job_id: str) -> dict[str, Any]:
        cost = self.policy.units_for("parse_status")
        decision = self.budget.can_spend("parse_status", cost)
        if not decision.allowed:
            return {"allowed": False, "reason": decision.reason}
        payload = await self.transport.get_parse_request(job_id)
        self.budget.spend("parse_status", cost)
        self.ledger.record(
            "parse_status",
            policy=self.policy,
            metadata={"job_id": job_id},
        )
        return payload


def plan_deep_scan(
    patterns: Iterable[PatternCandidate],
    feature_set: SummaryFeatureSet,
    *,
    max_primary_hypotheses: int = 3,
    max_deep_matches: int = 25,
    max_parse_requests: int = 0,
    max_data_cost: float = 50.0,
    min_marginal_information_gain: float = 0.05,
    available_families_by_match: Mapping[int, frozenset[str]] | None = None,
) -> tuple[list[Hypothesis], SelectionPlan]:
    hypotheses = generate_hypotheses(patterns)
    primary = _select_primary_hypotheses(hypotheses, max_primary_hypotheses)
    candidates = generate_candidate_matches(
        primary,
        feature_set,
        available_families_by_match=available_families_by_match,
        parse_cost_units=0.0,
    )
    plan = plan_selection(
        primary,
        candidates,
        max_deep_matches=max_deep_matches,
        max_parse_requests=max_parse_requests,
        max_data_cost=max_data_cost,
        min_marginal_information_gain=min_marginal_information_gain,
    )
    return primary, plan


def _select_primary_hypotheses(
    hypotheses: list[Hypothesis],
    maximum: int,
) -> list[Hypothesis]:
    limit = max(0, maximum)
    selected: list[Hypothesis] = []
    source_patterns: set[str] = set()
    for hypothesis in hypotheses:
        if len(selected) >= limit:
            break
        if hypothesis.source_pattern_id in source_patterns:
            continue
        selected.append(hypothesis)
        source_patterns.add(hypothesis.source_pattern_id)
    if len(selected) < limit:
        selected_ids = {item.hypothesis_id for item in selected}
        selected.extend(
            item
            for item in hypotheses
            if item.hypothesis_id not in selected_ids
        )
    return selected[:limit]


def evaluate_deep_hypotheses(
    hypotheses: Iterable[Hypothesis],
    plan: SelectionPlan,
    features: Iterable[MatchFeature],
) -> list[DeepFinding]:
    """Evaluate only the evidence roles actually selected and hydrated."""

    by_match_id = {feature.match_id: feature for feature in features}
    findings: list[DeepFinding] = []
    for hypothesis in hypotheses:
        groups: dict[str, list[MatchFeature]] = {"positive": [], "negative": [], "control": []}
        for selected in plan.selected:
            role = selected.candidate.evidence_roles.get(hypothesis.hypothesis_id)
            feature = by_match_id.get(selected.match_id)
            if role in groups and feature is not None:
                groups[role].append(feature)

        positive = groups["positive"]
        negative = groups["negative"]
        control = groups["control"]
        required = tuple(hypothesis.required_data_families)
        data_quality = _data_quality(positive + negative + control, required)
        minimums_met = (
            len(positive) >= hypothesis.min_positive
            and len(negative) >= hypothesis.min_negative
            and len(control) >= hypothesis.min_control
        )
        if not minimums_met or data_quality < 1.0:
            findings.append(
                DeepFinding(
                    hypothesis_id=hypothesis.hypothesis_id,
                    status="insufficient_evidence",
                    observation="The selected evidence did not meet the sample or family-coverage requirements.",
                    evidence={
                        "positive_matches": len(positive),
                        "negative_matches": len(negative),
                        "control_matches": len(control),
                        "required_families": list(required),
                        "data_quality": round(data_quality, 4),
                    },
                    impact="No causal recommendation was published.",
                    recommendation="Collect the missing evidence only if this hypothesis remains high priority.",
                    confidence="low",
                    positive_match_ids=tuple(item.match_id for item in positive),
                    negative_match_ids=tuple(item.match_id for item in negative),
                    control_match_ids=tuple(item.match_id for item in control),
                    data_families_used=required,
                    rejected_alternatives=("Sample adequacy or required evidence-family coverage was insufficient.",),
                )
            )
            continue

        positive_value, negative_value, control_value, unit = _hypothesis_values(
            hypothesis,
            positive,
            negative,
            control,
        )
        effect = _difference(positive_value, control_value)
        confidence = _finding_confidence(
            effect=effect,
            sample_size=min(len(positive), len(negative), len(control)),
            data_quality=data_quality,
        )
        findings.append(
            DeepFinding(
                hypothesis_id=hypothesis.hypothesis_id,
                status="resolved" if confidence != "low" else "moderate",
                observation=_observation_text(unit, positive_value, negative_value, control_value),
                evidence={
                    "positive_value": positive_value,
                    "negative_value": negative_value,
                    "control_value": control_value,
                    "unit": unit,
                    "effect": effect,
                    "sample_sizes": {
                        "positive": len(positive),
                        "negative": len(negative),
                        "control": len(control),
                    },
                    "data_quality": data_quality,
                },
                impact="Use this as a targeted behavior experiment, not a permanent identity label.",
                recommendation="Review the selected positive, negative, and control matches together before changing the behavior.",
                confidence=confidence,
                positive_match_ids=tuple(item.match_id for item in positive),
                negative_match_ids=tuple(item.match_id for item in negative),
                control_match_ids=tuple(item.match_id for item in control),
                data_families_used=required,
            )
        )
    return findings


def _hypothesis_values(
    hypothesis: Hypothesis,
    positive: list[MatchFeature],
    negative: list[MatchFeature],
    control: list[MatchFeature],
) -> tuple[float | None, float | None, float | None, str]:
    if hypothesis.explanation_type in {"death_risk_difference", "late_death_risk", "session_risk"}:
        return (
            _mean(item.deaths for item in positive),
            _mean(item.deaths for item in negative),
            _mean(item.deaths for item in control),
            "deaths per match",
        )
    if hypothesis.explanation_type == "timing_difference":
        return (
            _mean(item.gold_per_min for item in positive),
            _mean(item.gold_per_min for item in negative),
            _mean(item.gold_per_min for item in control),
            "GPM",
        )
    return (
        _rate(positive),
        _rate(negative),
        _rate(control),
        "win rate",
    )


def _data_quality(features: list[MatchFeature], required: tuple[str, ...]) -> float:
    if not features:
        return 0.0
    scores = [
        min(feature.coverage.by_family.get(family, 0.0) for family in required)
        if required
        else 1.0
        for feature in features
    ]
    return sum(scores) / len(scores)


def _finding_confidence(*, effect: float | None, sample_size: int, data_quality: float) -> str:
    if data_quality < 1.0 or sample_size < 3 or effect is None:
        return "low"
    if sample_size >= 8 and abs(effect) >= 0.15:
        return "high"
    return "moderate"


def _observation_text(
    unit: str,
    positive: float | None,
    negative: float | None,
    control: float | None,
) -> str:
    if positive is None or negative is None:
        return "The selected evidence did not provide a complete comparison."
    if control is None:
        return f"Positive evidence measured {positive:.2f} {unit}; negative evidence measured {negative:.2f} {unit}."
    return (
        f"Positive evidence measured {positive:.2f} {unit}, negative evidence {negative:.2f}, "
        f"and the control group {control:.2f}."
    )


def _mean(values: Iterable[float | int]) -> float | None:
    values = list(values)
    return sum(values) / len(values) if values else None


def _rate(features: list[MatchFeature]) -> float | None:
    return sum(item.won for item in features) / len(features) if features else None


def _difference(left: float | None, right: float | None) -> float | None:
    return left - right if left is not None and right is not None else None


async def acquire_selected_matches(
    plan: SelectionPlan,
    *,
    source: Any,
    repository: Any,
    account_id: int,
    ledger: DataCostLedger,
    policy: CostPolicy,
) -> list[NormalizedMatch]:
    """Hydrate only the globally selected matches, preferring local payloads."""

    normalized: list[NormalizedMatch] = []
    for selected in plan.selected:
        match_id = selected.match_id
        detail = _cached_detail(repository, match_id)
        if detail is None:
            if selected.candidate.already_available:
                ledger.record(
                    "detail",
                    policy=policy,
                    match_id=match_id,
                    existing=True,
                    units=0.0,
                    metadata={"reason": "summary families satisfy hypothesis"},
                )
                continue
            detail = await source.get_match(match_id)
            ledger.record(
                "detail",
                policy=policy,
                match_id=match_id,
                metadata={"reason": selected.reason},
            )
            repository.persist_raw_payload(f"/matches/{match_id}", str(match_id), detail)
        else:
            ledger.record(
                "detail",
                policy=policy,
                match_id=match_id,
                existing=True,
                units=0.0,
                metadata={"reason": "cached deep payload"},
            )
        eligibility = assess_match(detail, detail=detail, account_id=account_id)
        if not eligibility.eligible:
            continue
        try:
            item = normalize_match(detail, account_id=account_id, eligibility=eligibility)
        except (KeyError, ValueError):
            continue
        normalized.append(item)
        repository.save_normalized_match(match_id, _normalized_record(item))
    return normalized


def _cached_detail(repository: Any, match_id: int) -> dict[str, Any] | None:
    getter = getattr(repository, "get_cached_raw_payload", None)
    if getter is None:
        return None
    value = getter(f"/matches/{match_id}", str(match_id))
    return value if isinstance(value, dict) else None


def _normalized_record(match: NormalizedMatch) -> dict[str, Any]:
    target = match.target_participant
    return {
        "match_id": match.match_id,
        "account_id": match.account_id,
        "start_time": match.start_time,
        "duration_seconds": match.duration_seconds,
        "radiant": match.radiant,
        "won": match.won,
        "game_mode": match.game_mode,
        "lobby_type": match.lobby_type,
        "patch": match.patch,
        "rank_tier": match.rank_tier,
        "coverage": match.coverage.as_dict(),
        "participants": [
            {
                "account_id": participant.account_id,
                "player_slot": participant.player_slot,
                "hero_id": participant.hero_id,
                "lane_role": participant.lane_role,
                "won": participant.won,
                "kills": participant.kills,
                "deaths": participant.deaths,
                "assists": participant.assists,
                "last_hits": participant.last_hits,
                "gold_per_min": participant.gold_per_min,
                "tower_damage": participant.tower_damage,
                "role": participant.role,
                "role_probability": participant.role_probability,
                "death_events_available": participant.death_events_available,
            }
            for participant in match.participants
        ],
        "target_hero_id": target.hero_id,
        "objectives": [event.payload for event in match.objectives],
    }
