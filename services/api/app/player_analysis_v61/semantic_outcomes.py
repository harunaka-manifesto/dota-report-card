"""Frozen V6.1 semantic-outcome tree and public entitlement contracts."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

from app.player_analysis_v6.constants import FINDING_FAMILY_KEYS

from .versions import SEMANTIC_OUTCOMES_VERSION

RolloutStatus = Literal["public_candidate", "shadow_only", "rejected"]


@dataclass(frozen=True, slots=True)
class SemanticOutcomeDefinition:
    family_key: str
    hypothesis_branch: str
    semantic_outcome_key: str
    evidence_groups: tuple[str, ...]
    opportunity_denominator: str
    minimum_opportunities: int
    minimum_sessions: int
    effect_or_equivalence_contract: str
    robustness_checks: tuple[str, ...]
    claim_tokens: tuple[str, ...]
    forbidden_tokens: tuple[str, ...]
    alternatives: tuple[str, ...]
    recommendation_key: str | None
    verification_metric_keys: tuple[str, ...]
    interaction_key: str | None
    share_key: str | None
    rollout_status: RolloutStatus
    version: str = SEMANTIC_OUTCOMES_VERSION

    def __post_init__(self) -> None:
        if self.family_key not in FINDING_FAMILY_KEYS:
            raise ValueError(f"unknown semantic outcome family: {self.family_key}")
        if len(self.evidence_groups) < 2 and self.rollout_status == "public_candidate":
            raise ValueError(f"{self.semantic_outcome_key} needs two evidence groups")
        if not self.opportunity_denominator or self.minimum_opportunities < 1:
            raise ValueError(f"{self.semantic_outcome_key} needs an opportunity contract")
        if not self.claim_tokens or not self.alternatives:
            raise ValueError(f"{self.semantic_outcome_key} needs copy and alternatives")
        if self.recommendation_key and not self.verification_metric_keys:
            raise ValueError(f"{self.semantic_outcome_key} recommendation needs verification")


_FORBIDDEN = (
    "aggression",
    "intent",
    "tilt",
    "fatigue",
    "positioning",
    "skill",
    "causes",
    "rank",
    "mmr",
    "personality",
    "death quality",
    "warm-up",
)
_ROBUST = ("chronological_halves", "dominant_hero", "session_boundary", "taxonomy")


def _outcome(
    family: str,
    key: str,
    *,
    branch: str,
    interaction: str | None,
    rollout: RolloutStatus = "public_candidate",
    denominator: str = "matches",
    opportunities: int = 30,
    sessions: int = 12,
    recommendation: str | None = None,
) -> SemanticOutcomeDefinition:
    return SemanticOutcomeDefinition(
        family_key=family,
        hypothesis_branch=branch,
        semantic_outcome_key=key,
        evidence_groups=("selection", "expression"),
        opportunity_denominator=denominator,
        minimum_opportunities=opportunities,
        minimum_sessions=sessions,
        effect_or_equivalence_contract="interval-inside-rope-or-practical-effect-1.0.0",
        robustness_checks=_ROBUST,
        claim_tokens=(key.replace("_", " "),),
        forbidden_tokens=_FORBIDDEN,
        alternatives=("unobserved draft and match context", "taxonomy or coverage uncertainty"),
        recommendation_key=recommendation,
        verification_metric_keys=(("primary", "guardrail") if recommendation else ()),
        interaction_key=interaction,
        share_key=(f"share:{key}" if rollout == "public_candidate" else None),
        rollout_status=rollout,
    )


SEMANTIC_OUTCOME_CATALOG = (
    _outcome("pool_shape", "hidden_center", branch="shape", interaction="contradiction_reveal"),
    _outcome("pool_shape", "names_wide_jobs_narrow", branch="name_job", interaction="contradiction_reveal"),
    _outcome("pool_shape", "names_narrow_jobs_wide", branch="name_job", interaction="contradiction_reveal"),
    _outcome("pool_shape", "names_changed_jobs_held", branch="migration", interaction="contradiction_reveal"),
    _outcome("transfer", "clean_transfer", branch="frontier", interaction="core_boundary", recommendation="verify_transfer"),
    _outcome("transfer", "no_transfer", branch="frontier", interaction="core_boundary"),
    _outcome("transfer", "results_stop_first", branch="component_frontier", interaction="two_versions"),
    _outcome("transfer", "expression_stops_first", branch="component_frontier", interaction="two_versions"),
    _outcome("transfer", "involvement_boundary", branch="component_frontier", interaction="core_boundary"),
    _outcome("transfer", "exposure_boundary", branch="component_frontier", interaction="core_boundary"),
    _outcome("transfer", "localized_function_bottleneck", branch="function", interaction="core_boundary"),
    _outcome("post_loss_response", "one_loss_runback", branch="result_state", interaction="after_x", denominator="transitions"),
    _outcome("post_loss_response", "two_loss_switch", branch="streak_state", interaction="after_x", denominator="transitions"),
    _outcome("post_loss_response", "result_shaped_pool", branch="bidirectional", interaction="after_x", denominator="transitions"),
    _outcome("post_loss_response", "result_invariant_response", branch="equivalence", interaction="after_x", denominator="transitions"),
    _outcome("post_loss_response", "adjustment_without_recovery", branch="chain", interaction="after_x", denominator="transitions"),
    _outcome("combat_expression", "involvement_holds_exposure_moves", branch="conditional_expression", interaction="two_versions"),
    _outcome("combat_expression", "exposure_holds_involvement_moves", branch="conditional_expression", interaction="two_versions"),
    _outcome("combat_expression", "same_expression_different_results", branch="result_expression", interaction="two_versions"),
    _outcome("combat_expression", "different_expression_same_results", branch="result_expression", interaction="two_versions"),
    _outcome("combat_expression", "localized_variance", branch="variance", interaction="variance_decomposition"),
    _outcome("session_drift", "opening_game_signature", branch="position_curve", interaction="session_curve", denominator="sessions"),
    _outcome("session_drift", "gradual_session_drift", branch="position_curve", interaction="session_curve", denominator="sessions"),
    _outcome("session_drift", "predeclared_breakpoint", branch="breakpoint", interaction="session_curve", denominator="sessions"),
    _outcome("session_drift", "selection_only_drift", branch="selection", interaction="session_curve", denominator="sessions"),
    _outcome("session_drift", "bounded_stopping_response", branch="stopping", interaction="session_curve", denominator="sessions"),
    _outcome("pool_shape", "hero_lifecycle", branch="lifecycle", interaction="hero_lifecycle", rollout="shadow_only"),
    _outcome("pool_shape", "identity_eras", branch="eras", interaction="identity_eras", rollout="shadow_only"),
    _outcome("session_drift", "behavioral_loop", branch="motif", interaction="behavioral_loop", rollout="shadow_only", denominator="occurrences"),
)

SEMANTIC_OUTCOME_REGISTRY = MappingProxyType(
    {definition.semantic_outcome_key: definition for definition in SEMANTIC_OUTCOME_CATALOG}
)


def validate_semantic_outcomes(
    definitions: Iterable[SemanticOutcomeDefinition] = SEMANTIC_OUTCOME_CATALOG,
) -> tuple[SemanticOutcomeDefinition, ...]:
    ordered = tuple(definitions)
    keys = [definition.semantic_outcome_key for definition in ordered]
    if len(keys) != len(set(keys)):
        raise ValueError("semantic outcome keys must be unique")
    if {definition.family_key for definition in ordered} != set(FINDING_FAMILY_KEYS):
        raise ValueError("semantic outcome tree must have exactly five family roots")
    return ordered


validate_semantic_outcomes()

__all__ = [
    "SEMANTIC_OUTCOME_CATALOG",
    "SEMANTIC_OUTCOME_REGISTRY",
    "SemanticOutcomeDefinition",
    "validate_semantic_outcomes",
]
