import type { PatternVisualProps } from "./visual-types";
import { recordArray, stringArray, stringValue } from "./visual-types";

export function ToolkitOrbit({ proof }: PatternVisualProps) {
  const heroes = recordArray(proof.hero_job_maps);
  const coverage = (proof.coverage && typeof proof.coverage === "object" ? proof.coverage : {}) as Record<string, unknown>;
  const groups = [["STRONGLY COVERED", stringArray(coverage.strongly_covered)], ["THIN", stringArray(coverage.thin)], ["MISSING", stringArray(coverage.missing)]] as const;
  return (
    <div className="pattern-visual pattern-visual-toolkit" aria-label="Toolkit coverage orbit">
      <div className="toolkit-orbit-center"><span className="eyebrow">ESTABLISHED CORE</span><strong>{heroes.length || "—"} heroes</strong></div>
      <div className="toolkit-hero-ring">{heroes.map((hero) => <div className="toolkit-hero" key={stringValue(hero.hero_id)}><strong>{stringValue(hero.hero_name)}</strong><small>{stringArray(hero.primary_jobs).slice(0, 2).join(" · ") || "Job map limited"}</small></div>)}</div>
      <div className="toolkit-coverage-grid">{groups.map(([label, items]) => <div key={label}><span className="eyebrow">{label}</span><p>{items.join(" · ") || "None called out"}</p></div>)}</div>
    </div>
  );
}
