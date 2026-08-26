import styles from "./primitives.module.css";

export type SegmentOption = { id: string; label: string };
export type SegmentedControlProps = {
  options: readonly SegmentOption[];
  value: string;
  onChange: (value: string) => void;
  label?: string;
  className?: string;
};

export function SegmentedControl({ options, value, onChange, label = "Select view", className = "" }: SegmentedControlProps) {
  return (
    <div className={`${styles.segmentedControl} ${className}`} role="tablist" aria-label={label}>
      {options.map((option) => (
        <button key={option.id} type="button" role="tab" aria-selected={option.id === value} className={`${styles.segmentButton} ${option.id === value ? styles.segmentButtonSelected : ""}`} onClick={() => onChange(option.id)}>
          {option.label}
        </button>
      ))}
    </div>
  );
}
