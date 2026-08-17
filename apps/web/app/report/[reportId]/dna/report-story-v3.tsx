"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type {
  BehaviorElement,
  BehaviorFinding,
  FreeDnaReportV3,
  StoryPageV3,
} from "../../../../../../packages/api-client/src";
import { track } from "../../../lib/analytics";
import {
  DeepDiveTeaser,
  HeroPortraitCard,
  Spectrum,
  StoryPage as StoryPageFrame,
} from "../../../components/story/primitives";
import ShareControls from "../../../components/share/share-controls";

export default function ReportStoryV3({ report }: { report: FreeDnaReportV3 }) {
  const pages = useMemo(() => report.pages, [report.pages]);
  const pageRefs = useRef<Record<string, HTMLElement | null>>({});
  const [activePage, setActivePage] = useState(pages[0]?.id ?? "");
  const activePageRef = useRef(activePage);

  useEffect(() => {
    document.documentElement.dataset.reportStory = "true";
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting || entry.intersectionRatio < 0.55) continue;
        const id = entry.target.getAttribute("data-page-id");
        if (!id || id === activePageRef.current) continue;
        activePageRef.current = id;
        setActivePage(id);
        const page = pages.find((item) => item.id === id);
        track("report.page_viewed.v1", {
          page: id,
          page_kind: page?.kind ?? null,
          section: page?.section ?? null,
          report_schema_version: report.schema_version,
        });
        if (page?.kind === "finding" && page.finding_key) {
          const finding = report.findings.find((item) => item.key === page.finding_key);
          if (finding) track("finding.viewed.v1", { finding_key: finding.key, finding_kind: finding.kind, confidence: finding.confidence });
        }
      }
    }, { threshold: [0.55, 0.8] });
    Object.values(pageRefs.current).forEach((element) => element && observer.observe(element));
    return () => {
      observer.disconnect();
      delete document.documentElement.dataset.reportStory;
    };
  }, [pages, report.findings, report.schema_version]);

  const activeIndex = Math.max(0, pages.findIndex((page) => page.id === activePage));
  return (
    <main className="report-story report-story-v3" aria-label="Finding-led Dota behavioral report">
      <nav className="story-progress" aria-label="Report progress">
        <span>{String(activeIndex + 1).padStart(2, "0")} / {String(pages.length).padStart(2, "0")}</span>
        <div className="story-progress-track"><span style={{ width: `${((activeIndex + 1) / Math.max(1, pages.length)) * 100}%` }} /></div>
        <a href="#archetypes" className="story-progress-link">Contexts</a>
      </nav>
      {pages.map((page, index) => (
        <div key={page.id} ref={(element) => { pageRefs.current[page.id] = element; }}>
          <StoryPageFrame id={page.id} index={index} kind={page.kind}>
            {renderPage(page, report)}
          </StoryPageFrame>
        </div>
      ))}
    </main>
  );
}

function renderPage(page: StoryPageV3, report: FreeDnaReportV3) {
  if (page.kind === "finding" && page.finding_key) {
    const finding = report.findings.find((item) => item.key === page.finding_key);
    return finding ? <FindingPage finding={finding} report={report} headingId={`${page.id}-heading`} /> : <FallbackPage page={page} />;
  }
  if (page.kind === "experiment" && page.finding_key) {
    const finding = report.findings.find((item) => item.key === page.finding_key);
    return finding?.experiment ? <ExperimentPage finding={finding} headingId={`${page.id}-heading`} /> : <FallbackPage page={page} />;
  }
  if (page.kind === "archetypes") return <ArchetypePage report={report} page={page} />;
  if (page.kind === "dna_xray") return <ElementPage report={report} page={page} />;
  if (page.kind === "heroes") return <HeroPage report={report} page={page} />;
  if (page.kind === "deep_dive") return <DeepDiveTeaser href={report.deep_dive.href} title={page.title} body={page.body} headingId={`${page.id}-heading`} onClick={() => track("deep_dive.cta_clicked.v1", { page: page.id, report_schema_version: report.schema_version })} />;
  return <FallbackPage page={page} />;
}

function FindingPage({ finding, report, headingId }: { finding: BehaviorFinding; report: FreeDnaReportV3; headingId: string }) {
  return (
    <article className={`finding-page finding-${finding.kind}`}>
      <p className="eyebrow">{finding.kind.replaceAll("_", " ")}</p>
      <h2 id={headingId}>{finding.headline}</h2>
      <p className="finding-body">{finding.body}</p>
      <div className="finding-receipts" aria-label="Finding evidence">
        {finding.receipts.map((receipt) => <span key={receipt.key}><strong>{receipt.value}</strong><small>{receipt.label} · {receipt.confidence}</small></span>)}
      </div>
      <section className="finding-interpretation"><span>What this means</span><p>{finding.interpretation}</p></section>
      <details className="finding-evidence-details">
        <summary>See the Elements</summary>
        <div className="finding-details-body">
          {finding.supporting_element_keys.map((key) => {
            const element = report.elements.find((item) => item.key === key);
            return element ? <ElementRow key={element.key} element={element} /> : null;
          })}
          <p className="muted">
            {finding.source_pattern_keys.length > 0
              ? "The Pattern is built from these upstream Elements. Private source match IDs stay out of the report."
              : "This is an Element-level signal. A qualified Pattern is not available yet."}
          </p>
        </div>
      </details>
      {report.report_id && <ShareControls reportId={report.report_id} defaultCardType="identity" findingKind={finding.kind} findingKey={finding.key} reportSchema={report.schema_version} />}
    </article>
  );
}

function ExperimentPage({ finding, headingId }: { finding: BehaviorFinding; headingId: string }) {
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

function ArchetypePage({ report, page }: { report: FreeDnaReportV3; page: StoryPageV3 }) {
  return (
    <article className="identity-card">
      <p className="eyebrow">Context archetypes</p>
      <h2 id={`${page.id}-heading`}>{page.title}</h2>
      <p>{page.body}</p>
      <div className="archetype-grid">
        {report.archetypes.map((archetype) => (
          <section className="pattern-card" key={archetype.group_key}>
            <p className="eyebrow">{archetype.group_label}</p>
            <h3>{archetype.label}</h3>
            <p>{archetype.confidence} confidence · {Math.round(archetype.fit * 100)}% fit</p>
            <div className="descriptor-list">{archetype.descriptors.map((item) => <span key={item.key}>{item.label}</span>)}</div>
            <small>{archetype.explanation_evidence.join(" · ")}</small>
          </section>
        ))}
      </div>
      {report.report_id && <ShareControls reportId={report.report_id} defaultCardType="identity" reportSchema={report.schema_version} />}
    </article>
  );
}

function ElementPage({ report, page }: { report: FreeDnaReportV3; page: StoryPageV3 }) {
  const byDimension = report.elements.reduce<Record<string, BehaviorElement[]>>((groups, element) => {
    (groups[element.dimension_key] ??= []).push(element);
    return groups;
  }, {});
  return (
    <article className="dna-xray">
      <p className="eyebrow">Evidence layer</p>
      <h2 id={`${page.id}-heading`}>{page.title}</h2>
      <p>{page.body}</p>
      {Object.entries(byDimension).map(([dimension, elements]) => (
        <section className="dna-xray-list" key={dimension}>
          <p className="eyebrow">{dimension.replaceAll("_", " ")}</p>
          {elements.map((element) => <ElementRow key={element.key} element={element} />)}
        </section>
      ))}
    </article>
  );
}

function ElementRow({ element }: { element: BehaviorElement }) {
  return (
    <div className="dna-xray-row">
      <div><strong>{element.label}</strong><small>{element.status} · {element.confidence} · n={element.sample_size}</small></div>
      <Spectrum score={element.score} left={element.axis.left ?? "Lower"} right={element.axis.right ?? "Higher"} disabled={element.score === null} />
      {element.receipts.slice(0, 2).map((receipt) => <small key={receipt.key}>{receipt.value} · {receipt.key.replaceAll("_", " ")}</small>)}
      {element.missing_reasons.slice(0, 1).map((reason) => <small key={reason}>Unavailable: {reason.replaceAll("_", " ")}</small>)}
    </div>
  );
}

function HeroPage({ report, page }: { report: FreeDnaReportV3; page: StoryPageV3 }) {
  return (
    <article className="identity-card">
      <p className="eyebrow">Hero identity</p>
      <h2 id={`${page.id}-heading`}>{page.title}</h2>
      <p>{page.body}</p>
      {report.heroes.signature && <HeroPortraitCard hero={report.heroes.signature} featured />}
      {report.heroes.comfort_picks.length > 0 && <div className="hero-grid">{report.heroes.comfort_picks.slice(0, 5).map((hero) => <HeroPortraitCard key={hero.hero_id} hero={hero} />)}</div>}
    </article>
  );
}

function FallbackPage({ page }: { page: StoryPageV3 }) {
  return <div className="story-summary"><p className="eyebrow">Dota behavior model</p><h2 id={`${page.id}-heading`}>{page.title}</h2>{page.body && <p>{page.body}</p>}</div>;
}
