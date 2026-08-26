import type { ReactNode } from "react";
import { EvidenceRow, type EvidenceRowProps } from "./evidence-row";
import styles from "./primitives.module.css";

export type EvidencePanelProps = { heading?: string; rows?: readonly EvidenceRowProps[]; children?: ReactNode; className?: string };

export function EvidencePanel({ heading = "What we measured", rows = [], children, className = "" }: EvidencePanelProps) {
  return <section className={`${styles.evidencePanel} ${className}`} aria-label={heading}><h2 className={styles.evidenceHeading}>{heading}</h2>{rows.map((row) => <EvidenceRow key={`${row.label}-${row.value}`} {...row} />)}{children}</section>;
}
