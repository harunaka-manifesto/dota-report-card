import type { V6ComparisonRow } from "../../types";
import styles from "./session-curve.module.css";

export type SessionCurvePhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export type SessionPoint = {
  id: string;
  label: string;
  value?: string | number | null;
  revealAt: 0 | 1 | 2 | 3 | 4;
};

export function comparisonRowsToSessionPoints(rows: readonly V6ComparisonRow[]): SessionPoint[] {
  return rows.map((row, index) => ({
    id: row.key ?? `${row.label}-${index}`,
    label: row.label,
    value: row.value ?? row.estimate,
    revealAt: index === 0 ? 1 : index < 3 ? 2 : 3,
  }));
}

/** Persistent SVG nodes: phase changes update classes, never replace the curve. */
export function SessionCurve({ points, phase = 0 }: { points: readonly SessionPoint[]; phase?: SessionCurvePhase }) {
  const coordinates = points.map((point, index) => `${12 + (index * 76) / Math.max(1, points.length - 1)},${58 - numericValue(point.value, index, points.length)}`).join(" ");
  return (
    <figure className={styles.figure} aria-label="Session movement curve">
      {points.length > 0 ? (
        <svg className={styles.curve} viewBox="0 0 88 64" role="img" aria-label="Observed session points">
          <polyline className={styles.grid} points="0,16 88,16 M0,32 88,32 M0,48 88,48" />
          <polyline className={styles.line} points={coordinates} />
          {points.map((point, index) => {
            const x = 12 + (index * 76) / Math.max(1, points.length - 1);
            const y = 58 - numericValue(point.value, index, points.length);
            return <g className={point.revealAt <= phase ? styles.pointVisible : styles.point} key={point.id} transform={`translate(${x} ${y})`}><circle r="2.8" /><title>{point.label}{point.value !== null && point.value !== undefined ? `: ${point.value}` : ""}</title></g>;
          })}
        </svg>
      ) : <p className={styles.empty}>No session points were included for this finding.</p>}
      {points.length > 0 && <figcaption>{phase >= 4 ? "Relevant movement highlighted" : "Session points remain stable as the read builds."}</figcaption>}
    </figure>
  );
}

function numericValue(value: string | number | null | undefined, index: number, count: number): number {
  void index;
  void count;
  if (typeof value === "number" && Number.isFinite(value)) return Math.max(2, Math.min(48, Math.abs(value) * 48));
  return 26;
}
