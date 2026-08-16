from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.content.catalog import copy_version
from app.dna.baselines import BASELINE_VERSION
from app.dna.pipeline import DnaAnalysisResult

REPORT_SCHEMA_VERSION = "free-dna-report-1.0.0"
COPY_VERSION = copy_version()


def assemble_free_dna_report(
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
    legacy_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dimensions = [item.as_dict() for item in analysis.dimensions]
    available = [item for item in dimensions if item["score"] is not None and item["confidence_score"] >= 0.50]
    dates = [item.started_at for item in analysis.matches if item.started_at is not None]
    display_name = profile.get("personaname") or "Anonymous player"
    payload: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA_VERSION,
        # ``free_player_dna`` remains the wire-level compatibility value for
        # existing clients.  ``dna_report_variant`` and the schema version are
        # the new contract; the web dispatches on either field.
        "report_variant": "free_player_dna",
        "dna_report_variant": "free_dna_report",
        "legacy_report_variant": "free_player_dna",
        "noindex": True,
        "identity": {
            # Retained for server-side compatibility with the existing report
            # store; story/share contracts use account_id_masked only.
            "account_id": account_id,
            "account_id_masked": _mask_account_id(account_id),
            "personaname": display_name,
            "display_name": display_name,
            "avatarfull": profile.get("avatarfull"),
            "avatar_url": profile.get("avatarfull"),
            "profile_url": profile.get("profile_url"),
            "rank_tier": profile.get("rank_tier"),
        },
        "metadata": {
            "created_at": datetime.now(UTC).isoformat(),
            "data_from": datetime.fromtimestamp(min(dates), UTC).isoformat() if dates else None,
            "data_to": datetime.fromtimestamp(max(dates), UTC).isoformat() if dates else None,
            "processed_matches": processed_matches,
            "eligible_matches": eligible_matches,
            "history_limit": history_limit,
            "raw_payload_hash": raw_payload_hash,
        },
        "versions": {
            "eligibility": "summary-eligibility-1.0.0",
            "sessions": analysis.sessions.policy.version,
            "features": analysis.features.feature_version,
            "dna_scoring": "dna-scoring-1.0.0",
            "baselines": BASELINE_VERSION,
            "archetype": analysis.archetype.classifier_version,
            "hero_taxonomy": analysis.heroes.taxonomy_version,
            "recommendations": "hero-recommendations-1.0.0" if analysis.heroes.recommendations else None,
            "copy": COPY_VERSION,
            "model": model_version,
            "template": template_version,
            "share_renderer": "share-svg-1.0.0",
        },
        "quality": {
            "overall_confidence": analysis.overall_confidence,
            "missing_data_flags": [item["key"] for item in dimensions if item["status"] == "unavailable"],
            "partial": bool(analysis.warnings),
            "warnings": list(analysis.warnings),
        },
        "dimensions": dimensions,
        "archetype": analysis.archetype.as_dict(),
        "heroes": analysis.heroes.as_dict(),
        "pages": _pages(analysis, display_name),
        "shares": _shares(analysis, display_name, eligible_matches),
        "deep_dive": {
            "available": True,
            "cta_label": "See what drives it",
            # Deep Scan deliberately does not echo a raw account ID into a
            # link. The user can choose the player again on the input screen.
            "href": "/?mode=deep_scan",
            "copy": "Deep Dive can inspect a small set of matches in more detail.",
        },
        "dna": analysis.as_dict(),
        "evidence_scope": {
            "processed_matches": processed_matches,
            "eligible_matches": eligible_matches,
            "normalized_matches": len(analysis.matches),
            "excluded_matches": max(0, processed_matches - eligible_matches),
            "summary_parse_coverage": _summary_coverage(analysis),
            "replay_parse_coverage": 0.0,
            "replay_evidence_status": "not_requested",
            "replay_limitation": "Deep evidence was not requested for this Player DNA report.",
            "role_confidence": analysis.features.role_coverage,
            "role_status": "available" if analysis.features.role_coverage >= 0.40 else "limited",
            "published_insight_count": len(available),
            "suppressed_insight_count": len(dimensions) - len(available),
            "missing_feature_families": [item["key"] for item in dimensions if item["status"] == "unavailable"],
        },
        "cost": {"history_requests": 1, "detail_requests": 0, "parse_requests": 0, "requested_history_limit": history_limit},
    }
    if legacy_report:
        payload["legacy_summary"] = legacy_report
        # Keep the old cards/evidence available to older consumers while the
        # new variant is adopted.  New UI code reads only the fields above.
        payload.setdefault("sections", legacy_report.get("sections", {}))
        payload.setdefault("evidence_appendix", legacy_report.get("evidence_appendix", []))
        payload.setdefault("player_dna", legacy_report.get("player_dna", {}))
        payload.setdefault("deep_scan_legacy", legacy_report.get("deep_scan"))
    return payload


def _pages(analysis: DnaAnalysisResult, display_name: str) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = [
        {"id": "steam-input", "kind": "input", "section": "intro", "title": "What kind of Dota player are you?"},
        {"id": "player-found", "kind": "player_found", "section": "intro", "title": f"Found {display_name}."},
        {"id": "analysis", "kind": "analysis", "section": "intro", "title": "Reading your recent matches."},
        {"id": "report-reveal", "kind": "reveal", "section": "intro", "title": "We found your pattern."},
        {"id": "dna-intro", "kind": "section_intro", "section": "dna", "title": "Your Dota DNA", "body": "Eight signals that describe how your matches tend to look."},
    ]
    for dimension in analysis.dimensions:
        pages.append({
            "id": dimension.key,
            "kind": "dimension",
            "section": "dna",
            "title": _dimension_title(dimension.key),
            "body": _dimension_body(dimension),
            "evidence_keys": [item.key for item in dimension.evidence],
        })
    pages.extend([
        {"id": "archetype", "kind": "archetype", "section": "dna", "title": analysis.archetype.label, "body": "Your archetype is a synthesis of the signals that cleared their evidence gates."},
        {"id": "dna-summary", "kind": "summary", "section": "dna", "title": "The fingerprint", "body": "A compact view of the signals that stood out."},
        {"id": "heroes-intro", "kind": "section_intro", "section": "heroes", "title": "The heroes that make it yours", "body": "Familiarity, recurrence, and role fit shape this section."},
        {"id": "signature-hero", "kind": "signature_hero", "section": "heroes", "title": "Your Signature Hero", "body": analysis.heroes.signature.name if analysis.heroes.signature else "No signature hero cleared the stability gate."},
        {"id": "comfort-picks", "kind": "comfort", "section": "heroes", "title": "Comfort Picks", "body": "The heroes you keep returning to."},
        {"id": "hero-pattern", "kind": "hero_pattern", "section": "heroes", "title": "Your Hero Pattern", "body": analysis.heroes.patterns[0].get("label") if analysis.heroes.patterns else "Your comfort pool is still forming."},
        {"id": "hero-recommendations", "kind": "recommendations", "section": "heroes", "title": "Recommended expansion heroes", "body": "Taste adjacency, not a meta list."},
        {"id": "heroes-summary", "kind": "summary", "section": "heroes", "title": "The cast around your style"},
        {"id": "final-card", "kind": "final_card", "section": "finale", "title": display_name, "body": analysis.archetype.label},
        {"id": "deep-dive", "kind": "deep_dive", "section": "finale", "title": "See what drives it", "body": "A deeper read is available when you want to inspect the evidence."},
    ])
    # The inventory is 23 states, including the input/loading states so a
    # fixture payload can exercise the complete story without another schema.
    return pages


def _shares(analysis: DnaAnalysisResult, display_name: str, eligible_matches: int) -> dict[str, Any]:
    strong = [item.as_dict() for item in analysis.dimensions if item.score is not None and item.confidence_score >= 0.50]
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


def _dimension_title(key: str) -> str:
    return {
        "breadth": "How wide is your pool?",
        "role": "Your role is part of your identity.",
        "adaptability": "Does your play travel with you?",
        "activity": "How often are you in the action?",
        "orientation": "Do you finish or connect?",
        "resilience": "What changes after the last result?",
        "endurance": "What happens as the session stretches?",
        "rhythm": "What does a normal session look like?",
    }.get(key, key.replace("_", " ").title())


def _dimension_body(dimension: Any) -> str:
    if dimension.status == "unavailable":
        return "The signal is faint here because the history is missing a required field or sample."
    if dimension.status == "limited":
        return "The direction is visible, but more history would make it steadier."
    return dimension.label or "A readable signal from your history."


def _summary_coverage(analysis: DnaAnalysisResult) -> float:
    if not analysis.matches:
        return 0.0
    fields = ("hero_id", "started_at", "duration_seconds", "won", "side")
    return sum(sum(getattr(item, field) is not None for field in fields) / len(fields) for item in analysis.matches) / len(analysis.matches)


def _mask_account_id(account_id: int) -> str:
    text = str(account_id)
    return "••••••" + text[-3:]
