import type { ReactNode } from "react";
import styles from "./primitives.module.css";

export type HeadlineProps = { children: ReactNode; as?: "h1" | "h2" | "h3"; className?: string };

export function Headline({ children, as = "h1", className = "" }: HeadlineProps) {
  const Tag = as;
  return <Tag className={`${styles.headline} ${className}`}>{children}</Tag>;
}
