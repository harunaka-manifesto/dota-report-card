"""Public v4 report projection for Elements, Patterns, and Hero Portfolio."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.analysis.budget import DataCostLedger
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
    resolve_page_copy,
    resolve_pattern_copy,
    resolve_portfolio_copy,
    resolve_story_copy,
    validate_copy_catalog,
)
from app.dna.pipeline import DnaAnalysisResult
from app.hero_portfolio.config import PORTFOLIO_CONFIG_VERSION
from app.hero_portfolio.models import HeroPortfolioResult
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
from app.share.service import RENDERER_VERSION

REPORT_SCHEMA_VERSION = "free-dna-report-4.0.0"
REPORT_STORY_VERSION = "free-story-4.2.0"


def assemble_free_dna_report_v4(
    *,
    account_id: int,
    profile: dict[str, Any],
    analysis: DnaAnalysisResult,
    processed_matches: int,
    eligible_matches: int,
    raw_payload_hash: str,
    history_limit: int,
    model_version: str,
    template_version: str,
    cost_ledger: DataCostLedger | None,
    analysis_version_fingerprint: str,
) -> dict[str, Any]:
    """Assemble one immutable, privacy-safe v4 snapshot.

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
    pages = _story_pages(
        element_highlights=element_highlights,
        pattern_highlights=pattern_highlights,
        element_map=element_map,
        pattern_map=pattern_map,
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
        "pattern_ranking": PATTERN_RANKING_VERSION,
        "pattern_actions": PATTERN_ACTIONS_VERSION,
        "hero_taxonomy": _taxonomy_version(portfolio),
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
            "pool_direction": _evolution_copy(portfolio.evolution.variant),
        },
        "hero_mirror": (
            {"hero_id": hero_mirror.hero_id, "hero_name": hero_mirror.hero_name}
            if hero_mirror.hero_id is not None and hero_mirror.hero_name is not None
            else None
        ),
    }
    data_from, data_to = _date_bounds(analysis)
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
            "created_at": datetime.now(UTC).isoformat(),
            "expires_at": None,
            "data_from": data_from,
            "data_to": data_to,
            "processed_matches": max(0, processed_matches),
            "eligible_matches": max(0, eligible_matches),
            "history_limit": max(1, min(500, history_limit)),
            "raw_history_hash": raw_payload_hash,
            "history_tier": analysis.history_tier,
        },
        "versions": versions,
        "quality": quality,
        "elements": [item.as_dict(public=True) for item in behavior.elements],
        "patterns": [item.as_dict(public=True) for item in behavior.patterns],
        "highlights": {
            "element_keys": [item.element_key for item in element_highlights],
            "pattern_keys": [item.key for item in pattern_highlights],
        },
        "hero_portfolio": portfolio.as_dict(include_private_eligibility=False),
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
                "Hero Portfolio uses established hero history and a reviewed versioned taxonomy.",
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
    portfolio: HeroPortfolioResult,
) -> list[dict[str, Any]]:
    element_scan_copy = resolve_page_copy("element_scan")
    final_copy = resolve_page_copy("final_card")
    deep_dive_copy = resolve_page_copy("deep_dive")
    common_question = resolve_portfolio_copy("common_thread.question")
    exception_question = resolve_portfolio_copy("exception.question")
    evolution_question = resolve_portfolio_copy("evolution.question")
    evolution_body = _evolution_copy(portfolio.evolution.variant) or resolve_portfolio_copy("evolution.unavailable")
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
                },
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
                "options": [option.as_dict() for option in portfolio.exception.options],
                "content": {
                    "boundary": resolve_portfolio_copy("exception.boundary"),
                    "correct_label": resolve_portfolio_copy("exception.correct"),
                    "incorrect_label": resolve_portfolio_copy("exception.incorrect"),
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
                "content": {"locked_copy": resolve_portfolio_copy("evolution.locked")},
                "options": [
                    {"key": "more_experimental", "label": resolve_portfolio_copy("evolution.option_more_experimental")},
                    {"key": "same_style", "label": resolve_portfolio_copy("evolution.option_same_style")},
                    {"key": "different_kind", "label": resolve_portfolio_copy("evolution.option_different_kind")},
                    {"key": "not_changed", "label": resolve_portfolio_copy("evolution.option_not_changed")},
                ],
            },
            {
                "id": "pool-evolution-reveal",
                "kind": "pool_evolution_reveal",
                "section": "hero_portfolio",
                "title": "Pool Evolution",
                "body": evolution_body,
                "evidence_keys": [],
                "portfolio_key": "evolution",
                "content": {
                    "copy": evolution_body,
                    "locked_copy": resolve_portfolio_copy("evolution.locked"),
                },
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


def _date_bounds(analysis: DnaAnalysisResult) -> tuple[str | None, str | None]:
    timestamps = [item.started_at for item in analysis.matches if item.started_at is not None]
    if not timestamps:
        return None, None
    return (
        datetime.fromtimestamp(min(timestamps), tz=UTC).isoformat(),
        datetime.fromtimestamp(max(timestamps), tz=UTC).isoformat(),
    )


def _taxonomy_version(portfolio: HeroPortfolioResult) -> str:
    # The taxonomy is part of the portfolio calculation; keep the public value
    # stable even when no candidate clears an individual insight gate.
    del portfolio
    from app.heroes.taxonomy import TAXONOMY_VERSION

    return TAXONOMY_VERSION


def _evolution_copy(variant: str | None) -> str | None:
    if not variant:
        return None
    return resolve_portfolio_copy(f"evolution.{variant}")


def _pattern_action_copy(key: str) -> dict[str, str] | None:
    if key not in {"same_playbook", "comfort_edge"}:
        return None
    values = validate_copy_catalog()["story_templates"]["pattern_action"]
    return {name: resolve_story_copy("pattern_action", name) for name in values}


__all__ = ["REPORT_SCHEMA_VERSION", "assemble_free_dna_report_v4"]
