import type { V6DiagnosticQuestion, V6IdentitySummary } from "../../../types";
import { IdentityCard } from "../../cards/identity-card";
import styles from "../chapters.module.css";

export function PremiumChapter({
  identity,
  questions,
  phase,
  selectedQuestion,
  onSelectQuestion,
  onStart,
  loading = false,
}: {
  identity: V6IdentitySummary;
  questions: V6DiagnosticQuestion[];
  phase: number;
  selectedQuestion?: string;
  onSelectQuestion: (id: string) => void;
  onStart: () => void;
  loading?: boolean;
}) {
  const offered = questions.filter((question) => question.offered !== false && question.available !== false);
  const heading = identity.headline ?? identity.title ?? "There are deeper layers under this read.";
  const body = identity.body ?? "Deep can test one evidence-qualified thread against more match detail.";
  const previewSlots = [identity.slots?.primary, identity.slots?.twist, identity.slots?.anchor].filter((slot): slot is NonNullable<typeof slot> => Boolean(slot?.text));
  return (
    <section className={`${styles.chapter} ${styles.premiumChapter}`} data-phase={phase} aria-labelledby="story-premium-title">
      <div className={styles.chapterHeader}><span>Go deeper</span><span>10 / 11</span></div>
      <div className={styles.recededCard} data-receded={phase >= 1}><IdentityCard summary={identity} phase={8} /></div>
      {phase >= 1 && <div className={styles.hiddenLayers} aria-hidden="true">{Array.from({ length: 5 }, (_, index) => <i key={index} />)}</div>}
      {phase >= 2 && <><div className={styles.deepPreview} aria-label="Deep analysis preview">{(previewSlots.length > 0 ? previewSlots : [null, null, null]).map((slot, index) => <span key={slot?.kind ?? index} data-tone={index}>{slot?.text ?? "More signal"}</span>)}</div><h1 id="story-premium-title">{heading}</h1><p className={styles.body}>{body}</p></>}
      {phase >= 3 && offered.length > 0 && (
        <div className={styles.deepChoices}>
          <div className={styles.questionList} role="radiogroup" aria-label="Choose a Deep question">
          {offered.map((question, index) => {
            const id = question.question_id ?? question.id ?? `question-${index}`;
            return <button key={id} type="button" role="radio" aria-checked={selectedQuestion === id} onClick={() => onSelectQuestion(id)}>{question.label ?? question.question ?? "Deep question"}</button>;
          })}
          </div>
          <button type="button" className={styles.primaryAction} disabled={!selectedQuestion || loading} onClick={onStart}>{loading ? "Starting…" : "Explore with Deep"}</button>
        </div>
      )}
    </section>
  );
}
