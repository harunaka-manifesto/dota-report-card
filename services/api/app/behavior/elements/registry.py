"""Versioned catalog of the 23 active Free Elements."""

from __future__ import annotations

from app.behavior.models import ElementDefinition
from app.behavior.tiers import SUMMARY_CAPABILITIES

ELEMENT_REGISTRY_VERSION = "free-elements-1.0.0"


def _element(
    key: str,
    label: str,
    dimension: str,
    question: str,
    description: str,
    axis: tuple[str, str],
    *,
    minimum_sample: int,
    minimum_coverage: float = 0.0,
    capabilities: tuple[str, ...] = (),
    normalization: str,
    confounders: tuple[str, ...] = (),
    version: str = ELEMENT_REGISTRY_VERSION,
) -> ElementDefinition:
    return ElementDefinition(
        key=key,
        label=label,
        dimension_key=dimension,
        description=description,
        user_question=question,
        why_it_exists=description,
        product_tier="free",
        minimum_evidence_tier="summary_history",
        required_capabilities=capabilities or tuple(sorted(SUMMARY_CAPABILITIES & {"summary.hero"})),
        scorer_key=key,
        minimum_sample=minimum_sample,
        minimum_coverage=minimum_coverage,
        axis_left=axis[0],
        axis_right=axis[1],
        normalization_basis=normalization,
        confounders=confounders,
        copy_guardrails=("Describe observed match behavior; do not infer hidden intent.",),
        version=version,
    )


ELEMENTS: tuple[ElementDefinition, ...] = (
    _element("hero_pool_breadth", "Hero Pool Breadth", "hero_identity", "How distributed is your hero usage?", "Measures whether picks are concentrated or spread across a wider pool.", ("Specialized", "Broad"), minimum_sample=30, capabilities=("summary.hero",), normalization="bounded_absolute", confounders=("hero availability and patch changes can shape the pool",)),
    _element("hero_pool_stability", "Hero Pool Stability", "hero_identity", "Do you return to a similar hero distribution over time?", "Compares earlier and later hero distributions without calling change a flaw.", ("Changing", "Stable"), minimum_sample=60, capabilities=("summary.hero", "summary.chronology"), normalization="window_comparison", confounders=("patches, hero releases, and the bounded history window can move the distribution",)),
    _element("hero_exploration_rate", "Hero Exploration", "hero_identity", "How often do you leave your established pool?", "Measures later picks outside a pool built from earlier history.", ("Familiar picks", "Exploratory picks"), minimum_sample=60, capabilities=("summary.hero", "summary.chronology"), normalization="conditional_comparison", confounders=("a short recent window can make exploration look larger than it is",)),
    _element("toolkit_breadth", "Toolkit Breadth", "hero_identity", "Do your heroes ask for different toolkits?", "Uses the versioned hero taxonomy to distinguish hero count from repeated tools.", ("Narrow toolkit", "Diverse toolkit"), minimum_sample=30, minimum_coverage=0.80, capabilities=("summary.hero", "hero.taxonomy"), normalization="bounded_absolute", confounders=("taxonomy labels are editorial and versioned",)),
    _element("signature_dependence", "Signature Dependence", "hero_identity", "How much does performance hold up on established heroes?", "Compares a past-established pool with later off-pool results.", ("Little dependence", "High dependence"), minimum_sample=30, capabilities=("summary.hero", "summary.outcome", "summary.chronology"), normalization="conditional_comparison", confounders=("hero learning, patch, role mix, and draft quality differ across windows",)),
    _element("post_loss_familiarity_shift", "Post-Loss Familiarity Shift", "hero_identity", "Do picks become more familiar after a loss?", "Measures selection response inside valid sessions, not a mental state.", ("Explores after losses", "Returns to familiarity after losses"), minimum_sample=30, capabilities=("summary.hero", "summary.outcome", "summary.chronology"), normalization="conditional_comparison", confounders=("session gaps and stopping behavior affect valid transitions",)),
    _element("role_breadth", "Role Breadth", "role_identity", "How concentrated are credible role-context hints?", "Measures role-hint concentration without pretending summary data identifies exact positions.", ("Role-anchored", "Role-flexible"), minimum_sample=30, minimum_coverage=0.40, capabilities=("summary.role_hint",), normalization="bounded_absolute", confounders=("lane-role values are hints, not exact position labels",)),
    _element("role_switch_rate", "Role Switching", "role_identity", "How often does the role context change?", "Measures changes between adjacent credible role hints.", ("Usually same context", "Frequently switches context"), minimum_sample=20, capabilities=("summary.role_hint", "summary.chronology"), normalization="bounded_absolute", confounders=("missing role hints remove transitions from the denominator",)),
    _element("combat_involvement", "Combat Involvement", "combat_expression", "How often are you involved in kills relative to time?", "Uses kills, assists, duration, and cautious role adjustment when supported.", ("Lower involvement", "Higher involvement"), minimum_sample=30, capabilities=("summary.kda", "summary.time"), normalization="role_adjusted_provisional", confounders=("team tempo and hero style affect involvement rate",)),
    _element("finisher_orientation", "Finisher Orientation", "combat_expression", "When involved, how often are you the killer?", "Describes the split between kills and assists without assigning motive.", ("Assist-oriented", "Kill-oriented"), minimum_sample=30, capabilities=("summary.kda",), normalization="role_adjusted_provisional", confounders=("team kill totals and role mix are only partly visible in summary history",)),
    _element("death_exposure", "Death Exposure", "risk_survival", "How often do you die relative to time and role context?", "Measures deaths per unit of time while keeping role and hero confounding visible.", ("Lower exposure", "Higher exposure"), minimum_sample=30, capabilities=("summary.kda", "summary.time"), normalization="role_adjusted_provisional", confounders=("some heroes and role contexts structurally trade deaths for map value",)),
    _element("off_pool_performance", "Off-Pool Performance", "adaptability", "How well does observable performance transfer away from your pool?", "Compares familiar and off-pool evaluation matches using a chronological split.", ("Drops off-pool", "Travels off-pool"), minimum_sample=40, capabilities=("summary.hero", "summary.outcome", "summary.chronology"), normalization="conditional_comparison", confounders=("patch, draft quality, and hero learning can differ between windows",)),
    _element("off_pool_activity_stability", "Off-Pool Activity Stability", "adaptability", "Does combat involvement stay similar off-pool?", "Keeps the signed activity change while scoring how much the activity travels.", ("Activity changes off-pool", "Activity travels off-pool"), minimum_sample=24, capabilities=("summary.hero", "summary.kda", "summary.time"), normalization="self_relative", confounders=("role and game tempo can change with hero choice",)),
    _element("off_role_performance", "Off-Role Performance", "adaptability", "How well does performance transfer outside established role contexts?", "Compares performance in familiar and off-role contexts when role hints are well covered.", ("Drops off-role", "Travels off-role"), minimum_sample=24, minimum_coverage=0.50, capabilities=("summary.role_hint", "summary.outcome", "summary.chronology"), normalization="conditional_comparison", confounders=("summary role hints have a lower evidence ceiling than parsed positions",)),
    _element("performance_volatility", "Performance Volatility", "consistency_form", "How variable is the observable performance proxy?", "Uses robust dispersion rather than letting one extreme match decide the result.", ("Steadier", "More variable"), minimum_sample=30, capabilities=("summary.outcome", "summary.kda", "summary.time"), normalization="self_relative", confounders=("the proxy is not a full performance model",)),
    _element("recent_form_shift", "Recent Form Shift", "consistency_form", "Is recent observable performance different from the preceding window?", "Compares recent matches with an earlier reference window and keeps the direction visible.", ("Recent decline", "Recent improvement"), minimum_sample=45, capabilities=("summary.outcome", "summary.chronology"), normalization="window_comparison", confounders=("recent opponents, patches, and hero mix are not controlled",)),
    _element("recent_activity_shift", "Recent Activity Shift", "consistency_form", "Has combat involvement changed recently?", "Compares recent and prior role-aware activity without treating activity as a grade.", ("Recently less involved", "Recently more involved"), minimum_sample=45, capabilities=("summary.kda", "summary.time", "summary.chronology"), normalization="window_comparison", confounders=("team tempo and role mix may differ between windows",)),
    _element("long_game_performance_shift", "Long-Game Performance Shift", "consistency_form", "Does observable performance differ in long games?", "Contrasts long and short games while keeping duration endogenous to the match state.", ("Falls in long games", "Improves in long games"), minimum_sample=20, capabilities=("summary.outcome", "summary.time"), normalization="conditional_comparison", confounders=("game duration is shaped by both teams and game state",)),
    _element("session_length_tendency", "Session Length Tendency", "session_response", "Do you usually play short bursts or long sessions?", "Describes session shape without using results to define it.", ("Short bursts", "Long sessions"), minimum_sample=25, capabilities=("summary.chronology", "summary.time"), normalization="bounded_absolute", confounders=("the history limit can truncate a session boundary",)),
    _element("late_session_performance", "Late-Session Performance", "session_response", "Does observable performance rise or fall as a session continues?", "Measures within-session performance movement across independent multi-game sessions.", ("Declines later", "Improves later"), minimum_sample=27, capabilities=("summary.chronology", "summary.outcome", "summary.time"), normalization="window_comparison", confounders=("stopping behavior and role mix can confound session position",)),
    _element("post_loss_performance_response", "Post-Loss Performance Response", "session_response", "How does next-match observable performance differ after a loss?", "Compares valid within-session next matches after wins and losses.", ("Lower after losses", "Higher after losses"), minimum_sample=30, capabilities=("summary.outcome", "summary.chronology"), normalization="conditional_comparison", confounders=("matchmaking, parties, stopping behavior, and hero changes affect the next game",)),
    _element("post_loss_activity_shift", "Post-Loss Activity Shift", "session_response", "Does combat involvement change after a loss?", "Measures the next-match activity contrast inside valid sessions.", ("Slower after losses", "More active after losses"), minimum_sample=30, capabilities=("summary.kda", "summary.time", "summary.outcome", "summary.chronology"), normalization="conditional_comparison", confounders=("a next match may have a different role or team tempo",)),
    _element("post_loss_death_shift", "Post-Loss Death Exposure Shift", "session_response", "Does death exposure change after a loss?", "Measures next-match deaths per minute after losses versus wins.", ("Lower exposure after losses", "Higher exposure after losses"), minimum_sample=30, capabilities=("summary.kda", "summary.time", "summary.outcome", "summary.chronology"), normalization="conditional_comparison", confounders=("role and hero changes affect death exposure",)),
)

ELEMENT_REGISTRY = {item.key: item for item in ELEMENTS}

if len(ELEMENT_REGISTRY) != 23:
    raise ValueError("The active Free Element registry must contain exactly 23 Elements")

__all__ = ["ELEMENT_REGISTRY", "ELEMENTS", "ELEMENT_REGISTRY_VERSION"]
