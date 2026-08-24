import type { BehaviorPattern, StoryPage } from "../../../../../../packages/api-client/src";
import { useEffect, useRef } from "react";
import { track } from "../../../lib/analytics";
import { EvidenceReceipt } from "../primitives";
import { HeroJobCluster } from "./hero-job-cluster";
import { HeroReliabilityLadder } from "./hero-reliability-ladder";
import { FlexWindowGrid } from "./flex-window-grid";
import { PostLossTransition } from "./post-loss-transition";
import { PresenceExposureMap } from "./presence-exposure-map";
import { SessionCurve } from "./session-curve";
import { ToolkitOrbit } from "./toolkit-orbit";
import { TransferSplit } from "./transfer-split";

type PatternStoryScreenProps = {
  pattern: BehaviorPattern;
  page: StoryPage;
  reportSchemaVersion: string;
};

export function PatternStoryScreen({ pattern, page, reportSchemaVersion }: PatternStoryScreenProps) {
  const presentation = pattern.presentation;
  const copy = page.content?.presentation_copy;
  const evidenceRef = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const evidence = evidenceRef.current;
    if (!evidence) return;
    const handleToggle = () => {
      if (evidence.open) track("report.pattern_element_expanded.v1", {
        pattern_key: pattern.key,
        report_schema_version: reportSchemaVersion,
      });
    };
    evidence.addEventListener("toggle", handleToggle);
    return () => evidence.removeEventListener("toggle", handleToggle);
  }, [pattern.key, reportSchemaVersion]);
  if (!presentation || !copy) return null;
  const nextStep = copy.recommendation ?? {
    eyebrow: "NEXT STEP",
    title: copy.fallback.title ?? "Keep the pattern testable",
    body: copy.fallback.body ?? "Use another supported window before turning this relationship into a stronger claim.",
  };
  return (
    <article className={`pattern-story-screen pattern-story-${presentation.visual_variant}`} data-pattern-id={pattern.key} data-outcome-id={presentation.outcome_id}>
      <header className="pattern-story-reveal">
        <p className="eyebrow">{pattern.label} · reveal</p>
        <h2 id={`${page.id}-heading`}>{copy.headline}</h2>
        <p className="story-lede">{copy.subheadline}</p>
      </header>
      <section className="pattern-story-proof" aria-labelledby={`${page.id}-proof-heading`}>
        <h3 id={`${page.id}-proof-heading`} className="visually-hidden">Visual proof</h3>
        <PatternVisual presentation={presentation} />
      </section>
      <section className="pattern-story-interpretation" aria-labelledby={`${page.id}-interpretation-heading`}>
        <span className="eyebrow">What this actually means</span>
        <h3 id={`${page.id}-interpretation-heading`}>{copy.interpretation.title}</h3>
        <p>{copy.interpretation.body}</p>
      </section>
      <section className={`pattern-story-recommendation${copy.recommendation ? "" : " is-fallback"}`} aria-labelledby={`${page.id}-next-step-heading`}><span className="eyebrow">{nextStep.eyebrow}</span><h3 id={`${page.id}-next-step-heading`}>{nextStep.title}</h3><p>{nextStep.body}</p>{copy.recommendation && presentation.recommendation_id && typeof presentation.recommendation_context?.hero_name === "string" && <span className="recommendation-hero">{presentation.recommendation_context.hero_name}</span>}<RecommendationFacts context={presentation.recommendation_context} /></section>
      {copy.deep_dive && presentation.deep_dive_id && <aside className="pattern-story-deep-dive"><span className="eyebrow">Next diagnostic question</span><h3>{copy.deep_dive.title}</h3><p>{copy.deep_dive.body}</p><a href="#deep-diagnostic" onClick={() => { window.dispatchEvent(new CustomEvent("dota-dna:deep-dive", { detail: { pattern: pattern.key, reportSchemaVersion } })); }}>Explore Deep Dive →</a></aside>}
      <details ref={evidenceRef} className="pattern-story-evidence"><summary>Evidence details</summary><EvidenceReceipt evidence={pattern.receipts} /><dl className="pattern-raw-metrics">{Object.entries(presentation.raw_metrics).map(([key, value]) => <div key={key}><dt>{metricLabel(key)}</dt><dd>{formatMetricValue(key, value)}</dd></div>)}</dl><p className="muted">Confidence: {presentation.confidence}. Evidence references: {presentation.evidence_refs.join(", ") || "pattern qualification"}.</p></details>
      {pattern.story_blockers.length > 0 && <p className="muted">{pattern.story_blockers.join(" ")}</p>}
    </article>
  );
}

function RecommendationFacts({ context }: { context: Record<string, unknown> | null }) {
  if (!context || context.kind !== "hero") return null;
  const anchors = stringList(context.familiar_anchors);
  const additions = stringList(context.adds);
  const demands = stringList(context.new_demands);
  const learningDistance = publicLabel(context.learning_distance);
  const roleFit = publicLabel(context.role_fit);
  const confidence = publicLabel(context.confidence);
  return <dl className="pattern-recommendation-facts" aria-label="Why this recommendation fits">
    {anchors.length > 0 && <div><dt>Stays familiar</dt><dd>{anchors.join(", ")}</dd></div>}
    {additions.length > 0 && <div><dt>Adds</dt><dd>{additions.join(", ")}</dd></div>}
    {learningDistance && <div><dt>Learning step</dt><dd>{learningDistance}</dd></div>}
    {roleFit && <div><dt>Role check</dt><dd>{roleFit}</dd></div>}
    {demands.length > 0 && <div><dt>New demands</dt><dd>{demands.join(", ")}</dd></div>}
    {confidence && <div><dt>Confidence</dt><dd>{confidence}</dd></div>}
  </dl>;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string").map((item) => publicLabel(item) ?? item) : [];
}

function publicLabel(value: unknown): string | null {
  if (typeof value !== "string" || !value.trim()) return null;
  return value.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function PatternVisual({ presentation }: { presentation: NonNullable<BehaviorPattern["presentation"]> }) {
  const props = { patternId: presentation.pattern_id, variant: presentation.visual_variant, proof: presentation.proof_data };
  if (presentation.visual_variant === "hero_job_cluster") return <HeroJobCluster {...props} />;
  if (presentation.visual_variant === "hero_reliability_ladder") return <HeroReliabilityLadder {...props} />;
  if (presentation.visual_variant === "transfer_split") return <TransferSplit {...props} />;
  if (presentation.visual_variant === "toolkit_orbit") return <ToolkitOrbit {...props} />;
  if (presentation.visual_variant === "flex_window_grid") return <FlexWindowGrid {...props} />;
  if (presentation.visual_variant === "post_loss_transition") return <PostLossTransition {...props} />;
  if (presentation.visual_variant === "presence_exposure_map") return <PresenceExposureMap {...props} />;
  if (presentation.visual_variant === "session_curve") return <SessionCurve {...props} />;
  return <div className="pattern-visual pattern-visual-fallback" role="status">Visual proof is unavailable for this presentation version. Evidence details remain available below.</div>;
}

const METRIC_LABELS: Record<string, string> = {
  effective_sample_size: "Effective sample size",
  confidence_score: "Confidence",
  evidence_coverage: "Evidence coverage",
  relationship_strength: "How clearly it repeats",
  result_delta: "Result difference",
  hero_distribution_shift: "Hero-pool shift",
  toolkit_distribution_shift: "Toolkit shift",
};

function metricLabel(key: string): string {
  return METRIC_LABELS[key] ?? key.replaceAll("_", " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function formatMetricValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return "Not available";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value !== "number" || !Number.isFinite(value)) return String(value);
  if (key.includes("coverage") || key.includes("confidence") || key.includes("share")) return `${Math.round(value * 100)}%`;
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}
