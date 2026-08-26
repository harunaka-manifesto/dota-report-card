import type { ReactNode } from "react";
import styles from "./primitives.module.css";

export type BodyCopyProps = { children: ReactNode; className?: string };

export function BodyCopy({ children, className = "" }: BodyCopyProps) {
  return <p className={`${styles.bodyCopy} ${className}`}>{children}</p>;
}
