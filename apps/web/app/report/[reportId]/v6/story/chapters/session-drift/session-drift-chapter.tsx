import type { V6Finding } from "../../../types";
import type { StoryModel } from "../../story-model";
import { comparisonRowsToSessionPoints, SessionCurve, type SessionCurvePhase, type SessionPoint } from "../../visualizations/session-curve";
import styles from "./session-drift-chapter.module.css";

export type SessionDriftState = "qualified" | "neutral" | "insufficient";
export type SessionDriftPhase = SessionCurvePhase;

export type SessionDriftData = {
  state: SessionDriftState;
  claim?: string | null;
  interpretation?: string | null;
  evidence: readonly string[];
  alternatives: readonly string[];
  points: readonly SessionPoint[];
};

export function createSessionDriftData(model: Pick<StoryModel, "session">): SessionDriftData {
  const finding = model.session.finding;
  const rows = [finding?.comparison?.rows ?? [], finding?.comparison?.positive ?? [], finding?.comparison?.negative ?? [], finding?.comparison?.control ?? []].flat();
  return {
    state: findingState(finding),
    claim: claimFor(finding),
    interpretation: interpretationFor(finding),
    evidence: evidenceFor(finding),
    alternatives: finding?.claim_contract?.alternatives ?? finding?.layers?.alternatives ?? [],
    points: comparisonRowsToSessionPoints(rows),
  };
}

export function SessionDriftChapter({
  data,
  phase = 0,
  onAdvance,
}: {
  data: SessionDriftData;
  phase?: SessionDriftPhase;
  onAdvance?: () => void;
}) {
  if (data.state !== "qualified") {
    return (
      <section className={styles.chapter} data-phase={phase} data-state={data.state} aria-label="Session Drift">
        <div className={styles.stateCard} role="status">
          <span className={styles.eyebrow}>Session drift · {data.state}</span>
          <h1>{data.state === "neutral" ? "No single session movement owns the read." : "Not enough completed sessions yet."}</h1>
          <p>{data.state === "neutral" ? "The supported session signals remain compatible in this sample." : "The report keeps this conclusion open until more completed sessions are available."}</p>
        </div>
      </section>
    );
  }

  const reveal = (at: SessionDriftPhase) => phase === at;
  return (
    <section className={styles.chapter} data-phase={phase} data-state={data.state} aria-label="Session Drift">
      <div className={`${styles.state} ${reveal(0) ? styles.visible : ""}`} aria-hidden={!reveal(0)}>
        <span className={styles.eyebrow}>Session skeleton</span>
        <h1>A session is more than one match.</h1>
        <SessionCurve points={data.points} phase={phase} />
      </div>

      <div className={`${styles.state} ${reveal(1) ? styles.visible : ""}`} aria-hidden={!reveal(1)}>
        <span className={styles.eyebrow}>Game 1</span>
        <h2>The opening game sets the first point.</h2>
        <SessionCurve points={data.points} phase={phase} />
      </div>

      <div className={`${styles.state} ${reveal(2) ? styles.visible : ""}`} aria-hidden={!reveal(2)}>
        <span className={styles.eyebrow}>Games 2–3</span>
        <h2>The next points show whether that shape repeats.</h2>
        <SessionCurve points={data.points} phase={phase} />
      </div>

      <div className={`${styles.state} ${reveal(3) ? styles.visible : ""}`} aria-hidden={!reveal(3)}>
        <span className={styles.eyebrow}>Games 4–5+</span>
        <h2>Later games add the longer view.</h2>
        <SessionCurve points={data.points} phase={phase} />
      </div>

      <div className={`${styles.state} ${reveal(4) ? styles.visible : ""}`} aria-hidden={!reveal(4)}>
        <span className={styles.eyebrow}>Relevant movement highlighted</span>
        <SessionCurve points={data.points} phase={phase} />
      </div>

      <div className={`${styles.state} ${styles.analytical} ${reveal(5) ? styles.visible : ""}`} aria-hidden={!reveal(5)}>
        <span className={styles.eyebrow}>Session result</span>
        <h2>{data.claim ?? "No server-authored session outcome was provided."}</h2>
        {data.interpretation && <p>{data.interpretation}</p>}
      </div>

      <div className={`${styles.state} ${styles.analytical} ${reveal(6) ? styles.visible : ""}`} aria-hidden={!reveal(6)}>
        <span className={styles.eyebrow}>Session evidence</span>
        <EvidenceList evidence={data.evidence} alternatives={data.alternatives} />
      </div>

      <div className={`${styles.state} ${reveal(7) ? styles.visible : ""}`} aria-hidden={!reveal(7)}>
        <span className={styles.eyebrow}>Zoom out</span>
        <h2>The curve is a shape across matches, not a verdict on one match.</h2>
        <SessionCurve points={data.points} phase={phase} />
      </div>

      <div className={`${styles.state} ${styles.analytical} ${reveal(8) ? styles.visible : ""}`} aria-hidden={!reveal(8)}>
        <span className={styles.eyebrow}>Recurrence</span>
        <p>{data.interpretation ?? "No server-authored recurrence interpretation was provided."}</p>
      </div>

      {onAdvance && <button className={styles.advance} type="button" onClick={onAdvance}>Continue <span aria-hidden="true">→</span></button>}
    </section>
  );
}

function EvidenceList({ evidence, alternatives }: { evidence: readonly string[]; alternatives: readonly string[] }) {
  if (evidence.length === 0 && alternatives.length === 0) return <p>No server-authored evidence was provided.</p>;
  return <div className={styles.evidence}><ul>{evidence.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>{alternatives.length > 0 && <><span className={styles.subhead}>Alternatives kept in view</span><ul>{alternatives.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></>}</div>;
}

function findingState(finding: V6Finding | null): SessionDriftState {
  if (!finding || finding.status === "limited" || finding.status === "unavailable") return "insufficient";
  if (finding.status === "suppressed" || finding.direction === "neutral") return "neutral";
  return finding.published === false ? "neutral" : "qualified";
}

function claimFor(finding: V6Finding | null): string | null {
  const claim = finding?.claim ?? finding?.claim_contract?.claim ?? finding?.layers?.claim;
  return typeof claim === "string" && claim.trim() ? claim.trim() : null;
}

function interpretationFor(finding: V6Finding | null): string | null {
  const interpretation = finding?.interpretation ?? finding?.claim_contract?.interpretation ?? finding?.layers?.interpretation;
  return typeof interpretation === "string" && interpretation.trim() ? interpretation.trim() : null;
}

function evidenceFor(finding: V6Finding | null): string[] {
  if (!finding) return [];
  const values: unknown[] = [finding.evidence_text, typeof finding.evidence === "string" ? finding.evidence : null, finding.claim_contract?.evidence, finding.layers?.evidence];
  if (Array.isArray(finding.evidence)) values.push(...finding.evidence.flatMap((item) => [item.observation, item.label]));
  if (finding.evidence_items) values.push(...finding.evidence_items.flatMap((item) => [item.observation, item.label]));
  return [...new Set(values.filter((value): value is string => typeof value === "string" && value.trim().length > 0).map((value) => value.trim()))];
}
