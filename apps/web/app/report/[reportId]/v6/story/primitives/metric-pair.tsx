import type { MetricProps } from "./metric";
import { Metric } from "./metric";
import styles from "./primitives.module.css";

export type MetricPairProps = { left: MetricProps; right: MetricProps; className?: string };

export function MetricPair({ left, right, className = "" }: MetricPairProps) {
  return <div className={`${styles.metricPair} ${className}`}><Metric {...left} /><span className={styles.metricDivider} aria-hidden="true" /><Metric {...right} /></div>;
}
