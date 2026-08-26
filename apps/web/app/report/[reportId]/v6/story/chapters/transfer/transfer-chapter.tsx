import type { StoryModel, StoryFamilyModel } from "../../story-model";
import styles from "./transfer-chapter.module.css";

export type TransferStatus = "qualified" | "neutral" | "insufficient" | "unavailable";
export type TransferMetric = { label: string; value: string };
export type TransferData = {
  status: TransferStatus;
  familiarHero?: string | null;
  stretchHero?: string | null;
  question?: string | null;
  coreMeasurement?: TransferMetric | null;
  stretchMeasurement?: TransferMetric | null;
  result?: string | null;
  evidence?: string | null;
};
export type TransferPhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

export function createTransferData(model: Pick<StoryModel, "transfer" | "heroes">): TransferData {
  const finding = model.transfer.finding;
  const rows = comparisonRows(finding);
  const first = rows[0];
  const second = rows[1];
  const heroes = model.heroes.heroes ?? [];
  return {
    status: findingStatus(model.transfer),
    familiarHero: heroes[0]?.display_name ?? heroes[0]?.hero_name ?? heroes[0]?.name,
    stretchHero: heroes[1]?.display_name ?? heroes[1]?.hero_name ?? heroes[1]?.name,
    question: finding?.claim ?? finding?.title ?? finding?.label,
    coreMeasurement: first ? { label: first.label, value: first.value } : null,
    stretchMeasurement: second ? { label: second.label, value: second.value } : null,
    result: finding?.interpretation ?? finding?.observation,
    evidence: evidenceText(finding),
  };
}

export function TransferChapter({ data, phase = 0, onAdvance }: { data: TransferData; phase?: TransferPhase; onAdvance?: () => void }) {
  const reveal = (at: TransferPhase) => phase === at;
  const qualified = data.status === "qualified";
  return (
    <section className={styles.chapter} data-phase={phase} aria-label="Transfer">
      <div className={`${styles.state} ${reveal(0) ? styles.visible : ""}`} aria-hidden={!reveal(0)}><span className={styles.eyebrow}>Boundary</span><TransferBoundary data={data} phase={phase} /><h1>What happens when the hero changes?</h1></div>
      <div className={`${styles.state} ${reveal(1) ? styles.visible : ""}`} aria-hidden={!reveal(1)}><span className={styles.eyebrow}>Hero crosses boundary</span><p className={styles.crossing}>{data.familiarHero || "Familiar hero"}<span aria-hidden="true">→</span>{data.stretchHero || "Stretch hero"}</p></div>
      <div className={`${styles.state} ${reveal(2) ? styles.visible : ""}`} aria-hidden={!reveal(2)}><span className={styles.eyebrow}>Transfer question</span><h2>{data.question || "What survives when your comfort zone changes?"}</h2></div>
      <div className={`${styles.measurements} ${reveal(3) ? styles.visible : ""}`} aria-hidden={!reveal(3)}><span className={styles.eyebrow}>Core measurements</span><Measurement metric={data.coreMeasurement} /></div>
      <div className={`${styles.measurements} ${reveal(4) ? styles.visible : ""}`} aria-hidden={!reveal(4)}><span className={styles.eyebrow}>Stretch measurements</span><Measurement metric={data.stretchMeasurement} /></div>
      <div className={`${styles.state} ${reveal(5) ? styles.visible : ""}`} aria-hidden={!reveal(5)}><span className={styles.eyebrow}>{qualified ? "Transfer result" : statusLabel(data.status)}</span><h2>{qualified ? (data.result || "Transfer result is available in the evidence.") : fallbackCopy(data.status)}</h2></div>
      <div className={`${styles.state} ${reveal(6) ? styles.visible : ""}`} aria-hidden={!reveal(6)}><span className={styles.eyebrow}>Evidence summary</span><p>{data.evidence || "No evidence summary was supplied for this comparison."}</p></div>
      <div className={`${styles.state} ${reveal(7) ? styles.visible : ""}`} aria-hidden={!reveal(7)}><span className={styles.eyebrow}>Leave comfort</span><p>The boundary makes the next question visible.</p></div>
      <div className={`${styles.state} ${reveal(8) ? styles.visible : ""}`} aria-hidden={!reveal(8)}><span className={styles.eyebrow}>Introduce loss</span><h2>Now look at what changes after a loss.</h2></div>
      {onAdvance && <button className={styles.advance} type="button" onClick={onAdvance}>Continue <span aria-hidden="true">→</span></button>}
    </section>
  );
}

function TransferBoundary({ data, phase }: { data: TransferData; phase: TransferPhase }) {
  return <div className={styles.boundary} aria-label="Hero transfer boundary"><span className={styles.boundaryLine} /><span className={`${styles.heroNode} ${phase >= 1 ? styles.heroCrossed : ""}`}><span aria-hidden="true">{(data.familiarHero || data.stretchHero || "?").slice(0, 2).toUpperCase()}</span><small>{data.familiarHero || "Hero"}</small></span><span className={styles.boundaryLabel}>FAMILIAR / STRETCH</span></div>;
}

function Measurement({ metric }: { metric?: TransferMetric | null }) {
  return metric ? <div className={styles.metric}><strong>{metric.value}</strong><span>{metric.label}</span></div> : <p className={styles.unavailable}>Measurement not available.</p>;
}

function findingStatus(family: StoryFamilyModel): TransferStatus {
  const finding = family.finding;
  if (!finding || finding.status === "unavailable") return "unavailable";
  if (finding.status === "insufficient" || finding.status === "limited") return "insufficient";
  if (finding.status === "suppressed" || finding.published !== true) return "neutral";
  return "qualified";
}

function statusLabel(status: TransferStatus): string {
  return { qualified: "Qualified", neutral: "Neutral", insufficient: "Insufficient evidence", unavailable: "Unavailable" }[status];
}

function fallbackCopy(status: TransferStatus): string {
  if (status === "insufficient") return "Not enough signal to call transfer here.";
  if (status === "neutral") return "The supported comparison does not separate cleanly.";
  return "Transfer is unavailable for this report.";
}

function comparisonRows(finding: StoryFamilyModel["finding"]): TransferMetric[] {
  const comparison = finding?.comparison;
  const rows = comparison?.positive ?? comparison?.rows ?? comparison?.contexts ?? [];
  return rows.slice(0, 2).map((row) => ({ label: row.label, value: typeof row.value === "string" ? row.value : typeof row.value === "number" ? String(row.value) : typeof row.estimate === "number" ? String(row.estimate) : "Not available" }));
}

function evidenceText(finding: StoryFamilyModel["finding"]): string {
  if (!finding) return "";
  if (typeof finding.evidence === "string") return finding.evidence;
  return finding.evidence_text ?? finding.observation ?? "";
}
