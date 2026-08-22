import type { PatternVisualProps } from "./visual-types";
import { recordArray, stringValue } from "./visual-types";

export function HeroReliabilityLadder({ proof }: PatternVisualProps) {
  const heroes = recordArray(proof.ranked_heroes);
  return (
    <div className="pattern-visual pattern-visual-reliability" aria-label="Hero reliability ladder">
      <div className="ladder-labels"><span>REFERENCE CORE</span><span>DEVELOPMENT SIDE</span></div>
      <ol className="reliability-ladder">
        {heroes.map((hero) => <li key={`${stringValue(hero.hero_name)}-${stringValue(hero.rank)}`} className={`reliability-step reliability-${String(hero.band).toLowerCase().replaceAll(" ", "-")}`}><span className="reliability-rank">#{stringValue(hero.rank)}</span><strong>{stringValue(hero.hero_name)}</strong><span className="reliability-band">{stringValue(hero.band)}</span><small>{stringValue(hero.matches, "0")} usable matches</small></li>)}
      </ol>
    </div>
  );
}
