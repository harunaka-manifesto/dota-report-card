import styles from "./primitives.module.css";

export type EvidenceRowProps = { label: string; value: string | number; className?: string };

export function EvidenceRow({ label, value, className = "" }: EvidenceRowProps) {
  return <div className={`${styles.evidenceRow} ${className}`} role="group"><span className={styles.evidenceKey}>{label}</span><span className={styles.evidenceValue}>{value}</span></div>;
}
