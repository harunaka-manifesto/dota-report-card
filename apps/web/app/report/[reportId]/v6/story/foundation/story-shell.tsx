import type { ReactNode } from "react";
import styles from "./story-shell.module.css";

export type StoryShellProps = {
  children: ReactNode;
  progress?: ReactNode;
  action?: ReactNode;
  label?: string;
  className?: string;
};

/** The fixed-width editorial canvas; content remains scrollable for text zoom. */
export function StoryShell({ children, progress, action, label = "Dota report story", className = "" }: StoryShellProps) {
  return (
    <main className={`${styles.viewport} dnaStory ${className}`} aria-label={label} tabIndex={-1}>
      <div className={styles.decorativeGrid} aria-hidden="true" />
      <div className={styles.content}>
        {progress ? <div className={styles.progress}>{progress}</div> : null}
        <section className={styles.storyArea}>{children}</section>
        {action ? <footer className={styles.action}>{action}</footer> : null}
      </div>
    </main>
  );
}
