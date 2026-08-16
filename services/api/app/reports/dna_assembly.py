from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.analysis.budget import DataCostLedger
from app.content.catalog import copy_version
from app.content.renderer import resolve_dimension_copy, resolve_page_copy
from app.dna.baselines import BASELINE_VERSION
from app.dna.pipeline import DNA_SCORING_VERSION, DnaAnalysisResult
from app.share.service import RENDERER_VERSION

REPORT_SCHEMA_VERSION = "free-dna-report-1.0.0"
COPY_VERSION = copy_version()


def assemble_free_dna_report(
    *,
    account_id: int | None = None,
    profile: dict[str, Any],
    analysis: DnaAnalysisResult,
    processed_matches: int,
    eligible_matches: int,
    raw_payload_hash: str,
    history_limit: int,
    model_version: str,
    template_version: str,
    cost_ledger: DataCostLedger | None = None,
    analysis_version_fingerprint: str = "free-analysis-unknown",
) -> dict[str, Any]:
    """Build only the intentional frontend-facing Free DNA contract.

    ``account_id`` remains an internal call-site argument for compatibility,
    but it is never copied into this public object. Normalized rows, sessions,
    legacy summary cards, and Deep Scan payloads stay in internal memory or
    private evidence storage.
    """

    dimensions = [_public_dimension(item.as_dict()) for item in analysis.dimensions]
    dates = [item.started_at for item in analysis.matches if item.started_at is not None]
    display_name = _public_display_name(
        profile.get("personaname") or profile.get("display_name"), account_id
    )
    avatar_url = _public_avatar_url(
        profile.get("avatarfull") or profile.get("avatar_url"), account_id
    )
    history_tier = "limited" if 30 <= eligible_matches < 60 else "normal"
    created_at = datetime.now(UTC).isoformat()
    cost = _public_cost(cost_ledger)
    return {
        "schema_version": REPORT_SCHEMA_VERSION,
        "report_variant": "free_dna_report",
        "noindex": True,
        "identity": {
            "display_name": display_name,
            "avatar_url": avatar_url,
            "rank_tier": profile.get("rank_tier"),
        },
        "metadata": {
            "created_at": created_at,
            "expires_at": None,
            "data_from": datetime.fromtimestamp(min(dates), UTC).isoformat() if dates else None,
            "data_to": datetime.fromtimestamp(max(dates), UTC).isoformat() if dates else None,
            "processed_matches": max(0, processed_matches),
            "eligible_matches": max(0, eligible_matches),
            "history_limit": max(1, min(500, history_limit)),
            "raw_history_hash": raw_payload_hash,
            "history_tier": history_tier,
        },
        "versions": {
            "eligibility": "summary-eligibility-1.1.0",
            "sessions": analysis.sessions.policy.version,
            "features": analysis.features.feature_version,
            "dna_scoring": DNA_SCORING_VERSION,
            "baselines": BASELINE_VERSION,
            "archetype": analysis.archetype.classifier_version,
            "hero_identity": analysis.heroes.identity_version,
            "hero_taxonomy": analysis.heroes.taxonomy_version or "unavailable",
            "recommendations": "hero-recommendations-1.1.0",
            "copy": COPY_VERSION,
            "model": model_version,
            "template": template_version,
            "share_renderer": RENDERER_VERSION,
            "analysis_version_fingerprint": analysis_version_fingerprint,
        },
        "quality": {
            "overall_confidence": analysis.overall_confidence,
            "history_tier": history_tier,
            "missing_data_flags": [item["key"] for item in dimensions if item["status"] == "unavailable"],
            "partial": bool(analysis.warnings) or history_tier == "limited",
            "warnings": list(analysis.warnings),
        },
        "dimensions": dimensions,
        "archetype": analysis.archetype.as_dict(),
        "heroes": analysis.heroes.as_dict(),
        "pages": _pages(analysis, display_name),
        "shares": _shares(analysis, display_name, eligible_matches),
        "deep_dive": {
            "available": True,
            "cta_label": resolve_page_copy("deep_dive")["title"],
            "href": "/?mode=deep_scan",
            "copy": resolve_page_copy("deep_dive")["body"],
        },
        "methodology": {
            "free_summary_only": True,
            "session_gap_minutes": analysis.sessions.policy.gap_minutes,
            "session_policy_version": analysis.sessions.policy.version,
            "notes": [
                "One bounded player-history read was used for this report.",
                "No match-detail reads or replay parses were requested.",
            ],
        },
        "cost": cost,
    }


def _public_dimension(value: dict[str, Any]) -> dict[str, Any]:
    evidence = [
        {
            "key": item.get("key", ""),
            "value": item.get("value"),
            "unit": item.get("unit", ""),
            "denominator": max(0, int(item.get("denominator", 0) or 0)),
        }
        for item in value.get("evidence", [])
    ]
    resolved_copy = resolve_dimension_copy(value["key"], value["status"])
    return {
        "key": value["key"],
        "status": value["status"],
        "score": value.get("score"),
        "centered_score": value.get("centered_score"),
        "label": value.get("label"),
        "confidence": value.get("confidence", "unavailable"),
        "confidence_score": value.get("confidence_score", 0.0),
        "sample_size": value.get("sample_size", 0),
        "effective_sample_size": value.get("effective_sample_size", 0.0),
        "coverage": value.get("coverage", 0.0),
        "evidence": evidence,
        "confounders": list(value.get("confounders", [])),
        "missing_reasons": list(value.get("missing_reasons", [])),
        "copy": {
            key: resolved_copy[key]
            for key in (
                "headline_key", "receipt_key", "receipt_params", "left_label", "right_label"
            )
        },
        "methodology_version": value.get("methodology_version", "dna-scoring-1.1.0"),
        "descriptor_eligible": bool(value.get("descriptor_eligible", True)),
    }


def _public_cost(ledger: DataCostLedger | None) -> dict[str, Any]:
    if ledger is None:
        return {
            "history_requests": 0,
            "detail_requests": 0,
            "parse_requests": 0,
            "parse_status_requests": 0,
            "cache_hits": 0,
            "estimated_cost_units": 0.0,
        }
    value = ledger.as_dict()
    return {
        "history_requests": int(value["history_requests"]),
        "detail_requests": 0,
        "parse_requests": 0,
        "parse_status_requests": int(value["parse_status_requests"]),
        "cache_hits": int(value["cache_hits"]),
        "estimated_cost_units": float(value["estimated_cost_units"]),
    }


def _public_display_name(value: Any, account_id: int | None) -> str:
    candidate = str(value or "Anonymous player").strip()
    # A profile name that is exactly the internal account ID is not useful
    # identity copy and would reintroduce the identifier into the public
    # report/share boundary.
    return "Anonymous player" if account_id is not None and candidate == str(account_id) else candidate


def _public_avatar_url(value: Any, account_id: int | None) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or parsed.hostname not in {
        "steamcdn-a.akamaihd.net",
        "avatars.akamai.steamstatic.com",
    }:
        return None
    if parsed.query or parsed.fragment or (account_id is not None and str(account_id) in parsed.path):
        return None
    return value


def _pages(analysis: DnaAnalysisResult, display_name: str) -> list[dict[str, Any]]:
    def page(key: str, **params: str) -> dict[str, str]:
        return resolve_page_copy(key, **params)

    steam_input = page("steam_input")
    player_found = page("player_found", display_name=display_name)
    analysis_page = page("analysis")
    reveal = page("report_reveal")
    dna_intro = page("dna_intro")
    dna_summary = page("dna_summary")
    archetype_page = page("archetype")
    heroes_intro = page("heroes_intro")
    signature = page("signature_hero")
    comfort = page("comfort_picks")
    pattern = page("hero_pattern")
    recommendations = page("hero_recommendations")
    heroes_summary = page("heroes_summary")
    final = page("final_card")
    deep_dive = page("deep_dive")
    pages: list[dict[str, Any]] = [
        {"id": "steam-input", "kind": "input", "section": "intro", **steam_input},
        {"id": "player-found", "kind": "player_found", "section": "intro", **player_found},
        {"id": "analysis", "kind": "analysis", "section": "intro", **analysis_page},
        {"id": "report-reveal", "kind": "reveal", "section": "intro", **reveal},
        {"id": "dna-intro", "kind": "section_intro", "section": "dna", **dna_intro},
    ]
    for dimension in analysis.dimensions:
        dimension_copy = resolve_dimension_copy(dimension.key, dimension.status)
        pages.append({
            "id": dimension.key,
            "kind": "dimension",
            "section": "dna",
            "title": dimension_copy["headline"],
            "body": dimension_copy["body"],
            "evidence_keys": [item.key for item in dimension.evidence],
        })
    pages.extend([
        {"id": "archetype", "kind": "archetype", "section": "dna", "title": analysis.archetype.label, "body": archetype_page["body"]},
        {"id": "dna-summary", "kind": "summary", "section": "dna", **dna_summary},
        {"id": "heroes-intro", "kind": "section_intro", "section": "heroes", **heroes_intro},
        {"id": "signature-hero", "kind": "signature_hero", "section": "heroes", **signature},
        {"id": "comfort-picks", "kind": "comfort", "section": "heroes", **comfort},
        {"id": "hero-pattern", "kind": "hero_pattern", "section": "heroes", **pattern, "body": analysis.heroes.patterns[0].get("label") if analysis.heroes.patterns else pattern["body"]},
        {"id": "hero-recommendations", "kind": "recommendations", "section": "heroes", **recommendations},
        {"id": "heroes-summary", "kind": "summary", "section": "heroes", **heroes_summary},
        {"id": "final-card", "kind": "final_card", "section": "finale", "title": final["title"], "body": final["body"]},
        {"id": "deep-dive", "kind": "deep_dive", "section": "finale", **deep_dive},
    ])
    return pages


def _shares(analysis: DnaAnalysisResult, display_name: str, eligible_matches: int) -> dict[str, Any]:
    strong = [
        {
            "key": item.key,
            "label": item.label,
            "score": item.score,
            "centered_score": item.centered_score,
            "confidence": item.confidence,
        }
        for item in analysis.dimensions
        if item.score is not None and item.confidence_score >= 0.50
    ]
    common = {
        "archetype": analysis.archetype.label,
        "descriptors": list(analysis.archetype.descriptors),
        "match_count": eligible_matches,
    }
    return {
        "dna": {**common, "spectra": strong[:3]},
        "heroes": {
            "signature": analysis.heroes.signature.as_dict() if analysis.heroes.signature else None,
            "comfort": [item.as_dict() for item in analysis.heroes.comfort_picks[:3]],
            "pattern": analysis.heroes.patterns[0] if analysis.heroes.patterns else None,
            "recommendations": list(analysis.heroes.recommendations[:3]),
        },
        "final": {
            **common,
            "display_name": display_name,
            "signature": analysis.heroes.signature.name if analysis.heroes.signature else None,
            "pattern": analysis.heroes.patterns[0].get("label") if analysis.heroes.patterns else None,
            "rhythm": next((item.label for item in analysis.dimensions if item.key == "rhythm"), None),
        },
        "privacy_defaults": {"show_name": True, "show_avatar": True, "show_raw_id": False},
    }
