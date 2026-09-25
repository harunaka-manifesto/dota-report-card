/**
 * The explicit legacy compatibility path.
 *
 * A persisted V6.1 report that predates `story_payload` renders through the
 * original Case Notes composer, unchanged.  New reports never reach this file:
 * `report-story-v6.tsx` routes them to the thirty-three-page story instead.
 */

"use client";

import Link from "next/link";
import {
  type CSSProperties,
  type KeyboardEvent as ReactKeyboardEvent,
  type MutableRefObject,
  type PointerEvent as ReactPointerEvent,
  type ReactNode,
  type RefObject,
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { track } from "../../../lib/analytics";
import {
  SIGNAL_LABELS,
  buildStoryPages,
  type EvidenceModel,
  type StoryPage,
} from "./story-v61";
import type { V61Report } from "./types";
import styles from "./report-story-v6.module.css";

type Direction = "forward" | "backward";
type NavSource = "pointer" | "keyboard";
type DialogName = "methodology" | "exit" | null;
type PointerStart = { x: number; y: number; target: EventTarget | null; selectionActive: boolean };

const ENTRANCE_DURATION = 320;
const EDGE_WIDTH = 56;
const DRAG_THRESHOLD = 12;
const INTERACTIVE_SELECTOR = "button, a, input, textarea, select, dialog, [contenteditable='true']";
const DIGIT_REVEAL = 460;
const DIGIT_STAGGER = 65;

/**
 * Entrance steps, in milliseconds after the press. Nothing the reader needs
 * arrives later than STEP.EVIDENCE; the Signature reveal is the only page
 * allowed to run past it, and it does so once.
 */
const STEP = { BRIDGE: 90, LEAD: 180, HAIRLINE: 340, SUPPORT: 340, EVIDENCE: 440 } as const;
const ROW_STAGGER = 55;
const MAX_STAGGERED_ROWS = 3;

/**
 * Chapter composition. `ratio` positions the hairline between the two voices;
 * null means the chapter speaks with one voice and has no hairline. `question`
 * marks the chapters whose composer copy supplies a question, which is the only
 * place a claim may precede its supporting observation.
 *
 * Derived from `page.chapter`, which every persisted report already carries, so
 * this adds nothing to the StoryPage contract. An unknown chapter falls back to
 * a balanced, observation-led composition rather than failing to render.
 */
type ChapterLayout = { ratio: number | null; question: boolean };
const CHAPTER_LAYOUT: Record<string, ChapterLayout> = {
  Recognition: { ratio: null, question: false },
  Familiarity: { ratio: 0.38, question: false },
  Structure: { ratio: 0.5, question: false },
  Adaptability: { ratio: 0.55, question: true },
  Adversity: { ratio: 0.62, question: true },
  Expression: { ratio: 0.5, question: true },
  Time: { ratio: 0.44, question: true },
  Coherence: { ratio: 0.7, question: false },
  Signature: { ratio: null, question: false },
  Share: { ratio: null, question: false },
  End: { ratio: null, question: false },
};
const DEFAULT_LAYOUT: ChapterLayout = { ratio: 0.5, question: false };
const PAGE_RATIO_OVERRIDE: Record<string, number> = { "pool-movement": 0.44 };

function chapterLayout(page: StoryPage): ChapterLayout {
  const base = CHAPTER_LAYOUT[page.chapter] ?? DEFAULT_LAYOUT;
  const override = PAGE_RATIO_OVERRIDE[page.id];
  return override === undefined ? base : { ...base, ratio: override };
}

export default function LegacyStoryV61({ report }: { report: V61Report }) {
  const pages = useMemo(() => buildStoryPages(report), [report]);
  const reducedMotion = useReducedMotion();
  const [pageIndex, setPageIndex] = useState(0);
  const [direction, setDirection] = useState<Direction>("forward");
  const [navSource, setNavSource] = useState<NavSource>("pointer");
  const [openDialog, setOpenDialog] = useState<DialogName>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [fallbackUrl, setFallbackUrl] = useState("");
  const pointerStart = useRef<PointerStart | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const focusHeadingAfterNavigation = useRef(false);
  const evidenceControl = useRef<HTMLButtonElement | null>(null);
  const overlayStarted = useRef(0);
  const overlayOrigin = useRef<HTMLElement | null>(null);
  const leaveDirection = useRef<string>("exit");
  const receiptSettled = useRef(false);
  const page = pages[pageIndex];
  const layout = chapterLayout(page);

  usePageAnalytics(page, pageIndex, pages.length, reducedMotion, leaveDirection);

  useEffect(() => { setEvidenceOpen(false); }, [pageIndex]);

  useLayoutEffect(() => {
    if (!focusHeadingAfterNavigation.current) return;
    focusHeadingAfterNavigation.current = false;
    headingRef.current?.focus({ preventScroll: true });
  }, [page.id]);

  /**
   * The page commits on the press. There is no leave phase to wait out, so the
   * frame never blanks and a press cadence faster than the entrance can never
   * starve the commit: every press lands exactly one page.
   */
  const navigate = useCallback((step: number, nextDirection: Direction, source: NavSource = "pointer") => {
    setPageIndex((current) => {
      const nextIndex = current + step;
      if (nextIndex < 0 || nextIndex >= pages.length) return current;
      leaveDirection.current = nextDirection;
      focusHeadingAfterNavigation.current = true;
      setNavSource(source);
      setDirection(nextDirection);
      requestAnimationFrame(() => {
        track("report.story_transition_completed.v1", {
          page_id: pages[nextIndex].id,
          direction: nextDirection,
          transition_duration_ms: reducedMotion ? 0 : ENTRANCE_DURATION,
          reduced_motion: reducedMotion,
        });
      });
      return nextIndex;
    });
  }, [pages, reducedMotion]);

  const handlePointerDown = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    const selection = window.getSelection();
    pointerStart.current = { x: event.clientX, y: event.clientY, target: event.target, selectionActive: Boolean(selection && !selection.isCollapsed) };
  }, []);

  const handlePointerUp = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    const start = pointerStart.current;
    pointerStart.current = null;
    if (!start || openDialog) return;
    if (Math.hypot(event.clientX - start.x, event.clientY - start.y) > DRAG_THRESHOLD) return;
    const startTarget = start.target instanceof Element ? start.target : null;
    const endTarget = event.target instanceof Element ? event.target : null;
    if (startTarget?.closest(INTERACTIVE_SELECTOR) || endTarget?.closest(INTERACTIVE_SELECTOR)) return;
    const selection = window.getSelection();
    if (start.selectionActive || (selection && !selection.isCollapsed)) return;
    if (event.clientX <= EDGE_WIDTH) navigate(-1, "backward", "pointer");
    else if (event.clientX >= window.innerWidth - EDGE_WIDTH) navigate(1, "forward", "pointer");
  }, [navigate, openDialog]);

  const closeEvidence = useCallback(() => {
    setEvidenceOpen(false);
    track("report.evidence_closed.v1", {
      ...pageEvent(page, pageIndex, pages.length),
      overlay_duration_ms: roundedDuration(overlayStarted.current),
    });
    requestAnimationFrame(() => evidenceControl.current?.focus());
  }, [page, pageIndex, pages.length]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (openDialog || event.altKey || event.ctrlKey || event.metaKey) return;
      if (event.key === "Escape" && evidenceOpen) { closeEvidence(); return; }
      if (evidenceOpen) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, button, a, [contenteditable='true']")) return;
      if (event.key === "ArrowRight") navigate(1, "forward", "keyboard");
      if (event.key === "ArrowLeft") navigate(-1, "backward", "keyboard");
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [closeEvidence, evidenceOpen, navigate, openDialog]);

  const openEvidence = (origin: HTMLButtonElement) => {
    overlayStarted.current = performance.now();
    evidenceControl.current = origin;
    setEvidenceOpen(true);
    track("report.evidence_opened.v1", pageEvent(page, pageIndex, pages.length));
  };

  const openOverlay = (name: Exclude<DialogName, null>, event: string, origin?: HTMLElement) => {
    overlayStarted.current = performance.now();
    overlayOrigin.current = origin ?? document.activeElement as HTMLElement | null;
    setOpenDialog(name);
    track(event, pageEvent(page, pageIndex, pages.length));
  };

  const closeOverlay = (name: Exclude<DialogName, null>, event: string) => {
    if (openDialog !== name) return;
    setOpenDialog(null);
    track(event, {
      ...pageEvent(page, pageIndex, pages.length),
      overlay_duration_ms: roundedDuration(overlayStarted.current),
    });
    requestAnimationFrame(() => overlayOrigin.current?.focus());
  };

  const copyLink = async () => {
    const url = `${window.location.origin}${window.location.pathname}`;
    setCopyStatus("idle");
    try {
      await navigator.clipboard.writeText(url);
      setCopyStatus("copied");
      setFallbackUrl("");
      track("report.copy_link_completed.v1", pageEvent(page, pageIndex, pages.length));
    } catch {
      setCopyStatus("failed");
      setFallbackUrl(url);
      track("report.copy_link_failed.v1", pageEvent(page, pageIndex, pages.length));
    }
  };

  const readAgain = () => {
    track("report.read_again.v1", pageEvent(page, pageIndex, pages.length));
    leaveDirection.current = "read_again";
    setCopyStatus("idle");
    setDirection("backward");
    focusHeadingAfterNavigation.current = true;
    setPageIndex(0);
  };

  const confirmExit = () => {
    track("report.exit_confirmed.v1", pageEvent(page, pageIndex, pages.length));
    window.location.assign("/");
  };

  return (
    <main className={styles.story} data-direction={direction} data-nav-source={navSource}>
      <header className={styles.top}>
        <div
          className={styles.progress}
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={pages.length}
          aria-valuenow={pageIndex + 1}
          aria-valuetext={`Page ${pageIndex + 1} of ${pages.length}`}
          style={{ "--progress-count": pages.length, "--progress-done": pageIndex + 1 } as CSSProperties}
        >
          {pages.map((item, index) => (
            <span key={item.id} className={index <= pageIndex ? styles.progressDone : styles.progressTodo} />
          ))}
        </div>
        <button className={styles.textControl} type="button" onClick={(event) => openOverlay("exit", "report.exit_prompted.v1", event.currentTarget)}>Exit</button>
      </header>

      <section
        className={styles.viewport}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onPointerCancel={() => { pointerStart.current = null; }}
      >
        {/* The margin is outside the swapping content: it is the frame the
            investigation happens inside, and it never blinks between pages. */}
        <div className={styles.sheet}>
          <aside className={styles.margin} aria-hidden="true">
            <span className={styles.marginChapter} key={page.chapter}>{page.chapter}</span>
            <span className={styles.marginIndex}>{pad(pageIndex + 1)} / {pad(pages.length)}</span>
          </aside>
          <div
            className={styles.page}
            data-page-id={page.id}
            data-chapter={page.chapter}
            data-entrance={direction === "backward" ? "composed" : "staged"}
            data-voices={layout.ratio === null ? "one" : "two"}
            style={{ "--hairline-ratio": layout.ratio ?? 0 } as CSSProperties}
            key={page.id}
          >
            <PageContent
              page={page}
              layout={layout}
              headingRef={headingRef}
              reducedMotion={reducedMotion}
              exitOpen={openDialog === "exit"}
              receiptSettled={receiptSettled}
              copyStatus={copyStatus}
              fallbackUrl={fallbackUrl}
              evidenceOpen={evidenceOpen}
              onCopy={copyLink}
              onEvidence={openEvidence}
              onEvidenceClose={closeEvidence}
              onMethodology={(origin) => openOverlay("methodology", "report.methodology_opened.v1", origin)}
              onExit={(origin) => openOverlay("exit", "report.exit_prompted.v1", origin)}
              onReadAgain={readAgain}
              onScopeComplete={() => track("report.scope_sequence_completed.v1", pageEvent(page, pageIndex, pages.length))}
            />
          </div>
        </div>
      </section>

      <nav className={styles.edgeControls} aria-label="Story navigation">
        <button className={`${styles.edgeControl} ${styles.edgeBack}`} type="button" disabled={pageIndex === 0} onClick={(event) => navigate(-1, "backward", activationSource(event))}>Back</button>
        <button className={`${styles.edgeControl} ${styles.edgeNext}`} type="button" disabled={pageIndex === pages.length - 1} onClick={(event) => navigate(1, "forward", activationSource(event))}>Next</button>
      </nav>

      <NativeDialog open={openDialog === "methodology"} title="How this was measured" onClose={() => closeOverlay("methodology", "report.methodology_closed.v1")}>
        <Methodology report={report} />
      </NativeDialog>
      <NativeDialog open={openDialog === "exit"} title="Exit Dota DNA?" onClose={() => closeOverlay("exit", "report.exit_cancelled.v1")}>
        <p>Your place in this report won’t be saved.</p>
        <div className={styles.dialogActions}>
          <form method="dialog"><button className={styles.textControl}>Stay</button></form>
          <button className={styles.textControl} type="button" onClick={confirmExit}>Exit report</button>
        </div>
      </NativeDialog>
    </main>
  );
}

function PageContent({ page, layout, headingRef, reducedMotion, exitOpen, receiptSettled, copyStatus, fallbackUrl, evidenceOpen, onCopy, onEvidence, onEvidenceClose, onMethodology, onExit, onReadAgain, onScopeComplete }: {
  page: StoryPage;
  layout: ChapterLayout;
  headingRef: RefObject<HTMLHeadingElement>;
  reducedMotion: boolean;
  exitOpen: boolean;
  receiptSettled: MutableRefObject<boolean>;
  copyStatus: "idle" | "copied" | "failed";
  fallbackUrl: string;
  evidenceOpen: boolean;
  onCopy: () => void;
  onEvidence: (origin: HTMLButtonElement) => void;
  onEvidenceClose: () => void;
  onMethodology: (origin: HTMLElement) => void;
  onExit: (origin: HTMLElement) => void;
  onReadAgain: () => void;
  onScopeComplete: () => void;
}) {
  if (page.kind === "scope" && page.scope) {
    return <ScopeReceipt page={page} reducedMotion={reducedMotion} exitOpen={exitOpen} settled={receiptSettled} onComplete={onScopeComplete} headingRef={headingRef} />;
  }

  const leadHero = page.id === "lead-hero" ? page.heroRows?.[0] : undefined;
  const askedQuestion = layout.question && page.subtitle ? page.subtitle : undefined;
  const observedLine = !askedQuestion && page.subtitle && page.id !== "lead-hero" ? page.subtitle : undefined;
  // Coherence is the one page whose subject is the relationship between findings
  // already read. Its referenced findings compose the observation band directly
  // instead of hiding one layer down.
  const convergingRows = page.id === "coherence" ? page.evidence?.rows ?? [] : [];
  const signatureSlots = page.id === "signature-reveal" ? dedupeSignatureSlots(page) : page.slots;
  const showEvidence = Boolean(page.evidence) && page.id !== "coherence";

  const support = (
    <div className={styles.voiceObservation} style={step(STEP.SUPPORT)}>
      {observedLine && <p className={styles.observed}>{observedLine}</p>}
      {leadHero && <p className={styles.heroMetric}>
        <OdometerNumber value={leadHero.match_count ?? 0} suffix=" matches" />
        <span aria-hidden="true"> · </span>
        <OdometerNumber value={Math.round((leadHero.share ?? 0) * 100)} suffix="% of the year" />
      </p>}
      {convergingRows.length > 0 && <ul className={styles.converging}>
        {convergingRows.map((row, index) => <li key={row} style={rowStep(index)}>{row}</li>)}
      </ul>}
      {page.description?.map((line) => <p key={line} className={styles.interpreted}>{line}</p>)}
      {page.heroRows && page.id !== "lead-hero" && <HeroRows rows={page.heroRows} />}
      {page.bands && <PoolBands bands={page.bands} />}
      {page.timeline && <Timeline rows={page.timeline} />}
      {signatureSlots && signatureSlots.length > 0 && <SignatureSlots slots={signatureSlots} />}
      {page.kind === "share" && page.share && <ShareSummary summary={page.share} subtitle={page.subtitle} copyStatus={copyStatus} fallbackUrl={fallbackUrl} onCopy={onCopy} />}
      {page.kind === "end" && <div className={styles.endActions}>
        <button className={styles.textControl} type="button" onClick={onReadAgain}>Read again</button>
        <button className={styles.textControl} type="button" onClick={(event) => onExit(event.currentTarget)}>Exit</button>
        <button className={styles.textControl} type="button" onClick={(event) => onMethodology(event.currentTarget)}>How this was measured</button>
      </div>}
      {showEvidence && page.evidence && <EvidenceDisclosure evidence={page.evidence} open={evidenceOpen} onOpen={onEvidence} onClose={onEvidenceClose} />}
    </div>
  );

  return (
    <>
      {page.bridge && <p className={styles.bridge} style={step(STEP.BRIDGE)}>{page.bridge}</p>}
      <div className={styles.bands}>
        <div className={styles.voiceInterpretation} style={step(STEP.LEAD)}>
          {page.eyebrow && normalizeSentence(page.eyebrow) !== normalizeSentence(page.chapter) && <p className={styles.eyebrow}>{page.eyebrow}</p>}
          {askedQuestion && <p className={styles.question}>{askedQuestion}</p>}
          <h1 className={styles.headline} ref={headingRef} tabIndex={-1}>{page.headline}</h1>
          {page.id === "signature-reveal" && page.slots?.[0]?.scope && <p className={styles.slotScope}>{page.slots[0].scope}</p>}
        </div>
        {layout.ratio !== null && <span className={styles.hairline} style={step(STEP.HAIRLINE)} aria-hidden="true" />}
        {support}
      </div>
    </>
  );
}

/**
 * The Signature headline is the primary slot. When the server sends the same
 * sentence in both places, the duplicate render is omitted and its scope is
 * attached to the headline instead. Nothing is invented and no other slot is
 * touched; if the two differ, both are shown.
 */
function dedupeSignatureSlots(page: StoryPage): StoryPage["slots"] {
  const slots = page.slots;
  if (!slots?.length) return slots;
  const headline = normalizeSentence(page.headline);
  return slots.filter((slot, index) => !(index === 0 && normalizeSentence(slot.text ?? "") === headline));
}

function normalizeSentence(value: string): string {
  return value.toLowerCase().replace(/[\s.,;:!?’'"]+/g, " ").trim();
}

function step(delay: number): CSSProperties {
  return { "--enter-delay": `${delay}ms` } as CSSProperties;
}

function rowStep(index: number): CSSProperties {
  return { "--enter-delay": `${STEP.SUPPORT + Math.min(index, MAX_STAGGERED_ROWS) * ROW_STAGGER}ms` } as CSSProperties;
}

function ScopeReceipt({ page, reducedMotion, exitOpen, settled, onComplete, headingRef }: { page: StoryPage; reducedMotion: boolean; exitOpen: boolean; settled: MutableRefObject<boolean>; onComplete: () => void; headingRef: RefObject<HTMLHeadingElement> }) {
  const heroCount = page.scope?.heroCount ?? 0;
  const facts = useMemo(() => {
    const rows = [
      { value: 365, suffix: " days", subtitle: "of Dota", direction: "forward" as Direction },
      { value: page.scope?.matches ?? 0, suffix: " matches", subtitle: "made the cut", direction: "backward" as Direction },
      { value: 7, suffix: " signals", subtitle: "did the measuring", direction: "forward" as Direction },
    ];
    if (heroCount > 0) rows.push({ value: heroCount, suffix: " most-played heroes", subtitle: "give us somewhere familiar to start", direction: "backward" as Direction });
    return rows;
  }, [heroCount, page.scope?.matches]);
  const finalStage = facts.length - 1;
  // A receipt accumulates. Returning to it shows the completed list rather than
  // performing the sequence again.
  const startStage = reducedMotion || settled.current ? finalStage : 0;
  const [stage, setStage] = useState(startStage);
  const [paused, setPaused] = useState(false);
  const completed = useRef(false);
  const onCompleteRef = useRef(onComplete);
  const pauseReasons = useRef(new Set<string>());
  const scheduler = useRef({ pause: () => {}, resume: () => {} });
  const pressedPointer = useRef<number | null>(null);
  onCompleteRef.current = onComplete;

  const setPauseReason = useCallback((reason: string, active: boolean) => {
    const wasPaused = pauseReasons.current.size > 0;
    if (active) pauseReasons.current.add(reason);
    else pauseReasons.current.delete(reason);
    const isPaused = pauseReasons.current.size > 0;
    if (!wasPaused && isPaused) scheduler.current.pause();
    if (wasPaused && !isPaused) scheduler.current.resume();
    setPaused(isPaused);
  }, []);

  useEffect(() => {
    if (reducedMotion || settled.current) {
      setStage(finalStage);
      // The completion event belongs to the sequence, not to this mount, so a
      // return visit to a settled receipt must not fire it again.
      if (!settled.current && !completed.current) onCompleteRef.current();
      settled.current = true;
      completed.current = true;
      return;
    }
    const steps: Array<{ after: number; stage: number | null }> = [];
    for (let index = 1; index <= finalStage; index += 1) steps.push({ after: index === 3 ? 1_500 : 1_300, stage: index });
    steps.push({ after: 900, stage: null });
    let index = 0;
    let remaining = steps[0].after;
    let startedAt = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const run = () => {
      if (pauseReasons.current.size || index >= steps.length) return;
      startedAt = performance.now();
      timer = setTimeout(() => {
        timer = null;
        const current = steps[index];
        if (current.stage === null) {
          if (!settled.current && !completed.current) onCompleteRef.current();
          settled.current = true;
          completed.current = true;
        } else setStage(current.stage);
        index += 1;
        if (index < steps.length) {
          remaining = steps[index].after;
          run();
        }
      }, remaining);
    };
    scheduler.current = {
      pause: () => {
        if (!timer) return;
        remaining = Math.max(0, remaining - (performance.now() - startedAt));
        clearTimeout(timer);
        timer = null;
      },
      resume: run,
    };
    run();
    return () => { if (timer) clearTimeout(timer); };
  }, [finalStage, reducedMotion, settled]);

  useEffect(() => {
    const onVisibility = () => setPauseReason("hidden", document.hidden);
    onVisibility();
    document.addEventListener("visibilitychange", onVisibility);
    return () => document.removeEventListener("visibilitychange", onVisibility);
  }, [setPauseReason]);

  useEffect(() => setPauseReason("exit", exitOpen), [exitOpen, setPauseReason]);

  const releasePointer = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (pressedPointer.current !== event.pointerId) return;
    pressedPointer.current = null;
    setPauseReason("pointer", false);
  };

  const pressPointer = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (event.clientX <= EDGE_WIDTH || event.clientX >= window.innerWidth - EDGE_WIDTH) return;
    pressedPointer.current = event.pointerId;
    event.currentTarget.setPointerCapture(event.pointerId);
    setPauseReason("pointer", true);
  };

  const holdWithSpace = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.code !== "Space" || event.repeat) return;
    event.preventDefault();
    setPauseReason("keyboard", true);
  };

  const releaseSpace = (event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (event.code !== "Space") return;
    event.preventDefault();
    setPauseReason("keyboard", false);
  };

  const visibleStage = Math.min(stage, finalStage);
  const showHint = !reducedMotion && visibleStage === 0 && !settled.current;

  return <div
    className={styles.receipt}
    data-receipt-stage={visibleStage}
    data-paused={paused ? "true" : "false"}
    tabIndex={0}
    role="group"
    aria-describedby="receipt-instructions"
    onPointerDown={pressPointer}
    onPointerUp={releasePointer}
    onPointerCancel={releasePointer}
    onLostPointerCapture={releasePointer}
    onKeyDown={holdWithSpace}
    onKeyUp={releaseSpace}
    onBlur={() => setPauseReason("keyboard", false)}
  >
    <span id="receipt-instructions" className={styles.srOnly}>Press and hold the centre, or hold Space, to pause this receipt.</span>
    <span className={styles.srOnly} aria-live="polite">Receipt {paused ? "paused" : "playing"}.</span>
    <ol className={styles.receiptLines}>
      {facts.slice(0, visibleStage + 1).map((fact, index) => (
        <li key={fact.subtitle} className={styles.receiptLine} data-latest={index === visibleStage ? "true" : "false"}>
          {index === 0
            ? <h1 ref={headingRef} tabIndex={-1}><OdometerNumber value={fact.value} suffix={fact.suffix} direction={fact.direction} delay={350} /></h1>
            : <p className={styles.receiptValue}><OdometerNumber value={fact.value} suffix={fact.suffix} direction={fact.direction} /></p>}
          <p className={styles.receiptCaption}>{fact.subtitle}</p>
          {index === 2 && <ul className={styles.signals}>{SIGNAL_LABELS.map((label, position) => <li key={label} style={{ "--signal-index": position } as CSSProperties}>{label}</li>)}</ul>}
        </li>
      ))}
    </ol>
    {showHint && <p className={styles.receiptHint}>Hold to pause</p>}
  </div>;
}

function HeroRows({ rows }: { rows: NonNullable<StoryPage["heroRows"]> }) {
  return <ul className={styles.rows}>{rows.map((row, index) => <li style={rowStep(index)} key={`${row.display_name ?? row.hero_name ?? row.name}-${index}`}><strong>{row.display_name ?? row.hero_name ?? row.name}</strong><span><OdometerNumber value={row.match_count ?? 0} suffix=" matches" /> <span aria-hidden="true">·</span> <OdometerNumber value={Math.round((row.share ?? 0) * 100)} suffix="%" /></span></li>)}</ul>;
}

function PoolBands({ bands }: { bands: NonNullable<StoryPage["bands"]> }) {
  return <div className={styles.bandRows}>{bands.filter((band) => band.rows.length).map((band, index) => <section style={rowStep(index)} key={band.label}><h2>{band.label}</h2><p>{band.rows.map((row) => row.display_name ?? row.hero_name ?? row.name).join(", ")}</p></section>)}</div>;
}

function Timeline({ rows }: { rows: NonNullable<StoryPage["timeline"]> }) {
  return <ol className={styles.rows}>{rows.map((row, index) => <li style={rowStep(index)} key={row.id ?? `${row.label}-${index}`}><strong>{row.label}</strong><span>{row.summary ?? row.evidence ?? row.period}</span></li>)}</ol>;
}

function SignatureSlots({ slots }: { slots: NonNullable<StoryPage["slots"]> }) {
  return <div className={styles.slots}>{slots.map((slot, index) => <section style={rowStep(index + 1)} key={slot.kind}><h2>{titleCase(slot.kind ?? "Signal")}</h2><p>{slot.text}</p>{slot.scope && <small>{slot.scope}</small>}</section>)}</div>;
}

function OdometerNumber({ value, suffix = "", direction = "forward", delay = 0 }: { value: number; suffix?: string; direction?: Direction; delay?: number }) {
  const target = String(Math.max(0, Math.round(value)));
  // Digits are revealed behind a mask instead of cycled through a wheel, so no
  // value other than the settled one is ever legible. The unit follows the last
  // digit, so a number is never readable next to a unit it does not yet equal.
  const settleDelay = delay + (target.length - 1) * DIGIT_STAGGER + DIGIT_REVEAL;
  return <span className={styles.odometer} aria-label={`${target}${suffix}`} data-odometer-value={target}>
    <span className={styles.odometerDigits} aria-hidden="true" style={{ "--digit-count": target.length } as CSSProperties}>
      {target.split("").map((digit, index) => (
        <span className={styles.odometerColumn} key={`${index}-${digit}-${direction}`}>
          <span
            className={`${styles.odometerTrack} ${direction === "backward" ? styles.odometerDown : styles.odometerUp}`}
            style={{ "--digit-delay": `${delay + index * DIGIT_STAGGER}ms` } as CSSProperties}
          >{digit}</span>
        </span>
      ))}
    </span>
    {suffix && <span className={styles.odometerSuffix} aria-hidden="true" key={suffix} style={{ "--suffix-delay": `${settleDelay}ms` } as CSSProperties}>{suffix}</span>}
  </span>;
}

function ShareSummary({ summary, subtitle, copyStatus, fallbackUrl, onCopy }: { summary: NonNullable<StoryPage["share"]>; subtitle?: string; copyStatus: "idle" | "copied" | "failed"; fallbackUrl: string; onCopy: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { if (copyStatus === "failed") inputRef.current?.select(); }, [copyStatus]);
  // The Signature line belongs to this page once. When the page subtitle already
  // carries it, the summary does not repeat it.
  const repeatsSubtitle = Boolean(summary.signature && subtitle && normalizeSentence(summary.signature) === normalizeSentence(subtitle));
  return <div className={styles.shareSummary}>
    <h2>{summary.displayName}</h2>
    {summary.signature && !repeatsSubtitle && <p className={styles.shareSignature}>{summary.signature}</p>}
    {summary.findings.length > 0 && <ul className={styles.shareFindings}>{summary.findings.map((finding, index) => <li key={finding} style={rowStep(index)}>{finding}</li>)}</ul>}
    <p className={styles.shareCaption}>
      {summary.heroes.length > 0 && <span>{summary.heroes.join(" · ")}</span>}
      <span>{SIGNAL_LABELS.join(" · ")}</span>
    </p>
    <button className={styles.primaryControl} type="button" onClick={onCopy}>Copy report link</button>
    <p className={styles.copyStatus} key={copyStatus} role="status" aria-live="polite">{copyStatus === "copied" && "Report link copied."}{copyStatus === "failed" && "Couldn’t copy the link. Select it below."}</p>
    {copyStatus === "failed" && <input ref={inputRef} className={styles.urlFallback} value={fallbackUrl} readOnly aria-label="Report URL" />}
  </div>;
}

/**
 * Evidence sits one layer beneath the story, not in a window on top of it. The
 * disclosure expands inside the observation band it belongs to, so it inherits
 * the claim's context by construction and closing it restores orientation for
 * free — nothing moved.
 */
function EvidenceDisclosure({ evidence, open, onOpen, onClose }: { evidence: EvidenceModel; open: boolean; onOpen: (origin: HTMLButtonElement) => void; onClose: () => void }) {
  const panelRef = useRef<HTMLDivElement>(null);
  useEffect(() => { if (open) panelRef.current?.focus(); }, [open]);
  return <div className={styles.evidence}>
    <button
      className={styles.evidenceControl}
      type="button"
      aria-expanded={open}
      aria-controls="evidence-panel"
      style={step(STEP.EVIDENCE)}
      onClick={(event) => (open ? onClose() : onOpen(event.currentTarget))}
    >Why this?</button>
    {open && <div className={styles.evidencePanel} id="evidence-panel" ref={panelRef} tabIndex={-1} role="region" aria-label="Why this?">
      {evidence.statement && <p className={styles.evidenceStatement}>{evidence.statement}</p>}
      <p className={styles.evidenceCounts}>
        {typeof evidence.sampleSize === "number" && <span><OdometerNumber value={evidence.sampleSize} suffix=" comparable matches" /></span>}
        {typeof evidence.sessions === "number" && <span><OdometerNumber value={evidence.sessions} suffix=" sessions" /></span>}
      </p>
      {evidence.rows.length > 0 && <ul>{evidence.rows.map((row) => <li key={row}>{row}</li>)}</ul>}
      {evidence.alternatives.length > 0 && <section><h3>What else could explain it?</h3><ul>{evidence.alternatives.map((item) => <li key={item}>{item}</li>)}</ul></section>}
      {evidence.limitations.length > 0 && <section><h3>Limitations</h3><ul>{evidence.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>}
      <button className={styles.textControl} type="button" onClick={onClose}>Close evidence</button>
    </div>}
  </div>;
}

function Methodology({ report }: { report: V61Report }) {
  const versions = report.versions ?? {};
  const manifestRequests = report.reproducibility?.request_manifest?.physical_request_count;
  const historyRequests = report.cost?.history_requests ?? (typeof manifestRequests === "number" ? manifestRequests : undefined);
  return <div className={styles.dialogBody}>
    <section><h3>What we read</h3><p>A 365-day summary history with {report.metadata?.eligible_matches ?? 0} eligible matches from {report.metadata?.processed_matches ?? 0} history rows.</p>{typeof historyRequests === "number" && <p>{historyRequests} physical history request{historyRequests === 1 ? "" : "s"}.</p>}</section>
    <section><h3>What we did not read</h3><p>No match detail, replay, parse, rank, or MMR data.</p></section>
    <section><h3>How findings qualify</h3><p>Seven public signals feed five finding families. At most three findings are published. Sessions are the independent unit, and the server owns every evidence gate.</p></section>
    <section><h3>Versions</h3><dl className={styles.versions}>
      <div><dt>Report</dt><dd>{report.schema_version}</dd></div>
      <div><dt>Model</dt><dd>{versions.model ?? versions.behavior_model ?? "Not reported"}</dd></div>
      <div><dt>Copy</dt><dd>{versions.copy ?? versions.semantic_copy ?? "Not reported"}</dd></div>
      <div><dt>Methodology</dt><dd>{String(report.methodology?.version ?? versions.methodology ?? versions.element_registry ?? "Not reported")}</dd></div>
    </dl></section>
  </div>;
}

function NativeDialog({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: ReactNode }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      requestAnimationFrame(() => headingRef.current?.focus());
    } else if (!open && dialog.open) dialog.close();
  }, [open]);
  return <dialog className={styles.dialog} ref={dialogRef} onClose={onClose}>
    <div className={styles.dialogHeader}><h2 ref={headingRef} tabIndex={-1}>{title}</h2><form method="dialog"><button className={styles.textControl} aria-label="Close dialog">Close</button></form></div>
    {children}
  </dialog>;
}

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReduced(query.matches);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return reduced;
}

function usePageAnalytics(page: StoryPage, index: number, total: number, reducedMotion: boolean, leaveDirection: MutableRefObject<string>) {
  useEffect(() => {
    const started = performance.now();
    let hiddenAt = document.hidden ? started : 0;
    let hiddenDuration = 0;
    const visibility = () => {
      if (document.hidden && !hiddenAt) hiddenAt = performance.now();
      if (!document.hidden && hiddenAt) { hiddenDuration += performance.now() - hiddenAt; hiddenAt = 0; }
    };
    document.addEventListener("visibilitychange", visibility);
    track("report.story_page_viewed.v1", { ...pageEvent(page, index, total), reduced_motion: reducedMotion, result_status: page.evidence ? "supported" : "descriptive" });
    return () => {
      document.removeEventListener("visibilitychange", visibility);
      if (hiddenAt) hiddenDuration += performance.now() - hiddenAt;
      // eslint-disable-next-line react-hooks/exhaustive-deps -- cleanup needs the direction that triggered this page change.
      track("report.story_page_left.v1", { ...pageEvent(page, index, total), direction: leaveDirection.current, dwell_ms: Math.max(0, Math.round((performance.now() - started - hiddenDuration) / 100) * 100) });
    };
  }, [index, page, reducedMotion, total, leaveDirection]);
}

function pageEvent(page: StoryPage, index: number, total: number) {
  return { schema: "free-dna-report-6.1.0", page_id: page.id, chapter: page.chapter, page_index: index + 1, page_total: total };
}
// A click synthesised by Enter/Space reports detail 0; a real pointer click does not.
function activationSource(event: { detail: number }): NavSource {
  return event.detail === 0 ? "keyboard" : "pointer";
}
function pad(value: number): string { return String(value).padStart(2, "0"); }
function roundedDuration(started: number): number { return Math.max(0, Math.round((performance.now() - started) / 100) * 100); }
function titleCase(value: string): string { return value.toLowerCase().replace(/(^|_)([a-z])/g, (_match, prefix, letter) => `${prefix ? " " : ""}${letter.toUpperCase()}`); }

export function UnsupportedReport() {
  return <main className={styles.stateShell}><h1>This report can’t open here.</h1><p>It uses an older Dota DNA format. Generate a new report to continue.</p><Link className={styles.primaryControl} href="/">Generate new report</Link></main>;
}
