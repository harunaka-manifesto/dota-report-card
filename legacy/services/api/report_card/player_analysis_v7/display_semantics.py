"""Canonical measurement semantics for V7 frontend copy and formatting."""

from __future__ import annotations

from typing import Literal

from report_card.player_analysis_v7.population import load_population_parameters
from report_card.player_analysis_v7.report_contract import PublicV7Model
from report_card.player_analysis_v7.research.pass2_observations import OBSERVATION_REGISTRY
from report_card.player_analysis_v7.research.recommendation import RECOMMENDATION_REGISTRY
from report_card.player_analysis_v7.research.registry import FAMILY_BY_NAME

DISPLAY_SEMANTICS_VERSION = "v7-display-semantics-1.0.0"


class FindingDisplaySemantics(PublicV7Model):
    dimension_key: str
    exact_definition: str
    display_unit: Literal[
        "proportion",
        "seconds",
        "adjusted_log_seconds",
        "normalized_match_progress",
        "adjusted_log_duration",
    ]
    numeric_conversion: Literal["direct", "omit_without_baseline"]
    direction_source: Literal["population_position", "own_contrast_direction"]


class RecommendationDisplaySemantics(PublicV7Model):
    dimension_key: str
    canonical_instruction: str
    canonical_verification: str
    measurement_note: str | None = None
    upstream_of_result: Literal[True] = True
    outcome_contaminated: Literal[False] = False


class DisplaySemantics(PublicV7Model):
    version: Literal["v7-display-semantics-1.0.0"] = "v7-display-semantics-1.0.0"
    findings: dict[str, FindingDisplaySemantics]
    recommendations: dict[str, RecommendationDisplaySemantics]


_UNITS: dict[str, tuple[str, str]] = {
    "closer_vs_comeback": ("proportion", "direct"),
    "death_clustering": ("proportion", "direct"),
    "deaths_alone_share": ("proportion", "direct"),
    "duration_tempo": ("adjusted_log_duration", "omit_without_baseline"),
    "fight_conversion": ("proportion", "direct"),
    "fight_timing_centroid": ("normalized_match_progress", "direct"),
    "hero_novelty": ("proportion", "direct"),
    "lane_vs_jungle_share": ("proportion", "direct"),
    "lead_retention": ("proportion", "direct"),
    "position_flexibility": ("proportion", "direct"),
    "post_loss_hero_switch": ("proportion", "direct"),
    "post_loss_requeue_latency": ("adjusted_log_seconds", "omit_without_baseline"),
    "post_loss_session_continuation": ("proportion", "direct"),
    "purchase_tempo": ("normalized_match_progress", "direct"),
    "spike_usage": ("seconds", "direct"),
    "vision_coverage": ("proportion", "direct"),
}


def build_display_semantics() -> DisplaySemantics:
    parameters = load_population_parameters()
    findings: dict[str, FindingDisplaySemantics] = {}
    for key in parameters.shipping_dimensions:
        source = OBSERVATION_REGISTRY.get(key) or FAMILY_BY_NAME.get(key)
        if source is None:
            raise RuntimeError(f"shipping dimension {key!r} has no canonical definition")
        unit, conversion = _UNITS[key]
        arm_family = source.arm_family
        findings[key] = FindingDisplaySemantics(
            dimension_key=key,
            exact_definition=source.estimand,
            display_unit=unit,  # type: ignore[arg-type]
            numeric_conversion=conversion,  # type: ignore[arg-type]
            direction_source=("own_contrast_direction" if arm_family else "population_position"),
        )
    recommendations = {
        key: RecommendationDisplaySemantics(
            dimension_key=key,
            canonical_instruction=row.recommendation,
            canonical_verification=row.verification,
            measurement_note=(
                "Measures the time of the first real-item purchase; it is not the "
                "first purchase, damage-item timing, a full build, or a power spike."
                if key == "first_real_item_time"
                else None
            ),
        )
        for key, row in RECOMMENDATION_REGISTRY.items()
        if row.upstream and not row.outcome_contaminated
    }
    return DisplaySemantics(findings=findings, recommendations=recommendations)


__all__ = [
    "DISPLAY_SEMANTICS_VERSION",
    "DisplaySemantics",
    "FindingDisplaySemantics",
    "RecommendationDisplaySemantics",
    "build_display_semantics",
]
