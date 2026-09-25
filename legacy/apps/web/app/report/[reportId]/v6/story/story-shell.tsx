"use client";

/**
 * The persistent frame.
 *
 * One shell owns the top rail, the story stage, and the navigation dock, so a
 * page change never flashes blank.  It also owns every piece of state that
 * must survive a page change: which beats are revealed, which pages have
 * already been read, and whether the archetype card has been turned.
 */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import { track } from "../../../../lib/analytics";
import type { ComposedStory } from "./compose";
import { COPY } from "./copy";
import { beatOffsets, MOTION, rhythmForPage, type BeatPlan } from "./motion";
import { StoryPageView } from "./pages";
import { BeatProvider } from "./story-runtime";
import styles from "./story.module.css";

type Direction = "forward" | "backward";
const EDGE_ZONE = 56;
const SWIPE_DISTANCE = 48;

export function StoryShell({ story, methodology }: { story: ComposedStory; methodology: React.ReactNode }) {
  const pages = story.pages;
  const reducedMotion = useReducedMotion();
  const [pageIndex, setPageIndex] = useState(0);
  const [direction, setDirection] = useState<Direction>("forward");
  const [beatState, setBeatState] = useState<{ pageId: string; revealed: number; plan: BeatPlan | null }>(() => ({
    pageId: pages[0]?.id ?? "",
    revealed: 0,
    plan: null,
  }));
  const [visited, setVisited] = useState<ReadonlySet<string>>(() => new Set<string>());
  const [archetypeRevealed, setArchetypeRevealed] = useState(false);
  // The hero-pool call resolves once and stays resolved, like the card.
  const [poolRevealed, setPoolRevealed] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const [paused, setPaused] = useState(false);

  const headingRef = useRef<HTMLHeadingElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const elapsed = useRef(0);
  const revealedRef = useRef(0);
  const keyboardOrigin = useRef(false);
  // WebKit does not focus a button on click, so `document.activeElement` is
  // not a reliable record of what opened a dialog.  Capture the control.
  const methodologyOrigin = useRef<HTMLElement | null>(null);
  const pointerStart = useRef<{ x: number; y: number } | null>(null);

  const page = pages[Math.min(pageIndex, Math.max(0, pages.length - 1))];

  // A new page resets the reveal during render, before the incoming page's
  // renderer registers its plan.  Doing this in an effect would race the
  // child effect and null the plan straight after it arrived.
  if (page && beatState.pageId !== page.id) {
    elapsed.current = 0;
    setBeatState({ pageId: page.id, revealed: 0, plan: null });
  }

  const alreadyRead = page ? visited.has(page.id) : false;
  const plan = beatState.plan;
  // Reduced motion and previously-read pages arrive fully composed: a joke or
  // statistic is never re-performed.
  const revealed = reducedMotion || alreadyRead ? Number.POSITIVE_INFINITY : beatState.revealed;
  const total = plan?.total ?? 0;
  // A page that is already fully composed — reduced motion, or one the reader
  // has read before — is complete the moment it mounts, before its renderer
  // has reported a plan.  Without this, the first forward action on such a
  // page is swallowed by the mid-reveal rule instead of advancing.
  const complete = revealed === Number.POSITIVE_INFINITY || (plan !== null && revealed >= total);
  revealedRef.current = revealed;

  const registerPlan = useCallback((next: BeatPlan) => {
    const rhythm = next.rhythm ?? rhythmForPage(page?.page ?? 0);
    setBeatState((current) =>
      current.plan &&
      current.plan.total === next.total &&
      current.plan.holdAfter === next.holdAfter &&
      current.plan.identityHoldAfter === next.identityHoldAfter &&
      current.plan.rhythm === rhythm
        ? current
        : { ...current, plan: { ...next, rhythm } },
    );
  }, [page?.page]);

  // Timers pause while the document is hidden or a dialog is open.
  useEffect(() => {
    const update = () => setPaused(document.hidden);
    document.addEventListener("visibilitychange", update);
    update();
    return () => document.removeEventListener("visibilitychange", update);
  }, []);

  const frozen = paused || methodologyOpen || evidenceOpen;
  const pageId = page?.id ?? "";

  useEffect(() => {
    if (plan === null || frozen || revealedRef.current === Number.POSITIVE_INFINITY) return;
    const offsets = beatOffsets(plan);
    const base = elapsed.current;
    const startedAt = performance.now();
    const timers = offsets.flatMap((offset, index) => {
      if (index < revealedRef.current) return [];
      return [
        setTimeout(
          () =>
            setBeatState((current) =>
              current.pageId === pageId && current.revealed < index + 1
                ? { ...current, revealed: index + 1 }
                : current,
            ),
          Math.max(0, offset - base),
        ),
      ];
    });
    return () => {
      elapsed.current = base + (performance.now() - startedAt);
      timers.forEach(clearTimeout);
    };
    // `revealed` is read through a ref on purpose: each tick re-enters through
    // the setter, and re-running on it would restart the whole schedule.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [plan, pageId, frozen]);

  useEffect(() => {
    if (!page) return;
    if (complete || revealed === Number.POSITIVE_INFINITY) {
      setVisited((current) => (current.has(page.id) ? current : new Set([...current, page.id])));
    }
  }, [complete, revealed, page]);

  const completeNow = useCallback(() => {
    setBeatState((current) => ({ ...current, revealed: Number.POSITIVE_INFINITY }));
    // The card is a page beat, not an exception to the mid-reveal rule.
    if (page?.page === 30) setArchetypeRevealed(true);
    headingRef.current?.focus({ preventScroll: true });
  }, [page?.page]);

  const navigate = useCallback(
    (nextIndex: number, nextDirection: Direction) => {
      if (evidenceOpen || nextIndex < 0 || nextIndex >= pages.length || nextIndex === pageIndex) return;
      setDirection(nextDirection);
      setEvidenceOpen(false);
      setPageIndex(nextIndex);
      track("report.story_transition_completed.v1", {
        page_id: pages[nextIndex].id,
        chapter: pages[nextIndex].chapterName,
        direction: nextDirection,
        reduced_motion: reducedMotion,
      });
      requestAnimationFrame(() => headingRef.current?.focus({ preventScroll: true }));
    },
    [evidenceOpen, pageIndex, pages, reducedMotion],
  );

  /**
   * The mid-reveal rule: the first forward action completes the current page,
   * the second advances.  This prevents skipping an unseen fact.
   */
  const forward = useCallback(() => {
    if (evidenceOpen) return;
    if (!complete && revealed !== Number.POSITIVE_INFINITY) {
      completeNow();
      return;
    }
    // Page 17's call is its own beat: a forward action may reveal it, but may
    // not both reveal it and leave the page.
    if (page?.page === 17 && story.heroPoolRevealRequired && !poolRevealed && !reducedMotion) {
      setPoolRevealed(true);
      return;
    }
    navigate(pageIndex + 1, "forward");
  }, [evidenceOpen, complete, revealed, completeNow, page?.page, story.heroPoolRevealRequired, poolRevealed, reducedMotion, navigate, pageIndex]);

  const backward = useCallback(() => navigate(pageIndex - 1, "backward"), [navigate, pageIndex]);

  const runItBack = useCallback(() => {
    track("report.run_it_back.v1", { page_id: page?.id ?? "", chapter: page?.chapterName ?? "" });
    setEvidenceOpen(false);
    setMethodologyOpen(false);
    setArchetypeRevealed(false);
    setPoolRevealed(false);
    setVisited(new Set<string>());
    setDirection("backward");
    setPageIndex(0);
    stageRef.current?.scrollTo({ top: 0 });
    requestAnimationFrame(() => headingRef.current?.focus({ preventScroll: true }));
  }, [page?.id, page?.chapterName]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (methodologyOpen || evidenceOpen || event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target as HTMLElement | null;
      // While a control has focus its own keys win; the story never steals them.
      if (target?.closest("input, textarea, select, button, a, [contenteditable='true']")) return;
      if (event.key === "ArrowRight" || event.key === "PageDown") {
        keyboardOrigin.current = true;
        event.preventDefault();
        forward();
      }
      if (event.key === "ArrowLeft" || event.key === "PageUp") {
        keyboardOrigin.current = true;
        event.preventDefault();
        backward();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [forward, backward, methodologyOpen, evidenceOpen]);

  useEffect(() => {
    if (!page) return;
    const started = performance.now();
    track("report.story_page_viewed.v1", {
      page_id: page.id,
      chapter: page.chapterName,
      page_index: pageIndex + 1,
      page_total: pages.length,
      reduced_motion: reducedMotion,
    });
    return () => {
      track("report.story_page_left.v1", {
        page_id: page.id,
        chapter: page.chapterName,
        dwell_ms: Math.max(0, Math.round((performance.now() - started) / 100) * 100),
      });
    };
  }, [page, pageIndex, pages.length, reducedMotion]);

  const gestureAllowed = (target: EventTarget | null): boolean => {
    const element = target as HTMLElement | null;
    if (!element) return false;
    if (element.closest("button, a, input, select, textarea, [role='region'], dialog")) return false;
    return (window.getSelection()?.toString().length ?? 0) === 0;
  };

  const onPointerDown = (event: ReactPointerEvent<HTMLDivElement>) => {
    keyboardOrigin.current = false;
    pointerStart.current = gestureAllowed(event.target) ? { x: event.clientX, y: event.clientY } : null;
  };

  const onPointerUp = (event: ReactPointerEvent<HTMLDivElement>) => {
    const start = pointerStart.current;
    pointerStart.current = null;
    if (!start || !gestureAllowed(event.target)) return;
    const dx = event.clientX - start.x;
    const dy = event.clientY - start.y;
    if (Math.abs(dx) >= SWIPE_DISTANCE && Math.abs(dx) >= Math.abs(dy) * 1.5) {
      if (dx < 0) forward();
      else backward();
      return;
    }
    if (Math.abs(dx) < 8 && Math.abs(dy) < 8) {
      const bounds = event.currentTarget.getBoundingClientRect();
      if (event.clientX - bounds.left <= EDGE_ZONE) backward();
      else if (bounds.right - event.clientX <= EDGE_ZONE) forward();
    }
  };

  const chapterTicks = useMemo(() => {
    const seen = new Set<number>();
    return pages
      .map((item, index) => ({ item, index }))
      .filter(({ item }) => {
        if (seen.has(item.chapter)) return false;
        seen.add(item.chapter);
        return true;
      });
  }, [pages]);

  if (!page) return null;

  const rhythm = plan?.rhythm ?? rhythmForPage(page.page);

  return (
    <main
      className={styles.story}
      data-direction={direction}
      data-alignment={page.alignment}
      data-rhythm={rhythm}
      data-keyboard={keyboardOrigin.current}
    >
      <header className={styles.rail}>
        <p className={styles.chapterLabel}>{page.chapterName}</p>
        <div
          className={styles.progress}
          role="progressbar"
          aria-valuemin={1}
          aria-valuemax={pages.length}
          aria-valuenow={pageIndex + 1}
          aria-valuetext={COPY.shell.progress(pageIndex + 1, pages.length)}
        >
          <span
            className={styles.progressFill}
            style={{ width: `${((pageIndex + 1) / pages.length) * 100}%` }}
          />
          {chapterTicks.map(({ item, index }) => (
            <span
              key={item.id}
              className={styles.progressTick}
              style={{ left: `${(index / pages.length) * 100}%` }}
            />
          ))}
        </div>
        <a className={styles.textControl} href="/">
          {COPY.shell.exit}
        </a>
      </header>

      <section
        className={styles.stage}
        ref={stageRef}
        onPointerDown={onPointerDown}
        onPointerUp={onPointerUp}
      >
        <div className={styles.chapterRule} data-chapter={page.chapter} aria-hidden="true" />
        <article className={styles.page} key={page.id} data-page={page.page}>
          <BeatProvider value={{ revealed, registerPlan, reducedMotion }}>
            <StoryPageView
              story={story}
              page={page}
              headingRef={headingRef}
              reducedMotion={reducedMotion}
              archetypeRevealed={archetypeRevealed}
              onRevealArchetype={() => setArchetypeRevealed(true)}
              poolRevealed={poolRevealed}
              onRevealPool={() => setPoolRevealed(true)}
              onRunItBack={runItBack}
              evidenceOpen={evidenceOpen}
              onToggleEvidence={() => setEvidenceOpen((open) => !open)}
              onShared={() => track("report.share_completed.v1", { channel: "web_share" })}
              onCopied={() => track("report.share_completed.v1", { channel: "copy_link" })}
              onShareFailed={() => track("report.share_failed.v1", { channel: "copy_link" })}
            />
          </BeatProvider>
        </article>
      </section>

      <nav className={styles.dock} aria-label="Story navigation">
        <button className={styles.textControl} type="button" onClick={backward} disabled={evidenceOpen || pageIndex === 0}>
          {COPY.shell.back}
        </button>
        <button
          className={styles.textControl}
          type="button"
          onClick={(event) => {
            methodologyOrigin.current = event.currentTarget;
            setMethodologyOpen(true);
          }}
        >
          {COPY.shell.methodology}
        </button>
        <button
          className={styles.textControl}
          type="button"
          onClick={forward}
          disabled={evidenceOpen || (pageIndex === pages.length - 1 && (complete || revealed === Number.POSITIVE_INFINITY))}
        >
          {COPY.shell.next}
        </button>
      </nav>

      <MethodologyDialog open={methodologyOpen} origin={methodologyOrigin} onClose={() => setMethodologyOpen(false)}>
        {methodology}
      </MethodologyDialog>
    </main>
  );
}

function MethodologyDialog({
  open,
  origin,
  onClose,
  children,
}: {
  open: boolean;
  origin: React.MutableRefObject<HTMLElement | null>;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const headingRef = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
      requestAnimationFrame(() => headingRef.current?.focus());
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);
  return (
    <dialog
      className={styles.dialog}
      ref={dialogRef}
      onClose={() => {
        onClose();
        // Some engines move focus themselves as the dialog closes, so restore
        // the opener on the next frame rather than synchronously.
        requestAnimationFrame(() => origin.current?.focus());
      }}
    >
      <div className={styles.dialogHeader}>
        <h2 ref={headingRef} tabIndex={-1}>
          {COPY.shell.methodology}
        </h2>
        <form method="dialog">
          <button className={styles.textControl} aria-label="Close">
            Close
          </button>
        </form>
      </div>
      <div className={styles.dialogBody}>{children}</div>
    </dialog>
  );
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

export { MOTION };
