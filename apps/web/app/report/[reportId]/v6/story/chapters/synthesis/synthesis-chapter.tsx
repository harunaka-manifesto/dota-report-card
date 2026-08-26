import type { V6Element, V6IdentitySummary } from "../../../types";
import { DNASignature } from "../../visualizations/dna-signature";
import styles from "../chapters.module.css";

export function SynthesisChapter({ elements, identity, phase }: { elements: V6Element[]; identity: V6IdentitySummary; phase: number }) {
  return (
    <section className={`${styles.chapter} ${styles.synthesisChapter}`} data-phase={phase} aria-labelledby="story-synthesis-title">
      <div className={styles.chapterHeader}><span>Synthesis</span><span>08 / 11</span></div>
      <p className={styles.eyebrow}>Putting it together</p>
      <h1 id="story-synthesis-title">The signals keep resolving into one shape.</h1>
      <DNASignature elements={elements} slots={identity.slots} phase={phase} />
      {phase >= 5 && identity.common_thread && <p className={styles.body}>{identity.common_thread}</p>}
    </section>
  );
}
