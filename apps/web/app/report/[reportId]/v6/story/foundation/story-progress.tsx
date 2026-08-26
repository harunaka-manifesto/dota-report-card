import styles from "./story-progress.module.css";

export type StoryProgressProps = {
  total?: number;
  active?: number;
  label?: string;
};

/** Fourteen narrative segments; micro-reveal phases do not add segments. */
export function StoryProgress({ total = 14, active = 0, label = "Story progress" }: StoryProgressProps) {
  const count = Math.max(1, Math.floor(total));
  const current = Math.min(count - 1, Math.max(0, Math.floor(active)));

  return (
    <div className={styles.progress} role="progressbar" aria-label={label} aria-valuemin={1} aria-valuemax={count} aria-valuenow={current + 1} aria-valuetext={`Step ${current + 1} of ${count}`}>
      {Array.from({ length: count }, (_, index) => (
        <span key={index} className={`${styles.segment} ${index <= current ? styles.complete : ""}`} aria-hidden="true" />
      ))}
    </div>
  );
}
