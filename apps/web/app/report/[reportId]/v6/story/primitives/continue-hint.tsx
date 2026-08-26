import type { ButtonHTMLAttributes } from "react";
import styles from "./primitives.module.css";

export type ContinueHintProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "className"> & { className?: string };

export function ContinueHint({ children = "Continue  →", className = "", type = "button", ...props }: ContinueHintProps) {
  return <button {...props} type={type} className={`${styles.continueHint} ${className}`}>{children}</button>;
}
