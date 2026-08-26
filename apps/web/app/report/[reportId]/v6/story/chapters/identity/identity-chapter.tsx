import type { V6IdentitySummary } from "../../../types";
import { IdentityCard } from "../../cards/identity-card";
import styles from "../chapters.module.css";

export function IdentityChapter({ identity, phase }: { identity: V6IdentitySummary; phase: number }) {
  const support = identity.supporting_lines ?? identity.support ?? [];
  return (
    <section className={`${styles.chapter} ${styles.identityChapter}`} data-phase={phase} aria-labelledby="story-identity-title">
      <div className={styles.chapterHeader}><span>Your read</span><span>09 / 11</span></div>
      <p className={styles.eyebrow}>Primary read</p>
      <h1 id="story-identity-title" className={phase < 4 ? styles.visuallyHidden : undefined}>Your Dota DNA.</h1>
      <IdentityCard summary={identity} phase={phase} />
      {phase >= 6 && identity.body && <p className={styles.body}>{identity.body}</p>}
      {phase >= 7 && support.length > 0 && <ul className={styles.evidence}>{support.map((line) => <li key={line}>{line}</li>)}</ul>}
    </section>
  );
}
