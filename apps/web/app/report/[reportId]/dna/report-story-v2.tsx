"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  DnaDimension,
  FreeDnaReportV2,
  PublicFinding,
  StoryPageV2,
} from "../../../../../../packages/api-client/src";
import { track } from "../../../lib/analytics";
import {
  DeepDiveTeaser,
  MethodologySheet,
  Spectrum,
  StoryPage as StoryPageFrame,
} from "../../../components/story/primitives";
import ShareControls from "../../../components/share/share-controls";

const entryPageKinds = new Set<StoryPageV2["kind"]>(["input", "player_found", "analysis"]);

export default function ReportStoryV2({ report }: { report: FreeDnaReportV2 }) {
  const pages = useMemo(
    () => report.pages.filter((page) => !entryPageKinds.has(page.kind)),
    [report.pages]
  );
  const pageRefs = useRef<Record<string, HTMLElement | null>>({});
  const [activePage, setActivePage] = useState(pages[0]?.id ?? "");
  const [methodology, setMethodology] = useState<DnaDimension | null>(null);
  const reducedMotion = useRef(false);

  const pageIndex = useCallback((id: string) => pages.findIndex((page) => page.id === id), [pages]);

  useEffect(() => {
    document.documentElement.dataset.reportStory = "true";
    reducedMotion.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let stored: string | null = null;
    try {
      stored = sessionStorage.getItem(`dota-report-page:${report.report_id ?? "current"}`);
    } catch {
      // Page resume is an enhancement; private browsing may disable storage.
    }
    const fromHash = window.location.hash.slice(1);
    const target = pages.some((page) => page.id === stored)
      ? stored
      : pages.some((page) => page.id === fromHash)
        ? fromHash
        : pages[0]?.id;
    if (target) {
      setActivePage(target);
      window.requestAnimationFrame(() => pageRefs.current[target]?.scrollIntoView({ block: "start", behavior: "auto" }));
    }

    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting || entry.intersectionRatio < 0.55) continue;
        const id = entry.target.getAttribute("data-page-id");
        if (!id || id === activePage) continue;
        setActivePage(id);
        try {
          sessionStorage.setItem(`dota-report-page:${report.report_id ?? "current"}`, id);
        } catch {
          // Ignore storage failures; the report remains fully navigable.
        }
        window.history.replaceState(null, "", `#${id}`);
        const page = pages.find((item) => item.id === id);
        if (page?.kind === "finding") {
          const finding = findingForPage(page, report);
          if (finding) track("finding.viewed.v1", { finding_key: finding.key, finding_kind: finding.kind, confidence: finding.confidence, ordinal: pageIndex(id) });
        }
        if (page?.kind === "experiment") {
          const finding = findingForPage(page, report);
          if (finding?.experiment) track("finding.experiment_viewed.v1", { finding_key: finding.key, finding_kind: finding.kind, experiment_key: finding.experiment.key, ordinal: pageIndex(id) });
        }
      }
    }, { threshold: [0.55, 0.8] });
    Object.values(pageRefs.current).forEach((element) => element && observer.observe(element));
    return () => {
      observer.disconnect();
      delete document.documentElement.dataset.reportStory;
    };
    // The report is immutable; observer setup should run once per snapshot.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pageIndex, pages, report.report_id]);

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

  const activeIndex = Math.max(0, pageIndex(activePage));
  const openMethodology = (dimension: DnaDimension) => {
    track("report.methodology_opened.v1", { dimension: dimension.key });
    setMethodology(dimension);
  };
  const closeMethodology = () => {
    if (methodology) track("report.methodology_closed.v1", { dimension: methodology.key });
    setMethodology(null);
  };

  return (
    <main className="report-story report-story-v2" aria-label="Finding-led Dota DNA report">
      <nav className="story-progress" aria-label="Report progress">
        <span>{String(activeIndex + 1).padStart(2, "0")} / {String(pages.length).padStart(2, "0")}</span>
        <div className="story-progress-track"><span style={{ width: `${((activeIndex + 1) / Math.max(1, pages.length)) * 100}%` }} /></div>
        <a href="#identity-card" className="story-progress-link">Identity</a>
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
        body={methodology ? `${methodology.confidence} confidence. ${methodology.confounders.join(" ") || "This evidence uses readable summary fields from the bounded history."}` : ""}
        onClose={closeMethodology}
      />
    </main>
  );
}

function renderPage(page: StoryPageV2, report: FreeDnaReportV2, openMethodology: (dimension: DnaDimension) => void) {
  if (page.kind === "reveal") {
    return <div className="story-hero-copy"><p className="eyebrow">Report reveal</p><h2 id={`${page.id}-heading`}>{page.title}</h2>{page.body && <p>{page.body}</p>}</div>;
  }
  if (page.kind === "finding") {
    const finding = findingForPage(page, report);
    return finding ? <FindingPage finding={finding} report={report} headingId={`${page.id}-heading`} /> : <FallbackPage page={page} />;
  }
  if (page.kind === "experiment") {
    const finding = findingForPage(page, report);
    return finding?.experiment ? <ExperimentPage finding={finding} headingId={`${page.id}-heading`} /> : <FallbackPage page={page} />;
  }
  if (page.kind === "identity_card") return <IdentityCard report={report} page={page} />;
  if (page.kind === "dna_xray") return <DnaXray report={report} page={page} onMethodology={openMethodology} />;
  if (page.kind === "deep_dive") return <DeepDiveTeaser href={report.deep_dive.href} title={page.title} body={page.body} headingId={`${page.id}-heading`} onClick={() => track("deep_dive.cta_clicked.v1", { page: page.id })} />;
  return <FallbackPage page={page} />;
}

function FindingPage({ finding, report, headingId }: { finding: PublicFinding; report: FreeDnaReportV2; headingId: string }) {
  return (
    <article className={`finding-page finding-${finding.kind}`}>
      <p className="eyebrow">{finding.kind.replaceAll("_", " ")}</p>
      <h2 id={headingId}>{finding.headline}</h2>
      <p className="finding-body">{finding.body}</p>
      <div className="finding-receipts" aria-label="Finding evidence">
        {finding.receipts.map((receipt) => (
          <span key={receipt.key}><strong>{receipt.value}</strong><small>{receipt.label} · {receipt.confidence}</small></span>
        ))}
      </div>
      {finding.interpretation && <section className="finding-interpretation"><span>What this means</span><p>{finding.interpretation}</p></section>}
      <details className="finding-evidence-details" onToggle={(event) => {
        if ((event.currentTarget as HTMLDetailsElement).open) track("finding.evidence_opened.v1", { finding_key: finding.key, finding_kind: finding.kind, confidence: finding.confidence });
      }}>
        <summary>See why</summary>
        <div className="finding-details-body">
          {finding.related_dimensions.map((key) => {
            const dimension = report.dimensions.find((item) => item.key === key);
            if (!dimension) return null;
            return <div key={dimension.key}><strong>{dimension.label ?? dimension.key}</strong><Spectrum score={dimension.score} left={dimension.copy?.left_label ?? "Lower"} right={dimension.copy?.right_label ?? "Higher"} disabled={dimension.score === null} /></div>;
          })}
          <p className="muted">Receipts use deterministic summary-history evidence. Sample sizes and confidence stay visible so the conclusion can be read in context.</p>
        </div>
      </details>
    </article>
  );
}

function ExperimentPage({ finding, headingId }: { finding: PublicFinding; headingId: string }) {
  const experiment = finding.experiment;
  if (!experiment) return null;
  return (
    <article className="experiment-page">
      <p className="eyebrow">Your next experiment</p>
      <h2 id={headingId}>{experiment.title}</h2>
      <p className="experiment-instruction">{experiment.instruction}</p>
      <dl className="experiment-facts">
        <div><dt>Testing</dt><dd>{experiment.hypothesis}</dd></div>
        <div><dt>Measure</dt><dd>{experiment.measurement}</dd></div>
        <div><dt>Window</dt><dd>{experiment.window}</dd></div>
      </dl>
      <p className="muted">This is a player-observable test, not an automatic promise of re-analysis.</p>
    </article>
  );
}

function IdentityCard({ report, page }: { report: FreeDnaReportV2; page: StoryPageV2 }) {
  const share = report.shares.identity;
  return (
    <article className="identity-card">
      <p className="eyebrow">Your Dota DNA</p>
      <h2 id={`${page.id}-heading`}>{share.headline}</h2>
      <p className="identity-archetype">{share.archetype ?? report.archetype.label}</p>
      <div className="finding-receipts">{share.receipts.map((receipt) => <span key={receipt}><strong>{receipt}</strong><small>Evidence receipt</small></span>)}</div>
      <p>{report.identity.display_name} · {report.archetype.label}</p>
      {report.report_id && <ShareControls reportId={report.report_id} defaultCardType="identity" findingKind="identity" findingKey={share.finding_key ?? undefined} reportSchema={report.schema_version} />}
    </article>
  );
}

function DnaXray({ report, page, onMethodology }: { report: FreeDnaReportV2; page: StoryPageV2; onMethodology: (dimension: DnaDimension) => void }) {
  return (
    <article className="dna-xray">
      <p className="eyebrow">Evidence layer</p>
      <h2 id={`${page.id}-heading`}>{page.title}</h2>
      <p>{page.body}</p>
      <div className="dna-xray-list">
        {report.dimensions.map((dimension) => (
          <div className="dna-xray-row" key={dimension.key}>
            <div><strong>{dimension.label ?? dimension.key}</strong><small>{dimension.confidence} · n={dimension.sample_size}</small></div>
            <Spectrum score={dimension.score} left={dimension.copy?.left_label ?? "Lower"} right={dimension.copy?.right_label ?? "Higher"} disabled={dimension.score === null} />
            <button type="button" className="methodology-button" onClick={() => onMethodology(dimension)}>How is this read?</button>
          </div>
        ))}
      </div>
    </article>
  );
}

function FallbackPage({ page }: { page: StoryPageV2 }) {
  return <div className="story-summary"><p className="eyebrow">Dota DNA</p><h2 id={`${page.id}-heading`}>{page.title}</h2>{page.body && <p>{page.body}</p>}</div>;
}

function findingForPage(page: StoryPageV2, report: FreeDnaReportV2): PublicFinding | null {
  return page.finding_key ? report.findings.find((finding) => finding.key === page.finding_key) ?? null : null;
}
