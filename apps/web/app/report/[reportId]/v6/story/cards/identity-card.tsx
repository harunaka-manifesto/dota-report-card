import type { V6IdentitySummary } from "../../types";
import styles from "./identity-card.module.css";

function identityName(summary: V6IdentitySummary): string {
  return summary.slots?.primary?.text ?? summary.title ?? summary.headline ?? "Identity still forming";
}

export function IdentityCard({ summary, phase = 0 }: { summary: V6IdentitySummary; phase?: number }) {
  const currentPhase = Math.max(0, Math.min(8, phase));
  const front = currentPhase >= 3;
  const descriptors = [summary.slots?.primary?.scope, summary.slots?.twist?.text, summary.slots?.anchor?.text].filter((value): value is string => Boolean(value));

  return (
    <article className={styles.stage} data-phase={currentPhase} aria-label="Dota DNA identity card">
      <div className={styles.card} data-front={front}>
        <div className={`${styles.face} ${styles.back}`} aria-hidden={front}>
          <p>DOTA DNA</p>
          <IdentityMark />
          <strong>PRIMARY / 01</strong>
        </div>
        <div className={`${styles.face} ${styles.front}`} aria-hidden={!front || currentPhase < 4}>
          <p>PRIMARY READ</p>
          <IdentityMark />
          <h2 aria-live="polite">{identityName(summary)}</h2>
          {descriptors.length > 0 && <small>{descriptors.join(" · ")}</small>}
        </div>
      </div>
    </article>
  );
}

function IdentityMark() {
  return <span className={styles.mark} aria-hidden="true"><i /><i /><i /><i /><i /><i /></span>;
}
