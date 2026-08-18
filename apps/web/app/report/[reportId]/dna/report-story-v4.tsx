"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type {
  BehaviorElement,
  BehaviorPattern,
  ChoiceOption,
  FreeDnaReportV4,
  HeroException,
  StoryPage,
} from "../../../../../../packages/api-client/src";
import { track } from "../../../lib/analytics";
import { DeepDiveTeaser, EvidenceReceipt, MethodologySheet, Spectrum, StoryPage as StoryPageFrame } from "../../../components/story/primitives";
import ShareControls from "../../../components/share/share-controls";

export default function ReportStoryV4({ report }: { report: FreeDnaReportV4 }) {
  const pages = useMemo(() => report.pages, [report.pages]);
  const pageRefs = useRef<Record<string, HTMLElement | null>>({});
  const [activePage, setActivePage] = useState(pages[0]?.id ?? "");
  const activePageRef = useRef(activePage);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const seenPageIds = useRef<Set<string>>(new Set());
  const elements = useMemo(() => new Map(report.elements.map((item) => [item.key, item])), [report.elements]);
  const patterns = useMemo(() => new Map(report.patterns.map((item) => [item.key, item])), [report.patterns]);

  useEffect(() => {
    document.documentElement.dataset.reportStory = "true";
    const emitPageImpression = (page: StoryPage) => {
      if (seenPageIds.current.has(page.id)) return;
      seenPageIds.current.add(page.id);
      const base = { page: page.id, page_kind: page.kind, section: page.section, report_schema_version: report.schema_version };
      track("report.page_viewed.v1", base);
      if (page.kind === "element_scan") track("report.element_scan_viewed.v1", base);
      if (page.kind === "element_highlight") track("report.element_highlight_viewed.v1", { ...base, element_key: page.element_key ?? null });
      if (page.kind === "pattern_highlight") track("report.pattern_viewed.v1", { ...base, pattern_key: page.pattern_key ?? null });
      if (page.kind === "hero_common_thread_question" || page.kind === "hero_exception_question" || page.kind === "pool_evolution_question") {
        track("hero_portfolio.question_viewed.v1", { ...base, question_key: page.portfolio_key ?? page.kind, portfolio_model_version: report.versions.hero_portfolio });
      }
    };
    const observer = new IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting || entry.intersectionRatio < 0.55) continue;
        const id = entry.target.getAttribute("data-page-id");
        const page = pages.find((item) => item.id === id);
        if (!id || !page) continue;
        if (id !== activePageRef.current) {
          activePageRef.current = id;
          setActivePage(id);
        }
        emitPageImpression(page);
      }
    }, { threshold: [0.55, 0.8] });
    Object.values(pageRefs.current).forEach((element) => element && observer.observe(element));
    if (pages[0]) emitPageImpression(pages[0]);
    return () => {
      observer.disconnect();
      delete document.documentElement.dataset.reportStory;
    };
  }, [pages, report.schema_version, report.versions.hero_portfolio]);

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
  const [scanStage, setScanStage] = useState<"scanning" | "ready">("scanning");

  useEffect(() => {
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduced) {
      setScanStage("ready");
      return;
    }
    const timer = window.setTimeout(() => setScanStage("ready"), 700);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <article className={`element-scan is-${scanStage}`} data-scan-state={scanStage}>
      <p className="eyebrow">17 Elements · summary history only</p>
      <h2 id={`${page.id}-heading`}>{page.title}</h2>
      <p className="story-lede" aria-live="polite">{scanStage === "scanning" ? page.content?.scanning_body ?? page.body : page.content?.ready_body ?? page.body}</p>
      <div className="element-scan-grid">
        {report.elements.map((element, index) => <ElementTile key={element.key} element={element} featured={scanStage === "ready" && highlightKeys.has(element.key)} scanIndex={index} />)}
      </div>
      <button type="button" className="methodology-button" onClick={() => setMethodologyOpen(true)}>How the Elements are measured</button>
      <MethodologySheet open={context.methodologyOpen} title="Observable Elements" body="Each Element is a reviewed, versioned summary-history measurement. Unavailable fields stay unavailable; a score is never filled with a neutral guess." onClose={() => setMethodologyOpen(false)} />
    </article>
  );
}

function ElementTile({ element, featured = false, scanIndex = 0 }: { element: BehaviorElement; featured?: boolean; scanIndex?: number }) {
  return (
    <article className={`element-tile is-${element.status}${featured ? " is-featured" : ""}`} style={{ "--scan-index": scanIndex } as React.CSSProperties}>
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
      <p className="story-lede">{page.content?.observation ?? page.body}</p>
      <Spectrum score={element.score} left={element.axis.left} right={element.axis.right} disabled={element.status === "unavailable"} />
      <div className="signal-status"><strong>{element.zone ?? "Signal unavailable"}</strong><span>{element.confidence} confidence · {element.sample_size ? `n=${element.sample_size}` : "no readable sample"}</span></div>
      {page.content?.why_highlight && <p>{page.content.why_highlight}</p>}
      <EvidenceReceipt evidence={element.receipts} />
      {page.content?.evidence && <p className="muted">{page.content.evidence}</p>}
      {page.content?.what_to_notice && <p><strong>What to notice.</strong> {page.content.what_to_notice}</p>}
      {page.content?.guardrail && <p className="muted"><strong>Do not overread this.</strong> {page.content.guardrail}</p>}
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
      <p className="eyebrow">Pattern highlight</p>
      <h2 id={`${page.id}-heading`}>{pattern.label}</h2>
      <p className="story-lede">{page.content?.meaning ?? page.body}</p>
      <div className="pattern-verdict"><strong>What these signals share</strong><span>{pattern.confidence} confidence</span></div>
      {page.content?.observations && <div className="pattern-observations"><span className="eyebrow">What we observed</span>{page.content.observations.map((observation) => <p key={observation}>{observation}</p>)}</div>}
      {page.content?.worth_noticing && <p><strong>The part worth noticing.</strong> {page.content.worth_noticing}</p>}
      {page.content?.player_read && <p><strong>What this says about your Dota.</strong> {page.content.player_read}</p>}
      <EvidenceReceipt evidence={pattern.receipts} />
      <div className="pattern-ingredients-visible">
        <span className="eyebrow">Element ingredients</span>
        <IngredientGroup title="Required Elements" keys={pattern.element_keys} ingredientMap={ingredientMap} />
        {pattern.modifier_element_keys.length > 0 && <IngredientGroup title="Modifier Elements" keys={pattern.modifier_element_keys} ingredientMap={ingredientMap} />}
      </div>
      <details className="pattern-ingredients" onToggle={(event) => { if ((event.currentTarget as HTMLDetailsElement).open) track("report.pattern_element_expanded.v1", { pattern_key: pattern.key }); }}>
        <summary>See methodology detail</summary>
        <div className="ingredient-list"><span>Relationship strength: {Math.round(pattern.strength * 100)}% · Tier {pattern.tier} · {pattern.family}</span></div>
      </details>
      {page.content?.takeaway && <p><strong>Useful takeaway.</strong> {page.content.takeaway}</p>}
      {page.content?.guardrail && <p className="muted"><strong>Do not overread this.</strong> {page.content.guardrail}</p>}
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
    track("hero_portfolio.answer_selected.v1", {
      question_key: kind,
      selected_option_key: option.key,
      matched_computed_answer: correct !== null && option.key === correct,
      report_schema_version: context.report.schema_version,
      portfolio_model_version: context.report.versions.hero_portfolio,
    });
  };
  const reveal = () => {
    context.setRevealed((current) => ({ ...current, [kind]: true }));
    track("hero_portfolio.reveal_viewed.v1", {
      question_key: kind,
      matched_computed_answer: selected !== undefined && selected === correct,
      report_schema_version: context.report.schema_version,
      portfolio_model_version: context.report.versions.hero_portfolio,
    });
  };
  return (
    <article className="portfolio-question">
      <p className="eyebrow">Hero Portfolio · {kind === "common_thread" ? "Common Thread" : "The Exception"}</p>
      <h2 id={`${page.id}-heading`}>{page.title}</h2>
      <p className="story-lede">{page.body}</p>
      {unavailable ? <UnavailableMessage limitations={result.limitations} /> : <>
        <div className="choice-grid" role="radiogroup" aria-labelledby={`${page.id}-heading`}>
          {options.map((option) => <button key={option.key} type="button" role="radio" aria-checked={selected === option.key} className={selected === option.key ? "is-selected" : ""} onClick={() => choose(option)}>{option.label}</button>)}
        </div>
        {selected && <p className="choice-status" role="status" aria-live="polite">Selected: {options.find((option) => option.key === selected)?.label}</p>}
        <button type="button" className="reveal-button" disabled={!selected || isRevealed} onClick={reveal}>{isRevealed ? "Answer revealed" : "Reveal"}</button>
        {isRevealed && <div aria-live="polite"><PortfolioReveal kind={kind} selected={selected} correct={correct} result={result} content={page.content} /></div>}
      </>}
    </article>
  );
}

function PortfolioReveal({ kind, selected, correct, result, content }: { kind: "common_thread" | "exception"; selected?: string; correct: string | null; result: FreeDnaReportV4["hero_portfolio"]["common_thread"] | HeroException; content?: StoryPage["content"] }) {
  const right = selected !== undefined && selected === correct;
  const selectedOption = result.options.find((option) => option.key === selected);
  const resultLabel = right ? content?.correct_label ?? "You spotted it." : content?.incorrect_label ?? "A useful correction.";
  if (kind === "common_thread") {
    const common = result as FreeDnaReportV4["hero_portfolio"]["common_thread"];
    return <div className="portfolio-reveal"><span className="eyebrow">{resultLabel}</span><h3>{common.trait_label ?? "No clear common thread"}</h3><p>{selectedOption?.feedback ?? common.limitations.join(" ")}</p><div className="descriptor-list">{common.secondary_traits.map((trait) => <span key={trait}>{trait}</span>)}</div></div>;
  }
  const exception = result as HeroException;
  return <div className="portfolio-reveal"><span className="eyebrow">{resultLabel}</span><h3>{exception.hero_name ?? "No clear exception"}</h3><p>{selectedOption?.feedback ?? exception.limitations.join(" ")}</p><div className="descriptor-list">{exception.exception_traits.map((trait) => <span key={trait}>{trait}</span>)}</div></div>;
}

function EvolutionQuestion({ page, context }: { page: StoryPage; context: StoryContext }) {
  const selected = context.answers.evolution;
  const isRevealed = context.revealed.evolution;
  const choose = (option: ChoiceOption) => {
    context.setAnswers((current) => ({ ...current, evolution: option.key }));
    track("hero_portfolio.answer_selected.v1", {
      question_key: "evolution",
      selected_option_key: option.key,
      matched_computed_answer: null,
      report_schema_version: context.report.schema_version,
      portfolio_model_version: context.report.versions.hero_portfolio,
    });
  };
  return <article className="portfolio-question"><p className="eyebrow">Hero Portfolio · Pool Evolution</p><h2 id={`${page.id}-heading`}>{page.title}</h2><p className="story-lede">{page.body}</p><div className="choice-grid" role="radiogroup" aria-labelledby={`${page.id}-heading`}>{page.options.map((option) => <button key={option.key} type="button" role="radio" aria-checked={selected === option.key} className={selected === option.key ? "is-selected" : ""} onClick={() => choose(option)}>{option.label}</button>)}</div>{selected && <p className="choice-status" role="status" aria-live="polite">Your read: {page.options.find((option) => option.key === selected)?.label}</p>}<button type="button" className="reveal-button" disabled={!selected || isRevealed} onClick={() => { context.setRevealed((current) => ({ ...current, evolution: true })); track("hero_portfolio.reveal_viewed.v1", { question_key: "evolution", matched_computed_answer: null, report_schema_version: context.report.schema_version, portfolio_model_version: context.report.versions.hero_portfolio }); }}>{isRevealed ? "Answer revealed" : "Reveal"}</button></article>;
}

function EvolutionReveal({ page, context }: { page: StoryPage; context: StoryContext }) {
  const evolution = context.report.hero_portfolio.evolution;
  if (!context.revealed.evolution) {
    return <article className="evolution-reveal"><p className="eyebrow">Pool Evolution · report read</p><h2 id={`${page.id}-heading`}>{page.title}</h2><div className="unavailable-message"><strong>{page.content?.locked_copy ?? "Complete the self-assessment above to see the report read."}</strong></div></article>;
  }
  return <article className="evolution-reveal"><p className="eyebrow">Pool Evolution · report read</p><h2 id={`${page.id}-heading`}>{page.title}</h2>{evolution.status === "available" && evolution.variant ? <><p className="story-lede">{page.content?.copy ?? page.body}</p><div className="evolution-columns"><div><span className="eyebrow">Earlier window · n={evolution.earlier_sample_size}</span><div className="descriptor-list">{evolution.earlier_traits.map((trait) => <span key={trait}>{trait}</span>)}</div></div><div><span className="eyebrow">Recent window · n={evolution.recent_sample_size}</span><div className="descriptor-list">{evolution.recent_traits.map((trait) => <span key={trait}>{trait}</span>)}</div></div></div></> : <UnavailableMessage limitations={evolution.limitations} />}</article>;
}

function MirrorPage({ page, context }: { page: StoryPage; context: StoryContext }) {
  const mirror = context.report.hero_portfolio.hero_mirror;
  const open = context.revealed.hero_mirror;
  const [dragProgress, setDragProgress] = useState(0);
  const dragProgressRef = useRef(0);
  const pointer = useRef<{ id: number; startX: number; startY: number; dragging: boolean } | null>(null);
  const started = useRef(false);
  const completed = useRef(false);
  const trackStart = (interaction: string) => {
    if (started.current) return;
    started.current = true;
    track("hero_mirror.reveal_started.v1", { interaction, report_schema_version: context.report.schema_version, portfolio_model_version: context.report.versions.hero_mirror });
  };
  const reveal = (interaction: string) => {
    trackStart(interaction);
    if (open) return;
    context.setRevealed((current) => ({ ...current, hero_mirror: true }));
    if (!completed.current) {
      completed.current = true;
      track("hero_mirror.reveal_completed.v1", { result_status: mirror.status, report_schema_version: context.report.schema_version, portfolio_model_version: context.report.versions.hero_mirror });
    }
  };
  const onPointerDown = (event: React.PointerEvent<HTMLElement>) => {
    if (open || (event.pointerType === "mouse" && event.button !== 0)) return;
    pointer.current = { id: event.pointerId, startX: event.clientX, startY: event.clientY, dragging: false };
  };
  const onPointerMove = (event: React.PointerEvent<HTMLElement>) => {
    const current = pointer.current;
    if (!current || current.id !== event.pointerId || open) return;
    const dx = event.clientX - current.startX;
    const dy = event.clientY - current.startY;
    if (!current.dragging) {
      if (Math.abs(dx) < 8 || Math.abs(dx) <= Math.abs(dy)) return;
      current.dragging = true;
      event.currentTarget.setPointerCapture(event.pointerId);
      trackStart("drag");
    }
    event.preventDefault();
    const width = Math.max(event.currentTarget.clientWidth, 1);
    const progress = Math.min(1, Math.abs(dx) / width);
    dragProgressRef.current = progress;
    setDragProgress(progress);
  };
  const onPointerUp = (event: React.PointerEvent<HTMLElement>) => {
    const current = pointer.current;
    if (!current || current.id !== event.pointerId) return;
    if (current.dragging) {
      if (dragProgressRef.current >= 0.35) reveal("drag");
      else {
        dragProgressRef.current = 0;
        setDragProgress(0);
      }
      if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    }
    pointer.current = null;
  };
  const onPointerCancel = () => {
    pointer.current = null;
    dragProgressRef.current = 0;
    setDragProgress(0);
  };
  return <article className={`mirror-card${open ? " is-open" : ""}${dragProgress > 0 && !open ? " is-dragging" : ""}`} style={{ "--mirror-progress": dragProgress } as React.CSSProperties} tabIndex={0} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerCancel} onKeyDown={(event) => { if ((event.key === "Enter" || event.key === " ") && !open) { event.preventDefault(); reveal("keyboard"); } }}><div className="mirror-cover"><p className="eyebrow">ONE LAST COMPARISON</p><h2 id={`${page.id}-heading`}>Your Hero Mirror</h2>{!open && <><p className="story-lede">{page.content?.closed ?? page.body}</p><button type="button" className="mirror-reveal-button" onClick={() => reveal("button")}>Reveal Hero Mirror</button><p className="muted mirror-gesture-hint">Swipe across this card, or use the button.</p></>}</div>{open && <MirrorReveal mirror={mirror} content={page.content ?? {}} />}</article>;
}

function MirrorReveal({ mirror, content }: { mirror: FreeDnaReportV4["hero_portfolio"]["hero_mirror"]; content: StoryPage["content"] }) {
  if (mirror.status !== "available" || !mirror.hero_name) return <UnavailableMessage limitations={mirror.limitations} />;
  const rows = ["involvement", "finishing", "deaths", "role_context"];
  return <div className="mirror-reveal" aria-live="polite"><p className="story-lede">{content.available ?? `Hero Mirror: ${mirror.hero_name}`}</p><p className="muted">{content.qualifier}</p><div className="hero-behavior-table" role="table" aria-label="Player and hero behavior comparison"><div className="hero-behavior-row header" role="row"><span>Observable behavior</span><span>Your history</span><span>{mirror.hero_name}</span></div>{rows.map((key) => <div className="hero-behavior-row" role="row" key={key}><strong>{key.replaceAll("_", " ")}</strong><span>{mirror.player_behavior[key] ?? "Not available"}</span><span>{mirror.hero_behavior[key] ?? "Not available"}</span></div>)}</div><p className="muted">{content.guardrail} {mirror.limitations.join(" ")}</p></div>;
}

function FinalCard({ page, report }: { page: StoryPage; report: FreeDnaReportV4 }) {
  const strongestElements = report.highlights.element_keys.map((key) => report.elements.find((element) => element.key === key)).filter((element): element is BehaviorElement => Boolean(element));
  const strongestPatterns = report.highlights.pattern_keys.map((key) => report.patterns.find((pattern) => pattern.key === key)).filter((pattern): pattern is BehaviorPattern => Boolean(pattern));
  return <article className="final-card"><p className="eyebrow">{page.title}</p><h2 id={`${page.id}-heading`}>{report.identity.display_name || "Your Dota DNA"}</h2><p className="story-lede">{page.body}</p><div className="final-summary"><div><span className="eyebrow">Elements</span><div className="descriptor-list">{strongestElements.map((element) => <span key={element.key}>{element.label} · {element.zone ?? "Unavailable"}</span>)}</div></div><div><span className="eyebrow">Patterns</span><div className="descriptor-list">{strongestPatterns.map((pattern) => <span key={pattern.key}>{pattern.label}</span>)}</div></div><div><span className="eyebrow">Hero Portfolio</span><p>{report.shares.final.hero_portfolio.common_thread ?? "No clear Common Thread yet."}</p><p>{report.shares.final.hero_portfolio.exception_hero ? `Exception · ${report.shares.final.hero_portfolio.exception_hero}` : "No clear Exception yet."}</p><p>{report.shares.final.hero_portfolio.pool_direction ?? "Pool Evolution is unavailable yet."}</p></div><div><span className="eyebrow">Hero Mirror</span><p>{report.shares.final.hero_mirror?.hero_name ?? "No clear Mirror yet."}</p></div></div>{report.report_id && <ShareControls reportId={report.report_id} reportSchema={report.schema_version} />}</article>;
}

function UnavailableMessage({ limitations }: { limitations: string[] }) {
  return <div className="unavailable-message"><strong>Not enough evidence yet</strong><p>{limitations.join(" ") || "The bounded summary history did not clear the evidence gate."}</p></div>;
}

function FallbackPage({ page }: { page: StoryPage }) {
  return <article className="story-summary"><p className="eyebrow">Dota DNA</p><h2 id={`${page.id}-heading`}>{page.title}</h2>{page.body && <p>{page.body}</p>}</article>;
}
