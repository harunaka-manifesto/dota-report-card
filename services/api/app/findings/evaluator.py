"""Deterministic evaluation and publication gates for Free findings."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from app.findings.context import FreeFindingContext
from app.findings.copy import render_finding_copy
from app.findings.experiments import experiment_for_finding
from app.findings.models import FindingCandidate, FindingDefinition, FindingSignal
from app.findings.ranking import rank_findings
from app.findings.registry import FINDING_REGISTRY
from app.findings.signals import derive_signals


def evaluate_free_findings(context: FreeFindingContext) -> tuple[FindingCandidate, ...]:
    """Return only publishable, editorially ranked findings."""

    candidates = evaluate_free_candidates(context)
    return tuple(
        candidate
        for candidate in rank_findings(candidates)
        if candidate.publication_status == "published"
    )


def evaluate_free_candidates(context: FreeFindingContext) -> tuple[FindingCandidate, ...]:
    """Evaluate every finite rule, retaining suppression reasons for tests."""

    signals = derive_signals(context)
    candidates: list[FindingCandidate] = []
    for key in FINDING_REGISTRY:
        if key == "hidden_strength_fallback":
            continue
        evidence, params, related_heroes = _rule(key, context, signals)
        if evidence:
            candidates.append(_candidate(
                FINDING_REGISTRY[key], context, evidence, params, related_heroes=related_heroes
            ))

    if not any(item.publication_status == "published" and item.kind == "strength" for item in candidates):
        evidence, params, related_heroes = _fallback_rule(context, signals)
        if evidence:
            candidates.append(_candidate(
                FINDING_REGISTRY["hidden_strength_fallback"], context, evidence, params,
                related_heroes=related_heroes,
            ))
    return tuple(sorted(candidates, key=lambda item: item.key))


def _rule(
    key: str,
    context: FreeFindingContext,
    signals: dict[str, FindingSignal],
) -> tuple[tuple[FindingSignal, ...], dict[str, str], tuple[int, ...]]:
    if key == "broad_pool_narrow_safety_zone":
        return _broad_pool_rule(signals)
    if key == "many_heroes_same_toolkit":
        pattern = signals.get("hero.pattern.primary")
        count = signals.get("feature.unique_hero_count")
        if pattern is None or count is None or not isinstance(count.value, (int, float)) or count.value < 8:
            return (), {}, ()
        traits = _list_text(pattern.metadata.get("traits"))
        if not traits or pattern.sample_size < 3:
            return (), {}, ()
        return (count, pattern), {"traits": _join_traits(traits)}, ()
    if key == "activity_travels_better_than_results":
        activity = signals.get("feature.off_pool_activity_delta")
        performance = signals.get("feature.familiar_vs_off_pool_delta")
        dimension = signals.get("dimension.activity")
        if not _number_in_range(activity, -0.30, 0.30) or not _number_at_least(performance, 0.10):
            return (), {}, ()
        assert activity is not None and performance is not None
        if dimension is None:
            evidence: tuple[FindingSignal, ...] = (activity, performance)
        else:
            assert dimension is not None
            evidence = (dimension, activity, performance)
        if min(item.sample_size for item in evidence) < 8:
            return (), {}, ()
        return evidence, {
            "activity_read": "close to your familiar-hero baseline",
            "performance_gap": _percent(performance.value),
        }, ()
    if key == "losses_change_trust_more_than_pace":
        familiarity = signals.get("derived.loss_familiarity_delta")
        resilience = signals.get("dimension.resilience")
        activity = signals.get("derived.loss_activity_delta")
        if not _number_at_least(familiarity, 0.12):
            return (), {}, ()
        assert familiarity is not None
        if familiarity.sample_size < 12:
            return (), {}, ()
        if activity is not None and isinstance(activity.value, (int, float)) and abs(activity.value) > 0.30:
            return (), {}, ()
        loss_evidence = (familiarity, resilience) if resilience is not None else (familiarity,)
        return loss_evidence, {
            "after_win": _percent(_signal_value(signals.get("derived.after_win_familiar_pick_rate"))),
            "after_loss": _percent(_signal_value(signals.get("derived.after_loss_familiar_pick_rate"))),
        }, ()
    if key == "long_session_tax":
        pattern = signals.get("pattern.session_decline")
        endurance = signals.get("dimension.endurance")
        session_length = signals.get("feature.session_length_p75")
        if pattern is None or pattern.sample_size < 8:
            return (), {}, ()
        if session_length is not None and isinstance(session_length.value, (int, float)) and session_length.value < 4:
            return (), {}, ()
        session_evidence = (pattern, endurance) if endurance is not None else (pattern,)
        return session_evidence, {"delta": "lower"}, ()
    if key == "long_game_edge":
        return _duration_rule(signals, "pattern.long_game_improvement", "higher")
    if key == "long_game_leak":
        return _duration_rule(signals, "pattern.long_game_decline", "lower")
    if key == "form_identity_divergence":
        patterns = [signals.get("pattern.recent_improvement"), signals.get("pattern.recent_decline")]
        pattern = next((item for item in patterns if item is not None), None)
        style_signal = signals.get("feature.recent_hero_concentration_delta")
        activity_signal = signals.get("feature.recent_activity_delta")
        style_signals = tuple(item for item in (style_signal, activity_signal) if item is not None and _numeric(item.value) is not None and abs(_numeric(item.value) or 0.0) <= 0.12)
        if pattern is None or pattern.sample_size < 15 or not style_signals:
            return (), {}, ()
        return (pattern, *style_signals), {"style_delta": _percent(max(abs(_numeric(item.value) or 0.0) for item in style_signals))}, ()
    if key == "strength_with_tax":
        return _strength_tax_rule(signals)
    if key == "signature_hero_mechanism":
        signature = signals.get("hero.signature")
        pattern = signals.get("hero.pattern.primary")
        if signature is None or pattern is None or pattern.sample_size < 3:
            return (), {}, ()
        traits = _list_text(pattern.metadata.get("traits"))
        hero_id = signature.metadata.get("hero_id")
        related = (hero_id,) if isinstance(hero_id, int) else ()
        return (signature, pattern), {"hero": str(signature.value), "traits": _join_traits(traits)}, related
    if key == "role_vs_hero_identity":
        role = signals.get("dimension.role")
        breadth = signals.get("dimension.breadth")
        hero_entropy = signals.get("feature.normalized_hero_entropy")
        if role is None or breadth is None or hero_entropy is None:
            return (), {}, ()
        if not isinstance(role.value, (int, float)) or not isinstance(breadth.value, (int, float)) or not isinstance(hero_entropy.value, (int, float)):
            return (), {}, ()
        if float(breadth.value) < 0.12 or float(role.value) > 0.18:
            return (), {}, ()
        return (role, breadth, hero_entropy), {}, ()
    if key == "volatile_results_stable_style":
        volatility = signals.get("pattern.consistency_collapse")
        stable_style_signals = tuple(
            item for item in (
                signals.get("feature.recent_hero_concentration_delta"),
                signals.get("feature.recent_activity_delta"),
            )
            if item is not None and isinstance(item.value, (int, float)) and abs(item.value) <= 0.12
        )
        if volatility is None or volatility.sample_size < 10 or not stable_style_signals:
            return (), {}, ()
        return (volatility, *stable_style_signals), {}, ()
    return (), {}, ()


def _broad_pool_rule(
    signals: dict[str, FindingSignal],
) -> tuple[tuple[FindingSignal, ...], dict[str, str], tuple[int, ...]]:
    entropy = signals.get("feature.normalized_hero_entropy")
    breadth = signals.get("dimension.breadth")
    wide = entropy is not None and _number_at_least(entropy, 0.55)
    if breadth is not None and _number_at_least(breadth, 0.20):
        wide = True
    if not wide:
        return (), {}, ()
    safety = signals.get("derived.loss_familiarity_delta")
    if safety is None or not _number_at_least(safety, 0.12) or safety.sample_size < 12:
        performance = signals.get("feature.familiar_vs_off_pool_delta")
        if performance is None or not _number_at_least(performance, 0.10) or performance.sample_size < 8:
            return (), {}, ()
        safety = performance
    breadth_evidence = breadth or entropy
    assert breadth_evidence is not None
    return (breadth_evidence, safety), {}, ()


def _duration_rule(
    signals: dict[str, FindingSignal], pattern_key: str, delta: str
) -> tuple[tuple[FindingSignal, ...], dict[str, str], tuple[int, ...]]:
    pattern = signals.get(pattern_key)
    endurance = signals.get("dimension.endurance")
    if pattern is None or pattern.sample_size < 5:
        return (), {}, ()
    return ((pattern, endurance) if endurance is not None else (pattern,)), {"delta": delta}, ()


def _strength_tax_rule(
    signals: dict[str, FindingSignal],
) -> tuple[tuple[FindingSignal, ...], dict[str, str], tuple[int, ...]]:
    activity = signals.get("dimension.activity")
    session_decline = signals.get("pattern.session_decline")
    if activity is not None and _number_at_least(activity, 0.20) and session_decline is not None:
        return (activity, session_decline), {"strength": "activity", "tax": "a later-session decline"}, ()
    breadth = signals.get("dimension.breadth")
    gap = signals.get("feature.familiar_vs_off_pool_delta")
    if breadth is not None and _number_at_least(breadth, 0.20) and _number_at_least(gap, 0.10):
        assert gap is not None
        return (breadth, gap), {"strength": "exploration", "tax": "a familiar-hero performance gap"}, ()
    specialization = signals.get("pattern.hero_specialization")
    if specialization is not None and gap is not None and _number_at_least(gap, 0.10):
        return (specialization, gap), {"strength": "specialization", "tax": "a stretch-hero gap"}, ()
    return (), {}, ()


def _fallback_rule(
    context: FreeFindingContext, signals: dict[str, FindingSignal]
) -> tuple[tuple[FindingSignal, ...], dict[str, str], tuple[int, ...]]:
    positive_dimensions = [
        item for key, item in signals.items()
        if key.startswith("dimension.") and (_numeric(item.value) or 0.0) >= 0.20
    ]
    positive_dimensions.sort(key=lambda item: (-(_numeric(item.value) or 0.0), item.key))
    if positive_dimensions:
        lead = positive_dimensions[0]
        support_key = {
            "dimension.breadth": "feature.unique_hero_count",
            "dimension.activity": "feature.activity_median",
            "dimension.endurance": "feature.endurance_delta",
            "dimension.role": "feature.dominant_role_share",
        }.get(lead.key, "feature.overall_win_rate")
        support = signals.get(support_key) or signals.get("feature.overall_win_rate")
        if support is not None:
            return (lead, support), {"strength": lead.public_receipt, "support": support.public_receipt}, ()
    positive_patterns = [
        item for key, item in signals.items()
        if key in {"pattern.hero_overperformance", "pattern.long_game_improvement", "pattern.recent_improvement"}
    ]
    positive_patterns.sort(key=lambda item: (-item.confidence_score, item.key))
    if positive_patterns:
        lead = positive_patterns[0]
        support = signals.get("feature.overall_win_rate")
        if support is not None:
            return (lead, support), {"strength": lead.public_receipt, "support": support.public_receipt}, ()
    return (), {}, ()


def _candidate(
    definition: FindingDefinition,
    context: FreeFindingContext,
    evidence: Iterable[FindingSignal],
    params: dict[str, str],
    *,
    related_heroes: tuple[int, ...] = (),
) -> FindingCandidate:
    deduped = tuple({item.key: item for item in evidence}.values())
    confidence = _finding_confidence(deduped)
    gate_reason = _publication_gate_reason(definition, deduped, confidence)
    copy = render_finding_copy(definition.key, **params)
    experiment = experiment_for_finding(definition.key, context, {item.key: item for item in deduped})
    if gate_reason is None:
        priority = _priority(definition, confidence, deduped)
        status: Literal["published", "suppressed"] = "published"
    else:
        priority = 0.0
        status = "suppressed"
    limitations = tuple(
        sorted({str(value) for item in deduped for value in item.metadata.get("confounders", ())})
    )
    return FindingCandidate(
        key=definition.key,
        kind=definition.kind,
        headline=copy["headline"],
        body=copy["body"],
        interpretation=copy["interpretation"],
        evidence=deduped,
        confidence_score=confidence,
        surprise_score=_bounded(definition.surprise_prior + _effect_bonus(deduped)),
        specificity_score=_bounded(definition.specificity_prior + 0.02 * min(3, len(deduped) - 2)),
        consequence_score=_bounded(definition.consequence_prior),
        actionability_score=_bounded(definition.actionability_prior if experiment is not None else definition.actionability_prior * 0.75),
        shareability_score=_bounded(definition.shareability_prior),
        priority_score=priority,
        experiment=experiment,
        limitations=limitations,
        publication_status=status,
        suppression_reason=gate_reason,
        definition_version=definition.version,
        concept_tags=definition.concept_tags,
        related_dimensions=definition.related_dimensions,
        related_heroes=related_heroes,
        share_copy=copy["share"],
    )


def _publication_gate_reason(
    definition: FindingDefinition,
    evidence: tuple[FindingSignal, ...],
    confidence: float,
) -> str | None:
    if len(evidence) < 2:
        return "minimum_two_evidence_items"
    if len({item.family for item in evidence}) < definition.minimum_families:
        return "insufficient_evidence_families"
    if confidence < definition.minimum_confidence:
        return "insufficient_confidence"
    for key, minimum in definition.minimum_samples.items():
        matching = [item.sample_size for item in evidence if item.key == key]
        if matching and min(matching) < minimum:
            return f"insufficient_sample:{key}"
    if any(item.coverage <= 0.0 for item in evidence):
        return "insufficient_coverage"
    return None


def _finding_confidence(evidence: tuple[FindingSignal, ...]) -> float:
    scores = sorted(item.confidence_score for item in evidence)
    if not scores:
        return 0.0
    return _bounded(0.65 * scores[0] + 0.35 * (sum(scores) / len(scores)))


def _priority(definition: FindingDefinition, confidence: float, evidence: tuple[FindingSignal, ...]) -> float:
    editorial = (
        0.28 * definition.surprise_prior
        + 0.22 * definition.specificity_prior
        + 0.20 * definition.consequence_prior
        + 0.15 * definition.actionability_prior
        + 0.15 * definition.shareability_prior
    )
    family_bonus = {1: 0.85, 2: 1.0, 3: 1.08}.get(min(3, len({item.family for item in evidence})), 1.08)
    contradiction_bonus = definition.contradiction_bonus
    return min(1.25, confidence ** 1.35 * editorial * family_bonus * contradiction_bonus)


def _effect_bonus(evidence: tuple[FindingSignal, ...]) -> float:
    numeric = [abs(float(item.value)) for item in evidence if isinstance(item.value, (int, float))]
    return min(0.12, (max(numeric, default=0.0) * 0.08))


def _number_at_least(signal: FindingSignal | None, threshold: float) -> bool:
    return signal is not None and isinstance(signal.value, (int, float)) and float(signal.value) >= threshold


def _number_in_range(signal: FindingSignal | None, lower: float, upper: float) -> bool:
    return signal is not None and isinstance(signal.value, (int, float)) and lower <= float(signal.value) <= upper


def _signal_value(signal: FindingSignal | None) -> float | None:
    return float(signal.value) if signal is not None and isinstance(signal.value, (int, float)) else None


def _percent(value: Any) -> str:
    numeric = _numeric(value)
    if numeric is None:
        return "not available"
    return f"{numeric:.0%}"


def _numeric(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _list_text(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, (list, tuple)) else []


def _join_traits(values: list[str]) -> str:
    if len(values) == 1:
        return values[0]
    if len(values) == 2:
        return f"{values[0]} and {values[1]}"
    return f"{', '.join(values[:-1])}, and {values[-1]}"


def _bounded(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
