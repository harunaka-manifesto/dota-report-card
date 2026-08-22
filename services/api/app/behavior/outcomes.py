"""Finite semantic outcome and recommendation states for v5.2.

The existing presentation IDs remain as a compatibility shell for the seeded
copy catalog.  These IDs are the frozen meaning layer handed to the next
deterministic content project; they do not generate prose at runtime.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SEMANTIC_OUTCOME_VERSION = "pattern-outcomes-5.2.0"

SEMANTIC_OUTCOME_BRANCHES: dict[str, tuple[str, ...]] = {
    "same_playbook": ("P01_NARROW_JOB_BRIDGE_FOUND", "P01_NARROW_JOB_NO_BRIDGE"),
    "comfort_edge": (
        "P02_CLEAR_RELIABILITY_LADDER",
        "P02_GRADUAL_RELIABILITY_LADDER",
        "P02_DEVELOPMENT_DEMAND_UNRESOLVED",
    ),
    "partial_transfer": (
        "P03_DEMAND_HYPOTHESIS",
        "P03_DIRECT_DIFFERENCE_ONLY",
        "P03_EXPLANATION_UNRESOLVED",
    ),
    "versatile_core": (
        "P04_GAP_WITH_BRIDGE",
        "P04_GAP_NO_BRIDGE",
        "P04_NO_MEANINGFUL_GAP",
    ),
    "proven_flexibility": ("P05_CONCENTRATED_FLEX_WINDOW", "P05_DISTRIBUTED_FLEXIBILITY"),
    "bounceback": ("P06_HERO_CONTEXT", "P06_FUNCTION_CONTEXT", "P06_OVERALL_CONTEXT"),
    "performance_slide": ("P07_HERO_CONTEXT", "P07_FUNCTION_CONTEXT", "P07_OVERALL_CONTEXT"),
    "controlled_presence": ("P08_HERO_CONTEXT", "P08_FUNCTION_CONTEXT", "P08_OVERALL_CONTEXT"),
    "presence_tax": (
        "P09_JOB_SHAPED",
        "P09_HERO_SPECIFIC",
        "P09_CROSS_CONTEXT",
        "P09_SOURCE_UNRESOLVED",
    ),
    "session_fade": ("P10_STABLE_BREAKPOINT", "P10_GRADUAL_FADE", "P10_BREAKPOINT_UNRESOLVED"),
    "session_rise": ("P11_STABLE_BREAKPOINT", "P11_GRADUAL_RISE", "P11_BREAKPOINT_UNRESOLVED"),
}

SEMANTIC_OUTCOME_IDS = frozenset(
    outcome_id for outcomes in SEMANTIC_OUTCOME_BRANCHES.values() for outcome_id in outcomes
)

SEMANTIC_RECOMMENDATION_BRANCHES: dict[str, tuple[str, ...]] = {
    "same_playbook": ("HR_DOUBLE_DOWN", "HR_ADJACENT_MOVE_ADD_FUNCTION", "HR_PRACTICE_FALLBACK"),
    "comfort_edge": ("HR_CHANGE_ANGLE", "HR_PRACTICE_FALLBACK"),
    "partial_transfer": ("HR_PRACTICE_TRANSFER_DEMAND", "HR_PRACTICE_FALLBACK"),
    "versatile_core": ("HR_FILL_GAP_ADD_FUNCTION", "HR_PRACTICE_FALLBACK"),
    "proven_flexibility": ("HR_PROTECT_RELIABLE_ANCHOR",),
    "bounceback": ("HR_REPEAT_POST_LOSS_ANCHOR",),
    "performance_slide": ("HR_CHANGE_ONE_TRANSITION",),
    "controlled_presence": ("HR_PRESERVE_LOW_COST_PRESENCE",),
    "presence_tax": ("HR_INVESTIGATE_PRESENCE_COST",),
    "session_fade": ("HR_CHECKPOINT_AT_BREAKPOINT",),
    "session_rise": ("HR_FRONTLOAD_FAMILIARITY",),
}
SEMANTIC_RECOMMENDATION_IDS = frozenset(
    recommendation_id
    for recommendations in SEMANTIC_RECOMMENDATION_BRANCHES.values()
    for recommendation_id in recommendations
)


def classify_pattern_outcome(pattern_key: str, action: Mapping[str, Any] | None = None) -> str:
    """Classify a Pattern into one registered semantic branch."""

    action = action or {}
    if pattern_key == "same_playbook":
        return (
            "P01_NARROW_JOB_BRIDGE_FOUND"
            if _has_semantic_candidate(action.get("stretch"))
            else "P01_NARROW_JOB_NO_BRIDGE"
        )
    if pattern_key == "comfort_edge":
        ranked = action.get("ranked_heroes") or []
        if action.get("status") == "available" and len(ranked) >= 4:
            return "P02_CLEAR_RELIABILITY_LADDER"
        if ranked:
            return "P02_GRADUAL_RELIABILITY_LADDER"
        return "P02_DEVELOPMENT_DEMAND_UNRESOLVED"
    if pattern_key == "partial_transfer":
        status = action.get("status")
        if status == "capability_hypothesis":
            return "P03_DEMAND_HYPOTHESIS"
        if status == "direct_signal":
            return "P03_DIRECT_DIFFERENCE_ONLY"
        return "P03_EXPLANATION_UNRESOLVED"
    if pattern_key == "versatile_core":
        if action.get("recommended_addition"):
            return "P04_GAP_WITH_BRIDGE"
        coverage = action.get("coverage_summary") or {}
        if coverage.get("missing") or coverage.get("thin_coverage"):
            return "P04_GAP_NO_BRIDGE"
        return "P04_NO_MEANINGFUL_GAP"
    if pattern_key == "proven_flexibility":
        return (
            "P05_CONCENTRATED_FLEX_WINDOW"
            if action.get("status") == "peak_window"
            else "P05_DISTRIBUTED_FLEXIBILITY"
        )
    if pattern_key in {"bounceback", "performance_slide", "controlled_presence"}:
        prefix = {"bounceback": "P06", "performance_slide": "P07", "controlled_presence": "P08"}[
            pattern_key
        ]
        context = action.get("strongest_context")
        if context is None and pattern_key == "controlled_presence":
            context = action.get("strongest_context")
        if isinstance(context, Mapping) and context.get("hero_id") is not None:
            return f"{prefix}_HERO_CONTEXT"
        if isinstance(context, Mapping) and context.get("function_family") is not None:
            return f"{prefix}_FUNCTION_CONTEXT"
        return f"{prefix}_OVERALL_CONTEXT"
    if pattern_key == "presence_tax":
        shape = action.get("shape")
        return {
            "job_shaped": "P09_JOB_SHAPED",
            "hero_specific": "P09_HERO_SPECIFIC",
            "cross_context": "P09_CROSS_CONTEXT",
        }.get(str(shape) if shape is not None else "", "P09_SOURCE_UNRESOLVED")
    if pattern_key in {"session_fade", "session_rise"}:
        state = action.get("breakpoint_state")
        if state == "stable_breakpoint":
            return (
                "P10_STABLE_BREAKPOINT"
                if pattern_key == "session_fade"
                else "P11_STABLE_BREAKPOINT"
            )
        if state == "gradual":
            return "P10_GRADUAL_FADE" if pattern_key == "session_fade" else "P11_GRADUAL_RISE"
        return (
            "P10_BREAKPOINT_UNRESOLVED"
            if pattern_key == "session_fade"
            else "P11_BREAKPOINT_UNRESOLVED"
        )
    raise ValueError(f"Unknown semantic outcome Pattern: {pattern_key}")


def classify_recommendation_state(
    pattern_key: str,
    action: Mapping[str, Any] | None = None,
) -> str:
    action = action or {}
    if pattern_key == "same_playbook":
        candidates = [*(action.get("stretch") or []), *(action.get("deepen") or [])]
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                continue
            rationale = candidate.get("semantic_rationale")
            if not isinstance(rationale, Mapping) or rationale.get("eligible") is False:
                continue
            return (
                "HR_DOUBLE_DOWN"
                if rationale.get("intent") == "double_down"
                else "HR_ADJACENT_MOVE_ADD_FUNCTION"
            )
        return "HR_PRACTICE_FALLBACK"
    if pattern_key == "versatile_core":
        addition = action.get("recommended_addition")
        rationale = addition.get("semantic_rationale") if isinstance(addition, Mapping) else None
        if isinstance(rationale, Mapping) and rationale.get("eligible") is not False:
            return "HR_FILL_GAP_ADD_FUNCTION"
        return "HR_PRACTICE_FALLBACK"
    if pattern_key == "partial_transfer":
        return (
            "HR_PRACTICE_TRANSFER_DEMAND"
            if action.get("status") in {"direct_signal", "capability_hypothesis", "deep_candidate"}
            else "HR_PRACTICE_FALLBACK"
        )
    if pattern_key == "comfort_edge" and not action.get("development"):
        return "HR_PRACTICE_FALLBACK"
    return {
        "comfort_edge": "HR_CHANGE_ANGLE",
        "proven_flexibility": "HR_PROTECT_RELIABLE_ANCHOR",
        "bounceback": "HR_REPEAT_POST_LOSS_ANCHOR",
        "performance_slide": "HR_CHANGE_ONE_TRANSITION",
        "controlled_presence": "HR_PRESERVE_LOW_COST_PRESENCE",
        "presence_tax": "HR_INVESTIGATE_PRESENCE_COST",
        "session_fade": "HR_CHECKPOINT_AT_BREAKPOINT",
        "session_rise": "HR_FRONTLOAD_FAMILIARITY",
    }[pattern_key]


def _has_semantic_candidate(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    candidate = value[0]
    if not isinstance(candidate, Mapping):
        return False
    rationale = candidate.get("semantic_rationale")
    return isinstance(rationale, Mapping) and rationale.get("eligible") is not False


__all__ = [
    "SEMANTIC_OUTCOME_VERSION",
    "SEMANTIC_OUTCOME_BRANCHES",
    "SEMANTIC_OUTCOME_IDS",
    "SEMANTIC_RECOMMENDATION_BRANCHES",
    "SEMANTIC_RECOMMENDATION_IDS",
    "classify_pattern_outcome",
    "classify_recommendation_state",
]
