import type { PatternVisualProps } from "./visual-types";
import { numberValue, recordArray, stringValue } from "./visual-types";

export function PresenceExposureMap({ proof }: PatternVisualProps) {
  const contexts = recordArray(proof.contexts);
  return (
    <div className="pattern-visual pattern-visual-presence" aria-label="Presence and death exposure map">
      <div className="presence-axis-y"><span>MORE DEATH EXPOSURE ↑</span></div>
      <div className="presence-map"><div className="presence-grid-lines" />{contexts.map((context) => <div className="presence-dot" key={stringValue(context.label)} style={{ left: `${Math.max(4, Math.min(96, numberValue(context.involvement_level) * 100))}%`, bottom: `${Math.max(4, Math.min(96, numberValue(context.death_exposure_level) * 100))}%` }} title={stringValue(context.label)}><span>{stringValue(context.label)}</span></div>)}<span className="presence-axis-x">MORE INVOLVED →</span></div>
      {contexts.length === 0 && <p className="muted">No subgroup cleared the map’s display gate; the overall relationship remains visible.</p>}
    </div>
  );
}
