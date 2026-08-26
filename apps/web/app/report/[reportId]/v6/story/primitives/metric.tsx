import styles from "./primitives.module.css";

export type MetricProps = { value: string | number; label: string; className?: string };

export function Metric({ value, label, className = "" }: MetricProps) {
  return <div className={`${styles.metric} ${className}`}><strong className={styles.metricValue}>{value}</strong><span className={styles.metricLabel}>{label}</span></div>;
}
