from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EffectGate:
    minimum_absolute_effect: float = 0.0
    unit: str = "native"
    confidence_interval_excludes_null: bool = False


@dataclass(frozen=True, slots=True)
class EligibilityRule:
    require_role_confidence: bool = False
    required_coverage_family: str | None = None


@dataclass(frozen=True, slots=True)
class InsightDefinition:
    id: str
    concept_id: str
    categories: tuple[str, ...]
    evidence_class: str
    required_features: tuple[str, ...]
    eligibility: EligibilityRule
    cohort_dimensions: tuple[str, ...]
    minimum_matches: int
    minimum_situations: int
    minimum_parse_coverage: float | None
    effect_gate: EffectGate
    confidence_method: str
    statement_template_id: str
    action_template_id: str
    base_ivs: float
    version: str = "1.0.0"
    requires_valid_cohort: bool = False


def _summary(
    insight_id: str,
    categories: tuple[str, ...],
    *,
    role: bool = False,
    effect: float = 0.0,
    template: str | None = None,
    action: str | None = None,
    ivs: float = 0.60,
    cohort_relative: bool = False,
) -> InsightDefinition:
    return InsightDefinition(
        id=insight_id,
        concept_id=insight_id,
        categories=categories,
        evidence_class="summary",
        required_features=("match_summary",),
        eligibility=EligibilityRule(require_role_confidence=role),
        cohort_dimensions=("hero_id", "role", "rank_tier", "patch") if cohort_relative else (),
        minimum_matches=5,
        minimum_situations=5,
        minimum_parse_coverage=None,
        effect_gate=EffectGate(effect, "native"),
        confidence_method="wilson_or_robust_median",
        statement_template_id=template or insight_id,
        action_template_id=action or insight_id,
        base_ivs=ivs,
        requires_valid_cohort=cohort_relative,
    )


def _replay(
    insight_id: str,
    categories: tuple[str, ...],
    *,
    role: bool = False,
    cohort_relative: bool = False,
    situations: int = 20,
    template: str | None = None,
    action: str | None = None,
    ivs: float = 0.60,
) -> InsightDefinition:
    return InsightDefinition(
        id=insight_id,
        concept_id=insight_id,
        categories=categories,
        evidence_class="replay",
        required_features=("replay_events",),
        eligibility=EligibilityRule(
            require_role_confidence=role, required_coverage_family="replay"
        ),
        cohort_dimensions=("hero_id", "role", "rank_tier", "patch")
        if cohort_relative
        else (),
        minimum_matches=5,
        minimum_situations=situations,
        minimum_parse_coverage=None,
        effect_gate=EffectGate(0.05, "native"),
        confidence_method="clustered_bootstrap",
        statement_template_id=template or insight_id,
        action_template_id=action or insight_id,
        base_ivs=ivs,
        requires_valid_cohort=cohort_relative,
    )


INSIGHT_DEFINITIONS: tuple[InsightDefinition, ...] = (
    _summary(
        "adjusted_role_fit",
        ("strength", "identity"),
        role=True,
        effect=0.05,
        ivs=0.82,
        cohort_relative=True,
    ),
    _summary(
        "hero_role_fit_residual",
        ("strength", "identity"),
        role=True,
        effect=0.05,
        ivs=0.76,
        cohort_relative=True,
    ),
    _summary("comfort_vs_stretch", ("identity", "weakness"), effect=0.05, ivs=0.72),
    _summary("specialization_hero_pool_entropy", ("identity",), ivs=0.58),
    _summary("collapse_tail_performance_floor", ("weakness", "consistency"), ivs=0.74),
    _summary(
        "economy_to_impact_efficiency",
        ("strength", "weakness"),
        effect=0.0005,
        ivs=0.80,
        cohort_relative=True,
    ),
    _summary(
        "tower_first_objective_orientation",
        ("strength", "style"),
        ivs=0.67,
        cohort_relative=True,
    ),
    _summary("item_timing_reliability", ("strength", "weakness"), effect=0.05, ivs=0.67),
    _summary("duration_curve", ("style", "weakness"), effect=0.05, ivs=0.65),
    _summary("current_form_divergence", ("form",), effect=0.05, ivs=0.78),
    _summary("recent_style_shift", ("form", "style"), effect=0.05, ivs=0.68),
    _summary("party_side_mode_splits", ("context",), effect=0.05, ivs=0.50),
    _replay("advantage_conversion", ("weakness", "conversion"), role=True, ivs=0.84),
    _replay("deaths_while_ahead_high_net_worth", ("weakness", "risk"), role=True, ivs=0.82),
    _replay("early_death_tax", ("weakness", "laning"), role=True, ivs=0.80),
    _replay("objective_follow_through", ("strength", "conversion"), ivs=0.76),
    _replay("power_spike_conversion", ("strength", "conversion"), role=True, ivs=0.74),
    _replay("farm_to_fight_pivot", ("style", "conversion"), role=True, ivs=0.74),
    _replay("lane_loss_recovery", ("weakness", "resilience"), role=True, ivs=0.72),
    _replay("comeback_trailing_side_safety", ("strength", "resilience"), ivs=0.70),
    _replay("teamfight_survival_conversion", ("strength", "teamfights"), role=True, ivs=0.78),
    _replay("objective_vision_timing", ("strength", "vision"), situations=10, ivs=0.76),
)

INSIGHT_REGISTRY = {definition.id: definition for definition in INSIGHT_DEFINITIONS}
MVP_A_IDS = tuple(
    definition.id for definition in INSIGHT_DEFINITIONS if definition.evidence_class == "summary"
)
MVP_B_IDS = tuple(
    definition.id for definition in INSIGHT_DEFINITIONS if definition.evidence_class == "replay"
)
