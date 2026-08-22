import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import type { BehaviorElementReceipt } from "../../../../../packages/api-client/src";

export function StoryPage({
  id,
  index,
  kind,
  children
}: {
  id: string;
  index: number;
  kind: string;
  children: ReactNode;
}) {
  return (
    <section id={id} className="story-page" data-page-id={id} data-page-kind={kind} aria-labelledby={`${id}-heading`}>
      <div className="story-page-inner">
        <span className="story-page-number">{String(index + 1).padStart(2, "0")}</span>
        {children}
      </div>
    </section>
  );
}

export function Spectrum({
  score,
  left,
  right,
  disabled = false
}: {
  score: number | null;
  left: string | null;
  right: string | null;
  disabled?: boolean;
}) {
  const position = score === null ? 50 : Math.round(Math.max(0, Math.min(1, score)) * 100);
  return (
    <div className={`spectrum${disabled ? " is-disabled" : ""}`} aria-label={score === null ? "Signal unavailable" : `${left ?? "Lower"} to ${right ?? "Higher"}, ${position}% toward ${right ?? "Higher"}`}>
      <div className="spectrum-labels"><span>{left ?? "Lower"}</span><span>{right ?? "Higher"}</span></div>
      <div className="spectrum-track"><span className="spectrum-marker" style={{ left: `${position}%` }} /></div>
    </div>
  );
}

export function EvidenceReceipt({ evidence }: { evidence: BehaviorElementReceipt[] }) {
  if (!evidence.length) return null;
  return <div className="receipt" aria-label="Evidence receipt">{evidence.slice(0, 3).map((item) => <span key={item.key}><strong>{formatValue(item.value, item.unit)}</strong><small>{item.comparison ?? item.key.replaceAll("_", " ")} · {item.denominator} matches</small></span>)}</div>;
}

export function MethodologySheet({
  open,
  title,
  body,
  onClose
}: {
  open: boolean;
  title: string;
  body: string;
  onClose: () => void;
}) {
  const closeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.requestAnimationFrame(() => closeRef.current?.focus());
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }
      if (event.key !== "Tab") return;
      const dialog = closeRef.current?.closest("[role=dialog]") as HTMLElement | null;
      if (!dialog) return;
      const focusable = Array.from(dialog.querySelectorAll<HTMLElement>("button, a, input, [tabindex]:not([tabindex='-1'])")).filter((element) => !element.hasAttribute("disabled"));
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
      previous?.focus();
    };
  }, [onClose, open]);

  if (!open) return null;
  return (
    <div className="sheet-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <div className="methodology-sheet" role="dialog" aria-modal="true" aria-labelledby="methodology-title">
        <button ref={closeRef} className="sheet-close" type="button" onClick={onClose} aria-label="Close methodology">×</button>
        <p className="eyebrow">How to read this</p>
        <h2 id="methodology-title">{title}</h2>
        <p>{body}</p>
        <p className="muted">Scores describe observable summary-history patterns. They are not grades, diagnoses, or predictions.</p>
      </div>
    </div>
  );
}

export function DeepDiveTeaser({ href, headingId, title = "Tell me more", body, onClick }: { href: string | null; headingId?: string; title?: string; body?: string | null; onClick?: () => void }) {
  return <div className="deep-dive-teaser"><p className="eyebrow">Next layer</p><h2 id={headingId}>{title}</h2><p>{body}</p>{href && <a className="story-link" href={href} onClick={onClick}>Explore Deep Dive →</a>}</div>;
}

function formatValue(value: string | number | boolean | null, unit: string): string {
  if (value === null) return "Not available";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "string") return value;
  if (unit === "share" || unit === "rate") return `${Math.round(value * 100)}%`;
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}
