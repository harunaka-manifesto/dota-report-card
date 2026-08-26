import type { StoryModel, StoryFamilyModel } from "../../story-model";
import { MatchTimeline, type MatchCell, type MatchTimelinePhase } from "../../visualizations/match-timeline";
import styles from "./post-loss-chapter.module.css";

export type PostLossStatus = "qualified" | "neutral" | "insufficient" | "unavailable";
export type PostLossData = {
  status: PostLossStatus;
  matches: readonly MatchCell[];
  typical?: string | null;
  afterLoss?: string | null;
  outcome?: string | null;
  whyItMatters?: string | null;
  evidence?: string | null;
};
export type PostLossPhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export function createPostLossData(model: Pick<StoryModel, "postLoss">): PostLossData {
  const finding = model.postLoss.finding;
  const rows = comparisonRows(finding);
  return {
    status: findingStatus(model.postLoss),
    matches: rows.map((row, index) => ({ id: `${row.label}-${index}`, label: row.label, result: row.value, context: row.context, isLoss: /loss/i.test(`${row.label} ${row.context ?? ""}`) })),
    typical: rows[0]?.value,
    afterLoss: rows[1]?.value,
    outcome: finding?.claim ?? finding?.title ?? finding?.interpretation,
    whyItMatters: finding?.interpretation,
    evidence: evidenceText(finding),
  };
}

export function PostLossChapter({ data, phase = 0, onAdvance }: { data: PostLossData; phase?: PostLossPhase; onAdvance?: () => void }) {
  const reveal = (at: PostLossPhase) => phase === at;
  const qualified = data.status === "qualified";
  return (
    <section className={styles.chapter} data-phase={phase} aria-label="Post-loss response">
      <div className={`${styles.state} ${reveal(0) ? styles.visible : ""}`} aria-hidden={!reveal(0)}><span className={styles.eyebrow}>Match timeline</span><h1>What happens after a loss?</h1><MatchTimeline matches={data.matches} phase={phase as MatchTimelinePhase} /></div>
      <div className={`${styles.state} ${reveal(1) ? styles.visible : ""}`} aria-hidden={!reveal(1)}><span className={styles.eyebrow}>Possibilities</span><p>After a loss, the next choice can repeat, move, or stop the old path.</p></div>
      <div className={`${styles.state} ${reveal(2) ? styles.visible : ""}`} aria-hidden={!reveal(2)}><span className={styles.eyebrow}>Next match revealed</span><p className={styles.nextMatch}>{data.matches[1]?.label || "Next match not available"}<span>{data.matches[1]?.result || "Result not available"}</span></p></div>
      <div className={`${styles.state} ${reveal(3) ? styles.visible : ""}`} aria-hidden={!reveal(3)}><span className={styles.eyebrow}>Typical vs after loss</span><Comparison typical={data.typical} afterLoss={data.afterLoss} /></div>
      <div className={`${styles.state} ${reveal(4) ? styles.visible : ""}`} aria-hidden={!reveal(4)}><span className={styles.eyebrow}>{qualified ? "Outcome highlight" : statusLabel(data.status)}</span><h2>{qualified ? (data.outcome || "The observed response is available in the evidence.") : fallbackCopy(data.status)}</h2></div>
      <div className={`${styles.state} ${reveal(5) ? styles.visible : ""}`} aria-hidden={!reveal(5)}><span className={styles.eyebrow}>Why it matters</span><p>{data.whyItMatters || "The supported comparison does not establish a stronger interpretation."}</p></div>
      <details className={`${styles.evidence} ${reveal(6) ? styles.visible : ""}`} aria-hidden={!reveal(6)} open={phase === 6}><summary>Evidence expanded</summary><p>{data.evidence || "Evidence details are not available for this report."}</p></details>
      <div className={`${styles.state} ${reveal(7) ? styles.visible : ""}`} aria-hidden={!reveal(7)}><span className={styles.eyebrow}>Match collapses</span><p>The timeline narrows to the transition that the data supports.</p></div>
      <div className={`${styles.state} ${reveal(8) ? styles.visible : ""}`} aria-hidden={!reveal(8)}><span className={styles.eyebrow}>Inside the match</span><p>{data.evidence || "Inside-match evidence is not available in this report."}</p></div>
      {onAdvance && <button className={styles.advance} type="button" onClick={onAdvance}>Continue <span aria-hidden="true">→</span></button>}
    </section>
  );
}

function Comparison({ typical, afterLoss }: { typical?: string | null; afterLoss?: string | null }) {
  return <div className={styles.comparison}><div><span>Typical</span><strong>{typical || "Not available"}</strong></div><div><span>After loss</span><strong>{afterLoss || "Not available"}</strong></div></div>;
}

function findingStatus(family: StoryFamilyModel): PostLossStatus {
  const finding = family.finding;
  if (!finding || finding.status === "unavailable") return "unavailable";
  if (finding.status === "insufficient" || finding.status === "limited") return "insufficient";
  if (finding.status === "suppressed" || finding.published !== true) return "neutral";
  return "qualified";
}

function statusLabel(status: PostLossStatus): string {
  return { qualified: "Qualified", neutral: "Neutral", insufficient: "Insufficient evidence", unavailable: "Unavailable" }[status];
}

function fallbackCopy(status: PostLossStatus): string {
  if (status === "insufficient") return "Not enough signal to call a post-loss response.";
  if (status === "neutral") return "The supported response does not separate cleanly.";
  return "Post-loss response is unavailable for this report.";
}

function comparisonRows(finding: StoryFamilyModel["finding"]): Array<{ label: string; value: string; context?: string | null }> {
  const comparison = finding?.comparison;
  const rows = comparison?.positive ?? comparison?.rows ?? comparison?.contexts ?? [];
  return rows.slice(0, 5).map((row) => ({ label: row.label, value: typeof row.value === "string" ? row.value : typeof row.value === "number" ? String(row.value) : typeof row.estimate === "number" ? String(row.estimate) : "Not available", context: row.direction }));
}

function evidenceText(finding: StoryFamilyModel["finding"]): string {
  if (!finding) return "";
  if (typeof finding.evidence === "string") return finding.evidence;
  return finding.evidence_text ?? finding.observation ?? "";
}
