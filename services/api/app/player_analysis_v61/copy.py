"""Deterministic safe copy for the frozen V6.1 semantic outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from app.player_analysis_v61.semantic_outcomes import SEMANTIC_OUTCOME_REGISTRY


@dataclass(frozen=True, slots=True)
class SemanticCopy:
    claim: str
    interpretation: str
    evidence_label: str
    neutral_variant: str | None = None
    insufficient_variant: str | None = None
    mixed_variant: str | None = None


_POOL_VARIANTS = (
    "No single pool shape separated cleanly.",
    "Not enough stable pool history to call the shape.",
    "Your pool has two valid layers: the names move, while the jobs hold.",
)
_TRANSFER_VARIANTS = (
    "The supported comparison does not separate familiar and stretch contexts.",
    "Not enough comparable familiar and stretch matches to call transfer.",
    "Your answer changes by signal.",
)
_POST_LOSS_VARIANTS = (
    "No single result state separated your next-choice movement.",
    "Not enough same-session transitions to call a post-loss pattern.",
    "The one-loss and two-plus-loss states do not tell the same story.",
)
_COMBAT_VARIANTS = (
    "The covered match signals stay within the supported range.",
    "Not enough context-resolved matches to call this one.",
    "One signal holds while another moves.",
)
_SESSION_VARIANTS = (
    "Your covered expression stays compatible across completed session positions.",
    "Not enough completed sessions to call a session pattern.",
    "The session story changes by what you measure.",
)


def _matrix_copy(
    claim: str,
    evidence_label: str,
    limitation: str,
    variants: tuple[str, str, str],
) -> SemanticCopy:
    return SemanticCopy(claim, limitation, evidence_label, *variants)


_COPY = {
    "hidden_center": _matrix_copy(
        "Your pool is wider than it first looks—but it has a center.",
        "Annual hero mass and stable core.",
        "Taxonomy and coverage uncertainty remain alternatives.",
        _POOL_VARIANTS,
    ),
    "names_wide_jobs_narrow": _matrix_copy(
        "Your hero names cover more ground than the jobs behind them.",
        "Hero diversity versus fractional job mass.",
        "Functional jobs depend on taxonomy coverage.",
        _POOL_VARIANTS,
    ),
    "names_narrow_jobs_wide": _matrix_copy(
        "A compact hero set covers a wider mix of jobs.",
        "Hero diversity versus fractional job mass.",
        "Taxonomy is descriptive, not actual role truth.",
        _POOL_VARIANTS,
    ),
    "names_changed_jobs_held": _matrix_copy(
        "Your hero names moved more across the year than the jobs they covered.",
        "Chronological hero and job distribution distance.",
        "Taxonomy and unobserved context remain unresolved.",
        _POOL_VARIANTS,
    ),
    "clean_transfer": _matrix_copy(
        "More of your observed expression travels when the hero changes.",
        "Outcome/activity/survival components across distance bands.",
        "Covered distance bands only; no why.",
        _TRANSFER_VARIANTS,
    ),
    "results_stop_first": _matrix_copy(
        "The result changes before your expression does.",
        "Outcome versus expression frontiers.",
        "Similar activity/exposure can coexist with a different result distribution.",
        _TRANSFER_VARIANTS,
    ),
    "expression_stops_first": _matrix_copy(
        "Your expression changes before the result does.",
        "Outcome versus expression frontiers.",
        "Compatible results do not mean equal rates.",
        _TRANSFER_VARIANTS,
    ),
    "involvement_boundary": _matrix_copy(
        "Involvement holds farther into the hero change.",
        "Cross-fitted involvement frontier.",
        "Covered scoreboard-event activity only.",
        _TRANSFER_VARIANTS,
    ),
    "exposure_boundary": _matrix_copy(
        "Death exposure holds farther into the hero change.",
        "Cross-fitted exposure frontier.",
        "Does not identify what happened inside a game.",
        _TRANSFER_VARIANTS,
    ),
    "localized_function_bottleneck": _matrix_copy(
        "The supported gap sits in one mapped job context.",
        "Function-localized distance frontier.",
        "Localization depends on taxonomy coverage.",
        _TRANSFER_VARIANTS,
    ),
    "one_loss_runback": _matrix_copy(
        "After one loss, your next choice stays closer to your prior path.",
        "Exactly-one-loss transitions.",
        "Same-session transition association only.",
        _POST_LOSS_VARIANTS,
    ),
    "two_loss_switch": _matrix_copy(
        "After two or more losses, your next choice changes differently.",
        "One-loss versus two-plus-loss transitions.",
        "Streak threshold describes opportunities, not motive.",
        _POST_LOSS_VARIANTS,
    ),
    "result_shaped_pool": _matrix_copy(
        "Your next choice moves differently after wins and losses.",
        "Bidirectional result-state transitions.",
        "Next selection is observed; reason remains unknown.",
        _POST_LOSS_VARIANTS,
    ),
    "result_invariant_response": _matrix_copy(
        "Your next-choice movement stays about the same after wins and losses.",
        "Result-state equivalence.",
        "Complete interval supports bounded equivalence.",
        _POST_LOSS_VARIANTS,
    ),
    "adjustment_without_recovery": _matrix_copy(
        "Your next choice changes after the result, while the next result stays unresolved.",
        "Selection, expression, and next-result chain.",
        "“Whether it helped is unresolved” remains Depth 2 copy.",
        _POST_LOSS_VARIANTS,
    ),
    "involvement_holds_exposure_moves": _matrix_copy(
        "Involvement holds while death exposure moves.",
        "Conditional involvement and exposure.",
        "Covered summary rates only.",
        _COMBAT_VARIANTS,
    ),
    "exposure_holds_involvement_moves": _matrix_copy(
        "Death exposure holds while involvement moves.",
        "Conditional involvement and exposure.",
        "Context-adjusted summary rates only.",
        _COMBAT_VARIANTS,
    ),
    "same_expression_different_results": _matrix_copy(
        "Similar summary expression can arrive with different results.",
        "Expression equivalence and result difference.",
        "Draft, objective, and inside-game context remain alternatives.",
        _COMBAT_VARIANTS,
    ),
    "different_expression_same_results": _matrix_copy(
        "Similar results can arrive with different summary expression.",
        "Result equivalence and expression difference.",
        "Similar result distribution does not mean same game.",
        _COMBAT_VARIANTS,
    ),
    "localized_variance": _matrix_copy(
        "More of the expression variance sits in one supported context.",
        "Conditional variance decomposition.",
        "Localization is descriptive.",
        _COMBAT_VARIANTS,
    ),
    "opening_game_signature": _matrix_copy(
        "Game 1 has a different supported shape from later games.",
        "G1 versus later session positions.",
        "Direct positions and completed sessions only.",
        _SESSION_VARIANTS,
    ),
    "gradual_session_drift": _matrix_copy(
        "A covered part of your expression moves as the session continues.",
        "G1 through G5-plus position curve.",
        "Selection into longer sessions remains unresolved.",
        _SESSION_VARIANTS,
    ),
    "predeclared_breakpoint": _matrix_copy(
        "The first clear break appears at the registered session position.",
        "Frozen G2, G3, or G4 comparison.",
        "Breakpoint was frozen before evaluation.",
        _SESSION_VARIANTS,
    ),
    "selection_only_drift": _matrix_copy(
        "Your pool changes across a session while summary expression stays compatible.",
        "Selection curve and expression equivalence.",
        "Choice movement is descriptive.",
        _SESSION_VARIANTS,
    ),
    "bounded_stopping_response": _matrix_copy(
        "Completed session endings differ after the registered result state.",
        "Censor-aware session endings.",
        "365-day boundary and session-gap sensitivity limit the claim.",
        _SESSION_VARIANTS,
    ),
    "hero_lifecycle": SemanticCopy(
        "A hero lifecycle candidate is available only for protected shadow evaluation.",
        "First observed in the window is not the same as discovered.",
        "left-truncation-aware lifecycle",
    ),
    "identity_eras": SemanticCopy(
        "An identity-era candidate is available only for protected shadow evaluation.",
        "A stable year with no qualifying chapter is a valid result.",
        "session-block era candidate",
    ),
    "behavioral_loop": SemanticCopy(
        "A sequence candidate is available only for protected shadow evaluation.",
        "No loop is public without discovery and independent verification support.",
        "non-overlapping motif occurrences",
    ),
}

SEMANTIC_COPY_REGISTRY = MappingProxyType(_COPY)

if len(SEMANTIC_COPY_REGISTRY) != len(SEMANTIC_OUTCOME_REGISTRY) or set(
    SEMANTIC_COPY_REGISTRY
) != set(SEMANTIC_OUTCOME_REGISTRY):
    missing = sorted(set(SEMANTIC_OUTCOME_REGISTRY) - set(SEMANTIC_COPY_REGISTRY))
    extra = sorted(set(SEMANTIC_COPY_REGISTRY) - set(SEMANTIC_OUTCOME_REGISTRY))
    raise ValueError(
        "V6.1 semantic copy registry drift; "
        f"copy_count={len(SEMANTIC_COPY_REGISTRY)}, "
        f"outcome_count={len(SEMANTIC_OUTCOME_REGISTRY)}, "
        f"missing={missing}, extra={extra}"
    )

for key, definition in SEMANTIC_OUTCOME_REGISTRY.items():
    copy = SEMANTIC_COPY_REGISTRY[key]
    if definition.rollout_status == "public_candidate" and any(
        variant is None
        for variant in (copy.neutral_variant, copy.insufficient_variant, copy.mixed_variant)
    ):
        raise ValueError(f"V6.1 public copy state variants missing for {key}")

__all__ = ["SEMANTIC_COPY_REGISTRY", "SemanticCopy"]
