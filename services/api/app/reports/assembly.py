from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.analysis.budget import DataCostLedger
from app.features.summary_models import SummaryFeatureSet
from app.hypotheses.models import Hypothesis
from app.insights.evaluator import InsightContext
from app.insights.models import EvidenceObject
from app.insights.templates import render_action, render_statement
from app.patterns.models import PatternCandidate
from app.selection.models import SelectionPlan

REPLAY_COVERAGE_FAMILIES = frozenset(
    {"time_series", "events", "teamfights", "objectives", "wards"}
)


def assemble_player_dna_report(
    *,
    account_id: int,
    profile: dict[str, Any],
    feature_set: SummaryFeatureSet,
    patterns: list[PatternCandidate],
    hypotheses: list[Hypothesis] | None = None,
    selection_plan: SelectionPlan | None = None,
    cost_ledger: DataCostLedger | None = None,
    processed_matches: int,
    eligible_matches: int,
    history_limit: int,
    model_version: str,
    template_version: str,
) -> tuple[dict[str, Any], list[EvidenceObject]]:
    """Assemble the free report directly from broad summary facts."""

    hypotheses = hypotheses or []
    published_patterns = [item for item in patterns if item.sample_size > 0]
    cards = [_pattern_card(item, account_id=account_id) for item in published_patterns]
    strengths = [
        card
        for item, card in zip(published_patterns, cards, strict=True)
        if item.category == "strength"
    ]
    weaknesses = [
        card
        for item, card in zip(published_patterns, cards, strict=True)
        if item.category in {"weakness", "consistency"}
    ]
    context_cards = [
        card
        for item, card in zip(published_patterns, cards, strict=True)
        if item.category in {"context", "form", "identity"}
    ]
    evidence = [
        _pattern_to_evidence(
            pattern,
            account_id=account_id,
            history_limit=history_limit,
            model_version=model_version,
            template_version=template_version,
            summary_coverage=feature_set.summary_coverage,
        )
        for pattern in published_patterns
    ]
    return (
        {
            "schema_version": "report-2.0.0",
            "report_variant": "free_player_dna",
            "noindex": True,
            "identity": {
                "account_id": account_id,
                "personaname": profile.get("personaname"),
                "avatarfull": profile.get("avatarfull"),
                "profile_url": profile.get("profile_url"),
                "rank_tier": profile.get("rank_tier"),
            },
            "evidence_scope": {
                "processed_matches": processed_matches,
                "eligible_matches": eligible_matches,
                "normalized_matches": 0,
                "excluded_matches": max(0, processed_matches - eligible_matches),
                "summary_parse_coverage": feature_set.summary_coverage,
                "replay_parse_coverage": 0.0,
                "replay_evidence_status": "not_requested",
                "replay_limitation": "Deep evidence was not requested for this Player DNA report.",
                "role_confidence": None,
                "role_status": "summary_hint_only",
                "published_insight_count": len(evidence),
                "suppressed_insight_count": 0,
                "missing_feature_families": ["time_series", "events", "teamfights", "objectives", "wards"],
            },
            "player_dna": {
                "style_summary": _style_summary(published_patterns),
                "strongest_traits": [
                    item.statement
                    for item in published_patterns
                    if item.category == "strength"
                ][:3],
                "hero_identity": {
                    "distinct_heroes": feature_set.distinct_heroes,
                    "hero_counts": feature_set.hero_counts,
                },
                "game_shape": {
                    "sessions": [session.as_dict() for session in feature_set.sessions],
                    "win_rate": feature_set.win_rate,
                },
                "recent_trajectory": [
                    item.as_dict()
                    for item in published_patterns
                    if item.category == "form"
                ],
            },
            "deep_scan": {
                "opportunities": [
                    item.as_dict() for item in published_patterns if item.unexplained
                ],
                "hypotheses": [item.as_dict() for item in hypotheses],
                "selection": selection_plan.as_dict() if selection_plan else None,
            },
            "cost": cost_ledger.as_dict() if cost_ledger else None,
            "sections": {
                "strongest_superpowers": strengths[:3],
                "contradictions": context_cards[:3],
                "highest_value_weaknesses": weaknesses[:3],
                "next_rank": {
                    "status": "deferred",
                    "reason": "Deep Scan is the next step for explaining the highest-priority patterns.",
                },
                "keep": strengths[:3],
                "avoid": weaknesses[:2],
                "work_on_next": weaknesses[:3],
                "hero_role_map": [],
                "career_current_form": {"patterns": [item.as_dict() for item in published_patterns]},
            },
            "evidence_appendix": [
                {
                    **item.as_dict(),
                    "statement": item.statement,
                    "action_text": (
                        "Use Deep Scan to test what is driving this pattern before turning it into a rule."
                        if item.unexplained
                        else "Treat this as a descriptive baseline for the rest of the report."
                    ),
                    "publication_status": "published",
                    "provenance": {
                        "raw_payload_refs": [f"/players/{account_id}/matches"],
                        "normalized_match_refs": [],
                        "derived_feature_refs": [],
                    },
                }
                for item in published_patterns
            ],
        },
        evidence,
    )


def assemble_report(
    *,
    context: InsightContext,
    evidence: list[EvidenceObject],
    exclusion_ledger: list[dict[str, Any]],
    processed_matches: int,
    eligible_matches: int,
) -> dict[str, Any]:
    published = [item for item in evidence if item.published]
    strengths = [item for item in published if _placement(item) == "strength"]
    weaknesses = [item for item in published if _placement(item) == "weakness"]
    contradictions = [
        item
        for item in published
        if any(category in item.categories for category in ("form", "context", "style"))
    ]
    return {
        "schema_version": "report-1.0.0",
        "noindex": True,
        "evidence_scope": _scope(
            context, evidence, exclusion_ledger, processed_matches, eligible_matches
        ),
        "identity": {
            "account_id": context.account_id,
            "personaname": context.profile.get("personaname"),
            "profile_url": context.profile.get("profile_url"),
            "rank_tier": context.profile.get("rank_tier"),
        },
        "sections": {
            "strongest_superpowers": [
                _card(
                    item,
                    "This is one of the highest-ranked positive patterns in the available evidence.",
                )
                for item in strengths[:3]
            ],
            "contradictions": [
                _card(item, "This context changes how the broader pattern should be interpreted.")
                for item in contradictions[:3]
            ],
            "highest_value_weaknesses": [
                _card(item, "This is a measurable behavior worth testing next.")
                for item in weaknesses[:3]
            ],
            "next_rank": {
                "status": "unavailable",
                "reason": "Next-Rank Gap is deferred until aspirational warehouse cohorts and reweighting are qualified.",
            },
            "keep": [
                _card(item, "Keep the behavior while the evidence remains directionally stable.")
                for item in strengths[:3]
            ],
            "avoid": [
                _card(item, "Avoid turning this observed pattern into a permanent identity label.")
                for item in weaknesses[:2]
            ],
            "work_on_next": [
                _card(item, "Use the target as the next practice experiment.")
                for item in weaknesses[:3]
            ],
            "hero_role_map": _hero_role_map(context),
            "career_current_form": _evolution(context),
        },
        "evidence_appendix": [
            {
                **item.as_dict(),
                "statement": render_statement(item) if item.published else None,
                "action_text": render_action(item) if item.published else None,
            }
            for item in evidence
        ],
    }


def _pattern_card(pattern: PatternCandidate, *, account_id: int) -> dict[str, Any]:
    confidence = _pattern_confidence(pattern)
    direction = (
        "positive" if pattern.effect_size > 0.05 else "negative" if pattern.effect_size < -0.05 else None
    )
    return {
        "insight_id": pattern.pattern_id,
        "statement": pattern.statement,
        "player_metric": {"value": pattern.effect_size, "unit": pattern.unit},
        "cohort_metric": (
            {"value": pattern.baseline_value, "unit": pattern.unit}
            if pattern.baseline_value is not None
            else None
        ),
        "effect": {"value": pattern.effect_size, "direction": direction, "unit": pattern.unit},
        "denominator": {
            "matches": pattern.sample_size,
            "situations": pattern.sample_size,
            "parsed_matches": 0,
        },
        "parse_coverage": {"summary": 1.0, "replay": 0.0, "relevant": 1.0},
        "role_certainty": {
            "mean_probability": None,
            "threshold": None,
            "below_threshold": False,
        },
        "selected_cohort": None,
        "evidence_statements": [pattern.statement],
        "confidence": confidence,
        "why_it_matters": (
            "This is a summary-level observation; the causal explanation remains untested."
        ),
        "behavior": (
            "Keep this pattern in mind and use Deep Scan to test the behavior behind it."
        ),
        "target": "Recheck the pattern after the next 20 eligible matches.",
        "practice_window": "next 20 matches",
        "limitations": list(pattern.confounders),
        "source_match_ids": list(pattern.source_match_ids),
        "provenance": {
            "raw_payload_refs": [f"/players/{account_id}/matches"],
            "normalized_match_refs": [],
            "derived_feature_refs": [],
        },
    }


def _pattern_to_evidence(
    pattern: PatternCandidate,
    *,
    account_id: int,
    history_limit: int,
    model_version: str,
    template_version: str,
    summary_coverage: float,
) -> EvidenceObject:
    direction = (
        "positive" if pattern.effect_size > 0.05 else "negative" if pattern.effect_size < -0.05 else None
    )
    return EvidenceObject(
        insight_id=pattern.pattern_id,
        concept_id=pattern.pattern_id,
        categories=(pattern.category,),
        report_scope=f"player_summary_{history_limit}_eligible_matches",
        player={
            "account_id": account_id,
            "value": pattern.effect_size,
            "unit": pattern.unit,
        },
        cohort=(
            {"value": pattern.baseline_value, "unit": pattern.unit}
            if pattern.baseline_value is not None
            else None
        ),
        effect={"value": pattern.effect_size, "direction": direction, "unit": pattern.unit},
        interval=None,
        unit=pattern.unit,
        denominators={
            "matches": pattern.sample_size,
            "situations": pattern.sample_size,
            "parsed_matches": 0,
        },
        parse_coverage={"summary": summary_coverage, "replay": 0.0, "relevant": summary_coverage},
        role_certainty={"mean_probability": None, "threshold": None, "below_threshold": False},
        selected_cohort=None,
        evidence_statements=(pattern.statement,),
        confidence=_pattern_confidence(pattern),
        material_confounders=pattern.confounders,
        action={
            "behavior": "Use Deep Scan to test the behavior behind this observation.",
            "target": "Recheck the pattern after the next 20 eligible matches.",
            "practice_window": "next 20 matches",
        },
        versions={
            "feature_version": "summary-features-1.0.0",
            "cohort_version": "cohorts-1.0.0",
            "model_version": model_version,
            "template_version": template_version,
        },
        source_match_ids=pattern.source_match_ids,
        provenance={
            "raw_payload_refs": [f"/players/{account_id}/matches"],
            "normalized_match_refs": [],
            "derived_feature_refs": [],
        },
        publication_status="published",
        publication_reason=None,
        ivs=pattern.priority,
        definition_version="patterns-1.0.0",
        statement_template_id=pattern.pattern_id,
        action_template_id=pattern.pattern_id,
        investigation={"source_pattern_id": pattern.pattern_id},
    )


def _pattern_confidence(pattern: PatternCandidate) -> str:
    score = min(pattern.summary_confidence, pattern.stability)
    if pattern.sample_size >= 20 and score >= 0.75:
        return "high"
    if pattern.sample_size >= 10 and score >= 0.5:
        return "moderate"
    return "low"


def _style_summary(patterns: list[PatternCandidate]) -> str:
    categories = {item.category for item in patterns if item.unexplained}
    if "strength" in categories and "weakness" in categories:
        return "The adaptive competitor"
    if "strength" in categories:
        return "The timing-hungry specialist"
    if "weakness" in categories:
        return "The high-variance competitor"
    return "The developing competitor"


def _scope(
    context: InsightContext,
    evidence: list[EvidenceObject],
    exclusion_ledger: list[dict[str, Any]],
    processed_matches: int,
    eligible_matches: int,
) -> dict[str, Any]:
    suppressed_replay = [
        item
        for item in evidence
        if item.publication_status == "suppressed"
        and "INSUFFICIENT_PARSE_COVERAGE" in (item.publication_reason or "")
    ]
    missing_families = sorted(
        family
        for family, value in _coverage_families(context).items()
        if value
        < (
            context.replay_coverage_threshold
            if family in REPLAY_COVERAGE_FAMILIES
            else context.summary_coverage_threshold
        )
    )
    return {
        "processed_matches": processed_matches,
        "eligible_matches": eligible_matches,
        "normalized_matches": len(context.features),
        "excluded_matches": len(exclusion_ledger),
        "exclusion_reasons": _reason_counts(exclusion_ledger),
        "summary_parse_coverage": context.summary_coverage,
        "replay_parse_coverage": context.replay_coverage,
        "role_confidence": context.role_confidence,
        "role_status": "available"
        if context.role_confidence >= context.role_confidence_threshold
        else "uncertain",
        "missing_feature_families": missing_families,
        "replay_evidence_status": "available"
        if context.replay_coverage >= context.replay_coverage_threshold
        else "not_enough_evidence",
        "replay_limitation": (
            "Replay-dependent insight families are suppressed because parsed coverage is below the publication gate."
            if suppressed_replay
            else None
        ),
        "cohort": context.cohort.as_dict()
        if context.cohort
        else {
            "valid": False,
            "suppression_reason": "NO_VALID_COHORT",
        },
        "published_insight_count": sum(item.published for item in evidence),
        "suppressed_insight_count": sum(not item.published for item in evidence),
    }


def _card(item: EvidenceObject, why: str) -> dict[str, Any]:
    return {
        "insight_id": item.insight_id,
        "statement": render_statement(item),
        "player_metric": item.player,
        "cohort_metric": item.cohort,
        "effect": item.effect,
        "denominator": item.denominators,
        "parse_coverage": item.parse_coverage,
        "role_certainty": item.role_certainty,
        "selected_cohort": item.selected_cohort,
        "evidence_statements": item.evidence_statements,
        "confidence": item.confidence,
        "why_it_matters": why,
        "behavior": render_action(item),
        "target": item.action.get("target"),
        "practice_window": item.action.get("practice_window"),
        "limitations": item.material_confounders,
        "source_match_ids": item.source_match_ids,
        "provenance": item.provenance,
    }


def _placement(item: EvidenceObject) -> str | None:
    """Place a card only when its measured direction supports the claim."""

    direction = item.effect.get("direction")
    if direction == "positive" and "strength" in item.categories:
        return "strength"
    if direction == "negative" and "weakness" in item.categories:
        return "weakness"
    return None


def _hero_role_map(context: InsightContext) -> list[dict[str, Any]]:
    grouped: dict[tuple[int | None, int | None], list[bool]] = defaultdict(list)
    for feature in context.features:
        grouped[(feature.hero_id, feature.role)].append(feature.won)
    return [
        {
            "hero_id": hero_id,
            "role": role,
            "matches": len(results),
            "win_rate": sum(results) / len(results),
        }
        for (hero_id, role), results in sorted(
            grouped.items(), key=lambda item: (-len(item[1]), item[0])
        )
    ]


def _evolution(context: InsightContext) -> dict[str, Any]:
    ordered = sorted(context.features, key=lambda feature: feature.start_time or feature.match_id)
    midpoint = max(1, int(len(ordered) * 0.70))
    prior = ordered[:midpoint]
    recent = ordered[midpoint:]
    return {
        "prior_matches": len(prior),
        "recent_matches": len(recent),
        "prior_win_rate": _rate(prior),
        "recent_win_rate": _rate(recent),
        "recent_heroes": Counter(feature.hero_id for feature in recent).most_common(),
    }


def _coverage_families(context: InsightContext) -> dict[str, float]:
    values: dict[str, list[float]] = defaultdict(list)
    for feature in context.features:
        for family, value in feature.coverage.by_family.items():
            values[family].append(value)
    return {family: sum(items) / len(items) for family, items in values.items() if items}


def _reason_counts(ledger: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for item in ledger:
        counts.update(item.get("reasons", []))
    return dict(sorted(counts.items()))


def _rate(features: list[Any]) -> float | None:
    return sum(feature.won for feature in features) / len(features) if features else None
