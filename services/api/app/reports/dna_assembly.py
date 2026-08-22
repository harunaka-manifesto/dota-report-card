"""Public v5 report projection for Elements, Patterns, and Hero Portfolio."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.analysis.budget import DataCostLedger
from app.behavior.outcomes import SEMANTIC_OUTCOME_VERSION
from app.behavior.presentation import (
    PATTERN_PRESENTATION_VERSION,
    PatternPresentationPayload,
    build_pattern_presentation,
)
from app.behavior.ranking import (
    FREE_ELEMENT_HIGHLIGHT_LIMIT,
    FREE_PATTERN_HIGHLIGHT_LIMIT,
    PATTERN_RANKING_VERSION,
    rank_element_highlights,
    rank_pattern_highlights,
)
from app.content.catalog import copy_version
from app.content.renderer import (
    resolve_element_copy,
    resolve_evolution_copy,
    resolve_page_copy,
    resolve_pattern_copy,
    resolve_pattern_presentation_copy,
    resolve_portfolio_copy,
    resolve_story_copy,
    validate_copy_catalog,
)
from app.dna.pipeline import DnaAnalysisResult
from app.hero_portfolio.config import PORTFOLIO_CONFIG_VERSION
from app.hero_portfolio.models import HeroExceptionResult, HeroPortfolioResult
from app.hero_portfolio.version import (
    HERO_EXPRESSIONS_VERSION,
    HERO_MATCHUPS_VERSION,
    HERO_MIRROR_VERSION,
    HERO_RELATIONSHIPS_VERSION,
    HERO_RELIABILITY_VERSION,
    HERO_SITUATIONS_VERSION,
    HERO_SYNERGIES_VERSION,
    PATTERN_ACTIONS_VERSION,
)
from app.heroes.knowledge import FullRosterHeroKnowledgeProvider
from app.heroes.recommendations import SEMANTIC_RECOMMENDATION_VERSION
from app.share.service import RENDERER_VERSION

REPORT_SCHEMA_VERSION = "free-dna-report-5.2.0"
# 5.3 keeps the public report schema stable while making the reviewed story
# contract explicit: Pool Evolution is one choose -> reveal payoff, not two
# consecutive pages. The schema validator still accepts 5.2 snapshots.
REPORT_STORY_VERSION = "free-story-5.3.0"


def assemble_free_dna_report_v4(
    *,
    account_id: int,
    profile: dict[str, Any],
    analysis: DnaAnalysisResult,
    processed_matches: int,
    eligible_matches: int,
    raw_payload_hash: str,
    history_limit: int | None,
    model_version: str,
    template_version: str,
    cost_ledger: DataCostLedger | None,
    analysis_version_fingerprint: str,
) -> dict[str, Any]:
    """Assemble one immutable, privacy-safe v5 snapshot.

    The public projection deliberately omits raw rows, raw match identifiers,
    and private scorer metrics.  All downstream story pages read this snapshot
    rather than recalculating from source history.
    """

    behavior = analysis.behavior
    element_highlights = rank_element_highlights(behavior.elements, limit=FREE_ELEMENT_HIGHLIGHT_LIMIT)
    pattern_highlights = rank_pattern_highlights(behavior.patterns, limit=FREE_PATTERN_HIGHLIGHT_LIMIT)
    element_map = behavior.element_map
    pattern_map = behavior.pattern_map
    portfolio = analysis.hero_portfolio
    taxonomy = analysis.taxonomy
    if taxonomy is None:
        raise ValueError("Free DNA report assembly requires the scoring hero taxonomy snapshot")
    hero_knowledge = analysis.hero_knowledge or FullRosterHeroKnowledgeProvider(taxonomy)
    if not getattr(hero_knowledge, "available", True):
        # Historical callers may construct an analysis without semantic data.
        # Keep the structural full-roster adapter explicit and versioned.
        hero_knowledge = FullRosterHeroKnowledgeProvider(taxonomy)
    pattern_presentations = {
        pattern.key: build_pattern_presentation(
            pattern,
            element_map,
            matches=analysis.matches,
            taxonomy=taxonomy,
            hero_knowledge=hero_knowledge,
        )
        for pattern in behavior.patterns
    }
    pages = _story_pages(
        element_highlights=element_highlights,
        pattern_highlights=pattern_highlights,
        element_map=element_map,
        pattern_map=pattern_map,
        pattern_presentations=pattern_presentations,
        portfolio=portfolio,
    )
    ordered_page_ids = [item["id"] for item in pages]
    display_name = str(profile.get("personaname") or "Anonymous player")
    versions = {
        "eligibility": "summary-eligibility-1.0.0",
        "sessions": analysis.sessions.policy.version,
        "features": analysis.features.feature_version,
        "behavior_model": behavior.versions.behavior_model,
        "element_registry": behavior.versions.element_registry,
        "pattern_registry": behavior.versions.pattern_registry,
        "context_baseline": behavior.versions.context_baseline,
        "pattern_ranking": PATTERN_RANKING_VERSION,
        "pattern_actions": PATTERN_ACTIONS_VERSION,
        "presentation": PATTERN_PRESENTATION_VERSION,
        "semantic_outcomes": SEMANTIC_OUTCOME_VERSION,
        "semantic_recommendations": SEMANTIC_RECOMMENDATION_VERSION,
        "hero_taxonomy": _taxonomy_version(portfolio),
        "hero_knowledge": hero_knowledge.version,
        "hero_relationships": HERO_RELATIONSHIPS_VERSION,
        "hero_expressions": HERO_EXPRESSIONS_VERSION,
        "hero_reliability": HERO_RELIABILITY_VERSION,
        "hero_matchups": HERO_MATCHUPS_VERSION,
        "hero_synergies": HERO_SYNERGIES_VERSION,
        "hero_situations": HERO_SITUATIONS_VERSION,
        "hero_portfolio": f"{portfolio.version}+{PORTFOLIO_CONFIG_VERSION}",
        "hero_mirror": HERO_MIRROR_VERSION,
        "story": REPORT_STORY_VERSION,
        "copy": copy_version(),
        "model": model_version,
        "template": template_version,
        "share_renderer": RENDERER_VERSION,
        "analysis_version_fingerprint": analysis_version_fingerprint,
        "performance_proxy": analysis.features.performance_proxy_version,
        "recency_weighting": analysis.features.recency_weighting_version,
        "sessionization": analysis.sessions.policy.version,
    }
    cost = _free_cost(cost_ledger)
    quality = {
        "overall_confidence": behavior.quality.overall_confidence,
        "history_tier": analysis.history_tier,
        "missing_data_flags": [item.key for item in behavior.elements if item.status == "unavailable"],
        "partial": analysis.history_tier == "limited" or bool(behavior.quality.warnings),
        "warnings": list(dict.fromkeys(analysis.warnings)),
        "available_elements": behavior.quality.available_elements,
        "limited_elements": behavior.quality.limited_elements,
        "unavailable_elements": behavior.quality.unavailable_elements,
        "qualified_patterns": behavior.quality.qualified_patterns,
    }
    strongest_elements = [
        {"key": item.key, "label": item.label, "zone": item.zone}
        for item in (element_map[key.element_key] for key in element_highlights)
    ]
    strongest_patterns = [
        {"key": item.key, "label": item.label}
        for item in pattern_highlights
    ]
    hero_mirror = portfolio.hero_mirror
    share = {
        "display_name": display_name,
        "strongest_elements": strongest_elements,
        "strongest_patterns": strongest_patterns,
        "hero_portfolio": {
            "common_thread": portfolio.common_thread.trait_label,
            "exception_hero": portfolio.exception.hero_name,
            "pool_direction": _evolution_display_copy(portfolio.evolution.variant),
        },
        "hero_mirror": (
            {"hero_id": hero_mirror.hero_id, "hero_name": hero_mirror.hero_name}
            if hero_mirror.hero_id is not None and hero_mirror.hero_name is not None
            else None
        ),
    }
    data_from, data_to = _date_bounds(analysis)
    generated_at = datetime.now(UTC).isoformat()
    reproducibility = {
        "model_version": model_version,
        "element_registry_version": behavior.versions.element_registry,
        "pattern_registry_version": behavior.versions.pattern_registry,
        "context_baseline_version": behavior.versions.context_baseline,
        "hero_taxonomy_version": _taxonomy_version(portfolio),
        "hero_knowledge_version": hero_knowledge.version,
        "performance_proxy_version": analysis.features.performance_proxy_version,
        "sessionization_version": analysis.sessions.policy.version,
        "recency_weighting_version": analysis.features.recency_weighting_version,
        "generated_at": generated_at,
        "window_start": data_from,
        "window_end": data_to,
        "input_snapshot_hash": raw_payload_hash,
        "raw_match_count": max(0, processed_matches),
        "usable_match_count": max(0, eligible_matches),
        "deduplicated_match_count": len(analysis.matches),
        "session_count": len(analysis.sessions.sessions),
        "completed_session_count": len(analysis.sessions.completed_sessions),
        "left_censored_session_count": analysis.sessions.left_censored_session_count,
        "right_censored_session_count": analysis.sessions.right_censored_session_count,
        "role_hint_coverage": analysis.features.role_coverage,
        "hero_taxonomy_coverage": _hero_taxonomy_coverage(analysis),
        "effective_sample_size": analysis.features.effective_sample_size,
        "recency_config": {
            "half_life_days": analysis.features.recency_half_life_days,
            "version": analysis.features.recency_weighting_version,
        },
        "session_gap_config": {
            "gap_minutes": analysis.sessions.policy.gap_minutes,
            "clock_tolerance_seconds": analysis.sessions.policy.clock_tolerance_seconds,
        },
    }
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_variant": "free_dna_report",
        "report_id": None,
        "noindex": True,
        "identity": {
            "display_name": display_name,
            "avatar_url": profile.get("avatarfull"),
            "rank_tier": profile.get("rank_tier"),
        },
        "metadata": {
            "created_at": generated_at,
            "expires_at": None,
            "data_from": data_from,
            "data_to": data_to,
            "processed_matches": max(0, processed_matches),
            "eligible_matches": max(0, eligible_matches),
            "history_limit": history_limit,
            "raw_history_hash": raw_payload_hash,
            "history_tier": analysis.history_tier,
        },
        "versions": versions,
        "reproducibility": reproducibility,
        "quality": quality,
        "elements": [item.as_dict(public=True) for item in behavior.elements],
        "patterns": [
            {
                **item.as_dict(public=True),
                "presentation": pattern_presentations[item.key].as_dict(),
            }
            for item in behavior.patterns
        ],
        "highlights": {
            "element_keys": [item.element_key for item in element_highlights],
            "pattern_keys": [item.key for item in pattern_highlights],
        },
        "hero_portfolio": _public_portfolio(portfolio),
        "story": {
            "version": REPORT_STORY_VERSION,
            "ordered_pages": ordered_page_ids,
        },
        "pages": pages,
        "shares": {
            "final": share,
            "privacy_defaults": {"show_name": True, "show_avatar": True, "show_raw_id": False},
        },
        "deep_dive": {
            "available": True,
            "cta_label": "Tell me more",
            "href": "/?mode=deep_scan",
            "copy": "Go deeper when you want selected match-detail explanations behind a supported discovery.",
        },
        "methodology": {
            "free_summary_only": True,
            "session_gap_minutes": analysis.sessions.policy.gap_minutes,
            "session_policy_version": analysis.sessions.policy.version,
            "notes": [
                "One bounded public summary-history window powers this report.",
                "No individual match-detail reads or replay parses are required for Free DNA.",
                "Hero Portfolio uses established hero history and a versioned semantic hero layer with explicit review status.",
            ],
        },
        "cost": cost,
    }


def _story_pages(
    *,
    element_highlights,
    pattern_highlights,
    element_map,
    pattern_map,
    pattern_presentations: dict[str, PatternPresentationPayload],
    portfolio: HeroPortfolioResult,
) -> list[dict[str, Any]]:
    element_scan_copy = resolve_page_copy("element_scan")
    final_copy = resolve_page_copy("final_card")
    deep_dive_copy = resolve_page_copy("deep_dive")
    common_question = resolve_portfolio_copy("common_thread.question")
    exception_question = resolve_portfolio_copy("exception.question")
    evolution_question = resolve_portfolio_copy("evolution.question")
    evolution_content = _evolution_content(portfolio.evolution.variant)
    mirror_closed = resolve_portfolio_copy("hero_mirror.closed")
    pages: list[dict[str, Any]] = [
        {
            "id": "element-scan",
            "kind": "element_scan",
            "section": "elements",
            "title": element_scan_copy["title"],
            "body": element_scan_copy["body"] + " The strongest three get a closer look next.",
            "content": {
                "scanning_body": element_scan_copy["scanning_body"],
                "ready_body": element_scan_copy["ready_body"],
            },
            "evidence_keys": list(element_map),
        }
    ]
    for highlight in element_highlights:
        element = element_map[highlight.element_key]
        element_copy = resolve_element_copy(element.key)
        pages.append(
            {
                "id": f"element-{element.key}",
                "kind": "element_highlight",
                "section": "elements",
                "title": element.label,
                "body": element_copy["body"],
                "evidence_keys": [element.key],
                "element_key": element.key,
                "content": {
                    "meaning": element_copy["body"],
                    "observation": resolve_story_copy(
                        "element",
                        "observation",
                        label=element.label,
                        zone=element.zone or "unavailable",
                    ),
                    "why_highlight": resolve_story_copy("element", "distinctive"),
                    "evidence": resolve_story_copy("element", "evidence"),
                    "what_to_notice": resolve_story_copy("element", "notice"),
                    "guardrail": resolve_story_copy("element", "guardrail"),
                    "display_reason": highlight.display_reason,
                },
            }
        )
    for pattern in pattern_highlights:
        pattern_copy = resolve_pattern_copy(pattern.key)
        presentation = pattern_presentations[pattern.key]
        presentation_copy = _pattern_presentation_copy(presentation)
        required_observations = [
            resolve_story_copy(
                "pattern",
                "observation",
                label=element_map[key].label,
                zone=element_map[key].zone or "unavailable",
            )
            for key in pattern.element_keys
            if key in element_map
        ]
        pages.append(
            {
                "id": f"pattern-{pattern.key}",
                "kind": "pattern_highlight",
                "section": "patterns",
                "title": pattern.label,
                "body": pattern_copy["body"],
                "evidence_keys": list(pattern.element_keys),
                "pattern_key": pattern.key,
                "content": {
                    "meaning": pattern_copy["body"],
                    "observations": required_observations,
                    "worth_noticing": resolve_story_copy("pattern", "worth_noticing"),
                    "player_read": resolve_story_copy("pattern", "player_read"),
                    "takeaway": resolve_story_copy("pattern", "takeaway"),
                    "guardrail": resolve_story_copy("pattern", "guardrail"),
                    "required_element_keys": list(pattern.element_keys),
                    "modifier_element_keys": list(pattern.modifier_element_keys),
                    "action_copy": _pattern_action_copy(pattern.key) if pattern.action is not None else None,
                    "presentation_copy": presentation_copy,
                },
                "presentation": presentation.as_dict(),
            }
        )
    if not pattern_highlights:
        pages.append(
            {
                "id": "pattern-read",
                "kind": "pattern_highlight",
                "section": "patterns",
                "title": "No Pattern cleared yet",
                "body": "The current summary history did not support a clear Pattern yet. The report keeps the uncertainty visible while the Elements remain readable.",
                "evidence_keys": [],
                "pattern_key": None,
                "content": {},
                "presentation": None,
            }
        )
    pages.extend(
        [
            {
                "id": "hero-common-thread",
                "kind": "hero_common_thread_question",
                "section": "hero_portfolio",
                "title": common_question,
                "body": resolve_portfolio_copy("common_thread.question_body"),
                "evidence_keys": [],
                "portfolio_key": "common_thread",
                "options": [option.as_dict() for option in portfolio.common_thread.options],
                "content": {
                    "boundary": resolve_portfolio_copy("common_thread.boundary"),
                    "correct_label": resolve_portfolio_copy("common_thread.correct"),
                    "incorrect_label": resolve_portfolio_copy("common_thread.incorrect"),
                },
            },
            {
                "id": "hero-exception",
                "kind": "hero_exception_question",
                "section": "hero_portfolio",
                "title": exception_question,
                "body": resolve_portfolio_copy("exception.question_body"),
                "evidence_keys": [],
                "portfolio_key": "exception",
                "options": _public_exception_options(portfolio.exception),
                "content": {
                    "boundary": resolve_portfolio_copy("exception.boundary"),
                    "correct_label": resolve_portfolio_copy("exception.correct"),
                    "incorrect_label": resolve_portfolio_copy("exception.incorrect"),
                    "no_clear_insight": {
                        "eyebrow": resolve_portfolio_copy("exception.no_clear_insight.eyebrow"),
                        "headline": resolve_portfolio_copy("exception.no_clear_insight.headline"),
                        "body": resolve_portfolio_copy("exception.no_clear_insight.body"),
                        "boundary": resolve_portfolio_copy("exception.no_clear_insight.boundary"),
                    },
                },
            },
            {
                "id": "pool-evolution-question",
                "kind": "pool_evolution_question",
                "section": "hero_portfolio",
                "title": evolution_question,
                "body": resolve_portfolio_copy("evolution.question_body"),
                "evidence_keys": [],
                "portfolio_key": "evolution",
                "content": {
                    "locked_copy": resolve_portfolio_copy("evolution.locked"),
                    "payoff_heading": evolution_content["heading"],
                    "copy": evolution_content["body"],
                },
                "options": [
                    {"key": "more_experimental", "label": resolve_portfolio_copy("evolution.option_more_experimental")},
                    {"key": "same_style", "label": resolve_portfolio_copy("evolution.option_same_style")},
                    {"key": "different_kind", "label": resolve_portfolio_copy("evolution.option_different_kind")},
                    {"key": "not_changed", "label": resolve_portfolio_copy("evolution.option_not_changed")},
                ],
            },
            {
                "id": "hero-mirror",
                "kind": "hero_mirror_reveal",
                "section": "finale",
                "title": "Your Hero Mirror",
                "body": mirror_closed,
                "evidence_keys": [],
                "portfolio_key": "hero_mirror",
                "content": {
                    "closed": mirror_closed,
                    "available": resolve_portfolio_copy(
                        "hero_mirror.available",
                        hero=portfolio.hero_mirror.hero_name or "the selected hero",
                    ),
                    "qualifier": resolve_portfolio_copy("hero_mirror.qualifier"),
                    "guardrail": resolve_portfolio_copy(
                        "hero_mirror.guardrail",
                        hero=portfolio.hero_mirror.hero_name or "this hero",
                    ),
                },
            },
            {
                "id": "final-card",
                "kind": "final_card",
                "section": "finale",
                "title": final_copy["title"],
                "body": final_copy["body"],
                "evidence_keys": [],
            },
            {
                "id": "deep-dive",
                "kind": "deep_dive",
                "section": "finale",
                "title": deep_dive_copy["title"],
                "body": deep_dive_copy["body"],
                "evidence_keys": [],
            },
        ]
    )
    return pages


def _free_cost(cost_ledger: DataCostLedger | None) -> dict[str, Any]:
    if cost_ledger is None:
        raise ValueError("Free DNA summary-only assembly requires an actual cost ledger")
    raw = cost_ledger.as_dict()
    prohibited = {
        "detail_requests": int(raw.get("detail_requests", 0)),
        "parse_requests": int(raw.get("parse_requests", 0)),
        "parse_status_requests": int(raw.get("parse_status_requests", 0)),
    }
    if any(value != 0 for value in prohibited.values()):
        raise ValueError(f"Free DNA summary-only cost boundary violated: {prohibited}")
    return {
        "history_requests": int(raw.get("history_requests", 0)),
        "detail_requests": prohibited["detail_requests"],
        "parse_requests": prohibited["parse_requests"],
        "parse_status_requests": prohibited["parse_status_requests"],
        "cache_hits": int(raw.get("cache_hits", 0)),
        "estimated_cost_units": float(raw.get("estimated_cost_units", 0.0)),
    }


def _public_portfolio(portfolio: HeroPortfolioResult) -> dict[str, Any]:
    """Project Hero Portfolio choices without inviting guesses at no-clear states."""

    value = portfolio.as_dict(include_private_eligibility=False)
    exception = value["exception"]
    if exception["status"] == "no_clear_exception":
        exception["options"] = [
            option
            for option in exception["options"]
            if option.get("key") == "no_clear_exception"
        ] or [{
            "key": "no_clear_exception",
            "label": "No clear exception",
            "hero_id": None,
            "feedback": resolve_portfolio_copy(
                "exception.no_clear_feedback",
                selected="No clear exception",
            ),
        }]
    elif exception["status"] == "unavailable":
        exception["options"] = []
        exception["correct_option_key"] = None
    return value


def _public_exception_options(exception: HeroExceptionResult) -> list[dict[str, Any]]:
    if exception.status == "unavailable":
        return []
    if exception.status == "no_clear_exception":
        options = [
            option.as_dict()
            for option in exception.options
            if option.key == "no_clear_exception"
        ]
        return options or [{
            "key": "no_clear_exception",
            "label": "No clear exception",
            "hero_id": None,
            "feedback": resolve_portfolio_copy(
                "exception.no_clear_feedback",
                selected="No clear exception",
            ),
        }]
    return [option.as_dict() for option in exception.options]


def _date_bounds(analysis: DnaAnalysisResult) -> tuple[str | None, str | None]:
    if analysis.features.window_start is not None and analysis.features.window_end is not None:
        return (
            datetime.fromtimestamp(analysis.features.window_start, tz=UTC).isoformat(),
            datetime.fromtimestamp(analysis.features.window_end, tz=UTC).isoformat(),
        )
    timestamps = [item.started_at for item in analysis.matches if item.started_at is not None]
    if not timestamps:
        return None, None
    return (
        datetime.fromtimestamp(min(timestamps), tz=UTC).isoformat(),
        datetime.fromtimestamp(max(timestamps), tz=UTC).isoformat(),
    )


def _hero_taxonomy_coverage(analysis: DnaAnalysisResult) -> float:
    if not analysis.matches:
        return 0.0
    usable = analysis.features.hero_counts
    toolkit = next(
        (item for item in analysis.behavior.elements if item.key == "toolkit_breadth"),
        None,
    )
    if toolkit is not None and toolkit.coverage:
        return toolkit.coverage
    return len(usable) / max(len(analysis.matches), 1)


def _taxonomy_version(portfolio: HeroPortfolioResult) -> str:
    # The taxonomy is part of the portfolio calculation; keep the public value
    # stable even when no candidate clears an individual insight gate.
    del portfolio
    from app.heroes.taxonomy import TAXONOMY_VERSION

    return TAXONOMY_VERSION


def _evolution_content(variant: str | None) -> dict[str, str]:
    if not variant:
        return {
            "heading": resolve_portfolio_copy("evolution.unavailable_heading"),
            "body": resolve_portfolio_copy("evolution.unavailable"),
        }
    return resolve_evolution_copy(variant)


def _evolution_display_copy(variant: str | None) -> str | None:
    if not variant:
        return None
    content = resolve_evolution_copy(variant)
    return f"{content['heading']} {content['body']}"


def _pattern_action_copy(key: str) -> dict[str, str] | None:
    if key not in {
        "same_playbook",
        "comfort_edge",
        "versatile_core",
        "proven_flexibility",
        "controlled_presence",
        "presence_tax",
        "bounceback",
        "performance_slide",
        "session_fade",
        "session_rise",
    }:
        return None
    values = validate_copy_catalog()["story_templates"]["pattern_action"]
    return {name: resolve_story_copy("pattern_action", name) for name in values}


def _pattern_presentation_copy(payload: PatternPresentationPayload) -> dict[str, Any]:
    context = payload.recommendation_context or {}
    params: dict[str, str] = {}
    if payload.recommendation_id in {
        "P01_ADD_MISSING_FUNCTION",
        "P04_ADD_MISSING_FUNCTION",
    }:
        params["hero_name"] = str(context.get("hero_name") or "a reviewed bridge hero")
    return resolve_pattern_presentation_copy(
        payload.pattern_id,
        payload.outcome_id,
        recommendation_id=payload.recommendation_id,
        deep_dive_id=payload.deep_dive_id,
        params=params,
    )


assemble_free_dna_report_v5 = assemble_free_dna_report_v4

__all__ = ["REPORT_SCHEMA_VERSION", "assemble_free_dna_report_v4", "assemble_free_dna_report_v5"]
