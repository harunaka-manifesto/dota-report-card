"""Finite, versioned registry of Free DNA finding definitions."""

from __future__ import annotations

from app.findings.models import FindingDefinition

FINDING_VERSION = "free-findings-1.0.0"


def _definition(
    key: str,
    kind: str,
    *,
    required: tuple[str, ...],
    optional: tuple[str, ...] = (),
    families: int = 2,
    minimum_confidence: float = 0.45,
    samples: dict[str, int] | None = None,
    contradiction_bonus: float = 1.0,
    surprise: float,
    specificity: float,
    consequence: float,
    actionability: float,
    shareability: float,
    experiment: str | None,
    tags: frozenset[str],
    dimensions: tuple[str, ...] = (),
) -> FindingDefinition:
    return FindingDefinition(
        key=key,
        kind=kind,  # type: ignore[arg-type]
        required_signals=required,
        optional_signals=optional,
        minimum_families=families,
        minimum_confidence=minimum_confidence,
        minimum_samples=samples or {},
        contradiction_bonus=contradiction_bonus,
        surprise_prior=surprise,
        specificity_prior=specificity,
        consequence_prior=consequence,
        actionability_prior=actionability,
        shareability_prior=shareability,
        headline_template_key=key,
        body_template_key=key,
        interpretation_template_key=key,
        experiment_key=experiment,
        concept_tags=tags,
        related_dimensions=dimensions,
        version=FINDING_VERSION,
    )


FINDING_REGISTRY: dict[str, FindingDefinition] = {
    "broad_pool_narrow_safety_zone": _definition(
        "broad_pool_narrow_safety_zone", "contradiction",
        required=("feature.normalized_hero_entropy",),
        optional=("dimension.breadth", "feature.familiar_vs_off_pool_delta", "derived.loss_familiarity_delta"),
        samples={"feature.normalized_hero_entropy": 20}, surprise=0.92, specificity=0.88,
        consequence=0.78, actionability=0.82, shareability=0.96, experiment="adjacent_pick_after_loss",
        tags=frozenset({"hero_breadth", "hero_familiarity"}), dimensions=("breadth", "adaptability", "resilience"),
        contradiction_bonus=1.08,
    ),
    "many_heroes_same_toolkit": _definition(
        "many_heroes_same_toolkit", "identity",
        required=("feature.unique_hero_count", "hero.pattern.primary"),
        samples={"feature.unique_hero_count": 20, "hero.pattern.primary": 3},
        surprise=0.86, specificity=0.90, consequence=0.62, actionability=0.76, shareability=0.90,
        experiment="adjacent_toolkit_pick", tags=frozenset({"hero_breadth", "hero_toolkit"}),
        dimensions=("breadth", "role"),
    ),
    "activity_travels_better_than_results": _definition(
        "activity_travels_better_than_results", "contradiction",
        required=("feature.off_pool_activity_delta", "feature.familiar_vs_off_pool_delta"),
        optional=("dimension.activity", "dimension.adaptability"),
        samples={"feature.off_pool_activity_delta": 8, "feature.familiar_vs_off_pool_delta": 8},
        surprise=0.88, specificity=0.91, consequence=0.86, actionability=0.90, shareability=0.88,
        experiment="stretch_conversion_rule", tags=frozenset({"activity", "hero_familiarity"}),
        dimensions=("activity", "adaptability"), contradiction_bonus=1.08,
    ),
    "losses_change_trust_more_than_pace": _definition(
        "losses_change_trust_more_than_pace", "contradiction",
        required=("derived.loss_familiarity_delta",),
        optional=("dimension.resilience", "derived.loss_activity_delta"),
        samples={"derived.loss_familiarity_delta": 12}, surprise=0.95, specificity=0.93,
        consequence=0.74, actionability=0.82, shareability=0.98, experiment="adjacent_pick_after_loss",
        tags=frozenset({"hero_familiarity", "activity", "form"}), dimensions=("resilience", "activity"),
        contradiction_bonus=1.08,
    ),
    "long_session_tax": _definition(
        "long_session_tax", "leak", required=("pattern.session_decline",),
        optional=("dimension.endurance", "feature.session_length_p75"), samples={"pattern.session_decline": 8},
        surprise=0.88, specificity=0.84, consequence=0.88, actionability=0.93, shareability=0.86,
        experiment="game_four_opt_in", tags=frozenset({"session_endurance", "form"}), dimensions=("endurance", "rhythm"),
    ),
    "long_game_edge": _definition(
        "long_game_edge", "edge", required=("pattern.long_game_improvement",),
        optional=("dimension.endurance", "dimension.orientation"), samples={"pattern.long_game_improvement": 5},
        surprise=0.78, specificity=0.77, consequence=0.74, actionability=0.68, shareability=0.72,
        experiment="late_game_repeat", tags=frozenset({"duration", "session_endurance"}), dimensions=("endurance",),
    ),
    "long_game_leak": _definition(
        "long_game_leak", "leak", required=("pattern.long_game_decline",),
        optional=("dimension.endurance", "dimension.orientation"), samples={"pattern.long_game_decline": 5},
        surprise=0.84, specificity=0.82, consequence=0.88, actionability=0.86, shareability=0.80,
        experiment="late_game_simplification", tags=frozenset({"duration", "session_endurance"}), dimensions=("endurance",),
    ),
    "form_identity_divergence": _definition(
        "form_identity_divergence", "trajectory",
        required=("pattern.recent_improvement",),
        optional=("pattern.recent_decline", "feature.recent_hero_concentration_delta", "feature.recent_activity_delta"),
        samples={"pattern.recent_improvement": 15}, surprise=0.90, specificity=0.88, consequence=0.70,
        actionability=0.70, shareability=0.84, experiment="recent_style_check", tags=frozenset({"form", "hero_breadth"}),
        dimensions=("breadth", "activity", "rhythm"),
    ),
    "strength_with_tax": _definition(
        "strength_with_tax", "leak", required=(), optional=(), families=2, samples={}, surprise=0.90,
        specificity=0.86, consequence=0.84, actionability=0.85, shareability=0.84, experiment="strength_tax_check",
        tags=frozenset({"activity", "hero_breadth", "session_endurance"}), dimensions=("activity", "adaptability", "endurance"),
    ),
    "signature_hero_mechanism": _definition(
        "signature_hero_mechanism", "edge", required=("hero.signature", "hero.pattern.primary"),
        optional=("dimension.breadth", "dimension.role", "dimension.activity"), samples={"hero.pattern.primary": 3},
        surprise=0.80, specificity=0.94, consequence=0.68, actionability=0.78, shareability=0.86,
        experiment="adjacent_toolkit_pick", tags=frozenset({"hero_toolkit", "role_identity"}), dimensions=("breadth", "role"),
    ),
    "role_vs_hero_identity": _definition(
        "role_vs_hero_identity", "identity", required=("dimension.role", "dimension.breadth"),
        optional=("feature.dominant_role_share", "feature.normalized_hero_entropy"), samples={"dimension.role": 20, "dimension.breadth": 20},
        surprise=0.78, specificity=0.82, consequence=0.58, actionability=0.66, shareability=0.78,
        experiment="role_toolkit_swap", tags=frozenset({"role_identity", "hero_breadth"}), dimensions=("role", "breadth"),
    ),
    "volatile_results_stable_style": _definition(
        "volatile_results_stable_style", "contradiction", required=("pattern.consistency_collapse",),
        optional=("feature.recent_hero_concentration_delta", "feature.recent_activity_delta"), samples={"pattern.consistency_collapse": 10},
        surprise=0.86, specificity=0.83, consequence=0.70, actionability=0.62, shareability=0.78,
        experiment="stable_style_review", tags=frozenset({"form", "activity", "hero_breadth"}), dimensions=("activity", "breadth"),
        contradiction_bonus=1.08,
    ),
    "hidden_strength_fallback": _definition(
        "hidden_strength_fallback", "strength", required=(), optional=(), families=1, minimum_confidence=0.60,
        samples={}, surprise=0.48, specificity=0.68, consequence=0.54, actionability=0.58, shareability=0.72,
        experiment=None, tags=frozenset({"strength"}),
    ),
}

__all__ = ["FINDING_REGISTRY", "FINDING_VERSION"]
