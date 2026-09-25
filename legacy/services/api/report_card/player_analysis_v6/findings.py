"""Five non-redundant v6 finding families and conservative publication gates."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
from typing import Any, Literal

from .constants import FDR_Q, FINDING_FAMILY_KEYS, FORBIDDEN_FREE_TERMS, NORMAL_REPORT_MATCHES
from .copy import family_copy
from .family_statistics import benjamini_hochberg_five
from .models import ElementResultV6, Estimate, FamilyEvidence, FindingFamilyResult
from .recommendations import recommendation_for_family
from .statistics import benjamini_hochberg

FAMILY_DEFINITIONS: Mapping[str, Mapping[str, Any]] = {
    "pool_shape": {
        "label": "Pool Shape",
        "required": ("breadth", "toolkit"),
        "min_signals": 2,
        "description": "Hero-pool width and functional job coverage move together or apart.",
        "question": "What does your hero pool ask you to repeat or stretch?",
    },
    "transfer": {
        "label": "Transfer",
        "required": ("transfer", "breadth_or_toolkit"),
        "min_signals": 2,
        "description": "Summary-visible expression carries from familiar choices into stretch choices.",
        "question": "What changes when you leave your familiar heroes?",
    },
    "post_loss_response": {
        "label": "Post-Loss Response",
        "required": ("response", "familiarity_or_tempo"),
        "min_signals": 2,
        "min_transitions": 30,
        "min_sessions": 12,
        "min_coverage": 0.50,
        "description": "The next-choice pattern after a loss differs from the established pool context.",
        "question": "How does your next game differ after a loss?",
    },
    "combat_expression": {
        "label": "Combat Expression",
        "required": ("involvement", "death_exposure"),
        "min_signals": 2,
        "description": "Summary-visible participation and exposure remain separate combat-expression signals.",
        "question": "How do participation and exposure travel together?",
    },
    "session_drift": {
        "label": "Session Drift",
        "required": (),
        "min_signals": 2,
        "min_sessions": 12,
        "description": "Expression shifts across positions in completed sessions in the available summary evidence.",
        "question": "What changes as a play session gets longer?",
    },
}


def forbidden_inference_violations(text: str | None) -> tuple[str, ...]:
    if not text:
        return ()
    lowered = text.casefold()
    return tuple(term for term in FORBIDDEN_FREE_TERMS if term in lowered)


def _element_map(elements: Sequence[ElementResultV6] | Mapping[str, Any] | None) -> dict[str, Any]:
    if elements is None:
        return {}
    if isinstance(elements, Mapping):
        return dict(elements)
    return {item.key: item for item in elements}


def _evidence(key: str, value: Any, *, default_sample: int = 0, default_sessions: int = 0, default_coverage: float = 0.0) -> FamilyEvidence | None:
    if value is None:
        return None
    if isinstance(value, FamilyEvidence):
        return value
    if isinstance(value, ElementResultV6):
        estimate = value.estimate
        if estimate.value is None or estimate.status == "unavailable":
            return None
        return FamilyEvidence(
            key,
            estimate.value,
            estimate.unit,
            estimate.interval,
            estimate.direction,
            estimate.sample_size,
            estimate.independent_sessions,
            estimate.coverage,
            estimate.evidence_refs or (f"element:{key}",),
            estimate.limitations,
            estimate.stability,
        )
    if isinstance(value, Mapping):
        numeric = value.get("value", value.get("estimate", value.get("delta")))
        try:
            numeric = float(numeric) if numeric is not None else None
        except (TypeError, ValueError):
            numeric = None
        raw_signal = str(value.get("direction", value.get("signal", "unknown")))
        if raw_signal == "positive":
            signal: Literal["positive", "negative", "neutral", "mixed", "unknown"] = "positive"
        elif raw_signal == "negative":
            signal = "negative"
        elif raw_signal == "neutral":
            signal = "neutral"
        elif raw_signal == "mixed":
            signal = "mixed"
        else:
            signal = "unknown"
        return FamilyEvidence(
            key,
            numeric,
            str(value.get("unit", "")),
            tuple(value["interval"]) if value.get("interval") else None,
            signal,
            int(value.get("sample_size", default_sample) or 0),
            int(value.get("independent_sessions", default_sessions) or 0),
            float(value.get("coverage", default_coverage) or 0.0),
            tuple(value.get("evidence_refs", (f"family:{key}",))),
            tuple(value.get("limitations", ())),
            float(value.get("stability", 0.0) or 0.0),
        )
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return FamilyEvidence(key, numeric, sample_size=default_sample, independent_sessions=default_sessions, coverage=default_coverage, evidence_refs=(f"family:{key}",), stability=0.0)


def _signal_keys(evidence: Sequence[FamilyEvidence]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.key for item in evidence if item.value is not None))


def _infer_direction(evidence: Sequence[FamilyEvidence]) -> str:
    directions = [item.signal for item in evidence if item.signal in {"positive", "negative", "mixed"}]
    if any(item == "mixed" for item in directions):
        return "mixed"
    positive = sum(item == "positive" for item in directions)
    negative = sum(item == "negative" for item in directions)
    if positive and negative:
        return "mixed"
    if positive >= 2:
        return "positive"
    if negative >= 2:
        return "negative"
    return "unknown"


def _confidence(evidence: Sequence[FamilyEvidence], sample_size: int, sessions: int, comparable_coverage: float) -> tuple[str, float]:
    if not evidence:
        return "unavailable", 0.0
    # Confidence is derived from the bootstrap zone/direction stability that
    # each estimator records.  Interval width is not a cross-metric proxy.
    stability_values = [item.stability for item in evidence if item.value is not None]
    # A family is only as stable as its weakest required signal. Averaging can
    # let one highly stable metric conceal another that misses its gate.
    score = min(stability_values) if stability_values else 0.0
    if sample_size >= NORMAL_REPORT_MATCHES and sessions >= 8 and comparable_coverage >= 0.5 and score >= 0.90:
        return "high", score
    if sample_size >= 30 and sessions >= 8 and comparable_coverage >= 0.5 and score >= 0.75:
        return "moderate", score
    return "descriptive", score


def qualify_family(
    family: str,
    evidence: Mapping[str, Any] | Sequence[FamilyEvidence] = (),
    sample_size: int = 0,
    independent_sessions: int = 0,
    transitions: int = 0,
    comparable_context_coverage: float = 1.0,
    p_value: float | None = None,
    q_value: float | None = None,
    direction: str = "unknown",
    claim: str | None = None,
    interpretation: str | None = None,
    recommendation: Mapping[str, Any] | str | None = None,
    blocking_confounders: Sequence[str] = (),
) -> FindingFamilyResult:
    """Build one family result, preserving suppressed/unavailable states."""

    if family not in FAMILY_DEFINITIONS:
        raise ValueError(f"Unknown v6 family: {family}")
    definition = FAMILY_DEFINITIONS[family]
    if isinstance(evidence, Mapping):
        source = dict(evidence)
        if family == "transfer" and "breadth_or_toolkit" not in source:
            source["breadth_or_toolkit"] = source.get("breadth", source.get("toolkit"))
        if family == "post_loss_response":
            source.setdefault("response", source.get("post_loss_response"))
            source.setdefault("familiarity_or_tempo", source.get("familiarity", source.get("tempo")))
        items = tuple(item for key, value in source.items() if (item := _evidence(key, value, default_sample=sample_size, default_sessions=independent_sessions, default_coverage=comparable_context_coverage)) is not None)
    else:
        items = tuple(evidence)
    if sample_size <= 0:
        sample_size = max((item.sample_size for item in items), default=0)
    if independent_sessions <= 0:
        independent_sessions = max((item.independent_sessions for item in items), default=0)
    if comparable_context_coverage == 1.0 and items:
        comparable_context_coverage = min(item.coverage for item in items)
    signals = _signal_keys(items)
    missing = tuple(str(item) for item in definition.get("required", ()) if item not in signals and not (item == "breadth_or_toolkit" and ({"breadth", "toolkit"} & set(signals))))
    if not items:
        return FindingFamilyResult(
            family,
            "unavailable",
            direction="unknown",
            confidence="unavailable",
            confidence_score=0.0,
            estimate=Estimate(
                None,
                "family signal",
                zone="unknown",
                direction="unknown",
                sample_size=sample_size,
                independent_sessions=independent_sessions,
                coverage=comparable_context_coverage,
                confidence="unavailable",
                status="unavailable",
                limitations=("no usable independent evidence",),
            ),
            qualification_reason="no usable independent evidence",
        )
    reasons: list[str] = []
    if missing:
        reasons.append("missing independent signals: " + ", ".join(missing))
    if len(signals) < int(definition.get("min_signals", 2)):
        reasons.append("fewer than two meaningfully independent signals")
    if sample_size < 30:
        reasons.append("fewer than 30 eligible matches")
    limited_history = 30 <= sample_size < NORMAL_REPORT_MATCHES
    if limited_history:
        reasons.append("limited history; this sample is descriptive")
    if independent_sessions < int(definition.get("min_sessions", 1)):
        reasons.append(f"fewer than {definition['min_sessions']} independent sessions")
    if transitions < int(definition.get("min_transitions", 0)):
        reasons.append(f"fewer than {definition['min_transitions']} transitions")
    if comparable_context_coverage < float(definition.get("min_coverage", 0.0)):
        reasons.append(f"comparable-context coverage below {definition['min_coverage']:.0%}")
    min_sessions = int(definition.get("min_sessions", 1))
    for item in items:
        if item.sample_size and item.sample_size < 30:
            reasons.append(f"{item.key}: fewer than 30 usable matches")
        if item.independent_sessions and item.independent_sessions < min_sessions:
            reasons.append(f"{item.key}: fewer than {min_sessions} independent sessions")
    confidence, confidence_score = _confidence(items, sample_size, independent_sessions, comparable_context_coverage)
    hard_reasons = [reason for reason in reasons if reason != "limited history; this sample is descriptive"]
    if not items:
        status = "unavailable"
    elif hard_reasons:
        status = "suppressed"
    else:
        status = "qualified"
    if q_value is not None and q_value > FDR_Q:
        reasons.append(f"BH FDR q-value exceeds {FDR_Q:.2f}")
        status = "suppressed"
    evidence_text = "; ".join(f"{item.key}={item.value:g}" for item in items if item.value is not None)
    copy_payload = family_copy(
        family,
        direction=direction if direction in {"positive", "negative", "mixed"} else "mixed",
        evidence_labels=signals,
        evidence_refs=tuple(ref for item in items for ref in item.evidence_refs),
        recommendation=recommendation if isinstance(recommendation, Mapping) else None,
    )
    claim = claim or copy_payload.get("claim")
    evidence_text = evidence_text or str(copy_payload.get("evidence") or "")
    interpretation = interpretation or str(copy_payload.get("interpretation") or "")
    if limited_history:
        claim = f"In this sample, {claim[0].lower() + claim[1:] if claim else 'the available evidence remains descriptive.'}"
        interpretation = "In this sample, the observed association is descriptive and does not establish cause."
        recommendation = None
    def _copy_texts(value: Any) -> tuple[str, ...]:
        if isinstance(value, str):
            return (value,)
        if isinstance(value, Mapping):
            return tuple(text for child in value.values() for text in _copy_texts(child))
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            return tuple(text for child in value for text in _copy_texts(child))
        return ()

    text_values = (claim, interpretation, *_copy_texts(recommendation))
    violations = tuple(dict.fromkeys(term for text in text_values for term in forbidden_inference_violations(text)))
    if violations:
        reasons.append("forbidden summary inference: " + ", ".join(violations))
        status = "suppressed"
    if direction == "unknown":
        direction = _infer_direction(items)
    evidence_text = evidence_text or "; ".join(f"{item.key}={item.value:g}" for item in items if item.value is not None)
    numeric_values = [item.value for item in items if item.value is not None]
    estimate_value = sum(numeric_values) / len(numeric_values) if numeric_values else None
    intervals = [item.interval for item in items if item.interval is not None]
    estimate_interval = (
        (min(item[0] for item in intervals), max(item[1] for item in intervals))
        if intervals
        else None
    )
    estimate = Estimate(
        estimate_value,
        "family signal",
        interval=estimate_interval,
        zone=direction,
        direction=direction if direction in {"positive", "negative", "neutral", "mixed", "unknown"} else "unknown",  # type: ignore[arg-type]
        stability=confidence_score,
        sample_size=max(sample_size, max((item.sample_size for item in items), default=0)),
        independent_sessions=max(independent_sessions, max((item.independent_sessions for item in items), default=0)),
        coverage=min(comparable_context_coverage, min((item.coverage for item in items), default=comparable_context_coverage)),
        confidence=confidence,  # type: ignore[arg-type]
        status="available" if status == "qualified" else "limited",
        evidence_refs=tuple(dict.fromkeys(ref for item in items for ref in item.evidence_refs)),
        limitations=tuple(dict.fromkeys(item for evidence_item in items for item in evidence_item.limitations)),
    )
    return FindingFamilyResult(
        family,
        status,  # type: ignore[arg-type]
        direction=direction if direction in {"positive", "negative", "neutral", "mixed", "unknown"} else "unknown",  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
        confidence_score=confidence_score,
        identity_value=min(1.0, 0.5 + 0.5 * confidence_score),
        actionability=0.8 if recommendation and status == "qualified" else 0.25,
        diversity_score=1.0,
        p_value=p_value,
        q_value=q_value,
        evidence=items,
        estimate=estimate,
        claim=claim,
        evidence_text=evidence_text or None,
        interpretation=interpretation,
        recommendation=recommendation,
        qualification_reason="; ".join(dict.fromkeys(reasons)) if reasons else "all family gates passed",
        limitations=tuple(dict.fromkeys(item for evidence_item in items for item in evidence_item.limitations)),
        blocking_confounders=tuple(blocking_confounders),
    )


family_result = qualify_family
qualify_finding_family = qualify_family


def _family_input(
    family: str,
    elements: Mapping[str, Any],
    signals: Mapping[str, Any],
    *,
    sample_size: int,
    independent_sessions: int,
    transitions: int,
    comparable_context_coverage: float,
) -> dict[str, Any]:
    def choose(*keys: str) -> Any:
        for key in keys:
            value = elements.get(key, signals.get(key))
            if isinstance(value, ElementResultV6) and value.estimate.status != "available":
                continue
            if value is not None:
                return value
        return None

    if family == "pool_shape":
        return {"breadth": choose("breadth"), "toolkit": choose("toolkit")}
    if family == "transfer":
        return {"transfer": choose("transfer"), "breadth_or_toolkit": choose("breadth", "toolkit")}
    if family == "post_loss_response":
        return {"response": choose("post_loss_response", "response"), "familiarity_or_tempo": choose("familiarity", "tempo")}
    if family == "combat_expression":
        return {"involvement": choose("involvement"), "death_exposure": choose("death_exposure")}
    return {
        "drift_outcome": choose("drift_outcome"),
        "drift_activity": choose("drift_activity"),
        "drift_survival": choose("drift_survival"),
    }


def evaluate_families(
    elements: Sequence[ElementResultV6] | Mapping[str, Any],
    *,
    signals: Mapping[str, Any] | None = None,
    sample_size: int = 0,
    independent_sessions: int = 0,
    transitions: Mapping[str, int] | int = 0,
    comparable_context_coverage: Mapping[str, float] | float = 1.0,
    p_values: Mapping[str, float] | None = None,
) -> tuple[FindingFamilyResult, ...]:
    """Evaluate and FDR-correct all five families in canonical order."""

    element_map = _element_map(elements)
    signal_map = signals or {}
    transitions_map = transitions if isinstance(transitions, Mapping) else {}
    coverage_map = comparable_context_coverage if isinstance(comparable_context_coverage, Mapping) else {}
    p_values = p_values or {}
    raw: list[FindingFamilyResult] = []
    for family in FINDING_FAMILY_KEYS:
        evidence = _family_input(family, element_map, signal_map, sample_size=sample_size, independent_sessions=independent_sessions, transitions=int(transitions_map.get(family, transitions if isinstance(transitions, int) else 0)), comparable_context_coverage=float(coverage_map.get(family, comparable_context_coverage if isinstance(comparable_context_coverage, (int, float)) else 1.0)))
        direction = str(signal_map.get(f"{family}_direction", signal_map.get(f"{family}_signal", "unknown")))
        raw.append(
            qualify_family(
                family,
                evidence=evidence,
                sample_size=sample_size,
                independent_sessions=independent_sessions,
                transitions=int(transitions_map.get(family, transitions if isinstance(transitions, int) else 0)),
                comparable_context_coverage=float(coverage_map.get(family, comparable_context_coverage if isinstance(comparable_context_coverage, (int, float)) else 1.0)),
                p_value=p_values.get(family),
                direction=direction,
                claim=signal_map.get(f"{family}_claim"),
                interpretation=signal_map.get(f"{family}_interpretation"),
                recommendation=signal_map.get(f"{family}_recommendation"),
            )
        )
    return rank_findings(raw)


def rank_findings(
    findings: Sequence[FindingFamilyResult],
    *,
    q: float = FDR_Q,
    max_published: int = 3,
) -> tuple[FindingFamilyResult, ...]:
    """Apply BH FDR and publish at most three diverse qualified families."""

    values = tuple(findings)
    raw_map = {item.family: (1.0 if item.p_value is None else float(item.p_value)) for item in values}
    q_map = benjamini_hochberg_five(raw_map)
    corrected: list[FindingFamilyResult] = []
    for item in values:
        raw_p_value = raw_map[item.family]
        q_value = q_map[item.family]
        status = item.status
        reason = item.qualification_reason
        if q_value > q:
            status = "suppressed"
            reason = "; ".join(filter(None, (reason, f"BH FDR q-value exceeds {q:.2f}")))
        corrected.append(replace(item, p_value=raw_p_value, q_value=q_value, status=status, published=False, qualification_reason=reason))
    candidates: list[FindingFamilyResult] = []
    for item in corrected:
        if item.status == "qualified" and item.q_value is not None and item.p_value is not None and item.q_value <= q and item.p_value < 1.0:
            candidates.append(item)
    order = {family: index for index, family in enumerate(FINDING_FAMILY_KEYS)}
    candidates.sort(key=lambda item: (-item.confidence_score, -item.identity_value, -item.actionability, -item.diversity_score, order[item.family]))
    published = {item.family for item in candidates[: max(0, int(max_published))]}
    result: list[FindingFamilyResult] = []
    for item in corrected:
        is_published = item.family in published
        recommendation = None if item.sample_size < NORMAL_REPORT_MATCHES else recommendation_for_family(
            item.family,
            status=item.status,
            confidence=item.confidence,
            published=is_published,
            evidence_refs=item.evidence_refs,
            supported_metric_keys=tuple(evidence.key for evidence in item.evidence),
        )
        result.append(replace(item, published=is_published, recommendation=recommendation))
    return tuple(result)


rank_finding_families = rank_findings
apply_bh_fdr = benjamini_hochberg


__all__ = [
    "FAMILY_DEFINITIONS",
    "forbidden_inference_violations",
    "qualify_family",
    "family_result",
    "qualify_finding_family",
    "evaluate_families",
    "rank_findings",
    "rank_finding_families",
    "apply_bh_fdr",
]
