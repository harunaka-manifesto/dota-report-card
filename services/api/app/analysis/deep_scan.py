from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from app.analysis.budget import BudgetState, CostPolicy, DataCostLedger
from app.features.models import MatchFeature
from app.features.summary_models import SummaryFeatureSet
from app.hypotheses.generator import generate_diagnostic_hypotheses, generate_hypotheses
from app.hypotheses.models import DiagnosticQuestion, Hypothesis
from app.ingestion.coverage import coverage_for_match
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
    recommendation: str | None
    confidence: str
    positive_match_ids: tuple[int, ...]
    negative_match_ids: tuple[int, ...]
    control_match_ids: tuple[int, ...]
    data_families_used: tuple[str, ...]
    rejected_alternatives: tuple[str, ...] = ()
    stopping_reason: str | None = None
    abstention_reason: str | None = None
    verification_rule: str | None = None

    @property
    def abstained(self) -> bool:
        return self.abstention_reason is not None

    def as_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "status": self.status,
            "observation": self.observation,
            "evidence": dict(self.evidence),
            "impact": self.impact,
            "recommendation": self.recommendation,
            "verification_rule": self.verification_rule,
            "confidence": self.confidence,
            "positive_match_ids": list(self.positive_match_ids),
            "negative_match_ids": list(self.negative_match_ids),
            "control_match_ids": list(self.control_match_ids),
            "data_families_used": list(self.data_families_used),
            "rejected_alternatives": list(self.rejected_alternatives),
            "stopping_reason": self.stopping_reason,
            "abstention_reason": self.abstention_reason,
            "abstained": self.abstained,
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
    patterns: Iterable[PatternCandidate] | DiagnosticQuestion | Mapping[str, Any] | str,
    feature_set: SummaryFeatureSet,
    *,
    max_primary_hypotheses: int = 3,
    max_deep_matches: int = 25,
    max_parse_requests: int = 25,
    max_data_cost: float = 160.0,
    min_marginal_information_gain: float = 0.05,
    parse_min_marginal_information_gain: float = 0.10,
    available_families_by_match: Mapping[int, frozenset[str]] | None = None,
    diagnostic_question: DiagnosticQuestion | Mapping[str, Any] | str | None = None,
) -> tuple[list[Hypothesis], SelectionPlan]:
    if diagnostic_question is not None:
        return plan_diagnostic_deep_scan(
            diagnostic_question,
            feature_set,
            available_families_by_match=available_families_by_match,
            max_deep_matches=max_deep_matches,
            max_parse_requests=max_parse_requests,
            max_data_cost=max_data_cost,
            min_marginal_information_gain=min_marginal_information_gain,
            parse_min_marginal_information_gain=parse_min_marginal_information_gain,
        )
    if isinstance(patterns, (DiagnosticQuestion, str, Mapping)):
        return plan_diagnostic_deep_scan(
            patterns,
            feature_set,
            available_families_by_match=available_families_by_match,
            max_deep_matches=max_deep_matches,
            max_parse_requests=max_parse_requests,
            max_data_cost=max_data_cost,
            min_marginal_information_gain=min_marginal_information_gain,
            parse_min_marginal_information_gain=parse_min_marginal_information_gain,
        )
    hypotheses = generate_hypotheses(patterns)
    primary = _select_primary_hypotheses(hypotheses, max_primary_hypotheses)
    candidates = generate_candidate_matches(
        primary,
        feature_set,
        available_families_by_match=available_families_by_match,
        parse_cost_units=0.0,
        summary_satisfies_requirements=False,
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


def plan_diagnostic_deep_scan(
    question: DiagnosticQuestion | Mapping[str, Any] | str,
    feature_set: SummaryFeatureSet,
    *,
    available_families_by_match: Mapping[int, frozenset[str]] | None = None,
    max_deep_matches: int = 25,
    max_parse_requests: int = 25,
    max_data_cost: float = 160.0,
    min_marginal_information_gain: float = 0.05,
    parse_min_marginal_information_gain: float = 0.10,
) -> tuple[list[Hypothesis], SelectionPlan]:
    """Plan Deep v2 from one report-offered diagnostic question.

    The question produces one user-primary hypothesis and at most one
    secondary.  ``generate_candidate_matches`` marks summary/cached evidence
    as free, while the selector prefers those candidates before spending on
    detail/parse reads.  Detail and parse ceilings remain separate and the
    cost ceiling accounts for both operations.
    """

    hypotheses = generate_diagnostic_hypotheses(question)
    candidates = generate_candidate_matches(
        hypotheses,
        feature_set,
        available_families_by_match=available_families_by_match,
        detail_cost_units=1.0,
        # Stage A selects summary/detail candidates only. Parse marginal gain
        # is evaluated after detail hydration, so parse cost is not charged
        # while the detail plan is being built.
        parse_cost_units=0.0,
    )
    plan = plan_selection(
        hypotheses,
        candidates,
        max_deep_matches=min(25, max(0, max_deep_matches)),
        max_parse_requests=min(25, max(0, max_parse_requests)),
        max_data_cost=min(160.0, max(0.0, max_data_cost)),
        min_marginal_information_gain=max(0.05, min_marginal_information_gain),
        parse_min_marginal_information_gain=max(0.10, parse_min_marginal_information_gain),
        prefer_cached=True,
    )
    return hypotheses, plan


# Short alias used by callers that refer to the feature as Deep Diagnostics.
plan_deep_diagnostics = plan_diagnostic_deep_scan


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
                    recommendation=None,
                    confidence="low",
                    positive_match_ids=tuple(item.match_id for item in positive),
                    negative_match_ids=tuple(item.match_id for item in negative),
                    control_match_ids=tuple(item.match_id for item in control),
                    data_families_used=required,
                    rejected_alternatives=("Sample adequacy or required evidence-family coverage was insufficient.",),
                    stopping_reason="evidence_sufficiency_not_met",
                    abstention_reason=(
                        "Positive, negative, or control evidence did not meet the declared minimums."
                        if not minimums_met
                        else "A required evidence family was unavailable or incomplete."
                    ),
                    verification_rule=None,
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
                recommendation=_deep_recommendation(hypothesis.explanation_type, effect),
                confidence=confidence,
                positive_match_ids=tuple(item.match_id for item in positive),
                negative_match_ids=tuple(item.match_id for item in negative),
                control_match_ids=tuple(item.match_id for item in control),
                data_families_used=required,
                stopping_reason="resolved" if confidence != "low" else "practical_effect_or_quality_not_met",
                verification_rule="Recheck the same positive, negative, and control definitions on the next eligible evidence batch.",
            )
        )
    return findings


def _deep_recommendation(explanation_type: str, effect: float | None) -> str:
    """Select finite, template-owned Deep guidance from the hypothesis type."""

    del effect
    return {
        "functional_job_reuse": "Compare one repeated job across two different heroes in the selected evidence.",
        "core_to_stretch_transfer": "Compare one familiar hero context with one stretch hero context while keeping the declared lane context visible.",
        "session_position_reuse": "Compare the same evidence definition in early and later session positions.",
        "same_session_post_loss_transition": "Record the next eligible match after a loss and compare it with the declared comparable context.",
        "participation_exposure_quadrant": "Review participation and exposure together across the selected evidence groups.",
        "session_position_shift": "Compare early and later matches from completed sessions using the declared evidence groups.",
    }.get(explanation_type, "Review the declared evidence groups using the stored comparison context.")


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
    parse_transport: Any | None = None,
    repository: Any,
    account_id: int,
    ledger: DataCostLedger,
    policy: CostPolicy,
    parse_min_marginal_information_gain: float = 0.10,
) -> list[NormalizedMatch]:
    """Hydrate only the globally selected matches, preferring local payloads."""

    normalized: list[NormalizedMatch] = []
    parse_transport = parse_transport or (source if callable(getattr(source, "request_parse", None)) else None)
    parse_service = None
    if parse_transport is not None:
        possible_parse_requests = sum(
            bool(selected.parse_required or selected.candidate.metadata.get("parse_required_families"))
            for selected in plan.selected
        )
        parse_budget = BudgetState(
            max_parse_requests=min(25, max(0, possible_parse_requests)),
            max_data_cost_per_report=160.0,
            estimated_cost_units=ledger.estimated_cost_units,
        )
        parse_service = ParseRequestService(parse_transport, budget=parse_budget, ledger=ledger, policy=policy)
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
        target_player: dict[str, Any] | None = next(
            (
                player
                for player in detail.get("players", [])
                if isinstance(player, dict) and player.get("account_id") == account_id
            ),
            None,
        )
        detail_families = coverage_for_match(detail, target_player).by_family
        parse_families = {
            str(item)
            for item in selected.candidate.metadata.get("parse_required_families", ())
            if detail_families.get(str(item), 0.0) < 1.0
        }
        if selected.parse_required:
            parse_families.update(
                str(item)
                for item in selected.candidate.metadata.get("parse_required_families", ())
                if detail_families.get(str(item), 0.0) < 1.0
            )
            if not parse_families:
                # A manually constructed plan may mark a parse as required
                # without naming families; retain the explicit request.
                parse_families.add("events")
        if parse_families:
            raw_parse_gain = selected.candidate.metadata.get("parse_marginal_gain")
            try:
                parse_gain = float(raw_parse_gain) if raw_parse_gain is not None else float(selected.marginal_gain)
            except (TypeError, ValueError):
                parse_gain = float(selected.marginal_gain)
            # Stage A's score is the information value before the parse read.
            # Apply the same relative cost penalty used by candidate scoring so
            # Stage B cannot spend on a marginal gain below the v6 0.10 floor.
            if raw_parse_gain is None:
                parse_gain -= 0.04 * policy.units_for("parse")
            minimum_parse_gain = max(0.10, float(parse_min_marginal_information_gain))
            if parse_gain < minimum_parse_gain:
                ledger.events.append({
                    "operation": "parse_skipped",
                    "match_id": match_id,
                    "estimated_units": 0.0,
                    "metadata": {
                        "reason": "parse marginal information gain below threshold",
                        "parse_marginal_gain": round(parse_gain, 6),
                        "minimum_parse_marginal_information_gain": minimum_parse_gain,
                        "required_families": sorted(parse_families),
                    },
                })
                parse_families = set()
        if parse_families:
            if parse_service is None:
                ledger.events.append({
                    "operation": "parse_unavailable",
                    "match_id": match_id,
                    "estimated_units": 0.0,
                    "metadata": {"reason": "selected parse marker had no parse transport"},
                })
            else:
                parse_result = await parse_service.request_parse(
                    match_id,
                    hypothesis_ids=selected.candidate.hypothesis_ids,
                    required_families=tuple(sorted(parse_families)),
                    hypothesis_priority=max(0.01, selected.score),
                )
                if parse_result.allowed and isinstance(parse_result.payload, dict):
                    parse_payload = parse_result.payload
                    job_id = parse_payload.get("job") or parse_payload.get("job_id")
                    if job_id and callable(getattr(parse_transport, "get_parse_request", None)):
                        status_payload = await parse_service.get_parse_status(str(job_id))
                        if isinstance(status_payload, dict):
                            parse_payload = {**parse_payload, **status_payload}
                    nested = parse_payload.get("match")
                    if isinstance(nested, Mapping):
                        detail = {**detail, **dict(nested)}
                    else:
                        detail = {**detail, **parse_payload}
                    repository.persist_raw_payload(f"/matches/{match_id}/parse", str(match_id), parse_payload)
                else:
                    ledger.events.append({
                        "operation": "parse_abstained",
                        "match_id": match_id,
                        "estimated_units": 0.0,
                        "metadata": {"reason": parse_result.reason},
                    })
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
