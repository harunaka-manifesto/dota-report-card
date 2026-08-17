"""Canonical reviewed v4 Patterns over upstream Element results."""

from __future__ import annotations

from app.behavior.models import PatternDefinition

PATTERN_REGISTRY_VERSION = "free-patterns-4.0.0"


def _pattern(
    key: str,
    label: str,
    kind: str,
    required: tuple[str, ...],
    dimensions: tuple[str, ...],
    description: str,
    why: str,
    *,
    modifiers: tuple[str, ...] = (),
    family: str,
    tier: str,
    diagnostic_questions: tuple[str, ...] = (),
    required_deep_elements: tuple[str, ...] = (),
) -> PatternDefinition:
    return PatternDefinition(
        key=key,
        label=label,
        description=description,
        kind=kind,  # type: ignore[arg-type]
        dimension_keys=dimensions,
        required_elements=required,
        modifier_elements=modifiers,
        minimum_element_confidence=0.45,
        evaluator_key=key,
        product_tier="free",
        minimum_evidence_tier="summary_history",
        why_it_matters=why,
        copy_guardrails=("Describe the relationship; do not imply psychology or causality.",),
        version=PATTERN_REGISTRY_VERSION,
        family=family,
        tier=tier,  # type: ignore[arg-type]
        diagnostic_questions=diagnostic_questions,
        required_deep_elements=required_deep_elements,
    )


PATTERNS: tuple[PatternDefinition, ...] = (
    _pattern(
        "same_playbook", "Same Playbook", "identity",
        ("hero_pool_breadth", "toolkit_breadth"), ("hero_identity",),
        "The player changes hero names more than the kinds of Dota jobs those heroes perform.",
        "It separates hero-name variety from the toolkit repeated underneath.",
        family="breadth_toolkit", tier="A",
    ),
    _pattern(
        "comfort_edge", "Comfort Edge", "contradiction",
        ("hero_pool_breadth", "off_pool_performance"), ("hero_identity", "adaptability"),
        "The playable pool is wider than the range where current results reliably hold.",
        "It shows where selection range and result transfer diverge without assigning a motive.",
        modifiers=("hero_exploration_rate", "post_loss_familiarity_shift"),
        family="breadth_transfer", tier="A",
    ),
    _pattern(
        "partial_transfer", "Partial Transfer", "contradiction",
        ("off_pool_activity_stability", "off_pool_performance"), ("combat_expression", "adaptability"),
        "Fight presence travels off-pool better than results do.",
        "It weakens the simple explanation that the player merely disappears from fights outside comfort.",
        family="presence_transfer", tier="A",
    ),
    _pattern(
        "stable_style", "Stable Style", "trajectory",
        ("recent_form_shift", "hero_pool_stability", "recent_activity_shift"), ("consistency_form", "hero_identity"),
        "Recent results changed more than the visible hero-pool shape and fight pace did.",
        "It keeps current form separate from a claim that the player’s whole style changed.",
        family="form_stability", tier="A",
    ),
    _pattern(
        "versatile_core", "Versatile Core", "identity",
        ("hero_pool_breadth", "toolkit_breadth"), ("hero_identity",),
        "A small hero count still covers meaningfully different Dota jobs.",
        "It distinguishes a focused pool from a narrow functional toolkit.",
        family="breadth_toolkit", tier="A",
    ),
    _pattern(
        "proven_flexibility", "Proven Flexibility", "edge",
        ("hero_pool_breadth", "off_pool_performance"), ("hero_identity", "adaptability"),
        "The player’s broader pool is backed by performance transfer, not only selection variety.",
        "It makes a broad pool meaningful without treating variety alone as proof.",
        family="breadth_transfer", tier="A",
    ),
    _pattern(
        "selective_closer", "Selective Closer", "style",
        ("combat_involvement", "finisher_orientation"), ("combat_expression",),
        "The player is not everywhere, but their appearances skew toward final kill credit.",
        "It describes event volume and finishing expression without making deaths part of the gate.",
        modifiers=("death_exposure",), family="involvement_finishing", tier="B",
    ),
    _pattern(
        "loss_response", "Loss Response", "trajectory",
        ("post_loss_familiarity_shift", "post_loss_activity_shift"), ("hero_identity", "session_response"),
        "After a loss, hero familiarity and next-game activity can move together or separately.",
        "It exposes observable post-loss selection and activity movement without naming a mental state.",
        family="post_loss", tier="B",
    ),
    _pattern(
        "controlled_presence", "Controlled Presence", "style",
        ("combat_involvement", "death_exposure"), ("combat_expression", "risk_survival"),
        "High involvement appears without a similarly high death-exposure signal.",
        "It describes frequent participation with a separate exposure measure.",
        modifiers=("finisher_orientation",), family="involvement_deaths", tier="B",
    ),
    _pattern(
        "heavy_exposure", "Heavy Exposure", "leak",
        ("combat_involvement", "death_exposure"), ("combat_expression", "risk_survival"),
        "High presence currently carries a visible death cost.",
        "It makes the participation/exposure trade-off visible without calling it reckless.",
        modifiers=("finisher_orientation",), family="involvement_deaths", tier="B",
    ),
    _pattern(
        "session_fade", "Session Fade", "leak",
        ("session_length_tendency", "late_session_performance"), ("session_response",),
        "Later games in sufficiently long sessions show a repeated weaker result signal.",
        "It turns session shape into a testable observation without claiming fatigue.",
        family="session_drift", tier="B",
    ),
    _pattern(
        "session_rise", "Session Rise", "edge",
        ("session_length_tendency", "late_session_performance"), ("session_response",),
        "Later-session results improve often enough to stand out.",
        "It surfaces a late-session improvement pattern without claiming warm-up or resilience.",
        family="session_drift", tier="B",
    ),
    _pattern(
        "session_hold", "Session Hold", "edge",
        ("session_length_tendency", "late_session_performance"), ("session_response",),
        "Long sessions exist without a meaningful late-session result decline.",
        "It distinguishes a stable long-session result signal from a claim about fatigue resistance.",
        family="session_drift", tier="B",
    ),
    _pattern(
        "assist_presence", "Assist Presence", "style",
        ("combat_involvement", "finisher_orientation"), ("combat_expression",),
        "Meaningful fight involvement is expressed more through assists than final kill credit.",
        "It describes the visible kill/assist split without inferring duties from assists alone.",
        modifiers=("death_exposure",), family="involvement_finishing", tier="B",
    ),
)

PATTERN_REGISTRY = {item.key: item for item in PATTERNS}
EXPECTED_PATTERN_KEYS = frozenset(item.key for item in PATTERNS)
if len(PATTERN_REGISTRY) != 14 or set(PATTERN_REGISTRY) != EXPECTED_PATTERN_KEYS:
    raise ValueError("The active Free Pattern registry must contain exactly the canonical 14 Patterns")

__all__ = ["PATTERN_REGISTRY", "PATTERNS", "PATTERN_REGISTRY_VERSION", "EXPECTED_PATTERN_KEYS"]
