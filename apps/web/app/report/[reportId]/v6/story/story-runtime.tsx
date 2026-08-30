"use client";

/**
 * Shared story runtime: the beat context and the composition primitives.
 *
 * Beats are revealed by opacity and translation only.  Every beat is in the
 * DOM in reading order from mount, so a delayed beat is still announced to
 * assistive technology — visual delay must never hide meaning.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  type ReactNode,
} from "react";
import type { BeatPlan } from "./motion";
import styles from "./story.module.css";

type BeatContextValue = {
  /** How many beats are currently revealed; Infinity once complete. */
  revealed: number;
  /** A page reports its plan on mount so the shell can schedule and complete it. */
  registerPlan: (plan: BeatPlan) => void;
  reducedMotion: boolean;
};

const BeatContext = createContext<BeatContextValue>({
  revealed: Number.POSITIVE_INFINITY,
  registerPlan: () => {},
  reducedMotion: true,
});

export function BeatProvider({ value, children }: { value: BeatContextValue; children: ReactNode }) {
  return <BeatContext.Provider value={value}>{children}</BeatContext.Provider>;
}

export function useBeats(): BeatContextValue {
  return useContext(BeatContext);
}

/** Declares the page's beat plan. Call once per page renderer. */
export function useBeatPlan(plan: BeatPlan): void {
  const { registerPlan } = useBeats();
  const total = plan.total;
  const holdAfter = plan.holdAfter;
  const identityHoldAfter = plan.identityHoldAfter;
  const rhythm = plan.rhythm;
  useEffect(() => {
    registerPlan({ total, holdAfter, identityHoldAfter, rhythm });
  }, [registerPlan, total, holdAfter, identityHoldAfter, rhythm]);
}

export function Beat({
  index,
  className,
  children,
  as: Tag = "div",
}: {
  index: number;
  className?: string;
  children: ReactNode;
  as?: "div" | "p" | "section" | "ul" | "ol" | "footer";
}) {
  const { revealed } = useBeats();
  return (
    <Tag className={[styles.beat, className].filter(Boolean).join(" ")} data-revealed={revealed > index}>
      {children}
    </Tag>
  );
}

/**
 * The Endstop: silence with a visible full stop.  It resolves after the final
 * factual beat and stays still. Shown on every silent close and whenever an
 * optional close is not selected.
 */
export function Endstop({ index }: { index: number }) {
  const { revealed } = useBeats();
  return <div className={styles.endstop} data-revealed={revealed > index} aria-hidden="true" />;
}

/**
 * A dominant value.  Value and unit are separate spans forming one accessible
 * sentence; width is reserved from the settled text so nothing reflows.
 */
export function DominantFact({
  index,
  value,
  unit,
  headingRef,
  heading = true,
}: {
  index: number;
  value: string;
  unit?: string;
  headingRef?: React.RefObject<HTMLHeadingElement>;
  heading?: boolean;
}) {
  const body = (
    <>
      <span className={styles.dominantValue}>{value}</span>
      {unit ? <span className={styles.dominantUnit}>{unit}</span> : null}
    </>
  );
  return (
    <Beat index={index} className={styles.dominant}>
      {heading ? (
        <h1 className={styles.dominantLine} ref={headingRef} tabIndex={-1}>
          {body}
        </h1>
      ) : (
        <p className={styles.dominantLine}>{body}</p>
      )}
    </Beat>
  );
}

/**
 * A dominant value carried inside a contracted sentence.  The sentence is
 * rendered exactly as written; only the numeral takes the larger optical size.
 */
export function DominantSentence({
  index,
  parts,
  headingRef,
}: {
  index: number;
  parts: readonly [string, string, string];
  headingRef?: React.RefObject<HTMLHeadingElement>;
}) {
  return (
    <Beat index={index} className={styles.dominant}>
      <h1 className={styles.dominantSentence} ref={headingRef} tabIndex={-1}>
        {parts[0]}
        <span className={styles.dominantValue}>{parts[1]}</span>
        {parts[2]}
      </h1>
    </Beat>
  );
}

/** One to five text cards sharing a baseline and an ordinal marker. */
export function OrderedStack({
  index,
  rows,
  label,
}: {
  index: number;
  rows: Array<{ key: string; ordinal: number; name: string; detail: string }>;
  label?: string;
}) {
  const { revealed, reducedMotion } = useBeats();
  const open = revealed > index;
  return (
    <Beat index={index} className={styles.stack} as="ol">
      {label ? <span className={styles.visuallyHidden}>{label}</span> : null}
      {rows.map((row, position) => (
        <li
          key={row.key}
          className={styles.stackRow}
          data-revealed={open}
          style={reducedMotion ? undefined : { transitionDelay: `${Math.min(position, 4) * 70}ms` }}
        >
          <span className={styles.stackOrdinal}>{row.ordinal}</span>
          <span className={styles.stackName}>{row.name}</span>
          <span className={styles.stackDetail}>{row.detail}</span>
        </li>
      ))}
    </Beat>
  );
}

/**
 * Dots or blocks on a rule, for streaks and week/day/match geometry.  The
 * chronology is supplied; the renderer never constructs it.
 */
export function Sequence({
  index,
  blocks,
  label,
}: {
  index: number;
  blocks: Array<{ key: string; tone: "loss" | "win" | "neutral" | "highlight" }>;
  label: string;
}) {
  const { revealed, reducedMotion } = useBeats();
  const open = revealed > index;
  return (
    <Beat index={index} className={styles.sequence}>
      <span className={styles.visuallyHidden}>{label}</span>
      <div className={styles.sequenceTrack} aria-hidden="true">
        {blocks.map((block, position) => (
          <span
            key={block.key}
            className={styles.sequenceBlock}
            data-tone={block.tone}
            data-revealed={open}
            style={reducedMotion ? undefined : { transitionDelay: `${Math.min(position, 11) * 70}ms` }}
          />
        ))}
      </div>
    </Beat>
  );
}

/** Seven labeled channels. Unavailable values are omitted, never zeroed. */
export function SignalField({
  index,
  channels,
}: {
  index: number;
  channels: Array<{ key: string; label: string; measured: boolean }>;
}) {
  const { revealed, reducedMotion } = useBeats();
  const open = revealed > index;
  return (
    <Beat index={index} className={styles.signalField} as="ul">
      {channels.map((channel, position) => (
        <li
          key={channel.key}
          className={styles.signalChannel}
          data-element={channel.key}
          data-revealed={open}
          style={reducedMotion ? undefined : { transitionDelay: `${Math.min(position, 6) * 70}ms` }}
        >
          <span className={styles.signalLabel}>{channel.label}</span>
          <span className={styles.signalRail} data-measured={channel.measured} aria-hidden="true" />
        </li>
      ))}
    </Beat>
  );
}

/** Inline Evidence, expanded in place beneath the fact it explains. */
export function InlineEvidence({
  id,
  open,
  onToggle,
  headline,
  statement,
  rows,
  alternatives,
  limitations,
}: {
  id: string;
  open: boolean;
  onToggle: () => void;
  headline: string;
  statement?: string | null;
  rows: string[];
  alternatives: string[];
  limitations: string[];
}) {
  const regionId = `${id}-region`;
  const toggleRef = useRef<HTMLButtonElement>(null);
  const regionRef = useRef<HTMLDivElement>(null);
  const previousOpen = useRef(open);
  useEffect(() => {
    if (previousOpen.current === open) return;
    previousOpen.current = open;
    requestAnimationFrame(() => (open ? regionRef.current : toggleRef.current)?.focus());
  }, [open]);
  return (
    <div
      className={styles.evidence}
      onKeyDown={(event) => {
        if (event.key !== "Escape") return;
        event.preventDefault();
        onToggle();
      }}
    >
      <button
        ref={toggleRef}
        type="button"
        className={styles.evidenceToggle}
        aria-expanded={open}
        aria-controls={regionId}
        onClick={onToggle}
      >
        {open ? "Hide evidence" : "Why this?"}
      </button>
      <div
        ref={regionRef}
        id={regionId}
        className={styles.evidenceRegion}
        role="region"
        aria-label={headline}
        data-open={open}
        hidden={!open}
        tabIndex={-1}
      >
        {statement ? <p>{statement}</p> : null}
        {rows.length > 0 ? (
          <ul>
            {rows.map((row) => (
              <li key={row}>{row}</li>
            ))}
          </ul>
        ) : null}
        {alternatives.length > 0 ? (
          <section>
            <h3>What else could explain it?</h3>
            <ul>
              {alternatives.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        ) : null}
        {limitations.length > 0 ? (
          <section>
            <h3>Limitations</h3>
            <ul>
              {limitations.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>
    </div>
  );
}

/** Convenience for pages that only need to know their own reveal state. */
export function useRevealed(index: number): boolean {
  const { revealed } = useBeats();
  return useMemo(() => revealed > index, [revealed, index]);
}
