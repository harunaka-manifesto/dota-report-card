import type { V6Finding } from "../../../types";
import type { StoryModel } from "../../story-model";
import styles from "./combat-expression-chapter.module.css";

export type CombatExpressionPhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9;
export type CombatExpressionState = "qualified" | "neutral" | "insufficient";

export type CombatSignal = {
  key: "involvement" | "exposure";
  label: string;
  value?: string | number | null;
  revealAt: 1 | 3 | 4;
};

export type CombatExpressionData = {
  state: CombatExpressionState;
  claim?: string | null;
  interpretation?: string | null;
  evidence: readonly string[];
  alternatives: readonly string[];
  signals: readonly CombatSignal[];
};

/** Adapter keeps the chapter on the presentation model, not raw report data. */
export function createCombatExpressionData(model: Pick<StoryModel, "combat">): CombatExpressionData {
  const finding = model.combat.finding;
  return {
    state: findingState(finding),
    claim: claimFor(finding),
    interpretation: interpretationFor(finding),
    evidence: evidenceFor(finding),
    alternatives: finding?.claim_contract?.alternatives ?? finding?.layers?.alternatives ?? [],
    signals: signalsFor(finding),
  };
}

export function CombatExpressionChapter({
  data,
  phase = 0,
  onAdvance,
}: {
  data: CombatExpressionData;
  phase?: CombatExpressionPhase;
  onAdvance?: () => void;
}) {
  if (data.state !== "qualified") {
    return (
      <section className={styles.chapter} data-phase={phase} data-state={data.state} aria-label="Combat Expression">
        <div className={styles.stateCard} role="status">
          <span className={styles.eyebrow}>Combat expression · {data.state}</span>
          <h1>{data.state === "neutral" ? "No single combat signal owns the read." : "Not enough combat evidence yet."}</h1>
          <p>{data.state === "neutral" ? "The supported signals remain compatible in this sample." : "The report keeps the conclusion open until the supported sample is larger."}</p>
        </div>
      </section>
    );
  }

  const reveal = (at: CombatExpressionPhase) => phase === at;
  const signal = (key: CombatSignal["key"]) => data.signals.find((item) => item.key === key);
  return (
    <section className={styles.chapter} data-phase={phase} data-state={data.state} aria-label="Combat Expression">
      <div className={`${styles.state} ${reveal(0) ? styles.visible : ""}`} aria-hidden={!reveal(0)}>
        <span className={styles.eyebrow}>Combat expression · Quiet signal</span>
        <h1>Two signals begin apart.</h1>
        <SignalPair signals={data.signals} phase={phase} />
      </div>

      <div className={`${styles.state} ${reveal(1) ? styles.visible : ""}`} aria-hidden={!reveal(1)}>
        <span className={styles.eyebrow}>Signal activates</span>
        <h2>Involvement and exposure do not mean the same thing.</h2>
        <SignalPair signals={data.signals} phase={phase} />
      </div>

      <div className={`${styles.state} ${reveal(2) ? styles.visible : ""}`} aria-hidden={!reveal(2)}>
        <span className={styles.eyebrow}>Components separate</span>
        <SignalPair signals={data.signals} phase={phase} separated />
      </div>

      <div className={`${styles.state} ${reveal(3) ? styles.visible : ""}`} aria-hidden={!reveal(3)}>
        <span className={styles.eyebrow}>First signal</span>
        <SignalDetail signal={signal("involvement")} />
      </div>

      <div className={`${styles.state} ${reveal(4) ? styles.visible : ""}`} aria-hidden={!reveal(4)}>
        <span className={styles.eyebrow}>Second signal</span>
        <SignalDetail signal={signal("exposure")} />
      </div>

      <div className={`${styles.state} ${reveal(5) ? styles.visible : ""}`} aria-hidden={!reveal(5)}>
        <span className={styles.eyebrow}>Signals recombine</span>
        <SignalPair signals={data.signals} phase={phase} />
      </div>

      <div className={`${styles.state} ${styles.analytical} ${reveal(6) ? styles.visible : ""}`} aria-hidden={!reveal(6)}>
        <span className={styles.eyebrow}>Combat outcome</span>
        <h2>{data.claim ?? "No server-authored combat outcome was provided."}</h2>
        {data.interpretation && <p>{data.interpretation}</p>}
      </div>

      <div className={`${styles.state} ${styles.analytical} ${reveal(7) ? styles.visible : ""}`} aria-hidden={!reveal(7)}>
        <span className={styles.eyebrow}>Combat evidence</span>
        <EvidenceList evidence={data.evidence} alternatives={data.alternatives} />
      </div>

      <div className={`${styles.state} ${reveal(8) ? styles.visible : ""}`} aria-hidden={!reveal(8)}>
        <span className={styles.eyebrow}>One match</span>
        <p>One observed match can show expression. The pattern needs repeated support.</p>
        <SignalPair signals={data.signals} phase={phase} />
      </div>

      <div className={`${styles.state} ${reveal(9) ? styles.visible : ""}`} aria-hidden={!reveal(9)}>
        <span className={styles.eyebrow}>Five copies</span>
        <div className={styles.copyGrid} aria-label="Repeated combat signal copies">
          {[0, 1, 2, 3, 4].map((copy) => <SignalPair key={copy} signals={data.signals} phase={phase} />)}
        </div>
      </div>

      {onAdvance && <button className={styles.advance} type="button" onClick={onAdvance}>Continue <span aria-hidden="true">→</span></button>}
    </section>
  );
}

function SignalPair({ signals, phase, separated = false }: { signals: readonly CombatSignal[]; phase: CombatExpressionPhase; separated?: boolean }) {
  return (
    <div className={`${styles.signalPair} ${separated ? styles.separated : ""}`} role="img" aria-label="Two combat signals">
      {signals.map((signal) => <div className={`${styles.signal} ${phase >= signal.revealAt ? styles.signalVisible : ""}`} data-signal={signal.key} key={signal.key}>
        <span className={styles.signalMark} aria-hidden="true" />
        <span className={styles.signalLabel}>{signal.label}</span>
        {signal.value !== null && signal.value !== undefined && <strong>{signal.value}</strong>}
      </div>)}
    </div>
  );
}

function SignalDetail({ signal }: { signal?: CombatSignal }) {
  return <div className={styles.signalDetail}><span className={styles.signalMark} aria-hidden="true" /><h2>{signal?.label ?? "Signal unavailable"}</h2>{signal?.value !== null && signal?.value !== undefined && <strong>{signal.value}</strong>}</div>;
}

function EvidenceList({ evidence, alternatives }: { evidence: readonly string[]; alternatives: readonly string[] }) {
  if (evidence.length === 0 && alternatives.length === 0) return <p>No server-authored evidence was provided.</p>;
  return <div className={styles.evidence}><ul>{evidence.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul>{alternatives.length > 0 && <><span className={styles.subhead}>Alternatives kept in view</span><ul>{alternatives.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul></>}</div>;
}

function findingState(finding: V6Finding | null): CombatExpressionState {
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

function signalsFor(finding: V6Finding | null): CombatSignal[] {
  const rows = finding?.comparison?.rows ?? [];
  const valueFor = (key: CombatSignal["key"]): string | number | null | undefined => {
    const rowKeys: Record<CombatSignal["key"], readonly string[]> = {
      involvement: ["involvement", "combat_involvement"],
      exposure: ["exposure", "death_exposure"],
    };
    const row = rows.find((item) => rowKeys[key].includes(item.key ?? ""));
    return row?.value ?? row?.estimate;
  };
  return [
    { key: "involvement", label: "Involvement", value: valueFor("involvement"), revealAt: 3 },
    { key: "exposure", label: "Exposure", value: valueFor("exposure"), revealAt: 4 },
  ];
}
