import type { PatternVisualProps } from "./visual-types";
import { numberValue, recordArray, stringArray, stringValue } from "./visual-types";

export function FlexWindowGrid({ proof }: PatternVisualProps) {
  const names = stringArray(proof.hero_names);
  const namedRows = recordArray(proof.hero_rows);
  const counts = Array.isArray(proof.hero_game_counts) ? proof.hero_game_counts : [];
  const rows = namedRows.length > 0
    ? namedRows.map((row) => ({ name: stringValue(row.hero_name), count: numberValue(row.game_count) }))
    : names.map((name, index) => ({ name, count: Array.isArray(counts[index]) ? numberValue(counts[index][1]) : 0 }));
  return (
    <div className="pattern-visual pattern-visual-flex" aria-label="Flexibility window">
      <div className="flex-window-stats"><strong>{stringValue(proof.total_games, "—")} games</strong><span>{stringValue(proof.functional_job_count, "—")} functional jobs</span><span>{stringValue(proof.repeated_hero_count, "—")} heroes repeated</span></div>
      <div className="flex-hero-grid">{rows.map((row) => <div className="flex-hero-cell" key={row.name}><strong>{row.name}</strong><span>{row.count}×</span></div>)}</div>
      <div className="flex-jobs"><span className="eyebrow">FUNCTIONAL RANGE</span><p>{stringArray(proof.functional_jobs).join(" · ") || "Functional coverage is limited."}</p></div>
    </div>
  );
}
