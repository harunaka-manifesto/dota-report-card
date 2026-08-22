import type { PatternVisualProps } from "./visual-types";
import { stringValue } from "./visual-types";

export function TransferSplit({ proof }: PatternVisualProps) {
  return (
    <div className="pattern-visual pattern-visual-transfer" aria-label="Familiar and off-pool transfer comparison">
      <div className="transfer-rail"><div className="transfer-half"><span className="eyebrow">FAMILIAR POOL</span><strong>{stringValue(proof.familiar_presence)}</strong><small>fight presence</small></div><div className="transfer-split-mark">→</div><div className="transfer-half"><span className="eyebrow">OFF-POOL</span><strong>{stringValue(proof.off_pool_presence)}</strong><small>fight presence</small></div></div>
      <div className="transfer-result"><span className="eyebrow">RESULT DIRECTION</span><strong>{stringValue(proof.result_direction)}</strong><small>Presence and result are shown separately.</small></div>
      {typeof proof.strongest_demand === "string" && <p className="visual-callout"><span className="eyebrow">STRONGEST DEMAND DIFFERENCE</span><strong>{proof.strongest_demand}</strong></p>}
    </div>
  );
}
