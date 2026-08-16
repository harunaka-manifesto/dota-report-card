"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  DnaDimension,
  FreeDnaReportV1,
  StoryPageV1
} from "../../../../../../packages/api-client/src";
import { track } from "../../../lib/analytics";
import {
  DeepDiveTeaser,
  EvidenceReceipt,
  HeroPortraitCard,
  MethodologySheet,
  SectionIntro,
  Spectrum,
  StoryPage as StoryPageFrame
} from "../../../components/story/primitives";
import ShareControls from "../../../components/share/share-controls";

export type StoryReport = FreeDnaReportV1;

const entryPageKinds = new Set<StoryPageV1["kind"]>(["input", "player_found", "analysis"]);

export default function ReportStory({ report }: { report: StoryReport }) {
  // The API returns the complete state machine so a client can resume an
  // analysis, but a completed report must open on the actual report reveal.
  const pages = useMemo(
    () => (report.pages ?? []).filter((page) => !entryPageKinds.has(page.kind)),
    [report.pages]
  );
  const pageRefs = useRef<Record<string, HTMLElement | null>>({});
  const [activePage, setActivePage] = useState(pages[0]?.id ?? "");
  const [methodology, setMethodology] = useState<DnaDimension | null>(null);
  const startedAt = useRef<number>(Date.now());
  const activePageRef = useRef(activePage);
  const activeStartedAt = useRef<number>(Date.now());
  const activeElapsedMs = useRef(0);
  const hiddenRef = useRef(false);
  const exitedRef = useRef(false);
  const completedRef = useRef(false);
  const reducedMotion = useRef(false);

  const pageIndex = useCallback((id: string) => pages.findIndex((page) => page.id === id), [pages]);
  const dwellMs = () => activeElapsedMs.current + (
    hiddenRef.current ? 0 : Math.max(0, Date.now() - activeStartedAt.current)
  );

  useEffect(() => {
    document.documentElement.dataset.reportStory = "true";
    reducedMotion.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let stored: string | null = null;
    try {
      stored = sessionStorage.getItem(`dota-report-page:${report.report_id ?? "current"}`);
    } catch {
      // Resuming a page is an enhancement; private browsing may disable storage.
    }
    const fromHash = window.location.hash.slice(1);
    const target = pages.some((page) => page.id === stored)
      ? stored
      : pages.some((page) => page.id === fromHash)
        ? fromHash
        : pages[0]?.id;
    if (target) {
      activePageRef.current = target;
      setActivePage(target);
      window.requestAnimationFrame(() => pageRefs.current[target]?.scrollIntoView({ block: "start", behavior: "auto" }));
    }

    const reportStartedAt = startedAt.current;
    const trackViewed = (id: string, previous: string | null, dwell: number) => {
      const ordinal = pageIndex(id);
      track("report.page_viewed.v1", {
        page: id,
        page_kind: pages[ordinal]?.kind ?? "unknown",
        ordinal,
        previous_page: previous,
        dwell_bucket: Math.floor(dwell / 5000) * 5,
        direction: previous === null || ordinal >= pageIndex(previous) ? "forward" : "backward"
      });
      if (pages[ordinal]?.kind === "deep_dive") {
        track("deep_dive.teaser_viewed.v1", { page: id });
      }
    };
    const trackExited = () => {
      if (exitedRef.current || !activePageRef.current) return;
      exitedRef.current = true;
      track("report.page_exited.v1", {
        page: activePageRef.current,
        page_kind: pages[pageIndex(activePageRef.current)]?.kind ?? "unknown",
        dwell_bucket: Math.floor(dwellMs() / 5000) * 5
      });
    };
    const transitionTo = (id: string) => {
      if (id === activePageRef.current) return;
      const previous = activePageRef.current;
      const dwell = dwellMs();
      track("report.page_exited.v1", {
        page: previous,
        page_kind: pages[pageIndex(previous)]?.kind ?? "unknown",
        next_page: id,
        dwell_bucket: Math.floor(dwell / 5000) * 5
      });
      activeElapsedMs.current = 0;
      activeStartedAt.current = Date.now();
      activePageRef.current = id;
      setActivePage(id);
      try {
        sessionStorage.setItem(`dota-report-page:${report.report_id ?? "current"}`, id);
      } catch {
        // Ignore storage failures; the report remains fully navigable.
      }
      window.history.replaceState(null, "", `#${id}`);
      trackViewed(id, previous, dwell);
    };
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting || entry.intersectionRatio < 0.55) continue;
        const id = entry.target.getAttribute("data-page-id");
        if (!id) continue;
        transitionTo(id);
        if (id === pages.at(-1)?.id && !completedRef.current) {
          completedRef.current = true;
          track("report.completed.v1", {
            elapsed_bucket: Math.floor((Date.now() - reportStartedAt) / 10000) * 10,
            page_count: pages.length
          });
        }
      }
    }, { threshold: [0.55, 0.8] });

    Object.values(pageRefs.current).forEach((element) => element && observer.observe(element));
    const markOverflowing = () => {
      Object.values(pageRefs.current).forEach((element) => {
        const section = element?.querySelector<HTMLElement>(".story-page");
        const inner = section?.querySelector<HTMLElement>(".story-page-inner");
        if (!section || !inner) return;
        section.dataset.overflowing = inner.scrollHeight > inner.clientHeight + 8 ? "true" : "false";
      });
    };
    const resizeObserver = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(markOverflowing);
    Object.values(pageRefs.current).forEach((element) => {
      const inner = element?.querySelector<HTMLElement>(".story-page-inner");
      if (inner) resizeObserver?.observe(inner);
    });
    window.addEventListener("resize", markOverflowing);
    window.requestAnimationFrame(markOverflowing);
    track("report.started.v1", {
      page_count: pages.length,
      first_page: target ?? null,
      confidence: report.quality.overall_confidence,
      elapsed_bucket: 0
    });
    if (target) trackViewed(target, null, 0);

    const onVisibilityChange = () => {
      if (document.visibilityState === "hidden") {
        if (!hiddenRef.current) {
          activeElapsedMs.current += Math.max(0, Date.now() - activeStartedAt.current);
          hiddenRef.current = true;
        }
      } else if (hiddenRef.current) {
        hiddenRef.current = false;
        activeStartedAt.current = Date.now();
      }
    };
    const onPageHide = () => trackExited();
    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("pagehide", onPageHide);
    return () => {
      observer.disconnect();
      resizeObserver?.disconnect();
      window.removeEventListener("resize", markOverflowing);
      delete document.documentElement.dataset.reportStory;
      trackExited();
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("pagehide", onPageHide);
    };
    // The report is immutable; observer setup should run once per report.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageIndex, report.report_id, pages]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, button, a, textarea, dialog")) return;
      if (!["ArrowDown", "PageDown", " ", "ArrowUp", "PageUp", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const index = pageIndex(activePage);
      const next = event.key === "Home"
        ? 0
        : event.key === "End"
          ? pages.length - 1
          : event.key === "ArrowUp" || event.key === "PageUp"
            ? Math.max(0, index - 1)
            : Math.min(pages.length - 1, index + 1);
      const page = pages[next];
      if (page) pageRefs.current[page.id]?.scrollIntoView({ behavior: reducedMotion.current ? "auto" : "smooth", block: "start" });
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activePage, pageIndex, pages]);

  const openMethodology = (dimension: DnaDimension) => {
    track("report.methodology_opened.v1", { dimension: dimension.key });
    setMethodology(dimension);
  };
  const closeMethodology = () => {
    if (methodology) track("report.methodology_closed.v1", { dimension: methodology.key });
    setMethodology(null);
  };
  const activeIndex = Math.max(0, pageIndex(activePage));

  return (
    <main className="report-story" aria-label="Dota DNA report">
      <nav className="story-progress" aria-label="Report progress">
        <span>{String(activeIndex + 1).padStart(2, "0")} / {String(pages.length).padStart(2, "0")}</span>
        <div className="story-progress-track"><span style={{ width: `${((activeIndex + 1) / Math.max(1, pages.length)) * 100}%` }} /></div>
        <a href="#final-card" className="story-progress-link">Fingerprint</a>
      </nav>
      {pages.map((page, index) => (
        <div key={page.id} ref={(element) => { pageRefs.current[page.id] = element; }}>
          <StoryPageFrame id={page.id} index={index} kind={page.kind}>
            {renderPage(page, report, openMethodology)}
          </StoryPageFrame>
        </div>
      ))}
      <MethodologySheet
        open={methodology !== null}
        title={methodology ? methodology.key.replaceAll("_", " ") : "Methodology"}
        body={methodology ? `${methodology.confidence} confidence. ${methodology.confounders.join(" ") || "This page uses only the readable summary fields in your history."}` : ""}
        onClose={closeMethodology}
      />
    </main>
  );
}

function renderPage(page: StoryPageV1, report: StoryReport, openMethodology: (dimension: DnaDimension) => void) {
  if (page.kind === "section_intro") return <SectionIntro title={page.title} body={page.body} headingId={`${page.id}-heading`} />;
  if (page.kind === "reveal") return <div className="story-hero-copy"><p className="eyebrow">Report reveal</p><h2 id={`${page.id}-heading`}>{page.title}</h2>{page.body && <p>{page.body}</p>}</div>;
  if (page.kind === "dimension") {
    const dimension = report.dimensions.find((item) => item.key === page.id);
    if (!dimension) return <div><h2 id={`${page.id}-heading`}>{page.title}</h2><p>{page.body}</p></div>;
    return <DimensionPage page={page} dimension={dimension} onMethodology={() => openMethodology(dimension)} />;
  }
  if (page.kind === "archetype") return <div className="archetype-reveal"><p className="eyebrow">Your archetype</p><h2 id={`${page.id}-heading`}>{report.archetype.label}</h2><div className="descriptor-list">{report.archetype.descriptors.map((item) => <span key={item.key}>{item.label}</span>)}</div><p>{page.body ?? report.archetype.explanation_evidence.join(" · ")}</p></div>;
  if (page.kind === "signature_hero") return <div><p className="eyebrow">Heroes</p><h2 id={`${page.id}-heading`}>{page.title}</h2><HeroPortraitCard hero={report.heroes.signature} featured /><p>{page.body}</p></div>;
  if (page.kind === "comfort") return <div><p className="eyebrow">Heroes</p><h2 id={`${page.id}-heading`}>{page.title}</h2><div className="hero-grid">{report.heroes.comfort_picks.map((hero) => <HeroPortraitCard key={hero.hero_id} hero={hero} />)}</div><p>{page.body}</p></div>;
  if (page.kind === "hero_pattern") return <div className="pattern-card"><p className="eyebrow">Hero Pattern</p><h2 id={`${page.id}-heading`}>{page.title}</h2><p>{page.body}</p></div>;
  if (page.kind === "recommendations") return <div><p className="eyebrow">Taste adjacency</p><h2 id={`${page.id}-heading`}>{page.title}</h2><p>{page.body}</p><div className="recommendation-list">{report.heroes.recommendations.length ? report.heroes.recommendations.map((hero) => <div className="recommendation" key={hero.hero_id}><strong>{hero.name}</strong><span>{hero.familiar_traits.join(" · ")}</span><small>New angle: {hero.new_traits.join(" · ")}</small></div>) : <p className="muted">Your history is still too small for responsible recommendations.</p>}</div></div>;
  if (page.kind === "final_card") return <div className="final-card"><p className="eyebrow">{page.title}</p><h2 id={`${page.id}-heading`}>{report.archetype.label}</h2><div className="descriptor-list">{report.archetype.descriptors.map((item) => <span key={item.key}>{item.label}</span>)}</div><p>{page.body}</p>{report.report_id && <ShareControls reportId={report.report_id} />}</div>;
  if (page.kind === "deep_dive") return <DeepDiveTeaser href={report.deep_dive.href} title={page.title} body={page.body} headingId={`${page.id}-heading`} onClick={() => track("deep_dive.cta_clicked.v1", { page: page.id })} />;
  return <div className="story-summary"><p className="eyebrow">Dota DNA</p><h2 id={`${page.id}-heading`}>{page.title}</h2><div className="descriptor-list">{report.archetype.descriptors.map((item) => <span key={item.key}>{item.label}</span>)}</div><p>{page.body}</p></div>;
}

function DimensionPage({ page, dimension, onMethodology }: { page: StoryPageV1; dimension: DnaDimension; onMethodology: () => void }) {
  const left = dimension.copy?.left_label ?? "Lower";
  const right = dimension.copy?.right_label ?? "Higher";
  return <div className={`dimension-page is-${dimension.status}`}><p className="eyebrow">DNA signal · {dimension.confidence}</p><h2 id={`${page.id}-heading`}>{page.title}</h2><p className="dimension-label">{dimension.label ?? "Signal faint"}</p><Spectrum score={dimension.score} left={left} right={right} disabled={dimension.score === null} /><EvidenceReceipt evidence={dimension.evidence} />{dimension.status === "unavailable" ? <p className="muted">{page.body}</p> : <p>{page.body}</p>}<button className="methodology-button" type="button" onClick={onMethodology}>How is this read?</button></div>;
}
