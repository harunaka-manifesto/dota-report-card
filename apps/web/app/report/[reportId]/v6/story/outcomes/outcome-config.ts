import type { V6ClaimLayers, V6Finding } from "../../types";

export const OUTCOME_PHASES = [
  "reveal",
  "interpretation",
  "evidence",
  "expanded-evidence",
] as const;

export type OutcomePhase = (typeof OUTCOME_PHASES)[number];

export const OUTCOME_VARIANT_KEYS = [
  "hidden_center",
  "names_wide_jobs_narrow",
  "names_narrow_jobs_wide",
  "names_changed_jobs_held",
  "clean_transfer",
  "results_stop_first",
  "expression_stops_first",
  "involvement_boundary",
  "exposure_boundary",
  "localized_function_bottleneck",
  "one_loss_runback",
  "two_loss_switch",
  "result_shaped_pool",
  "result_invariant_response",
  "adjustment_without_recovery",
  "involvement_holds_exposure_moves",
  "exposure_holds_involvement_moves",
  "same_expression_different_results",
  "different_expression_same_results",
  "localized_variance",
  "opening_game_signature",
  "gradual_session_drift",
  "predeclared_breakpoint",
  "selection_only_drift",
  "bounded_stopping_response",
] as const;

export type OutcomeVariantKey = (typeof OUTCOME_VARIANT_KEYS)[number];

export type OutcomePhasePresentation = {
  label: string;
  heading: string;
};

export type OutcomePresentation = {
  family: string;
  label: string;
  phases: Record<OutcomePhase, OutcomePhasePresentation>;
};

const phasePresentation = (heading: string): Record<OutcomePhase, OutcomePhasePresentation> => ({
  reveal: { label: "Signal", heading },
  interpretation: { label: "What it means", heading: "Read the signal" },
  evidence: { label: "Evidence", heading: "What was observed" },
  "expanded-evidence": { label: "Expanded evidence", heading: "Keep the alternatives in view" },
});

const presentation = (family: string, label: string, heading: string): OutcomePresentation => ({
  family,
  label,
  phases: phasePresentation(heading),
});

/** Every public V6.1 semantic outcome has one explicit presentation entry. */
export const OUTCOME_CONFIG: Record<OutcomeVariantKey, OutcomePresentation> = {
  hidden_center: presentation("Pool Shape", "Hidden center", "A wider pool still has a center."),
  names_wide_jobs_narrow: presentation("Pool Shape", "Names wide, jobs narrow", "Names move farther than the jobs behind them."),
  names_narrow_jobs_wide: presentation("Pool Shape", "Names narrow, jobs wide", "A compact hero set covers a wider mix of jobs."),
  names_changed_jobs_held: presentation("Pool Shape", "Names changed, jobs held", "Hero names moved while the jobs held."),
  clean_transfer: presentation("Transfer", "Clean transfer", "More expression travels when the hero changes."),
  results_stop_first: presentation("Transfer", "Results stop first", "The result changes before expression does."),
  expression_stops_first: presentation("Transfer", "Expression stops first", "Expression changes before the result does."),
  involvement_boundary: presentation("Transfer", "Involvement boundary", "Involvement holds farther into the hero change."),
  exposure_boundary: presentation("Transfer", "Exposure boundary", "Exposure holds farther into the hero change."),
  localized_function_bottleneck: presentation("Transfer", "Localized function bottleneck", "The supported gap sits in one mapped job."),
  one_loss_runback: presentation("Post-Loss Response", "One-loss runback", "The next choice stays closer after one loss."),
  two_loss_switch: presentation("Post-Loss Response", "Two-loss switch", "The next choice changes after repeated losses."),
  result_shaped_pool: presentation("Post-Loss Response", "Result-shaped pool", "The next choice moves differently by result."),
  result_invariant_response: presentation("Post-Loss Response", "Result-invariant response", "The next-choice movement stays compatible across results."),
  adjustment_without_recovery: presentation("Post-Loss Response", "Adjustment without recovery", "The next choice changes while the next result stays unresolved."),
  involvement_holds_exposure_moves: presentation("Combat Expression", "Involvement holds, exposure moves", "Involvement holds while exposure moves."),
  exposure_holds_involvement_moves: presentation("Combat Expression", "Exposure holds, involvement moves", "Exposure holds while involvement moves."),
  same_expression_different_results: presentation("Combat Expression", "Same expression, different results", "Similar expression can arrive with different results."),
  different_expression_same_results: presentation("Combat Expression", "Different expression, same results", "Similar results can arrive with different expression."),
  localized_variance: presentation("Combat Expression", "Localized variance", "More expression variance sits in one context."),
  opening_game_signature: presentation("Session Drift", "Opening-game signature", "Game 1 has a different supported shape."),
  gradual_session_drift: presentation("Session Drift", "Gradual session drift", "A covered signal moves as the session continues."),
  predeclared_breakpoint: presentation("Session Drift", "Predeclared breakpoint", "The first clear break appears at the registered position."),
  selection_only_drift: presentation("Session Drift", "Selection-only drift", "The pool changes while expression stays compatible."),
  bounded_stopping_response: presentation("Session Drift", "Bounded stopping response", "Session endings differ after the registered result."),
};

/**
 * Explicit backend adapter. Unknown backend identifiers intentionally abstain;
 * outcome selection must never be inferred from substrings.
 */
export const BACKEND_OUTCOME_TO_STORY_VARIANT: Record<OutcomeVariantKey, OutcomeVariantKey> = {
  hidden_center: "hidden_center",
  names_wide_jobs_narrow: "names_wide_jobs_narrow",
  names_narrow_jobs_wide: "names_narrow_jobs_wide",
  names_changed_jobs_held: "names_changed_jobs_held",
  clean_transfer: "clean_transfer",
  results_stop_first: "results_stop_first",
  expression_stops_first: "expression_stops_first",
  involvement_boundary: "involvement_boundary",
  exposure_boundary: "exposure_boundary",
  localized_function_bottleneck: "localized_function_bottleneck",
  one_loss_runback: "one_loss_runback",
  two_loss_switch: "two_loss_switch",
  result_shaped_pool: "result_shaped_pool",
  result_invariant_response: "result_invariant_response",
  adjustment_without_recovery: "adjustment_without_recovery",
  involvement_holds_exposure_moves: "involvement_holds_exposure_moves",
  exposure_holds_involvement_moves: "exposure_holds_involvement_moves",
  same_expression_different_results: "same_expression_different_results",
  different_expression_same_results: "different_expression_same_results",
  localized_variance: "localized_variance",
  opening_game_signature: "opening_game_signature",
  gradual_session_drift: "gradual_session_drift",
  predeclared_breakpoint: "predeclared_breakpoint",
  selection_only_drift: "selection_only_drift",
  bounded_stopping_response: "bounded_stopping_response",
};

export type AdaptedOutcome = {
  key: OutcomeVariantKey;
  config: OutcomePresentation;
  finding: V6Finding;
  layers: V6ClaimLayers;
  claim: string | null;
  interpretation: string | null;
  evidence: string[];
  alternatives: string[];
};

function nonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function evidenceStrings(finding: V6Finding): string[] {
  const values: unknown[] = [
    finding.evidence_text,
    typeof finding.evidence === "string" ? finding.evidence : null,
    ...(Array.isArray(finding.evidence) ? finding.evidence.flatMap((item) => [item.observation, item.label, item.key]) : []),
    ...(finding.evidence_items ?? []).flatMap((item) => [item.observation, item.label, item.key]),
    finding.claim_contract?.evidence,
    finding.layers?.evidence,
  ];
  return [...new Set(values.filter(nonEmpty).map((value) => value.trim()))];
}

function exactOutcomeKey(value: string | null | undefined): OutcomeVariantKey | null {
  if (!value || !Object.prototype.hasOwnProperty.call(BACKEND_OUTCOME_TO_STORY_VARIANT, value)) return null;
  return BACKEND_OUTCOME_TO_STORY_VARIANT[value as OutcomeVariantKey];
}

export function adaptV6Finding(finding: V6Finding): AdaptedOutcome | null {
  const key = exactOutcomeKey(finding.semantic_outcome_key) ?? exactOutcomeKey(finding.outcome_key);
  if (!key) return null;
  const layers = finding.claim_contract ?? finding.layers ?? {};
  return {
    key,
    config: OUTCOME_CONFIG[key],
    finding,
    layers,
    claim: nonEmpty(finding.claim) ? finding.claim.trim() : nonEmpty(layers.claim) ? layers.claim.trim() : null,
    interpretation: nonEmpty(finding.interpretation)
      ? finding.interpretation.trim()
      : nonEmpty(layers.interpretation) ? layers.interpretation.trim() : null,
    evidence: evidenceStrings(finding),
    alternatives: (layers.alternatives ?? []).filter(nonEmpty).map((value) => value.trim()),
  };
}
