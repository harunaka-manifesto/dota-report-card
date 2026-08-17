from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from app.analysis.budget import DataCostLedger
from app.behavior.evidence import public_receipt_value
from app.behavior.models import (
    ContextArchetypeResult,
    ElementResult,
    PatternResult,
)
from app.content.catalog import copy_version
from app.content.renderer import resolve_dimension_copy, resolve_page_copy
from app.dna.baselines import BASELINE_VERSION
from app.dna.pipeline import DNA_SCORING_VERSION, DnaAnalysisResult
from app.findings.behavior import BehaviorFinding, BehaviorStorySelection, select_behavior_story
from app.findings.conflicts import select_story_findings
from app.findings.models import FindingCandidate, StorySelection
from app.findings.ranking import RANKING_VERSION
from app.findings.registry import FINDING_VERSION
from app.findings.story import STORY_VERSION
from app.share.service import RENDERER_VERSION

REPORT_SCHEMA_VERSION_V2 = "free-dna-report-2.0.0"
REPORT_SCHEMA_VERSION = "free-dna-report-3.0.0"
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
    findings: Iterable[FindingCandidate] = (),
    story_selection: StorySelection | None = None,
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
    published_findings = tuple(
        item for item in findings if item.publication_status == "published"
    )
    selection = story_selection or select_story_findings(published_findings)
    public_findings = [_public_finding(item) for item in published_findings]
    finding_by_key = {item["key"]: item for item in public_findings}
    return {
        "schema_version": REPORT_SCHEMA_VERSION_V2,
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
            "findings": FINDING_VERSION,
            "finding_ranking": RANKING_VERSION,
            "story": STORY_VERSION,
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
        "findings": public_findings,
        "story": _story(selection, analysis, display_name, finding_by_key),
        "pages": _pages_v2(analysis, display_name, published_findings, selection),
        "shares": _shares_v2(analysis, display_name, eligible_matches, published_findings, selection),
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
                "Findings combine deterministic summary signals and retain the eight DNA dimensions as evidence.",
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
        "methodology_version": value.get("methodology_version", "dna-scoring-1.2.0"),
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
    # A profile name containing the internal account ID would reintroduce the
    # identifier into the public report/share boundary. It is safer to lose a
    # little display-name fidelity than to publish a raw identifier.
    return "Anonymous player" if account_id is not None and str(account_id) in candidate else candidate


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


def _pages_v2(
    analysis: DnaAnalysisResult,
    display_name: str,
    findings: tuple[FindingCandidate, ...],
    selection: StorySelection,
) -> list[dict[str, Any]]:
    def page(key: str, **params: str) -> dict[str, str]:
        return resolve_page_copy(key, **params)

    steam_input = page("steam_input")
    player_found = page("player_found", display_name=display_name)
    analysis_page = page("analysis")
    reveal = page("report_reveal")
    deep_dive = page("deep_dive")
    findings_by_key = {item.key: item for item in findings}
    pages: list[dict[str, Any]] = [
        {"id": "steam-input", "kind": "input", "section": "intro", **steam_input},
        {"id": "player-found", "kind": "player_found", "section": "intro", **player_found},
        {"id": "analysis", "kind": "analysis", "section": "intro", **analysis_page},
        {"id": "report-reveal", "kind": "reveal", "section": "intro", **reveal},
    ]
    for key in selection.ordered_finding_keys:
        finding = findings_by_key.get(key)
        if finding is None:
            continue
        pages.append({
            "id": f"finding-{finding.key}",
            "kind": "finding",
            "section": "findings",
            "title": finding.headline,
            "body": finding.body,
            "evidence_keys": [item.key for item in finding.evidence],
            "finding_key": finding.key,
        })
    experiment_key = selection.experiment_key
    experiment_finding = next(
        (
            item
            for item in findings
            if item.experiment is not None and item.experiment.key == experiment_key
        ),
        None,
    )
    if experiment_finding is not None and experiment_finding.experiment is not None:
        experiment = experiment_finding.experiment
        pages.append({
            "id": f"experiment-{experiment.key}",
            "kind": "experiment",
            "section": "findings",
            "title": experiment.title,
            "body": experiment.instruction,
            "evidence_keys": [item.key for item in experiment_finding.evidence],
            "finding_key": experiment_finding.key,
            "experiment_key": experiment.key,
        })
    thesis = findings_by_key.get(selection.thesis_key or "")
    pages.extend([
        {
            "id": "identity-card",
            "kind": "identity_card",
            "section": "finale",
            "title": analysis.archetype.label,
            "body": thesis.headline if thesis else f"{display_name}, this is your bounded Dota DNA read.",
            "evidence_keys": [item.key for item in thesis.evidence] if thesis else [],
            "finding_key": thesis.key if thesis else None,
        },
        {
            "id": "dna-xray",
            "kind": "dna_xray",
            "section": "dna",
            "title": "Your full DNA",
            "body": "All eight dimensions remain available as the evidence behind the findings.",
            "evidence_keys": [dimension.key for dimension in analysis.dimensions],
        },
        {"id": "deep-dive", "kind": "deep_dive", "section": "finale", **deep_dive},
    ])
    return pages


def _story(
    selection: StorySelection,
    analysis: DnaAnalysisResult,
    display_name: str,
    findings: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    page_ids = ["steam-input", "player-found", "analysis", "report-reveal"]
    page_ids.extend(f"finding-{key}" for key in selection.ordered_finding_keys if key in findings)
    if selection.experiment_key:
        page_ids.append(f"experiment-{selection.experiment_key}")
    page_ids.extend(["identity-card", "dna-xray", "deep-dive"])
    return {
        "version": STORY_VERSION,
        "thesis_key": selection.thesis_key,
        "strength_key": selection.strength_key,
        "contradiction_key": selection.contradiction_key,
        "edge_key": selection.edge_key,
        "leak_key": selection.leak_key,
        "experiment_key": selection.experiment_key,
        "ordered_pages": page_ids,
    }


def _public_finding(finding: FindingCandidate) -> dict[str, Any]:
    return {
        "key": finding.key,
        "kind": finding.kind,
        "headline": finding.headline,
        "body": finding.body,
        "interpretation": finding.interpretation,
        "confidence": finding.confidence,
        "receipts": [
            {
                "key": item.receipt_key,
                "label": item.receipt_label,
                "value": item.public_receipt,
                "context": item.family,
                "confidence": item.confidence,
            }
            for item in finding.evidence[:4]
        ],
        "related_dimensions": list(finding.related_dimensions),
        "related_heroes": list(finding.related_heroes),
        "experiment": _public_experiment(finding),
        "share_copy": finding.share_copy,
    }


def _public_experiment(finding: FindingCandidate) -> dict[str, Any] | None:
    if finding.experiment is None:
        return None
    experiment = finding.experiment
    return {
        "key": experiment.key,
        "title": experiment.title,
        "instruction": experiment.instruction,
        "hypothesis": experiment.hypothesis,
        "measurement": experiment.measurement,
        "window": experiment.window,
    }


def _shares_v2(
    analysis: DnaAnalysisResult,
    display_name: str,
    eligible_matches: int,
    findings: tuple[FindingCandidate, ...],
    selection: StorySelection,
) -> dict[str, Any]:
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
    public = {item.key: _public_finding(item) for item in findings}
    thesis = public.get(selection.thesis_key or "") or next(iter(public.values()), None)
    exposed = public.get(selection.contradiction_key or "") or public.get(selection.leak_key or "") or thesis
    strength = public.get(selection.strength_key or "") or thesis
    identity = {
        "finding_key": thesis.get("key") if thesis else None,
        "headline": thesis.get("headline") if thesis else analysis.archetype.label,
        "archetype": analysis.archetype.label,
        "receipts": [item["value"] for item in (thesis.get("receipts", []) if thesis else [])[:2]],
    }
    exposed_card = {
        "finding_key": exposed.get("key") if exposed else None,
        "headline": exposed.get("share_copy") or exposed.get("headline") if exposed else "Your Dota pattern",
        "archetype": analysis.archetype.label,
        "receipts": [item["value"] for item in (exposed.get("receipts", []) if exposed else [])[:2]],
    }
    strength_card = {
        "finding_key": strength.get("key") if strength else None,
        "headline": strength.get("share_copy") or strength.get("headline") if strength else "A supported Dota strength",
        "archetype": analysis.archetype.label,
        "receipts": [item["value"] for item in (strength.get("receipts", []) if strength else [])[:2]],
    }
    return {
        "identity": identity,
        "exposed": exposed_card,
        "strength": strength_card,
        # Keep aliases so older clients can continue to request a report card
        # while v2 clients use the finding-oriented cards above.
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


def assemble_free_dna_report_v3(
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
    findings: tuple[BehaviorFinding, ...] | list[BehaviorFinding] = (),
    story_selection: BehaviorStorySelection | None = None,
) -> dict[str, Any]:
    """Build the immutable v3 public contract from upstream behavior results."""

    behavior = analysis.behavior
    if behavior is None:
        raise ValueError("v3 report assembly requires BehaviorAnalysisResult")
    dates = [item.started_at for item in analysis.matches if item.started_at is not None]
    display_name = _public_display_name(profile.get("personaname") or profile.get("display_name"), account_id)
    avatar_url = _public_avatar_url(profile.get("avatarfull") or profile.get("avatar_url"), account_id)
    history_tier = "limited" if 30 <= eligible_matches < 60 else "normal"
    public_findings = [_public_behavior_finding(item) for item in findings]
    selection = story_selection or select_behavior_story(tuple(findings))
    pages = _pages_v3(analysis, display_name, tuple(findings), selection)
    public_elements = [_public_behavior_element(item) for item in behavior.elements]
    public_patterns = [
        _public_behavior_pattern(item)
        for item in behavior.patterns
        if item.status == "qualified"
    ]
    public_archetypes = [_public_archetype(item) for item in behavior.archetypes]
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
            "created_at": datetime.now(UTC).isoformat(),
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
            "findings": "free-findings-3.0.0",
            "finding_ranking": "free-finding-ranking-3.0.0",
            "story": "free-story-3.0.0",
            "copy": COPY_VERSION,
            "model": model_version,
            "template": template_version,
            "share_renderer": RENDERER_VERSION,
            "analysis_version_fingerprint": analysis_version_fingerprint,
            **behavior.versions.as_dict(),
        },
        "quality": {
            "overall_confidence": behavior.quality.overall_confidence,
            "history_tier": history_tier,
            "missing_data_flags": [item.key for item in behavior.elements if item.status == "unavailable"],
            "partial": bool(behavior.quality.warnings) or history_tier == "limited",
            "warnings": list(behavior.quality.warnings),
            "available_elements": behavior.quality.available_elements,
            "limited_elements": behavior.quality.limited_elements,
            "unavailable_elements": behavior.quality.unavailable_elements,
            "qualified_patterns": behavior.quality.qualified_patterns,
        },
        "dimensions": [item.as_dict() for item in behavior.dimensions],
        "elements": public_elements,
        "patterns": public_patterns,
        "archetypes": public_archetypes,
        "heroes": analysis.heroes.as_dict(),
        "findings": public_findings,
        "story": _story_v3(selection, pages),
        "pages": pages,
        "shares": _shares_v3(analysis, display_name, eligible_matches, tuple(findings), selection, public_archetypes),
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
                "Elements measure narrow observable tendencies; Patterns qualify relationships between them.",
                "Context Archetypes describe one style per context group. Unavailable evidence is not treated as neutral.",
            ],
        },
        "cost": _public_cost(cost_ledger),
    }


def _public_behavior_element(element: ElementResult) -> dict[str, Any]:
    value = element.as_dict(public=True)
    value.pop("raw_metrics", None)
    value["axis"] = {"left": element.axis_left, "right": element.axis_right}
    value["receipts"] = [
        {
            "key": receipt.key,
            "value": public_receipt_value(receipt),
            "unit": receipt.unit,
            "denominator": receipt.denominator,
            "coverage": receipt.coverage,
            "confidence_score": receipt.confidence_score,
            "comparison": receipt.comparison,
        }
        for receipt in element.evidence[:4]
    ]
    return value


def _public_behavior_pattern(pattern: PatternResult) -> dict[str, Any]:
    return {
        "key": pattern.key,
        "label": pattern.label,
        "kind": pattern.kind,
        "strength": pattern.strength,
        "confidence": pattern.confidence,
        "confidence_score": pattern.confidence_score,
        "element_keys": list(pattern.element_keys),
        "receipts": [
            {
                "key": receipt.key,
                "value": public_receipt_value(receipt),
                "unit": receipt.unit,
                "denominator": receipt.denominator,
                "coverage": receipt.coverage,
                "confidence_score": receipt.confidence_score,
                "comparison": receipt.comparison,
            }
            for receipt in pattern.evidence[:4]
        ],
        "confounders": list(pattern.confounders),
    }


def _public_archetype(archetype: ContextArchetypeResult) -> dict[str, Any]:
    return {
        "group_key": archetype.group_key,
        "group_label": archetype.group_label,
        "key": archetype.key,
        "label": archetype.label,
        "fit": archetype.fit,
        "confidence": archetype.confidence,
        "runner_up": dict(archetype.runner_up) if archetype.runner_up else None,
        "descriptors": [dict(item) for item in archetype.descriptors],
        "contributing_element_keys": [str(item.get("key")) for item in archetype.contributing_elements],
        "contributing_pattern_keys": list(archetype.contributing_patterns),
        "explanation_evidence": list(archetype.explanation_evidence),
        "classifier_version": archetype.classifier_version,
    }


def _public_behavior_finding(finding: BehaviorFinding) -> dict[str, Any]:
    return finding.as_dict()


def _pages_v3(
    analysis: DnaAnalysisResult,
    display_name: str,
    findings: tuple[BehaviorFinding, ...],
    selection: BehaviorStorySelection,
) -> list[dict[str, Any]]:
    finding_by_key = {item.key: item for item in findings}
    pages: list[dict[str, Any]] = [
        {"id": "report-reveal", "kind": "reveal", "section": "intro", "title": "Your Dota pattern, with the receipts.", "body": "A bounded summary-history read of the way your matches tend to look."},
        {"id": "model-summary", "kind": "summary", "section": "intro", "title": "The report has layers.", "body": "Elements measure one tendency. Patterns connect them. Archetypes keep the context honest."},
    ]
    for key in selection.ordered_finding_keys:
        finding = finding_by_key.get(key)
        if finding is None:
            continue
        pages.append({"id": f"finding-{key}", "kind": "finding", "section": "findings", "title": finding.headline, "body": finding.body, "evidence_keys": list(finding.supporting_element_keys), "finding_key": key})
        if finding.experiment is not None:
            pages.append({"id": f"experiment-{finding.experiment['key']}", "kind": "experiment", "section": "findings", "title": str(finding.experiment["title"]), "body": str(finding.experiment["instruction"]), "evidence_keys": list(finding.supporting_element_keys), "finding_key": key, "experiment_key": str(finding.experiment["key"])})
    pages.extend(
        [
            {"id": "archetypes", "kind": "archetypes", "section": "finale", "title": "Three contexts. Three useful angles.", "body": f"{display_name}, no single label gets to summarize the whole match history."},
            {"id": "dna-xray", "kind": "dna_xray", "section": "dna", "title": "The Elements underneath", "body": "A score is a position on an observable axis — not a grade and not a percentile."},
            {"id": "heroes", "kind": "heroes", "section": "heroes", "title": "The heroes that make it yours", "body": "Hero identity stays factual: recurrence, range, toolkit, and role context."},
            {"id": "deep-dive", "kind": "deep_dive", "section": "finale", "title": "See what drives it", "body": "Deep Analysis can inspect selected matches when you want the richer evidence behind a Free Pattern."},
        ]
    )
    return pages


def _story_v3(selection: BehaviorStorySelection, pages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "version": selection.story_version,
        "thesis_key": selection.thesis_key,
        "strongest_key": selection.strongest_key,
        "experiment_key": selection.experiment_key,
        "ordered_pages": [item["id"] for item in pages],
    }


def _shares_v3(
    analysis: DnaAnalysisResult,
    display_name: str,
    eligible_matches: int,
    findings: tuple[BehaviorFinding, ...],
    selection: BehaviorStorySelection,
    archetypes: list[dict[str, Any]],
) -> dict[str, Any]:
    public = {item.key: _public_behavior_finding(item) for item in findings}
    thesis = public.get(selection.thesis_key or "") or next(iter(public.values()), None)
    strongest = public.get(selection.strongest_key or "") or thesis
    pattern = thesis or strongest or {"key": None, "headline": "A Dota pattern worth keeping", "receipts": [], "archetype_group_keys": []}

    def card(item: dict[str, Any] | None, fallback: str) -> dict[str, Any]:
        return {
            "finding_key": item.get("key") if item else None,
            "headline": item.get("share_copy") or item.get("headline") if item else fallback,
            "archetype_groups": item.get("archetype_group_keys", []) if item else [],
            "receipts": [receipt["value"] for receipt in (item.get("receipts", []) if item else [])[:2]],
        }

    return {
        "identity": card(thesis, f"{display_name}'s Dota pattern"),
        "strongest": card(strongest, "A supported Dota signal"),
        "pattern": card(pattern, "A Dota pattern worth keeping"),
        "archetypes": archetypes,
        "privacy_defaults": {"show_name": True, "show_avatar": True, "show_raw_id": False},
    }
