"""Server-owned, reviewed action modules for reviewed Patterns.

These actions are deliberately separate from Pattern qualification. A
qualified Pattern identifies an evidence-backed relationship; this module
turns only reviewed relationships into deterministic, explainable next steps.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from math import log
from statistics import median
from typing import Any, Literal

from app.behavior.context_baseline import (
    CONTEXT_BASELINE_VERSION,
    primary_function,
    resolve_leave_group_out_baseline,
)
from app.behavior.display_bands import job_display_label
from app.behavior.models import (
    ActionStatus,
    BouncebackAction,
    CapabilityHypothesis,
    ComfortEdgeAction,
    ComfortEdgeDevelopmentReason,
    ComfortEdgeHeroReliability,
    ControlledPresenceAction,
    CoverageSummary,
    HeroAdditionRecommendation,
    HeroJobMap,
    ObservedDifference,
    PartialTransferDiagnostic,
    PatternActionEvidence,
    PatternHeroRecommendation,
    PatternResult,
    PerformanceSlideAction,
    PresenceContext,
    PresenceTaxAction,
    ProvenFlexibilityAction,
    RecoveryContext,
    SamePlaybookAction,
    SessionCurveAction,
    SessionCurvePoint,
    VersatileCoreAction,
)
from app.dna.breakpoints import SESSION_BUCKETS, detect_breakpoint
from app.dna.performance import activity_rate, build_performance_map, death_rate
from app.dna.recency import effective_sample_size, recency_weight, weighted_mean, weighted_median
from app.hero_portfolio.config import PORTFOLIO_CONFIG
from app.hero_portfolio.version import (
    HERO_EXPRESSIONS_VERSION,
    HERO_MATCHUPS_VERSION,
    HERO_RELATIONSHIPS_VERSION,
    HERO_RELIABILITY_VERSION,
    HERO_SITUATIONS_VERSION,
    HERO_SYNERGIES_VERSION,
    PATTERN_ACTIONS_VERSION,
)
from app.heroes.evidence import (
    representative_matchups,
    representative_synergies,
    situations_for_traits,
)
from app.heroes.knowledge import FUNCTIONAL_JOBS, HERO_DEMAND_FAMILIES, HeroKnowledgeProvider
from app.heroes.recommendations import HeroRecommendationRationale, recommend_semantic_heroes
from app.heroes.relationships import (
    build_pool_profile,
    candidate_traits,
    expression_difference,
    learning_distance,
    pool_similarity,
    role_compatibility,
    trait_label,
)
from app.heroes.taxonomy import HeroTaxonomy, HeroTaxonomyEntry
from app.ingestion.summary_normalize import NormalizedSummaryMatch

_JOB_TRAITS = (
    "initiation",
    "mobility",
    "pickoff",
    "teamfight",
    "save",
    "sustain",
    "burst",
    "sustained_damage",
    "wave_clear",
    "push",
    "frontline",
    "scaling",
    "global_presence",
    "repositioning",
)
_P03_DIRECT_SIGNALS = (
    ("death_exposure", "deaths per 10 minutes", 0.35),
    ("combat_involvement", "events per minute", 0.25),
    ("finisher_orientation", "kill share inside involvement", 0.18),
    ("result_distribution", "win share", 0.20),
)
_P03_DIRECT_MIN_CELL_SAMPLE = 10
# Reuse the existing moderate comparison boundary.  P03 has no separate
# reviewed numeric confidence calibration, so this is intentionally named and
# versioned with the action rather than becoming an inline magic number.
_P03_DIRECT_MIN_COMPARISON_CONFIDENCE = 0.50
_P03_DIRECT_MIN_COVERAGE = 0.50
_P03_CAPABILITIES = (
    ("frontline", "sustained frontline commitment"),
    ("micro_intensity", "micro intensity"),
    ("mobility", "mobility execution demand"),
    ("farm_dependency", "farm dependence"),
    ("initiation", "initiation cadence"),
    ("pickoff", "target-selective catch"),
    ("repositioning", "disengage and repositioning"),
    ("sustained_damage", "damage uptime"),
)
_P03_SEMANTIC_DEMANDS = (
    ("commitment", "commitment"),
    ("access", "access"),
    ("repositioning", "repositioning"),
    ("economy", "economy"),
    ("timing", "timing"),
    ("execution", "execution"),
    ("exposure", "exposure"),
    ("micro", "micro"),
)
_PRESENCE_MIN_SAMPLE = 5
_PRESENCE_FUNCTION_THRESHOLD = 0.68
_PRESENCE_ACTIVE_LEVEL = 0.60
_PRESENCE_SAFE_LEVEL = 0.40
_PRESENCE_EXPOSED_LEVEL = 0.60
_HIGH_CONTACT_FUNCTIONS = frozenset({"initiation", "frontline", "teamfight"})
_RECOVERY_ACTION_MIN_EFFECT = 0.04

_PROVENANCE_KEYS = {
    "pattern_actions": PATTERN_ACTIONS_VERSION,
    "hero_relationships": HERO_RELATIONSHIPS_VERSION,
    "hero_expressions": HERO_EXPRESSIONS_VERSION,
    "hero_reliability": HERO_RELIABILITY_VERSION,
    "hero_matchups": HERO_MATCHUPS_VERSION,
    "hero_synergies": HERO_SYNERGIES_VERSION,
    "hero_situations": HERO_SITUATIONS_VERSION,
}


def _action_evidence(
    *,
    status: Literal["resolved", "fallback", "unresolved", "not_applicable"],
    sample_size: int,
    confidence_score: float,
    coverage: float,
    effective_sample_size_value: float | None = None,
    independent_group_count: int | None = None,
    evidence_keys: tuple[str, ...] = (),
    limitations: tuple[str, ...] = (),
    baseline: bool = False,
    provenance_versions: dict[str, str] | None = None,
) -> PatternActionEvidence:
    versions = {"pattern_actions": PATTERN_ACTIONS_VERSION}
    if baseline:
        versions["context_baseline"] = CONTEXT_BASELINE_VERSION
    if provenance_versions:
        versions.update(provenance_versions)
    return PatternActionEvidence(
        status=status,
        sample_size=max(0, sample_size),
        effective_sample_size=max(
            0.0,
            float(effective_sample_size_value if effective_sample_size_value is not None else sample_size),
        ),
        coverage=max(0.0, min(1.0, coverage)),
        confidence_score=max(0.0, min(1.0, confidence_score)),
        independent_group_count=independent_group_count,
        evidence_keys=evidence_keys,
        limitations=limitations,
        provenance_versions=versions,
    )


def attach_pattern_actions(
    patterns: Sequence[PatternResult],
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    hero_knowledge: HeroKnowledgeProvider | None = None,
) -> tuple[PatternResult, ...]:
    """Attach only reviewed actions to qualified Pattern results."""

    result: list[PatternResult] = []
    for pattern in patterns:
        action: (
            SamePlaybookAction
            | ComfortEdgeAction
            | PartialTransferDiagnostic
            | VersatileCoreAction
            | ProvenFlexibilityAction
            | BouncebackAction
            | PerformanceSlideAction
            | ControlledPresenceAction
            | PresenceTaxAction
            | SessionCurveAction
            | None
        ) = None
        if pattern.status == "qualified":
            if pattern.key == "same_playbook":
                action = build_same_playbook_action(matches, taxonomy, hero_knowledge=hero_knowledge)
            elif pattern.key == "comfort_edge":
                action = build_comfort_edge_action(matches, taxonomy, hero_knowledge=hero_knowledge)
            elif pattern.key == "partial_transfer":
                action = build_partial_transfer_action(matches, taxonomy, hero_knowledge=hero_knowledge)
            elif pattern.key == "versatile_core":
                action = build_versatile_core_action(matches, taxonomy, hero_knowledge=hero_knowledge)
            elif pattern.key == "proven_flexibility":
                action = build_proven_flexibility_action(matches, taxonomy)
            elif pattern.key == "bounceback":
                action = build_bounceback_action(matches, taxonomy)
            elif pattern.key == "performance_slide":
                action = build_performance_slide_action(matches, taxonomy)
            elif pattern.key == "controlled_presence":
                action = build_controlled_presence_action(matches, taxonomy)
            elif pattern.key == "presence_tax":
                action = build_presence_tax_action(matches, taxonomy)
            elif pattern.key in {"session_fade", "session_rise"}:
                action = build_session_curve_action(
                    matches,
                    taxonomy,
                    direction="fade" if pattern.key == "session_fade" else "rise",
                )
        result.append(replace(pattern, action=action))
    return tuple(result)


def build_session_curve_action(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    *,
    direction: Literal["fade", "rise"],
) -> SessionCurveAction:
    """Build one breakpoint-oriented curve for either mirrored session Pattern."""

    values, _observations = build_performance_map(matches)
    grouped: dict[str, list[NormalizedSummaryMatch]] = {}
    for item in matches:
        if item.session_id is not None and not item.session_corrupt:
            grouped.setdefault(item.session_id, []).append(item)
    ordered_groups = [
        sorted(rows, key=lambda item: (item.session_index is None, item.session_index or 0, item.match_id))
        for rows in grouped.values()
        if len(rows) >= 2
    ]
    ordered_groups.sort(key=lambda rows: (rows[0].started_at or 0, rows[0].match_id))
    left_censored_session_id = ordered_groups[0][0].session_id if ordered_groups else None
    if ordered_groups:
        # The first observed session is left-censored by the yearly window in
        # the absence of a pre-window anchor; do not manufacture its Game 1.
        ordered_groups[0] = ordered_groups[0][1:] or []
    ordered_groups = [rows for rows in ordered_groups if rows]
    window_end = max((item.started_at or 0 for item in matches), default=0)
    weights_by_match = {
        item.match_id: (
            recency_weight(item.started_at, window_end=window_end)
            if item.started_at is not None and window_end
            else 1.0
        )
        for item in matches
    }
    session_records: dict[str, dict[str, list[float]]] = {}
    session_starts: dict[str, int] = {}
    session_all_rows = {session_id: rows for session_id, rows in grouped.items()}
    for session_id, rows in session_all_rows.items():
        usable = [item for item in rows if item.match_id in values]
        if len(usable) < 2:
            continue
        session_starts[session_id] = min(item.started_at or 0 for item in usable)
        outside = [item for other_id, other_rows in session_all_rows.items() if other_id != session_id for item in other_rows if item.match_id in values]
        if not outside:
            continue
        records: dict[str, list[float]] = {}
        for item in usable:
            position = item.session_index or 0
            bucket = _session_bucket(position)
            if bucket == "G1" and session_id == left_censored_session_id:
                continue
            resolution = resolve_leave_group_out_baseline(
                target=item,
                candidate_rows=outside,
                performance_by_match=values,
                taxonomy=taxonomy,
                weights_by_match=weights_by_match,
                exclusion_group_id=session_id,
            )
            if resolution is None:
                continue
            baseline = resolution.value
            records.setdefault(bucket, []).append(values[item.match_id] - baseline)
        if records:
            session_records[session_id] = records

    curve: list[SessionCurvePoint] = []
    curve_values: dict[str, float] = {}
    counts: dict[str, int] = {}
    for bucket in SESSION_BUCKETS:
        observations = [
            (session_id, sum(values_for_bucket) / len(values_for_bucket))
            for session_id, records in session_records.items()
            if (values_for_bucket := records.get(bucket))
        ]
        weights = [
            recency_weight(
                session_starts[session_id],
                window_end=window_end,
            )
            for session_id, _value in observations
        ]
        aggregate = weighted_mean([value for _session_id, value in observations], weights)
        session_count = len(observations)
        sample_count = sum(len(session_records[session_id][bucket]) for session_id, _value in observations)
        effective = effective_sample_size(weights)
        supported = aggregate is not None and session_count >= 3
        if aggregate is not None:
            curve_values[bucket] = aggregate
        counts[bucket] = session_count
        curve.append(
            SessionCurvePoint(
                bucket=bucket,
                relative_delta=aggregate or 0.0,
                sample_size=sample_count,
                effective_sample_size=effective,
                supported=supported,
            )
        )
    supported_curve = {item.bucket: item.relative_delta for item in curve if item.supported}
    supported_counts = {item.bucket: counts[item.bucket] for item in curve if item.supported}
    breakpoint = detect_breakpoint(
        supported_curve,
        direction=direction,
        counts=supported_counts,
    )
    supported_sessions = len(session_records)
    confidence = min(
        1.0,
        min(1.0, supported_sessions / 12.0)
        * min(1.0, len(supported_curve) / 3.0)
        * (1.0 if breakpoint.state == "stable_breakpoint" else 0.75 if breakpoint.state == "gradual" else 0.50),
    )
    status: Literal["resolved", "fallback", "unresolved", "not_applicable"] = (
        "resolved" if breakpoint.state == "stable_breakpoint" else "fallback" if breakpoint.state == "gradual" else "unresolved"
    )
    return SessionCurveAction(
        action_type="session_fade" if direction == "fade" else "session_rise",
        status=status,
        direction=direction,
        curve=tuple(curve),
        breakpoint_state=breakpoint.state,  # type: ignore[arg-type]
        breakpoint_bucket=breakpoint.bucket,
        companion_signals=_session_companion_signals(matches, values, direction),
        independent_session_count=supported_sessions,
        confidence_score=confidence,
        limitations=(
            "The curve is relative to comparable summary-history performance and is balanced by independent sessions.",
            "It does not establish fatigue, warm-up, momentum, focus, or a recommended stopping point.",
        ),
        evidence_summary=_action_evidence(
            status=status,
            sample_size=sum(item.sample_size for item in curve),
            effective_sample_size_value=float(supported_sessions),
            coverage=len(supported_curve) / len(SESSION_BUCKETS),
            confidence_score=confidence,
            independent_group_count=supported_sessions,
            evidence_keys=("summary.performance_proxy", "context_baseline", "session_curve"),
            baseline=True,
        ),
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


def _session_companion_signals(
    matches: Sequence[NormalizedSummaryMatch], values: dict[int, float], direction: Literal["fade", "rise"]
) -> tuple[str, ...]:
    early = [item for item in matches if item.session_index in {1, 2} and item.match_id in values]
    late = [item for item in matches if item.session_index is not None and item.session_index >= 3 and item.match_id in values]
    if not early or not late:
        return ()
    signals: list[str] = []
    early_activity = [value for item in early if (value := activity_rate(item)) is not None]
    late_activity = [value for item in late if (value := activity_rate(item)) is not None]
    early_deaths = [value for item in early if (value := death_rate(item)) is not None]
    late_deaths = [value for item in late if (value := death_rate(item)) is not None]
    if early_activity and late_activity:
        if median(late_activity) < median(early_activity) * 0.90:
            signals.append("Involvement moves down around the curve.")
        elif median(late_activity) > median(early_activity) * 1.10:
            signals.append("Involvement moves up around the curve.")
    if early_deaths and late_deaths:
        if median(late_deaths) > median(early_deaths) * 1.10:
            signals.append("Death exposure moves up around the curve.")
        elif median(late_deaths) < median(early_deaths) * 0.90:
            signals.append("Death exposure moves down around the curve.")
    return tuple(signals[:2])


def build_partial_transfer_action(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    *,
    hero_knowledge: HeroKnowledgeProvider | None = None,
) -> PartialTransferDiagnostic:
    """Explain a qualified P03 gap only to the strongest supported level."""

    core_ids, off_ids = _transfer_hero_sets(matches, taxonomy)
    core_rows = [item for item in matches if item.hero_id in core_ids]
    off_rows = [item for item in matches if item.hero_id in off_ids]
    direct: list[ObservedDifference] = []
    row_confidence = _comparison_confidence(core_rows, off_rows)
    for signal_key, _label, minimum_delta in _P03_DIRECT_SIGNALS:
        core_values = _p03_signal_values(core_rows, signal_key)
        off_values = _p03_signal_values(off_rows, signal_key)
        coverage = _p03_signal_coverage(
            len(core_values),
            len(off_values),
            len(core_rows),
            len(off_rows),
        )
        if (
            len(core_values) < _P03_DIRECT_MIN_CELL_SAMPLE
            or len(off_values) < _P03_DIRECT_MIN_CELL_SAMPLE
            or row_confidence < _P03_DIRECT_MIN_COMPARISON_CONFIDENCE
            or coverage < _P03_DIRECT_MIN_COVERAGE
        ):
            continue
        core_value = median(core_values)
        off_value = median(off_values)
        delta = off_value - core_value
        scale = max(_mad([*core_values, *off_values]), minimum_delta)
        effect_size = abs(delta) / scale
        if abs(delta) < minimum_delta or effect_size < 1.0:
            continue
        direct.append(
            ObservedDifference(
                signal_key=signal_key,
                core_value=core_value,
                off_pool_value=off_value,
                effect_size=effect_size,
                confidence_score=row_confidence,
                player_facing_claim=_p03_claim(signal_key, delta),
                coverage=coverage,
            )
        )
    direct.sort(key=lambda item: (-float(item.effect_size or 0.0), item.signal_key))

    hypotheses: list[CapabilityHypothesis] = []
    if not direct and core_ids and off_ids and row_confidence >= 0.50:
        capability_definitions = _P03_SEMANTIC_DEMANDS if hero_knowledge else _P03_CAPABILITIES
        for capability_key, display_name in capability_definitions:
            core_prevalence = _hero_capability_prevalence(
                core_ids, taxonomy, capability_key, hero_knowledge=hero_knowledge
            )
            off_prevalence = _hero_capability_prevalence(
                off_ids, taxonomy, capability_key, hero_knowledge=hero_knowledge
            )
            if core_prevalence is None or off_prevalence is None:
                continue
            separation = off_prevalence - core_prevalence
            confidence = min(
                row_confidence,
                min(1.0, len(core_ids) / 2.0),
                min(1.0, len(off_ids) / 2.0),
            )
            if separation < 0.25 or confidence < 0.50:
                continue
            hypotheses.append(
                CapabilityHypothesis(
                    capability_key=capability_key,
                    core_prevalence=core_prevalence,
                    off_pool_prevalence=off_prevalence,
                    separation_score=separation,
                    confidence_score=confidence,
                    player_facing_hypothesis=(
                        f"The best lead we can see is {display_name}. Your weaker hero set asks for "
                        f"more {display_name} than the heroes where your results hold best."
                    ),
                )
            )
    hypotheses.sort(key=lambda item: (-item.separation_score, item.capability_key))

    if direct:
        status: Literal["direct_signal", "capability_hypothesis", "unresolved", "deep_candidate"] = "direct_signal"
        lead = direct[0].player_facing_claim
        deep_eligible = False
    elif hypotheses:
        status = "capability_hypothesis"
        lead = hypotheses[0].player_facing_hypothesis
        deep_eligible = False
    elif len(core_rows) >= 12 and len(off_rows) >= 12:
        status = "deep_candidate"
        lead = "We found where the result gap appears. Deeper match evidence is needed to explain the mechanism."
        deep_eligible = True
    else:
        status = "unresolved"
        lead = "We found the gap. Not the cause."
        deep_eligible = False

    limitations: tuple[str, ...] = (
        "Free summary history can show observable differences or hero-demand differences, but it cannot establish positioning, item timing, spell usage, target choice, farming efficiency, or fight conversion.",
    )
    if hero_knowledge is not None:
        semantic_entries = [
            hero_knowledge.get(hero_id) for hero_id in sorted(core_ids | off_ids)
        ]
        if any(entry is None for entry in semantic_entries):
            limitations += (
                "Hero semantics are unavailable for part of the comparison pool; no demand hypothesis is inferred from missing records.",
            )
        elif any(
            entry is not None
            and any(value == "unknown" for value in entry.demands.values())
            for entry in semantic_entries
        ):
            limitations += (
                "Some demand families are unknown in the frozen hero snapshot; the hypothesis remains intentionally narrow.",
            )
    if not core_rows or not off_rows:
        limitations += ("The familiar and off-pool comparison cells are too sparse for a narrower lead.",)
    action_resolution: Literal["resolved", "fallback", "unresolved", "not_applicable"] = (
        "resolved" if status == "direct_signal" else "fallback" if status in {"capability_hypothesis", "deep_candidate"} else "unresolved"
    )
    direct_coverage = min((item.coverage for item in direct), default=0.0)
    return PartialTransferDiagnostic(
        action_type="partial_transfer",
        status=status,
        summary_differences=tuple(direct[:3]),
        capability_hypotheses=tuple(hypotheses[:3]),
        strongest_supported_lead=lead,
        core_hero_ids=tuple(sorted(core_ids)),
        off_pool_hero_ids=tuple(sorted(off_ids)),
        confidence_score=row_confidence,
        limitations=limitations,
        deep_analysis_eligible=deep_eligible,
        evidence_summary=_action_evidence(
            status=action_resolution,
            sample_size=len(core_rows) + len(off_rows),
            effective_sample_size_value=float(min(len(core_rows), len(off_rows))),
            coverage=direct_coverage if direct else (1.0 if core_rows and off_rows else 0.0),
            confidence_score=row_confidence,
            evidence_keys=("summary.hero", "summary.kda", "summary.outcome", "summary.time"),
        ),
    )


def build_versatile_core_action(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    *,
    hero_knowledge: HeroKnowledgeProvider | None = None,
) -> VersatileCoreAction:
    """Map the compact core, then recommend a real next tool or abstain."""

    core_ids = _core_hero_ids(matches, taxonomy, limit=5)
    profile = build_pool_profile(matches, taxonomy, hero_ids=core_ids)
    job_maps_list: list[HeroJobMap] = []
    for hero_id in core_ids:
        job_map = _hero_job_map(taxonomy.get(hero_id))
        if job_map is not None:
            job_maps_list.append(job_map)
    job_maps = tuple(job_maps_list)
    coverage = (
        _semantic_coverage_summary(core_ids, hero_knowledge)
        if hero_knowledge is not None
        else _coverage_summary(core_ids, taxonomy)
    )
    recommendation_candidates = (
        _semantic_addition_candidates(matches, hero_knowledge)
        if hero_knowledge is not None
        else _versatile_addition_candidates(matches, taxonomy, profile, coverage)
    )
    recommendation = recommendation_candidates[0] if recommendation_candidates else None
    alternatives = tuple(recommendation_candidates[1:3]) if recommendation else ()
    if recommendation is None:
        status: Literal[
            "coverage_only",
            "coverage_plus_recommendation",
            "coverage_plus_alternatives",
            "no_obvious_gap",
        ] = "no_obvious_gap" if not coverage.missing and not coverage.thin_coverage else "coverage_only"
    elif alternatives:
        status = "coverage_plus_alternatives"
    else:
        status = "coverage_plus_recommendation"
    limitations: list[str] = [
        "Jobs and expressions come from the reviewed, versioned hero-characteristics database; they describe available tools, not guaranteed execution.",
    ]
    if not core_ids:
        limitations.append("No taxonomy-covered core hero cleared the meaningful-history gate.")
    if recommendation is None and (coverage.missing or coverage.thin_coverage):
        limitations.append("No candidate cleared the role, learning-distance, expression, and redundancy gates without filler.")
    return VersatileCoreAction(
        action_type="versatile_core",
        status=status,
        core_hero_ids=tuple(core_ids),
        hero_job_maps=job_maps,
        coverage_summary=coverage,
        recommended_addition=recommendation,
        alternative_additions=alternatives,
        confidence_score=profile.confidence_score,
        limitations=tuple(limitations),
        evidence_summary=_action_evidence(
            status="resolved" if status == "no_obvious_gap" or recommendation is not None else "fallback",
            sample_size=len(matches),
            effective_sample_size_value=float(len(matches)),
            coverage=len(profile.hero_ids) / max(len(matches), 1),
            confidence_score=profile.confidence_score,
            evidence_keys=(
                "hero.knowledge" if hero_knowledge is not None else "hero.taxonomy",
                "hero.pool_profile",
                "hero.job_coverage",
            ),
            provenance_versions=(
                {"hero_knowledge": hero_knowledge.version}
                if hero_knowledge is not None
                else {}
            ),
        ),
    )


def build_proven_flexibility_action(
    matches: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy
) -> ProvenFlexibilityAction:
    """Find the strongest sufficiently active rolling seven-day flex window."""

    dated = [
        item
        for item in matches
        if item.hero_id is not None
        and item.started_at is not None
        and taxonomy.get(item.hero_id) is not None
        and taxonomy.get(item.hero_id).available  # type: ignore[union-attr]
    ]
    if not dated:
        return _distributed_flexibility_action(matches, taxonomy, "No dated taxonomy-covered matches can form a flex window.")
    dated.sort(key=lambda item: (item.started_at or 0, item.match_id))
    dates = sorted({_utc_date(item.started_at or 0) for item in dated})
    windows = [_flex_window(dated, start, taxonomy) for start in dates]
    eligible = [item for item in windows if item["total_games"] >= 10]
    if not eligible:
        return _distributed_flexibility_action(
            matches,
            taxonomy,
            "Your flexibility is spread out, not concentrated in one clear week. No seven-day stretch has enough activity to crown confidently.",
        )
    selected = max(
        eligible,
        key=lambda item: (
            item["score"],
            item["functional_job_count"],
            item["repeated_hero_count"],
            item["activity_confidence"],
            item["window_start"],
        ),
    )
    return ProvenFlexibilityAction(
        action_type="proven_flexibility",
        status="peak_window",
        window_start=selected["window_start"],
        window_end=selected["window_end"],
        total_games=selected["total_games"],
        hero_ids=selected["hero_ids"],
        hero_names=tuple(
            entry.name
            for hero_id in selected["hero_ids"]
            if (entry := taxonomy.get(hero_id)) is not None
        ),
        hero_game_counts=selected["hero_game_counts"],
        meaningful_hero_count=selected["meaningful_hero_count"],
        functional_jobs=selected["functional_jobs"],
        functional_job_count=selected["functional_job_count"],
        repeated_hero_count=selected["repeated_hero_count"],
        longest_same_hero_streak=selected["longest_same_hero_streak"],
        secondary_proof=selected["secondary_proof"],
        flex_week_score=selected["score"],
        activity_confidence=selected["activity_confidence"],
        distribution_quality=selected["distribution_quality"],
        confidence_score=min(1.0, 0.45 * selected["activity_confidence"] + 0.30 * selected["distribution_quality"] + 0.25 * min(1.0, selected["functional_job_count"] / 8.0)),
        limitations=(
            "The selected proof uses a rolling seven-day calendar window and rewards functional breadth, repeated participation, activity, and distribution rather than raw unique-hero count alone.",
        ),
        evidence_summary=_action_evidence(
            status="resolved",
            sample_size=int(selected["total_games"]),
            effective_sample_size_value=float(selected["total_games"]),
            coverage=1.0,
            confidence_score=min(1.0, 0.45 * selected["activity_confidence"] + 0.30 * selected["distribution_quality"] + 0.25 * min(1.0, selected["functional_job_count"] / 8.0)),
            evidence_keys=("summary.dated_history", "hero.taxonomy", "hero.functional_jobs"),
        ),
    )


def _transfer_hero_sets(
    matches: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy
) -> tuple[set[int], set[int]]:
    core = set(_core_hero_ids(matches, taxonomy, limit=10))
    covered = {
        int(item.hero_id)
        for item in matches
        if item.hero_id is not None
        and taxonomy.get(item.hero_id) is not None
        and taxonomy.get(item.hero_id).available  # type: ignore[union-attr]
    }
    return core, covered - core


def _core_hero_ids(
    matches: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy, *, limit: int
) -> tuple[int, ...]:
    counts = Counter(
        int(item.hero_id)
        for item in matches
        if item.hero_id is not None
        and taxonomy.get(item.hero_id) is not None
        and taxonomy.get(item.hero_id).available  # type: ignore[union-attr]
    )
    latest: dict[int, tuple[int, int]] = {}
    for item in matches:
        if item.hero_id is not None:
            latest[int(item.hero_id)] = max(
                latest.get(int(item.hero_id), (-1, -1)),
                (item.started_at or -1, item.match_id),
            )
    candidates = [item for item in counts.items() if item[1] >= 3]
    if not candidates:
        candidates = [item for item in counts.items() if item[1] >= 2]
    candidates.sort(
        key=lambda item: (
            -item[1],
            -latest.get(item[0], (-1, -1))[0],
            -latest.get(item[0], (-1, -1))[1],
            item[0],
        )
    )
    if not candidates:
        return ()
    target = max(1, sum(count for _hero_id, count in candidates) * 0.50)
    selected: list[int] = []
    total = 0
    for hero_id, count in candidates[:limit]:
        selected.append(hero_id)
        total += count
        if total >= target and len(selected) >= min(3, len(candidates)):
            break
    return tuple(selected[:limit])


def _p03_signal_values(rows: Sequence[NormalizedSummaryMatch], signal_key: str) -> list[float]:
    values: list[float] = []
    for item in rows:
        if item.duration_seconds is None or item.duration_seconds < 600:
            continue
        if signal_key == "result_distribution":
            if item.won is not None:
                values.append(1.0 if item.won else 0.0)
        elif signal_key == "death_exposure":
            if item.deaths is not None:
                values.append(item.deaths / max(item.duration_seconds / 60.0 / 10.0, 1e-9))
        elif signal_key == "combat_involvement":
            if item.kills is not None and item.assists is not None:
                values.append((item.kills + item.assists) / max(item.duration_seconds / 60.0, 1e-9))
        elif signal_key == "finisher_orientation":
            if item.kills is not None and item.assists is not None and item.kills + item.assists > 0:
                values.append(item.kills / (item.kills + item.assists))
    return values


def _p03_claim(signal_key: str, delta: float) -> str:
    if signal_key == "death_exposure":
        return (
            "Your presence transfers, but death exposure rises off-pool."
            if delta > 0
            else "Your off-pool games show lower death exposure despite the result gap."
        )
    if signal_key == "finisher_orientation":
        return (
            "You still reach the action, but you finish less of it."
            if delta < 0
            else "Your off-pool involvement leans more toward final kill credit."
        )
    if signal_key == "combat_involvement":
        return "Your fight activity changes meaningfully outside the familiar pool."
    return "The off-pool result distribution separates meaningfully from the familiar pool."


def _comparison_confidence(
    core_rows: Sequence[NormalizedSummaryMatch], off_rows: Sequence[NormalizedSummaryMatch]
) -> float:
    return min(1.0, min(len(core_rows), len(off_rows)) / 25.0)


def _p03_signal_coverage(
    core_usable: int,
    off_usable: int,
    core_rows: int,
    off_rows: int,
) -> float:
    """Coverage is usable signal rows divided by each comparison cell."""

    return min(
        core_usable / max(core_rows, 1),
        off_usable / max(off_rows, 1),
    )


def _hero_capability_prevalence(
    hero_ids: set[int],
    taxonomy: HeroTaxonomy,
    capability_key: str,
    *,
    hero_knowledge: HeroKnowledgeProvider | None = None,
) -> float | None:
    if not hero_ids:
        return None
    if hero_knowledge is not None:
        known = 0
        covered = 0
        for hero_id in hero_ids:
            entry = hero_knowledge.get(hero_id)
            if entry is None:
                continue
            band = entry.demands.get(capability_key)
            if band == "unknown" or band is None:
                continue
            known += 1
            covered += band in {"medium", "high"}
        return covered / known if known else None
    covered = sum(
        1
        for hero_id in hero_ids
        if (entry := taxonomy.get(hero_id)) is not None and entry.traits.get(capability_key, 0.0) >= 0.68
    )
    return covered / len(hero_ids)


def _hero_job_map(entry: HeroTaxonomyEntry | None) -> HeroJobMap | None:
    if entry is None or not entry.available:
        return None
    ranked = sorted(
        (
            (entry.traits.get(trait, 0.0), trait)
            for trait in _JOB_TRAITS
            if entry.traits.get(trait, 0.0) >= 0.60
        ),
        reverse=True,
    )
    if not ranked:
        ranked = sorted(
            ((entry.traits.get(trait, 0.0), trait) for trait in _JOB_TRAITS),
            reverse=True,
        )[:2]
    jobs = tuple(trait_label(trait) for _value, trait in ranked[:4])
    if len(jobs) >= 2:
        expression = f"A {jobs[0]} and {jobs[1]} expression of this hero's toolkit."
    elif jobs:
        expression = f"A focused {jobs[0]} expression of this hero's toolkit."
    else:
        expression = None
    return HeroJobMap(entry.hero_id, entry.name, jobs, expression)


def _coverage_summary(core_ids: Sequence[int], taxonomy: HeroTaxonomy) -> CoverageSummary:
    counts = Counter(
        trait
        for hero_id in core_ids
        if (entry := taxonomy.get(hero_id)) is not None
        for trait in _JOB_TRAITS
        if entry.traits.get(trait, 0.0) >= 0.60
    )
    strong_gate = max(2, (len(core_ids) + 1) // 2)
    strong = tuple(sorted(trait_label(key) for key, value in counts.items() if value >= strong_gate))
    single = tuple(sorted(trait_label(key) for key, value in counts.items() if value == 1))
    thin = tuple(sorted(trait_label(key) for key, value in counts.items() if value == 2))
    missing = tuple(sorted(trait_label(key) for key in _JOB_TRAITS if counts.get(key, 0) == 0))
    return CoverageSummary(strong, single, thin, missing)


def _semantic_coverage_summary(
    core_ids: Sequence[int], provider: HeroKnowledgeProvider
) -> CoverageSummary:
    counts = Counter(
        job
        for hero_id in core_ids
        if (entry := provider.get(hero_id)) is not None
        for job in (*entry.primary_functions, *entry.secondary_functions)
    )
    strong_gate = max(2, (len(core_ids) + 1) // 2)
    strong = tuple(
        job_display_label(key)
        for key in FUNCTIONAL_JOBS
        if counts.get(key, 0) >= strong_gate
    )
    single = tuple(job_display_label(key) for key in FUNCTIONAL_JOBS if counts.get(key, 0) == 1)
    thin = tuple(job_display_label(key) for key in FUNCTIONAL_JOBS if counts.get(key, 0) == 2)
    missing = tuple(job_display_label(key) for key in FUNCTIONAL_JOBS if counts.get(key, 0) == 0)
    return CoverageSummary(strong, single, thin, missing)


def _semantic_addition_candidates(
    matches: Sequence[NormalizedSummaryMatch],
    provider: HeroKnowledgeProvider,
) -> list[HeroAdditionRecommendation]:
    rationales = recommend_semantic_heroes(
        matches,
        provider,
        intent="fill_gap",
        limit=3,
    )
    return [_addition_from_rationale(rationale, provider) for rationale in rationales]


def _addition_from_rationale(
    rationale: HeroRecommendationRationale,
    provider: HeroKnowledgeProvider,
) -> HeroAdditionRecommendation:
    entry = provider.get(rationale.hero_id)
    if entry is None:
        raise ValueError(f"Semantic recommendation references unknown hero {rationale.hero_id}")
    adds = tuple(job_display_label(key) for key in rationale.adds[:4])
    anchors = tuple(job_display_label(key) for key in rationale.familiar_anchors[:3])
    first_add = adds[0] if adds else "a distinct functional job"
    confidence = {"high": 0.90, "medium": 0.65, "low": 0.25}[rationale.confidence]
    return HeroAdditionRecommendation(
        hero_id=entry.hero_id,
        hero_name=entry.display_name,
        adds_jobs=adds,
        shared_anchors=anchors,
        solves_gap=f"adds {first_add} to the current core",
        player_facing_reason=(
            f"{entry.display_name} keeps {', '.join(anchors) or 'a reviewed anchor'} "
            f"and adds {', '.join(adds) or 'a new functional job'}."
        ),
        confidence_score=confidence,
        semantic_rationale=rationale,
    )


def _versatile_addition_candidates(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    profile: Any,
    coverage: CoverageSummary,
) -> list[HeroAdditionRecommendation]:
    label_to_key = {trait_label(key): key for key in _JOB_TRAITS}
    gap_labels = (*coverage.missing, *coverage.thin_coverage, *coverage.single_point_coverage)
    gap_keys = tuple(label_to_key[label] for label in gap_labels if label in label_to_key)
    candidates: list[tuple[float, HeroAdditionRecommendation]] = []
    core_ids = set(profile.hero_ids)
    for entry in sorted(taxonomy.heroes.values(), key=lambda item: item.hero_id):
        if not entry.available or entry.hero_id in core_ids:
            continue
        added_keys = tuple(key for key in gap_keys if entry.traits.get(key, 0.0) >= 0.60)
        expression = expression_difference(entry, profile)
        if not added_keys and not expression:
            continue
        anchors = tuple(
            trait
            for trait in profile.dominant_traits
            if entry.traits.get(trait, 0.0) >= 0.55
        )
        role_fit = role_compatibility(entry, profile)
        distance = learning_distance(entry, profile)
        similarity = pool_similarity(entry, profile)
        gap_score = min(1.0, len(added_keys) / 3.0)
        expression_score = min(1.0, len(expression) / 3.0)
        redundancy = max(0.0, similarity - 0.90)
        score = 0.42 * gap_score + 0.20 * expression_score + 0.20 * role_fit + 0.18 * (1.0 - distance) - redundancy
        confidence = min(1.0, profile.confidence_score * (0.70 + 0.30 * role_fit) * (1.0 - 0.25 * distance))
        if score < 0.35 or confidence < 0.35:
            continue
        adds = tuple(trait_label(key) for key in added_keys[:4]) or expression[:3]
        anchors_display = tuple(trait_label(key) for key in anchors[:3])
        solves_gap = adds[0] if adds else "a distinct expression of an existing job"
        recommendation = HeroAdditionRecommendation(
            hero_id=entry.hero_id,
            hero_name=entry.name,
            adds_jobs=adds,
            shared_anchors=anchors_display,
            solves_gap=f"adds {solves_gap} to the current core",
            player_facing_reason=(
                f"{entry.name} adds {', '.join(adds)} while keeping "
                f"{', '.join(anchors_display) if anchors_display else 'a nearby learning distance'} familiar."
            ),
            confidence_score=confidence,
        )
        candidates.append((score, recommendation))
    candidates.sort(key=lambda item: (-item[0], -item[1].confidence_score, item[1].hero_id))
    return [item[1] for item in candidates]


def _flex_window(
    rows: Sequence[NormalizedSummaryMatch], start: date, taxonomy: HeroTaxonomy
) -> dict[str, Any]:
    end = start + timedelta(days=6)
    window_rows = [
        item
        for item in rows
        if item.started_at is not None
        and start <= _utc_date(item.started_at) <= end
    ]
    counts = Counter(int(item.hero_id) for item in window_rows if item.hero_id is not None)
    jobs = {
        trait
        for hero_id in counts
        if (entry := taxonomy.get(hero_id)) is not None
        for trait in _JOB_TRAITS
        if entry.traits.get(trait, 0.0) >= 0.60
    }
    distribution = _distribution_quality(counts)
    total = len(window_rows)
    activity = min(1.0, total / 10.0)
    hero_diversity = min(1.0, len(counts) / max(3.0, total * 0.45))
    job_diversity = min(1.0, len(jobs) / 8.0)
    score = hero_diversity * max(0.50, job_diversity) * activity * distribution
    streak = _longest_same_hero_streak(window_rows)
    repeated = sum(count >= 2 for count in counts.values())
    secondary = (
        f"{repeated} of the {len(counts)} heroes appeared more than once."
        if repeated
        else f"Longest same-hero streak: {streak} game{'s' if streak != 1 else ''}."
    )
    return {
        "window_start": start,
        "window_end": end,
        "total_games": total,
        "hero_ids": tuple(sorted(counts)),
        "hero_game_counts": tuple(sorted(counts.items())),
        "meaningful_hero_count": len(counts),
        "functional_jobs": tuple(sorted(trait_label(key) for key in jobs)),
        "functional_job_count": len(jobs),
        "repeated_hero_count": repeated,
        "longest_same_hero_streak": streak,
        "secondary_proof": secondary if counts else None,
        "score": score,
        "activity_confidence": activity,
        "distribution_quality": distribution,
    }


def _distributed_flexibility_action(
    matches: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy, reason: str
) -> ProvenFlexibilityAction:
    rows = [
        item
        for item in matches
        if item.hero_id is not None
        and taxonomy.get(item.hero_id) is not None
        and taxonomy.get(item.hero_id).available  # type: ignore[union-attr]
    ]
    counts = Counter(int(item.hero_id) for item in rows if item.hero_id is not None)
    jobs = {
        trait
        for hero_id in counts
        if (entry := taxonomy.get(hero_id)) is not None
        for trait in _JOB_TRAITS
        if entry.traits.get(trait, 0.0) >= 0.60
    }
    return ProvenFlexibilityAction(
        action_type="proven_flexibility",
        status="distributed_flexibility",
        window_start=None,
        window_end=None,
        total_games=len(rows),
        hero_ids=tuple(sorted(counts)),
        hero_names=tuple(
            entry.name
            for hero_id in sorted(counts)
            if (entry := taxonomy.get(hero_id)) is not None
        ),
        hero_game_counts=tuple(sorted(counts.items())),
        meaningful_hero_count=len(counts),
        functional_jobs=tuple(sorted(trait_label(key) for key in jobs)),
        functional_job_count=len(jobs),
        repeated_hero_count=sum(count >= 2 for count in counts.values()),
        longest_same_hero_streak=_longest_same_hero_streak(rows),
        secondary_proof=None,
        flex_week_score=None,
        activity_confidence=min(1.0, len(rows) / 10.0),
        distribution_quality=_distribution_quality(counts) if counts else None,
        confidence_score=0.0,
        limitations=(reason,),
        evidence_summary=_action_evidence(
            status="fallback",
            sample_size=len(rows),
            effective_sample_size_value=float(len(rows)),
            coverage=1.0 if rows else 0.0,
            confidence_score=0.0,
            evidence_keys=("summary.dated_history", "hero.taxonomy", "hero.functional_jobs"),
        ),
    )


def _distribution_quality(counts: Counter[int]) -> float:
    if len(counts) <= 1:
        return 0.0
    total = sum(counts.values())
    entropy = -sum((count / total) * log(count / total) for count in counts.values())
    return min(1.0, entropy / max(log(len(counts)), 1e-9))


def _longest_same_hero_streak(rows: Sequence[NormalizedSummaryMatch]) -> int:
    ordered = sorted(rows, key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id))
    longest = current = 0
    previous_hero: int | None = None
    for item in ordered:
        hero_id = item.hero_id
        if hero_id is None:
            continue
        current = current + 1 if hero_id == previous_hero else 1
        longest = max(longest, current)
        previous_hero = hero_id
    return longest


def _mad(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    centre = median(values)
    return median([abs(value - centre) for value in values])


def _utc_date(timestamp: int) -> date:
    return datetime.fromtimestamp(timestamp, tz=UTC).date()


def build_bounceback_action(
    matches: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy
) -> BouncebackAction:
    """Show the strongest confidence-qualified positive Recovery context."""

    contexts = _recovery_action_contexts(matches, taxonomy, direction="positive")
    strongest = contexts[0] if contexts else None
    return BouncebackAction(
        action_type="bounceback",
        strongest_context=strongest,
        comparison_contexts=tuple(contexts[:4]),
        fallback_level=_recovery_fallback_level(strongest),
        confidence_score=strongest.confidence_score if strongest else 0.0,
        limitations=(
            "This is a comparable summary-performance breakdown after a loss; it does not infer resilience, confidence, emotion, intent, or a hero causing the result.",
            "Hero and function contexts need their own sample and independent-session gates; otherwise the action falls back to a broader context.",
        ),
        evidence_summary=_recovery_action_evidence(contexts, strongest, direction="positive"),
    )


def build_performance_slide_action(
    matches: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy
) -> PerformanceSlideAction:
    """Show the strongest confidence-qualified negative Recovery context."""

    contexts = _recovery_action_contexts(matches, taxonomy, direction="negative")
    strongest = contexts[0] if contexts else None
    return PerformanceSlideAction(
        action_type="performance_slide",
        strongest_context=strongest,
        comparison_contexts=tuple(contexts[:4]),
        fallback_level=_recovery_fallback_level(strongest),
        confidence_score=strongest.confidence_score if strongest else 0.0,
        limitations=(
            "This is a comparable summary-performance breakdown after a loss; it does not infer tilt, choking, mental weakness, emotion, intent, or a hero causing the result.",
            "Hero and function contexts need their own sample and independent-session gates; otherwise the action falls back to a broader context.",
        ),
        evidence_summary=_recovery_action_evidence(contexts, strongest, direction="negative"),
    )


def _recovery_action_evidence(
    contexts: Sequence[RecoveryContext],
    strongest: RecoveryContext | None,
    *,
    direction: Literal["positive", "negative"],
) -> PatternActionEvidence:
    del direction  # The common envelope describes evidence, not direction.
    return _action_evidence(
        status=(
            "unresolved"
            if strongest is None
            else "fallback"
            if _recovery_fallback_level(strongest) != "hero"
            else "resolved"
        ),
        sample_size=sum(item.sample_size for item in contexts),
        effective_sample_size_value=float(sum(item.session_count for item in contexts)),
        coverage=1.0 if contexts else 0.0,
        confidence_score=strongest.confidence_score if strongest else 0.0,
        independent_group_count=sum(item.session_count for item in contexts) if contexts else 0,
        evidence_keys=("summary.performance_proxy", "context_baseline", "post_loss_transition"),
        baseline=True,
    )


def _recovery_action_contexts(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    *,
    direction: Literal["positive", "negative"],
) -> tuple[RecoveryContext, ...]:
    """Compare post-loss games with a leave-session-out context baseline.

    The baseline is resolved per target row, from the narrowest available
    hero/function/role context and then widened to overall.  It is built from
    other sessions only, so neither the target result nor its neighbouring
    games can leak into the reference distribution.
    """
    valid = [
        item
        for item in matches
        if item.session_id is not None
        and not item.session_corrupt
        and item.duration_seconds is not None
        and item.duration_seconds >= 600
        and item.won is not None
        and item.kills is not None
        and item.assists is not None
    ]
    if not valid:
        return ()
    performance, _observations = build_performance_map(valid)
    valid_by_id = {item.match_id: item for item in valid}
    sessions: dict[str, list[NormalizedSummaryMatch]] = {}
    for item in matches:
        if item.session_id is not None and not item.session_corrupt:
            sessions.setdefault(item.session_id, []).append(item)
    window_end = max((item.started_at or 0 for item in matches), default=0)
    weights_by_match = {
        item.match_id: (
            recency_weight(item.started_at, window_end=window_end)
            if item.started_at is not None and window_end
            else 1.0
        )
        for item in matches
    }
    grouped: dict[tuple[str, int | str], dict[str, Any]] = {}
    for session_id, session_rows in sessions.items():
        ordered = sorted(session_rows, key=lambda item: (item.session_index is None, item.session_index or 0, item.started_at or 0, item.match_id))
        outside = [
            item
            for other_id, other_rows in sessions.items()
            if other_id != session_id
            for item in other_rows
            if item.match_id in performance
        ]
        if not outside:
            continue
        for previous, current in zip(ordered, ordered[1:], strict=False):
            if (
                previous.match_id not in valid_by_id
                or current.match_id not in valid_by_id
                or current.match_id not in performance
                or previous.won is None
                or previous.won
            ):
                continue
            resolution = resolve_leave_group_out_baseline(
                target=current,
                candidate_rows=outside,
                performance_by_match=performance,
                taxonomy=taxonomy,
                weights_by_match=weights_by_match,
                exclusion_group_id=session_id,
            )
            if resolution is None:
                continue
            spec = _recovery_spec_for_level(current, taxonomy, resolution.level)
            baseline = resolution.value
            kind, identity, label, hero_id, function_family, role_context, primary_jobs = spec
            group = grouped.setdefault(
                (kind, identity),
                {
                    "kind": kind,
                    "label": label,
                    "hero_id": hero_id,
                    "function_family": function_family,
                    "role_context": role_context,
                    "primary_jobs": primary_jobs,
                    "records": [],
                },
            )
            group["records"].append((current, performance[current.match_id], baseline))

    contexts: list[RecoveryContext] = []
    for group in grouped.values():
        loss_rows = group["records"]
        if not loss_rows:
            continue
        records_by_session: dict[str, list[tuple[NormalizedSummaryMatch, float, float]]] = {}
        for record in loss_rows:
            item, value, row_baseline = record
            if item.session_id is not None:
                records_by_session.setdefault(item.session_id, []).append(record)
        session_deltas: list[float] = []
        session_weights: list[float] = []
        session_baselines: list[float] = []
        session_observed: list[float] = []
        for _session_id, records in sorted(records_by_session.items()):
            row_weights = [weights_by_match.get(item.match_id, 1.0) for item, _value, _baseline in records]
            session_delta = weighted_median(
                [value - row_baseline for _item, value, row_baseline in records],
                row_weights,
            )
            if session_delta is None:
                continue
            session_deltas.append(session_delta)
            session_weights.append(
                recency_weight(
                    min((item.started_at or 0 for item, _value, _baseline in records), default=0),
                    window_end=window_end,
                )
                if window_end
                else 1.0
            )
            session_baselines.append(
                weighted_median(
                    [row_baseline for _item, _value, row_baseline in records],
                    row_weights,
                )
                or 0.0
            )
            session_observed.append(
                weighted_median(
                    [value for _item, value, _baseline in records],
                    row_weights,
                )
                or 0.0
            )
        baseline = weighted_median(session_baselines, session_weights) or 0.0
        observed = weighted_median(session_observed, session_weights) or 0.0
        delta = weighted_median(session_deltas, session_weights) or 0.0
        session_count = len(session_deltas)
        kind = str(group["kind"])
        minimum_sample = 15 if kind == "overall" else 8 if kind in {"function", "role"} else 5
        minimum_sessions = 3 if kind != "hero" else 2
        if len(loss_rows) < minimum_sample or session_count < minimum_sessions or len(session_deltas) < 3:
            continue
        if direction == "positive" and delta < _RECOVERY_ACTION_MIN_EFFECT:
            continue
        if direction == "negative" and delta > -_RECOVERY_ACTION_MIN_EFFECT:
            continue
        confidence = min(
            1.0,
            min(1.0, len(loss_rows) / 20.0)
            * min(1.0, session_count / 5.0)
            * min(1.0, len(session_deltas) / 5.0),
        )
        contexts.append(
            RecoveryContext(
                label=str(group["label"]),
                hero_id=group["hero_id"],
                function_family=group["function_family"],
                role_context=group["role_context"],
                performance_delta=delta,
                baseline_performance=baseline,
                observed_performance=observed,
                sample_size=len(loss_rows),
                session_count=session_count,
                primary_jobs=tuple(group["primary_jobs"]),
                confidence_score=confidence,
            )
        )
    contexts.sort(
        key=lambda item: (
            _recovery_specificity(item),
            -item.performance_delta if direction == "positive" else item.performance_delta,
            -item.confidence_score,
            item.label,
        )
    )
    return tuple(contexts)


def _recovery_action_specs(
    item: NormalizedSummaryMatch, taxonomy: HeroTaxonomy
) -> tuple[tuple[str, int | str, str, int | None, str | None, str | None, tuple[str, ...]], ...]:
    specs: list[tuple[str, int | str, str, int | None, str | None, str | None, tuple[str, ...]]] = []
    entry = taxonomy.get(item.hero_id)
    jobs = _hero_jobs(entry) if entry is not None and entry.available else ()
    if entry is not None and entry.available:
        primary = primary_function(item, taxonomy)
        if primary is not None and item.role_hint:
            specs.append(
                (
                    "hero_role_function",
                    entry.hero_id,
                    entry.name,
                    entry.hero_id,
                    primary,
                    item.role_hint,
                    jobs,
                )
            )
        if primary is not None:
            specs.append(
                ("hero_function", entry.hero_id, entry.name, entry.hero_id, primary, None, jobs)
            )
        if primary is not None:
            specs.append(("function", primary, trait_label(primary), None, primary, None, jobs))
    if item.role_hint:
        specs.append(("role", item.role_hint, item.role_hint, None, None, item.role_hint, jobs))
    specs.append(("overall", "overall", "Overall", None, None, None, jobs))
    return tuple(specs)


def _recovery_spec_for_level(
    item: NormalizedSummaryMatch,
    taxonomy: HeroTaxonomy,
    level: str,
) -> tuple[str, int | str, str, int | None, str | None, str | None, tuple[str, ...]]:
    for spec in _recovery_action_specs(item, taxonomy):
        if spec[0] == level:
            return spec
    entry = taxonomy.get(item.hero_id)
    return ("overall", "overall", "Overall", None, None, None, _hero_jobs(entry) if entry else ())


def _hero_jobs(entry: HeroTaxonomyEntry) -> tuple[str, ...]:
    ranked = sorted(
        ((entry.traits.get(trait, 0.0), trait) for trait in _JOB_TRAITS if entry.traits.get(trait, 0.0) >= 0.60),
        reverse=True,
    )
    return tuple(trait_label(trait) for _value, trait in ranked[:4])


def _recovery_specificity(context: RecoveryContext) -> int:
    if context.hero_id is not None:
        return 0
    if context.function_family is not None:
        return 1
    if context.role_context is not None:
        return 2
    return 3


def _recovery_fallback_level(context: RecoveryContext | None) -> Literal["hero", "function", "role", "overall"]:
    if context is None:
        return "overall"
    if context.hero_id is not None:
        return "hero"
    if context.function_family is not None:
        return "function"
    if context.role_context is not None:
        return "role"
    return "overall"


def build_controlled_presence_action(
    matches: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy
) -> ControlledPresenceAction:
    contexts = _presence_contexts(matches, taxonomy)
    candidates = [
        item
        for item in contexts
        if item.involvement_level >= _PRESENCE_ACTIVE_LEVEL
        and item.death_exposure_level <= _PRESENCE_SAFE_LEVEL
    ]
    if not candidates:
        return ControlledPresenceAction(
            "controlled_presence", None, (), None, "overall", 0.0,
            ("No hero, function, or role subgroup cleared both the high-involvement and low-exposure gates; show the overall Pattern only. This relationship does not prove positioning quality.",),
            evidence_summary=_presence_action_evidence(contexts, None),
        )
    ranked = sorted(
        candidates,
        key=lambda item: (
            _presence_specificity(item),
            -(item.involvement_level - item.death_exposure_level),
            -item.confidence_score,
            item.label,
        ),
    )
    strongest = ranked[0]
    return ControlledPresenceAction(
        action_type="controlled_presence",
        strongest_context=strongest,
        comparison_rows=tuple(ranked[:3]),
        finishing_flavor=_finishing_flavor(matches),
        fallback_level=_presence_fallback_level(strongest),
        confidence_score=strongest.confidence_score,
        limitations=("This relationship does not prove positioning quality, teamfight skill, or the value of any individual death.",),
        evidence_summary=_presence_action_evidence(contexts, strongest),
    )


def build_presence_tax_action(
    matches: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy
) -> PresenceTaxAction:
    contexts = _presence_contexts(matches, taxonomy)
    involved = [item for item in contexts if item.involvement_level >= _PRESENCE_ACTIVE_LEVEL]
    exposed = [item for item in involved if item.death_exposure_level >= _PRESENCE_EXPOSED_LEVEL]
    exposed.sort(key=lambda item: (-item.death_exposure_level, -_presence_specificity(item), -item.confidence_score, item.label))
    if not exposed:
        return PresenceTaxAction(
            "presence_tax", "unresolved", (), (), False, 0.0,
            ("The global Pattern qualifies, but subgroup evidence is too sparse to localize the exposure.",),
            evidence_summary=_presence_action_evidence(contexts, None),
        )
    function_rows = [item for item in exposed if item.function_family is not None]
    high_contact_rows = [item for item in function_rows if item.function_family in _HIGH_CONTACT_FUNCTIONS]
    other_function_rows = [item for item in function_rows if item.function_family not in _HIGH_CONTACT_FUNCTIONS]
    top = exposed[0]
    shape = "unresolved"
    hero_specific_gap = _hero_function_exposure_gap(matches, taxonomy)
    if hero_specific_gap >= 0.18:
        shape = "hero_specific"
    elif high_contact_rows and not other_function_rows:
        shape = "job_shaped"
    elif len({item.function_family for item in function_rows}) >= 2:
        shape = "cross_context"
    elif high_contact_rows:
        shape = "job_shaped"
    deep_candidate = shape != "unresolved"
    return PresenceTaxAction(
        action_type="presence_tax",
        shape=shape,  # type: ignore[arg-type]
        strongest_contexts=tuple(exposed[:2]),
        comparison_contexts=tuple(exposed[:4]),
        deep_analysis_candidate=deep_candidate,
        confidence_score=top.confidence_score,
        limitations=("Summary history localizes the death cost but cannot establish positioning, fight selection, timing, target choice, or whether deaths were useful.",),
        evidence_summary=_action_evidence(
            status="resolved" if shape != "unresolved" else "unresolved",
            sample_size=sum(item.sample_size for item in exposed),
            effective_sample_size_value=float(sum(item.sample_size for item in exposed)),
            coverage=1.0 if exposed else 0.0,
            confidence_score=top.confidence_score,
            independent_group_count=None,
            evidence_keys=("summary.kda", "summary.time", "presence_context"),
        ),
    )


def _presence_action_evidence(
    contexts: Sequence[PresenceContext], strongest: PresenceContext | None
) -> PatternActionEvidence:
    fallback = _presence_fallback_level(strongest)
    return _action_evidence(
        status="unresolved" if strongest is None else "fallback" if fallback != "hero" else "resolved",
        sample_size=sum(item.sample_size for item in contexts),
        effective_sample_size_value=float(sum(item.sample_size for item in contexts)),
        coverage=1.0 if contexts else 0.0,
        confidence_score=strongest.confidence_score if strongest else 0.0,
        evidence_keys=("summary.kda", "summary.time", "presence_context"),
    )


def _presence_contexts(
    matches: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy
) -> tuple[PresenceContext, ...]:
    usable = [
        item
        for item in matches
        if item.hero_id
        and item.duration_seconds
        and item.duration_seconds >= 600
        and item.kills is not None
        and item.assists is not None
        and item.deaths is not None
    ]
    groups: dict[tuple[str, str, int | None, str | None, str | None], list[NormalizedSummaryMatch]] = {}
    for item in usable:
        groups.setdefault(("overall", "Overall", None, None, None), []).append(item)
        hero_id = item.hero_id
        if hero_id is None:
            continue
        entry = taxonomy.get(hero_id)
        if entry is None or not entry.available:
            continue
        groups.setdefault(("hero", entry.name, entry.hero_id, None, None), []).append(item)
        for family in _JOB_TRAITS:
            if entry.traits.get(family, 0.0) >= _PRESENCE_FUNCTION_THRESHOLD:
                groups.setdefault(("function", trait_label(family), None, family, None), []).append(item)
        if item.role_hint:
            groups.setdefault(("role", item.role_hint, None, None, item.role_hint), []).append(item)
    rows: list[PresenceContext] = []
    for group_key, items in groups.items():
        if len(items) < _PRESENCE_MIN_SAMPLE:
            continue
        minutes = sum(float(item.duration_seconds or 0) / 60.0 for item in items)
        involvement = sum((item.kills or 0) + (item.assists or 0) for item in items) / max(minutes, 1.0)
        deaths = sum(item.deaths or 0 for item in items) / max(minutes / 10.0, 1.0)
        rows.append(PresenceContext(group_key[1], group_key[2], group_key[3], group_key[4], min(1.0, involvement / 1.2), min(1.0, deaths / 1.2), len(items), min(1.0, len(items) / 20.0)))
    return tuple(rows)


def _hero_function_exposure_gap(
    matches: Sequence[NormalizedSummaryMatch], taxonomy: HeroTaxonomy
) -> float:
    usable = _presence_usable_matches(matches)
    hero_groups: dict[tuple[int, str], list[NormalizedSummaryMatch]] = {}
    function_groups: dict[str, list[NormalizedSummaryMatch]] = {}
    for item in usable:
        hero_id = item.hero_id
        if hero_id is None:
            continue
        entry = taxonomy.get(hero_id)
        family = _presence_primary_function(entry)
        if entry is None or family is None:
            continue
        hero_groups.setdefault((entry.hero_id, family), []).append(item)
        function_groups.setdefault(family, []).append(item)
    strongest_gap = 0.0
    for (hero_id, family), hero_rows in hero_groups.items():
        peers = [item for item in function_groups.get(family, ()) if item.hero_id != hero_id]
        if len(hero_rows) < _PRESENCE_MIN_SAMPLE or len(peers) < _PRESENCE_MIN_SAMPLE:
            continue
        hero_involvement, hero_deaths = _presence_levels(hero_rows)
        _peer_involvement, peer_deaths = _presence_levels(peers)
        if hero_involvement >= _PRESENCE_ACTIVE_LEVEL and hero_deaths >= _PRESENCE_EXPOSED_LEVEL:
            strongest_gap = max(strongest_gap, hero_deaths - peer_deaths)
    return strongest_gap


def _presence_usable_matches(
    matches: Sequence[NormalizedSummaryMatch],
) -> list[NormalizedSummaryMatch]:
    return [
        item
        for item in matches
        if item.hero_id
        and item.duration_seconds
        and item.duration_seconds >= 600
        and item.kills is not None
        and item.assists is not None
        and item.deaths is not None
    ]


def _presence_levels(items: Sequence[NormalizedSummaryMatch]) -> tuple[float, float]:
    minutes = sum(float(item.duration_seconds or 0) / 60.0 for item in items)
    involvement = sum((item.kills or 0) + (item.assists or 0) for item in items) / max(minutes, 1.0)
    deaths = sum(item.deaths or 0 for item in items) / max(minutes / 10.0, 1.0)
    return min(1.0, involvement / 1.2), min(1.0, deaths / 1.2)


def _presence_primary_function(entry: HeroTaxonomyEntry | None) -> str | None:
    if entry is None or not entry.available:
        return None
    ranked = sorted(
        ((entry.traits.get(family, 0.0), family) for family in _JOB_TRAITS),
        reverse=True,
    )
    return ranked[0][1] if ranked and ranked[0][0] >= _PRESENCE_FUNCTION_THRESHOLD else None


def _presence_specificity(context: PresenceContext) -> int:
    if context.hero_id is not None:
        return 0
    if context.function_family is not None:
        return 1
    if context.role_context is not None:
        return 2
    return 3


def _presence_fallback_level(context: PresenceContext | None) -> Literal["hero", "function", "role", "overall"]:
    if context is None:
        return "overall"
    if context.hero_id is not None:
        return "hero"
    if context.function_family is not None:
        return "function"
    if context.role_context is not None:
        return "role"
    return "overall"


def _finishing_flavor(matches: Sequence[NormalizedSummaryMatch]) -> str | None:
    kills = sum(item.kills or 0 for item in matches)
    assists = sum(item.assists or 0 for item in matches)
    if kills + assists < 30:
        return None
    return "controlled_finishing_presence" if kills / (kills + assists) >= 0.45 else "controlled_setup_presence"


def build_same_playbook_action(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    *,
    hero_knowledge: HeroKnowledgeProvider | None = None,
) -> SamePlaybookAction:
    profile = build_pool_profile(matches, taxonomy)
    if len(profile.hero_ids) < 2 or not profile.dominant_traits:
        return SamePlaybookAction(
            action_type="same_playbook",
            status="unavailable",
            dominant_traits=tuple(trait_label(item) for item in profile.dominant_traits),
            underrepresented_traits=tuple(trait_label(item) for item in profile.underrepresented_traits),
            deepen=(),
            stretch=(),
            confidence_score=profile.confidence_score,
            limitations=("At least two established, taxonomy-covered heroes are needed to build a playbook path.",),
            provenance_versions={
                **dict(_PROVENANCE_KEYS),
                **({"hero_knowledge": hero_knowledge.version} if hero_knowledge else {}),
            },
            evidence_summary=_action_evidence(
                status="unresolved",
                sample_size=len(matches),
                effective_sample_size_value=float(len(matches)),
                coverage=0.0 if not profile.hero_ids else len(profile.hero_ids) / max(len(matches), 1),
                confidence_score=profile.confidence_score,
                evidence_keys=(
                    "hero.knowledge" if hero_knowledge is not None else "hero.taxonomy",
                    "hero.pool_profile",
                    "hero.relationships",
                ),
                provenance_versions={
                    **dict(_PROVENANCE_KEYS),
                    **({"hero_knowledge": hero_knowledge.version} if hero_knowledge else {}),
                },
            ),
        )

    if hero_knowledge is not None:
        deepen = _semantic_pattern_recommendations(
            matches, hero_knowledge, intent="double_down", direction="deepen"
        )
        stretch = _semantic_pattern_recommendations(
            matches, hero_knowledge, intent="adjacent_move", direction="stretch"
        )
    else:
        deepen = _recommendations(matches, taxonomy, profile, direction="deepen")
        stretch = _recommendations(matches, taxonomy, profile, direction="stretch")
    status: ActionStatus = "available" if deepen and stretch else "limited" if deepen or stretch else "unavailable"
    limitations: list[str] = []
    if len(deepen) < 3:
        limitations.append("Fewer than three high-confidence deepen candidates cleared the functional-fit gates.")
    if len(stretch) < 3:
        limitations.append("Fewer than three high-confidence stretch candidates cleared the anchor and learning-distance gates.")
    if status == "unavailable":
        limitations.append("No reviewed hero relationship was strong enough to recommend without filler.")
    return SamePlaybookAction(
        action_type="same_playbook",
        status=status,
        dominant_traits=tuple(trait_label(item) for item in profile.dominant_traits),
        underrepresented_traits=tuple(trait_label(item) for item in profile.underrepresented_traits),
        deepen=deepen,
        stretch=stretch,
        confidence_score=profile.confidence_score,
        limitations=tuple(limitations),
        provenance_versions={
            **dict(_PROVENANCE_KEYS),
            **({"hero_knowledge": hero_knowledge.version} if hero_knowledge else {}),
        },
        evidence_summary=_action_evidence(
            status="resolved" if status == "available" else "fallback" if status == "limited" else "unresolved",
            sample_size=len(matches),
            effective_sample_size_value=float(len(matches)),
            coverage=len(profile.hero_ids) / max(len(matches), 1),
            confidence_score=profile.confidence_score,
            evidence_keys=(
                "hero.knowledge" if hero_knowledge is not None else "hero.taxonomy",
                "hero.pool_profile",
                "hero.relationships",
            ),
            provenance_versions={
                **dict(_PROVENANCE_KEYS),
                **({"hero_knowledge": hero_knowledge.version} if hero_knowledge else {}),
            },
        ),
    )


def build_comfort_edge_action(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    *,
    hero_knowledge: HeroKnowledgeProvider | None = None,
) -> ComfortEdgeAction:
    rows = _latest_usable_rows(matches)
    reliability = _rank_hero_reliability(rows, taxonomy)
    if len(reliability) < PORTFOLIO_CONFIG.p02_min_action_heroes:
        return ComfortEdgeAction(
            action_type="comfort_edge",
            status="unavailable",
            ranked_heroes=tuple(reliability),
            reference_core_hero_ids=tuple(item.hero_id for item in reliability[:2]),
            development=(),
            confidence_score=min((item.confidence_score for item in reliability), default=0.0),
            limitations=(
                f"Comfort Edge needs {PORTFOLIO_CONFIG.p02_min_action_heroes} sufficiently rankable heroes; "
                f"only {len(reliability)} cleared the per-hero sample gate.",
            ),
            provenance_versions={
                **dict(_PROVENANCE_KEYS),
                **({"hero_knowledge": hero_knowledge.version} if hero_knowledge else {}),
            },
            evidence_summary=_action_evidence(
                status="unresolved",
                sample_size=len(rows),
                effective_sample_size_value=float(len(rows)),
                coverage=len(reliability) / max(PORTFOLIO_CONFIG.p02_min_action_heroes, 1),
                confidence_score=min((item.confidence_score for item in reliability), default=0.0),
                evidence_keys=(
                    "hero.knowledge" if hero_knowledge is not None else "hero.taxonomy",
                    "hero.reliability",
                    "hero.pool_profile",
                ),
                provenance_versions={
                    **dict(_PROVENANCE_KEYS),
                    **({"hero_knowledge": hero_knowledge.version} if hero_knowledge else {}),
                },
            ),
        )

    top_five = tuple(reliability[:5])
    profile = build_pool_profile(rows, taxonomy, hero_ids=[item.hero_id for item in top_five])
    reference_core = top_five[: PORTFOLIO_CONFIG.p02_reference_core_size]
    development = tuple(
        _development_reason(item, reference_core, profile, taxonomy, hero_knowledge=hero_knowledge)
        for item in top_five[PORTFOLIO_CONFIG.p02_reference_core_size :]
    )
    examples_complete = all(
        reason.teammate_examples and reason.enemy_examples
        for reason in development
    )
    status: ActionStatus = "available" if examples_complete else "limited"
    limitations = [
        "Reliability is player-relative and confidence-adjusted; it is not a current-patch hero tier list.",
    ]
    if not examples_complete:
        limitations.append(
            "Concrete teammate and enemy examples remain limited until reviewed aggregate artifacts clear their confidence gate."
        )
    else:
        limitations.append(
            "Concrete teammate or enemy examples appear only when the versioned aggregate evidence clears its confidence gate."
        )
    return ComfortEdgeAction(
        action_type="comfort_edge",
        status=status,
        ranked_heroes=top_five,
        reference_core_hero_ids=tuple(item.hero_id for item in reference_core),
        development=development,
        confidence_score=min(item.confidence_score for item in top_five),
        limitations=tuple(limitations),
        provenance_versions={
            **dict(_PROVENANCE_KEYS),
            **({"hero_knowledge": hero_knowledge.version} if hero_knowledge else {}),
        },
        evidence_summary=_action_evidence(
            status="resolved" if status == "available" else "fallback",
            sample_size=len(rows),
            effective_sample_size_value=float(len(rows)),
            coverage=1.0,
            confidence_score=min(item.confidence_score for item in top_five),
            evidence_keys=(
                "hero.knowledge" if hero_knowledge is not None else "hero.taxonomy",
                "hero.reliability",
                "hero.pool_profile",
            ),
            provenance_versions={
                **dict(_PROVENANCE_KEYS),
                **({"hero_knowledge": hero_knowledge.version} if hero_knowledge else {}),
            },
        ),
    )


def _semantic_pattern_recommendations(
    matches: Sequence[NormalizedSummaryMatch],
    provider: HeroKnowledgeProvider,
    *,
    intent: Literal["double_down", "adjacent_move"],
    direction: Literal["deepen", "stretch"],
) -> tuple[PatternHeroRecommendation, ...]:
    rationales = recommend_semantic_heroes(matches, provider, intent=intent, limit=3)
    result: list[PatternHeroRecommendation] = []
    for rationale in rationales:
        entry = provider.get(rationale.hero_id)
        if entry is None:
            continue
        confidence = {"high": 0.90, "medium": 0.65, "low": 0.25}[rationale.confidence]
        similarity = min(1.0, 0.55 + 0.15 * len(rationale.familiar_anchors))
        novelty = min(1.0, 0.25 + 0.20 * len(rationale.adds))
        familiar = ", ".join(job_display_label(item) for item in rationale.familiar_anchors[:3])
        changed = ", ".join(job_display_label(item) for item in rationale.adds[:3]) or "a different expression of the same jobs"
        result.append(
            PatternHeroRecommendation(
                hero_id=entry.hero_id,
                hero_name=entry.display_name,
                direction=direction,
                anchor_traits=rationale.familiar_anchors[:3],
                added_traits=rationale.adds[:3],
                role_fit=tuple(entry.roles),
                similarity_score=similarity,
                novelty_score=novelty,
                confidence_score=confidence,
                why_it_fits=(
                    f"{entry.display_name} keeps {familiar or 'a reviewed anchor'} "
                    f"and adds {changed}."
                ),
                what_stays_familiar=f"The {familiar or 'reviewed anchor'} part of the current game remains visible.",
                what_changes=f"The next demand is {', '.join(rationale.new_demands) or changed}.",
                provenance_versions=dict(rationale.provenance_versions),
                semantic_rationale=rationale,
            )
        )
    return tuple(result)


def _recommendations(
    matches: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
    profile: Any,
    *,
    direction: str,
) -> tuple[PatternHeroRecommendation, ...]:
    candidates: list[tuple[float, HeroTaxonomyEntry, tuple[str, ...], tuple[str, ...], float, float]] = []
    for entry in sorted(taxonomy.heroes.values(), key=lambda item: item.hero_id):
        if not entry.available or entry.hero_id in profile.usage_counts:
            continue
        anchors, added = candidate_traits(entry, profile)
        similarity = pool_similarity(entry, profile)
        role_fit = role_compatibility(entry, profile)
        distance = learning_distance(entry, profile)
        if direction == "deepen":
            if not anchors or similarity < 0.55 or distance > 0.62:
                continue
            score = 0.55 * similarity + 0.25 * role_fit + 0.20 * (1.0 - distance)
        else:
            if not anchors or not added or similarity < 0.42 or similarity > 0.94 or distance > 0.68:
                continue
            anchor_score = min(1.0, len(anchors) / max(len(profile.dominant_traits), 1))
            added_score = min(1.0, len(added) / max(len(profile.underrepresented_traits), 1))
            score = 0.35 * anchor_score + 0.30 * added_score + 0.20 * role_fit + 0.15 * (1.0 - distance)
        confidence = min(1.0, profile.confidence_score * (0.70 + 0.30 * role_fit) * (1.0 - 0.25 * distance))
        candidates.append((score, entry, anchors, added, similarity, confidence))

    candidates.sort(key=lambda item: (-item[0], -item[5], item[1].hero_id))
    selected: list[PatternHeroRecommendation] = []
    selected_traits: set[str] = set()
    for _score, entry, anchors, added, similarity, confidence in candidates:
        if len(selected) >= 3:
            break
        # Keep the small recommendation set meaningfully varied where the
        # taxonomy gives us a choice, rather than returning three clones.
        novelty = min(1.0, len(set(added) - selected_traits) / max(len(added), 1)) if added else 0.25
        if selected and direction == "deepen" and added and set(added).issubset(selected_traits) and novelty == 0:
            continue
        expression = expression_difference(entry, profile)
        anchor_labels = tuple(trait_label(item) for item in anchors[:2])
        added_labels = tuple(trait_label(item) for item in added[:2])
        changed = added_labels or expression or ("a different secondary expression of the same jobs",)
        familiar_text = ", ".join(anchor_labels) or "part of your current functional core"
        changed_text = ", ".join(changed)
        selected.append(
            PatternHeroRecommendation(
                hero_id=entry.hero_id,
                hero_name=entry.name,
                direction=direction,  # type: ignore[arg-type]
                anchor_traits=anchors[:3],
                added_traits=added[:3],
                role_fit=tuple(entry.roles),
                similarity_score=max(0.0, min(1.0, similarity)),
                novelty_score=max(0.0, min(1.0, novelty)),
                confidence_score=max(0.0, min(1.0, confidence)),
                why_it_fits=f"You already lean on {familiar_text}. {entry.name} keeps that anchor while offering {changed_text}.",
                what_stays_familiar=f"You still get the {familiar_text} part of your current game.",
                what_changes=f"This adds {changed_text} without asking you to leave the whole playbook behind.",
                provenance_versions=dict(_PROVENANCE_KEYS),
            )
        )
        selected_traits.update(added)
    return tuple(selected)


def _latest_usable_rows(matches: Sequence[NormalizedSummaryMatch]) -> tuple[NormalizedSummaryMatch, ...]:
    ordered = sorted(
        (
            item
            for item in matches
            if item.hero_id is not None
            and item.won is not None
            and item.duration_seconds is not None
            and item.duration_seconds >= 600
            and item.kills is not None
            and item.deaths is not None
            and item.assists is not None
        ),
        key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id),
    )
    limit = PORTFOLIO_CONFIG.p02_history_limit
    return tuple(ordered if limit is None else ordered[-limit:])


def _rank_hero_reliability(
    rows: Sequence[NormalizedSummaryMatch],
    taxonomy: HeroTaxonomy,
) -> tuple[ComfortEdgeHeroReliability, ...]:
    by_hero: dict[int, list[NormalizedSummaryMatch]] = {}
    for item in rows:
        if item.hero_id is not None and taxonomy.get(item.hero_id) is not None:
            by_hero.setdefault(int(item.hero_id), []).append(item)
    if not by_hero:
        return ()

    credible_roles = Counter(item.role_hint for item in rows if item.role_hint)
    role_order = {role for role, count in credible_roles.items() if count >= 3}
    player_baseline = _weighted_performance(rows, role_order)
    scores: list[ComfortEdgeHeroReliability] = []
    for hero_id, hero_rows in by_hero.items():
        if len(hero_rows) < PORTFOLIO_CONFIG.p02_min_rankable_matches:
            continue
        raw = _weighted_performance(hero_rows, role_order)
        shrink = len(hero_rows) / (len(hero_rows) + PORTFOLIO_CONFIG.p02_shrinkage_prior)
        score = player_baseline + (raw - player_baseline) * shrink
        coverage = len(hero_rows) / max(len(rows), 1)
        confidence = min(1.0, len(hero_rows) / 25.0) * min(1.0, len(hero_rows) / max(len(hero_rows), 1))
        # A small but rankable hero remains visibly uncertain; it can rank,
        # but it cannot silently become a high-confidence recommendation.
        confidence *= 0.85 + 0.15 * min(1.0, coverage * 8.0)
        entry = taxonomy.get(hero_id)
        if entry is None:
            continue
        scores.append(
            ComfortEdgeHeroReliability(
                hero_id=hero_id,
                hero_name=entry.name,
                reliability_rank=0,
                reliability_score=max(0.0, min(1.0, score)),
                confidence_score=max(0.0, min(1.0, confidence)),
                matches=len(hero_rows),
            )
        )
    ordered = sorted(scores, key=lambda item: (-item.reliability_score, -item.confidence_score, item.hero_id))[:5]
    return tuple(replace(item, reliability_rank=index) for index, item in enumerate(ordered, start=1))


def _weighted_performance(
    rows: Sequence[NormalizedSummaryMatch],
    credible_roles: set[str],
) -> float:
    if not rows:
        return 0.5
    ordered = sorted(rows, key=lambda item: (item.started_at is None, item.started_at or 0, item.match_id))
    total_weight = 0.0
    weighted_score = 0.0
    for index, item in enumerate(ordered):
        recency = PORTFOLIO_CONFIG.p02_recency_floor + (1.0 - PORTFOLIO_CONFIG.p02_recency_floor) * (index / max(len(ordered) - 1, 1))
        duration_minutes = max(float(item.duration_seconds or 0) / 60.0, 1.0)
        contribution = min(1.0, ((item.kills or 0) + (item.assists or 0)) / max(duration_minutes * 1.2, 1.0))
        survival = 1.0 - min(1.0, (item.deaths or 0) / max(duration_minutes * 0.75, 1.0))
        outcome = 1.0 if item.won else 0.0
        role = 1.0 if not credible_roles or item.role_hint in credible_roles else 0.5
        row_score = 0.42 * outcome + 0.28 * contribution + 0.20 * survival + 0.10 * role
        weight = recency
        weighted_score += weight * row_score
        total_weight += weight
    return weighted_score / max(total_weight, 1e-9)


def _development_reason(
    item: ComfortEdgeHeroReliability,
    reference_core: Sequence[ComfortEdgeHeroReliability],
    profile: Any,
    taxonomy: HeroTaxonomy,
    *,
    hero_knowledge: HeroKnowledgeProvider | None = None,
) -> ComfortEdgeDevelopmentReason:
    entry = taxonomy.get(item.hero_id)
    core_ids = tuple(hero.hero_id for hero in reference_core)
    core_names = tuple(hero.hero_name for hero in reference_core)
    changes = expression_difference(entry, profile) if entry is not None else ()
    if not changes:
        changes = ("a different expression of the jobs your stronger heroes already cover",)
    situations = situations_for_traits(tuple(
        trait for trait in profile.underrepresented_traits if entry is not None and entry.traits.get(trait, 0.0) >= 0.60
    ))
    if not situations:
        situations = ("a draft where the stronger core needs a different way to solve the same broad problem",)
    matchup_records = representative_matchups(item.hero_id)
    synergy_records = representative_synergies(item.hero_id)
    enemy_ids = tuple(record.related_hero_id for record in matchup_records)
    teammate_ids = tuple(record.related_hero_id for record in synergy_records)
    enemy_names = tuple(_hero_name(taxonomy, hero_id) for hero_id in enemy_ids)
    teammate_names = tuple(_hero_name(taxonomy, hero_id) for hero_id in teammate_ids)
    what_changes = ", ".join(changes[:2])
    useful = situations[0]
    why = (
        f"Compared with your stronger {', '.join(core_names)}, {item.hero_name} changes {what_changes}. "
        f"That can matter when {useful}."
    )
    limitations: list[str] = []
    if not enemy_ids:
        limitations.append("No high-confidence aggregate matchup examples are available in the checked-in artifact.")
    if not teammate_ids:
        limitations.append("No high-confidence aggregate teammate-synergy examples are available in the checked-in artifact.")
    semantic_rationale = _comfort_edge_semantic_rationale(
        item.hero_id,
        core_ids,
        hero_knowledge,
    )
    return ComfortEdgeDevelopmentReason(
        hero_id=item.hero_id,
        hero_name=item.hero_name,
        reliability_rank=item.reliability_rank,
        reliability_score=item.reliability_score,
        confidence_score=item.confidence_score,
        reference_core_hero_ids=core_ids,
        reference_core_hero_names=core_names,
        what_changes=tuple(changes),
        useful_situations=situations,
        teammate_examples=teammate_ids,
        teammate_example_names=teammate_names,
        enemy_examples=enemy_ids,
        enemy_example_names=enemy_names,
        tradeoffs=("It may ask for a different learning rhythm than the stronger reference core.",),
        why_learn=why,
        limitations=tuple(limitations),
        provenance_versions={
            **dict(_PROVENANCE_KEYS),
            **(
                {"hero_knowledge": hero_knowledge.version}
                if hero_knowledge is not None
                else {}
            ),
        },
        semantic_rationale=semantic_rationale,
    )


def _comfort_edge_semantic_rationale(
    hero_id: int,
    core_ids: Sequence[int],
    provider: HeroKnowledgeProvider | None,
) -> HeroRecommendationRationale | None:
    """Describe an established development hero without inventing a new pick."""

    if provider is None:
        return None
    candidate = provider.get(hero_id)
    core_entries = tuple(
        entry for core_id in core_ids if (entry := provider.get(core_id)) is not None
    )
    if candidate is None or not core_entries:
        return None
    core_jobs = {
        job
        for entry in core_entries
        for job in (*entry.primary_functions, *entry.secondary_functions)
    }
    familiar = tuple(
        job
        for job in (*candidate.primary_functions, *candidate.secondary_functions)
        if job in core_jobs
    )
    adds = tuple(
        job
        for job in (*candidate.primary_functions, *candidate.secondary_functions)
        if job not in core_jobs
    )
    demand_order = {"low": 0, "medium": 1, "high": 2, "unknown": -1}
    core_demands: dict[str, str] = {}
    for family in HERO_DEMAND_FAMILIES:
        known = [entry.demands.get(family, "unknown") for entry in core_entries]
        core_demands[family] = max(known, key=lambda value: demand_order.get(value, -1))
    new_demands = tuple(
        family
        for family in HERO_DEMAND_FAMILIES
        if candidate.demands.get(family) in {"medium", "high"}
        and core_demands.get(family) not in {"medium", "high"}
    )
    unknown_demands = sum(
        candidate.demands.get(family) == "unknown" for family in HERO_DEMAND_FAMILIES
    )
    high_new = sum(candidate.demands.get(family) == "high" for family in new_demands)
    learning_distance: Literal["low", "moderate", "high"]
    if high_new >= 3 or candidate.demands.get("micro") == "high" and "micro" in new_demands:
        learning_distance = "high"
    elif len(new_demands) >= 2 or unknown_demands >= 4:
        learning_distance = "moderate"
    else:
        learning_distance = "low"
    empirical_support = (
        candidate.empirical_support
        if candidate.empirical_support in {"high", "medium", "low", "unknown"}
        else "unknown"
    )
    candidate_confidence = (
        candidate.confidence if candidate.confidence in {"high", "medium", "low"} else "low"
    )
    confidence = (
        "medium"
        if empirical_support == "unknown" and candidate_confidence == "high"
        else candidate_confidence
    )
    limitations: list[str] = []
    if empirical_support == "unknown":
        limitations.append("Empirical support is unknown; this is not a current-meta claim.")
    if unknown_demands:
        limitations.append("Some hero-demand families are unknown in the frozen snapshot.")
    return HeroRecommendationRationale(
        hero_id=candidate.hero_id,
        intent="change_angle",
        familiar_anchors=tuple(dict.fromkeys(familiar))[:4],
        adds=tuple(dict.fromkeys(adds))[:4],
        new_demands=new_demands[:4],
        learning_distance=learning_distance,
        role_fit="conditional",
        empirical_support=empirical_support,  # type: ignore[arg-type]
        confidence=confidence,  # type: ignore[arg-type]
        limitations=tuple(limitations),
        provenance_versions={
            **dict(candidate.provenance_versions),
            "hero_knowledge": provider.version,
        },
        evidence_refs=candidate.evidence_refs,
        eligible=True,
    )


def _hero_name(taxonomy: HeroTaxonomy, hero_id: int) -> str:
    entry = taxonomy.get(hero_id)
    return entry.name if entry is not None else str(hero_id)


__all__ = [
    "attach_pattern_actions",
    "build_comfort_edge_action",
    "build_controlled_presence_action",
    "build_bounceback_action",
    "build_partial_transfer_action",
    "build_presence_tax_action",
    "build_performance_slide_action",
    "build_proven_flexibility_action",
    "build_same_playbook_action",
    "build_versatile_core_action",
]
