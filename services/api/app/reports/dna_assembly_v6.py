"""Public projection for the summary-only Free DNA v6 analytical core."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from app.analysis.budget import DataCostLedger
from app.dna.pipeline import DnaAnalysisResult
from app.player_analysis_v6 import analyze_free_dna_v6
from app.player_analysis_v6.baselines import BaselineResolver
from app.player_analysis_v6.constants import (
    BASELINE_VERSION,
    BOOTSTRAP_VERSION,
    CLAIM_VERSION,
    DIAGNOSTICS_VERSION,
    ELEMENTS_VERSION,
    EXPRESSION_VERSION,
    FINDINGS_VERSION,
    INTERACTION_VERSION,
    REPORT_VERSION,
    SEMANTIC_COPY_VERSION,
    SHARE_VERSION,
    STORY_VERSION,
    THRESHOLDS_VERSION,
)
from app.player_analysis_v6.thresholds import MetricThreshold

REPORT_SCHEMA_VERSION_V6 = REPORT_VERSION

_PUBLIC_STORY_IDS = (
    "self-estimate",
    "identity-reveal",
    "pool-evolution",
    "combat-expression",
    "strongest-finding",
    "secondary-finding",
    "recommendation",
    "hero-mirror",
    "deep-diagnostic",
)


def assemble_free_dna_report_v6(
    *,
    account_id: int,
    profile: dict[str, Any],
    analysis: DnaAnalysisResult | Sequence[Any],
    processed_matches: int,
    eligible_matches: int,
    raw_payload_hash: str,
    history_limit: int | None,
    model_version: str,
    template_version: str,
    cost_ledger: DataCostLedger | None,
    analysis_version_fingerprint: str,
    baseline_resolver: BaselineResolver | None = None,
    thresholds: Mapping[str, MetricThreshold] | None = None,
    completed_sessions: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Assemble one immutable v6 snapshot without altering v5 projection code."""

    del account_id  # Raw player identifiers never cross the public report boundary.
    generated_at = datetime.now(UTC).isoformat()
    seed = int(raw_payload_hash[:16], 16) if raw_payload_hash else 0
    history_tier = "limited" if eligible_matches < 60 else "normal"
    core = analyze_free_dna_v6(
        analysis,
        profile=profile,
        metadata={"history_tier": history_tier},
        seed=seed,
        baseline_resolver=baseline_resolver,
        thresholds=thresholds,
        completed_sessions=completed_sessions,
    )
    public = core.as_dict()
    elements = [_element(item) for item in core.elements]
    findings = [_finding(item, limited=history_tier == "limited") for item in core.findings]
    evidence_refs = {
        ref for item in [*elements, *findings] for ref in item.get("evidence_refs", [])
    }
    identity_refs = [ref for ref in core.identity.evidence_refs if ref in evidence_refs]
    data_from, data_to = _date_bounds(analysis)
    pages = [
        {
            "id": public_id,
            "kind": beat.key,
            "observed": dict(beat.observed),
            "content": {
                "title": beat.title,
                "prompt": beat.prompt,
                "interaction": beat.interaction,
                "observed": dict(beat.observed),
            },
            "title": beat.title,
            "prompt": beat.prompt,
            "body": beat.prompt,
            "options": [dict(option) for option in beat.options],
            "evidence_refs": [ref for ref in beat.evidence_refs if ref in evidence_refs],
            "available": beat.available,
            "skippable": beat.skippable,
        }
        for public_id, beat in zip(_PUBLIC_STORY_IDS, core.story, strict=True)
    ]
    return {
        "report_id": None,
        "schema_version": REPORT_VERSION,
        "report_variant": "free_dna_report",
        "noindex": True,
        "identity": {
            "display_name": str(profile.get("personaname") or "Anonymous player"),
            "avatar_url": profile.get("avatarfull"),
        },
        "metadata": {
            "created_at": generated_at,
            "expires_at": None,
            "data_from": data_from,
            "data_to": data_to,
            "processed_matches": max(0, processed_matches),
            "eligible_matches": max(30, eligible_matches),
            "history_limit": history_limit,
            "raw_history_hash": raw_payload_hash,
            "history_tier": history_tier,
        },
        "versions": {
            "elements": ELEMENTS_VERSION,
            "findings": FINDINGS_VERSION,
            "expression": EXPRESSION_VERSION,
            "statistics": BOOTSTRAP_VERSION,
            "context_baseline": BASELINE_VERSION,
            "thresholds": THRESHOLDS_VERSION,
            "claims": CLAIM_VERSION,
            "story": STORY_VERSION,
            "copy": SEMANTIC_COPY_VERSION,
            "deep_diagnostics": DIAGNOSTICS_VERSION,
            "share_renderer": SHARE_VERSION,
            "interactions": INTERACTION_VERSION,
            "model": model_version,
            "template": template_version,
            "analysis_version_fingerprint": analysis_version_fingerprint,
        },
        "reproducibility": {
            "generated_at": generated_at,
            "input_snapshot_hash": raw_payload_hash,
            "window_start": data_from,
            "window_end": data_to,
            "raw_match_count": max(0, processed_matches),
            "usable_match_count": max(30, eligible_matches),
            "independent_session_count": int(
                public.get("quality", {}).get("independent_session_count", 0)
            ),
            "bootstrap_iterations": int(
                public.get("reproducibility", {}).get("bootstrap_iterations", 2_000)
            ),
            "bootstrap_seed": str(seed),
            "session_gap_minutes": getattr(getattr(getattr(analysis, "sessions", None), "policy", None), "gap_minutes", 90),
            "baseline_artifact": BASELINE_VERSION,
            "threshold_artifact": THRESHOLDS_VERSION,
        },
        "quality": _quality(core, history_tier, analysis),
        "elements": elements,
        "findings": findings,
        "identity_summary": {
            "headline": core.identity.headline,
            "supporting_lines": list(core.identity.supporting_lines[:2]),
            "evidence_refs": identity_refs,
            "confidence": core.identity.confidence,
        },
        "hero_portfolio": public.get("hero_portfolio", {}),
        "diagnostic_questions": [
            {
                "id": item.question_id,
                "prompt": item.prompt,
                "finding_family": item.family,
                "diagnostic_question_id": item.question_id,
                "version": item.version,
                "statement": item.statement or item.prompt,
                "context": dict(item.context),
                "primary_hypothesis": dict(item.primary_hypothesis),
                "secondary_hypothesis": dict(item.secondary_hypothesis) if item.secondary_hypothesis is not None else None,
                "required_summary_metrics": list(item.required_summary_metrics),
                "required_detail_metrics": list(item.required_detail_metrics),
                "required_parse_metrics": list(item.required_parse_metrics),
                "secondary_reuse_fraction": item.secondary_reuse_fraction,
                "options": [dict(option) for option in item.options],
                "observed": dict(item.observed),
                "available": item.available,
                "skippable": item.skippable,
                "question_spec": dict(item.question_spec),
                "evidence_refs": [ref for ref in item.evidence_refs if ref in evidence_refs],
                "confidence": item.confidence,
            }
            for item in core.diagnostic_questions
            if item.offered and item.confidence in {"moderate", "high"}
        ][:3],
        "story": {"version": STORY_VERSION, "ordered_beats": list(_PUBLIC_STORY_IDS)},
        "pages": pages,
        "share_candidates": [_share_candidate(item) for item in core.share_candidates][:3],
        "methodology": {
            "free_summary_only": True,
            "population_window_days": 365,
            "weighting": "equal",
            "lane_context": list(public.get("methodology", {}).get("lane_context", [])),
            "notes": [
                "Stable identity uses equal weighting; recency is appendix-only.",
                "Intervals resample independent sessions rather than match rows.",
                "Lane context is literal and is not an inferred position label.",
            ],
        },
        "cost": _free_cost(cost_ledger),
    }


def _element(item: Any) -> dict[str, Any]:
    estimate = item.estimate
    return {
        "key": item.key,
        "label": item.label,
        "status": _measurement_status(estimate.status),
        "estimate": estimate.value,
        "unit": estimate.unit,
        "interval": _interval(estimate.interval),
        "zone": estimate.zone,
        "direction": estimate.direction,
        "bootstrap_stability": estimate.stability,
        "sample_size": estimate.sample_size,
        "independent_session_count": estimate.independent_sessions,
        "coverage": estimate.coverage,
        "confidence": estimate.confidence,
        "evidence_refs": list(item.evidence_refs or estimate.evidence_refs),
        "limitations": list(estimate.limitations),
        "supported_claims": list(estimate.supported_claims),
        "forbidden_claims": list(estimate.forbidden_claims),
    }


def _finding(item: Any, *, limited: bool) -> dict[str, Any]:
    estimate = item.estimate
    evidence_refs = list(item.evidence_refs)
    signal_keys = [signal.key for signal in item.evidence]
    recommendation = None if limited else item.recommendation if isinstance(item.recommendation, dict) else None
    return {
        "key": item.family,
        "label": item.family.replace("_", " ").title(),
        "family": item.family,
        "status": _measurement_status(item.status),
        "estimate": estimate.value if estimate else None,
        "unit": estimate.unit if estimate else "mixed signals",
        "interval": _interval(estimate.interval if estimate else None),
        "zone": estimate.zone if estimate else None,
        "direction": item.direction,
        "bootstrap_stability": estimate.stability if estimate else item.confidence_score,
        "sample_size": estimate.sample_size if estimate else max(
            (signal.sample_size for signal in item.evidence), default=0
        ),
        "independent_session_count": estimate.independent_sessions if estimate else max(
            (signal.independent_sessions for signal in item.evidence), default=0
        ),
        "coverage": estimate.coverage if estimate else min(
            (signal.coverage for signal in item.evidence), default=0.0
        ),
        "confidence": item.confidence,
        "evidence_refs": evidence_refs,
        "limitations": list(item.limitations),
        "supported_claims": [item.claim] if item.claim else [],
        "forbidden_claims": [],
        "published": bool(item.published),
        "signal_keys": signal_keys,
        "outcome_key": getattr(item, "outcome_key", None),
        "raw_p_value": item.raw_p_value if item.raw_p_value is not None else 1.0,
        "adjusted_q_value": item.adjusted_q_value if item.adjusted_q_value is not None else 1.0,
        "claim_contract": {
            "claim": item.claim,
            "evidence": item.evidence_text,
            "interpretation": item.interpretation,
            "recommendation": recommendation,
            "copy_version": "free-dna-semantic-copy-6.0.0",
        },
    }


def _share_candidate(item: Any) -> dict[str, Any]:
    kind = {
        "identity": "dynamic_identity",
        "finding": "strongest_finding",
        "hero_mirror": "hero_mirror",
    }[item.kind]
    return {
        "id": item.candidate_id,
        "kind": kind,
        "eligible": item.eligible,
        "confidence": item.confidence,
        "evidence_refs": list(item.evidence_refs),
        "blocking_confounders": list(item.blocking_reasons),
        "contains_recommendation": False,
        "early_signal": False,
        "payload": {"title": item.title, "reason": item.reason},
    }


def _measurement_status(status: str) -> str:
    return {
        "qualified": "available",
        "limited": "descriptive",
        "available": "available",
        "suppressed": "suppressed",
        "unavailable": "unavailable",
    }.get(status, "unavailable")


def _interval(value: tuple[float, float] | None) -> dict[str, float] | None:
    if value is None:
        return None
    return {"lower": value[0], "upper": value[1], "level": 0.95}


def _quality(core: Any, history_tier: str, analysis: Any) -> dict[str, Any]:
    available = sum(item.status == "available" for item in core.elements)
    published = sum(item.published for item in core.findings)
    confidence_order = {"unavailable": 0, "descriptive": 1, "moderate": 2, "high": 3}
    overall = max(
        (item.confidence for item in core.elements),
        key=lambda item: confidence_order.get(item, 0),
        default="unavailable",
    )
    return {
        "overall_confidence": overall,
        "history_tier": history_tier,
        "partial": history_tier == "limited" or bool(getattr(analysis, "warnings", ()) or ()),
        "warnings": list(dict.fromkeys(getattr(analysis, "warnings", ()) or ())),
        "missing_data_flags": [item.key for item in core.elements if item.status == "unavailable"],
        "available_elements": available,
        "published_findings": published,
    }


def _date_bounds(analysis: Any) -> tuple[str | None, str | None]:
    features = getattr(analysis, "features", None)
    start = getattr(features, "window_start", None)
    end = getattr(features, "window_end", None)
    if start is None or end is None:
        rows = tuple(analysis) if isinstance(analysis, Sequence) and not isinstance(analysis, (str, bytes)) else ()
        timestamps: list[float] = []
        for row in rows:
            value = getattr(row, "start_time", None)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                timestamps.append(float(value))
        if not timestamps:
            return None, None
        start, end = min(timestamps), max(timestamps)
    start_value = float(start)
    end_value = float(end)
    return (
        datetime.fromtimestamp(start_value, tz=UTC).isoformat(),
        datetime.fromtimestamp(end_value, tz=UTC).isoformat(),
    )


def _free_cost(cost_ledger: DataCostLedger | None) -> dict[str, Any]:
    values = cost_ledger.as_dict() if cost_ledger is not None else {}
    return {
        "history_requests": 1,
        "detail_requests": 0,
        "parse_requests": 0,
        "parse_status_requests": 0,
        "cache_hits": max(0, int(values.get("cache_hits", 0))),
        "estimated_cost_units": max(0.0, float(values.get("estimated_cost_units", 0.0))),
    }


__all__ = ["REPORT_SCHEMA_VERSION_V6", "assemble_free_dna_report_v6"]
