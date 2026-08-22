"use client";

import { useEffect, useId, useMemo, useRef, useState } from "react";
import type {
  BehaviorElement,
  BehaviorPattern,
  BouncebackAction,
  ChoiceOption,
  FreeDnaReportV4,
  ComfortEdgeAction,
  ControlledPresenceAction,
  PartialTransferDiagnostic,
  PerformanceSlideAction,
  ProvenFlexibilityAction,
  HeroException,
  PatternActionCopy,
  SamePlaybookAction,
  PresenceTaxAction,
  SessionCurveAction,
  VersatileCoreAction,
  StoryPage,
} from "../../../../../../packages/api-client/src";
import { track } from "../../../lib/analytics";
import { DeepDiveTeaser, EvidenceReceipt, MethodologySheet, Spectrum, StoryPage as StoryPageFrame } from "../../../components/story/primitives";
import { PatternStoryScreen } from "../../../components/story/patterns/pattern-story-screen";
import ShareControls from "../../../components/share/share-controls";

export default function ReportStoryV4({ report }: { report: FreeDnaReportV4 }) {
  // Pool Evolution is a choose → reveal interaction. Older v5 payloads also
  // include a second `pool_evolution_reveal` page for the same payoff; keep
  // that page's copy as context, but render the payoff once in the question
  // screen so the reader does not get two reveal screens in a row.
  const pages = useMemo(() => {
    const hasEvolutionQuestion = report.pages.some((page) => page.kind === "pool_evolution_question");
    if (!hasEvolutionQuestion) return report.pages;
    return report.pages.filter((page) => page.kind !== "pool_evolution_reveal");
  }, [report.pages]);
  const evolutionRevealPage = useMemo(
    () => report.pages.find((page) => page.kind === "pool_evolution_reveal"),
    [report.pages]
  );
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
            {renderPage(page, { report, elements, patterns, answers, revealed, setAnswers, setRevealed, methodologyOpen, setMethodologyOpen, evolutionRevealPage })}
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
  evolutionRevealPage?: StoryPage;
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
      <p className="eyebrow">18 Elements · summary history only</p>
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
      <div className="element-tile-meta"><span>{element.zone ?? "No zone yet"}</span><span>{element.sample_size ? `${element.sample_size} matches` : "No sample"}</span></div>
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
    <div className="signal-status"><strong>{element.zone ?? "Signal unavailable"}</strong><span>{element.confidence} confidence · {element.sample_size ? `${element.sample_size} matches` : "no readable sample"}</span></div>
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
  if (pattern.presentation && page.content?.presentation_copy) {
    return <PatternStoryScreen pattern={pattern} page={page} reportSchemaVersion={context.report.schema_version} />;
  }
  const actionCopy = page.content?.action_copy ?? undefined;
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
        <div className="ingredient-list"><span>How clearly it repeats: {Math.round(pattern.strength * 100)}% · Tier {pattern.tier} · {pattern.family}</span></div>
      </details>
      {page.content?.takeaway && <p><strong>Useful takeaway.</strong> {page.content.takeaway}</p>}
      {pattern.action?.action_type === "same_playbook" && <SamePlaybookActionPanel action={pattern.action} copy={actionCopy} />}
      {pattern.action?.action_type === "comfort_edge" && <ComfortEdgeActionPanel action={pattern.action} copy={actionCopy} />}
      {pattern.action?.action_type === "partial_transfer" && <PartialTransferActionPanel action={pattern.action} copy={actionCopy} />}
      {pattern.action?.action_type === "versatile_core" && <VersatileCoreActionPanel action={pattern.action} copy={actionCopy} />}
      {pattern.action?.action_type === "proven_flexibility" && <ProvenFlexibilityActionPanel action={pattern.action} copy={actionCopy} />}
      {(pattern.action?.action_type === "bounceback" || pattern.action?.action_type === "performance_slide") && <RecoveryActionPanel action={pattern.action} copy={actionCopy} />}
      {(pattern.action?.action_type === "session_fade" || pattern.action?.action_type === "session_rise") && <SessionCurveActionPanel action={pattern.action} copy={actionCopy} />}
      {pattern.action?.action_type === "controlled_presence" && <ControlledPresenceActionPanel action={pattern.action} copy={actionCopy} />}
      {pattern.action?.action_type === "presence_tax" && <PresenceTaxActionPanel action={pattern.action} copy={actionCopy} />}
      {page.content?.guardrail && <p className="muted"><strong>Do not overread this.</strong> {page.content.guardrail}</p>}
      {pattern.suppression_reasons.length > 0 && <p className="muted">{pattern.suppression_reasons.join(" ")}</p>}
    </article>
  );
}

function ControlledPresenceActionPanel({ action, copy }: { action: ControlledPresenceAction; copy?: PatternActionCopy | null }) {
  return <section className="pattern-action" aria-labelledby="controlled-presence-heading">
    <span className="eyebrow">{copy?.controlled_presence_kicker ?? "Your cleanest presence"}</span>
    <h3 id="controlled-presence-heading">{action.strongest_context?.label ?? "The overall pattern is the strongest supported level"}</h3>
    {action.strongest_context && <p>High involvement · low death exposure · {action.strongest_context.sample_size} usable matches</p>}
    {action.comparison_rows.length > 0 && <div className="pattern-action-cards">{action.comparison_rows.map((row) => <article className="pattern-action-card" key={`${row.label}-${row.hero_id ?? row.function_family}`}><h4>{row.label}</h4><p>Involvement {Math.round(row.involvement_level * 100)} · death exposure {Math.round(row.death_exposure_level * 100)}</p><small>{row.sample_size} matches · {Math.round(row.confidence_score * 100)}% confidence</small></article>)}</div>}
    {action.finishing_flavor && <p><strong>{copy?.controlled_presence_finishing_label ?? "Finishing flavor."}</strong> {action.finishing_flavor === "controlled_setup_presence" ? "Your involvement leans toward setup and assists." : "Your involvement leans toward final kill credit."}</p>}
    <p className="muted">{action.limitations.join(" ")}</p>
  </section>;
}

function PresenceTaxActionPanel({ action, copy }: { action: PresenceTaxAction; copy?: PatternActionCopy | null }) {
  const shape = {
    hero_specific: "Hero-specific",
    job_shaped: "Job-specific",
    cross_context: "Across contexts",
    unresolved: "Context still forming",
  }[action.shape] ?? "Context still forming";
  return <section className="pattern-action" aria-labelledby="presence-tax-heading">
    <span className="eyebrow">{copy?.presence_tax_kicker ?? "Where does the tax come from?"}</span>
    <h3 id="presence-tax-heading">{shape || copy?.presence_tax_heading}</h3>
    {action.comparison_contexts.length > 0 && <div className="pattern-action-cards">{action.comparison_contexts.map((row) => <article className="pattern-action-card" key={`${row.label}-${row.hero_id ?? row.function_family}`}><h4>{row.label}</h4><p>Involvement {Math.round(row.involvement_level * 100)} · death exposure {Math.round(row.death_exposure_level * 100)}</p><small>{row.sample_size} matches · {Math.round(row.confidence_score * 100)}% confidence</small></article>)}</div>}
    {action.deep_analysis_candidate && <p><strong>{copy?.presence_tax_deep_label ?? "Deeper evidence needed."}</strong> We can see where the death cost concentrates. Replay-level evidence is needed to explain what those deaths are buying—or why they are happening.</p>}
    {action.shape === "unresolved" && <p>{copy?.presence_tax_unresolved_body ?? "The summary history shows the cost, but not a stable context for it yet."}</p>}
    <p className="muted">{action.limitations.join(" ")}</p>
  </section>;
}

function PartialTransferActionPanel({ action, copy }: { action: PartialTransferDiagnostic; copy?: PatternActionCopy | null }) {
  const signalLabels: Record<string, string> = {
    combat_involvement: "Fight presence",
    result_distribution: "Results",
    death_exposure: "Death cost",
    finisher_orientation: "Finishing",
  };
  const capabilityLabels: Record<string, string> = {
    commitment: "Commitment",
    access: "Access",
    repositioning: "Repositioning",
    economy: "Resource needs",
    timing: "Timing",
    execution: "Execution",
    exposure: "Exposure",
    micro: "Attention load",
  };
  const statusLabel = action.status.replaceAll("_", " ");
  return <section className="pattern-action" aria-labelledby="partial-transfer-heading">
    <span className="eyebrow">{copy?.partial_transfer_kicker ?? "Where the transfer bends"}</span>
    <h3 id="partial-transfer-heading">{action.status === "unresolved" ? copy?.partial_transfer_unresolved_heading ?? "The gap is real; the cause is not proven" : copy?.partial_transfer_heading ?? "One learning demand may explain the gap"}</h3>
    {action.strongest_supported_lead && <p>{action.strongest_supported_lead}</p>}
    {action.summary_differences.length > 0 && <div className="pattern-action-cards"><span className="eyebrow">{copy?.partial_transfer_direct_label ?? "Observable difference"}</span>{action.summary_differences.map((difference) => <article className="pattern-action-card" key={difference.signal_key}><h4>{signalLabels[difference.signal_key] ?? "Observable signal"}</h4><p>{difference.player_facing_claim}</p><small>{Math.round(difference.confidence_score * 100)}% confidence</small></article>)}</div>}
    {action.capability_hypotheses.length > 0 && <div className="pattern-action-cards"><span className="eyebrow">{copy?.partial_transfer_hypothesis_label ?? "Capability lead"}</span>{action.capability_hypotheses.map((hypothesis) => <article className="pattern-action-card" key={hypothesis.capability_key}><h4>{capabilityLabels[hypothesis.capability_key] ?? "Capability lead"}</h4><p>{hypothesis.player_facing_hypothesis}</p><small>{Math.round(hypothesis.confidence_score * 100)}% confidence</small></article>)}</div>}
    <p className="muted">Evidence level: {statusLabel}. {action.deep_analysis_eligible && (copy?.partial_transfer_deep_label ?? "Worth a deeper evidence pass.")}</p>
    {action.limitations.length > 0 && <p className="muted">{action.limitations.join(" ")}</p>}
  </section>;
}

function VersatileCoreActionPanel({ action, copy }: { action: VersatileCoreAction; copy?: PatternActionCopy | null }) {
  const coverage = action.coverage_summary;
  const familyMap = coverage.family_map ?? {};
  const familyDescriptions = coverage.family_descriptions ?? {};
  const coverageGroups = Object.entries(familyMap).map(([key, label]) => ({
    key,
    label,
    description: familyDescriptions[key],
    state: coverage.missing.includes(label)
      ? "gap"
      : coverage.thin_coverage.includes(label) || coverage.single_point_coverage.includes(label)
        ? "thin"
        : "covered",
  }));
  const legacyGroups = [
    ["Strongly covered", coverage.strongly_covered],
    ["One hero", coverage.single_point_coverage],
    ["Thin", coverage.thin_coverage],
    ["Missing", coverage.missing],
  ] as const;
  const qualified = action.complementarity_qualified !== false;
  return <section className="pattern-action" aria-labelledby="versatile-core-heading">
    <span className="eyebrow">{copy?.versatile_core_kicker ?? "Your compact toolkit"}</span>
    <h3 id="versatile-core-heading">{qualified ? copy?.versatile_core_heading ?? "Small pool. Different answers." : "No clear versatility read yet"}</h3>
    <div className="pattern-action-cards"><span className="eyebrow">{copy?.versatile_core_jobs_label ?? "Ways of helping in the core"}</span>{action.hero_job_maps.map((hero) => <article className="pattern-action-card" key={hero.hero_id}><h4>{hero.hero_name}</h4><p>{hero.primary_jobs.length > 0 ? hero.primary_jobs.map((job) => <SemanticChip key={job} label={job} />) : "No clear map yet"}</p>{hero.expression_summary && <small>{hero.expression_summary}</small>}</article>)}</div>
    <div className="descriptor-list" aria-label={copy?.versatile_core_coverage_label ?? "Coverage map"}>{coverageGroups.length > 0 ? coverageGroups.map((family) => <span key={family.key}><SemanticChip label={family.label} description={family.description} />: {family.state === "gap" ? "Needs coverage" : family.state === "thin" ? "One or two heroes" : "Covered by the core"}</span>) : legacyGroups.map(([label, jobs]) => jobs.length > 0 && <span key={label}><strong>{label}:</strong> {jobs.map((job) => <SemanticChip key={job} label={job} />)}</span>)}</div>
    {coverage.primary_gap && <p><strong>Primary gap.</strong> {coverage.primary_gap}. {coverage.secondary_gaps?.length ? `Secondary gaps: ${coverage.secondary_gaps.join(", ")}.` : ""}</p>}
    {qualified && action.recommended_addition ? <article className="pattern-action-card"><span className="eyebrow">{copy?.versatile_core_next_tool_label ?? "One useful next tool"}</span><h4>{action.recommended_addition.hero_name}</h4><p>{action.recommended_addition.player_facing_reason}</p><small>{action.recommended_addition.solves_gap}</small></article> : <p><strong>{qualified ? copy?.versatile_core_no_gap_heading ?? "No obvious hole needs filling" : "The family map is useful context, but it is not strong enough for a headline."}</strong></p>}
    {action.alternative_additions.length > 0 && <p><strong>{copy?.versatile_core_alternatives_label ?? "Other viable additions"}.</strong> {action.alternative_additions.map((hero) => hero.hero_name).join(", ")}</p>}
    {action.limitations.length > 0 && <p className="muted">{action.limitations.join(" ")}</p>}
  </section>;
}

function ProvenFlexibilityActionPanel({ action, copy }: { action: ProvenFlexibilityAction; copy?: PatternActionCopy | null }) {
  const roster = action.hero_names.map((name, index) => `${name} · ${action.hero_game_counts[index]?.[1] ?? 0}`);
  return <section className="pattern-action" aria-labelledby="proven-flexibility-heading">
    <span className="eyebrow">{copy?.proven_flexibility_kicker ?? "Proof of range"}</span>
    <h3 id="proven-flexibility-heading">{action.status === "distributed_flexibility" ? copy?.proven_flexibility_distributed_heading ?? "Your flexibility is distributed" : copy?.proven_flexibility_heading ?? "Your flexibility shows up in the calendar"}</h3>
    {action.window_start && action.window_end && <p>{action.window_start} → {action.window_end} · {action.total_games} games</p>}
    <p><strong>{copy?.proven_flexibility_roster_label ?? "Heroes in the window"}.</strong> {roster.join(", ") || "No reviewed hero roster yet."}</p>
    <p><strong>{copy?.proven_flexibility_proof_label ?? "What repeats"}.</strong> {action.functional_jobs.length > 0 ? action.functional_jobs.map((job) => <SemanticChip key={job} label={job} />) : "No clear range yet."}. {action.secondary_proof ?? `${action.meaningful_hero_count} meaningful heroes cover ${action.functional_job_count} ways of helping.`}</p>
    {action.limitations.length > 0 && <p className="muted">{action.limitations.join(" ")}</p>}
  </section>;
}

function RecoveryActionPanel({ action, copy }: { action: BouncebackAction | PerformanceSlideAction; copy?: PatternActionCopy | null }) {
  const positive = action.action_type === "bounceback";
  const context = action.strongest_context;
  const delta = context ? Math.abs(context.performance_delta).toFixed(2) : "0.00";
  return <section className="pattern-action" aria-labelledby={`${action.action_type}-heading`}>
    <span className="eyebrow">{positive ? copy?.bounceback_kicker ?? "Your best rebound tool" : copy?.performance_slide_kicker ?? "Your roughest post-loss tool"}</span>
    <h3 id={`${action.action_type}-heading`}>{context?.label ?? (positive ? copy?.bounceback_heading ?? "Where your post-loss performance recovers most" : copy?.performance_slide_heading ?? "Where the post-loss drop is largest")}</h3>
    {context ? <><p><strong>{positive ? "+" : "-"}{delta}</strong> compared with similar games · {context.sample_size} transitions across {context.session_count} sessions.</p><p><strong>{copy?.recovery_context_label ?? "Comparable context"}.</strong> {context.primary_jobs.length > 0 ? context.primary_jobs.map((job) => <SemanticChip key={job} label={job} />) : "Overall summary context"}.</p></> : <UnavailableMessage limitations={action.limitations} />}
    {action.comparison_contexts.length > 0 && <div className="pattern-action-cards">{action.comparison_contexts.map((row) => <article className="pattern-action-card" key={`${row.label}-${row.hero_id ?? row.function_family ?? row.role_context ?? "overall"}`}><h4>{row.label}</h4><p>{row.performance_delta >= 0 ? "+" : ""}{row.performance_delta.toFixed(2)} similar-game comparison units · {row.sample_size} transitions</p><small>{Math.round(row.confidence_score * 100)}% confidence</small></article>)}</div>}
    {action.limitations.length > 0 && <p className="muted">{action.limitations.join(" ")}</p>}
  </section>;
}

function SessionCurveActionPanel({ action, copy }: { action: SessionCurveAction; copy?: PatternActionCopy | null }) {
  const rising = action.action_type === "session_rise";
  const heading = rising
    ? copy?.session_rise_heading ?? "Where the session curve starts to lift"
    : copy?.session_fade_heading ?? "Where the session curve starts to fade";
  const breakpointLabel = rising
    ? copy?.session_rise_breakpoint_label ?? "Earliest supported lift"
    : copy?.session_fade_breakpoint_label ?? "Earliest supported fade";
  const gradualLabel = rising
    ? copy?.session_rise_gradual_label ?? "The movement is gradual"
    : copy?.session_fade_gradual_label ?? "The movement is gradual";
  return <section className="pattern-action session-curve-action" aria-labelledby={`${action.action_type}-heading`}>
    <span className="eyebrow">{rising ? copy?.session_rise_kicker ?? "A session curve" : copy?.session_fade_kicker ?? "A session curve"}</span>
    <h3 id={`${action.action_type}-heading`}>{heading}</h3>
    <p>This is a relative performance-proxy curve, balanced by independent sessions. The values are not calibrated percentages and do not establish fatigue, warm-up, or a stopping point.</p>
    <div className="pattern-action-cards" aria-label="Session position curve">
      {action.curve.map((point) => <article className={`pattern-action-card${point.supported ? "" : " is-muted"}`} key={point.bucket}>
        <h4>{point.bucket}</h4>
        <p>{point.supported ? `${point.relative_delta >= 0 ? "+" : ""}${point.relative_delta.toFixed(2)} comparison units` : "Not enough independent sessions"}</p>
        <small>{point.sample_size} matches · weighted comparison {point.effective_sample_size.toFixed(1)}</small>
      </article>)}
    </div>
    {action.breakpoint_state === "stable_breakpoint" && action.breakpoint_bucket && <p><strong>{breakpointLabel}:</strong> {action.breakpoint_bucket}. {action.independent_session_count} independent sessions support the curve.</p>}
    {action.breakpoint_state === "gradual" && <p><strong>{gradualLabel}.</strong> No single earliest bucket clears the stable-breakpoint rule.</p>}
    {action.companion_signals.length > 0 && <p><strong>Companion signals.</strong> {action.companion_signals.join(" ")}</p>}
    {action.limitations.length > 0 && <p className="muted">{action.limitations.join(" ")}</p>}
  </section>;
}

function SamePlaybookActionPanel({ action, copy }: { action: SamePlaybookAction; copy?: PatternActionCopy | null }) {
  const [direction, setDirection] = useState<"deepen" | "stretch">("deepen");
  const recommendations = direction === "deepen" ? action.deepen : action.stretch;
  if (action.status === "unavailable") return <UnavailableMessage limitations={action.limitations} />;
  return (
    <section className="pattern-action same-playbook-action" aria-labelledby="same-playbook-action-heading">
      <span className="eyebrow">{copy?.same_playbook_kicker ?? "A useful next step"}</span>
      <h3 id="same-playbook-action-heading">{copy?.same_playbook_heading ?? "Where do you want to take this?"}</h3>
      <p>{copy?.same_playbook_intro ?? "Both directions are valid: keep solving the same kind of Dota problem, or add range without abandoning your anchors."}</p>
      <div className="choice-grid" role="radiogroup" aria-label="Same Playbook direction">
        <button type="button" role="radio" aria-checked={direction === "deepen"} className={direction === "deepen" ? "is-selected" : ""} onClick={() => setDirection("deepen")}>
          <strong>{copy?.same_playbook_deepen_label ?? "Go deeper"}</strong><span>{copy?.same_playbook_deepen_description ?? "More heroes that keep your current game familiar."}</span>
        </button>
        <button type="button" role="radio" aria-checked={direction === "stretch"} className={direction === "stretch" ? "is-selected" : ""} onClick={() => setDirection("stretch")}>
          <strong>{copy?.same_playbook_stretch_label ?? "Stretch comfortably"}</strong><span>{copy?.same_playbook_stretch_description ?? "Bridge heroes that add a new answer while preserving an anchor."}</span>
        </button>
      </div>
      <p className="muted">{copy?.same_playbook_recurring_core_label ?? "Your recurring core:"} {action.dominant_traits.join(" · ") || "not clear yet"}.</p>
      {recommendations.length > 0 ? <div className="pattern-action-cards">{recommendations.map((recommendation) => <article className="pattern-action-card" key={recommendation.hero_id}>
        <h4>{recommendation.hero_name}</h4>
        <p>{recommendation.why_it_fits}</p>
        <p><strong>{copy?.same_playbook_familiar_label ?? "What stays familiar."}</strong> {recommendation.what_stays_familiar}</p>
        <p><strong>{copy?.same_playbook_changes_label ?? "What changes."}</strong> {recommendation.what_changes}</p>
      </article>)}</div> : <UnavailableMessage limitations={[copy?.same_playbook_empty_direction ?? "No candidate had enough evidence and a close enough learning step for this direction."]} />}
      {action.limitations.length > 0 && <p className="muted">{action.limitations.join(" ")}</p>}
    </section>
  );
}

function ComfortEdgeActionPanel({ action, copy }: { action: ComfortEdgeAction; copy?: PatternActionCopy | null }) {
  if (action.status === "unavailable") return <UnavailableMessage limitations={action.limitations} />;
  return (
    <section className="pattern-action comfort-edge-action" aria-labelledby="comfort-edge-action-heading">
      <span className="eyebrow">{copy?.comfort_edge_kicker ?? "Build the pool with a reason"}</span>
      <h3 id="comfort-edge-action-heading">{copy?.comfort_edge_heading ?? "Your strongest heroes are the safest part of this pool today."}</h3>
      <p>{copy?.comfort_edge_intro ?? "Here is why the other established heroes can still be worth learning. This is a player-relative reliability read, not a meta ranking."}</p>
      <ol className="hero-reliability-list" aria-label={copy?.comfort_edge_reliability_label ?? "Established hero reliability"}>
        {action.ranked_heroes.map((hero) => <li key={hero.hero_id} className={hero.reliability_rank <= 2 ? "is-reference-core" : "is-development-side"}>
          <span>#{hero.reliability_rank}</span><strong>{hero.hero_name}</strong><small>{hero.matches} usable matches · {Math.round(hero.confidence_score * 100)}% confidence</small>
        </li>)}
      </ol>
      {action.development.length > 0 && <div className="pattern-action-cards">{action.development.map((reason) => <article className="pattern-action-card" key={reason.hero_id}>
        <span className="eyebrow">{copy?.comfort_edge_why_learn_label ?? "Why learn"} {reason.hero_name}?</span>
        <h4>{reason.hero_name}</h4>
        <p>{reason.why_learn}</p>
        {reason.useful_situations.length > 0 && <p><strong>{copy?.comfort_edge_useful_when_label ?? "Useful when."}</strong> {reason.useful_situations.join(" ")}</p>}
        {reason.enemy_example_names.length > 0 && <p><strong>{copy?.comfort_edge_enemy_examples_label ?? "Enemy examples."}</strong> {reason.enemy_example_names.join(", ")}</p>}
        {reason.teammate_example_names.length > 0 && <p><strong>{copy?.comfort_edge_teammate_examples_label ?? "Teammate examples."}</strong> {reason.teammate_example_names.join(", ")}</p>}
        {reason.tradeoffs.length > 0 && <p className="muted"><strong>{copy?.comfort_edge_tradeoff_label ?? "Tradeoff."}</strong> {reason.tradeoffs.join(" ")}</p>}
        {reason.limitations.length > 0 && <p className="muted">{reason.limitations.join(" ")}</p>}
      </article>)}</div>}
      {action.limitations.length > 0 && <p className="muted">{action.limitations.join(" ")}</p>}
    </section>
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
  const noClearThread = kind === "common_thread" && result.status === "no_clear_thread";
  const noClearException = kind === "exception" && result.status === "no_clear_exception";
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
      {unavailable ? <UnavailableMessage limitations={result.limitations} /> : noClearThread ? <ExceptionNoClearInsight copy={page.content.no_clear_insight} fallbackBody={result.limitations[0]} /> : noClearException ? <ExceptionNoClearInsight copy={page.content.no_clear_insight} fallbackBody={result.limitations[0]} /> : <>
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

type NoClearInsightCopy = NonNullable<StoryPage["content"]["no_clear_insight"]>;

function ExceptionNoClearInsight({ copy, fallbackBody }: { copy?: NoClearInsightCopy; fallbackBody?: string }) {
  const resolved = copy && typeof copy === "object" ? copy : {
    eyebrow: "Exception read",
    headline: "No clear odd one out.",
    body: fallbackBody ?? "The pool did not clear one hero as a distinct outlier.",
    boundary: "Different does not mean better or worse.",
  };
  return <div className="portfolio-reveal exception-no-clear" aria-live="polite"><span className="eyebrow">{resolved.eyebrow}</span><h3>{resolved.headline}</h3><p>{resolved.body}</p><p className="muted">{resolved.boundary}</p></div>;
}

function PortfolioReveal({ kind, selected, correct, result, content }: { kind: "common_thread" | "exception"; selected?: string; correct: string | null; result: FreeDnaReportV4["hero_portfolio"]["common_thread"] | HeroException; content?: StoryPage["content"] }) {
  const right = selected !== undefined && selected === correct;
  const selectedOption = result.options.find((option) => option.key === selected);
  const resultLabel = right ? content?.correct_label ?? "You spotted it." : content?.incorrect_label ?? "A useful correction.";
  if (kind === "common_thread") {
    const common = result as FreeDnaReportV4["hero_portfolio"]["common_thread"];
    return <div className="portfolio-reveal"><span className="eyebrow">{resultLabel}</span><h3>{common.trait_label ?? "No clear common thread"}</h3><p>{selectedOption?.feedback ?? common.limitations.join(" ")}</p><div className="descriptor-list">{common.secondary_traits.map((trait) => <SemanticChip key={trait} label={trait} />)}</div></div>;
  }
  const exception = result as HeroException;
  return <div className="portfolio-reveal"><span className="eyebrow">{resultLabel}</span><h3>{exception.hero_name ?? (exception.status === "no_clear_exception" ? "Your pool has no odd one out." : "No exception yet")}</h3><p>{selectedOption?.feedback ?? exception.limitations.join(" ")}</p><div className="descriptor-list">{exception.exception_traits.map((trait) => <SemanticChip key={trait} label={trait} />)}</div></div>;
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
  return <article className="portfolio-question"><p className="eyebrow">Hero Portfolio · Pool Evolution</p><h2 id={`${page.id}-heading`}>{page.title}</h2><p className="story-lede">{page.body}</p><div className="choice-grid" role="radiogroup" aria-labelledby={`${page.id}-heading`}>{page.options.map((option) => <button key={option.key} type="button" role="radio" aria-checked={selected === option.key} className={selected === option.key ? "is-selected" : ""} onClick={() => choose(option)}>{option.label}</button>)}</div>{selected && <p className="choice-status" role="status" aria-live="polite">Your read: {page.options.find((option) => option.key === selected)?.label}</p>}<button type="button" className="reveal-button" disabled={!selected || isRevealed} onClick={() => { context.setRevealed((current) => ({ ...current, evolution: true })); track("hero_portfolio.reveal_viewed.v1", { question_key: "evolution", matched_computed_answer: null, report_schema_version: context.report.schema_version, portfolio_model_version: context.report.versions.hero_portfolio }); }}>{isRevealed ? "Answer revealed" : "Reveal"}</button>{isRevealed && <div aria-live="polite"><EvolutionResult evolution={context.report.hero_portfolio.evolution} content={context.evolutionRevealPage?.content ?? page.content} /></div>}</article>;
}

function EvolutionReveal({ page, context }: { page: StoryPage; context: StoryContext }) {
  const evolution = context.report.hero_portfolio.evolution;
  if (!context.revealed.evolution) {
    return <article className="evolution-reveal"><p className="eyebrow">Pool Evolution · report read</p><h2 id={`${page.id}-heading`}>{page.title}</h2><div className="unavailable-message"><strong>{page.content?.locked_copy ?? "Complete the self-assessment above to see the report read."}</strong></div></article>;
  }
  return <article className="evolution-reveal"><p className="eyebrow">Pool Evolution · report read</p><h2 id={`${page.id}-heading`}>{page.title}</h2><EvolutionResult evolution={evolution} content={page.content} /></article>;
}

function EvolutionResult({ evolution, content }: { evolution: FreeDnaReportV4["hero_portfolio"]["evolution"]; content?: StoryPage["content"] }) {
  if (evolution.status !== "available" || !evolution.variant) return <UnavailableMessage limitations={evolution.limitations} />;
  const dateRange = (start?: string | null, end?: string | null) => start && end ? ` · ${start}–${end}` : "";
  return <section className="portfolio-reveal evolution-payoff"><span className="eyebrow">Pool Evolution · report read</span><h3>{content?.payoff_heading ?? "Pool Evolution"}</h3><p className="story-lede">{content?.copy ?? "Your hero names changed; here is what changed underneath."}</p><div className="evolution-columns"><div><span className="eyebrow">Previous {evolution.earlier_sample_size} matches{dateRange(evolution.earlier_start, evolution.earlier_end)}</span><div className="descriptor-list">{evolution.earlier_traits.map((trait) => <SemanticChip key={trait} label={trait} />)}</div></div><div><span className="eyebrow">Latest {evolution.recent_sample_size} matches{dateRange(evolution.recent_start, evolution.recent_end)}</span><div className="descriptor-list">{evolution.recent_traits.map((trait) => <SemanticChip key={trait} label={trait} />)}</div></div></div></section>;
}

const SEMANTIC_JOB_DESCRIPTIONS: Record<string, string> = {
  "Fight start": "Starts fights on your terms.",
  "Counter-engage": "Punishes enemies after they commit.",
  Catch: "Locks down a target before they escape.",
  "Fight control": "Restricts where enemies can move or act once the fight starts.",
  Frontline: "Can occupy dangerous space for the team.",
  Save: "Prevents an ally from dying or being disabled.",
  Sustain: "Keeps allies healthy through longer fights.",
  "Forced movement": "Moves heroes from where they wanted to be.",
  Repositioning: "Reaches a better position during the fight.",
  Mobility: "Reaches or leaves positions quickly.",
  "Burst damage": "Deals a lot of damage in a short window.",
  "Sustained damage": "Keeps damage flowing through longer fights.",
  "Wave clear": "Removes creep waves quickly.",
  "Tower pressure": "Converts space into building pressure.",
  "Global reach": "Influences distant parts of the map quickly.",
  Vision: "Creates or denies information.",
  "Late-game scaling": "Gains more value as resources accumulate.",
};

function SemanticChip({ label, description }: { label: string; description?: string }) {
  const explanation = description || SEMANTIC_JOB_DESCRIPTIONS[label] || "A reviewed way this hero can contribute.";
  const [open, setOpen] = useState(false);
  const explanationId = useId();
  return <span className={`semantic-chip${open ? " is-open" : ""}`}>
    <button
      type="button"
      className="semantic-chip-trigger"
      title={explanation}
      aria-label={`${label}: ${explanation}`}
      aria-expanded={open}
      aria-describedby={open ? explanationId : undefined}
      onClick={() => setOpen((current) => !current)}
      onKeyDown={(event) => { if (event.key === "Escape") setOpen(false); }}
    >{label}<span aria-hidden="true">ⓘ</span></button>
    <span id={explanationId} className="semantic-chip-tooltip" role="tooltip">{explanation}</span>
  </span>;
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
  return <article className={`mirror-card${open ? " is-open" : ""}${dragProgress > 0 && !open ? " is-dragging" : ""}`} style={{ "--mirror-progress": dragProgress } as React.CSSProperties} tabIndex={0} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerCancel} onKeyDown={(event) => { if ((event.key === "Enter" || event.key === " ") && !open) { event.preventDefault(); reveal("keyboard"); } }}><div className="mirror-cover"><p className="eyebrow">ONE LAST COMPARISON</p><h2 id={`${page.id}-heading`}>{page.content?.title ?? page.title}</h2>{!open && <><p className="story-lede">{page.content?.closed ?? page.body}</p><button type="button" className="mirror-reveal-button" onClick={() => reveal("button")}>Reveal Hero Mirror</button><p className="muted mirror-gesture-hint">Swipe across this card, or use the button.</p></>}</div>{open && <MirrorReveal mirror={mirror} content={page.content ?? {}} />}</article>;
}

function MirrorReveal({ mirror, content }: { mirror: FreeDnaReportV4["hero_portfolio"]["hero_mirror"]; content: StoryPage["content"] }) {
  if (mirror.status !== "available" || !mirror.hero_name) return <UnavailableMessage limitations={[content.unavailable ?? "No played hero matches your usual behavior clearly enough to earn the mirror yet."]} />;
  const rows = ["involvement", "finishing", "deaths", "role_context"];
  return <div className="mirror-reveal" aria-live="polite"><p className="story-lede">{content.available ?? `Hero Mirror: ${mirror.hero_name}`}</p><p className="muted">{content.qualifier}</p><div className="hero-behavior-table" role="table" aria-label="Player and hero behavior comparison"><div className="hero-behavior-row header" role="row"><span>Observable behavior</span><span>Your history</span><span>{mirror.hero_name}</span></div>{rows.map((key) => <div className="hero-behavior-row" role="row" key={key}><strong>{key.replaceAll("_", " ")}</strong><span>{mirror.player_behavior[key] ?? "Not available"}</span><span>{mirror.hero_behavior[key] ?? "Not available"}</span></div>)}</div><p className="muted">{content.guardrail} {mirror.limitations.join(" ")}</p></div>;
}

function FinalCard({ page, report }: { page: StoryPage; report: FreeDnaReportV4 }) {
  const strongestElements = report.highlights.element_keys.map((key) => report.elements.find((element) => element.key === key)).filter((element): element is BehaviorElement => Boolean(element));
  const strongestPatterns = report.highlights.pattern_keys.map((key) => report.patterns.find((pattern) => pattern.key === key)).filter((pattern): pattern is BehaviorPattern => Boolean(pattern));
  return <article className="final-card"><p className="eyebrow">{page.title}</p><h2 id={`${page.id}-heading`}>{report.identity.display_name || "Your Dota DNA"}</h2><p className="story-lede">{page.body}</p><div className="final-summary"><div><span className="eyebrow">Elements</span><div className="descriptor-list">{strongestElements.map((element) => <span key={element.key}>{element.label} · {element.zone ?? "Unavailable"}</span>)}</div></div><div><span className="eyebrow">Patterns</span><div className="descriptor-list">{strongestPatterns.map((pattern) => <span key={pattern.key}>{pattern.label}</span>)}</div></div><div><span className="eyebrow">Hero Portfolio</span><p>{report.shares.final.hero_portfolio.common_thread ?? "No clear Common Thread yet."}</p><p>{report.shares.final.hero_portfolio.exception_hero ? `Exception · ${report.shares.final.hero_portfolio.exception_hero}` : "No clear Exception yet."}</p><p>{report.shares.final.hero_portfolio.pool_direction ?? "Pool Evolution is unavailable yet."}</p></div><div><span className="eyebrow">Hero Mirror</span><p>{report.shares.final.hero_mirror?.hero_name ?? "No clear Mirror yet."}</p></div></div>{report.report_id && <ShareControls reportId={report.report_id} reportSchema={report.schema_version} />}</article>;
}

function UnavailableMessage({ limitations }: { limitations: string[] }) {
  return <div className="unavailable-message"><strong>Not enough evidence yet</strong><p>{limitations.join(" ") || "These matches did not support a clear answer yet."}</p></div>;
}

function FallbackPage({ page }: { page: StoryPage }) {
  return <article className="story-summary"><p className="eyebrow">Dota DNA</p><h2 id={`${page.id}-heading`}>{page.title}</h2>{page.body && <p>{page.body}</p>}</article>;
}
