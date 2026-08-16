from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from math import log
from statistics import median

from app.cohorts.selector import CohortSelection
from app.cohorts.statistics import normal_interval, wilson_interval
from app.core.config import FREE_HISTORY_LIMIT
from app.features.models import MatchFeature
from app.insights.gates import GateResult, apply_publication_gates
from app.insights.models import EvidenceObject, MetricObservation
from app.insights.ranking import rank_evidence
from app.insights.registry import INSIGHT_DEFINITIONS, InsightDefinition


@dataclass(frozen=True, slots=True)
class InsightContext:
    account_id: int
    features: tuple[MatchFeature, ...]
    cohort: CohortSelection | None
    profile: dict[str, object]
    data_cutoff: int | None
    model_version: str
    template_version: str
    role_confidence_threshold: float = 0.60
    replay_coverage_threshold: float = 0.60
    summary_coverage_threshold: float = 0.60
    history_limit: int = FREE_HISTORY_LIMIT

    @property
    def role_confidence(self) -> float:
        if not self.features:
            return 0.0
        return sum(feature.role_probability for feature in self.features) / len(self.features)

    @property
    def summary_coverage(self) -> float:
        return _mean(feature.coverage.summary_coverage for feature in self.features)

    @property
    def replay_coverage(self) -> float:
        return _mean(feature.parsed_coverage for feature in self.features)


def evaluate_insights(context: InsightContext) -> list[EvidenceObject]:
    evaluated: list[EvidenceObject] = []
    for definition in INSIGHT_DEFINITIONS:
        observation = _observation(definition, context)
        coverage = (
            context.replay_coverage
            if definition.evidence_class == "replay"
            else context.summary_coverage
        )
        holdout = _holdout_survives(observation, context.features)
        gates = apply_publication_gates(
            definition,
            observation,
            role_confidence=context.role_confidence,
            role_confidence_threshold=context.role_confidence_threshold,
            parse_coverage=coverage,
            minimum_parse_coverage=(
                context.replay_coverage_threshold
                if definition.evidence_class == "replay"
                else context.summary_coverage_threshold
            ),
            holdout_survives=holdout,
        )
        evaluated.append(_to_evidence(definition, observation, context, gates))
    return rank_evidence(evaluated)


def _to_evidence(
    definition: InsightDefinition,
    observation: MetricObservation,
    context: InsightContext,
    gates: GateResult,
) -> EvidenceObject:
    effect: dict[str, object] = {
        "value": observation.effect,
        "direction": observation.direction,
        "unit": observation.unit,
    }
    interval = (
        {"lower": observation.interval[0], "upper": observation.interval[1], "null": 0.0}
        if observation.interval
        else None
    )
    cohort = None
    if observation.cohort_value is not None:
        cohort = {"value": observation.cohort_value, "unit": observation.unit}
    selected_cohort = context.cohort.as_dict() if context.cohort else None
    reason = None if gates.passed else "|".join(gates.reasons)
    return EvidenceObject(
        insight_id=definition.id,
        concept_id=definition.concept_id,
        categories=definition.categories,
        report_scope=f"player_recent_{context.history_limit}_eligible_matches",
        player={
            "account_id": context.account_id,
            "value": observation.player_value,
            "unit": observation.unit,
        },
        cohort=cohort,
        effect=effect,
        interval=interval,
        unit=observation.unit,
        denominators={
            "matches": observation.relevant_matches,
            "situations": observation.situation_count,
            "parsed_matches": observation.parsed_matches,
        },
        parse_coverage={
            "summary": context.summary_coverage,
            "replay": context.replay_coverage,
            "relevant": context.replay_coverage
            if definition.evidence_class == "replay"
            else context.summary_coverage,
        },
        role_certainty={
            "mean_probability": context.role_confidence,
            "threshold": context.role_confidence_threshold,
            "below_threshold": context.role_confidence < context.role_confidence_threshold,
        },
        selected_cohort=selected_cohort,
        evidence_statements=observation.evidence_facts,
        confidence=gates.confidence,
        material_confounders=observation.confounders,
        action={
            "behavior": observation.action_behavior,
            "target": observation.measurable_target,
            "practice_window": observation.practice_window,
        },
        versions={
            "feature_version": "features-1.0.0",
            "cohort_version": "cohorts-1.0.0",
            "model_version": context.model_version,
            "template_version": context.template_version,
        },
        source_match_ids=observation.source_match_ids,
        provenance={
            "raw_payload_refs": [
                f"/matches/{match_id}" for match_id in observation.source_match_ids
            ],
            "normalized_match_refs": [
                f"match:{match_id}" for match_id in observation.source_match_ids
            ],
            "derived_feature_refs": [
                f"feature:match:{match_id}" for match_id in observation.source_match_ids
            ],
        },
        publication_status="published" if gates.passed else "suppressed",
        publication_reason=reason,
        ivs=definition.base_ivs + _ivs_adjustment(observation, gates.confidence),
        definition_version=definition.version,
        statement_template_id=definition.statement_template_id,
        action_template_id=definition.action_template_id,
    )


def _observation(definition: InsightDefinition, context: InsightContext) -> MetricObservation:
    features = list(context.features)
    if definition.evidence_class == "replay":
        return _replay_observation(definition, features, context)
    calculators: dict[str, Callable[[list[MatchFeature], InsightContext], MetricObservation]] = {
        "adjusted_role_fit": _role_fit,
        "hero_role_fit_residual": _role_fit,
        "comfort_vs_stretch": _comfort_vs_stretch,
        "specialization_hero_pool_entropy": _hero_entropy,
        "collapse_tail_performance_floor": _collapse_tail,
        "economy_to_impact_efficiency": _economy_efficiency,
        "tower_first_objective_orientation": _tower_orientation,
        "item_timing_reliability": _item_timing,
        "duration_curve": _duration_curve,
        "current_form_divergence": _current_form,
        "recent_style_shift": _recent_style,
        "party_side_mode_splits": _splits,
    }
    return calculators[definition.id](features, context)


def _role_fit(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    wins = sum(feature.won for feature in features)
    value = wins / len(features) if features else None
    cohort_value = _cohort_metric(context, "win_rate")
    effect = value - cohort_value if value is not None and cohort_value is not None else None
    interval = normal_interval([1.0 if feature.won else 0.0 for feature in features])
    if interval and effect is not None:
        interval = (interval[0] - (cohort_value or 0), interval[1] - (cohort_value or 0))
    return _base(
        value,
        cohort_value,
        "win rate",
        effect,
        interval,
        wins,
        len(features),
        features,
        direction=_direction(effect),
        facts=(f"{wins} wins across {len(features)} eligible matches.",),
        confounders=("Hero mix and opponent composition are not causal controls.",),
        action_behavior="Keep the role when the same hero-role combination is available; review losses before changing roles.",
        target="Maintain or improve the recent win rate over the next 20 eligible matches.",
    )


def _comfort_vs_stretch(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    by_hero: dict[int | None, list[MatchFeature]] = {}
    for feature in features:
        by_hero.setdefault(feature.hero_id, []).append(feature)
    comfort = [feature for rows in by_hero.values() if len(rows) >= 2 for feature in rows]
    stretch = [feature for rows in by_hero.values() if len(rows) == 1 for feature in rows]
    comfort_rate = _rate(comfort)
    stretch_rate = _rate(stretch)
    effect = (
        comfort_rate - stretch_rate
        if comfort_rate is not None and stretch_rate is not None
        else None
    )
    return _base(
        comfort_rate,
        stretch_rate,
        "win rate",
        effect,
        normal_interval([1.0 if item.won else 0.0 for item in comfort]) if comfort else None,
        sum(item.won for item in comfort),
        len(comfort) + len(stretch),
        features,
        direction=_direction(effect),
        facts=(f"{len(by_hero)} distinct heroes; {len(comfort)} comfort-pick matches.",),
        confounders=("A single stretch pick can be a draft-specific exception.",),
        action_behavior="Use the comfort pool for ranked repetition until a stretch pick has enough practice matches.",
        target="Define a three-hero comfort pool and record at least 10 matches on each before expanding it.",
    )


def _hero_entropy(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    counts: dict[int | None, int] = {}
    for feature in features:
        counts[feature.hero_id] = counts.get(feature.hero_id, 0) + 1
    total = len(features)
    entropy = (
        -sum((count / total) * log(count / total, 2) for count in counts.values())
        if total
        else None
    )
    return _base(
        entropy,
        None,
        "entropy",
        None,
        None,
        total,
        total,
        features,
        direction=None,
        facts=(
            f"{len(counts)} distinct heroes produced {entropy:.2f} bits of hero-pool entropy."
            if entropy is not None
            else "No hero data was available.",
        ),
        confounders=("Entropy describes selection breadth, not hero quality.",),
        action_behavior="Keep a deliberate core pool and label any new pick as a stretch experiment.",
        target="Keep the next 20 matches within the chosen core pool unless the experiment is intentional.",
    )


def _collapse_tail(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    scores = sorted(feature.impact_score for feature in features)
    floor = scores[max(0, len(scores) // 4 - 1)] if scores else None
    return _base(
        floor,
        None,
        "impact score",
        None,
        normal_interval(scores[: max(1, len(scores) // 2)]) if scores else None,
        len(scores),
        len(scores),
        features,
        direction=None,
        facts=(
            f"The lower-tail impact floor is {floor:.2f}."
            if floor is not None
            else "No impact data was available.",
        ),
        confounders=("Impact is a transparent proxy and is not a causal win model.",),
        action_behavior="Review the lowest-impact losses and identify the first missed repeatable action.",
        target="Raise the bottom-quarter impact score by 10% over the next 20 matches.",
    )


def _economy_efficiency(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    values = [feature.derived.get("economy_impact_efficiency", 0.0) for feature in features]
    value = median(values) if values else None
    cohort_value = _cohort_metric(context, "median_impact_score")
    effect = value - cohort_value if value is not None and cohort_value is not None else None
    return _base(
        value,
        cohort_value,
        "efficiency",
        effect,
        normal_interval(values),
        len(values),
        len(values),
        features,
        direction=_direction(effect),
        facts=(
            f"Median impact per GPM proxy is {value:.4f}."
            if value is not None
            else "No economy data was available.",
        ),
        confounders=(
            "The efficiency proxy combines different stat scales and should be compared consistently.",
        ),
        action_behavior="Convert each completed item timing into a visible objective or fight before the next purchase.",
        target="Log the first objective or fight after each major item in the next 20 matches.",
    )


def _tower_orientation(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    values = [feature.tower_damage for feature in features]
    value = median(values) if values else None
    return _base(
        value,
        _cohort_metric(context, "median_tower_damage"),
        "tower damage",
        _difference(value, _cohort_metric(context, "median_tower_damage")),
        normal_interval(values),
        sum(values),
        len(features),
        features,
        direction=_direction(_difference(value, _cohort_metric(context, "median_tower_damage"))),
        facts=(
            f"Median tower damage is {value:.0f}."
            if value is not None
            else "No tower-damage data was available.",
        ),
        confounders=("Tower damage is affected by hero kit, game length, and team composition.",),
        action_behavior="After winning a fight, check the nearest objective before taking another neutral action.",
        target="Record one objective decision in at least 12 of the next 20 matches.",
    )


def _item_timing(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    matches_with_timings = [feature for feature in features if feature.item_timings]
    value = len(matches_with_timings) / len(features) if features else None
    return _base(
        value,
        None,
        "rate",
        None,
        wilson_interval(len(matches_with_timings), len(features)) if features else None,
        len(matches_with_timings),
        len(features),
        features,
        direction=None,
        facts=(
            f"{len(matches_with_timings)} of {len(features)} matches contain item timing records.",
        ),
        confounders=(
            "Item timing reliability measures recorded timing availability as well as behavior.",
        ),
        action_behavior="Name the next major item and the game-state condition it should unlock before buying components.",
        target="Write the intended timing and unlocked action before the first major item in 15 of the next 20 matches.",
    )


def _duration_curve(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    midpoint = median(feature.duration_minutes for feature in features) if features else 0
    long_matches = [feature for feature in features if feature.duration_minutes >= midpoint]
    short_matches = [feature for feature in features if feature.duration_minutes < midpoint]
    long_rate = _rate(long_matches)
    short_rate = _rate(short_matches)
    effect = _difference(long_rate, short_rate)
    return _base(
        long_rate,
        short_rate,
        "win rate",
        effect,
        normal_interval([1.0 if item.won else 0.0 for item in long_matches])
        if long_matches
        else None,
        sum(item.won for item in long_matches),
        len(long_matches) + len(short_matches),
        features,
        direction=_direction(effect),
        facts=(
            f"Long-match win rate is {long_rate:.0%} versus {short_rate:.0%} in shorter matches."
            if long_rate is not None and short_rate is not None
            else "Duration groups were unavailable.",
        ),
        confounders=("Duration is partly determined by both teams and game state.",),
        action_behavior="At the midpoint of a close game, choose one explicit win-condition action instead of drifting into late game.",
        target="State the win condition at minute 20 in 15 of the next 20 matches.",
    )


def _current_form(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    prior, recent = _split_temporal(features)
    recent_rate = _rate(recent)
    prior_rate = _rate(prior)
    effect = _difference(recent_rate, prior_rate)
    return _base(
        recent_rate,
        prior_rate,
        "win rate",
        effect,
        normal_interval([1.0 if item.won else 0.0 for item in recent]) if recent else None,
        sum(item.won for item in recent),
        len(features),
        features,
        direction=_direction(effect),
        facts=(
            f"Recent form is {recent_rate:.0%} versus {prior_rate:.0%} in the earlier window."
            if recent_rate is not None and prior_rate is not None
            else "Not enough temporal data for a form split.",
        ),
        confounders=("Short windows are noisy and may reflect opponent or hero-pool changes.",),
        action_behavior="Treat the recent trend as a review prompt, not as a permanent identity label.",
        target="Recheck the same split after the next 20 eligible matches.",
    )


def _recent_style(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    prior, recent = _split_temporal(features)
    recent_gpm = _mean(feature.gold_per_min for feature in recent)
    prior_gpm = _mean(feature.gold_per_min for feature in prior)
    effect = _difference(recent_gpm, prior_gpm)
    return _base(
        recent_gpm,
        prior_gpm,
        "GPM",
        effect,
        normal_interval([feature.gold_per_min for feature in recent]) if recent else None,
        recent_gpm,
        len(features),
        features,
        direction=_direction(effect),
        facts=(
            f"Recent median economy is {recent_gpm:.0f} GPM versus {prior_gpm:.0f} earlier."
            if recent and prior
            else "Not enough temporal data for a style split.",
        ),
        confounders=("The style shift is observational and may follow hero or role changes.",),
        action_behavior="Compare the changed economy pattern with the objective or fight it was supposed to create.",
        target="Annotate the reason for any GPM change in 10 of the next 20 matches.",
    )


def _splits(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    radiant = [feature for feature in features if feature.side == "radiant"]
    dire = [feature for feature in features if feature.side == "dire"]
    radiant_rate = _rate(radiant)
    dire_rate = _rate(dire)
    effect = _difference(radiant_rate, dire_rate)
    return _base(
        radiant_rate,
        dire_rate,
        "win rate",
        effect,
        normal_interval([1.0 if item.won else 0.0 for item in radiant]) if radiant else None,
        sum(item.won for item in radiant),
        len(features),
        features,
        direction=_direction(effect),
        facts=(
            f"Radiant win rate is {radiant_rate:.0%} versus {dire_rate:.0%} on Dire."
            if radiant_rate is not None and dire_rate is not None
            else "There are not enough side observations for a split.",
        ),
        confounders=("Side, party, and mode effects are observational and may be imbalanced.",),
        action_behavior="Use side-specific opening plans only when the split repeats after checking party and hero mix.",
        target="Review the next 20 matches with side and party context recorded.",
    )


def _replay_observation(
    definition: InsightDefinition,
    features: list[MatchFeature],
    context: InsightContext,
) -> MetricObservation:
    return REPLAY_CALCULATORS[definition.id](features, context)


def _advantage_conversion(
    features: list[MatchFeature], context: InsightContext
) -> MetricObservation:
    return _replay_ratio(
        features,
        opportunity_keys=("advantage_opportunities", "advantage_situations"),
        success_keys=("advantage_conversions", "advantage_successes"),
        label="advantage conversion",
        neutral_baseline=0.50,
        behavior="When ahead, convert the next advantage into an objective or safe map action before resetting.",
        target="Record a deliberate advantage conversion in at least 60% of qualifying situations over the next 20 matches.",
    )


def _deaths_while_ahead(
    features: list[MatchFeature], context: InsightContext
) -> MetricObservation:
    return _replay_ratio(
        features,
        opportunity_keys=("ahead_death_opportunities", "deaths_while_ahead_situations"),
        success_keys=("deaths_while_ahead", "ahead_deaths"),
        label="deaths while ahead",
        neutral_baseline=0.15,
        effect_sign=-1.0,
        behavior="When ahead or high-net-worth, identify the next safe reset before taking a contestable fight.",
        target="Keep deaths while ahead below 15% of qualifying situations over the next 20 matches.",
    )


def _early_death_tax(features: list[MatchFeature], context: InsightContext) -> MetricObservation:
    parsed = [
        feature
        for feature in features
        if feature.parsed_coverage > 0 and "death_events" in feature.derived
    ]
    if not parsed:
        return _replay_unavailable(
            features,
            "early death tax",
            "Protect the first ten minutes with a concrete escape or reset trigger.",
            "Keep early deaths below 15% in the next 20 matches.",
        )
    value = _mean(feature.derived.get("early_death", 0.0) for feature in parsed)
    effect = (0.15 - value)
    return _base(
        value,
        None,
        "rate",
        effect,
        wilson_interval(
            sum(1 for feature in parsed if feature.derived.get("early_death", 0.0) > 0),
            len(parsed),
        ),
        sum(1 for feature in parsed if feature.derived.get("early_death", 0.0) > 0),
        len(parsed),
        parsed,
        direction=_direction(effect),
        situations=len(parsed),
        parsed_matches=len(parsed),
        facts=(
            f"{sum(1 for feature in parsed if feature.derived.get('early_death', 0.0) > 0)} of {len(parsed)} parsed matches contain a verified early death.",
        ),
        confounders=("Death timing is only available when the replay event source records a victim timestamp.",),
        action_behavior="Protect the first ten minutes with a concrete escape or reset trigger.",
        target="Keep early deaths below 15% in the next 20 matches.",
    )


def _objective_follow_through(
    features: list[MatchFeature], context: InsightContext
) -> MetricObservation:
    return _replay_ratio(
        features,
        opportunity_keys=("objective_opportunities", "objective_situations"),
        success_keys=("objective_follow_through", "objective_conversions"),
        label="objective follow-through",
        neutral_baseline=0.50,
        behavior="After a won fight or timing window, take the nearest safe objective before farming again.",
        target="Complete the intended objective in at least 60% of qualifying windows over the next 20 matches.",
    )


def _power_spike_conversion(
    features: list[MatchFeature], context: InsightContext
) -> MetricObservation:
    return _replay_ratio(
        features,
        opportunity_keys=("power_spike_opportunities", "power_spike_situations"),
        success_keys=("power_spike_conversions", "power_spike_successes"),
        label="power-spike conversion",
        neutral_baseline=0.50,
        behavior="Use the first completed power spike to create a planned fight, tower, or objective window.",
        target="Create a visible conversion after at least 60% of qualifying power spikes over the next 20 matches.",
    )


def _farm_to_fight_pivot(
    features: list[MatchFeature], context: InsightContext
) -> MetricObservation:
    return _replay_ratio(
        features,
        opportunity_keys=("farm_to_fight_opportunities", "farm_to_fight_situations"),
        success_keys=("farm_to_fight_conversions", "farm_to_fight_successes"),
        label="farm-to-fight pivot",
        neutral_baseline=0.50,
        behavior="When the farm window closes, pivot toward the next team action instead of extending the route.",
        target="Make the planned farm-to-fight pivot in at least 60% of qualifying windows over the next 20 matches.",
    )


def _lane_loss_recovery(
    features: list[MatchFeature], context: InsightContext
) -> MetricObservation:
    return _replay_ratio(
        features,
        opportunity_keys=("lane_loss_opportunities", "lane_loss_situations"),
        success_keys=("lane_loss_recoveries", "lane_recovery_successes"),
        label="lane-loss recovery",
        neutral_baseline=0.50,
        behavior="After losing lane control, choose one recovery resource and protect its next timing.",
        target="Complete a defined recovery action in at least 60% of lane-loss situations over the next 20 matches.",
    )


def _comeback_trailing_side_safety(
    features: list[MatchFeature], context: InsightContext
) -> MetricObservation:
    return _replay_ratio(
        features,
        opportunity_keys=("comeback_opportunities", "trailing_side_situations"),
        success_keys=("comeback_safe_outcomes", "comeback_conversions"),
        label="comeback safety",
        neutral_baseline=0.50,
        behavior="When trailing, choose the lowest-variance comeback route before taking a blind contest.",
        target="Choose a defined safe comeback route in at least 60% of qualifying trailing situations over the next 20 matches.",
    )


def _teamfight_survival_conversion(
    features: list[MatchFeature], context: InsightContext
) -> MetricObservation:
    return _replay_ratio(
        features,
        opportunity_keys=("teamfight_survival_opportunities", "teamfight_situations"),
        success_keys=("teamfight_survival_conversions", "teamfight_conversion_successes"),
        label="teamfight survival conversion",
        neutral_baseline=0.50,
        behavior="After surviving a fight, name the nearest safe conversion before resetting.",
        target="Record a post-fight conversion in at least 60% of qualifying fights over the next 20 matches.",
    )


def _objective_vision_timing(
    features: list[MatchFeature], context: InsightContext
) -> MetricObservation:
    return _replay_ratio(
        features,
        opportunity_keys=("objective_vision_opportunities", "objective_situations"),
        success_keys=("vision_before_objective", "objective_vision_successes"),
        label="objective vision timing",
        neutral_baseline=0.50,
        behavior="Place vision before the next objective window and check whether it changes the approach.",
        target="Record vision before at least 60% of objective windows over the next 20 matches.",
    )


def _replay_ratio(
    features: list[MatchFeature],
    *,
    opportunity_keys: tuple[str, ...],
    success_keys: tuple[str, ...],
    label: str,
    neutral_baseline: float,
    behavior: str,
    target: str,
    effect_sign: float = 1.0,
) -> MetricObservation:
    rows: list[MatchFeature] = []
    opportunities = 0.0
    successes = 0.0
    for feature in features:
        if feature.parsed_coverage <= 0:
            continue
        opportunity = _first_derived(feature, opportunity_keys)
        success = _first_derived(feature, success_keys)
        if opportunity is None or success is None:
            continue
        rows.append(feature)
        opportunities += max(0.0, opportunity)
        successes += max(0.0, min(success, opportunity))
    if not rows or opportunities <= 0:
        return _replay_unavailable(features, label, behavior, target)
    value = successes / opportunities
    effect = effect_sign * (value - neutral_baseline)
    interval = wilson_interval(round(successes), round(opportunities))
    return _base(
        value,
        None,
        "rate",
        effect,
        interval,
        successes,
        round(opportunities),
        rows,
        direction=_direction(effect),
        situations=round(opportunities),
        parsed_matches=len(rows),
        facts=(
            f"{label.capitalize()} was {value:.0%} across {round(opportunities)} verified situations.",
            f"{len(rows)} parsed matches supplied the event records for this family.",
        ),
        confounders=("Replay parsing coverage and parser definitions limit this conclusion.",),
        action_behavior=behavior,
        target=target,
    )


def _replay_unavailable(
    features: list[MatchFeature], label: str, behavior: str, target: str
) -> MetricObservation:
    parsed = [feature for feature in features if feature.parsed_coverage > 0]
    return _base(
        None,
        None,
        "rate",
        None,
        None,
        None,
        0,
        parsed,
        direction=None,
        situations=0,
        parsed_matches=len(parsed),
        facts=(f"No verified {label} event metric was available.",),
        confounders=("Replay parsing coverage and parser definitions limit this conclusion.",),
        action_behavior=behavior,
        target=target,
    )


def _first_derived(feature: MatchFeature, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        if key in feature.derived:
            return float(feature.derived[key])
    return None


REPLAY_CALCULATORS: dict[
    str, Callable[[list[MatchFeature], InsightContext], MetricObservation]
] = {
    "advantage_conversion": _advantage_conversion,
    "deaths_while_ahead_high_net_worth": _deaths_while_ahead,
    "early_death_tax": _early_death_tax,
    "objective_follow_through": _objective_follow_through,
    "power_spike_conversion": _power_spike_conversion,
    "farm_to_fight_pivot": _farm_to_fight_pivot,
    "lane_loss_recovery": _lane_loss_recovery,
    "comeback_trailing_side_safety": _comeback_trailing_side_safety,
    "teamfight_survival_conversion": _teamfight_survival_conversion,
    "objective_vision_timing": _objective_vision_timing,
}


def _base(
    player_value: float | None,
    cohort_value: float | None,
    unit: str,
    effect: float | None,
    interval: tuple[float, float] | None,
    numerator: float | None,
    denominator: int,
    features: list[MatchFeature],
    *,
    direction: str | None,
    facts: tuple[str, ...],
    confounders: tuple[str, ...],
    action_behavior: str,
    target: str,
    situations: int | None = None,
    parsed_matches: int | None = None,
) -> MetricObservation:
    return MetricObservation(
        player_value=player_value,
        cohort_value=cohort_value,
        unit=unit,
        effect=effect,
        interval=interval,
        numerator=numerator,
        denominator=denominator,
        situation_count=situations if situations is not None else len(features),
        relevant_matches=len(features),
        parsed_matches=parsed_matches
        if parsed_matches is not None
        else sum(feature.parsed_coverage > 0 for feature in features),
        source_match_ids=tuple(feature.match_id for feature in features),
        direction=direction,
        evidence_facts=facts,
        confounders=confounders,
        action_behavior=action_behavior,
        measurable_target=target,
    )


def _cohort_metric(context: InsightContext, key: str) -> float | None:
    if context.cohort and context.cohort.valid:
        return context.cohort.metrics.get(key)
    return None


def _rate(features: list[MatchFeature]) -> float | None:
    return sum(feature.won for feature in features) / len(features) if features else None


def _mean(values: Iterable[float]) -> float:
    numbers = [float(value) for value in values]
    return sum(numbers) / len(numbers) if numbers else 0.0


def _difference(left: float | None, right: float | None) -> float | None:
    return left - right if left is not None and right is not None else None


def _direction(effect: float | None) -> str | None:
    if effect is None or abs(effect) < 1e-9:
        return None
    return "positive" if effect > 0 else "negative"


def _split_temporal(features: list[MatchFeature]) -> tuple[list[MatchFeature], list[MatchFeature]]:
    ordered = sorted(features, key=lambda feature: feature.start_time or feature.match_id)
    pivot = max(1, int(len(ordered) * 0.70))
    return ordered[:pivot], ordered[pivot:]


def _holdout_survives(observation: MetricObservation, features: tuple[MatchFeature, ...]) -> bool:
    if not observation.direction or len(features) < 6:
        return True
    _, recent = _split_temporal(list(features))
    if not recent:
        return True
    if observation.unit in {"win rate", "rate"}:
        recent_value = _rate(recent)
        if observation.cohort_value is None or recent_value is None:
            return True
        return (recent_value - observation.cohort_value) * (observation.effect or 0) >= 0
    return True


def _ivs_adjustment(observation: MetricObservation, confidence: str) -> float:
    adjustment = 0.05 if confidence == "high" else 0.02 if confidence == "moderate" else 0.0
    if observation.effect is not None and abs(observation.effect) >= 0.25:
        adjustment += 0.05
    return adjustment
