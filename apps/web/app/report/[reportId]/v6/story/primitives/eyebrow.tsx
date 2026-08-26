import type { ReactNode } from "react";
import styles from "./primitives.module.css";

export type EyebrowProps = { children: ReactNode; color?: string; className?: string };

export function Eyebrow({ children, color, className = "" }: EyebrowProps) {
  return <p className={`${styles.eyebrow} ${className}`} style={color ? { color } : undefined}>{children}</p>;
}
