import type { ButtonHTMLAttributes } from "react";
import styles from "./primitives.module.css";

export function SecondaryButton({ className = "", type = "button", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} type={type} className={`${styles.button} ${styles.secondaryButton} ${className}`} />;
}
