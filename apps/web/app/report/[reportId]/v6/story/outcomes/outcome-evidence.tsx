import type { AdaptedOutcome } from "./outcome-config";
import styles from "./outcomes.module.css";

export function OutcomeEvidence({ outcome, expanded = false }: { outcome: AdaptedOutcome; expanded?: boolean }) {
  if (outcome.evidence.length === 0 && (!expanded || outcome.alternatives.length === 0)) {
    return <p className={styles.empty}>Evidence was not included for this finding.</p>;
  }

  return (
    <div className={styles.evidence}>
      {outcome.evidence.length > 0 && (
        <ul className={styles.list} aria-label="Observed evidence">
          {outcome.evidence.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
        </ul>
      )}
      {expanded && outcome.alternatives.length > 0 && (
        <div className={styles.alternatives}>
          <p className={styles.subhead}>Alternatives kept in view</p>
          <ul className={styles.list} aria-label="Evidence alternatives">
            {outcome.alternatives.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}
