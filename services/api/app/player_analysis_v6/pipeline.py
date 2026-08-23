"""Coherent Free DNA v6 analytical core and report assembly seam."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from .baselines import BaselineResolver
from .constants import (
    BASELINE_VERSION,
    BOOTSTRAP_VERSION,
    CLAIM_VERSION,
    DEFAULT_BOOTSTRAP_ITERATIONS,
    ELEMENTS_VERSION,
    FINDINGS_VERSION,
    MIN_ELIGIBLE_MATCHES,
    NORMAL_REPORT_MATCHES,
    REPORT_VERSION,
)
from .costs import new_free_cost_ledger
from .elements import compute_elements
from .findings import evaluate_families
from .identity import synthesize_identity
from .models import FreeDnaReportV6
from .story import assemble_story, build_diagnostic_questions, build_share_candidates
from .thresholds import MetricThreshold


class InsufficientHistoryError(ValueError):
    """Raised when the v6 report eligibility floor is not met."""


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def _coerce_matches(analysis: Any, *, profile: Mapping[str, Any] | None = None) -> tuple[Any, ...]:
    """Accept a v5 DnaAnalysisResult, a normalized tuple, or raw rows."""

    if isinstance(analysis, Mapping):
        values = analysis.get("matches", analysis.get("history", ()))
    elif isinstance(analysis, Sequence) and not isinstance(analysis, (str, bytes)):
        values = analysis
    else:
        values = getattr(analysis, "matches", ())
    values = tuple(values or ())
    if not values or not isinstance(values[0], Mapping):
        return values
    # Keep raw-row support optional and isolated from v5.  Normalization is
    # best-effort; a caller may still pass lightweight dict fixtures directly.
    try:
        from app.ingestion.summary_normalize import normalize_summary_rows

        account_id = int((profile or {}).get("account_id", values[0].get("account_id", 0)) or 0)
        normalized = normalize_summary_rows(list(values), account_id)
        return normalized.matches
    except (ImportError, TypeError, ValueError):
        return values


def _taxonomy_mapping(analysis: Any, provided: Mapping[Any, Any] | None) -> Mapping[Any, Any] | None:
    if provided is not None:
        return provided
    taxonomy = getattr(analysis, "taxonomy", None)
    heroes = getattr(taxonomy, "heroes", None)
    if not isinstance(heroes, Mapping):
        return None
    return {hero_id: tuple(getattr(entry, "roles", ()) or ()) for hero_id, entry in heroes.items()}


def _safe_portfolio(analysis: Any, explicit: Mapping[str, Any] | None) -> dict[str, Any]:
    raw = explicit
    if raw is None:
        value = getattr(analysis, "hero_portfolio", None)
        if value is not None:
            try:
                raw = value.as_dict(include_private_eligibility=False)
            except (AttributeError, TypeError):
                try:
                    raw = value.as_dict()
                except (AttributeError, TypeError):
                    raw = None
    if not isinstance(raw, Mapping):
        return {}
    # Keep the public bridge compact and semantic.  Raw match IDs and internal
    # eligibility flags remain in v5's private assembly path.
    allowed = {
        "headline",
        "label",
        "anchor",
        "common_thread",
        "confidence",
        "evidence_refs",
        "heroes",
        "hero_names",
        # Compact portfolio context used by the prediction/timeline and Hero
        # Mirror beats.  These are semantic payloads; raw match identifiers
        # and private eligibility flags are deliberately excluded.
        "evolution",
        "hero_mirror",
        "mirror",
        "prediction",
        "prediction_refs",
        "timeline",
        "timeline_points",
        "timeline_refs",
        "hero_mirror_refs",
        "mirror_refs",
    }
    def sanitize(value: Any) -> Any:
        if isinstance(value, Mapping):
            return {
                str(key): sanitize(item)
                for key, item in value.items()
                if str(key) not in {"match_ids", "source_match_ids", "raw_match_ids", "private_eligibility"}
            }
        if isinstance(value, (tuple, list)):
            return tuple(sanitize(item) for item in value)
        return value
    return {str(key): sanitize(value) for key, value in raw.items() if str(key) in allowed}


def _lane_context(matches: Sequence[Any]) -> tuple[str, ...]:
    values = {
        str(value)
        for item in matches
        for value in (_get(item, "role_hint"), _get(item, "role"))
        if value
        and str(value) in {"carry", "mid", "offlane", "roamer", "safe_lane", "mid_lane", "off_lane", "unknown"}
    }
    return tuple(sorted(values))


def _signal_inputs(analysis: Any, matches: Sequence[Any], elements: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, int], dict[str, float]]:
    signals: dict[str, Any] = {}
    transitions: dict[str, int] = {}
    coverage: dict[str, float] = {}
    features = getattr(analysis, "features", None)
    # Post-loss response uses only precomputed summary transitions; no detail
    # parse is needed.  A simple paired-count signal is still kept separate
    # from transfer and consistency.
    loss_values = tuple(getattr(features, "transitions_after_loss", ()) or ())
    familiar_values = tuple(getattr(features, "familiar_performance", ()) or ())
    if loss_values:
        signals["post_loss_response"] = {
            "value": sum(float(item) for item in loss_values) / len(loss_values),
            "sample_size": len(loss_values),
            "independent_sessions": len({getattr(item, "session_id", None) for item in matches}),
            "coverage": 1.0,
            "evidence_refs": ("post_loss:response",),
        }
        transitions["post_loss_response"] = len(loss_values)
        coverage["post_loss_response"] = 1.0
    if familiar_values:
        signals["familiarity"] = {
            "value": sum(float(item) for item in familiar_values) / len(familiar_values),
            "sample_size": len(familiar_values),
            "independent_sessions": len({getattr(item, "session_id", None) for item in matches}),
            "coverage": len(familiar_values) / len(matches) if matches else 0.0,
            "evidence_refs": ("post_loss:familiarity",),
        }
    durations = [float(_get(item, "duration_seconds", _get(item, "duration"))) for item in matches if _get(item, "duration_seconds", _get(item, "duration")) not in (None, 0)]
    sessions = len({str(_get(item, "session_id", index)) for index, item in enumerate(matches)})
    if durations and sessions >= 12:
        median_duration = sorted(durations)[len(durations) // 2]
        late = [duration for duration in durations if duration >= median_duration]
        signals["duration"] = {"value": median_duration, "sample_size": len(durations), "independent_sessions": sessions, "coverage": len(durations) / len(matches), "evidence_refs": ("session:duration",)}
        signals["late_session"] = {"value": sum(late) / len(late) if late else None, "sample_size": len(late), "independent_sessions": sessions, "coverage": len(late) / len(matches), "evidence_refs": ("session:late",)}
        transitions["session_drift"] = sessions
        coverage["session_drift"] = len(durations) / len(matches)
    return signals, transitions, coverage


def analyze_free_dna_v6(
    analysis: Any,
    *,
    profile: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    hero_portfolio: Mapping[str, Any] | None = None,
    taxonomy_by_hero: Mapping[Any, Any] | None = None,
    taxonomy_by_match: Mapping[Any, Any] | None = None,
    baseline_resolver: BaselineResolver | None = None,
    thresholds: Mapping[str, MetricThreshold] | None = None,
    seed: int = 0,
    bootstrap_iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    enforce_eligibility: bool = True,
) -> FreeDnaReportV6:
    """Build the complete v6 report from normalized summary history.

    The function accepts the existing ``DnaAnalysisResult`` as a migration
    seam but never reads its v5 public Elements or Patterns.  It can also be
    called with a sequence of normalized matches or raw summary dictionaries.
    """

    matches = _coerce_matches(analysis, profile=profile)
    eligible_count = len(matches)
    if enforce_eligibility and eligible_count < MIN_ELIGIBLE_MATCHES:
        raise InsufficientHistoryError(f"Free DNA v6 requires at least {MIN_ELIGIBLE_MATCHES} eligible matches")
    metadata_value = dict(metadata or {})
    metadata_value.setdefault("history_window_days", 365)
    metadata_value.setdefault("eligible_match_count", eligible_count)
    metadata_value.setdefault("history_tier", "limited" if eligible_count < NORMAL_REPORT_MATCHES else "normal")
    metadata_value.setdefault("lane_context", list(_lane_context(matches)))
    metadata_value.pop("lane_role", None)
    metadata_value.pop("position", None)
    metadata_value.pop("positions", None)
    metadata_value.pop("mmr", None)
    metadata_value.pop("rank", None)

    taxonomy = _taxonomy_mapping(analysis, taxonomy_by_hero)
    computed_elements = compute_elements(
        matches,
        metadata=metadata_value,
        taxonomy_by_hero=taxonomy,
        taxonomy_by_match=taxonomy_by_match,
        baseline_resolver=baseline_resolver,
        thresholds=thresholds,
        seed=seed,
        bootstrap_iterations=bootstrap_iterations,
    )
    element_map = {item.key: item for item in computed_elements}
    signals, transitions, comparable_coverage = _signal_inputs(analysis, matches, element_map)
    findings = evaluate_families(
        element_map,
        signals=signals,
        sample_size=eligible_count,
        independent_sessions=len({_get(item, "session_id", index) for index, item in enumerate(matches)}),
        transitions=transitions,
        comparable_context_coverage=comparable_coverage or 1.0,
    )
    portfolio = _safe_portfolio(analysis, hero_portfolio)
    identity = synthesize_identity(findings, elements=element_map, hero_portfolio=portfolio)
    diagnostics = build_diagnostic_questions(findings)
    story = assemble_story(identity, findings, diagnostic_questions=diagnostics, hero_portfolio=portfolio)
    shares = build_share_candidates(identity, findings, hero_portfolio=portfolio)
    cost = new_free_cost_ledger(history_reads=1)
    versions = {
        "report": REPORT_VERSION,
        "elements": ELEMENTS_VERSION,
        "findings": FINDINGS_VERSION,
        "bootstrap": BOOTSTRAP_VERSION,
        "baseline": BASELINE_VERSION,
        "claims": CLAIM_VERSION,
    }
    quality = {
        "eligible_match_count": eligible_count,
        "independent_session_count": len({_get(item, "session_id", index) for index, item in enumerate(matches)}),
        "history_tier": metadata_value["history_tier"],
        "published_finding_count": sum(item.published for item in findings),
        "limited_identity": eligible_count < NORMAL_REPORT_MATCHES,
    }
    reproducibility = {
        "seed": int(seed),
        "bootstrap_iterations": int(bootstrap_iterations),
        "bootstrap_method": "clustered-bca-approximation-1.0.0",
        "history_window_days": 365,
    }
    methodology = {
        "summary_only": True,
        "session_resampling": "independent sessions with replacement",
        "baseline_hierarchy": (
            "patch+hero+lane",
            "patch+hero_function+lane",
            "patch+hero",
            "patch+lane",
            "patch",
            "overall",
        ),
        "lane_context": list(_lane_context(matches)),
        "lane_context_is_not_position": True,
        "forbidden_free_claims": ("lane positioning", "death quality", "causality"),
    }
    return FreeDnaReportV6(
        identity=identity,
        elements=computed_elements,
        findings=findings,
        story=story,
        diagnostic_questions=diagnostics,
        share_candidates=shares,
        hero_portfolio=portfolio,
        metadata=metadata_value,
        reproducibility=reproducibility,
        quality=quality,
        methodology=methodology,
        cost=cost,
        versions=versions,
    )


def assemble_v6_report(*args: Any, **kwargs: Any) -> FreeDnaReportV6:
    return analyze_free_dna_v6(*args, **kwargs)


def build_free_dna_report_v6(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return analyze_free_dna_v6(*args, **kwargs).as_dict()


__all__ = [
    "InsufficientHistoryError",
    "analyze_free_dna_v6",
    "assemble_v6_report",
    "build_free_dna_report_v6",
]
