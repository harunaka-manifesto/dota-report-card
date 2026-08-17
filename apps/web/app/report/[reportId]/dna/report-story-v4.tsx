"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type {
  BehaviorElement,
  BehaviorPattern,
  ChoiceOption,
  FreeDnaReportV4,
  HeroException,
  PoolEvolution,
  StoryPage,
} from "../../../../../../packages/api-client/src";
import { track } from "../../../lib/analytics";
import { DeepDiveTeaser, EvidenceReceipt, MethodologySheet, Spectrum, StoryPage as StoryPageFrame } from "../../../components/story/primitives";
import ShareControls from "../../../components/share/share-controls";
import { PORTFOLIO_COPY_V4 } from "./report-copy-v4";

export default function ReportStoryV4({ report }: { report: FreeDnaReportV4 }) {
  const pages = useMemo(() => report.pages, [report.pages]);
  const pageRefs = useRef<Record<string, HTMLElement | null>>({});
  const [activePage, setActivePage] = useState(pages[0]?.id ?? "");
  const activePageRef = useRef(activePage);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const elements = useMemo(() => new Map(report.elements.map((item) => [item.key, item])), [report.elements]);
  const patterns = useMemo(() => new Map(report.patterns.map((item) => [item.key, item])), [report.patterns]);

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
        track("report.page_viewed.v1", { page: id, page_kind: page?.kind ?? null, section: page?.section ?? null, report_schema_version: report.schema_version });
        if (page?.kind === "element_scan") track("report.element_scan_viewed.v1", { page: id });
        if (page?.kind === "element_highlight") track("report.element_highlight_viewed.v1", { element_key: page.element_key ?? null });
        if (page?.kind === "pattern_highlight") track("report.pattern_viewed.v1", { pattern_key: page.pattern_key ?? null });
        if (page?.kind.startsWith("hero_")) track("hero_portfolio.question_viewed.v1", { page: id, portfolio_key: page.portfolio_key ?? null });
        if (page?.kind === "pool_evolution_question") track("hero_portfolio.question_viewed.v1", { page: id, portfolio_key: "evolution" });
        if (page?.kind === "hero_mirror_reveal") track("hero_mirror.reveal_started.v1", { page: id });
      }
    }, { threshold: [0.55, 0.8] });
    Object.values(pageRefs.current).forEach((element) => element && observer.observe(element));
    return () => {
      observer.disconnect();
      delete document.documentElement.dataset.reportStory;
    };
  }, [pages, report.schema_version]);

  const activeIndex = Math.max(0, pages.findIndex((page) => page.id === activePage));
  return (
    <main className="report-story report-story-v4" aria-label="Dota Elements, Patterns, and Hero Portfolio report">
      <nav className="story-progress" aria-label="Report progress">
        <span>{String(activeIndex + 1).padStart(2, "0")} / {String(pages.length).padStart(2, "0")}</span>
        <div className="story-progress-track"><span style={{ width: `${((activeIndex + 1) / Math.max(1, pages.length)) * 100}%` }} /></div>
        <a href="#hero-mirror" className="story-progress-link">Hero Mirror</a>
      </nav>
      {pages.map((page, index) => (
        <div key={page.id} ref={(element) => { pageRefs.current[page.id] = element; }}>
          <StoryPageFrame id={page.id} index={index} kind={page.kind}>
            {renderPage(page, { report, elements, patterns, answers, revealed, setAnswers, setRevealed, methodologyOpen, setMethodologyOpen })}
          </StoryPageFrame>
        </div>
      ))}
    </main>
  );
}

type StoryContext = {
  report: FreeDnaReportV4;
  elements: Map<string, BehaviorElement>;
  patterns: Map<string, BehaviorPattern>;
  answers: Record<string, string>;
  revealed: Record<string, boolean>;
  setAnswers: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  setRevealed: React.Dispatch<React.SetStateAction<Record<string, boolean>>>;
  methodologyOpen: boolean;
  setMethodologyOpen: React.Dispatch<React.SetStateAction<boolean>>;
};

function renderPage(page: StoryPage, context: StoryContext) {
  const { report } = context;
  if (page.kind === "element_scan") return <ElementScan page={page} context={context} />;
  if (page.kind === "element_highlight") return <ElementHighlightPage page={page} context={context} />;
  if (page.kind === "pattern_highlight") return <PatternHighlightPage page={page} context={context} />;
  if (page.kind === "hero_common_thread_question") return <PortfolioQuestion page={page} context={context} kind="common_thread" />;
  if (page.kind === "hero_exception_question") return <PortfolioQuestion page={page} context={context} kind="exception" />;
  if (page.kind === "pool_evolution_question") return <EvolutionQuestion page={page} context={context} />;
  if (page.kind === "pool_evolution_reveal") return <EvolutionReveal page={page} context={context} />;
  if (page.kind === "hero_mirror_reveal") return <MirrorPage page={page} context={context} />;
  if (page.kind === "final_card") return <FinalCard page={page} report={report} />;
  if (page.kind === "deep_dive") return <DeepDiveTeaser href={report.deep_dive.href} title={page.title} body={page.body} headingId={`${page.id}-heading`} onClick={() => track("deep_dive.cta_clicked.v1", { page: page.id, report_schema_version: report.schema_version })} />;
  return <FallbackPage page={page} />;
}

function ElementScan({ page, context }: { page: StoryPage; context: StoryContext }) {
  const { report, setMethodologyOpen } = context;
  const highlightKeys = new Set(report.highlights.element_keys);
  return (
    <article className="element-scan">
      <p className="eyebrow">17 Elements · summary history only</p>
      <h2 id={`${page.id}-heading`}>{page.title}</h2>
      <p className="story-lede">{page.body}</p>
      <div className="element-scan-grid">
        {report.elements.map((element) => <ElementTile key={element.key} element={element} featured={highlightKeys.has(element.key)} />)}
      </div>
      <button type="button" className="methodology-button" onClick={() => setMethodologyOpen(true)}>How the Elements are measured</button>
      <MethodologySheet open={context.methodologyOpen} title="Observable Elements" body="Each Element is a reviewed, versioned summary-history measurement. Unavailable fields stay unavailable; a score is never filled with a neutral guess." onClose={() => setMethodologyOpen(false)} />
    </article>
  );
}

function ElementTile({ element, featured = false }: { element: BehaviorElement; featured?: boolean }) {
  return (
    <article className={`element-tile is-${element.status}${featured ? " is-featured" : ""}`}>
      <div className="element-tile-heading"><span className="eyebrow">{element.status}</span><strong>{element.label}</strong></div>
      <Spectrum score={element.score} left={element.axis.left} right={element.axis.right} disabled={element.status === "unavailable"} />
      <div className="element-tile-meta"><span>{element.zone ?? "No zone yet"}</span><span>{element.sample_size ? `n=${element.sample_size}` : "No sample"}</span></div>
    </article>
  );
}

function ElementHighlightPage({ page, context }: { page: StoryPage; context: StoryContext }) {
  const element = page.element_key ? context.elements.get(page.element_key) : undefined;
  if (!element) return <FallbackPage page={page} />;
  return (
    <article className="element-highlight-page">
      <p className="eyebrow">Element highlight</p>
      <h2 id={`${page.id}-heading`}>{element.label}</h2>
      <p className="story-lede">{page.body}</p>
      <Spectrum score={element.score} left={element.axis.left} right={element.axis.right} disabled={element.status === "unavailable"} />
      <div className="signal-status"><strong>{element.zone ?? "Signal unavailable"}</strong><span>{element.confidence} confidence · {element.sample_size ? `n=${element.sample_size}` : "no readable sample"}</span></div>
      <EvidenceReceipt evidence={element.receipts} />
      {element.missing_reasons.length > 0 && <p className="muted">{element.missing_reasons.join(" ")}</p>}
    </article>
  );
}

function PatternHighlightPage({ page, context }: { page: StoryPage; context: StoryContext }) {
  const pattern = page.pattern_key ? context.patterns.get(page.pattern_key) : undefined;
  if (!pattern) return <FallbackPage page={page} />;
  const ingredientMap = new Map([...pattern.element_keys, ...pattern.modifier_element_keys].map((key) => [key, context.elements.get(key)]));
  return (
    <article className={`pattern-highlight-page pattern-tier-${pattern.tier}`}>
      <p className="eyebrow">Pattern · {pattern.family} · Tier {pattern.tier}</p>
      <h2 id={`${page.id}-heading`}>{pattern.label}</h2>
      <p className="story-lede">{page.body}</p>
      <div className="pattern-verdict"><strong>{pattern.status === "qualified" ? "Qualified relationship" : "Still forming"}</strong><span>{pattern.confidence} confidence · {Math.round(pattern.strength * 100)}% strength</span></div>
      <EvidenceReceipt evidence={pattern.receipts} />
      <details className="pattern-ingredients" onToggle={(event) => { if ((event.currentTarget as HTMLDetailsElement).open) track("report.pattern_element_expanded.v1", { pattern_key: pattern.key }); }}>
        <summary>See the Element ingredients</summary>
        <div className="ingredient-list">
          <IngredientGroup title="Required Elements" keys={pattern.element_keys} ingredientMap={ingredientMap} />
          {pattern.modifier_element_keys.length > 0 && <IngredientGroup title="Modifier Elements" keys={pattern.modifier_element_keys} ingredientMap={ingredientMap} />}
        </div>
      </details>
      {pattern.suppression_reasons.length > 0 && <p className="muted">{pattern.suppression_reasons.join(" ")}</p>}
    </article>
  );
}

function IngredientGroup({ title, keys, ingredientMap }: { title: string; keys: string[]; ingredientMap: Map<string, BehaviorElement | undefined> }) {
  return <div className="ingredient-group"><span className="eyebrow">{title}</span>{keys.map((key) => { const element = ingredientMap.get(key); return <div className="ingredient-row" key={key}><strong>{element?.label ?? key}</strong><span>{element?.zone ?? "Unavailable"}</span></div>; })}</div>;
}

function PortfolioQuestion({ page, context, kind }: { page: StoryPage; context: StoryContext; kind: "common_thread" | "exception" }) {
  const result = context.report.hero_portfolio[kind];
  const selected = context.answers[kind];
  const isRevealed = context.revealed[kind];
  const options = result.options;
  const unavailable = result.status === "unavailable";
  const correct = result.correct_option_key;
  const choose = (option: ChoiceOption) => {
    context.setAnswers((current) => ({ ...current, [kind]: option.key }));
    track("hero_portfolio.answer_selected.v1", { portfolio_key: kind, option_key: option.key });
  };
  const reveal = () => {
    context.setRevealed((current) => ({ ...current, [kind]: true }));
    track("hero_portfolio.reveal_viewed.v1", { portfolio_key: kind, result_status: result.status });
  };
  return (
    <article className="portfolio-question">
      <p className="eyebrow">Hero Portfolio · {kind === "common_thread" ? "Common Thread" : "The Exception"}</p>
      <h2 id={`${page.id}-heading`}>{page.title}</h2>
      <p className="story-lede">{page.body}</p>
      {unavailable ? <UnavailableMessage limitations={result.limitations} /> : <>
        <div className="choice-grid">{options.map((option) => <button key={option.key} type="button" className={selected === option.key ? "is-selected" : ""} onClick={() => choose(option)}>{option.label}</button>)}</div>
        <button type="button" className="reveal-button" disabled={!selected} onClick={reveal}>{isRevealed ? "Answer revealed" : "Reveal"}</button>
        {isRevealed && <PortfolioReveal kind={kind} selected={selected} correct={correct} result={result} />}
      </>}
    </article>
  );
}

function PortfolioReveal({ kind, selected, correct, result }: { kind: "common_thread" | "exception"; selected?: string; correct: string | null; result: FreeDnaReportV4["hero_portfolio"]["common_thread"] | HeroException }) {
  const right = selected !== undefined && selected === correct;
  if (kind === "common_thread") {
    const common = result as FreeDnaReportV4["hero_portfolio"]["common_thread"];
    return <div className="portfolio-reveal"><span className="eyebrow">{right ? PORTFOLIO_COPY_V4.common_thread.correct : PORTFOLIO_COPY_V4.common_thread.incorrect}</span><h3>{common.trait_label ?? PORTFOLIO_COPY_V4.common_thread.unavailable}</h3><p>{common.trait_label ? PORTFOLIO_COPY_V4.common_thread.reveal(common.trait_label, common.hero_count) : common.limitations.join(" ")}</p><div className="descriptor-list">{common.secondary_traits.map((trait) => <span key={trait}>{trait}</span>)}</div></div>;
  }
  const exception = result as HeroException;
  return <div className="portfolio-reveal"><span className="eyebrow">{right ? PORTFOLIO_COPY_V4.exception.correct : PORTFOLIO_COPY_V4.exception.incorrect}</span><h3>{exception.hero_name ?? PORTFOLIO_COPY_V4.exception.unavailable}</h3><p>{exception.hero_name ? PORTFOLIO_COPY_V4.exception.reveal(exception.hero_name) : exception.limitations.join(" ")}</p><div className="descriptor-list">{exception.exception_traits.map((trait) => <span key={trait}>{trait}</span>)}</div></div>;
}

function EvolutionQuestion({ page, context }: { page: StoryPage; context: StoryContext }) {
  const selected = context.answers.evolution;
  const isRevealed = context.revealed.evolution;
  const choose = (option: ChoiceOption) => {
    context.setAnswers((current) => ({ ...current, evolution: option.key }));
    track("hero_portfolio.answer_selected.v1", { portfolio_key: "evolution", option_key: option.key });
  };
  return <article className="portfolio-question"><p className="eyebrow">Hero Portfolio · Pool Evolution</p><h2 id={`${page.id}-heading`}>{page.title}</h2><p className="story-lede">{page.body}</p><div className="choice-grid">{page.options.map((option) => <button key={option.key} type="button" className={selected === option.key ? "is-selected" : ""} onClick={() => choose(option)}>{option.label}</button>)}</div><button type="button" className="reveal-button" disabled={!selected} onClick={() => { context.setRevealed((current) => ({ ...current, evolution: true })); track("hero_portfolio.reveal_viewed.v1", { portfolio_key: "evolution", result_status: context.report.hero_portfolio.evolution.status }); }}>{isRevealed ? "Answer revealed" : PORTFOLIO_COPY_V4.evolution.check}</button>{selected && <p className="muted">Your read: {page.options.find((option) => option.key === selected)?.label}</p>}</article>;
}

function EvolutionReveal({ page, context }: { page: StoryPage; context: StoryContext }) {
  const evolution = context.report.hero_portfolio.evolution;
  return <article className="evolution-reveal"><p className="eyebrow">Pool Evolution · report read</p><h2 id={`${page.id}-heading`}>{page.title}</h2>{evolution.status === "available" && evolution.variant ? <><p className="story-lede">{evolutionCopy(evolution)}</p><div className="evolution-columns"><div><span className="eyebrow">Earlier window</span><div className="descriptor-list">{evolution.earlier_traits.map((trait) => <span key={trait}>{trait}</span>)}</div></div><div><span className="eyebrow">Recent window</span><div className="descriptor-list">{evolution.recent_traits.map((trait) => <span key={trait}>{trait}</span>)}</div></div></div></> : <UnavailableMessage limitations={evolution.limitations} />}</article>;
}

function evolutionCopy(evolution: PoolEvolution): string {
  return PORTFOLIO_COPY_V4.evolution.variants[evolution.variant ?? "broadly_stable"];
}

function MirrorPage({ page, context }: { page: StoryPage; context: StoryContext }) {
  const mirror = context.report.hero_portfolio.hero_mirror;
  const open = context.revealed.hero_mirror;
  const reveal = () => {
    context.setRevealed((current) => ({ ...current, hero_mirror: true }));
    track("hero_mirror.reveal_completed.v1", { result_status: mirror.status });
  };
  return <article className={`mirror-card${open ? " is-open" : ""}`} tabIndex={0} onKeyDown={(event) => { if ((event.key === "Enter" || event.key === " ") && !open) { event.preventDefault(); reveal(); } }}><p className="eyebrow">ONE LAST COMPARISON</p><h2 id={`${page.id}-heading`}>Your Hero Mirror</h2>{!open ? <><p className="story-lede">{PORTFOLIO_COPY_V4.hero_mirror.closed || page.body}</p><button type="button" className="mirror-reveal-button" onClick={reveal}>Reveal Hero Mirror</button></> : <MirrorReveal mirror={mirror} />}</article>;
}

function MirrorReveal({ mirror }: { mirror: FreeDnaReportV4["hero_portfolio"]["hero_mirror"] }) {
  if (mirror.status !== "available" || !mirror.hero_name) return <UnavailableMessage limitations={mirror.limitations} />;
  const rows = ["involvement", "finishing", "deaths", "role_context"];
  return <div className="mirror-reveal"><p className="story-lede">{PORTFOLIO_COPY_V4.hero_mirror.available(mirror.hero_name)}</p><p className="muted">{PORTFOLIO_COPY_V4.hero_mirror.qualifier}</p><div className="hero-behavior-table" role="table" aria-label="Player and hero behavior comparison"><div className="hero-behavior-row header" role="row"><span>Observable behavior</span><span>Your history</span><span>{mirror.hero_name}</span></div>{rows.map((key) => <div className="hero-behavior-row" role="row" key={key}><strong>{key.replaceAll("_", " ")}</strong><span>{mirror.player_behavior[key] ?? "Not available"}</span><span>{mirror.hero_behavior[key] ?? "Not available"}</span></div>)}</div><p className="muted">{PORTFOLIO_COPY_V4.hero_mirror.guardrail} {mirror.limitations.join(" ")}</p></div>;
}

function FinalCard({ page, report }: { page: StoryPage; report: FreeDnaReportV4 }) {
  return <article className="final-card"><p className="eyebrow">{page.title}</p><h2 id={`${page.id}-heading`}>{report.identity.display_name || "Your Dota DNA"}</h2><p className="story-lede">{page.body}</p><div className="final-summary"><div><span className="eyebrow">Elements</span><div className="descriptor-list">{report.highlights.element_keys.map((key) => <span key={key}>{report.elements.find((element) => element.key === key)?.label ?? key}</span>)}</div></div><div><span className="eyebrow">Patterns</span><div className="descriptor-list">{report.highlights.pattern_keys.map((key) => <span key={key}>{report.patterns.find((pattern) => pattern.key === key)?.label ?? key}</span>)}</div></div></div>{report.report_id && <ShareControls reportId={report.report_id} reportSchema={report.schema_version} />}</article>;
}

function UnavailableMessage({ limitations }: { limitations: string[] }) {
  return <div className="unavailable-message"><strong>Not enough evidence yet</strong><p>{limitations.join(" ") || "The bounded summary history did not clear the evidence gate."}</p></div>;
}

function FallbackPage({ page }: { page: StoryPage }) {
  return <article className="story-summary"><p className="eyebrow">Dota DNA</p><h2 id={`${page.id}-heading`}>{page.title}</h2>{page.body && <p>{page.body}</p>}</article>;
}
