"""Summary-only Element scoring.

The service is intentionally transport-free.  It receives the normalized
summary corpus and the already-computed private feature set from orchestration.
The old, well-tested dimension scorers are adapted for the overlapping
Elements; new Elements use the same robust comparison conventions here.
"""

from __future__ import annotations

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
from app.behavior.elements.registry import ELEMENT_REGISTRY
from app.behavior.evidence import BehaviorEvidence
from app.behavior.models import Confidence, ElementResult, ElementStatus
from app.dna.dimensions import activity as legacy_activity
from app.dna.dimensions import orientation as legacy_orientation
from app.dna.features.models import DnaFeatureSet
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


def _score_signature_dependence(context: SummaryBehaviorContext) -> ElementResult:
    familiar, off_pool, methodology = _evaluation_groups(context)
    familiar_values = _performance_values(context, familiar)
    off_values = _performance_values(context, off_pool)
    if len(familiar_values) < 15 or len(off_values) < 15:
        return _result("signature_dependence", score=None, sample_size=len(familiar_values) + len(off_values), effective_sample_size=min(len(familiar_values), len(off_values)), coverage=(len(familiar_values) + len(off_values)) / max(len(context.matches), 1), missing_reasons=("familiar_or_comparison_cell_too_small",))
    delta = robust_delta(off_values, familiar_values) or 0.0
    return _result(
        "signature_dependence",
        score=bounded_delta_score(delta, 0.30),
        sample_size=len(familiar_values) + len(off_values),
        effective_sample_size=min(len(familiar_values), len(off_values)) * 2,
        coverage=(len(familiar_values) + len(off_values)) / max(len(context.matches), 1),
        stability=0.85 if methodology == "time_split_70_30" else 0.60,
        quality=0.80,
        evidence=(
            BehaviorEvidence("familiar_performance", robust_median(familiar_values), "proxy", len(familiar_values)),
            BehaviorEvidence("off_pool_performance", robust_median(off_values), "proxy", len(off_values)),
            BehaviorEvidence("familiar_minus_off_pool_delta", round(delta, 4), "delta", len(familiar_values) + len(off_values)),
            BehaviorEvidence("evaluation_method", methodology, "method", len(familiar_values) + len(off_values)),
        ),
        raw_metrics={"delta": delta, "method": methodology},
        confounders=("patch, draft quality, and hero learning can differ between windows",),
        source_match_ids=tuple(item.match_id for item in familiar + off_pool),
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


def _score_role_switch_rate(context: SummaryBehaviorContext) -> ElementResult:
    valid = [item for item in context.ordered_matches if item.role_hint is not None and item.started_at is not None]
    pairs = [(left, right) for left, right in zip(valid, valid[1:], strict=False) if left.session_id == right.session_id or left.session_id is None or right.session_id is None]
    if len(pairs) < 20:
        return _result("role_switch_rate", score=None, sample_size=len(pairs), effective_sample_size=len(pairs), coverage=len(valid) / max(len(context.matches), 1), missing_reasons=("insufficient_role_transitions",))
    switched = sum(left.role_hint != right.role_hint for left, right in pairs)
    value = switched / len(pairs)
    return _result(
        "role_switch_rate",
        score=value,
        sample_size=len(pairs),
        effective_sample_size=len(pairs),
        coverage=len(valid) / max(len(context.matches), 1),
        evidence=(BehaviorEvidence("within_history_switch_rate", value, "share", len(pairs), source_match_ids=tuple(item.match_id for pair in pairs for item in pair)), BehaviorEvidence("valid_role_transitions", len(pairs), "transitions", len(pairs))),
        raw_metrics={"switch_rate": value, "switches": switched, "transitions": len(pairs)},
        confounders=("missing role hints remove transitions from the denominator",),
        source_match_ids=tuple(item.match_id for pair in pairs for item in pair),
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


def _score_off_role_performance(context: SummaryBehaviorContext) -> ElementResult:
    ordered = [item for item in context.ordered_matches if item.role_hint is not None and item.won is not None]
    if len(ordered) < 24 or context.features.role_coverage < 0.50:
        return _result("off_role_performance", score=None, sample_size=len(ordered), effective_sample_size=len(ordered), coverage=context.features.role_coverage, missing_reasons=("insufficient_credible_role_coverage",))
    split = max(12, int(len(ordered) * 0.70))
    counts = Counter(item.role_hint for item in ordered[:split])
    familiar_roles = {role for role, count in counts.items() if role is not None and count >= 3}
    evaluation = ordered[split:]
    familiar = [item for item in evaluation if item.role_hint in familiar_roles]
    off_role = [item for item in evaluation if item.role_hint not in familiar_roles]
    left = _performance_values(context, familiar)
    right = _performance_values(context, off_role)
    if len(left) < 12 or len(right) < 12:
        return _result("off_role_performance", score=None, sample_size=len(left) + len(right), effective_sample_size=min(len(left), len(right)), coverage=context.features.role_coverage, missing_reasons=("familiar_or_off_role_cell_too_small",))
    delta = robust_delta(left, right) or 0.0
    return _result(
        "off_role_performance",
        score=bounded_delta_score(delta, 0.30),
        sample_size=len(left) + len(right),
        effective_sample_size=min(len(left), len(right)) * 2,
        coverage=(len(left) + len(right)) / max(len(context.matches), 1),
        quality=0.70,
        evidence=(BehaviorEvidence("familiar_role_performance", robust_median(left), "proxy", len(left)), BehaviorEvidence("off_role_performance", robust_median(right), "proxy", len(right)), BehaviorEvidence("off_role_minus_familiar_delta", round(delta, 4), "delta", len(left) + len(right))),
        raw_metrics={"delta": delta, "familiar_roles": ",".join(sorted(familiar_roles))},
        confounders=("summary role hints have a lower evidence ceiling than parsed positions",),
        source_match_ids=tuple(item.match_id for item in familiar + off_role),
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


def _score_long_game_performance_shift(context: SummaryBehaviorContext) -> ElementResult:
    long = [context.features.performance_by_match[item.match_id] for item in context.matches if item.match_id in context.features.performance_by_match and (item.duration_seconds or 0) >= 2700]
    short = [context.features.performance_by_match[item.match_id] for item in context.matches if item.match_id in context.features.performance_by_match and 0 < (item.duration_seconds or 0) <= 2100]
    if len(long) < 10 or len(short) < 10:
        return _result("long_game_performance_shift", score=None, sample_size=len(long) + len(short), effective_sample_size=min(len(long), len(short)), coverage=(len(long) + len(short)) / max(len(context.matches), 1), missing_reasons=("insufficient_long_and_short_game_cells",))
    delta = robust_delta(short, long) or 0.0
    return _result("long_game_performance_shift", score=bounded_delta_score(delta, 0.30), sample_size=len(long) + len(short), effective_sample_size=min(len(long), len(short)) * 2, coverage=(len(long) + len(short)) / max(len(context.matches), 1), evidence=(BehaviorEvidence("long_game_performance", robust_median(long), "proxy", len(long)), BehaviorEvidence("short_game_performance", robust_median(short), "proxy", len(short)), BehaviorEvidence("long_minus_short_delta", round(delta, 4), "delta", len(long) + len(short))), raw_metrics={"delta": delta, "long_matches": len(long), "short_matches": len(short)}, confounders=("game duration is shaped by both teams and game state",), source_match_ids=tuple(context.features.performance_by_match))


def _score_session_length_tendency(context: SummaryBehaviorContext) -> ElementResult:
    lengths = context.features.session_lengths
    if len(lengths) < 10 or len(context.features.dated_match_ids) < 25:
        return _result("session_length_tendency", score=None, sample_size=len(context.features.dated_match_ids), effective_sample_size=len(lengths), coverage=len(context.features.dated_match_ids) / max(len(context.matches), 1), missing_reasons=("insufficient_dated_sessions",))
    median_length = float(median(lengths))
    share_long = sum(length >= 5 for length in lengths) / len(lengths)
    duration_hours = (median(context.features.session_durations) / 3600) if context.features.session_durations else 0.0
    value = clamp(0.5 + 0.35 * (median_length - 3.0) / 2.0 + 0.20 * (duration_hours - 3.0) / 2.0 + 0.15 * (share_long - 0.5))
    sensitivity = _session_stability(context, "session_length_tendency")
    return _result("session_length_tendency", score=value, sample_size=len(context.features.dated_match_ids), effective_sample_size=len(lengths), coverage=len(context.features.dated_match_ids) / max(len(context.matches), 1), stability=sensitivity, evidence=(BehaviorEvidence("median_matches_per_session", round(median_length, 2), "matches", len(lengths)), BehaviorEvidence("share_five_plus_sessions", round(share_long, 4), "share", len(lengths)), BehaviorEvidence("median_session_duration", round(duration_hours, 2), "hours", len(lengths))), raw_metrics={"median_length": median_length, "share_long": share_long, "median_duration_hours": duration_hours}, confounders=("the history limit can truncate the oldest session boundary",), source_match_ids=context.features.dated_match_ids)


def _score_late_session_performance(context: SummaryBehaviorContext) -> ElementResult:
    legacy = __import__("app.dna.dimensions.endurance", fromlist=["score"]).score(context.features)
    return _legacy_result(context, "late_session_performance", legacy)


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


def _score_post_loss_performance_response(context: SummaryBehaviorContext) -> ElementResult:
    after_win, after_loss = _transition_groups(context, "performance")
    return _signed_transition_result(context, "post_loss_performance_response", after_win, after_loss, 0.30, "proxy")


def _score_post_loss_activity_shift(context: SummaryBehaviorContext) -> ElementResult:
    after_win, after_loss = _transition_groups(context, "activity")
    return _signed_transition_result(context, "post_loss_activity_shift", after_win, after_loss, 2.0, "events_per_minute")


def _score_post_loss_death_shift(context: SummaryBehaviorContext) -> ElementResult:
    after_win, after_loss = _transition_groups(context, "death")
    return _signed_transition_result(context, "post_loss_death_shift", after_win, after_loss, 1.5, "deaths_per_10_minutes")


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
    "signature_dependence": _score_signature_dependence,
    "post_loss_familiarity_shift": _score_post_loss_familiarity_shift,
    "role_breadth": _score_role_breadth,
    "role_switch_rate": _score_role_switch_rate,
    "combat_involvement": _score_combat_involvement,
    "finisher_orientation": _score_finisher_orientation,
    "death_exposure": _score_death_exposure,
    "off_pool_performance": _score_off_pool_performance,
    "off_pool_activity_stability": _score_off_pool_activity_stability,
    "off_role_performance": _score_off_role_performance,
    "performance_volatility": _score_performance_volatility,
    "recent_form_shift": _score_recent_form_shift,
    "recent_activity_shift": _score_recent_activity_shift,
    "long_game_performance_shift": _score_long_game_performance_shift,
    "session_length_tendency": _score_session_length_tendency,
    "late_session_performance": _score_late_session_performance,
    "post_loss_performance_response": _score_post_loss_performance_response,
    "post_loss_activity_shift": _score_post_loss_activity_shift,
    "post_loss_death_shift": _score_post_loss_death_shift,
}
