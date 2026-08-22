import type { PatternVisualProps } from "./visual-types";
import { numberValue, recordArray, stringValue } from "./visual-types";

export function SessionCurve({ proof }: PatternVisualProps) {
  const points = recordArray(proof.curve);
  return (
    <div className="pattern-visual pattern-visual-session" aria-label="Session curve">
      <div className="session-curve-grid">{points.map((point) => { const delta = numberValue(point.relative_delta); return <div className="session-point" key={stringValue(point.bucket)}><div className={`session-bar ${delta < 0 ? "is-negative" : "is-positive"}`} style={{ height: `${Math.max(12, Math.min(100, Math.abs(delta) * 220 + 16))}%` }} /><strong>{stringValue(point.bucket_label, stringValue(point.bucket))}</strong><span>{stringValue(point.display_label)}</span></div>; })}</div>
      <div className="session-breakpoint"><span className="eyebrow">FIRST SUPPORTED POINT</span><strong>{stringValue(proof.breakpoint_label, "No single breakpoint")}</strong><small>{stringValue(proof.breakpoint_state).replaceAll("_", " ")}</small></div>
    </div>
  );
}
