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


_COPY = {
    "hidden_center": SemanticCopy("Your annual pool is broad around a smaller, repeatedly observed center.", "Breadth and concentration describe different parts of the same observed portfolio.", "annual hero mass and stable core"),
    "names_wide_jobs_narrow": SemanticCopy("Your hero names cover more ground than the mapped jobs behind them.", "Different heroes repeatedly supply a more concentrated functional mix.", "hero diversity versus fractional job mass"),
    "names_narrow_jobs_wide": SemanticCopy("A more compact hero set covers a wider mapped job mixture.", "The observed pool gets functional coverage without requiring the same amount of name diversity.", "hero diversity versus fractional job mass"),
    "names_changed_jobs_held": SemanticCopy("Your hero distribution changed across the year while the mapped job mixture stayed closer.", "The names moved more than the taxonomy-described functions; patch and draft context remain unresolved.", "chronological hero and job distribution distance"),
    "clean_transfer": SemanticCopy("Outcome and summary expression remain compatible through the supported distance frontier.", "The result is bounded to covered distance bands and does not identify why transfer held.", "cross-fitted distance-band components"),
    "results_stop_first": SemanticCopy("Observed results stop matching core sooner than summary expression does.", "Similar activity and exposure can coexist with a different result distribution.", "outcome versus expression frontiers"),
    "expression_stops_first": SemanticCopy("Summary expression changes before the observed result distribution does.", "Compatible results do not mean the underlying summary rates were the same.", "outcome versus expression frontiers"),
    "involvement_boundary": SemanticCopy("Adjusted involvement marks the nearest supported transfer boundary.", "The boundary is limited to covered scoreboard-event activity.", "cross-fitted involvement frontier"),
    "exposure_boundary": SemanticCopy("Adjusted death exposure marks the nearest supported transfer boundary.", "The boundary does not identify what happened inside individual games.", "cross-fitted exposure frontier"),
    "localized_function_bottleneck": SemanticCopy("The supported transfer gap is localized to one mapped function context.", "The taxonomy localization is descriptive and remains sensitive to mapping coverage.", "function-localized distance frontier"),
    "one_loss_runback": SemanticCopy("After exactly one loss, your next observed selection tends to stay closer to the prior choice or core.", "This is a same-session transition pattern, not evidence of motive or recovery.", "exactly-one-loss transitions"),
    "two_loss_switch": SemanticCopy("Your observed selection response after two or more losses differs from the one-loss state.", "The streak threshold describes choices in supported same-session opportunities, without explaining why they changed.", "one-loss versus two-plus-loss transitions"),
    "result_shaped_pool": SemanticCopy("Wins and losses precede different supported movements through your observed pool.", "Result state is associated with the next selection, without establishing why.", "bidirectional result-state transitions"),
    "result_invariant_response": SemanticCopy("Your next-selection movement is practically compatible across the supported result states.", "The complete interval, not a nonsignificant p-value, supports the bounded equivalence claim.", "result-state equivalence"),
    "adjustment_without_recovery": SemanticCopy("Selection or summary expression changes after the result state while the next-result evidence stays compatible.", "The adjustment is observable; whether it helped is unresolved.", "selection, expression, and next-result chain"),
    "involvement_holds_exposure_moves": SemanticCopy("Adjusted involvement stays compatible while death exposure moves in the qualified comparison.", "One expression component is stable and the other is context-dependent.", "conditional involvement and exposure"),
    "exposure_holds_involvement_moves": SemanticCopy("Adjusted death exposure stays compatible while involvement moves in the qualified comparison.", "The contrast is limited to covered summary rates.", "conditional involvement and exposure"),
    "same_expression_different_results": SemanticCopy("Supported summary-expression components are compatible across contexts with different result distributions.", "Unobserved draft, objective, and inside-game context remain plausible alternatives.", "expression equivalence and result difference"),
    "different_expression_same_results": SemanticCopy("The observed result distribution stays compatible while summary expression differs.", "Similar results can arrive with different covered scoreboard-rate profiles.", "result equivalence and expression difference"),
    "localized_variance": SemanticCopy("A supported hero, function, or distance context contains more of the observed expression variance.", "Localization is not blame and does not establish a cause.", "conditional variance decomposition"),
    "opening_game_signature": SemanticCopy("Game 1 has a supported summary signature relative to later direct positions.", "The comparison uses completed sessions and direct position opportunities.", "G1 versus later session positions"),
    "gradual_session_drift": SemanticCopy("A covered summary component moves gradually across supported session positions.", "Selection into longer sessions remains an unresolved alternative.", "G1 through G5-plus position curve"),
    "predeclared_breakpoint": SemanticCopy("A predeclared session position is the first supported break in the observed curve.", "The breakpoint was frozen before evaluation and does not explain the change.", "frozen G2, G3, or G4 comparison"),
    "selection_only_drift": SemanticCopy("Pool selection moves across supported session positions while summary expression stays compatible.", "The observed choice movement remains descriptive and does not explain why it occurred.", "selection curve and expression equivalence"),
    "bounded_stopping_response": SemanticCopy("Completed, boundary-safe session endings differ after the registered result state.", "The 365-day boundary and session-gap sensitivity limit the claim; intended stopping is unknown.", "censor-aware session endings"),
    "hero_lifecycle": SemanticCopy("A hero lifecycle candidate is available only for protected shadow evaluation.", "First observed in the window is not the same as discovered.", "left-truncation-aware lifecycle"),
    "identity_eras": SemanticCopy("An identity-era candidate is available only for protected shadow evaluation.", "A stable year with no qualifying chapter is a valid result.", "session-block era candidate"),
    "behavioral_loop": SemanticCopy("A sequence candidate is available only for protected shadow evaluation.", "No loop is public without discovery and independent verification support.", "non-overlapping motif occurrences"),
}

SEMANTIC_COPY_REGISTRY = MappingProxyType(_COPY)

if set(SEMANTIC_COPY_REGISTRY) != set(SEMANTIC_OUTCOME_REGISTRY):
    missing = sorted(set(SEMANTIC_OUTCOME_REGISTRY) - set(SEMANTIC_COPY_REGISTRY))
    extra = sorted(set(SEMANTIC_COPY_REGISTRY) - set(SEMANTIC_OUTCOME_REGISTRY))
    raise ValueError(f"V6.1 semantic copy registry drift; missing={missing}, extra={extra}")

__all__ = ["SEMANTIC_COPY_REGISTRY", "SemanticCopy"]
