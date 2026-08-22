"""Canonical public registry for the 18 Free Elements."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Iterable

from app.behavior.models import ElementDefinition
from app.behavior.tiers import SUMMARY_CAPABILITIES

ELEMENT_REGISTRY_VERSION = "free-elements-5.1.0"
# All public five-zone Elements use the same half-open score intervals.  The
# right edge belongs to the next zone, so 0.20 is the first point in zone 2.
# Keeping the boundary map here makes score → zone a single inspectable rule.
ZONE_BOUNDARIES = (0.20, 0.40, 0.60, 0.80)


def _element(
    key: str,
    label: str,
    dimension: str,
    question: str,
    description: str,
    axis: tuple[str, str],
    zones: tuple[str, ...],
    *,
    minimum_sample: int,
    minimum_coverage: float = 0.0,
    capabilities: tuple[str, ...] = (),
    normalization: str,
    confounders: tuple[str, ...] = (),
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
        version=ELEMENT_REGISTRY_VERSION,
        zone_labels=zones,
    )


ELEMENTS: tuple[ElementDefinition, ...] = (
    _element("hero_pool_breadth", "Breadth", "hero_identity", "How broad is your meaningful hero pool?", "How broad the meaningful hero pool is.", ("Focused", "Wide"), ("Focused", "Selective", "Mixed", "Varied", "Wide"), minimum_sample=30, capabilities=("summary.hero",), normalization="bounded_absolute", confounders=("hero availability and patch changes can shape the pool",)),
    _element("hero_pool_stability", "Stability", "hero_identity", "How settled is your hero pool over time?", "How settled versus shifting the hero pool is.", ("Restless", "Steady"), ("Restless", "Shifting", "Mixed", "Settled", "Steady"), minimum_sample=60, capabilities=("summary.hero", "summary.chronology"), normalization="window_comparison", confounders=("patches, hero releases, and the bounded history window can move the distribution",)),
    _element("hero_exploration_rate", "Exploration", "hero_identity", "How often do new or unfamiliar heroes enter?", "How often new or unfamiliar heroes enter the pool.", ("Comfort", "Experimental"), ("Comfort", "Familiar", "Open", "Curious", "Experimental"), minimum_sample=60, capabilities=("summary.hero", "summary.chronology"), normalization="conditional_comparison", confounders=("a short recent window can make exploration look larger than it is",)),
    _element("toolkit_breadth", "Toolkit", "hero_identity", "How varied are the Dota jobs underneath your picks?", "How varied the Dota jobs underneath the hero picks are.", ("Compact", "Diverse"), ("Compact", "Focused", "Mixed", "Versatile", "Diverse"), minimum_sample=30, minimum_coverage=0.80, capabilities=("summary.hero", "hero.taxonomy"), normalization="bounded_absolute", confounders=("taxonomy labels are editorial and versioned",)),
    _element("post_loss_familiarity_shift", "Familiarity", "hero_identity", "Where do your picks move after a loss?", "Whether post-loss hero choice moves toward or away from familiar picks.", ("Branches out", "Comfort pick"), ("Branches out", "Explores", "Unchanged", "Returns", "Comfort pick"), minimum_sample=30, capabilities=("summary.hero", "summary.outcome", "summary.chronology"), normalization="conditional_comparison", confounders=("session gaps and stopping behavior affect valid transitions",)),
    _element("role_breadth", "Role", "role_identity", "How broad are your credible role contexts?", "The breadth of credible role contexts visible in summary data.", ("Anchored", "Fluid"), ("Anchored", "Centered", "Mixed", "Flexible", "Fluid"), minimum_sample=30, minimum_coverage=0.40, capabilities=("summary.role_hint",), normalization="bounded_absolute", confounders=("lane-role values are hints, not exact position labels",)),
    _element("combat_involvement", "Involvement", "combat_expression", "How often do you appear in kill events per time?", "How frequently the player appears in kill events per time.", ("Quiet", "Everywhere"), ("Quiet", "Selective", "Present", "Active", "Everywhere"), minimum_sample=30, capabilities=("summary.kda", "summary.time"), normalization="role_adjusted_provisional", confounders=("team tempo and hero style affect involvement rate",)),
    _element("finisher_orientation", "Finishing", "combat_expression", "How does your involvement split between kills and assists?", "The kill-versus-assist expression inside involvement.", ("Setup", "Cleanup"), ("Setup", "Support", "Split", "Closer", "Cleanup"), minimum_sample=30, capabilities=("summary.kda",), normalization="role_adjusted_provisional", confounders=("team kill totals and role mix are only partly visible in summary history",)),
    _element("death_exposure", "Deaths", "risk_survival", "How exposed are you to deaths per time?", "Death exposure per unit of time.", ("Elusive", "Frequent"), ("Elusive", "Safe", "Mixed", "Exposed", "Frequent"), minimum_sample=30, capabilities=("summary.kda", "summary.time"), normalization="role_adjusted_provisional", confounders=("some heroes and role contexts structurally trade deaths for map value",)),
    _element("off_pool_performance", "Transfer", "adaptability", "Does observable performance travel outside the familiar pool?", "Whether observable performance holds outside the familiar pool.", ("Falls off", "Carries over"), ("Falls off", "Slips", "Holds", "Travels", "Carries over"), minimum_sample=40, capabilities=("summary.hero", "summary.outcome", "summary.chronology"), normalization="conditional_comparison", confounders=("patch, draft quality, and hero learning can differ between windows",)),
    _element("off_pool_activity_stability", "Presence", "adaptability", "Does combat activity hold outside the familiar pool?", "Whether combat activity holds outside the familiar pool.", ("Changes shape", "Unchanged"), ("Changes shape", "Shifts", "Similar", "Holds", "Unchanged"), minimum_sample=24, capabilities=("summary.hero", "summary.kda", "summary.time"), normalization="self_relative", confounders=("role and game tempo can change with hero choice",)),
    _element("performance_volatility", "Volatility", "consistency_form", "How variable is observable performance match to match?", "Match-to-match variability in the observable performance proxy.", ("Rock solid", "Wild"), ("Rock solid", "Steady", "Variable", "Swingy", "Wild"), minimum_sample=30, capabilities=("summary.outcome", "summary.kda", "summary.time"), normalization="self_relative", confounders=("the proxy is not a full performance model",)),
    _element("recent_form_shift", "Form", "consistency_form", "How has recent observable form moved?", "Recent result movement versus a prior window.", ("Sliding", "Surging"), ("Sliding", "Cooling", "Flat", "Rising", "Surging"), minimum_sample=45, capabilities=("summary.outcome", "summary.chronology"), normalization="window_comparison", confounders=("recent opponents, patches, and hero mix are not controlled",)),
    _element("recent_activity_shift", "Pace", "consistency_form", "How has recent combat activity moved?", "Recent combat-activity movement versus a prior window.", ("Quieter", "Full tilt"), ("Quieter", "Calmer", "Same", "Busier", "Full tilt"), minimum_sample=45, capabilities=("summary.kda", "summary.time", "summary.chronology"), normalization="window_comparison", confounders=("team tempo and role mix may differ between windows",)),
    _element("session_length_tendency", "Duration", "session_response", "What session length tends to appear?", "The typical session length tendency.", ("Burst", "Marathon"), ("Burst", "Short", "Medium", "Long", "Marathon"), minimum_sample=25, capabilities=("summary.chronology", "summary.time"), normalization="bounded_absolute", confounders=("the bounded time window can truncate a session boundary",)),
    _element("late_session_performance", "Drift", "session_response", "What happens to results later in a session?", "Later-session result movement.", ("Drops", "Finishes strong"), ("Drops", "Fades", "Holds", "Warms up", "Finishes strong"), minimum_sample=27, capabilities=("summary.chronology", "summary.outcome", "summary.time"), normalization="window_comparison", confounders=("stopping behavior and role mix can confound session position",)),
    _element("post_loss_activity_shift", "Tempo", "session_response", "How does next-game activity move after a loss?", "Post-loss next-game activity movement.", ("Pulls back", "Accelerates"), ("Pulls back", "Quieter", "Same", "Speeds up", "Accelerates"), minimum_sample=30, capabilities=("summary.kda", "summary.time", "summary.outcome", "summary.chronology"), normalization="conditional_comparison", confounders=("a next match may have a different role or team tempo",)),
    _element("post_loss_performance_response", "Recovery", "session_response", "How does comparable next-game performance move after a loss?", "Post-loss performance movement against the player's comparable personal baseline.", ("Drops", "Surges"), ("Drops", "Slips", "Holds", "Recovers", "Surges"), minimum_sample=30, capabilities=("summary.hero", "summary.kda", "summary.time", "summary.outcome", "summary.chronology", "hero.taxonomy"), normalization="context_adjusted_conditional_comparison", confounders=("role and hero-function context may differ between transitions", "session boundaries and stopping behavior limit valid comparisons")),
)

ELEMENT_REGISTRY = {item.key: item for item in ELEMENTS}

EXPECTED_ELEMENT_KEYS = frozenset(item.key for item in ELEMENTS)
if len(ELEMENT_REGISTRY) != 18 or set(ELEMENT_REGISTRY) != EXPECTED_ELEMENT_KEYS:
    raise ValueError("The active Free Element registry must contain exactly the canonical 18 Elements")


def zone_for_score(key: str, score: float | None) -> str | None:
    if score is None:
        return None
    labels = ELEMENT_REGISTRY[key].zone_labels
    if not labels:
        return None
    bounded = min(1.0, max(0.0, float(score)))
    index = bisect_right(ZONE_BOUNDARIES, bounded)
    return labels[min(len(labels) - 1, index)]


def element_in_zones(key: str, score: float | None, zones: Iterable[str]) -> bool:
    """Check membership using the canonical public score → zone mapping."""

    zone = zone_for_score(key, score)
    return zone is not None and zone in set(zones)


__all__ = [
    "ELEMENT_REGISTRY",
    "ELEMENTS",
    "ELEMENT_REGISTRY_VERSION",
    "EXPECTED_ELEMENT_KEYS",
    "ZONE_BOUNDARIES",
    "element_in_zones",
    "zone_for_score",
]
