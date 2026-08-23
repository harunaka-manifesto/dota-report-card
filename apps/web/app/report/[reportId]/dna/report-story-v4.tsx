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
import ShareControls from "../../../components/share/share-controls";
import { GLYPH_BY_KEY, GLYPH_REGISTRY, Glyph, glyphRegistryIsUnique, type GlyphDefinition } from "../../../components/story/glyphs";

export type ReportChapter = {
  id: "summary" | "elements" | "patterns" | "heroes" | "you";
  label: string;
  palette: "summary" | "elements" | "patterns" | "heroes" | "you";
};

export const REPORT_CHAPTERS: readonly ReportChapter[] = [
  { id: "summary", label: "Summary", palette: "summary" },
  { id: "elements", label: "Elements", palette: "elements" },
  { id: "patterns", label: "Patterns", palette: "patterns" },
  { id: "heroes", label: "Heroes", palette: "heroes" },
  { id: "you", label: "You", palette: "you" },
];

const ELEMENT_COPY: Record<string, string> = {
  hero_pool_breadth: "You keep more answers on the table than most fights strictly require.",
  hero_pool_stability: "A steady center keeps your decisions recognizable when the map gets noisy.",
  hero_exploration_rate: "You are willing to leave the familiar route when it looks worth the trouble.",
  toolkit_breadth: "Your heroes solve different problems, even when your taste is consistent.",
  post_loss_familiarity_shift: "A rough game changes what you reach for next, but not always in the obvious direction.",
  role_breadth: "You can occupy more than one job without turning the draft into a group project.",
  combat_involvement: "You tend to be present where the important decisions become visible.",
  finisher_orientation: "When a fight closes, you are often close to the final punctuation.",
  death_exposure: "You spend time in the places where the map can answer back.",
  off_pool_performance: "Your familiar decisions travel better than your hero names suggest.",
  off_pool_activity_stability: "A new hero does not automatically make you disappear from the game.",
  performance_volatility: "Some sessions arrive with a little more weather than others.",
  recent_form_shift: "Your recent games have a direction, not just a collection of incidents.",
  recent_activity_shift: "Your recent pace has its own rhythm, and it is not particularly shy about it.",
  session_length_tendency: "You tend to stay with a session until it feels finished—or until it objects.",
  late_session_performance: "The later part of a session adds a different shade to your usual pattern.",
  post_loss_activity_shift: "After a loss, your tempo changes before your identity does.",
  post_loss_performance_response: "A loss is information for you, even when it arrives wearing a smug little hat.",
};

const PATTERN_COPY: Record<string, { lead: string; detail: string; experiment: string }> = {
  same_playbook: { lead: "Your hero names change. The job keeps coming back.", detail: "Different picks keep finding a familiar way to help.", experiment: "Try one hero that keeps the job intact while changing the route there." },
  comfort_edge: { lead: "Your anchors are clearer than the learning problem.", detail: "The heroes you know best give you a reliable place to stretch from.", experiment: "Borrow one demand from the edge of your pool and keep one anchor decision intact." },
  partial_transfer: { lead: "The transfer gap is real. Its source is still taking the scenic route.", detail: "Your familiar involvement does not always arrive with familiar results.", experiment: "Change one entry decision on an unfamiliar hero and leave the rest alone." },
  versatile_core: { lead: "Small pool. Different answers.", detail: "A compact group of heroes is already covering more than one kind of problem.", experiment: "Try the missing job with the least dramatic change to your current habits." },
  proven_flexibility: { lead: "Your range is real, just spread out.", detail: "Flexibility shows up as a repeatable habit rather than a one-week stunt.", experiment: "Keep one reliable anchor visible while you rotate the next answer." },
  controlled_presence: { lead: "You stay involved without paying the full cost.", detail: "You find ways to matter in a fight without volunteering for every consequence.", experiment: "Keep the same presence and practice leaving one beat earlier." },
  session_fade: { lead: "Later games ask for a little more from you.", detail: "Your session has a point where the familiar rhythm starts to soften.", experiment: "Add a reset before that point: water, a pause, or one deliberately simple draft." },
  session_rise: { lead: "You warm into the right shape.", detail: "The session tends to improve once your first decisions have had time to settle.", experiment: "Start with a familiar job, then use the later game to widen the answer." },
  bounceback: { lead: "A loss can sharpen your next game.", detail: "You often return with a more useful version of the same intent.", experiment: "Name the one decision you want to repeat before the next queue pops." },
  performance_slide: { lead: "A loss can make the next game heavier.", detail: "Your next decisions sometimes carry the previous game farther than they should.", experiment: "Change one transition after a loss instead of rebuilding the entire plan." },
  presence_tax: { lead: "You get to the important places—and sometimes pay toll on the way out.", detail: "High involvement can bring a real cost when the context turns against you.", experiment: "Keep the presence; practice identifying the first safe exit." },
};

const EVOLUTION_LABELS: Record<string, string> = {
  new_heroes_new_toolkit: "New heroes. New tools.",
  new_heroes_same_toolkit: "New heroes. Same taste.",
  stable_core_new_branch: "A stable core with a new branch.",
  broadly_stable: "The pool is holding its shape.",
};

const ELEMENT_ORDER = [
  "hero_pool_breadth", "hero_pool_stability", "hero_exploration_rate", "toolkit_breadth", "post_loss_familiarity_shift", "role_breadth", "combat_involvement", "finisher_orientation", "death_exposure", "off_pool_performance", "off_pool_activity_stability", "performance_volatility", "recent_form_shift", "recent_activity_shift", "session_length_tendency", "late_session_performance", "post_loss_activity_shift", "post_loss_performance_response",
];

const PATTERN_ORDER = ["same_playbook", "comfort_edge", "partial_transfer", "versatile_core", "proven_flexibility", "controlled_presence", "session_fade", "session_rise", "bounceback", "performance_slide", "presence_tax"];

export default function ReportStoryV4({ report }: { report: FreeDnaReportV4 }) {
  const [activeChapter, setActiveChapter] = useState<ReportChapter["id"]>("summary");
  const [selectedElement, setSelectedElement] = useState<string | null>(null);
  const [selectedPattern, setSelectedPattern] = useState<string | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [revealed, setRevealed] = useState<Record<string, boolean>>({});
  const chapterRefs = useRef<Record<string, HTMLElement | null>>({});
  const seenChapters = useRef(new Set<string>());

  const elements = useMemo(() => orderByKeys(report.elements, ELEMENT_ORDER), [report.elements]);
  const patterns = useMemo(() => orderByKeys(report.patterns.filter((pattern) => pattern.status === "qualified"), PATTERN_ORDER), [report.patterns]);
  const readableElements = useMemo(() => elements.filter((element) => element.status !== "unavailable"), [elements]);
  const leadingElement = useMemo(() => {
    const highlighted = report.highlights.element_keys.map((key) => elements.find((element) => element.key === key)).find((element) => element && element.status !== "unavailable");
    return highlighted ?? readableElements[0] ?? null;
  }, [elements, readableElements, report.highlights.element_keys]);
  const leadingPattern = useMemo(() => {
    const highlighted = report.highlights.pattern_keys.map((key) => patterns.find((pattern) => pattern.key === key)).find(Boolean);
    return highlighted ?? patterns[0] ?? null;
  }, [patterns, report.highlights.pattern_keys]);
  const chosenElement = readableElements.find((element) => element.key === selectedElement) ?? leadingElement;
  const chosenPattern = patterns.find((pattern) => pattern.key === selectedPattern) ?? leadingPattern;
  const pageByKind = useMemo(() => new Map(report.pages.map((page) => [page.kind, page])), [report.pages]);
  const elementPages = useMemo(() => new Map(report.pages.filter((page) => page.kind === "element_highlight" && page.element_key).map((page) => [page.element_key as string, page])), [report.pages]);
  const patternPages = useMemo(() => new Map(report.pages.filter((page) => page.kind === "pattern_highlight" && page.pattern_key).map((page) => [page.pattern_key as string, page])), [report.pages]);

  useEffect(() => {
    document.documentElement.dataset.reportStory = "true";
    document.documentElement.style.scrollSnapType = "none";
    const observers = Object.values(chapterRefs.current).filter(Boolean).map((element) => {
      const observer = new IntersectionObserver((entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting || entry.intersectionRatio < 0.35) continue;
          const id = entry.target.getAttribute("data-chapter-id") as ReportChapter["id"] | null;
          if (!id) continue;
          setActiveChapter(id);
          if (!seenChapters.current.has(id)) {
            seenChapters.current.add(id);
            track("report.chapter_viewed.v1", { chapter: id, report_schema_version: report.schema_version });
          }
        }
      }, { threshold: [0.35, 0.6] });
      observer.observe(element as Element);
      return observer;
    });
    if (!seenChapters.current.has("summary")) {
      seenChapters.current.add("summary");
      track("report.chapter_viewed.v1", { chapter: "summary", report_schema_version: report.schema_version });
    }
    return () => {
      observers.forEach((observer) => observer.disconnect());
      document.documentElement.style.removeProperty("scroll-snap-type");
      delete document.documentElement.dataset.reportStory;
    };
  }, [report.schema_version]);

  function navigate(chapter: ReportChapter["id"]) {
    setActiveChapter(chapter);
    track("report.chapter_navigation.v1", { chapter, source: "report_nav", report_schema_version: report.schema_version });
    const behavior = typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
    chapterRefs.current[chapter]?.scrollIntoView({ behavior, block: "start" });
  }

  function chooseAnswer(question: string, option: ChoiceOption) {
    setAnswers((current) => ({ ...current, [question]: option.key }));
    const result = report.hero_portfolio[question as "common_thread" | "exception" | "evolution"];
    const correct = "correct_option_key" in result ? result.correct_option_key : null;
    track("hero_portfolio.answer_selected.v1", { question_key: question, selected_option_key: option.key, matched_computed_answer: correct !== null && option.key === correct, report_schema_version: report.schema_version, portfolio_model_version: report.versions.hero_portfolio });
  }

  function revealAnswer(question: string) {
    setRevealed((current) => ({ ...current, [question]: true }));
    const result = report.hero_portfolio[question as "common_thread" | "exception" | "evolution"];
    const correct = "correct_option_key" in result ? result.correct_option_key : null;
    track("hero_portfolio.reveal_viewed.v1", { question_key: question, matched_computed_answer: answers[question] !== undefined && correct !== null && answers[question] === correct, report_schema_version: report.schema_version, portfolio_model_version: report.versions.hero_portfolio });
  }

  return <main className="report-story report-story-v5" data-glyph-registry-size={GLYPH_REGISTRY.length} data-glyph-registry-unique={glyphRegistryIsUnique() ? "true" : "false"} data-glyph-registry-geometries={GLYPH_REGISTRY.map((definition) => definition.geometry).join(",")} aria-label="Your Dota identity report">
    <DesktopChapterRail activeChapter={activeChapter} onNavigate={navigate} />
    <div className="report-story-content">
      <header className="report-topline"><a className="report-wordmark" href="#summary" onClick={(event) => { event.preventDefault(); navigate("summary"); }}>FREE DNA</a><span>PERSONAL IDENTITY REPORT</span><span className="report-topline-name">{report.identity.display_name || "Anonymous player"}</span></header>
      <ChapterSection id="summary" palette="summary" chapterRefs={chapterRefs}><SummaryChapter report={report} leadingElement={leadingElement} leadingPattern={leadingPattern} elementPages={elementPages} patternPages={patternPages} onNavigate={navigate} /></ChapterSection>
      <ChapterSection id="elements" palette="elements" chapterRefs={chapterRefs}><ElementsChapter elements={readableElements} elementPages={elementPages} selected={chosenElement} onSelect={(element) => { setSelectedElement(element.key); track("report.element_selected.v1", { element_key: element.key, report_schema_version: report.schema_version }); }} /></ChapterSection>
      <ChapterSection id="patterns" palette="patterns" chapterRefs={chapterRefs}><PatternsChapter patterns={patterns} patternPages={patternPages} selected={chosenPattern} onSelect={(pattern) => { setSelectedPattern(pattern.key); track("report.pattern_selected.v1", { pattern_key: pattern.key, report_schema_version: report.schema_version }); }} /></ChapterSection>
      <ChapterSection id="heroes" palette="heroes" chapterRefs={chapterRefs}><HeroesChapter report={report} pageByKind={pageByKind} answers={answers} revealed={revealed} onChoose={chooseAnswer} onReveal={revealAnswer} /></ChapterSection>
      <ChapterSection id="you" palette="you" chapterRefs={chapterRefs}><YouChapter report={report} pageByKind={pageByKind} revealed={Boolean(revealed.hero_mirror)} onReveal={() => setRevealed((current) => ({ ...current, hero_mirror: true }))} /></ChapterSection>
    </div>
    <MobileChapterDock activeChapter={activeChapter} onNavigate={navigate} />
  </main>;
}

function ChapterSection({ id, palette, chapterRefs, children }: { id: ReportChapter["id"]; palette: ReportChapter["palette"]; chapterRefs: React.MutableRefObject<Record<string, HTMLElement | null>>; children: React.ReactNode }) {
  return <section id={id} data-chapter-id={id} data-palette={palette} className={`report-chapter report-chapter-${palette}`} ref={(element) => { chapterRefs.current[id] = element; }} aria-labelledby={`${palette}-heading`}>{children}</section>;
}

function DesktopChapterRail({ activeChapter, onNavigate }: { activeChapter: ReportChapter["id"]; onNavigate: (chapter: ReportChapter["id"]) => void }) {
  return <aside className="chapter-rail" aria-label="Report chapters"><span className="rail-mark" aria-hidden="true">◈</span><nav>{REPORT_CHAPTERS.map((chapter) => <button key={chapter.id} type="button" className={activeChapter === chapter.id ? "is-active" : ""} aria-current={activeChapter === chapter.id ? "page" : undefined} onClick={() => onNavigate(chapter.id)}><span className="rail-dot" aria-hidden="true" />{chapter.label}</button>)}</nav><span className="rail-footer">DOTA<br />IDENTITY</span></aside>;
}

function MobileChapterDock({ activeChapter, onNavigate }: { activeChapter: ReportChapter["id"]; onNavigate: (chapter: ReportChapter["id"]) => void }) {
  return <nav className="chapter-dock" aria-label="Report chapters">{REPORT_CHAPTERS.map((chapter) => <button key={chapter.id} type="button" className={activeChapter === chapter.id ? "is-active" : ""} aria-current={activeChapter === chapter.id ? "page" : undefined} onClick={() => onNavigate(chapter.id)}><span className="dock-glyph" aria-hidden="true">{chapter.id === "summary" ? "✦" : chapter.id === "elements" ? "◇" : chapter.id === "patterns" ? "⌘" : chapter.id === "heroes" ? "✷" : "●"}</span><span>{chapter.label}</span></button>)}</nav>;
}

function SummaryChapter({ report, leadingElement, leadingPattern, elementPages, patternPages, onNavigate }: { report: FreeDnaReportV4; leadingElement: BehaviorElement | null; leadingPattern: BehaviorPattern | null; elementPages: Map<string, StoryPage>; patternPages: Map<string, StoryPage>; onNavigate: (chapter: ReportChapter["id"]) => void }) {
  const elementPage = leadingElement ? elementPages.get(leadingElement.key) : undefined;
  const patternPage = leadingPattern ? patternPages.get(leadingPattern.key) : undefined;
  const localIdentity = leadingPattern ? PATTERN_COPY[leadingPattern.key]?.lead ?? `${leadingPattern.label} is part of your current Dota shape.` : leadingElement ? ELEMENT_COPY[leadingElement.key] : "Your Dota has a shape. It is not obliged to fit neatly in a box.";
  const localSignature = leadingPattern ? PATTERN_COPY[leadingPattern.key]?.detail ?? "A pattern that keeps its appointment." : leadingElement ? ELEMENT_COPY[leadingElement.key] : "The clearest parts of your report are still taking form.";
  const identityCopy = safeCatalogCopy(patternPage?.content.presentation_copy?.headline ?? patternPage?.content.meaning ?? elementPage?.content.observation ?? elementPage?.content.why_highlight ?? elementPage?.body, localIdentity);
  const signature = safeCatalogCopy(patternPage?.content.presentation_copy?.subheadline ?? patternPage?.content.presentation_copy?.interpretation.body ?? elementPage?.content.why_highlight ?? elementPage?.content.observation ?? elementPage?.body, localSignature);
  return <div className="chapter-inner summary-inner"><div className="chapter-kicker"><span className="chapter-index">01</span><span>SUMMARY / YOUR CURRENT SHAPE</span></div><div className="summary-hero-grid"><div className="summary-copy"><p className="eyebrow">{report.identity.display_name || "Your Dota identity"}</p><h1 id="summary-heading">{identityCopy}</h1><p className="chapter-lede">{signature}</p><div className="summary-actions"><button type="button" className="primary-action" onClick={() => onNavigate("elements")}>See the pieces <span aria-hidden="true">↘</span></button><button type="button" className="quiet-action" onClick={() => onNavigate("heroes")}>Meet the hero pool</button></div></div><div className="identity-tile summary-tile"><Glyph decorative glyph={leadingPattern?.key ?? leadingElement?.key ?? "hero_pool_breadth"} size={172} /><span className="tile-caption">YOUR LEADING SIGNAL</span><strong>{leadingPattern?.label ?? leadingElement?.label ?? "Still forming"}</strong><p>{leadingPattern ? "A pattern that keeps its appointment." : "A useful first line, with more on the way."}</p></div></div><div className="summary-strip"><span><strong>01</strong> Read the headline</span><span><strong>02</strong> Follow the texture</span><span><strong>03</strong> Choose your next experiment</span></div></div>;
}

function ElementsChapter({ elements, elementPages, selected, onSelect }: { elements: BehaviorElement[]; elementPages: Map<string, StoryPage>; selected: BehaviorElement | null; onSelect: (element: BehaviorElement) => void }) {
  return <div className="chapter-inner"><ChapterHeading index="02" eyebrow="ELEMENTS / THE RAW MATERIAL" title="The pieces of your Dota pattern" body="These are the tendencies that keep turning up in the way you move through a game." palette="elements" />{elements.length === 0 ? <UnavailableMessage message="Your Elements are still forming. There is nothing useful to force into a tile." /> : <><div className="glyph-grid element-grid">{elements.map((element) => <button key={element.key} type="button" className={`glyph-tile${selected?.key === element.key ? " is-selected" : ""}`} aria-pressed={selected?.key === element.key} onClick={() => onSelect(element)}><span className="glyph-tile-art"><Glyph decorative glyph={element.key} size={52} /></span><span className="tile-caption">ELEMENT</span><strong>{element.label}</strong><span className="tile-description">{elementNarrative(element, elementPages.get(element.key))}</span></button>)}</div>{selected && <ElementDetail element={selected} page={elementPages.get(selected.key)} />}</>}</div>;
}

function ElementDetail({ element, page }: { element: BehaviorElement; page?: StoryPage }) {
  const score = element.score === null ? null : Math.round(Math.max(0, Math.min(1, element.score)) * 100);
  const localDetail = ELEMENT_COPY[element.key] ?? "A signal with a particular shape.";
  const detail = safeCatalogCopy(page?.content.observation ?? page?.content.meaning ?? page?.content.why_highlight ?? page?.body, localDetail);
  const note = safeCatalogCopy(page?.content.why_highlight, element.zone ? `Right now, this reads as ${element.zone.toLowerCase()}.` : "The useful read is still taking shape.");
  return <article className="detail-panel element-detail" aria-labelledby="element-detail-heading"><div className="detail-art"><Glyph decorative glyph={element.key} size={88} /></div><div className="detail-copy"><p className="eyebrow">{element.label}</p><h3 id="element-detail-heading">{detail}</h3>{score === null ? <p className="detail-note">This one is still finding its edges.</p> : <div className="lean-meter" role="img" aria-label={`${element.label} is leaning toward ${element.axis.right ?? "the right side"}`}><div className="lean-meter-labels"><span>{element.axis.left ?? "Less"}</span><span>{element.axis.right ?? "More"}</span></div><div className="lean-meter-track"><span style={{ left: `${score}%` }} /></div></div>}<p className="detail-note">{note}</p></div></article>;
}

function PatternsChapter({ patterns, patternPages, selected, onSelect }: { patterns: BehaviorPattern[]; patternPages: Map<string, StoryPage>; selected: BehaviorPattern | null; onSelect: (pattern: BehaviorPattern) => void }) {
  return <div className="chapter-inner"><ChapterHeading index="03" eyebrow="PATTERNS / THE CONNECTIONS" title="The habits hiding between the heroes" body="A pattern is the part that keeps happening even when the surface details change." palette="patterns" />{patterns.length === 0 ? <UnavailableMessage message="No pattern wants the spotlight yet. That is a valid answer." /> : <><div className="glyph-grid pattern-grid">{patterns.map((pattern) => { const catalog = patternPages.get(pattern.key); const lead = safeCatalogCopy(catalog?.content.presentation_copy?.headline ?? catalog?.content.meaning ?? catalog?.body, PATTERN_COPY[pattern.key]?.lead ?? "A recurring shape in your current report."); return <button key={pattern.key} type="button" className={`glyph-tile${selected?.key === pattern.key ? " is-selected" : ""}`} aria-pressed={selected?.key === pattern.key} onClick={() => onSelect(pattern)}><span className="glyph-tile-art"><Glyph decorative glyph={pattern.key} size={52} /></span><span className="tile-caption">PATTERN</span><strong>{pattern.label}</strong><span className="tile-description">{lead}</span></button>; })}</div>{selected && <PatternDetail pattern={selected} page={patternPages.get(selected.key)} />}</>}</div>;
}

function PatternDetail({ pattern, page }: { pattern: BehaviorPattern; page?: StoryPage }) {
  const copy = PATTERN_COPY[pattern.key] ?? { lead: pattern.label, detail: "This pattern is part of your current Dota shape.", experiment: "Try one deliberate change and see what remains familiar." };
  const presentation = page?.content.presentation_copy;
  const catalogLead = safeCatalogCopy(presentation?.headline ?? page?.content.meaning ?? page?.body, copy.lead);
  const catalogDetail = safeCatalogCopy(presentation?.interpretation.body ?? presentation?.subheadline, copy.detail);
  const catalogExperiment = safeCatalogCopy(presentation?.recommendation?.body, copy.experiment);
  return <article className="detail-panel pattern-detail" aria-labelledby="pattern-detail-heading"><div className="detail-art"><Glyph decorative glyph={pattern.key} size={92} /></div><div className="detail-copy"><p className="eyebrow">{pattern.label}</p><h3 id="pattern-detail-heading">{catalogDetail}</h3><p>{catalogLead}</p><div className="experiment-card"><span className="tile-caption">NEXT EXPERIMENT</span><strong>{catalogExperiment}</strong></div></div></article>;
}

function HeroesChapter({ report, pageByKind, answers, revealed, onChoose, onReveal }: { report: FreeDnaReportV4; pageByKind: Map<string, StoryPage>; answers: Record<string, string>; revealed: Record<string, boolean>; onChoose: (question: string, option: ChoiceOption) => void; onReveal: (question: string) => void }) {
  const portfolio = report.hero_portfolio;
  const commonPage = pageByKind.get("hero_common_thread_question");
  const exceptionPage = pageByKind.get("hero_exception_question");
  const evolutionPage = pageByKind.get("pool_evolution_question");
  return <div className="chapter-inner"><ChapterHeading index="04" eyebrow="HEROES / THE PORTFOLIO" title="Your hero pool is a point of view" body="The names move around. The way you solve problems leaves a clearer trail." palette="heroes" /><div className="portfolio-overview"><PortfolioStat label="Common thread" value={portfolio.common_thread.trait_label ?? "Still forming"} body={portfolio.common_thread.status === "available" ? "The job that keeps finding you." : "No single job wants to claim the whole room."} /><PortfolioStat label="The exception" value={portfolio.exception.hero_name ?? "No odd one out"} body={portfolio.exception.status === "available" ? "The pick that bends the pattern." : "Your pool is more coherent than dramatic."} /><PortfolioStat label="Pool evolution" value={portfolio.evolution.variant ? EVOLUTION_LABELS[portfolio.evolution.variant] ?? "A new chapter" : "Still in motion"} body="Your current pool, in one honest sentence." /></div><div className="portfolio-questions"><PortfolioQuestion id="hero-common-thread" title="What keeps showing up across your established heroes?" result={portfolio.common_thread} page={commonPage} question="common_thread" answer={answers.common_thread} isRevealed={Boolean(revealed.common_thread)} onChoose={onChoose} onReveal={onReveal} /><PortfolioQuestion id="hero-exception" title="Which hero takes a different route?" result={portfolio.exception} page={exceptionPage} question="exception" answer={answers.exception} isRevealed={Boolean(revealed.exception)} onChoose={onChoose} onReveal={onReveal} /><PortfolioQuestion id="pool-evolution-question" title="How has your pool changed?" result={portfolio.evolution} page={evolutionPage} question="evolution" answer={answers.evolution} isRevealed={Boolean(revealed.evolution)} onChoose={onChoose} onReveal={onReveal} /></div></div>;
}

function PortfolioStat({ label, value, body }: { label: string; value: string; body: string }) {
  return <article className="portfolio-stat"><span className="tile-caption">{label}</span><strong>{value}</strong><p>{body}</p></article>;
}

function PortfolioQuestion({ id, title, result, page, question, answer, isRevealed, onChoose, onReveal }: { id: string; title: string; result: FreeDnaReportV4["hero_portfolio"]["common_thread"] | FreeDnaReportV4["hero_portfolio"]["exception"] | FreeDnaReportV4["hero_portfolio"]["evolution"]; page?: StoryPage; question: "common_thread" | "exception" | "evolution"; answer?: string; isRevealed: boolean; onChoose: (question: string, option: ChoiceOption) => void; onReveal: (question: string) => void }) {
  const options = "options" in result ? result.options : page?.options ?? [];
  const unavailable = result.status === "unavailable";
  const noClear = result.status === "no_clear_thread" || result.status === "no_clear_exception";
  return <article id={id} className="portfolio-question"><div className="question-topline"><span className="tile-caption">{question === "evolution" ? "POOL EVOLUTION" : question === "common_thread" ? "COMMON THREAD" : "THE EXCEPTION"}</span><span className="question-mark" aria-hidden="true">?</span></div><h3>{title}</h3>{unavailable ? <UnavailableMessage message="This part of the portfolio is still forming." /> : noClear ? <div className="question-result"><span className="tile-caption">USEFUL ANSWER</span><strong>{question === "exception" ? "Your pool has no odd one out." : "No single thread takes the whole stage."}</strong><p>The useful answer is that your pool does not need a forced headline here.</p></div> : <><div className="choice-grid" role="radiogroup" aria-label={title}>{options.map((option) => <button key={option.key} type="button" role="radio" aria-checked={answer === option.key} className={answer === option.key ? "is-selected" : ""} onClick={() => onChoose(question, option)}>{option.label}</button>)}</div><button type="button" className="reveal-button" disabled={!answer || isRevealed} onClick={() => onReveal(question)}>{isRevealed ? "Read revealed" : "Reveal the read"}</button>{isRevealed && <PortfolioResult question={question} result={result} page={page} answer={answer} />}</>}</article>;
}

function PortfolioResult({ question, result, page, answer }: { question: "common_thread" | "exception" | "evolution"; result: FreeDnaReportV4["hero_portfolio"]["common_thread"] | FreeDnaReportV4["hero_portfolio"]["exception"] | FreeDnaReportV4["hero_portfolio"]["evolution"]; page?: StoryPage; answer?: string }) {
  if (question === "common_thread") {
    const common = result as FreeDnaReportV4["hero_portfolio"]["common_thread"];
    const right = answer !== undefined && answer === common.correct_option_key;
    return <div className="question-result" aria-live="polite"><span className="tile-caption">{right ? "YOU SPOTTED IT" : "A USEFUL CORRECTION"}</span><strong>{common.trait_label ?? "No single thread yet"}</strong><p>{right ? `${common.trait_label} is the strongest recurring way of helping across the established pool.` : `${common.trait_label ?? "That thread"} has the stronger recurring role in your pool.`}</p><div className="tag-row">{common.secondary_traits.map((trait) => <span key={trait}>{trait}</span>)}</div></div>;
  }
  if (question === "exception") {
    const exception = result as HeroException;
    const right = answer !== undefined && answer === exception.correct_option_key;
    return <div className="question-result" aria-live="polite"><span className="tile-caption">{right ? "YOU SPOTTED IT" : "A USEFUL CORRECTION"}</span><strong>{exception.hero_name ?? "No exception yet"}</strong><p>{right ? `${exception.hero_name} takes the clearest different route through your pool.` : `${exception.hero_name ?? "This hero"} stands apart more clearly.`}</p><div className="tag-row">{exception.exception_traits.map((trait) => <span key={trait}>{trait}</span>)}</div></div>;
  }
  const evolution = result as FreeDnaReportV4["hero_portfolio"]["evolution"];
  const variant = evolution.variant ? EVOLUTION_LABELS[evolution.variant] ?? "The pool is in motion." : page?.content?.payoff_heading ?? "The pool is still forming.";
  return <div className="question-result" aria-live="polite"><span className="tile-caption">POOL READ</span><strong>{variant}</strong><p>{page?.content?.copy && !containsAnalysisLanguage(page.content.copy) ? page.content.copy : "Your recent heroes add texture without erasing the older shape."}</p><div className="tag-row">{[...evolution.earlier_traits.slice(0, 3), ...evolution.recent_traits.slice(0, 3)].map((trait, index) => <span key={`${trait}-${index}`}>{trait}</span>)}</div></div>;
}

function YouChapter({ report, pageByKind, revealed, onReveal }: { report: FreeDnaReportV4; pageByKind: Map<string, StoryPage>; revealed: boolean; onReveal: () => void }) {
  const mirror = report.hero_portfolio.hero_mirror;
  const mirrorPage = pageByKind.get("hero_mirror_reveal");
  return <div className="chapter-inner"><ChapterHeading index="05" eyebrow="YOU / THE MIRROR" title="One last comparison" body="The report ends with the hero who most clearly reflects your usual decisions." palette="you" /><MirrorCard mirror={mirror} page={mirrorPage} open={revealed} onReveal={onReveal} report={report} /><div id="final-card" className="final-share"><div><p className="eyebrow">KEEP THE SIGNAL</p><h3>Make the read yours.</h3><p>Choose what travels with the card. Your account ID stays out of it.</p></div>{report.report_id ? <ShareControls reportId={report.report_id} reportSchema={report.schema_version} /> : <UnavailableMessage message="Sharing is unavailable for this report." />}</div></div>;
}

function MirrorCard({ mirror, page, open, onReveal, report }: { mirror: FreeDnaReportV4["hero_portfolio"]["hero_mirror"]; page?: StoryPage; open: boolean; onReveal: () => void; report: FreeDnaReportV4 }) {
  const [dragProgress, setDragProgress] = useState(0);
  const dragProgressRef = useRef(0);
  const pointer = useRef<{ id: number; startX: number; dragging: boolean } | null>(null);
  const started = useRef(false);
  const completed = useRef(false);
  const reveal = (interaction: string) => {
    if (open) return;
    if (!started.current) {
      started.current = true;
      track("hero_mirror.reveal_started.v1", { interaction, report_schema_version: report.schema_version, portfolio_model_version: report.versions.hero_mirror });
    }
    onReveal();
    if (!completed.current) {
      completed.current = true;
      track("hero_mirror.reveal_completed.v1", { result_status: mirror.status, report_schema_version: report.schema_version, portfolio_model_version: report.versions.hero_mirror });
    }
  };
  return (
    <section id="hero-mirror" className="mirror-stage" aria-labelledby="hero-mirror-heading">
      <article
        className={`mirror-card${open ? " is-open" : ""}${dragProgress > 0 && !open ? " is-dragging" : ""}`}
        style={{ "--mirror-progress": dragProgress } as React.CSSProperties}
        tabIndex={0}
        onPointerDown={(event) => {
          if (!open && (event.pointerType !== "mouse" || event.button === 0)) pointer.current = { id: event.pointerId, startX: event.clientX, dragging: false };
        }}
        onPointerMove={(event) => {
          const current = pointer.current;
          if (!current || current.id !== event.pointerId || open) return;
          const dx = event.clientX - current.startX;
          if (!current.dragging && Math.abs(dx) < 8) return;
          current.dragging = true;
          event.currentTarget.setPointerCapture(event.pointerId);
          event.preventDefault();
          const progress = Math.min(1, Math.abs(dx) / Math.max(event.currentTarget.clientWidth, 1));
          dragProgressRef.current = progress;
          setDragProgress(progress);
        }}
        onPointerUp={(event) => {
          const current = pointer.current;
          if (!current || current.id !== event.pointerId) return;
          if (current.dragging && dragProgressRef.current >= 0.35) reveal("drag");
          else { dragProgressRef.current = 0; setDragProgress(0); }
          if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
          pointer.current = null;
        }}
        onPointerCancel={() => { pointer.current = null; dragProgressRef.current = 0; setDragProgress(0); }}
        onKeyDown={(event) => { if ((event.key === "Enter" || event.key === " ") && !open) { event.preventDefault(); reveal("keyboard"); } }}
      >
        <div className="mirror-cover"><span className="tile-caption">HERO MIRROR</span><h2 id="hero-mirror-heading">{page?.content?.title && !containsAnalysisLanguage(page.content.title) ? page.content.title : "Which hero looks a little too familiar?"}</h2><p>{page?.content?.closed && !containsAnalysisLanguage(page.content.closed) ? page.content.closed : "There is one hero who resembles your usual decisions from a different angle."}</p><button type="button" className="mirror-reveal-button" onClick={() => reveal("button")}>Reveal Hero Mirror</button><span className="mirror-gesture-hint">Swipe across the card, or use the button.</span></div>
        {open && <MirrorReveal mirror={mirror} />}
      </article>
    </section>
  );
}

function MirrorReveal({ mirror }: { mirror: FreeDnaReportV4["hero_portfolio"]["hero_mirror"] }) {
  if (mirror.status !== "available" || !mirror.hero_name) return <div className="mirror-result" aria-live="polite"><span className="tile-caption">THE MIRROR</span><h3>No single hero mirrors your current shape yet.</h3><p>That is still a useful result. Your identity is not asking for one mascot today.</p></div>;
  const rows = ["involvement", "finishing", "deaths", "role_context"];
  return <div className="mirror-result" aria-live="polite"><span className="tile-caption">THE MIRROR</span><h3>{mirror.hero_name} is where your usual Dota shows up most clearly.</h3><div className="hero-behavior-table" role="table" aria-label="Player and hero behavior comparison"><div className="hero-behavior-row header" role="row"><span>Behavior</span><span>Your shape</span><span>{mirror.hero_name}</span></div>{rows.map((key) => <div className="hero-behavior-row" role="row" key={key}><strong>{key.replaceAll("_", " ")}</strong><span>{mirror.player_behavior[key] ?? "Still forming"}</span><span>{mirror.hero_behavior[key] ?? "Still forming"}</span></div>)}</div></div>;
}

function ChapterHeading({ index, eyebrow, title, body, palette }: { index: string; eyebrow: string; title: string; body: string; palette: ReportChapter["palette"] }) {
  return <div className="chapter-heading"><div className="chapter-kicker"><span className="chapter-index">{index}</span><span>{eyebrow}</span></div><h2 id={`${palette}-heading`}>{title}</h2><p className="chapter-lede">{body}</p></div>;
}

function UnavailableMessage({ message }: { message: string }) {
  return <div className="unavailable-message"><strong>Still forming</strong><p>{message}</p></div>;
}

function orderByKeys<T extends { key: string }>(items: T[], order: string[]): T[] {
  const index = new Map(order.map((key, position) => [key, position]));
  return [...items].sort((a, b) => (index.get(a.key) ?? order.length) - (index.get(b.key) ?? order.length));
}

function containsAnalysisLanguage(value: string | null | undefined): boolean {
  if (!value) return false;
  return /confidence|coverage|evidence|provenance|sample|cohort|methodology|source|denominator|matches|played enough|\btrust\b|qualified relationship|evidence-backed|bounded (summary|history)|summary history|observable (summary|history)|raw metrics/i.test(value);
}

function safeCatalogCopy(value: string | null | undefined, fallback: string): string {
  return value && !containsAnalysisLanguage(value) ? value : fallback;
}

function elementNarrative(element: BehaviorElement, page?: StoryPage): string {
  return safeCatalogCopy(page?.content.observation ?? page?.content.meaning ?? page?.content.why_highlight ?? page?.body, ELEMENT_COPY[element.key] ?? "A distinct part of your current Dota shape.");
}

export function glyphDefinitionFor(key: string): GlyphDefinition | undefined {
  return GLYPH_BY_KEY[key];
}
