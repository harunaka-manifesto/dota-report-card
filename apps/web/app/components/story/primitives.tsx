import { useEffect, useRef } from "react";
import type { ReactNode } from "react";
import type { Evidence, HeroCard } from "../../../../../packages/api-client/src";

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

export function SectionIntro({ title, body, headingId }: { title: string; body?: string | null; headingId?: string }) {
  return <div className="story-intro"><p className="eyebrow">A new section</p><h2 id={headingId}>{title}</h2>{body && <p>{body}</p>}</div>;
}

export function Spectrum({
  score,
  left,
  right,
  disabled = false
}: {
  score: number | null;
  left: string;
  right: string;
  disabled?: boolean;
}) {
  const position = score === null ? 50 : Math.round(Math.max(0, Math.min(1, score)) * 100);
  return (
    <div className={`spectrum${disabled ? " is-disabled" : ""}`} aria-label={score === null ? "Signal unavailable" : `${left} to ${right}, ${position}% toward ${right}`}>
      <div className="spectrum-labels"><span>{left}</span><span>{right}</span></div>
      <div className="spectrum-track"><span className="spectrum-marker" style={{ left: `${position}%` }} /></div>
    </div>
  );
}

export function EvidenceReceipt({ evidence }: { evidence: Evidence[] }) {
  if (!evidence.length) return null;
  return <div className="receipt" aria-label="Evidence receipt">{evidence.slice(0, 3).map((item) => <span key={item.key}><strong>{formatValue(item.value, item.unit)}</strong><small>{item.key.replaceAll("_", " ")} · n={item.denominator}</small></span>)}</div>;
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
    const previousScrollY = window.scrollY;
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
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>("button, a, input, [tabindex]:not([tabindex='-1'])")
      ).filter((element) => !element.hasAttribute("disabled"));
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
      window.scrollTo({ top: previousScrollY, left: 0, behavior: "auto" });
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

export function HeroPortraitCard({ hero, featured = false }: { hero: HeroCard | null; featured?: boolean }) {
  return <article className={`hero-portrait-card${featured ? " is-featured" : ""}`}>
    <div className="hero-portrait-frame">{hero?.portrait_url ? <img src={hero.portrait_url} alt="" /> : <span>{hero?.name?.slice(0, 1) ?? "?"}</span>}</div>
    <div><span className="eyebrow">{featured ? "Signature hero" : "Comfort pick"}</span><h3>{hero?.name ?? "No stable hero yet"}</h3>{hero?.matches !== undefined && <p>{hero.matches} observed games</p>}</div>
  </article>;
}

export function DeepDiveTeaser({ href, headingId, title = "See what drives it", body = "Deep Dive can inspect selected matches in more detail when you want the explanation behind the pattern.", onClick }: { href: string | null; headingId?: string; title?: string; body?: string | null; onClick?: () => void }) {
  return <div className="deep-dive-teaser"><p className="eyebrow">Next layer</p><h2 id={headingId}>{title}</h2><p>{body}</p>{href && <a className="story-link" href={href} onClick={onClick}>Explore Deep Dive →</a>}</div>;
}

function formatValue(value: string | number | null, unit: string): string {
  if (value === null) return "Not available";
  if (typeof value === "string") return value;
  if (unit === "share" || unit === "rate") return `${Math.round(value * 100)}%`;
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}
