"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { track } from "../../../lib/analytics";
import {
  DeepDiveTeaser,
  EvidenceReceipt,
  HeroPortraitCard,
  MethodologySheet,
  SectionIntro,
  Spectrum,
  StoryPage
} from "../../../components/story/primitives";
import ShareControls from "../../../components/share/share-controls";

type Dimension = {
  key: string;
  status: "available" | "limited" | "unavailable";
  score: number | null;
  label: string | null;
  confidence: string;
  confidence_score: number;
  evidence: Array<{ key: string; value: string | number; unit: string; denominator: number }>;
  confounders: string[];
  missing_reasons: string[];
};

export type StoryReport = {
  report_id?: string;
  dna_report_variant?: string;
  identity: { display_name?: string; personaname?: string; avatar_url?: string | null; account_id_masked?: string };
  quality: { overall_confidence: string; warnings: string[]; partial: boolean };
  dimensions: Dimension[];
  archetype: { label: string; confidence: string; descriptors: Array<{ key: string; label: string; dimension: string }>; explanation_evidence: string[] };
  heroes: { signature: any; comfort_picks: any[]; patterns: any[]; recommendations: any[]; limitations: string[] };
  pages: Array<{ id: string; kind: string; section: string; title: string; body?: string; evidence_keys?: string[] }>;
  shares: { privacy_defaults: { show_name: boolean; show_avatar: boolean; show_raw_id: false } };
  deep_dive: { href: string | null };
};

export default function ReportStory({ report }: { report: StoryReport }) {
  const pages = useMemo(() => report.pages ?? [], [report.pages]);
  const pageRefs = useRef<Record<string, HTMLElement | null>>({});
  const [activePage, setActivePage] = useState(pages[0]?.id ?? "");
  const [methodology, setMethodology] = useState<Dimension | null>(null);
  const startedAt = useRef<number>(Date.now());
  const activeStartedAt = useRef<number>(Date.now());
  const activePageRef = useRef(activePage);
  const reducedMotion = useRef(false);

  useEffect(() => {
    reducedMotion.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const stored = sessionStorage.getItem(`dota-report-page:${report.report_id ?? "current"}`);
    const fromHash = window.location.hash.slice(1);
    const target = pages.some((page) => page.id === stored) ? stored : pages.some((page) => page.id === fromHash) ? fromHash : pages[0]?.id;
    if (target) {
      activePageRef.current = target;
      setActivePage(target);
      window.requestAnimationFrame(() => pageRefs.current[target!]?.scrollIntoView({ block: "start", behavior: "auto" }));
    }
    const reportStartedAt = startedAt.current;
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting || entry.intersectionRatio < 0.55) continue;
        const id = entry.target.getAttribute("data-page-id");
        if (!id || id === activePageRef.current) continue;
        const previous = activePageRef.current;
        const dwell = Math.max(0, Date.now() - activeStartedAt.current);
        track("report.page_viewed.v1", { page: id, ordinal: pages.findIndex((page) => page.id === id), previous_page: previous, dwell_bucket: Math.floor(dwell / 5000) * 5, direction: pages.findIndex((page) => page.id === id) > pages.findIndex((page) => page.id === previous) ? "forward" : "backward" });
        activeStartedAt.current = Date.now();
        activePageRef.current = id;
        setActivePage(id);
        sessionStorage.setItem(`dota-report-page:${report.report_id ?? "current"}`, id);
        window.history.replaceState(null, "", `#${id}`);
      }
    }, { threshold: [0.55, 0.8] });
    Object.values(pageRefs.current).forEach((element) => element && observer.observe(element));
    track("report.started.v1", { page_count: pages.length, confidence: report.quality.overall_confidence, elapsed_bucket: 0 });
    return () => {
      observer.disconnect();
      track("report.page_exited.v1", { page: activePageRef.current, dwell_bucket: Math.floor((Date.now() - activeStartedAt.current) / 5000) * 5 });
      track("report.completed.v1", { elapsed_bucket: Math.floor((Date.now() - reportStartedAt) / 10000) * 10 });
    };
    // The report is immutable; observer setup should run once per report.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report.report_id, pages]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, button, a, textarea, dialog")) return;
      if (!["ArrowDown", "PageDown", " ", "ArrowUp", "PageUp", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const index = pages.findIndex((page) => page.id === activePage);
      const next = event.key === "Home" ? 0 : event.key === "End" ? pages.length - 1 : event.key === "ArrowUp" || event.key === "PageUp" ? Math.max(0, index - 1) : Math.min(pages.length - 1, index + 1);
      const page = pages[next];
      if (page) pageRefs.current[page.id]?.scrollIntoView({ behavior: reducedMotion.current ? "auto" : "smooth", block: "start" });
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activePage, pages]);

  return (
    <main className="report-story" aria-label="Dota DNA report">
      <nav className="story-progress" aria-label="Report progress">
        <span>{String(Math.max(1, pages.findIndex((page) => page.id === activePage) + 1)).padStart(2, "0")} / {String(pages.length).padStart(2, "0")}</span>
        <div className="story-progress-track"><span style={{ width: `${((pages.findIndex((page) => page.id === activePage) + 1) / Math.max(1, pages.length)) * 100}%` }} /></div>
        <a href="#final-card" className="story-progress-link">Fingerprint</a>
      </nav>
      {pages.map((page, index) => (
        <div key={page.id} ref={(element) => { pageRefs.current[page.id] = element; }}>
          <StoryPage id={page.id} index={index} kind={page.kind}>
            {renderPage(page, report, setMethodology)}
          </StoryPage>
        </div>
      ))}
      <MethodologySheet open={methodology !== null} title={methodology ? methodology.key.replaceAll("_", " ") : "Methodology"} body={methodology ? `${methodology.confidence} confidence. ${methodology.confounders.join(" ") || "This page uses only the readable summary fields in your history."}` : ""} onClose={() => setMethodology(null)} />
    </main>
  );
}

function renderPage(page: StoryReport["pages"][number], report: StoryReport, openMethodology: (dimension: Dimension) => void) {
  if (page.kind === "section_intro") return <SectionIntro title={page.title} body={page.body} headingId={`${page.id}-heading`} />;
  if (page.kind === "input" || page.kind === "player_found" || page.kind === "analysis" || page.kind === "reveal") return <div className="story-hero-copy"><p className="eyebrow">{page.kind.replaceAll("_", " ")}</p><h2 id={`${page.id}-heading`}>{page.title}</h2>{page.body && <p>{page.body}</p>}</div>;
  if (page.kind === "dimension") {
    const dimension = report.dimensions.find((item) => item.key === page.id);
    if (!dimension) return <div><h2 id={`${page.id}-heading`}>{page.title}</h2><p>{page.body}</p></div>;
    return <DimensionPage page={page} dimension={dimension} onMethodology={() => openMethodology(dimension)} />;
  }
  if (page.kind === "archetype") return <div className="archetype-reveal"><p className="eyebrow">Your archetype</p><h2 id={`${page.id}-heading`}>{report.archetype.label}</h2><div className="descriptor-list">{report.archetype.descriptors.map((item) => <span key={item.key}>{item.label}</span>)}</div><p>{report.archetype.explanation_evidence.join(" · ")}</p></div>;
  if (page.kind === "signature_hero") return <div><p className="eyebrow">Heroes</p><h2 id={`${page.id}-heading`}>Your Signature Hero</h2><HeroPortraitCard hero={report.heroes.signature} featured /></div>;
  if (page.kind === "comfort") return <div><p className="eyebrow">Heroes</p><h2 id={`${page.id}-heading`}>Comfort Picks</h2><div className="hero-grid">{report.heroes.comfort_picks.map((hero) => <HeroPortraitCard key={hero.hero_id} hero={hero} />)}</div></div>;
  if (page.kind === "hero_pattern") return <div className="pattern-card"><p className="eyebrow">Hero Pattern</p><h2 id={`${page.id}-heading`}>{page.body}</h2><p>Your comfort pool points toward a toolkit, not a verdict.</p></div>;
  if (page.kind === "recommendations") return <div><p className="eyebrow">Taste adjacency</p><h2 id={`${page.id}-heading`}>Heroes to try next</h2><div className="recommendation-list">{report.heroes.recommendations.length ? report.heroes.recommendations.map((hero) => <div className="recommendation" key={hero.hero_id}><strong>{hero.name}</strong><span>{hero.familiar_traits.join(" · ")}</span><small>New angle: {hero.new_traits.join(" · ")}</small></div>) : <p className="muted">Your history is still too small for responsible recommendations.</p>}</div></div>;
  if (page.kind === "final_card") return <div className="final-card"><p className="eyebrow">Your fingerprint</p><h2 id={`${page.id}-heading`}>{report.archetype.label}</h2><div className="descriptor-list">{report.archetype.descriptors.map((item) => <span key={item.key}>{item.label}</span>)}</div><p>{page.body}</p>{report.report_id && <ShareControls reportId={report.report_id} />}</div>;
  if (page.kind === "deep_dive") return <DeepDiveTeaser href={report.deep_dive.href} headingId={`${page.id}-heading`} />;
  return <div className="story-summary"><p className="eyebrow">Dota DNA</p><h2 id={`${page.id}-heading`}>{page.title}</h2><div className="descriptor-list">{report.archetype.descriptors.map((item) => <span key={item.key}>{item.label}</span>)}</div><p>{page.body}</p></div>;
}

function DimensionPage({ page, dimension, onMethodology }: { page: StoryReport["pages"][number]; dimension: Dimension; onMethodology: () => void }) {
  const labels: Record<string, [string, string]> = { breadth: ["Focused", "Exploratory"], role: ["Anchored", "Fluid"], adaptability: ["Comfort-bound", "Transferable"], activity: ["Reserved", "Involved"], orientation: ["Facilitator", "Finisher"], resilience: ["Resetting", "Outcome-sensitive"], endurance: ["Front-loaded", "Sustained"], rhythm: ["Short-burst", "Grinder"] };
  return <div className={`dimension-page is-${dimension.status}`}><p className="eyebrow">DNA signal · {dimension.confidence}</p><h2 id={`${page.id}-heading`}>{page.title}</h2><p className="dimension-label">{dimension.label ?? "Signal faint"}</p><Spectrum score={dimension.score} left={labels[dimension.key]?.[0] ?? "Low"} right={labels[dimension.key]?.[1] ?? "High"} disabled={dimension.score === null} /><EvidenceReceipt evidence={dimension.evidence} />{dimension.status === "unavailable" ? <p className="muted">{page.body}</p> : <p>{page.body}</p>}<button className="methodology-button" type="button" onClick={onMethodology}>How is this read?</button></div>;
}
