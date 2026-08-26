"use client";

import type { V6Finding } from "../../types";
import {
  adaptV6Finding,
  type OutcomePhase,
} from "./outcome-config";
import { OutcomeEvidence } from "./outcome-evidence";
import styles from "./outcomes.module.css";

export type OutcomeSequenceProps = {
  outcome: V6Finding;
  phase: OutcomePhase;
};

export function OutcomeSequence({ outcome: finding, phase }: OutcomeSequenceProps) {
  const outcome = adaptV6Finding(finding);
  if (!outcome) {
    return <p className={styles.empty} role="status">This finding has no supported outcome presentation.</p>;
  }

  const presentation = outcome.config.phases[phase];
  const unavailable = finding.published === false || ["limited", "suppressed", "unavailable"].includes(finding.status ?? "");

  return (
    <article
      className={styles.root}
      data-outcome-key={outcome.key}
      data-phase={phase}
      data-state={unavailable ? "unavailable" : "available"}
      aria-label={`${outcome.config.family}: ${outcome.config.label}`}
    >
      <p className={styles.eyebrow}>{outcome.config.family} · {presentation.label}</p>
      <h2 className={styles.title}>{presentation.heading}</h2>
      {unavailable ? (
        <p className={styles.empty}>This finding did not clear the evidence threshold.</p>
      ) : phase === "reveal" ? (
        <p className={styles.copy}>{outcome.claim ?? "No server-authored claim was provided."}</p>
      ) : phase === "interpretation" ? (
        <p className={styles.copy}>{outcome.interpretation ?? "No server-authored interpretation was provided."}</p>
      ) : (
        <OutcomeEvidence outcome={outcome} expanded={phase === "expanded-evidence"} />
      )}
    </article>
  );
}

export default OutcomeSequence;
