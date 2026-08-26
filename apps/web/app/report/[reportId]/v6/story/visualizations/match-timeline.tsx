export type MatchCell = {
  id: string;
  label: string;
  result?: string | null;
  context?: string | null;
  isLoss?: boolean;
};

export type MatchTimelinePhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

import styles from "./match-timeline.module.css";

/** Persistent timeline cells; phase controls only disclosure, never identity. */
export function MatchTimeline({ matches, phase = 0 }: { matches: readonly MatchCell[]; phase?: MatchTimelinePhase }) {
  const reveal = (at: MatchTimelinePhase) => phase >= at;
  return (
    <ol className={styles.timeline} data-phase={phase} aria-label="Match timeline">
      {matches.map((match) => (
        <li className={`${styles.cell} ${match.isLoss ? styles.loss : ""}`} key={match.id}>
          <span className={styles.marker} aria-hidden="true" />
          <strong>{match.label}</strong>
          <span className={reveal(1) ? styles.revealed : styles.hidden}>{match.context || "Context not available"}</span>
          <small className={reveal(2) ? styles.revealed : styles.hidden}>{match.result || "Result not available"}</small>
        </li>
      ))}
      {matches.length === 0 && <li className={styles.empty}>Match timeline is not available for this report.</li>}
    </ol>
  );
}
