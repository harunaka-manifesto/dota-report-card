"use client";

import Link from "next/link";
import {
  type ReactNode,
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
type DialogName = "evidence" | "methodology" | "exit" | null;

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
  const headingRef = useRef<HTMLHeadingElement>(null);
  const overlayStarted = useRef(0);
  const overlayOrigin = useRef<HTMLElement | null>(null);
  const leaveDirection = useRef<string>("exit");
  const page = pages[pageIndex];

  usePageAnalytics(page, pageIndex, pages.length, reducedMotion, leaveDirection);

  useEffect(() => () => {
    if (transitionTimer.current) clearTimeout(transitionTimer.current);
  }, []);

  const navigate = useCallback((nextIndex: number, nextDirection: Direction) => {
    if (nextIndex < 0 || nextIndex >= pages.length || nextIndex === pageIndex) return;
    if (transitionTimer.current) clearTimeout(transitionTimer.current);
    leaveDirection.current = nextDirection;
    setDirection(nextDirection);
    setPhase(reducedMotion ? "entering" : "leaving");
    const finish = () => {
      setPageIndex(nextIndex);
      setPhase("entering");
      requestAnimationFrame(() => {
        setPhase("visible");
        headingRef.current?.focus({ preventScroll: true });
        track("report.story_transition_completed.v1", {
          page_id: pages[nextIndex].id,
          direction: nextDirection,
          transition_duration_ms: reducedMotion ? 0 : 160,
          reduced_motion: reducedMotion,
        });
      });
    };
    if (reducedMotion) finish();
    else transitionTimer.current = setTimeout(finish, 160);
  }, [pageIndex, pages, reducedMotion]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (openDialog || event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select, button, a, [contenteditable='true']")) return;
      if (event.key === "ArrowRight") navigate(pageIndex + 1, "forward");
      if (event.key === "ArrowLeft") navigate(pageIndex - 1, "backward");
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [navigate, openDialog, pageIndex]);

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
    <main className={styles.story} data-direction={direction}>
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

      <section className={styles.viewport}>
        <div className={`${styles.page} ${styles[phase]} ${styles[page.layout]}`} data-page-id={page.id} key={page.id}>
          <PageContent
            page={page}
            report={report}
            headingRef={headingRef}
            reducedMotion={reducedMotion}
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

      <nav className={styles.controls} aria-label="Story navigation">
        <button className={styles.textControl} type="button" disabled={pageIndex === 0} onClick={() => navigate(pageIndex - 1, "backward")}>Back</button>
        {pageIndex < pages.length - 1 && <button className={styles.textControl} type="button" onClick={() => navigate(pageIndex + 1, "forward")}>Next</button>}
      </nav>

      <NativeDialog open={openDialog === "evidence"} title={page.evidence?.headline ?? "Why this?"} onClose={() => closeOverlay("evidence", "report.evidence_closed.v1")}>
        {page.evidence && <Evidence evidence={page.evidence} />}
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

function PageContent({ page, report, headingRef, reducedMotion, copyStatus, fallbackUrl, onCopy, onEvidence, onMethodology, onExit, onReadAgain, onScopeComplete }: {
  page: StoryPage;
  report: V61Report;
  headingRef: React.RefObject<HTMLHeadingElement>;
  reducedMotion: boolean;
  copyStatus: "idle" | "copied" | "failed";
  fallbackUrl: string;
  onCopy: () => void;
  onEvidence: (origin: HTMLElement) => void;
  onMethodology: (origin: HTMLElement) => void;
  onExit: (origin: HTMLElement) => void;
  onReadAgain: () => void;
  onScopeComplete: () => void;
}) {
  if (page.kind === "scope" && page.scope) return <ScopeReceipt page={page} reducedMotion={reducedMotion} onComplete={onScopeComplete} headingRef={headingRef} />;
  return (
    <>
      {page.bridge && <p className={styles.bridge}>{page.bridge}</p>}
      <div className={styles.lead}>
        {page.eyebrow && <p className={styles.eyebrow}>{page.eyebrow}</p>}
        <h1 className={styles.headline} ref={headingRef} tabIndex={-1}>{page.headline}</h1>
        {page.subtitle && page.id !== "lead-hero" && <p className={styles.subtitle}>{page.subtitle}</p>}
      </div>
      <div className={styles.detail}>
        {page.id === "lead-hero" && page.subtitle && <p className={styles.heroMetric}>{page.subtitle}</p>}
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

function ScopeReceipt({ page, reducedMotion, onComplete, headingRef }: { page: StoryPage; reducedMotion: boolean; onComplete: () => void; headingRef: React.RefObject<HTMLHeadingElement> }) {
  const [stage, setStage] = useState(reducedMotion ? 4 : 0);
  const completed = useRef(false);
  const heroCount = page.scope?.heroCount ?? 0;
  useEffect(() => {
    if (reducedMotion) {
      if (!completed.current) onComplete();
      completed.current = true;
      return;
    }
    const times = heroCount ? [920, 1840, 2760, 3920] : [920, 1840, 2980];
    const timers = times.map((time, index) => setTimeout(() => {
      const next = index + 1;
      setStage(heroCount ? next : next === 3 ? 2 : next);
      if (index === times.length - 1 && !completed.current) {
        completed.current = true;
        onComplete();
      }
    }, time));
    return () => timers.forEach(clearTimeout);
  }, [heroCount, onComplete, reducedMotion]);
  if (reducedMotion) return <div className={styles.receiptStatic}>
    <h1 ref={headingRef} tabIndex={-1}>365 days <small>of Dota</small></h1>
    <p><strong>{page.scope?.matches ?? 0} matches</strong><span>made the cut</span></p>
    <p><strong>7 signals</strong><span>did the measuring</span></p>
    <ul>{SIGNAL_LABELS.map((label) => <li key={label}>{label}</li>)}</ul>
    {heroCount > 0 && <p><strong>{heroCount} most-played heroes</strong><span>give us somewhere familiar to start</span></p>}
  </div>;
  const facts = [
    ["365 days", "of Dota"],
    [`${page.scope?.matches ?? 0} matches`, "made the cut"],
    ["7 signals", "did the measuring"],
    [`${heroCount} most-played heroes`, "give us somewhere familiar to start"],
  ];
  const visibleStage = heroCount ? Math.min(stage, facts.length - 1) : Math.min(stage, 2);
  return <div className={styles.receipt} key={visibleStage}>
    <h1 ref={headingRef} tabIndex={-1}>{facts[visibleStage][0]}</h1>
    <p>{facts[visibleStage][1]}</p>
    {visibleStage === 2 && <ul>{SIGNAL_LABELS.map((label, index) => <li key={label} style={{ animationDelay: `${index * 80}ms` }}>{label}</li>)}</ul>}
  </div>;
}

function HeroRows({ rows }: { rows: NonNullable<StoryPage["heroRows"]> }) {
  return <ul className={styles.rows}>{rows.map((row, index) => <li key={`${row.display_name ?? row.hero_name ?? row.name}-${index}`}><strong>{row.display_name ?? row.hero_name ?? row.name}</strong><span>{row.match_count} matches · {Math.round((row.share ?? 0) * 100)}%</span></li>)}</ul>;
}

function PoolBands({ bands }: { bands: NonNullable<StoryPage["bands"]> }) {
  return <div className={styles.bands}>{bands.filter((band) => band.rows.length).map((band) => <section key={band.label}><h2>{band.label}</h2><p>{band.rows.map((row) => row.display_name ?? row.hero_name ?? row.name).join(", ")}</p></section>)}</div>;
}

function Timeline({ rows }: { rows: NonNullable<StoryPage["timeline"]> }) {
  return <ol className={styles.rows}>{rows.map((row, index) => <li key={row.id ?? `${row.label}-${index}`}><strong>{row.label}</strong><span>{row.summary ?? row.evidence ?? row.period}</span></li>)}</ol>;
}

function SignatureSlots({ slots }: { slots: NonNullable<StoryPage["slots"]> }) {
  return <div className={styles.slots}>{slots.map((slot) => <section key={slot.kind}><h2>{titleCase(slot.kind ?? "Signal")}</h2><p>{slot.text}</p>{slot.scope && <small>{slot.scope}</small>}</section>)}</div>;
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
    <p className={styles.copyStatus} role="status" aria-live="polite">{copyStatus === "copied" && "Report link copied."}{copyStatus === "failed" && "Couldn’t copy the link. Select it below."}</p>
    {copyStatus === "failed" && <input ref={inputRef} className={styles.urlFallback} value={fallbackUrl} readOnly aria-label="Report URL" />}
  </div>;
}

function Evidence({ evidence }: { evidence: EvidenceModel }) {
  return <div className={styles.dialogBody}>
    {evidence.statement && <p>{evidence.statement}</p>}
    {typeof evidence.sampleSize === "number" && <p>{evidence.sampleSize} comparable matches</p>}
    {typeof evidence.sessions === "number" && <p>{evidence.sessions} sessions</p>}
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

function usePageAnalytics(page: StoryPage, index: number, total: number, reducedMotion: boolean, leaveDirection: React.MutableRefObject<string>) {
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
function roundedDuration(started: number): number { return Math.max(0, Math.round((performance.now() - started) / 100) * 100); }
function titleCase(value: string): string { return value.toLowerCase().replace(/(^|_)([a-z])/g, (_match, prefix, letter) => `${prefix ? " " : ""}${letter.toUpperCase()}`); }

export function UnsupportedReport() {
  return <main className={styles.stateShell}><h1>This report can’t open here.</h1><p>It uses an older Dota DNA format. Generate a new report to continue.</p><Link className={styles.primaryControl} href="/">Generate new report</Link></main>;
}

export { isFreeDnaReportV6, isFreeDnaReportV61 } from "./types";
export type { V6Report, V61Report, V6StoryReport } from "./types";
