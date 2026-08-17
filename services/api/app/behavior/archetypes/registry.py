"""Three active Free archetype groups with local prototypes."""

from __future__ import annotations

from app.behavior.models import ArchetypeGroupDefinition, ArchetypePrototype

ARCHETYPE_REGISTRY_VERSION = "free-archetypes-1.0.0"


def _prototype(key: str, label: str, statement: str, expected: dict[str, float], required: tuple[str, ...], optional_patterns: tuple[str, ...] = ()) -> ArchetypePrototype:
    return ArchetypePrototype(key, label, statement, expected, {item: 1.0 for item in expected}, required, optional_patterns, ARCHETYPE_REGISTRY_VERSION)


ARCHETYPE_GROUPS: tuple[ArchetypeGroupDefinition, ...] = (
    ArchetypeGroupDefinition(
        key="hero_identity",
        label="Hero Identity",
        description="The shape of hero selection and the toolkit underneath it.",
        product_tier="free",
        required_elements=("hero_pool_breadth", "hero_pool_stability", "hero_exploration_rate"),
        optional_elements=("toolkit_breadth", "signature_dependence", "off_pool_performance"),
        optional_patterns=("broad_pool_narrow_toolkit", "specialist_transferable_style", "activity_travels_better_than_results"),
        minimum_reliable_elements=3,
        minimum_confidence_score=0.45,
        prototypes=(
            _prototype("specialist", "Specialist", "Repeated depth in a small, familiar pool.", {"hero_pool_breadth": 0.20, "hero_pool_stability": 0.80, "hero_exploration_rate": 0.20, "signature_dependence": 0.75}, ("hero_pool_breadth", "hero_pool_stability", "hero_exploration_rate")),
            _prototype("craftsman", "Craftsman", "Several heroes, one recurring set of tools.", {"hero_pool_breadth": 0.35, "toolkit_breadth": 0.30, "hero_pool_stability": 0.75, "signature_dependence": 0.65}, ("hero_pool_breadth", "hero_pool_stability", "toolkit_breadth"), ("broad_pool_narrow_toolkit",)),
            _prototype("explorer", "Explorer", "Novelty is a visible part of selection.", {"hero_pool_breadth": 0.80, "hero_exploration_rate": 0.75, "hero_pool_stability": 0.35}, ("hero_pool_breadth", "hero_pool_stability", "hero_exploration_rate")),
            _prototype("adapter", "Adapter", "Range that usually travels with the performance.", {"hero_pool_breadth": 0.70, "toolkit_breadth": 0.70, "off_pool_performance": 0.75, "hero_exploration_rate": 0.65}, ("hero_pool_breadth", "hero_exploration_rate", "toolkit_breadth"), ("activity_travels_better_than_results",)),
            _prototype("free_agent", "Free Agent", "No small hero subset dominates the observable identity.", {"hero_pool_breadth": 0.80, "signature_dependence": 0.30, "hero_pool_stability": 0.35}, ("hero_pool_breadth", "hero_pool_stability", "hero_exploration_rate")),
        ),
        version=ARCHETYPE_REGISTRY_VERSION,
    ),
    ArchetypeGroupDefinition(
        key="combat_expression",
        label="Combat Expression",
        description="How summary-visible kill involvement is distributed, within the limits of K/D/A and time.",
        product_tier="free",
        required_elements=("combat_involvement", "finisher_orientation", "death_exposure"),
        optional_elements=(),
        optional_patterns=("high_involvement_controlled_exposure", "high_involvement_high_exposure", "selective_finisher"),
        minimum_reliable_elements=2,
        minimum_confidence_score=0.45,
        prototypes=(
            _prototype("skirmisher", "Skirmisher", "Frequent involvement with a meaningful finishing share.", {"combat_involvement": 0.75, "finisher_orientation": 0.60, "death_exposure": 0.55}, ("combat_involvement", "finisher_orientation")),
            _prototype("enabler", "Enabler", "Frequent involvement with more assists than finishes and controlled exposure.", {"combat_involvement": 0.75, "finisher_orientation": 0.30, "death_exposure": 0.40}, ("combat_involvement", "finisher_orientation")),
            _prototype("selective_finisher", "Selective Finisher", "Fewer events, a higher finishing share, and lower exposure.", {"combat_involvement": 0.40, "finisher_orientation": 0.75, "death_exposure": 0.30}, ("combat_involvement", "finisher_orientation")),
            _prototype("connector", "Connector", "Assist-oriented involvement without a large exposure bill.", {"combat_involvement": 0.55, "finisher_orientation": 0.30, "death_exposure": 0.25}, ("combat_involvement", "finisher_orientation")),
            _prototype("balanced", "Balanced", "No strong extreme across the summary-visible combat Elements.", {"combat_involvement": 0.50, "finisher_orientation": 0.50, "death_exposure": 0.50}, ("combat_involvement", "finisher_orientation")),
        ),
        version=ARCHETYPE_REGISTRY_VERSION,
    ),
    ArchetypeGroupDefinition(
        key="session_style",
        label="Session Style",
        description="How sessions are shaped and what changes as a session continues.",
        product_tier="free",
        required_elements=("session_length_tendency", "late_session_performance"),
        optional_elements=("post_loss_performance_response", "post_loss_activity_shift", "post_loss_familiarity_shift", "post_loss_death_shift"),
        optional_patterns=("long_session_tax", "marathon_stability", "losses_change_picks_more_than_pace"),
        minimum_reliable_elements=2,
        minimum_confidence_score=0.45,
        prototypes=(
            _prototype("sprinter", "Sprinter", "Shorter sessions, with little game-four evidence.", {"session_length_tendency": 0.25, "late_session_performance": 0.50}, ("session_length_tendency",)),
            _prototype("grinder", "Grinder", "Longer sessions where later performance holds up.", {"session_length_tendency": 0.75, "late_session_performance": 0.55}, ("session_length_tendency", "late_session_performance"), ("marathon_stability",)),
            _prototype("second_wind", "Second Wind", "Performance improves as the session goes on.", {"session_length_tendency": 0.65, "late_session_performance": 0.75}, ("session_length_tendency", "late_session_performance")),
            _prototype("front_loaded", "Front-Loaded", "Long sessions are common, but the later games give back some edge.", {"session_length_tendency": 0.75, "late_session_performance": 0.25}, ("session_length_tendency", "late_session_performance"), ("long_session_tax",)),
            _prototype("reset_player", "Reset Player", "The next game changes in a measurable way after a loss.", {"session_length_tendency": 0.50, "post_loss_performance_response": 0.70, "post_loss_activity_shift": 0.55}, ("session_length_tendency", "post_loss_performance_response")),
            _prototype("even_keel", "Even-Keel", "Session position and post-loss shifts stay close to neutral.", {"session_length_tendency": 0.50, "late_session_performance": 0.50, "post_loss_performance_response": 0.50}, ("session_length_tendency", "late_session_performance")),
        ),
        version=ARCHETYPE_REGISTRY_VERSION,
    ),
)

ARCHETYPE_GROUP_REGISTRY = {item.key: item for item in ARCHETYPE_GROUPS}

__all__ = ["ARCHETYPE_GROUP_REGISTRY", "ARCHETYPE_GROUPS", "ARCHETYPE_REGISTRY_VERSION"]
