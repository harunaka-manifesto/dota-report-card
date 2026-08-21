"""Summary-only Element scoring.

The service is intentionally transport-free.  It receives the normalized
summary corpus and the already-computed private feature set from orchestration.
The old, well-tested dimension scorers are adapted for the overlapping
Elements; new Elements use the same robust comparison conventions here.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from dataclasses import dataclass
from statistics import median
from typing import Any

from app.behavior.comparisons import (
    bounded_delta_score,
    clamp,
    confidence_label,
    confidence_score,
    mad,
    robust_delta,
    robust_median,
)
from app.behavior.elements.registry import ELEMENT_REGISTRY, zone_for_score
from app.behavior.evidence import BehaviorEvidence
from app.behavior.models import Confidence, ElementResult, ElementStatus
from app.dna.breakpoints import SESSION_BUCKETS, detect_breakpoint
from app.dna.dimensions import activity as legacy_activity
from app.dna.dimensions import orientation as legacy_orientation
from app.dna.features.models import DnaFeatureSet
from app.dna.recency import effective_sample_size, weighted_mean, weighted_median
from app.dna.sessions import SessionResult
from app.heroes.taxonomy import HeroTaxonomy
from app.ingestion.summary_normalize import NormalizedSummaryMatch


@dataclass(frozen=True, slots=True)
class SummaryBehaviorContext:
    """The complete CPU-only input boundary for active Free semantics."""

    matches: tuple[NormalizedSummaryMatch, ...]
    sessions: SessionResult
    features: DnaFeatureSet
    taxonomy: HeroTaxonomy | None = None
    history_tier: str = "normal"

    @property
    def by_id(self) -> dict[int, NormalizedSummaryMatch]:
        return {item.match_id: item for item in self.matches}

    @property
    def ordered_matches(self) -> tuple[NormalizedSummaryMatch, ...]:
        return tuple(
            sorted(
                self.matches,
                key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id),
            )
        )


def score_all_elements(context: SummaryBehaviorContext) -> tuple[ElementResult, ...]:
    """Score every registered Free Element and fail closed per Element."""

    results: list[ElementResult] = []
    for key in ELEMENT_REGISTRY:
        try:
            results.append(score_element(context, key))
        except Exception:
            # One missing field family must not make the rest of the model
            # disappear.  The failure is explicit and carries no neutral score.
            results.append(_unavailable(key, ("scorer_failed",)))
    return tuple(results)


def score_element(context: SummaryBehaviorContext, key: str) -> ElementResult:
    if key not in ELEMENT_REGISTRY:
        raise KeyError(f"Unknown Free Element: {key}")
    scorer = _SCORERS.get(key)
    if scorer is None:
        raise KeyError(f"No scorer registered for Free Element: {key}")
    return scorer(context)


def _definition(key: str):
    return ELEMENT_REGISTRY[key]


def _result(
    key: str,
    *,
    score: float | None,
    sample_size: int,
    effective_sample_size: float,
    coverage: float,
    stability: float = 1.0,
    quality: float = 1.0,
    raw_metrics: dict[str, float | int | str | bool | None] | None = None,
    evidence: tuple[BehaviorEvidence, ...] = (),
    confounders: tuple[str, ...] = (),
    missing_reasons: tuple[str, ...] = (),
    source_match_ids: tuple[int, ...] = (),
    confidence_override: float | None = None,
) -> ElementResult:
    definition = _definition(key)
    coverage = clamp(coverage)
    available = (
        score is not None
        and sample_size >= definition.minimum_sample
        and coverage >= definition.minimum_coverage
    )
    confidence = (
        confidence_override
        if confidence_override is not None
        else confidence_score(
            sample_size=sample_size,
            effective_sample_size=effective_sample_size,
            coverage=coverage,
            stability=stability,
            quality=quality,
            minimum_sample=definition.minimum_sample,
        )
    ) if available else 0.0
    confidence = clamp(confidence)
    final_score = clamp(score) if available and score is not None else None
    status: ElementStatus = "unavailable" if final_score is None else "available" if confidence >= 0.50 else "limited"
    confidence_label_value: Confidence = confidence_label(confidence, unavailable=final_score is None)
    reasons = () if final_score is not None else (missing_reasons or ("insufficient_evidence",))
    return ElementResult(
        key=key,
        label=definition.label,
        dimension_key=definition.dimension_key,
        status=status,
        score=final_score,
        centered_score=(2.0 * final_score - 1.0) if final_score is not None else None,
        confidence=confidence_label_value,
        confidence_score=confidence,
        sample_size=max(0, sample_size),
        effective_sample_size=max(0.0, float(effective_sample_size)),
        coverage=coverage,
        stability=clamp(stability),
        quality=clamp(quality),
        raw_metrics=raw_metrics or {},
        evidence=evidence,
        confounders=confounders or definition.confounders,
        missing_reasons=reasons,
        methodology_version=definition.version,
        axis_left=definition.axis_left,
        axis_right=definition.axis_right,
        source_match_ids=source_match_ids,
        zone=zone_for_score(key, final_score),
    )


def _unavailable(key: str, reasons: tuple[str, ...]) -> ElementResult:
    definition = _definition(key)
    return ElementResult(
        key=key,
        label=definition.label,
        dimension_key=definition.dimension_key,
        status="unavailable",
        score=None,
        centered_score=None,
        confidence="unavailable",
        confidence_score=0.0,
        sample_size=0,
        effective_sample_size=0.0,
        coverage=0.0,
        stability=0.0,
        quality=0.0,
        confounders=definition.confounders,
        missing_reasons=reasons,
        methodology_version=definition.version,
        axis_left=definition.axis_left,
        axis_right=definition.axis_right,
        zone=None,
    )


def _legacy_result(context: SummaryBehaviorContext, key: str, legacy: Any) -> ElementResult:
    evidence = tuple(
        BehaviorEvidence(
            key=item.key,
            value=item.value,
            unit=item.unit,
            denominator=max(0, item.denominator),
            coverage=legacy.coverage,
            confidence_score=legacy.confidence_score,
            source_match_ids=tuple(item.source_match_ids),
        )
        for item in legacy.evidence
    )
    return _result(
        key,
        score=legacy.score,
        sample_size=legacy.sample_size,
        effective_sample_size=legacy.effective_sample_size,
        coverage=legacy.coverage,
        stability=legacy.confidence_score if legacy.score is not None else 0.0,
        quality=legacy.confidence_score,
        evidence=evidence,
        confounders=tuple(legacy.confounders),
        missing_reasons=tuple(legacy.missing_reasons),
        source_match_ids=tuple(legacy.source_match_ids),
        confidence_override=legacy.confidence_score,
    )


def _score_hero_pool_breadth(context: SummaryBehaviorContext) -> ElementResult:
    features = context.features
    sample = sum(item.hero_id is not None for item in context.matches)
    if not features.hero_counts:
        return _result("hero_pool_breadth", score=None, sample_size=sample, effective_sample_size=0, coverage=0.0, missing_reasons=("missing_hero_history",))
    effective = features.effective_hero_count
    top5 = features.top_hero_shares.get(5, 0.0)
    concentration = 0.45 * top5 + 0.35 * (1.0 - features.normalized_hero_entropy) + 0.20 * min(1.0, 10.0 / max(effective, 1.0))
    return _result(
        "hero_pool_breadth",
        score=1.0 - concentration,
        sample_size=sample,
        effective_sample_size=effective,
        coverage=sample / max(len(context.matches), 1),
        stability=_hero_window_stability(context),
        evidence=(
            BehaviorEvidence("unique_heroes", len(features.hero_counts), "heroes", sample, source_match_ids=features.source_match_ids),
            BehaviorEvidence("top_5_share", round(top5, 4), "share", sample, source_match_ids=features.source_match_ids),
        ),
        raw_metrics={"top_5_share": top5, "normalized_entropy": features.normalized_hero_entropy, "effective_hero_count": effective},
        source_match_ids=features.source_match_ids,
    )


def _score_hero_pool_stability(context: SummaryBehaviorContext) -> ElementResult:
    dated = [item for item in context.ordered_matches if item.started_at is not None and item.hero_id is not None]
    if len(dated) < 60:
        return _result("hero_pool_stability", score=None, sample_size=len(dated), effective_sample_size=len(dated), coverage=len(dated) / max(len(context.matches), 1), missing_reasons=("insufficient_dated_comparison_windows",))
    midpoint = len(dated) // 2
    similarity = _distribution_similarity(dated[:midpoint], dated[midpoint:])
    return _result(
        "hero_pool_stability",
        score=similarity,
        sample_size=len(dated),
        effective_sample_size=min(midpoint, len(dated) - midpoint) * 2,
        coverage=len(dated) / max(len(context.matches), 1),
        stability=_hero_window_stability(context),
        evidence=(
            BehaviorEvidence("distribution_similarity", round(similarity, 4), "similarity", len(dated), source_match_ids=tuple(item.match_id for item in dated)),
            BehaviorEvidence("comparison_window", midpoint, "matches", len(dated)),
        ),
        raw_metrics={"distribution_similarity": similarity, "recent_window": len(dated) - midpoint, "prior_window": midpoint},
        source_match_ids=tuple(item.match_id for item in dated),
    )


def _score_hero_exploration_rate(context: SummaryBehaviorContext) -> ElementResult:
    ordered = [item for item in context.ordered_matches if item.started_at is not None and item.hero_id is not None]
    if len(ordered) < 60:
        return _result("hero_exploration_rate", score=None, sample_size=len(ordered), effective_sample_size=len(ordered), coverage=len(ordered) / max(len(context.matches), 1), missing_reasons=("insufficient_dated_evaluation_history",))
    split = max(30, int(len(ordered) * 0.70))
    familiar = _familiar_set(ordered[:split])
    evaluation = ordered[split:]
    off_pool = [item for item in evaluation if item.hero_id not in familiar]
    return _result(
        "hero_exploration_rate",
        score=len(off_pool) / max(len(evaluation), 1),
        sample_size=len(ordered),
        effective_sample_size=len(evaluation),
        coverage=len(ordered) / max(len(context.matches), 1),
        evidence=(
            BehaviorEvidence("evaluation_off_pool_share", len(off_pool) / max(len(evaluation), 1), "share", len(evaluation), source_match_ids=tuple(item.match_id for item in evaluation)),
            BehaviorEvidence("familiar_pool_size", len(familiar), "heroes", split),
        ),
        raw_metrics={"off_pool_share": len(off_pool) / max(len(evaluation), 1), "familiar_hero_count": len(familiar)},
        source_match_ids=tuple(item.match_id for item in evaluation),
    )


def _score_toolkit_breadth(context: SummaryBehaviorContext) -> ElementResult:
    if context.taxonomy is None:
        return _result("toolkit_breadth", score=None, sample_size=0, effective_sample_size=0, coverage=0.0, missing_reasons=("hero_taxonomy_unavailable",))
    rows = [item for item in context.matches if item.hero_id is not None]
    signatures: list[str] = []
    for item in rows:
        hero = context.taxonomy.get(item.hero_id or 0)
        if hero is None or not hero.available:
            continue
        traits = tuple(sorted(hero.traits, key=lambda trait: (-hero.traits[trait], trait))[:3])
        signatures.append("|".join(traits) or "unclassified")
    coverage = len(signatures) / max(len(rows), 1)
    if len(signatures) < 30 or coverage < 0.80:
        return _result("toolkit_breadth", score=None, sample_size=len(signatures), effective_sample_size=len(signatures), coverage=coverage, missing_reasons=("insufficient_taxonomy_coverage",))
    counts = Counter(signatures)
    entropy = _normalized_entropy(counts.values())
    return _result(
        "toolkit_breadth",
        score=entropy,
        sample_size=len(signatures),
        effective_sample_size=math.exp(_entropy(counts.values())),
        coverage=coverage,
        evidence=(
            BehaviorEvidence("toolkit_signature_count", len(counts), "toolkits", len(signatures)),
            BehaviorEvidence("taxonomy_coverage", coverage, "share", len(rows)),
        ),
        raw_metrics={"toolkit_signature_count": len(counts), "taxonomy_coverage": coverage, "normalized_entropy": entropy},
        confounders=("taxonomy labels are editorial and versioned",),
        source_match_ids=tuple(item.match_id for item in rows),
    )


def _score_post_loss_familiarity_shift(context: SummaryBehaviorContext) -> ElementResult:
    losses: list[float] = []
    wins: list[float] = []
    ordered = context.ordered_matches
    for index, current in enumerate(ordered):
        if current.hero_id is None or current.session_id is None or current.session_index in (None, 1):
            continue
        previous = next((item for item in ordered[:index][::-1] if item.session_id == current.session_id), None)
        if previous is None or previous.won is None:
            continue
        familiar = _familiar_set([item for item in ordered[:index] if item.hero_id is not None])
        if not familiar:
            continue
        is_familiar = 1.0 if current.hero_id in familiar else 0.0
        (losses if previous.won is False else wins).append(is_familiar)
    sample = len(losses) + len(wins)
    if len(losses) < 15 or len(wins) < 15:
        return _result("post_loss_familiarity_shift", score=None, sample_size=sample, effective_sample_size=min(len(losses), len(wins)) * 2, coverage=sample / max(len(context.matches), 1), missing_reasons=("insufficient_post_result_transitions",))
    delta = (robust_median(losses) or 0.0) - (robust_median(wins) or 0.0)
    return _result(
        "post_loss_familiarity_shift",
        score=bounded_delta_score(delta, 0.35),
        sample_size=sample,
        effective_sample_size=min(len(losses), len(wins)) * 2,
        coverage=sample / max(len(context.matches), 1),
        stability=_session_stability(context, "post_loss_familiarity_shift"),
        evidence=(
            BehaviorEvidence("familiar_after_loss", robust_median(losses), "share", len(losses)),
            BehaviorEvidence("familiar_after_win", robust_median(wins), "share", len(wins)),
            BehaviorEvidence("loss_minus_win_delta", round(delta, 4), "delta", sample),
        ),
        raw_metrics={"delta": delta, "after_loss": robust_median(losses), "after_win": robust_median(wins)},
        confounders=("session gaps and stopping behavior affect valid transitions",),
        source_match_ids=tuple(item.match_id for item in ordered),
    )


def _score_role_breadth(context: SummaryBehaviorContext) -> ElementResult:
    features = context.features
    sample = len(features.role_match_ids)
    coverage = features.role_coverage
    if not features.role_counts:
        return _result("role_breadth", score=None, sample_size=sample, effective_sample_size=0, coverage=coverage, missing_reasons=("missing_credible_role_hints",))
    dominant = max(features.role_counts.values()) / sample if sample else 0.0
    anchoring = 0.65 * dominant + 0.35 * (1.0 - features.normalized_role_entropy)
    return _result(
        "role_breadth",
        score=1.0 - anchoring,
        sample_size=sample,
        effective_sample_size=sample * coverage,
        coverage=coverage,
        stability=1.0 if coverage >= 0.65 else 0.70,
        quality=coverage,
        evidence=(
            BehaviorEvidence("dominant_role_hint", features.dominant_role or "unknown", "role", sample, source_match_ids=features.role_match_ids),
            BehaviorEvidence("dominant_role_share", round(dominant, 4), "share", sample, source_match_ids=features.role_match_ids),
        ),
        raw_metrics={"dominant_role_share": dominant, "normalized_entropy": features.normalized_role_entropy},
        confounders=("summary lane labels are hints and may miss role swaps",),
        source_match_ids=features.role_match_ids,
    )


def _score_combat_involvement(context: SummaryBehaviorContext) -> ElementResult:
    return _legacy_result(context, "combat_involvement", legacy_activity.score(context.features))


def _score_finisher_orientation(context: SummaryBehaviorContext) -> ElementResult:
    return _legacy_result(context, "finisher_orientation", legacy_orientation.score(context.features))


def _score_death_exposure(context: SummaryBehaviorContext) -> ElementResult:
    rows = [item for item in context.matches if item.deaths is not None and item.duration_seconds and item.duration_seconds >= 600]
    values = [rate for item in rows if (rate := _death_rate(item)) is not None]
    if len(values) < 30:
        return _result("death_exposure", score=None, sample_size=len(values), effective_sample_size=len(values), coverage=len(values) / max(len(context.matches), 1), missing_reasons=("missing_deaths_or_duration",))
    centre = robust_median(values) or 0.0
    role_adjusted = sum(item.role_hint is not None and (item.role_confidence or 0.0) >= 0.60 for item in rows) >= 20
    if role_adjusted:
        residuals = [
            rate - _role_death_baseline(item.role_hint)
            for item in rows
            if item.role_hint is not None and (rate := _death_rate(item)) is not None
        ]
        centre = robust_median(residuals) or 0.0
        value = clamp(0.5 + 0.5 * math.tanh(centre / 1.2))
    else:
        value = clamp(0.5 + 0.5 * math.tanh((centre - 0.75) / 1.5))
    return _result(
        "death_exposure",
        score=value,
        sample_size=len(values),
        effective_sample_size=len(values),
        coverage=len(values) / max(len(context.matches), 1),
        quality=0.75 if role_adjusted else 0.55,
        evidence=(BehaviorEvidence("median_deaths_per_10_minutes", round(robust_median(values) or 0.0, 4), "deaths_per_10_minutes", len(values), source_match_ids=tuple(item.match_id for item in rows)), BehaviorEvidence("role_adjusted", role_adjusted, "boolean", len(rows))),
        raw_metrics={"median_deaths_per_10_minutes": robust_median(values), "role_adjusted": role_adjusted},
        confounders=("some heroes and role contexts structurally trade deaths for map value",) + (() if role_adjusted else ("role support is below 20 matches; role-relative wording is suppressed",)),
        source_match_ids=tuple(item.match_id for item in rows),
    )


def _score_off_pool_performance(context: SummaryBehaviorContext) -> ElementResult:
    familiar, off_pool, methodology = _evaluation_groups(context)
    familiar_values = _performance_values(context, familiar)
    off_values = _performance_values(context, off_pool)
    if len(familiar_values) < 20 or len(off_values) < 20:
        return _result("off_pool_performance", score=None, sample_size=len(familiar_values) + len(off_values), effective_sample_size=min(len(familiar_values), len(off_values)), coverage=(len(familiar_values) + len(off_values)) / max(len(context.matches), 1), missing_reasons=("familiar_or_off_pool_evaluation_too_small",))
    delta = robust_delta(familiar_values, off_values) or 0.0
    return _result(
        "off_pool_performance",
        score=bounded_delta_score(delta, 0.30),
        sample_size=len(familiar_values) + len(off_values),
        effective_sample_size=min(len(familiar_values), len(off_values)) * 2,
        coverage=(len(familiar_values) + len(off_values)) / max(len(context.matches), 1),
        stability=0.85 if methodology == "time_split_70_30" else 0.60,
        quality=0.80,
        evidence=(BehaviorEvidence("familiar_performance", robust_median(familiar_values), "proxy", len(familiar_values)), BehaviorEvidence("off_pool_performance", robust_median(off_values), "proxy", len(off_values)), BehaviorEvidence("off_pool_minus_familiar_delta", round(delta, 4), "delta", len(familiar_values) + len(off_values)), BehaviorEvidence("evaluation_method", methodology, "method", len(familiar_values) + len(off_values))),
        raw_metrics={"delta": delta, "method": methodology},
        confounders=("patch, draft quality, and hero learning can differ between windows",),
        source_match_ids=tuple(item.match_id for item in familiar + off_pool),
    )


def _score_off_pool_activity_stability(context: SummaryBehaviorContext) -> ElementResult:
    familiar, off_pool, _ = _evaluation_groups(context)
    left = [rate for item in familiar if (rate := _activity(item)) is not None]
    right = [rate for item in off_pool if (rate := _activity(item)) is not None]
    if len(left) < 12 or len(right) < 12:
        return _result("off_pool_activity_stability", score=None, sample_size=len(left) + len(right), effective_sample_size=min(len(left), len(right)), coverage=(len(left) + len(right)) / max(len(context.matches), 1), missing_reasons=("insufficient_activity_cells",))
    delta = robust_delta(left, right) or 0.0
    scale = mad([*left, *right]) or 1.0
    standardized = delta / scale
    score = clamp(1.0 - min(1.0, abs(standardized) / 2.0))
    return _result(
        "off_pool_activity_stability",
        score=score,
        sample_size=len(left) + len(right),
        effective_sample_size=min(len(left), len(right)) * 2,
        coverage=(len(left) + len(right)) / max(len(context.matches), 1),
        evidence=(BehaviorEvidence("off_pool_activity_delta", round(delta, 4), "events_per_minute_delta", len(left) + len(right)), BehaviorEvidence("standardized_delta", round(standardized, 4), "z_delta", len(left) + len(right))),
        raw_metrics={"delta": delta, "standardized_delta": standardized, "stability_score": score},
        confounders=("role and game tempo can change with hero choice",),
        source_match_ids=tuple(item.match_id for item in familiar + off_pool),
    )


def _score_performance_volatility(context: SummaryBehaviorContext) -> ElementResult:
    values = list(context.features.performance_by_match.values())
    if len(values) < 30:
        return _result("performance_volatility", score=None, sample_size=len(values), effective_sample_size=len(values), coverage=len(values) / max(len(context.matches), 1), missing_reasons=("insufficient_performance_history",))
    dispersion = mad(values)
    return _result(
        "performance_volatility",
        score=clamp(dispersion / 0.30),
        sample_size=len(values),
        effective_sample_size=len(values),
        coverage=len(values) / max(len(context.matches), 1),
        evidence=(BehaviorEvidence("performance_mad", round(dispersion, 4), "proxy_mad", len(values), source_match_ids=tuple(context.features.performance_by_match)),),
        raw_metrics={"mad": dispersion},
        confounders=("the proxy is not a full performance model",),
        source_match_ids=tuple(context.features.performance_by_match),
    )


def _score_recent_form_shift(context: SummaryBehaviorContext) -> ElementResult:
    values = [(item, context.features.performance_by_match[item.match_id]) for item in context.ordered_matches if item.match_id in context.features.performance_by_match]
    if len(values) < 45:
        return _result("recent_form_shift", score=None, sample_size=len(values), effective_sample_size=len(values), coverage=len(values) / max(len(context.matches), 1), missing_reasons=("insufficient_recent_and_prior_windows",))
    recent = [value for _, value in values[-20:]]
    prior = [value for _, value in values[-60:-20]]
    delta = robust_delta(prior, recent) or 0.0
    return _result("recent_form_shift", score=bounded_delta_score(delta, 0.30), sample_size=len(recent) + len(prior), effective_sample_size=min(len(recent), len(prior)) * 2, coverage=(len(recent) + len(prior)) / max(len(context.matches), 1), evidence=(BehaviorEvidence("recent_performance", robust_median(recent), "proxy", len(recent)), BehaviorEvidence("prior_performance", robust_median(prior), "proxy", len(prior)), BehaviorEvidence("recent_minus_prior_delta", round(delta, 4), "delta", len(recent) + len(prior))), raw_metrics={"delta": delta}, confounders=("recent opponents, patches, and hero mix are not controlled",), source_match_ids=tuple(item.match_id for item, _ in values[-60:]))


def _score_recent_activity_shift(context: SummaryBehaviorContext) -> ElementResult:
    values = [
        (item, activity)
        for item in context.ordered_matches
        if (activity := _activity(item)) is not None
    ]
    if len(values) < 45:
        return _result("recent_activity_shift", score=None, sample_size=len(values), effective_sample_size=len(values), coverage=len(values) / max(len(context.matches), 1), missing_reasons=("insufficient_recent_and_prior_activity_windows",))
    recent = [value for _, value in values[-20:]]
    prior = [value for _, value in values[-60:-20]]
    delta = robust_delta(prior, recent) or 0.0
    return _result("recent_activity_shift", score=bounded_delta_score(delta, 2.0), sample_size=len(recent) + len(prior), effective_sample_size=min(len(recent), len(prior)) * 2, coverage=(len(recent) + len(prior)) / max(len(context.matches), 1), evidence=(BehaviorEvidence("recent_activity", robust_median(recent), "events_per_minute", len(recent)), BehaviorEvidence("prior_activity", robust_median(prior), "events_per_minute", len(prior)), BehaviorEvidence("recent_minus_prior_delta", round(delta, 4), "delta", len(recent) + len(prior))), raw_metrics={"delta": delta}, confounders=("team tempo and role mix may differ between windows",), source_match_ids=tuple(item.match_id for item, _ in values[-60:]))


def _score_session_length_tendency(context: SummaryBehaviorContext) -> ElementResult:
    lengths = context.features.session_lengths
    completed_weights = [
        context.features.session_weights.get(session.session_id, 1.0)
        for session in context.sessions.completed_sessions
    ]
    if len(lengths) < 10 or len(context.features.dated_match_ids) < 25:
        return _result("session_length_tendency", score=None, sample_size=len(context.features.dated_match_ids), effective_sample_size=effective_sample_size(completed_weights), coverage=len(context.features.dated_match_ids) / max(len(context.matches), 1), missing_reasons=("insufficient_dated_sessions",))
    median_length = float(weighted_median([float(value) for value in lengths], completed_weights) or 0.0)
    share_long = float(
        weighted_mean(
            [1.0 if length >= 5 else 0.0 for length in lengths],
            completed_weights,
        )
        or 0.0
    )
    duration_hours = (
        float(
            weighted_median(
                [float(value) for value in context.features.session_durations],
                completed_weights,
            )
            or 0.0
        )
        / 3600
        if context.features.session_durations
        else 0.0
    )
    value = clamp(0.5 + 0.35 * (median_length - 3.0) / 2.0 + 0.20 * (duration_hours - 3.0) / 2.0 + 0.15 * (share_long - 0.5))
    sensitivity = _session_stability(context, "session_length_tendency")
    return _result("session_length_tendency", score=value, sample_size=len(context.features.dated_match_ids), effective_sample_size=effective_sample_size(completed_weights), coverage=len(context.features.dated_match_ids) / max(len(context.matches), 1), stability=sensitivity, evidence=(BehaviorEvidence("median_matches_per_session", round(median_length, 2), "matches", len(lengths)), BehaviorEvidence("share_five_plus_sessions", round(share_long, 4), "share", len(lengths)), BehaviorEvidence("median_session_duration", round(duration_hours, 2), "hours", len(lengths))), raw_metrics={"median_length": median_length, "share_long": share_long, "median_duration_hours": duration_hours}, confounders=("the oldest session may be left-censored; the latest session is excluded when its end is not confirmed",), source_match_ids=context.features.dated_match_ids)


def _score_late_session_performance(context: SummaryBehaviorContext) -> ElementResult:
    by_id = context.by_id
    performance = context.features.performance_by_match
    sessions = {
        session.session_id: [
            by_id[match_id]
            for match_id in session.match_ids
            if match_id in by_id
            and match_id in performance
            and not by_id[match_id].session_corrupt
        ]
        for session in context.sessions.sessions
    }
    sessions = {
        session_id: sorted(
            rows,
            key=lambda item: (item.session_index is None, item.session_index or 0, item.match_id),
        )
        for session_id, rows in sessions.items()
        if len(rows) >= 2
    }
    session_order = sorted(
        sessions,
        key=lambda session_id: min((item.started_at or 0 for item in sessions[session_id]), default=0),
    )
    bucket_by_session: dict[str, dict[str, float]] = {}
    source_ids: list[int] = []
    fallback_counts: Counter[str] = Counter()
    for session_id, rows in sessions.items():
        outside = [
            item
            for other_id, other_rows in sessions.items()
            if other_id != session_id
            for item in other_rows
        ]
        if not outside:
            continue
        observations: dict[str, list[float]] = {}
        for item in rows:
            if session_order and session_id == session_order[0] and item.session_index == 1:
                continue
            baseline, fallback = _context_baseline(item, outside, performance, context)
            if baseline is None:
                continue
            bucket = _session_bucket(item.session_index or 0)
            observations.setdefault(bucket, []).append(performance[item.match_id] - baseline)
            fallback_counts[fallback] += 1
            source_ids.append(item.match_id)
        if observations:
            bucket_by_session[session_id] = {
                bucket: median(residuals)
                for bucket, residuals in observations.items()
            }
    if len(bucket_by_session) < 12:
        return _result(
            "late_session_performance",
            score=None,
            sample_size=len(source_ids),
            effective_sample_size=effective_sample_size(
                [context.features.session_weights.get(key, 1.0) for key in bucket_by_session]
            ),
            coverage=len(source_ids) / max(len(context.matches), 1),
            missing_reasons=("insufficient_independent_context_adjusted_sessions",),
            raw_metrics={"fallback_levels": json.dumps(dict(fallback_counts), sort_keys=True)},
            source_match_ids=tuple(source_ids),
        )

    bucket_values: dict[str, float] = {}
    bucket_counts: dict[str, int] = {}
    for bucket in SESSION_BUCKETS:
        entries = [
            (session_id, values[bucket])
            for session_id, values in bucket_by_session.items()
            if bucket in values
        ]
        if entries:
            weights = [context.features.session_weights.get(session_id, 1.0) for session_id, _ in entries]
            bucket_values[bucket] = weighted_mean([value for _, value in entries], weights) or 0.0
            bucket_counts[bucket] = len(entries)
    early = [value for bucket, value in bucket_values.items() if bucket in {"G1", "G2"}]
    late = [value for bucket, value in bucket_values.items() if bucket in {"G3", "G4", "G5+"}]
    if not early or not late:
        return _result(
            "late_session_performance",
            score=None,
            sample_size=len(source_ids),
            effective_sample_size=effective_sample_size(
                [context.features.session_weights.get(key, 1.0) for key in bucket_by_session]
            ),
            coverage=len(source_ids) / max(len(context.matches), 1),
            missing_reasons=("insufficient_early_or_late_session_buckets",),
            raw_metrics={"curve_json": json.dumps(bucket_values, sort_keys=True)},
            source_match_ids=tuple(source_ids),
        )
    delta = float((weighted_mean(late, [1.0] * len(late)) or 0.0) - (weighted_mean(early, [1.0] * len(early)) or 0.0))
    direction = "fade" if delta < -0.04 else "rise" if delta > 0.04 else "flat"
    breakpoint = (
        detect_breakpoint(
            bucket_values,
            direction="fade" if direction == "fade" else "rise",
            counts=bucket_counts,
        )
        if direction != "flat"
        else None
    )
    return _result(
        "late_session_performance",
        score=bounded_delta_score(delta, 0.20),
        sample_size=len(source_ids),
        effective_sample_size=effective_sample_size(
            [context.features.session_weights.get(key, 1.0) for key in bucket_by_session]
        ),
        coverage=len(source_ids) / max(len(context.matches), 1),
        stability=min(
            1.0,
            _session_stability(context, "late_session_performance")
            * (1.0 if direction == "flat" or (breakpoint and breakpoint.state != "unresolved") else 0.75),
        ),
        quality=min(1.0, 0.70 + min(0.30, len(bucket_by_session) / 40.0)),
        evidence=(
            BehaviorEvidence("context_adjusted_late_minus_early_delta", round(delta, 4), "proxy_delta", len(source_ids)),
            BehaviorEvidence("independent_sessions", len(bucket_by_session), "sessions", len(bucket_by_session)),
            BehaviorEvidence("breakpoint_state", breakpoint.state if breakpoint else "unresolved", "state", len(bucket_by_session)),
            BehaviorEvidence("breakpoint_bucket", breakpoint.bucket if breakpoint else None, "bucket", len(bucket_by_session)),
        ),
        raw_metrics={
            "delta": delta,
            "curve_json": json.dumps(bucket_values, sort_keys=True),
            "bucket_counts_json": json.dumps(bucket_counts, sort_keys=True),
            "breakpoint_state": breakpoint.state if breakpoint else "unresolved",
            "breakpoint_bucket": breakpoint.bucket if breakpoint else None,
            "fallback_levels": json.dumps(dict(fallback_counts), sort_keys=True),
        },
        confounders=(
            "session stopping behavior remains observable but not causal",
            "role and hero-function context is adjusted without conditioning on session position",
        ),
        source_match_ids=tuple(source_ids),
    )


def _session_bucket(position: int) -> str:
    if position <= 1:
        return "G1"
    if position == 2:
        return "G2"
    if position == 3:
        return "G3"
    if position == 4:
        return "G4"
    return "G5+"


def _context_baseline(
    target: NormalizedSummaryMatch,
    outside: list[NormalizedSummaryMatch],
    values: dict[int, float],
    context: SummaryBehaviorContext,
) -> tuple[float | None, str]:
    taxonomy = context.taxonomy
    target_function = _primary_function(target, taxonomy)
    groups = (
        ("hero_role_function", [item for item in outside if item.hero_id == target.hero_id and item.role_hint == target.role_hint and _primary_function(item, taxonomy) == target_function]),
        ("hero_function", [item for item in outside if item.hero_id == target.hero_id and _primary_function(item, taxonomy) == target_function]),
        ("role", [item for item in outside if target.role_hint is not None and item.role_hint == target.role_hint]),
        ("overall", list(outside)),
    )
    for level, rows in groups:
        usable = [(values[item.match_id], context.features.weights_by_match.get(item.match_id, 1.0)) for item in rows if item.match_id in values]
        if len(usable) >= 3:
            return weighted_median([value for value, _ in usable], [weight for _, weight in usable]), level
    return None, "unresolved"


def _primary_function(item: NormalizedSummaryMatch, taxonomy: HeroTaxonomy | None) -> str | None:
    if taxonomy is None or item.hero_id is None:
        return None
    entry = taxonomy.get(item.hero_id)
    if entry is None or not entry.available:
        return None
    candidates = (
        "initiation", "mobility", "pickoff", "teamfight", "save", "sustain",
        "burst", "sustained_damage", "wave_clear", "push", "frontline",
        "scaling", "global_presence", "repositioning",
    )
    ranked = sorted(((entry.traits.get(key, 0.0), key) for key in candidates), reverse=True)
    return ranked[0][1] if ranked and ranked[0][0] >= 0.60 else None


def _transition_groups(context: SummaryBehaviorContext, metric: str) -> tuple[list[float], list[float]]:
    by_id = context.by_id
    after_win: list[float] = []
    after_loss: list[float] = []
    for session in context.sessions.sessions:
        for previous_id, current_id in zip(session.match_ids, session.match_ids[1:], strict=False):
            previous = by_id.get(previous_id)
            current = by_id.get(current_id)
            if previous is None or current is None or previous.session_corrupt or current.session_corrupt or previous.won is None:
                continue
            value = _transition_metric(current, metric, context)
            if value is None:
                continue
            (after_win if previous.won else after_loss).append(value)
    return after_win, after_loss


def _score_post_loss_activity_shift(context: SummaryBehaviorContext) -> ElementResult:
    after_win, after_loss = _transition_groups(context, "activity")
    return _signed_transition_result(context, "post_loss_activity_shift", after_win, after_loss, 2.0, "events_per_minute")


def _score_post_loss_performance_response(context: SummaryBehaviorContext) -> ElementResult:
    """Measure the next game after a loss against a leave-session-out baseline."""

    by_id = context.by_id
    values = context.features.performance_by_match
    session_rows = {
        session.session_id: [
            by_id[match_id]
            for match_id in session.match_ids
            if match_id in by_id and match_id in values and not by_id[match_id].session_corrupt
        ]
        for session in context.sessions.sessions
        if not session.corrupt
    }
    residuals: list[float] = []
    baselines: list[float] = []
    observed: list[float] = []
    matched_ids: list[int] = []
    loss_sessions: set[str] = set()
    fallback_counts: Counter[str] = Counter()
    total_loss_transitions = 0
    for session_id, rows in session_rows.items():
        ordered = sorted(rows, key=lambda item: (item.session_index is None, item.session_index or 0, item.match_id))
        outside = [item for other_id, other_rows in session_rows.items() if other_id != session_id for item in other_rows]
        if not outside:
            continue
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if previous.won is None:
                continue
            if not previous.won:
                total_loss_transitions += 1
            if previous.won is not False or current.match_id not in values:
                continue
            baseline, fallback = _context_baseline(current, outside, values, context)
            if baseline is None:
                continue
            residuals.append(values[current.match_id] - baseline)
            baselines.append(baseline)
            observed.append(values[current.match_id])
            matched_ids.append(current.match_id)
            loss_sessions.add(session_id)
            fallback_counts[fallback] += 1

    matched_coverage = len(residuals) / max(total_loss_transitions, 1)
    missing: list[str] = []
    if len(residuals) < 15:
        missing.append("insufficient_comparable_post_loss_transitions")
    if len(loss_sessions) < 3:
        missing.append("insufficient_independent_post_loss_sessions")
    if matched_coverage < 0.50:
        missing.append("insufficient_role_function_context_overlap")
    if missing:
        return _result(
            "post_loss_performance_response",
            score=None,
            sample_size=total_loss_transitions,
            effective_sample_size=effective_sample_size(
                [context.features.weights_by_match.get(match_id, 1.0) for match_id in matched_ids]
            ),
            coverage=total_loss_transitions / max(len(context.matches), 1),
            missing_reasons=tuple(dict.fromkeys(missing)),
            raw_metrics={"fallback_levels": json.dumps(dict(fallback_counts), sort_keys=True)},
            source_match_ids=tuple(matched_ids),
        )

    weights = [context.features.weights_by_match.get(match_id, 1.0) for match_id in matched_ids]
    delta = weighted_median(residuals, weights) or 0.0
    return _result(
        "post_loss_performance_response",
        score=bounded_delta_score(delta, 0.20),
        sample_size=len(residuals),
        effective_sample_size=effective_sample_size(weights),
        coverage=len(residuals) / max(len(context.matches), 1),
        stability=_session_stability(context, "post_loss_performance_response"),
        quality=min(1.0, 0.70 + 0.10 * min(1.0, len(loss_sessions) / 5.0) + 0.20 * matched_coverage),
        evidence=(
            BehaviorEvidence("leave_session_out_baseline", weighted_median(baselines, weights), "performance_score", len(baselines)),
            BehaviorEvidence("matched_after_loss_performance", weighted_median(observed, weights), "performance_score", len(observed)),
            BehaviorEvidence("loss_minus_context_baseline_delta", round(delta, 4), "delta", len(residuals)),
        ),
        raw_metrics={
            "delta": delta,
            "matched_coverage": matched_coverage,
            "independent_sessions": len(loss_sessions),
            "leave_session_out": True,
            "fallback_levels": json.dumps(dict(fallback_counts), sort_keys=True),
        },
        confounders=_definition("post_loss_performance_response").confounders,
        source_match_ids=tuple(matched_ids),
    )


def _signed_transition_result(context: SummaryBehaviorContext, key: str, after_win: list[float], after_loss: list[float], scale: float, unit: str) -> ElementResult:
    sample = len(after_win) + len(after_loss)
    if len(after_win) < 15 or len(after_loss) < 15:
        return _result(key, score=None, sample_size=sample, effective_sample_size=min(len(after_win), len(after_loss)) * 2, coverage=sample / max(len(context.matches), 1), missing_reasons=("insufficient_within_session_transitions",))
    delta = (robust_median(after_loss) or 0.0) - (robust_median(after_win) or 0.0)
    return _result(key, score=bounded_delta_score(delta, scale), sample_size=sample, effective_sample_size=min(len(after_win), len(after_loss)) * 2, coverage=sample / max(len(context.matches), 1), stability=_session_stability(context, key), quality=0.80, evidence=(BehaviorEvidence("after_win", robust_median(after_win), unit, len(after_win)), BehaviorEvidence("after_loss", robust_median(after_loss), unit, len(after_loss)), BehaviorEvidence("loss_minus_win_delta", round(delta, 4), "delta", sample)), raw_metrics={"delta": delta, "after_win": robust_median(after_win), "after_loss": robust_median(after_loss)}, confounders=_definition(key).confounders, source_match_ids=context.features.dated_match_ids)


def _transition_metric(item: NormalizedSummaryMatch, metric: str, context: SummaryBehaviorContext) -> float | None:
    if metric == "performance":
        return context.features.performance_by_match.get(item.match_id)
    if metric == "activity":
        return _activity(item)
    if metric == "death":
        return _death_rate(item)
    return None


def _evaluation_groups(context: SummaryBehaviorContext) -> tuple[list[NormalizedSummaryMatch], list[NormalizedSummaryMatch], str]:
    ordered = [item for item in context.ordered_matches if item.hero_id is not None and item.won is not None]
    if not ordered:
        return [], [], "no_evaluation_rows"
    split = max(1, int(len(ordered) * 0.70))
    familiar = _familiar_set(ordered[:split])
    evaluation = ordered[split:]
    familiar_eval = [item for item in evaluation if item.hero_id in familiar]
    off_eval = [item for item in evaluation if item.hero_id not in familiar]
    if len(familiar_eval) < 12 or len(off_eval) < 12:
        # A deterministic leave-one-window fallback remains outcome-blind.
        for left_end, right_start in ((0.35, 0.35), (0.50, 0.50), (0.70, 0.70)):
            left = ordered[: max(1, int(len(ordered) * left_end))]
            right = ordered[max(1, int(len(ordered) * right_start)):]
            candidate_familiar = _familiar_set(left)
            candidate_familiar_eval = [item for item in right if item.hero_id in candidate_familiar]
            candidate_off = [item for item in right if item.hero_id not in candidate_familiar]
            if min(len(candidate_familiar_eval), len(candidate_off)) > min(len(familiar_eval), len(off_eval)):
                familiar, familiar_eval, off_eval = candidate_familiar, candidate_familiar_eval, candidate_off
        return familiar_eval, off_eval, "leave_one_window_out_fallback"
    return familiar_eval, off_eval, "time_split_70_30"


def _familiar_set(rows: list[NormalizedSummaryMatch]) -> set[int]:
    counts = Counter(item.hero_id for item in rows if item.hero_id is not None)
    stable = sorted(((hero_id, count) for hero_id, count in counts.items() if count >= 3), key=lambda item: (-item[1], item[0]))
    if not stable:
        return set()
    target = max(1, math.ceil(len(rows) * 0.50))
    chosen: set[int] = set()
    total = 0
    for hero_id, count in stable[:10]:
        chosen.add(hero_id)
        total += count
        if total >= target and len(chosen) >= min(3, len(stable)):
            break
    return chosen


def _performance_values(context: SummaryBehaviorContext, rows: list[NormalizedSummaryMatch]) -> list[float]:
    return [context.features.performance_by_match[item.match_id] for item in rows if item.match_id in context.features.performance_by_match]


def _activity(item: NormalizedSummaryMatch) -> float | None:
    if item.duration_seconds is None or item.duration_seconds < 600 or item.kills is None or item.assists is None:
        return None
    return (item.kills + item.assists) / max(item.duration_seconds / 60.0, 1 / 60)


def _death_rate(item: NormalizedSummaryMatch) -> float | None:
    if item.duration_seconds is None or item.duration_seconds < 600 or item.deaths is None:
        return None
    return item.deaths / max(item.duration_seconds / 600.0, 1 / 60)


def _role_death_baseline(role: str | None) -> float:
    # Keep this explicitly provisional.  No role-specific death cohort is
    # available yet, so the baseline is a conservative common reference.
    return {"carry": 0.72, "mid": 0.78, "offlane": 0.95, "jungle": 0.85, "roamer": 1.05}.get(role or "", 0.85)


def _performance_proxy(context: SummaryBehaviorContext, item: NormalizedSummaryMatch) -> float | None:
    return context.features.performance_by_match.get(item.match_id)


def _hero_window_stability(context: SummaryBehaviorContext) -> float:
    dated = [item for item in context.ordered_matches if item.started_at is not None and item.hero_id is not None]
    if len(dated) < 20:
        return 0.65
    values: list[float] = []
    for width in (50, 100, len(dated)):
        window = dated[-min(width, len(dated)):]
        counts = Counter(item.hero_id for item in window)
        values.append(1.0 - sum(sorted(counts.values(), reverse=True)[:5]) / len(window))
    return clamp(1.0 - (max(values) - min(values)) * 2.0, 0.55, 1.0)


def _distribution_similarity(left: list[NormalizedSummaryMatch], right: list[NormalizedSummaryMatch]) -> float:
    left_counts = Counter(item.hero_id for item in left)
    right_counts = Counter(item.hero_id for item in right)
    keys = set(left_counts) | set(right_counts)
    left_total, right_total = len(left), len(right)
    p = {key: left_counts[key] / left_total for key in keys}
    q = {key: right_counts[key] / right_total for key in keys}
    midpoint = {key: (p[key] + q[key]) / 2 for key in keys}
    jsd = 0.5 * sum(p[key] * math.log(p[key] / midpoint[key]) for key in keys if p[key] > 0) + 0.5 * sum(q[key] * math.log(q[key] / midpoint[key]) for key in keys if q[key] > 0)
    return clamp(1.0 - math.sqrt(jsd / math.log(2)))


def _session_stability(context: SummaryBehaviorContext, key: str) -> float:
    scores = context.features.session_sensitivity_scores
    if not scores:
        return 0.60
    baseline = scores.get(90, {}).get("endurance" if key == "late_session_performance" else "rhythm")
    if baseline is None:
        return 0.60
    directions = []
    for gap in (60, 90, 120):
        value = scores.get(gap, {}).get("endurance" if key == "late_session_performance" else "rhythm")
        if value is not None:
            directions.append(0 if abs(value) < 0.08 else 1 if value > 0 else -1)
    return 1.0 if len(set(directions)) <= 1 else 0.75 if len(directions) >= 2 else 0.60


def _entropy(values: Any) -> float:
    numbers = [float(value) for value in values if value]
    total = sum(numbers)
    if not total or len(numbers) <= 1:
        return 0.0
    return -sum((value / total) * math.log(value / total) for value in numbers)


def _normalized_entropy(values: Any) -> float:
    numbers = [value for value in values if value]
    if len(numbers) <= 1:
        return 0.0
    return _entropy(numbers) / math.log(len(numbers))


_SCORERS = {
    "hero_pool_breadth": _score_hero_pool_breadth,
    "hero_pool_stability": _score_hero_pool_stability,
    "hero_exploration_rate": _score_hero_exploration_rate,
    "toolkit_breadth": _score_toolkit_breadth,
    "post_loss_familiarity_shift": _score_post_loss_familiarity_shift,
    "role_breadth": _score_role_breadth,
    "combat_involvement": _score_combat_involvement,
    "finisher_orientation": _score_finisher_orientation,
    "death_exposure": _score_death_exposure,
    "off_pool_performance": _score_off_pool_performance,
    "off_pool_activity_stability": _score_off_pool_activity_stability,
    "performance_volatility": _score_performance_volatility,
    "recent_form_shift": _score_recent_form_shift,
    "recent_activity_shift": _score_recent_activity_shift,
    "session_length_tendency": _score_session_length_tendency,
    "late_session_performance": _score_late_session_performance,
    "post_loss_activity_shift": _score_post_loss_activity_shift,
    "post_loss_performance_response": _score_post_loss_performance_response,
}
