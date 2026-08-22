import type { PatternVisualProps } from "./visual-types";
import { recordArray, stringArray, stringValue } from "./visual-types";

export function HeroJobCluster({ proof }: PatternVisualProps) {
  const heroes = stringArray(proof.hero_names);
  const jobs = recordArray(proof.job_clusters);
  return (
    <div className="pattern-visual pattern-visual-job-cluster" aria-label="Hero job clusters">
      <div className="pattern-visual-heading"><span className="eyebrow">Hero pool</span><strong>{heroes.length || stringValue(proof.regular_hero_count, "—")} heroes · {stringValue(proof.regular_hero_count, "—")} regular</strong></div>
      <div className="hero-name-cloud">{heroes.map((hero) => <span key={hero}>{hero}</span>)}</div>
      <div className="job-cluster-list">
        {jobs.length > 0 ? jobs.map((job) => {
          const names = stringArray(job.hero_names);
          return <div className="job-cluster-row" key={stringValue(job.job)}><div><strong>{stringValue(job.job)}</strong><small>{names.join(" · ")}</small></div><span className="job-cluster-count">{names.length}</span></div>;
        }) : <p className="muted">The repeated job cluster is supported; hero-level grouping is limited.</p>}
      </div>
    </div>
  );
}
