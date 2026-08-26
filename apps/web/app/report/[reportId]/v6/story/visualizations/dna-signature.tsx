import type { V6Element, V61IdentitySlot } from "../../types";
import styles from "./dna-signature.module.css";

type Slot = V61IdentitySlot | null | undefined;

export function DNAFragment({ index, active = true }: { index: number; active?: boolean }) {
  return (
    <span
      className={styles.fragment}
      data-active={active}
      style={{ "--fragment-index": index } as React.CSSProperties}
      aria-hidden="true"
    >
      <i /><i /><i />
    </span>
  );
}

export function DNASignature({
  elements,
  slots,
  phase = 0,
  label = "Dota DNA signature",
}: {
  elements: V6Element[];
  slots?: { primary?: Slot; twist?: Slot; anchor?: Slot } | null;
  phase?: number;
  label?: string;
}) {
  const available = elements.filter((element) => !["suppressed", "unavailable"].includes(element.status ?? "available"));
  const reads = [slots?.primary, slots?.twist, slots?.anchor].filter((slot): slot is V61IdentitySlot => Boolean(slot?.text));
  const labels = elements.slice(0, 7).map((element) => element.label).filter(Boolean);

  return (
    <figure className={styles.signature} data-phase={Math.max(0, Math.min(6, phase))} aria-label={label}>
      <div className={styles.field} aria-hidden="true">
        <span className={styles.connections} />
        {Array.from({ length: 7 }, (_, index) => <DNAFragment key={index} index={index} active={index < available.length} />)}
      </div>
      <figcaption className={styles.caption}>
        {phase >= 2 && labels.map((text, index) => <span key={`${text}-${index}`} className={styles.elementLabel}>{text}</span>)}
        {reads.map((slot) => <span key={`${slot.kind}-${slot.scope}`}>{slot.text}</span>)}
      </figcaption>
    </figure>
  );
}
