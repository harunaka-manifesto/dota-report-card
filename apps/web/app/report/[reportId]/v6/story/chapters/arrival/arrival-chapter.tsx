/* eslint-disable @next/next/no-img-element -- Avatar URLs are server-owned and may not be configured for Next image optimization. */
import type { StoryModel } from "../../story-model";
import styles from "./arrival-chapter.module.css";

export type ArrivalElement = {
  key: string;
  label: string;
  status?: string | null;
};

export type ArrivalData = {
  displayName?: string | null;
  avatarUrl?: string | null;
  hoursPlayed?: number | null;
  heroCount?: number | null;
  openingStatement?: string | null;
  elements: readonly ArrivalElement[];
  dominantElements?: readonly ArrivalElement[];
};

export type ArrivalPhase = 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11;

/** Small adapter from the presentation model; absent values remain absent. */
export function createArrivalData(model: Pick<StoryModel, "player" | "identity" | "elements">): ArrivalData {
  const elements = model.elements.map((element) => ({ key: element.key, label: element.label, status: element.status }));
  return {
    displayName: model.player.display_name,
    avatarUrl: model.player.avatar_url,
    openingStatement: model.identity.headline ?? model.identity.body,
    elements,
    dominantElements: elements.filter((element) => element.status !== "suppressed" && element.status !== "unavailable").slice(0, 3),
  };
}

export function ArrivalChapter({ data, phase = 0, onAdvance }: { data: ArrivalData; phase?: ArrivalPhase; onAdvance?: () => void }) {
  const reveal = (at: ArrivalPhase) => phase === at;
  const dominant = data.dominantElements ?? [];
  return (
    <section className={styles.chapter} data-phase={phase} aria-label="Arrival">
      <div className={`${styles.state} ${reveal(0) ? styles.visible : ""}`} aria-hidden={!reveal(0)}>
        <span className={styles.eyebrow}>Analysis complete</span>
        <h1>We sequenced your Dota.</h1>
        <p>Your report is ready to recognize the shape in how you play.</p>
      </div>

      <div className={`${styles.state} ${styles.playerState} ${reveal(1) ? styles.visible : ""}`} aria-hidden={!reveal(1)}>
        <span className={styles.eyebrow}>Player identified</span>
        {data.avatarUrl && <img className={styles.avatar} src={data.avatarUrl} alt={data.displayName ? `Portrait of ${data.displayName}` : ""} />}
        <h2>{data.displayName || "Anonymous player"}</h2>
      </div>

      <div className={`${styles.state} ${reveal(2) ? styles.visible : ""}`} aria-hidden={!reveal(2)}>
        <span className={styles.eyebrow}>Opening statement</span>
        <p className={styles.statement}>{data.openingStatement || "Here’s what we found in the way you play."}</p>
      </div>

      <div className={`${styles.state} ${styles.scaleState} ${reveal(3) ? styles.visible : ""}`} aria-hidden={!reveal(3)}>
        <span className={styles.eyebrow}>A year of Dota</span>
        <h2>Scale gives the signal somewhere to land.</h2>
      </div>

      <div className={`${styles.state} ${styles.scaleState} ${reveal(4) ? styles.visible : ""}`} aria-hidden={!reveal(4)}>
        <span className={styles.eyebrow}>Hours added</span>
        <div className={styles.metrics}><Metric label="Hours added" value={data.hoursPlayed} /></div>
      </div>

      <div className={`${styles.state} ${styles.scaleState} ${reveal(5) ? styles.visible : ""}`} aria-hidden={!reveal(5)}>
        <span className={styles.eyebrow}>Hero count added</span>
        <div className={styles.metrics}><Metric label="Heroes added" value={data.heroCount} /></div>
      </div>

      <div className={`${styles.state} ${styles.explainState} ${reveal(6) ? styles.visible : ""}`} aria-hidden={!reveal(6)}>
        <span className={styles.eyebrow}>Raw history isn’t enough</span>
        <h2>The useful read is in the relationships.</h2>
        <p>Seven signals keep the report grounded in what the history can support.</p>
      </div>

      <div className={`${styles.state} ${styles.elementsState} ${phase >= 7 && phase <= 8 ? styles.visible : ""}`} aria-hidden={phase < 7 || phase > 8}>
        <span className={styles.eyebrow}>Seven elements</span>
        <div className={styles.elementSkeleton} aria-label="Seven signal positions">
          {data.elements.slice(0, 7).map((element, index) => <span key={element.key || index} className={styles.elementNode} style={{ "--node-index": index } as React.CSSProperties} />)}
        </div>
        <ul className={styles.elementLabels}>{data.elements.slice(0, 7).map((element) => <li key={element.key}>{phase >= 8 ? element.label : "Signal"}</li>)}</ul>
      </div>

      <div className={`${styles.state} ${styles.dominantState} ${reveal(9) ? styles.visible : ""}`} aria-hidden={!reveal(9)}>
        <span className={styles.eyebrow}>Dominant three</span>
        <div className={styles.dominantList}>{dominant.map((element) => <span key={element.key}>{element.label}</span>)}</div>
      </div>

      <div className={`${styles.state} ${styles.bridgeState} ${reveal(10) ? styles.visible : ""}`} aria-hidden={!reveal(10)}>
        <span className={styles.eyebrow}>Hero bridge</span>
        <p>Start with the heroes. Then we’ll look at what they reveal together.</p>
      </div>

      <div className={`${styles.state} ${styles.bridgeState} ${reveal(11) ? styles.visible : ""}`} aria-hidden={!reveal(11)}>
        <span className={styles.eyebrow}>Hero silhouette</span>
        <div className={styles.silhouette} aria-hidden="true" />
      </div>

      {onAdvance && <button className={styles.advance} type="button" onClick={onAdvance}>Continue <span aria-hidden="true">→</span></button>}
    </section>
  );
}

function Metric({ label, value }: { label: string; value?: number | null }) {
  return <div className={styles.metric}><strong>{typeof value === "number" ? value.toLocaleString() : "Not available"}</strong><span>{label}</span></div>;
}
