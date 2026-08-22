import type { BehaviorPattern, StoryPage } from "../../../../../../packages/api-client/src";
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
  if (!presentation || !copy) return null;
  return (
    <article className={`pattern-story-screen pattern-story-${presentation.visual_variant}`} data-pattern-id={pattern.key} data-outcome-id={presentation.outcome_id}>
      <header className="pattern-story-reveal">
        <p className="eyebrow">{pattern.label} · reveal</p>
        <h2 id={`${page.id}-heading`}>{copy.headline}</h2>
        <p className="story-lede">{copy.subheadline}</p>
      </header>
      <PatternVisual presentation={presentation} />
      <section className="pattern-story-interpretation">
        <span className="eyebrow">What this actually means</span>
        <h3>{copy.interpretation.title}</h3>
        <p>{copy.interpretation.body}</p>
      </section>
      {copy.recommendation && presentation.recommendation_id && <section className="pattern-story-recommendation"><span className="eyebrow">{copy.recommendation.eyebrow}</span><h3>{copy.recommendation.title}</h3><p>{copy.recommendation.body}</p>{typeof presentation.recommendation_context?.hero_name === "string" && <span className="recommendation-hero">{presentation.recommendation_context.hero_name}</span>}</section>}
      {copy.deep_dive && presentation.deep_dive_id && <aside className="pattern-story-deep-dive"><span className="eyebrow">Next diagnostic question</span><h3>{copy.deep_dive.title}</h3><p>{copy.deep_dive.body}</p><a href="/?mode=deep_scan" onClick={() => { window.dispatchEvent(new CustomEvent("dota-dna:deep-dive", { detail: { pattern: pattern.key, reportSchemaVersion } })); }}>Explore Deep Dive →</a></aside>}
      <details className="pattern-story-evidence"><summary>Evidence details</summary><EvidenceReceipt evidence={pattern.receipts} /><dl className="pattern-raw-metrics">{Object.entries(presentation.raw_metrics).map(([key, value]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{String(value)}</dd></div>)}</dl><p className="muted">Confidence: {presentation.confidence}. Evidence references: {presentation.evidence_refs.join(", ") || "pattern qualification"}.</p></details>
      {pattern.story_blockers.length > 0 && <p className="muted">{pattern.story_blockers.join(" ")}</p>}
    </article>
  );
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
  return <SessionCurve {...props} />;
}
