from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from app.insights.evaluator import InsightContext
from app.insights.models import EvidenceObject
from app.insights.templates import render_action, render_statement

REPLAY_COVERAGE_FAMILIES = frozenset(
    {"time_series", "events", "teamfights", "objectives", "wards"}
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
