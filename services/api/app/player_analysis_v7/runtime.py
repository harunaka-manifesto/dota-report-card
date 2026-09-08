"""Pure V7 analytical runtime over already-acquired canonical evidence.

The runtime applies frozen DISCOVERY fits.  It never fits context or population
parameters and never contacts a provider.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, cast

from app.player_analysis_v7.assembly import assemble_v7_capability
from app.player_analysis_v7.context_projection import (
    SHIPPING_FINDING_IDS,
    UnsupportedContextLevel,
    assert_population_compatible,
    load_context_projection,
)
from app.player_analysis_v7.population import PopulationParameters, load_population_parameters
from app.player_analysis_v7.report_contract import (
    ArchetypeModifier,
    ArchetypeSection,
    Direction,
    FightStyleAxis,
    Finding,
    FindingSectionKey,
    PointEstimateWithInterval,
    Recommendation,
    RecommendationObservation,
    TempoAxis,
)
from app.player_analysis_v7.research import archetype, inference, recommendation
from app.player_analysis_v7.research.features import FEATURE_VERSION, PlayerFrame, extract
from app.player_analysis_v7.research.inference import PlayerInference
from app.player_analysis_v7.research.pass2_features import (
    closer_vs_comeback as closing_feature,
)
from app.player_analysis_v7.research.pass2_features import vision_coverage as vision_feature
from app.player_analysis_v7.research.pass2_observations import (
    OBSERVATION_REGISTRY,
    OBSERVATION_VERSION,
    chronological,
)
from app.player_analysis_v7.research.pass2_tables import is_pass2_product_context
from app.player_analysis_v7.research.ranking import (
    FINDING_FLOOR,
    FINDING_SECTIONS,
    REPORT_SLOTS,
    PlayerDimension,
    RankedFinding,
    apply_score_gate,
    rank_player,
    select_stratified,
)
from app.player_analysis_v7.research.registry import FAMILY_BY_NAME
from app.player_analysis_v7.research.tables import is_product_context, order_by_time
from app.providers.base import V7CanonicalHistory

RUNTIME_VERSION = "v7-analytical-runtime-1.0.0"
PASS2_PLAYER_QUESTIONS = {
    "closer_vs_comeback": "Closing out leads versus coming back",
    "death_clustering": "Dying again soon after you died",
    "deaths_alone_share": "Dying away from your team",
    "fight_conversion": "Turning won fights into towers",
    "lane_vs_jungle_share": "Farming the jungle versus the lane",
    "spike_usage": "Using your item window",
    "vision_coverage": "How much of the map your wards keep lit",
}


class V7RuntimeError(RuntimeError):
    """Acquired evidence cannot support a valid frozen-lineage result."""


def _direction(value: float) -> str:
    return "positive" if value > 0 else "negative" if value < 0 else "zero"


def history_rows(history: V7CanonicalHistory) -> list[dict[str, Any]]:
    """Adapt the provider-neutral history contract to the frozen feature schema."""

    rows: list[dict[str, Any]] = []
    for match in history.matches:
        if match.started_at is None or match.duration_seconds is None:
            continue
        row = {
            "match_id": match.match_id,
            "hero_id": match.hero_id,
            "started_at": match.started_at,
            "ended_at": match.started_at + match.duration_seconds,
            "duration_seconds": match.duration_seconds,
            "is_radiant": None if match.side is None else match.side == "radiant",
            "is_victory": match.won,
            "game_version_id": match.game_version_id,
            "game_mode_native": match.game_mode_native,
            "lobby_type_native": match.lobby_native,
            "leaver_status_native": match.leaver_status_native,
        }
        if match.won is not None and match.side is not None:
            row["did_radiant_win"] = match.won == (match.side == "radiant")
        if is_product_context(row):
            rows.append(row)
    return order_by_time(rows)


def parsed_rows(deep_rows: Sequence[Mapping[str, Any]]) -> dict[int, dict[str, Any]]:
    """Adapt production Pass-2 canonical rows to the Pass-1 parsed join shape."""

    out: dict[int, dict[str, Any]] = {}
    for source in deep_rows:
        self_ = source.get("self")
        if not isinstance(self_, Mapping) or source.get("match_id") is None:
            continue
        raw_events = self_.get("events")
        events: Mapping[str, Any] = raw_events if isinstance(raw_events, Mapping) else {}
        row = dict(source)
        row.update(
            hero_id=self_.get("hero_id"),
            is_radiant=self_.get("is_radiant"),
            is_victory=self_.get("is_victory"),
            position_native=self_.get("position_native"),
            role_native=self_.get("role_native"),
            lane_native=self_.get("lane_native"),
            stats={
                "kill_events": events.get("kill_events"),
                "assist_events": events.get("assist_events"),
                "item_purchases": events.get("item_purchases"),
            },
        )
        out[int(source["match_id"])] = row
    return out


def _estimate(
    finding_id: str,
    opportunities: Sequence[Any],
    *,
    treated: str | None,
    control: str | None,
    recommendation_projection: bool = False,
) -> PlayerInference | None:
    artifact = load_context_projection()
    projection = (
        artifact.recommendation(finding_id)
        if recommendation_projection
        else artifact.finding(finding_id)
    )
    try:
        residuals = [
            projection.residual(value=o.value, context=dict(o.ctx), arm=o.arm)
            for o in opportunities
        ]
    except UnsupportedContextLevel:
        # An unseen player level refuses this dimension.  Do not map it to a
        # zero effect or hide artifact validation failures under this branch.
        return None
    armed = treated is not None and control is not None
    arms = [1 if o.arm == treated else 0 if o.arm == control else -1 for o in opportunities]
    return inference.player_inference(
        "runtime_player",
        residuals,
        arms if armed else None,
        1 if armed else None,
        0 if armed else None,
    )


def _finding_rows(
    frame: PlayerFrame, deep_rows: Sequence[dict[str, Any]], population: PopulationParameters
) -> tuple[list[Finding], dict[str, PlayerInference]]:
    estimates: dict[str, PlayerInference] = {}
    dimensions: list[PlayerDimension] = []
    for key in sorted(SHIPPING_FINDING_IDS):
        pass2_source = OBSERVATION_REGISTRY.get(key)
        family = FAMILY_BY_NAME.get(key)
        source = pass2_source or family
        if source is None:
            raise V7RuntimeError(f"{key}: no observation contract")
        opportunities = pass2_source.fn(deep_rows) if pass2_source else extract(key, frame)
        result = _estimate(
            key,
            opportunities,
            treated=source.treated,
            control=source.control,
        )
        if result is None:
            continue
        fitted = population.finding(key)
        if not fitted.ships:
            raise V7RuntimeError(f"{key}: runtime requested a withheld population fit")
        estimates[key] = result
        dimensions.append(
            PlayerDimension(
                key=key,
                section=fitted.section,
                delta_hat=result.delta,
                se=result.standard_error,
                sample_size=result.n,
                mu=fitted.mu,
                tau=fitted.tau,
                dependence_inflation=fitted.dependence_inflation,
            )
        )
    if len(dimensions) < FINDING_FLOOR:
        return [], estimates
    selected = apply_score_gate(
        select_stratified(rank_player(dimensions), FINDING_SECTIONS, REPORT_SLOTS)
    )
    return [_public_finding(row) for row in selected], estimates


def _public_finding(row: RankedFinding) -> Finding:
    source = OBSERVATION_REGISTRY.get(row.key) or FAMILY_BY_NAME[row.key]
    return Finding(
        dimension_key=row.key,
        section=cast(FindingSectionKey, row.section),
        direction=cast(Direction, row.direction),
        own_contrast_direction=(
            cast(Direction, _direction(row.shrunk_estimate.point)) if source.arm_family else None
        ),
        z=row.z,
        reliability=row.reliability,
        score=row.score,
        estimate=PointEstimateWithInterval(
            point=row.shrunk_estimate.point,
            interval_low=row.shrunk_estimate.interval.lower,
            interval_high=row.shrunk_estimate.interval.upper,
        ),
        sample_size=row.sample_size,
        player_facing_question=(
            FAMILY_BY_NAME[row.key].player_question
            if row.key in FAMILY_BY_NAME
            else PASS2_PLAYER_QUESTIONS[row.key]
        ),
    )


def _arm_means(opportunities: Sequence[Any], residuals: Sequence[float]) -> tuple[float, float]:
    """Block-paired win/loss values whose difference is the fitted gap."""

    wins: list[float] = []
    losses: list[float] = []
    for start, end in inference.block_bounds(len(residuals)):
        block_wins = [residuals[i] for i in range(start, end) if opportunities[i].arm == recommendation.ARM_WIN]
        block_losses = [residuals[i] for i in range(start, end) if opportunities[i].arm == recommendation.ARM_LOSS]
        if block_wins and block_losses:
            wins.append(sum(block_wins) / len(block_wins))
            losses.append(sum(block_losses) / len(block_losses))
    if not wins:
        raise V7RuntimeError("recommendation contrast has no valid paired blocks")
    return sum(wins) / len(wins), sum(losses) / len(losses)


def _recommendation(
    deep_rows: Sequence[dict[str, Any]], population: PopulationParameters
) -> Recommendation | None:
    artifact = load_context_projection()
    scored: list[recommendation.ScoredRecommendation] = []
    observations: dict[str, tuple[float, float]] = {}
    for key, dimension in recommendation.eligible_dimensions().items():
        series = recommendation.opportunities(deep_rows, dimension)
        if not recommendation.has_denominator(series):
            continue
        projection = artifact.recommendation(key)
        try:
            residuals = [projection.residual(o.value, dict(o.ctx)) for o in series]
        except UnsupportedContextLevel:
            continue
        result = _estimate(
            key,
            series,
            treated=recommendation.ARM_LOSS,
            control=recommendation.ARM_WIN,
            recommendation_projection=True,
        )
        if result is None:
            continue
        if (
            result.n_control < recommendation.MIN_PER_ARM
            or result.n_treated < recommendation.MIN_PER_ARM
        ):
            continue
        fitted = population.recommendation(key)
        if not fitted.eligible or fitted.outcome_contaminated:
            raise V7RuntimeError(f"{key}: Recommendation artifact contradicts registry")
        standardized = recommendation.standardized_gap(result.delta, fitted.dimension_scale)
        reliability = recommendation.gap_reliability(
            result.standard_error, fitted.dimension_scale, fitted.dependence_inflation
        )
        scored.append(
            recommendation.ScoredRecommendation(
                key=key,
                gap=result.delta,
                standard_error=result.standard_error,
                standardized_gap=standardized,
                reliability=reliability,
                actionability=dimension.actionability,
                priority=recommendation.priority(standardized, reliability, dimension.actionability),
                direction=_direction(result.delta),
                wins=result.n_control,
                losses=result.n_treated,
                recommendation=dimension.recommendation,
                verification=dimension.verification,
            )
        )
        observations[key] = _arm_means(series, residuals)
    selected, _ = recommendation.select(scored)
    if selected is None:
        return None
    win, loss = observations[selected.key]
    return Recommendation(
        dimension_key=selected.key,
        observation=RecommendationObservation(win_value=win, loss_value=loss, gap=loss - win),
        direction=cast(Direction, selected.direction),
        recommendation_text=selected.recommendation,
        verification=selected.verification,
        sample_wins=selected.wins,
        sample_losses=selected.losses,
        reliability=selected.reliability,
        actionability_weight=selected.actionability,
        priority_score=selected.priority,
    )


def _archetype(
    deep_rows: Sequence[dict[str, Any]], history: Sequence[dict[str, Any]], population: PopulationParameters
) -> tuple[ArchetypeSection | None, str | None]:
    measured = archetype.measure(deep_rows, history)
    if measured.stratum is None:
        return None, None
    cuts = archetype.PopulationCuts(**population.cuts_for(measured.stratum))
    vision = vision_feature(deep_rows)
    closing = closing_feature(deep_rows)
    assigned = archetype.assign(
        measured,
        cuts,
        vision_coverage=vision.primary.value if vision else None,
        closing_rate=closing.primary.value if closing else None,
    )
    if assigned is None:
        return None, measured.stratum
    return (
        ArchetypeSection(
            tempo=cast(TempoAxis, assigned.tempo),
            fight_style=cast(FightStyleAxis, assigned.fight_style),
            modifier=cast(ArchetypeModifier, assigned.modifier),
            label=assigned.special_label or assigned.label,
            is_special=assigned.is_special,
            special_label=assigned.special_label,
        ),
        measured.stratum,
    )


def analyze_v7(
    *,
    history: V7CanonicalHistory,
    deep_rows: Sequence[Mapping[str, Any]],
    hero_metadata: Mapping[int, Mapping[str, object]],
    generated_at: str,
    rank_display: Any | None = None,
) -> Any:
    """Produce one persisted-capability-ready report from acquired evidence."""

    population = load_population_parameters()
    projection = load_context_projection()
    assert_population_compatible(
        projection,
        {
            "schema_version": population.schema_version,
            "analytical_lineage_id": population.analytical_lineage_id,
            "context_projection_sha256": population.context_projection_sha256,
            "population_compatibility_id": population.population_compatibility_id,
        },
    )
    history_evidence = history_rows(history)
    history_match_ids = {row["match_id"] for row in history_evidence}
    deep_evidence = chronological(
        [
            dict(row)
            for row in deep_rows
            if row.get("match_id") in history_match_ids and is_pass2_product_context(dict(row))
        ]
    )
    deep_match_ids = [row["match_id"] for row in deep_evidence]
    if len(deep_match_ids) != len(set(deep_match_ids)):
        raise V7RuntimeError("deep evidence contains duplicate match ids")
    frame = PlayerFrame(
        pseudonym="runtime_player",
        split="RUNTIME",
        completeness="complete",
        rows=history_evidence,
        parsed=parsed_rows(deep_evidence),
    )
    findings, _ = _finding_rows(frame, deep_evidence, population)
    private_recommendation = _recommendation(deep_evidence, population)
    archetype_section, dominant_mode = _archetype(deep_evidence, history_evidence, population)
    refused: dict[str, str] = {"rank_display": "not_collected"} if rank_display is None else {}
    if not findings:
        refused["findings"] = "fewer_than_floor_dimensions"
    if private_recommendation is None:
        refused["recommendation"] = "insufficient_wins_or_losses_per_arm"
    if dominant_mode is None:
        refused["dominant_mode"] = "no_dominant_mode_stratum"
    if archetype_section is None:
        refused["archetype"] = (
            "no_dominant_mode_stratum" if dominant_mode is None else "insufficient_event_support"
        )
    return assemble_v7_capability(
        history=history,
        hero_metadata=hero_metadata,
        generated_at=generated_at,
        findings=findings,
        recommendation=private_recommendation,
        archetype=archetype_section,
        dominant_mode=dominant_mode,
        rank_display=rank_display,
        refused=refused,
        feature_version=f"{FEATURE_VERSION}+{OBSERVATION_VERSION}",
        inference_version=RUNTIME_VERSION,
    )


__all__ = ["RUNTIME_VERSION", "V7RuntimeError", "analyze_v7", "history_rows", "parsed_rows"]
