import type { ButtonHTMLAttributes } from "react";
import styles from "./primitives.module.css";

export function PrimaryButton({ className = "", type = "button", ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button {...props} type={type} className={`${styles.button} ${styles.primaryButton} ${className}`} />;
}
