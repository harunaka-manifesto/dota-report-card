import type { PatternVisualProps } from "./visual-types";
import { stringArray, stringValue } from "./visual-types";

export function PostLossTransition({ proof }: PatternVisualProps) {
  const jobs = stringArray(proof.primary_jobs);
  return (
    <div className="pattern-visual pattern-visual-transition" aria-label="Post-loss transition">
      <div className="transition-arrow"><span>LOSS</span><strong>→</strong><span>NEXT GAME</span></div>
      <div className={`transition-result ${String(proof.transition_label).includes("WEAKER") ? "is-weaker" : "is-stronger"}`}>{stringValue(proof.transition_label)}</div>
      <div className="transition-context"><span className="eyebrow">STRONGEST SUPPORTED CONTEXT</span><strong>{stringValue(proof.context_label)}</strong>{typeof proof.function_family === "string" && <small>{proof.function_family}</small>}{jobs.length > 0 && <small>{jobs.join(" · ")}</small>}</div>
    </div>
  );
}
