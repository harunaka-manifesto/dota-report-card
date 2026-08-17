"""Public v4 report projection for Elements, Patterns, and Hero Portfolio."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.analysis.budget import DataCostLedger
from app.behavior.ranking import rank_element_highlights, rank_pattern_highlights
from app.content.catalog import copy_version
from app.content.renderer import resolve_page_copy, resolve_portfolio_copy
from app.dna.pipeline import DnaAnalysisResult
from app.hero_portfolio.models import HeroPortfolioResult
from app.hero_portfolio.version import HERO_MIRROR_VERSION
from app.share.service import RENDERER_VERSION

REPORT_SCHEMA_VERSION = "free-dna-report-4.0.0"
REPORT_STORY_VERSION = "free-story-4.0.0"


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
    element_highlights = rank_element_highlights(behavior.elements)
    pattern_highlights = rank_pattern_highlights(behavior.patterns)
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
        "pattern_ranking": "free-pattern-ranking-4.0.0",
        "hero_taxonomy": _taxonomy_version(portfolio),
        "hero_portfolio": portfolio.version,
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
            "pool_direction": portfolio.evolution.variant,
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
    mirror_closed = resolve_portfolio_copy("hero_mirror.closed")
    pages: list[dict[str, Any]] = [
        {
            "id": "element-scan",
            "kind": "element_scan",
            "section": "elements",
            "title": element_scan_copy["title"],
            "body": element_scan_copy["body"] + " The strongest three get a closer look next.",
            "evidence_keys": list(element_map),
        }
    ]
    for highlight in element_highlights:
        element = element_map[highlight.element_key]
        pages.append(
            {
                "id": f"element-{element.key}",
                "kind": "element_highlight",
                "section": "elements",
                "title": element.label,
                "body": f"{element.zone or 'Observed signal'} · {highlight.display_reason}.",
                "evidence_keys": [element.key],
                "element_key": element.key,
            }
        )
    for pattern in pattern_highlights:
        pages.append(
            {
                "id": f"pattern-{pattern.key}",
                "kind": "pattern_highlight",
                "section": "patterns",
                "title": pattern.label,
                "body": pattern_map[pattern.key].as_dict(public=True).get("direction") or "A qualified relationship between Elements.",
                "evidence_keys": list(pattern.element_keys),
                "pattern_key": pattern.key,
            }
        )
    pages.extend(
        [
            {
                "id": "hero-common-thread",
                "kind": "hero_common_thread_question",
                "section": "hero_portfolio",
                "title": common_question,
                "body": "Make your guess, then compare it with the recurring functional trait across your established pool.",
                "evidence_keys": [],
                "portfolio_key": "common_thread",
            },
            {
                "id": "hero-exception",
                "kind": "hero_exception_question",
                "section": "hero_portfolio",
                "title": exception_question,
                "body": "Different does not mean better or worse. Pick the functional outlier you expect.",
                "evidence_keys": [],
                "portfolio_key": "exception",
            },
            {
                "id": "pool-evolution-question",
                "kind": "pool_evolution_question",
                "section": "hero_portfolio",
                "title": evolution_question,
                "body": "Choose the description that feels closest. This is a self-assessment, not a score.",
                "evidence_keys": [],
                "portfolio_key": "evolution",
                "options": [
                    {"key": "more_experimental", "label": "I’ve become more experimental"},
                    {"key": "same_style", "label": "My heroes changed, but my style didn’t"},
                    {"key": "different_kind", "label": "I’ve shifted toward a different kind of hero"},
                    {"key": "not_changed", "label": "It hasn’t changed much"},
                ],
            },
            {
                "id": "pool-evolution-reveal",
                "kind": "pool_evolution_reveal",
                "section": "hero_portfolio",
                "title": "Pool Evolution",
                "body": portfolio.evolution.variant or "The comparison is not available yet.",
                "evidence_keys": [],
                "portfolio_key": "evolution",
            },
            {
                "id": "hero-mirror",
                "kind": "hero_mirror_reveal",
                "section": "finale",
                "title": "Your Hero Mirror",
                "body": mirror_closed,
                "evidence_keys": [],
                "portfolio_key": "hero_mirror",
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
    raw = cost_ledger.as_dict() if cost_ledger else {}
    return {
        "history_requests": int(raw.get("history_requests", 0)),
        "detail_requests": 0,
        "parse_requests": 0,
        "parse_status_requests": 0,
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


__all__ = ["REPORT_SCHEMA_VERSION", "assemble_free_dna_report_v4"]
