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
type DialogName = "evidence" | "methodology" | "exit" | null;
type PointerStart = { x: number; y: number; target: EventTarget | null; selectionActive: boolean };

const TRANSITION_DURATION = 280;
const DIGIT_REVEAL = 460;
const DIGIT_STAGGER = 65;
const EDGE_WIDTH = 56;
const DRAG_THRESHOLD = 12;
const INTERACTIVE_SELECTOR = "button, a, input, textarea, select, dialog, [contenteditable='true']";

export default function ReportStoryV6({ report }: { report: V61Report }) {
  const pages = useMemo(() => buildStoryPages(report), [report]);
  const reducedMotion = useReducedMotion();
  const [pageIndex, setPageIndex] = useState(0);
  const [direction, setDirection] = useState<Direction>("forward");
  const [phase, setPhase] = useState<"visible" | "leaving" | "entering">("visible");
  const [openDialog, setOpenDialog] = useState<DialogName>(null);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied" | "failed">("idle");
  const [fallbackUrl, setFallbackUrl] = useState("");
  const transitionTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pointerStart = useRef<PointerStart | null>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const overlayStarted = useRef(0);
  const overlayOrigin = useRef<HTMLElement | null>(null);
  const leaveDirection = useRef<string>("exit");
  const targetIndex = useRef(0);
  const [navSource, setNavSource] = useState<NavSource>("pointer");
  const page = pages[pageIndex];

  usePageAnalytics(page, pageIndex, pages.length, reducedMotion, leaveDirection);

  useEffect(() => () => {
    if (transitionTimer.current) clearTimeout(transitionTimer.current);
  }, []);

  useEffect(() => { targetIndex.current = pageIndex; }, [pageIndex]);

  // A press always advances the story. While a transition is in flight the target
  // moves instead of the timer restarting, so presses faster than the transition
  // duration coalesce into one landing rather than starving the commit.
  const navigate = useCallback((step: number, nextDirection: Direction, source: NavSource = "pointer") => {
    const inFlight = transitionTimer.current !== null;
    const base = inFlight ? targetIndex.current : pageIndex;
    const nextIndex = base + step;
    if (nextIndex < 0 || nextIndex >= pages.length || nextIndex === base) return;
    targetIndex.current = nextIndex;
    leaveDirection.current = nextDirection;
    setNavSource(source);
    setDirection(nextDirection);
    if (inFlight) return;
    setPhase(reducedMotion ? "entering" : "leaving");
    const finish = () => {
      transitionTimer.current = null;
      const landing = targetIndex.current;
      setPageIndex(landing);
      setPhase("entering");
      requestAnimationFrame(() => {
        setPhase("visible");
        headingRef.current?.focus({ preventScroll: true });
        track("report.story_transition_completed.v1", {
          page_id: pages[landing].id,
          direction: nextDirection,
          transition_duration_ms: reducedMotion ? 0 : TRANSITION_DURATION,
          reduced_motion: reducedMotion,
        });
      });
    };
    if (reducedMotion) finish();
    else transitionTimer.current = setTimeout(finish, TRANSITION_DURATION);
  }, [pageIndex, pages, reducedMotion]);

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

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (openDialog || event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, button, a, [contenteditable='true']")) return;
      if (event.key === "ArrowRight") navigate(1, "forward", "keyboard");
      if (event.key === "ArrowLeft") navigate(-1, "backward", "keyboard");
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [navigate, openDialog]);

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
    if (transitionTimer.current) { clearTimeout(transitionTimer.current); transitionTimer.current = null; }
    targetIndex.current = 0;
    setCopyStatus("idle");
    setDirection("backward");
    setPageIndex(0);
    setPhase("entering");
    requestAnimationFrame(() => {
      setPhase("visible");
      headingRef.current?.focus({ preventScroll: true });
    });
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
        <div className={`${styles.page} ${styles[phase]} ${styles[page.layout]}`} data-page-id={page.id} key={page.id}>
          <PageContent
            page={page}
            headingRef={headingRef}
            reducedMotion={reducedMotion}
            exitOpen={openDialog === "exit"}
            copyStatus={copyStatus}
            fallbackUrl={fallbackUrl}
            onCopy={copyLink}
            onEvidence={(origin) => openOverlay("evidence", "report.evidence_opened.v1", origin)}
            onMethodology={(origin) => openOverlay("methodology", "report.methodology_opened.v1", origin)}
            onExit={(origin) => openOverlay("exit", "report.exit_prompted.v1", origin)}
            onReadAgain={readAgain}
            onScopeComplete={() => track("report.scope_sequence_completed.v1", pageEvent(page, pageIndex, pages.length))}
          />
        </div>
      </section>

      <nav className={styles.edgeControls} aria-label="Story navigation">
        <button className={`${styles.edgeControl} ${styles.edgeBack}`} type="button" disabled={pageIndex === 0} onClick={(event) => navigate(-1, "backward", activationSource(event))}>Back</button>
        <button className={`${styles.edgeControl} ${styles.edgeNext}`} type="button" disabled={pageIndex === pages.length - 1} onClick={(event) => navigate(1, "forward", activationSource(event))}>Next</button>
      </nav>

      <NativeDialog open={openDialog === "evidence"} title={page.evidence?.headline ?? "Why this?"} onClose={() => closeOverlay("evidence", "report.evidence_closed.v1")}>
        {openDialog === "evidence" && page.evidence && <Evidence evidence={page.evidence} />}
      </NativeDialog>
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

function PageContent({ page, headingRef, reducedMotion, exitOpen, copyStatus, fallbackUrl, onCopy, onEvidence, onMethodology, onExit, onReadAgain, onScopeComplete }: {
  page: StoryPage;
  headingRef: RefObject<HTMLHeadingElement>;
  reducedMotion: boolean;
  exitOpen: boolean;
  copyStatus: "idle" | "copied" | "failed";
  fallbackUrl: string;
  onCopy: () => void;
  onEvidence: (origin: HTMLElement) => void;
  onMethodology: (origin: HTMLElement) => void;
  onExit: (origin: HTMLElement) => void;
  onReadAgain: () => void;
  onScopeComplete: () => void;
}) {
  if (page.kind === "scope" && page.scope) return <ScopeReceipt page={page} reducedMotion={reducedMotion} exitOpen={exitOpen} onComplete={onScopeComplete} headingRef={headingRef} />;
  const leadHero = page.id === "lead-hero" ? page.heroRows?.[0] : undefined;
  return (
    <>
      {page.bridge && <p className={styles.bridge}>{page.bridge}</p>}
      <div className={styles.lead}>
        {page.eyebrow && <p className={styles.eyebrow}>{page.eyebrow}</p>}
        <h1 className={styles.headline} ref={headingRef} tabIndex={-1}>{page.headline}</h1>
        {page.subtitle && page.id !== "lead-hero" && <WordCascade text={page.subtitle} bridge={Boolean(page.bridge)} />}
      </div>
      <div className={styles.detail}>
        {leadHero && <p className={styles.heroMetric}>
          <OdometerNumber value={leadHero.match_count ?? 0} suffix=" matches" />
          <span aria-hidden="true"> · </span>
          <OdometerNumber value={Math.round((leadHero.share ?? 0) * 100)} suffix="% of the year" />
        </p>}
        {page.description?.map((line) => <p key={line}>{line}</p>)}
        {page.heroRows && page.id !== "lead-hero" && <HeroRows rows={page.heroRows} />}
        {page.bands && <PoolBands bands={page.bands} />}
        {page.timeline && <Timeline rows={page.timeline} />}
        {page.slots && <SignatureSlots slots={page.slots} />}
        {page.kind === "share" && page.share && <ShareSummary summary={page.share} copyStatus={copyStatus} fallbackUrl={fallbackUrl} onCopy={onCopy} />}
        {page.kind === "end" && <div className={styles.endActions}>
          <button className={styles.textControl} type="button" onClick={onReadAgain}>Read again</button>
          <button className={styles.textControl} type="button" onClick={(event) => onExit(event.currentTarget)}>Exit</button>
          <button className={styles.textControl} type="button" onClick={(event) => onMethodology(event.currentTarget)}>How this was measured</button>
        </div>}
      </div>
      {page.evidence && <button className={styles.evidenceButton} type="button" aria-label="Why this?" onClick={(event) => onEvidence(event.currentTarget)}>ⓘ</button>}
    </>
  );
}

function ScopeReceipt({ page, reducedMotion, exitOpen, onComplete, headingRef }: { page: StoryPage; reducedMotion: boolean; exitOpen: boolean; onComplete: () => void; headingRef: RefObject<HTMLHeadingElement> }) {
  const [stage, setStage] = useState(0);
  const [paused, setPaused] = useState(false);
  const completed = useRef(false);
  const onCompleteRef = useRef(onComplete);
  const pauseReasons = useRef(new Set<string>());
  const scheduler = useRef({ pause: () => {}, resume: () => {} });
  const pressedPointer = useRef<number | null>(null);
  const heroCount = page.scope?.heroCount ?? 0;
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
    if (reducedMotion) {
      if (!completed.current) onCompleteRef.current();
      completed.current = true;
      return;
    }
    const steps = heroCount
      ? [{ after: 2_200, stage: 1 }, { after: 1_850, stage: 2 }, { after: 2_800, stage: 3 }, { after: 1_800, stage: null }]
      : [{ after: 2_200, stage: 1 }, { after: 1_850, stage: 2 }, { after: 2_800, stage: null }];
    let index = 0;
    let remaining = steps[0].after;
    let startedAt = 0;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const run = () => {
      if (pauseReasons.current.size || index >= steps.length) return;
      startedAt = performance.now();
      timer = setTimeout(() => {
        timer = null;
        const step = steps[index];
        if (step.stage === null) {
          if (!completed.current) onCompleteRef.current();
          completed.current = true;
        } else setStage(step.stage);
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
  }, [heroCount, reducedMotion]);

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

  if (reducedMotion) return <div
    className={styles.receiptStatic}
    tabIndex={0}
    role="group"
    aria-describedby="receipt-instructions"
    data-paused={paused ? "true" : "false"}
    onPointerDown={pressPointer}
    onPointerUp={releasePointer}
    onPointerCancel={releasePointer}
    onLostPointerCapture={releasePointer}
    onKeyDown={holdWithSpace}
    onKeyUp={releaseSpace}
    onBlur={() => setPauseReason("keyboard", false)}
  >
    <span id="receipt-instructions" className={styles.srOnly}>Press and hold the center, or hold Space, to pause this receipt.</span>
    <span className={styles.srOnly} aria-live="polite">Receipt {paused ? "paused" : "playing"}.</span>
    <h1 ref={headingRef} tabIndex={-1}>365 days <small>of Dota</small></h1>
    <p><strong>{page.scope?.matches ?? 0} matches</strong><span>made the cut</span></p>
    <p><strong>7 signals</strong><span>did the measuring</span></p>
    <ul>{SIGNAL_LABELS.map((label) => <li key={label}>{label}</li>)}</ul>
    {heroCount > 0 && <p><strong>{heroCount} most-played heroes</strong><span>give us somewhere familiar to start</span></p>}
  </div>;
  const facts: Array<{ value: number; suffix: string; subtitle: string; direction: Direction }> = [
    { value: 365, suffix: " days", subtitle: "of Dota", direction: "forward" },
    { value: page.scope?.matches ?? 0, suffix: " matches", subtitle: "made the cut", direction: "backward" },
    { value: 7, suffix: " signals", subtitle: "did the measuring", direction: "forward" },
    { value: heroCount, suffix: " most-played heroes", subtitle: "give us somewhere familiar to start", direction: "backward" },
  ];
  const visibleStage = heroCount ? Math.min(stage, 3) : Math.min(stage, 2);
  const fact = facts[visibleStage];
  return <div
    className={`${styles.receipt} ${paused ? styles.receiptPaused : ""}`}
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
    <span id="receipt-instructions" className={styles.srOnly}>Press and hold the center, or hold Space, to pause this receipt.</span>
    <span className={styles.srOnly} aria-live="polite">Receipt {paused ? "paused" : "playing"}.</span>
    <h1 ref={headingRef} tabIndex={-1}>
      <OdometerNumber value={fact.value} suffix={fact.suffix} direction={fact.direction} delay={visibleStage === 0 ? 350 : 0} />
    </h1>
    <p key={`subtitle-${visibleStage}`} style={{ "--receipt-subtitle-delay": `${visibleStage === 0 ? 800 : 450}ms` } as CSSProperties}>{fact.subtitle}</p>
    {visibleStage === 2 && <ul>{SIGNAL_LABELS.map((label, index) => <li key={label} style={{ "--signal-index": index } as CSSProperties}>{label}</li>)}</ul>}
  </div>;
}

function HeroRows({ rows }: { rows: NonNullable<StoryPage["heroRows"]> }) {
  return <ul className={styles.rows}>{rows.map((row, index) => <li className={styles.stagedRow} style={{ "--row-index": index } as CSSProperties} key={`${row.display_name ?? row.hero_name ?? row.name}-${index}`}><strong>{row.display_name ?? row.hero_name ?? row.name}</strong><span><OdometerNumber value={row.match_count ?? 0} suffix=" matches" /> <span aria-hidden="true">·</span> <OdometerNumber value={Math.round((row.share ?? 0) * 100)} suffix="%" /></span></li>)}</ul>;
}

function PoolBands({ bands }: { bands: NonNullable<StoryPage["bands"]> }) {
  return <div className={styles.bands}>{bands.filter((band) => band.rows.length).map((band, index) => <section className={styles.stagedRow} style={{ "--row-index": index } as CSSProperties} key={band.label}><h2>{band.label}</h2><p>{band.rows.map((row) => row.display_name ?? row.hero_name ?? row.name).join(", ")}</p></section>)}</div>;
}

function Timeline({ rows }: { rows: NonNullable<StoryPage["timeline"]> }) {
  return <ol className={styles.rows}>{rows.map((row, index) => <li className={styles.stagedRow} style={{ "--row-index": index } as CSSProperties} key={row.id ?? `${row.label}-${index}`}><strong>{row.label}</strong><span>{row.summary ?? row.evidence ?? row.period}</span></li>)}</ol>;
}

function SignatureSlots({ slots }: { slots: NonNullable<StoryPage["slots"]> }) {
  return <div className={styles.slots}>{slots.map((slot, index) => <section className={styles.signatureRow} style={{ "--row-index": index } as CSSProperties} key={slot.kind}><h2>{titleCase(slot.kind ?? "Signal")}</h2><p>{slot.text}</p>{slot.scope && <small>{slot.scope}</small>}</section>)}</div>;
}

function WordCascade({ text, bridge }: { text: string; bridge: boolean }) {
  const words = text.split(/\s+/);
  const stagger = Math.min(55, 300 / Math.max(1, words.length - 1));
  const start = bridge ? 1_600 : 700;
  return <p className={styles.subtitle} aria-label={text}>
    {words.map((word, index) => <span
      aria-hidden="true"
      className={styles.subtitleWord}
      key={`${word}-${index}`}
      style={{ animationDelay: `${start + stagger * index}ms` }}
    >{word}{index < words.length - 1 ? "\u00a0" : ""}</span>)}
  </p>;
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

function ShareSummary({ summary, copyStatus, fallbackUrl, onCopy }: { summary: NonNullable<StoryPage["share"]>; copyStatus: "idle" | "copied" | "failed"; fallbackUrl: string; onCopy: () => void }) {
  const inputRef = useRef<HTMLInputElement>(null);
  useEffect(() => { if (copyStatus === "failed") inputRef.current?.select(); }, [copyStatus]);
  return <div className={styles.shareSummary}>
    <h2>{summary.displayName}</h2>
    {summary.signature && <p>{summary.signature}</p>}
    <p>{SIGNAL_LABELS.join(" · ")}</p>
    {summary.heroes.length > 0 && <p>{summary.heroes.join(" · ")}</p>}
    <ul>{summary.findings.map((finding) => <li key={finding}>{finding}</li>)}</ul>
    <button className={styles.primaryControl} type="button" onClick={onCopy}>Copy report link</button>
    <p className={styles.copyStatus} key={copyStatus} role="status" aria-live="polite">{copyStatus === "copied" && "Report link copied."}{copyStatus === "failed" && "Couldn’t copy the link. Select it below."}</p>
    {copyStatus === "failed" && <input ref={inputRef} className={styles.urlFallback} value={fallbackUrl} readOnly aria-label="Report URL" />}
  </div>;
}

function Evidence({ evidence }: { evidence: EvidenceModel }) {
  return <div className={styles.dialogBody}>
    {evidence.statement && <p>{evidence.statement}</p>}
    {typeof evidence.sampleSize === "number" && <p><OdometerNumber value={evidence.sampleSize} suffix=" comparable matches" /></p>}
    {typeof evidence.sessions === "number" && <p><OdometerNumber value={evidence.sessions} suffix=" sessions" /></p>}
    {evidence.rows.length > 0 && <ul>{evidence.rows.map((row) => <li key={row}>{row}</li>)}</ul>}
    {evidence.alternatives.length > 0 && <section><h3>What else could explain it?</h3><ul>{evidence.alternatives.map((item) => <li key={item}>{item}</li>)}</ul></section>}
    {evidence.limitations.length > 0 && <section><h3>Limitations</h3><ul>{evidence.limitations.map((item) => <li key={item}>{item}</li>)}</ul></section>}
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
function roundedDuration(started: number): number { return Math.max(0, Math.round((performance.now() - started) / 100) * 100); }
function titleCase(value: string): string { return value.toLowerCase().replace(/(^|_)([a-z])/g, (_match, prefix, letter) => `${prefix ? " " : ""}${letter.toUpperCase()}`); }

export function UnsupportedReport() {
  return <main className={styles.stateShell}><h1>This report can’t open here.</h1><p>It uses an older Dota DNA format. Generate a new report to continue.</p><Link className={styles.primaryControl} href="/">Generate new report</Link></main>;
}

export { isFreeDnaReportV6, isFreeDnaReportV61 } from "./types";
export type { V6Report, V61Report, V6StoryReport } from "./types";
