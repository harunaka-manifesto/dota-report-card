"""Coherent Free DNA v6 analytical core and report assembly seam."""

from __future__ import annotations

import math
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from .baselines import BaselineResolver
from .constants import (
    BASELINE_VERSION,
    BOOTSTRAP_VERSION,
    CLAIM_VERSION,
    DEFAULT_BOOTSTRAP_ITERATIONS,
    DIAGNOSTICS_VERSION,
    ELEMENTS_VERSION,
    FINDINGS_VERSION,
    INTERACTION_VERSION,
    MIN_ELIGIBLE_MATCHES,
    NORMAL_REPORT_MATCHES,
    REPORT_VERSION,
    SEMANTIC_COPY_VERSION,
    SHARE_VERSION,
    STORY_VERSION,
    THRESHOLDS_VERSION,
)
from .context_adjustment import match_field
from .costs import new_free_cost_ledger
from .elements import compute_elements
from .family_statistics import (
    family_p_values,
    finite_sample_directional_p,
    population_zone_p_value,
)
from .findings import evaluate_families
from .hero_portfolio import build_v6_hero_portfolio
from .identity import synthesize_identity
from .models import FreeDnaReportV6
from .post_loss import compute_post_loss_response
from .recommendations import bind_recommendation_baselines
from .session_drift import compute_session_drift
from .story import assemble_story, build_diagnostic_questions, build_share_candidates
from .thresholds import DEFAULT_THRESHOLDS, MetricThreshold, threshold_for


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
        for value in (match_field(item, "lane_context"), match_field(item, "role_hint"), match_field(item, "role"))
        if value
        and str(value) in {"carry", "mid", "offlane", "roamer", "safe_lane", "mid_lane", "off_lane", "unknown"}
    }
    return tuple(sorted(values))


def _signal_inputs(matches: Sequence[Any], elements: Mapping[str, Any], *, baseline_resolver: BaselineResolver | None, taxonomy_by_hero: Mapping[Any, Any] | None, thresholds: Mapping[str, MetricThreshold] | None = None, completed_sessions: Mapping[str, bool] | None = None, seed: int = 0, bootstrap_iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS, internal_evidence_out: MutableMapping[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, int], dict[str, float], dict[str, float]]:
    thresholds = thresholds or DEFAULT_THRESHOLDS
    signals: dict[str, Any] = {}
    transitions: dict[str, int] = {}
    coverage: dict[str, float] = {}
    transfer_element = elements.get("transfer")
    transfer_raw = transfer_element.raw_metrics if transfer_element is not None else {}
    raw_core_ids = transfer_raw.get("core_hero_ids", ()) if isinstance(transfer_raw, Mapping) else ()
    core_heroes = set(raw_core_ids) if isinstance(raw_core_ids, (tuple, list, set)) else None
    post_loss = compute_post_loss_response(matches, baseline_resolver=baseline_resolver, taxonomy_by_hero=taxonomy_by_hero, core_heroes=core_heroes, thresholds=thresholds, bootstrap_iterations=bootstrap_iterations, seed=seed + 100)
    if internal_evidence_out is not None:
        internal_evidence_out["post_loss"] = {
            "comparable_pair_count": post_loss.comparable_pair_count,
        }
    post_components = [float(value) for value in post_loss.component_deltas.values() if value is not None]
    post_value = sum(post_components) / len(post_components) if post_components else None
    post_direction = post_loss.direction
    if post_direction == "positive":
        post_signal = "positive"
    elif post_direction == "negative":
        post_signal = "negative"
    elif post_direction == "mixed":
        post_signal = "mixed"
    else:
        post_signal = "unknown"
    response_stabilities = {
        component: _bootstrap_direction_stability(
            post_loss.component_bootstrap_replicates.get(component, ()),
            post_loss.component_directions.get(component, "unknown"),
            threshold_for(f"post_loss_{component}_delta", thresholds),
        )
        for component in ("outcome", "activity", "survival")
    }
    response_stability_values = [value for value in response_stabilities.values() if value > 0.0]
    signals["post_loss_response"] = {"value": post_value, "direction": post_signal, "sample_size": len(post_loss.transitions), "independent_sessions": post_loss.qualifying_sessions, "coverage": post_loss.comparable_coverage, "evidence_refs": tuple(post_loss.as_dict()["transition_refs"]), "stability": sum(response_stability_values) / len(response_stability_values) if response_stability_values else 0.0}
    familiarity_direction = _threshold_direction(post_loss.familiarity_delta, threshold_for("post_loss_familiarity_delta", thresholds))
    tempo_direction = _threshold_direction(post_loss.tempo_delta, threshold_for("post_loss_tempo_delta", thresholds))
    signals["familiarity"] = {"value": post_loss.familiarity_delta, "direction": familiarity_direction, "sample_size": len(post_loss.transitions), "independent_sessions": post_loss.qualifying_sessions, "coverage": post_loss.comparable_coverage, "evidence_refs": ("post_loss:familiarity",), "stability": _bootstrap_direction_stability(post_loss.support_bootstrap_replicates.get("familiarity", ()), familiarity_direction, threshold_for("post_loss_familiarity_delta", thresholds))}
    signals["tempo"] = {"value": post_loss.tempo_delta, "direction": tempo_direction, "sample_size": len(post_loss.transitions), "independent_sessions": post_loss.qualifying_sessions, "coverage": post_loss.comparable_coverage, "evidence_refs": ("post_loss:tempo",), "stability": _bootstrap_direction_stability(post_loss.support_bootstrap_replicates.get("tempo", ()), tempo_direction, threshold_for("post_loss_tempo_delta", thresholds))}
    transitions["post_loss_response"] = len(post_loss.transitions)
    coverage["post_loss_response"] = post_loss.comparable_coverage

    transfer_element = elements.get("transfer")
    if transfer_element is not None:
        coverage["transfer"] = transfer_element.coverage

    drift = compute_session_drift(matches, baseline_resolver=baseline_resolver, taxonomy_by_hero=taxonomy_by_hero, completed_sessions=completed_sessions, thresholds=thresholds, bootstrap_iterations=bootstrap_iterations, seed=seed + 200)
    drift_components = [float(value) for value in drift.component_deltas.values() if value is not None]
    drift_value = sum(drift_components) / len(drift_components) if drift_components else None
    signals["duration"] = {"value": drift.duration_context.get("elapsed_session_minutes"), "direction": "neutral", "sample_size": len(matches), "independent_sessions": drift.qualifying_sessions, "coverage": drift.coverage, "evidence_refs": ("session:duration",), "stability": 0.0}
    signals["late_session"] = {"value": drift_value, "direction": {"rise": "positive", "fade": "negative"}.get(drift.direction, drift.direction if drift.direction in {"mixed", "unknown"} else "unknown"), "sample_size": len(matches), "independent_sessions": drift.qualifying_sessions, "coverage": drift.coverage, "evidence_refs": ("session:late_minus_early",), "stability": 1.0 if drift.available else 0.0}
    for component in ("outcome", "activity", "survival"):
        component_direction = _threshold_direction(
            drift.component_deltas.get(component),
            threshold_for(f"session_drift_{component}_delta", thresholds),
        )
        signals[f"drift_{component}"] = {
            "value": drift.component_deltas.get(component),
            "direction": component_direction,
            "sample_size": len(matches),
            "independent_sessions": drift.qualifying_sessions,
            "coverage": drift.coverage,
            "evidence_refs": (f"session:drift:{component}",),
            "stability": _bootstrap_direction_stability(
                drift.component_bootstrap_replicates.get(component, ()),
                component_direction,
                threshold_for(f"session_drift_{component}_delta", thresholds),
            ),
        }
    transitions["session_drift"] = drift.qualifying_sessions
    coverage["session_drift"] = drift.coverage

    transfer_element = elements.get("transfer")
    transfer_p = _element_p(transfer_element, thresholds=thresholds, center=0.0)
    transfer_raw_metrics: Mapping[str, Any] = transfer_element.raw_metrics if transfer_element is not None else {}
    transfer_replicates = transfer_raw_metrics.get("component_bootstrap_replicates", {})
    transfer_components = transfer_raw_metrics.get("components", {})
    transfer_p_values: list[float] = []
    transfer_directions = transfer_components.get("component_directions", {}) if isinstance(transfer_components, Mapping) else {}
    for component, values in (transfer_replicates.items() if isinstance(transfer_replicates, Mapping) else ()):
        direction = transfer_directions.get(component)
        threshold = thresholds.get(f"transfer_{component}_delta")
        if (
            transfer_element is not None
            and direction == transfer_element.estimate.direction
            and direction in {"positive", "negative"}
            and isinstance(threshold, MetricThreshold)
        ):
            transfer_p_values.append(finite_sample_directional_p(tuple(float(value) for value in values), direction=direction, practical_margin=threshold.practical_margin))
    if transfer_element is not None and transfer_element.estimate.direction not in {"positive", "negative"}:
        transfer_p_values = []
    if not transfer_p_values:
        transfer_p_values = [transfer_p, transfer_p]
    post_p_values: list[float] = []
    for component, values in (post_loss.component_bootstrap_replicates or {}).items():
        direction = post_loss.component_directions.get(component)
        threshold = thresholds.get(f"post_loss_{component}_delta")
        if direction in {"positive", "negative"} and isinstance(threshold, MetricThreshold):
            post_p_values.append(finite_sample_directional_p(values, direction=direction, practical_margin=threshold.practical_margin))
        else:
            post_p_values.append(1.0)
    for key, values in (post_loss.support_bootstrap_replicates or {}).items():
        delta = post_loss.familiarity_delta if key == "familiarity" else post_loss.tempo_delta
        direction = _sign(delta)
        threshold_key = "post_loss_familiarity_delta" if key == "familiarity" else "post_loss_tempo_delta"
        threshold = thresholds.get(threshold_key)
        post_p_values.append(finite_sample_directional_p(values, direction=direction, practical_margin=threshold.practical_margin) if direction in {"positive", "negative"} and isinstance(threshold, MetricThreshold) else 1.0)
    if post_loss.direction not in {"positive", "negative"}:
        post_p_values = []
    if not post_p_values:
        post_p_values = [1.0] * 5
    drift_p_values: list[float] = []
    for component, values in (drift.component_bootstrap_replicates or {}).items():
        direction = drift.component_directions.get(component)
        threshold = thresholds.get(f"session_drift_{component}_delta")
        drift_p_values.append(finite_sample_directional_p(values, direction=direction, practical_margin=threshold.practical_margin) if direction in {"positive", "negative"} and isinstance(threshold, MetricThreshold) else 1.0)
    if drift.direction not in {"rise", "fade"}:
        drift_p_values = []
    if not drift_p_values:
        drift_p_values = [1.0, 1.0, 1.0]
    p_values = family_p_values(
        pool_shape=_pool_shape_p(elements, thresholds),
        transfer=transfer_p_values,
        post_loss_response=post_p_values,
        combat_expression=_combat_expression_p(elements, thresholds),
        session_drift=drift_p_values,
    )
    return signals, transitions, coverage, p_values


def _threshold_direction(value: Any, threshold: MetricThreshold) -> str:
    return threshold.direction(value) if value is not None else "unknown"


def _bootstrap_direction_stability(
    replicates: Sequence[float],
    direction: str,
    threshold: MetricThreshold,
) -> float:
    if not replicates or direction not in {"positive", "negative", "neutral"}:
        return 0.0
    return sum(threshold.direction(value) == direction for value in replicates) / len(replicates)


def _sign(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "unknown"
    return "positive" if numeric > 0 else "negative" if numeric < 0 else "neutral"


def _signal_p(value: Any) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return 1.0
    if not numeric or not math.isfinite(numeric):
        return 1.0
    direction = "positive" if numeric > 0 else "negative"
    return finite_sample_directional_p((numeric,), direction=direction, center=0.0)


def _element_p(element: Any, *, thresholds: Mapping[str, MetricThreshold] | None = None, center: float = 0.0) -> float:
    if element is None or element.estimate.value is None:
        return 1.0
    replicates = element.raw_metrics.get("bootstrap_replicates", ())
    if not replicates:
        return 1.0
    metric_key = {
        "breadth": "breadth_effective_count",
        "toolkit": "toolkit_effective_count",
        "involvement": "involvement_adjusted",
        "finishing": "finishing_adjusted",
        "death_exposure": "death_exposure_adjusted",
        "transfer": "transfer_outcome_delta",
        "consistency": "consistency_outcome_dispersion",
    }.get(element.key, element.key)
    threshold = threshold_for(metric_key, thresholds)
    direction = element.estimate.direction
    if direction == "positive" and threshold is not None and threshold.high_cutoff is not None:
        return population_zone_p_value(replicates, zone="high", high_cutoff=threshold.high_cutoff)
    if direction == "negative" and threshold is not None and threshold.low_cutoff is not None:
        return population_zone_p_value(replicates, zone="low", low_cutoff=threshold.low_cutoff)
    if direction in {"positive", "negative"}:
        margin = threshold.practical_margin if threshold is not None else 0.0
        return finite_sample_directional_p(replicates, direction=direction, center=center, practical_margin=margin)
    return 1.0


def _pool_shape_p(elements: Mapping[str, Any], thresholds: Mapping[str, MetricThreshold]) -> float:
    breadth = elements.get("breadth")
    toolkit = elements.get("toolkit")
    if breadth is None or toolkit is None or breadth.estimate.zone not in {"low", "high"} or toolkit.estimate.zone not in {"low", "high"}:
        return 1.0
    return max(_element_p(breadth, thresholds=thresholds), _element_p(toolkit, thresholds=thresholds))


def _combat_expression_p(elements: Mapping[str, Any], thresholds: Mapping[str, MetricThreshold]) -> float:
    involvement = elements.get("involvement")
    exposure = elements.get("death_exposure")
    if involvement is None or exposure is None or involvement.estimate.zone not in {"low", "high"} or exposure.estimate.zone not in {"low", "high"}:
        return 1.0
    return max(_element_p(involvement, thresholds=thresholds), _element_p(exposure, thresholds=thresholds))


def second_smallest(first: float, second: float) -> float:
    return sorted((first, second))[1]


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
    completed_sessions: Mapping[str, bool] | None = None,
    seed: int = 0,
    bootstrap_iterations: int = DEFAULT_BOOTSTRAP_ITERATIONS,
    enforce_eligibility: bool = True,
    internal_evidence_out: MutableMapping[str, Any] | None = None,
) -> FreeDnaReportV6:
    """Build the complete v6 report from normalized summary history.

    The function accepts the existing ``DnaAnalysisResult`` as a migration
    seam but never reads its v5 public Elements or Patterns.  It can also be
    called with a sequence of normalized matches or raw summary dictionaries.
    ``internal_evidence_out`` is an optional non-serialized sink for additive
    assembly projections; it does not change the report contract.
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
    effective_thresholds = thresholds or DEFAULT_THRESHOLDS
    computed_elements = compute_elements(
        matches,
        metadata=metadata_value,
        taxonomy_by_hero=taxonomy,
        taxonomy_by_match=taxonomy_by_match,
        baseline_resolver=baseline_resolver,
        thresholds=effective_thresholds,
        seed=seed,
        bootstrap_iterations=bootstrap_iterations,
    )
    element_map = {item.key: item for item in computed_elements}
    signals, transitions, comparable_coverage, p_values = _signal_inputs(
        matches,
        element_map,
        baseline_resolver=baseline_resolver,
        taxonomy_by_hero=taxonomy,
        thresholds=effective_thresholds,
        completed_sessions=completed_sessions,
        seed=seed,
        bootstrap_iterations=bootstrap_iterations,
        internal_evidence_out=internal_evidence_out,
    )
    findings = evaluate_families(
        element_map,
        signals=signals,
        sample_size=eligible_count,
        independent_sessions=len({_get(item, "session_id", index) for index, item in enumerate(matches)}),
        transitions=transitions,
        comparable_context_coverage=comparable_coverage or 1.0,
        p_values=p_values,
    )
    findings = bind_recommendation_baselines(findings, matches)
    portfolio = _safe_portfolio(analysis, hero_portfolio)
    if not portfolio:
        portfolio = build_v6_hero_portfolio(matches, taxonomy_by_hero=taxonomy)
    identity = synthesize_identity(findings, elements=element_map, hero_portfolio=portfolio)
    diagnostics = build_diagnostic_questions(findings, elements=element_map, matches=matches, hero_portfolio=portfolio)
    story = assemble_story(identity, findings, elements=element_map, diagnostic_questions=diagnostics, hero_portfolio=portfolio)
    shares = build_share_candidates(identity, findings, hero_portfolio=portfolio)
    cost = new_free_cost_ledger(history_reads=1)
    versions = {
        "report": REPORT_VERSION,
        "elements": ELEMENTS_VERSION,
        "findings": FINDINGS_VERSION,
        "bootstrap": BOOTSTRAP_VERSION,
        "baseline": BASELINE_VERSION,
        "claims": CLAIM_VERSION,
        "thresholds": THRESHOLDS_VERSION,
        "story": STORY_VERSION,
        "semantic_copy": SEMANTIC_COPY_VERSION,
        "diagnostics": DIAGNOSTICS_VERSION,
        "share": SHARE_VERSION,
        "interactions": INTERACTION_VERSION,
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
        "baseline_artifact": getattr(baseline_resolver, "version", BASELINE_VERSION),
        "threshold_artifact": getattr(next(iter(thresholds.values()), None), "version", THRESHOLDS_VERSION) if thresholds else THRESHOLDS_VERSION,
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
