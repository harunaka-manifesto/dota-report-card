"""Reviewed v1 Pattern hypotheses; no unrestricted pair mining."""

from __future__ import annotations

from app.behavior.models import PatternDefinition

PATTERN_REGISTRY_VERSION = "free-patterns-1.0.0"


def _pattern(
    key: str,
    label: str,
    kind: str,
    required: tuple[str, ...],
    dimensions: tuple[str, ...],
    description: str,
    why: str,
    *,
    optional: tuple[str, ...] = (),
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
        optional_elements=optional,
        minimum_element_confidence=0.45,
        evaluator_key=key,
        product_tier="free",
        minimum_evidence_tier="summary_history",
        why_it_matters=why,
        copy_guardrails=("Describe the relationship; do not imply psychology or causality.",),
        version=PATTERN_REGISTRY_VERSION,
        diagnostic_questions=diagnostic_questions,
        required_deep_elements=required_deep_elements,
    )


PATTERNS: tuple[PatternDefinition, ...] = (
    _pattern("broad_pool_narrow_toolkit", "Broad Pool, Narrow Toolkit", "identity", ("hero_pool_breadth", "toolkit_breadth"), ("hero_identity",), "Many hero picks cluster around fewer recurring tools.", "It separates hero count from the playstyle repeated underneath.",),
    _pattern("broad_pool_narrow_safety_zone", "Broad Pool, Narrow Safety Zone", "contradiction", ("hero_pool_breadth", "off_pool_performance"), ("hero_identity", "adaptability"), "A broad selection range sits beside a familiar-pool performance edge.", "It shows where exploration and results diverge without calling the difference fear.", optional=("post_loss_familiarity_shift", "signature_dependence")),
    _pattern("specialist_transferable_style", "Specialist, Transferable Style", "identity", ("hero_pool_breadth", "off_pool_activity_stability"), ("hero_identity", "adaptability"), "A narrow hero pool still carries a similar activity profile outside it.", "It distinguishes preference from an observable activity drop.", optional=("off_pool_performance",)),
    _pattern("role_anchor_hero_explorer", "Role Anchor, Hero Explorer", "identity", ("role_breadth", "hero_pool_breadth"), ("role_identity", "hero_identity"), "Hero choice varies while credible role context stays concentrated.", "It makes the role context, not one pick, the through-line.",),
    _pattern("hero_anchor_role_flex", "Hero Anchor, Role Flex", "identity", ("hero_pool_breadth", "role_breadth"), ("hero_identity", "role_identity"), "A smaller hero pool appears across a wider set of role contexts.", "It distinguishes hero identity from role-context variety.",),
    _pattern("signature_strength_with_tax", "Signature Strength With a Tax", "leak", ("signature_dependence", "off_pool_performance"), ("hero_identity", "adaptability"), "Established heroes are a real performance strength while off-pool results lag.", "It keeps the strength and the constraint in the same frame.", optional=("hero_exploration_rate",)),
    _pattern("activity_travels_better_than_results", "Activity Travels Better Than Results", "contradiction", ("off_pool_activity_stability", "off_pool_performance"), ("combat_expression", "adaptability"), "Off-pool activity stays closer to familiar activity than off-pool results do.", "It points to a future diagnostic question without pretending summary data explains the gap.", diagnostic_questions=("Does laning efficiency stay stable off-pool?", "Do item timings become more variable?", "Does teamfight arrival shift?"), required_deep_elements=("lane_efficiency", "item_timing_reliability", "teamfight_participation")),
    _pattern("high_involvement_controlled_exposure", "High Involvement, Controlled Exposure", "style", ("combat_involvement", "death_exposure"), ("combat_expression", "risk_survival"), "The player joins many kill events without a similarly high death rate.", "It describes frequent participation with a separate exposure measure.",),
    _pattern("high_involvement_high_exposure", "High Involvement, High Exposure", "style", ("combat_involvement", "death_exposure"), ("combat_expression", "risk_survival"), "Frequent participation arrives with frequent deaths relative to time.", "It makes the participation/exposure trade-off visible.", optional=("post_loss_death_shift",), diagnostic_questions=("Which fight timings carry the highest cost?",), required_deep_elements=("death_cost", "teamfight_participation")),
    _pattern("selective_finisher", "Selective Finisher", "style", ("combat_involvement", "finisher_orientation", "death_exposure"), ("combat_expression", "risk_survival"), "Lower event volume combines with a higher kill share and lower death exposure.", "It describes event distribution, not kill stealing or intent.",),
    _pattern("losses_change_picks_more_than_pace", "Losses Change Picks More Than Pace", "trajectory", ("post_loss_familiarity_shift", "post_loss_activity_shift"), ("hero_identity", "session_response"), "Hero selection moves after losses while activity stays comparatively close.", "It replaces unsafe trust language with observable selection response.", optional=("post_loss_performance_response",)),
    _pattern("losses_change_pace_more_than_picks", "Losses Change Pace More Than Picks", "trajectory", ("post_loss_familiarity_shift", "post_loss_activity_shift"), ("hero_identity", "session_response"), "Activity moves after losses while hero familiarity changes little.", "It separates selection response from activity response.", optional=("post_loss_death_shift",)),
    _pattern("long_session_tax", "Long Session Tax", "leak", ("session_length_tendency", "late_session_performance"), ("session_response",), "Long sessions are common and later-session performance declines.", "It turns a session shape into a testable queue condition, not a permanent label.", optional=("post_loss_performance_response",), diagnostic_questions=("Does a game-four opt-in change the result?",), required_deep_elements=("advantage_protection",)),
    _pattern("marathon_stability", "Marathon Stability", "edge", ("session_length_tendency", "late_session_performance"), ("session_response",), "Long sessions are common and later-session performance holds or improves.", "It is the strength counterpart to a late-session leak.",),
    _pattern("form_identity_divergence", "Form Changed, Style Didn’t", "trajectory", ("recent_form_shift", "hero_pool_stability", "recent_activity_shift"), ("consistency_form", "hero_identity"), "Recent performance moves while hero distribution and activity remain comparatively stable.", "It keeps current form separate from a claim that identity changed.",),
)

PATTERN_REGISTRY = {item.key: item for item in PATTERNS}

if len(PATTERN_REGISTRY) != 15:
    raise ValueError("The active Free Pattern registry must contain exactly 15 Patterns")

__all__ = ["PATTERN_REGISTRY", "PATTERNS", "PATTERN_REGISTRY_VERSION"]
