"use client";

/* eslint-disable @next/next/no-img-element -- avatars and share previews are dynamic server-owned URLs. */

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from "react";
import { track } from "../../../lib/analytics";
import {
  createInteractionSession,
  deleteInteractionSession,
  followUpInteractionSession,
  getInteractionSession,
  initialInteractionState,
  patchInteractionSession,
  readResumeFragment,
  resumeFragment,
  startDeepAnalysis,
  V6InteractionError,
  V6RevisionConflictError,
  withoutResumeFragment,
  type V6InteractionSession,
  type V6InteractionState,
} from "../../../../lib/v6/interaction-client";
import {
  displayConfidence,
  firstNonEmpty,
  metricFor,
  metricInterval,
  metricValue,
  reportBeats,
  type V6Choice,
  type V6ClaimLayers,
  type V6Comparison,
  type V6Finding,
  type V6HeroMirror,
  type V6HeroPortfolio,
  type V6HeroRow,
  type V6IdentitySummary,
  type V6Element,
  type V6Recommendation,
  type V6ShareCandidate,
  type V6StoryReport,
  type V6StoryBeat,
  type V6TimelinePoint,
} from "./types";
import { Glyph } from "../../../components/story/glyph-registry";
import styles from "./report-story-v6.module.css";

const BEAT_IDS = [
  "self-estimate",
  "identity-reveal",
  "pool-evolution",
  "combat-expression",
  "strongest-finding",
  "secondary-finding",
  "recommendation",
  "hero-mirror",
  "deep-diagnostic",
] as const;

type BeatId = (typeof BEAT_IDS)[number];
type SyncStatus = "idle" | "loading" | "saving" | "saved" | "resumed" | "deleted" | "conflict" | "error";
type ClaimLayer = "claim" | "evidence" | "interpretation" | "recommendation";
type FamilyState = "qualified" | "neutral" | "insufficient" | "mixed" | "unavailable";

const CLAIM_LAYERS: readonly ClaimLayer[] = ["claim", "evidence", "interpretation", "recommendation"];

/** Dedicated v6 renderer. The parent route can select it by schema_version. */
export default function ReportStoryV6({ report }: { report: V6StoryReport }) {
  const beats = useMemo(() => reportBeats(report), [report]);
  const [journey, setJourney] = useState<V6InteractionState>(() => initialInteractionState());
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("idle");
  const [syncMessage, setSyncMessage] = useState("");
  const [conflictSession, setConflictSession] = useState<V6InteractionSession | null>(null);
  const [followUpResult, setFollowUpResult] = useState<unknown>(null);
  const [deepResult, setDeepResult] = useState<unknown>(null);
  const [deepLoading, setDeepLoading] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const sessionRef = useRef<V6InteractionSession | null>(null);
  const tokenRef = useRef<string | null>(null);
  const dirtyRef = useRef(false);
  const pendingStateRef = useRef<V6InteractionState | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const persistRef = useRef<(state: V6InteractionState) => void>(() => undefined);

  const currentBeat = clampBeat(journey.current_beat);
  const currentBeatId = BEAT_IDS[currentBeat];
  const isV61 = report.schema_version === "free-dna-report-6.1.0";
  const publishedFindings = useMemo(() => report.findings.filter(isPublished), [report.findings]);
  const poolFinding = useMemo(() => findFamily(report.findings, "pool_shape"), [report.findings]);
  const transferFinding = useMemo(() => findFamily(report.findings, "transfer"), [report.findings]);
  const lossFinding = useMemo(() => findFamily(report.findings, "post_loss"), [report.findings]);
  const combatFinding = useMemo(() => findFamily(report.findings, "combat"), [report.findings]);
  const sessionFinding = useMemo(() => findFamily(report.findings, "session"), [report.findings]);
  const timeline = useMemo(() => {
    const evolution = report.hero_portfolio.evolution;
    return evolution?.points ?? evolution?.timeline ?? report.hero_portfolio.timeline ?? [];
  }, [report.hero_portfolio]);
  const mirror = report.hero_portfolio.mirror ?? report.hero_portfolio.hero_mirror ?? null;
  const recommendations = useMemo(() => recommendationChoices(report, ...publishedFindings), [report, publishedFindings]);
  const selectedTimelineIndex = clampTimelineIndex(journey.ui_state.pool_evolution_position, timeline.length);
  const supportingEvidence = "supporting_evidence" in report ? report.supporting_evidence : undefined;

  const schedulePersist = useCallback((state: V6InteractionState) => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => {
      persistRef.current(state);
    }, 350);
  }, []);

  const updateJourney = useCallback((update: (state: V6InteractionState) => V6InteractionState) => {
    setJourney((previous) => {
      const next = update(previous);
      dirtyRef.current = true;
      pendingStateRef.current = next;
      return next;
    });
  }, []);

  const persist = useCallback(async (state: V6InteractionState) => {
    if (!dirtyRef.current) return;
    const existing = sessionRef.current;
    const token = tokenRef.current;
    setSyncStatus("saving");
    setSyncMessage("");
    try {
      if (existing && token) {
        const updated = await patchInteractionSession(existing.session_id, token, state, existing.revision);
        sessionRef.current = updated;
        setJourney(updated.state);
      } else {
        const created = await createInteractionSession(report.report_id ?? "", state);
        sessionRef.current = created.session;
        tokenRef.current = created.token;
        if (typeof window !== "undefined") {
          // The fragment is never sent in fetch(), analytics, or server logs.
          window.history.replaceState(null, document.title, `${window.location.pathname}${window.location.search}${resumeFragment(created.session.session_id, created.token)}`);
        }
        setJourney(created.session.state);
      }
      dirtyRef.current = false;
      setConflictSession(null);
      setSyncStatus("saved");
      setSyncMessage("Journey saved. You can resume it from this link.");
    } catch (error) {
      if (error instanceof V6RevisionConflictError) {
        let latest = error.latest;
        if (!latest && existing && token) {
          latest = await getInteractionSession(existing.session_id, token).catch(() => null);
        }
        if (latest) sessionRef.current = latest;
        setConflictSession(latest ?? existing);
        setSyncStatus("conflict");
        setSyncMessage("This journey changed in another tab. Choose which version to keep.");
      } else {
        setSyncStatus("error");
        setSyncMessage(error instanceof V6InteractionError ? error.message : "The journey could not be saved. You can keep playing and retry.");
      }
    }
  }, [report.report_id]);

  persistRef.current = (state) => {
    void persist(state);
  };

  useEffect(() => {
    const pending = pendingStateRef.current;
    if (!pending) return;
    pendingStateRef.current = null;
    schedulePersist(pending);
  }, [journey, schedulePersist]);

  useEffect(() => {
    const resume = readResumeFragment();
    if (!resume) return;
    tokenRef.current = resume.token;
    setSyncStatus("loading");
    void getInteractionSession(resume.sessionId, resume.token)
      .then((session) => {
        sessionRef.current = session;
        setJourney(normalizeInteractionState(session.state));
        dirtyRef.current = false;
        setSyncStatus("resumed");
        setSyncMessage("Saved journey resumed.");
      })
      .catch((error: unknown) => {
        tokenRef.current = null;
        setSyncStatus("error");
        setSyncMessage(error instanceof V6InteractionError && error.status === 404 ? "This saved journey has expired." : "The saved journey could not be resumed.");
      });
  }, []);

  useEffect(() => {
    document.documentElement.dataset.reportStoryV6 = "true";
    return () => {
      delete document.documentElement.dataset.reportStoryV6;
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    };
  }, []);

  function moveToBeat(index: number): void {
    const nextIndex = clampBeat(index);
    updateJourney((state) => ({ ...state, current_beat: nextIndex }));
    scrollToBeat(BEAT_IDS[nextIndex]);
    track("report.v6.beat_navigated.v1", { beat: BEAT_IDS[nextIndex], source: "visible_control" });
  }

  function finishBeat(index: number, next = index + 1): void {
    const nextIndex = clampBeat(next);
    updateJourney((state) => ({
      ...state,
      current_beat: nextIndex,
      completed_beats: uniqueNumbers([...state.completed_beats, index]).filter((item) => !state.skipped_beats.includes(item)),
      skipped_beats: state.skipped_beats.filter((item) => item !== index),
    }));
    if (next > index) scrollToBeat(BEAT_IDS[nextIndex]);
  }

  function skipBeat(index: number): void {
    updateJourney((state) => ({
      ...state,
      current_beat: clampBeat(index + 1),
      skipped_beats: uniqueNumbers([...state.skipped_beats, index]),
      completed_beats: state.completed_beats.filter((item) => item !== index),
    }));
    track("report.v6.beat_skipped.v1", { beat: BEAT_IDS[index] });
    if (index < BEAT_IDS.length - 1) scrollToBeat(BEAT_IDS[index + 1]);
  }

  function chooseUserAnswer(field: "identity_estimate" | "hero_pool_prediction" | "combat_expression_estimate", choice: V6Choice): void {
    const value = choice.id ?? choice.key ?? choice.value ?? choice.label;
    updateJourney((state) => ({ ...state, user_reported: { ...state.user_reported, [field]: value } }));
    // Keep analytics shape identity-safe; the selected server key remains in
    // the token-protected interaction state, not in the event payload.
    track("report.v6.user_reported_selected.v1", { field, selected: true });
  }

  function revealObserved(field: "identity_revealed" | "combat_expression_revealed", nextBeat: number): void {
    updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, [field]: true } }));
    track("report.v6.observed_reveal.v1", { field });
    finishBeat(nextBeat - 1, nextBeat);
  }

  function setTimeline(index: number): void {
    updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, pool_evolution_position: index } }));
    track("report.v6.timeline_scrubbed.v1", { beat: "pool-evolution" });
  }

  function setClaimLayer(layer: ClaimLayer): void {
    updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, claim_layer: layer } }));
  }

  async function saveJourney(): Promise<void> {
    dirtyRef.current = true;
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    await persist(journey);
  }

  async function deleteJourney(): Promise<void> {
    const session = sessionRef.current;
    const token = tokenRef.current;
    if (session && token) {
      try {
        await deleteInteractionSession(session.session_id, token);
      } catch {
        setSyncStatus("error");
        setSyncMessage("The saved journey could not be deleted. Try again.");
        return;
      }
    }
    sessionRef.current = null;
    tokenRef.current = null;
    dirtyRef.current = false;
    withoutResumeFragment();
    setJourney(initialInteractionState());
    setSyncStatus("deleted");
    setSyncMessage("Saved journey deleted from this device.");
  }

  function useServerVersion(): void {
    if (!conflictSession) return;
    sessionRef.current = conflictSession;
    setJourney(conflictSession.state);
    dirtyRef.current = false;
    setConflictSession(null);
    setSyncStatus("saved");
    setSyncMessage("Loaded the latest saved journey.");
  }

  function keepLocalVersion(): void {
    if (!conflictSession) return;
    sessionRef.current = conflictSession;
    setConflictSession(null);
    dirtyRef.current = true;
    setSyncMessage("Your local version is ready to save over the latest version.");
    schedulePersist(journey);
  }

  function selectRecommendation(id: string): void {
    updateJourney((state) => ({ ...state, user_reported: { ...state.user_reported, recommendation_id: id } }));
    track("report.v6.recommendation_selected.v1", { has_selection: true });
  }

  async function commitRecommendation(): Promise<void> {
    const recommendationId = journey.user_reported.recommendation_id;
    if (!recommendationId) return;
    const committedState: V6InteractionState = {
      ...journey,
      user_reported: {
        ...journey.user_reported,
        commitment: { recommendation_id: recommendationId, target_games: 5, started_at: new Date().toISOString() },
      },
    };
    dirtyRef.current = true;
    pendingStateRef.current = null;
    setJourney(committedState);
    track("report.v6.five_game_commitment.v1", { target_games: 5 });
    await persist(committedState);
  }

  async function checkFollowUp(): Promise<void> {
    const session = sessionRef.current;
    const token = tokenRef.current;
    if (!session || !token) {
      setSyncMessage("Save this journey before checking five-game progress.");
      return;
    }
    setSyncStatus("saving");
    try {
      const result = await followUpInteractionSession(session.session_id, token);
      setFollowUpResult(result);
      updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, follow_up: followUpState(result) } }));
      setSyncStatus("saved");
      setSyncMessage("Five-game progress updated from the server.");
    } catch (error) {
      setSyncStatus("error");
      setSyncMessage(error instanceof V6InteractionError ? error.message : "Five-game progress is not available yet.");
    }
  }

  async function chooseDiagnostic(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    const questionId = journey.ui_state.diagnostic_question_id;
    if (!questionId) return;
    setDeepLoading(true);
    setDeepResult(null);
    try {
      const result = await startDeepAnalysis(report.report_id ?? "", questionId, sessionRef.current?.session_id, tokenRef.current);
      setDeepResult(result);
      setSyncMessage("Your diagnostic question was sent to Deep.");
      updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, diagnostic_question_id: questionId } }));
      track("report.v6.deep_question_submitted.v1", { selected: true });
    } catch (error) {
      setSyncMessage(error instanceof V6InteractionError ? error.message : "Deep could not start this diagnostic yet.");
    } finally {
      setDeepLoading(false);
    }
  }

  function chooseDiagnosticQuestion(id: string): void {
    updateJourney((state) => ({
      ...state,
      ui_state: { ...state.ui_state, diagnostic_question_id: id },
    }));
  }

  async function copyShareCandidate(candidate: V6ShareCandidate): Promise<void> {
    const text = [candidate.title, candidate.headline, candidate.body].filter(Boolean).join("\n\n");
    if (!text || typeof navigator === "undefined" || !navigator.clipboard) return;
    await navigator.clipboard.writeText(text);
    setShareCopied(true);
    setTimeout(() => setShareCopied(false), 2200);
  }

  return (
    <main className={styles.story} aria-label={`Free DNA ${report.schema_version === "free-dna-report-6.1.0" ? "V6.1" : "V6"} identity report`}>
      <header className={styles.topbar}>
        <a className={styles.wordmark} href="#v6-beat-1">FREE DNA <span>{isV61 ? "6.1" : "06"}</span></a>
        <p className={styles.topline}>{isV61 ? "Your Dota, seen as a shape." : "Summary-only identity report"}</p>
        <div className={styles.sessionActions}>
          <span className={styles.syncStatus} role="status" aria-live="polite">{syncMessage || syncLabel(syncStatus)}</span>
          <button className={styles.textButton} type="button" onClick={() => void saveJourney()}>{sessionRef.current ? "Save now" : "Save journey"}</button>
          {sessionRef.current && <button className={styles.textButton} type="button" onClick={() => void deleteJourney()}>Delete saved journey</button>}
        </div>
      </header>

      {syncStatus === "conflict" && conflictSession && (
        <aside className={styles.conflict} role="alert">
          <strong>This saved journey has a newer version.</strong>
          <span>Choose whether to load it or save your local progress over it.</span>
          <div className={styles.inlineActions}>
            <button className={styles.secondaryButton} type="button" onClick={useServerVersion}>Load latest</button>
            <button className={styles.primaryButton} type="button" onClick={keepLocalVersion}>Keep my version</button>
          </div>
        </aside>
      )}

      <div className={styles.layout}>
        <aside className={styles.rail} aria-label="Report chapters">
          <div className={styles.railIntro}><span>V6</span><small>YOUR<br />SHAPE</small></div>
          <nav>
            {BEAT_IDS.map((id, index) => (
              <button key={id} className={currentBeat === index ? styles.railButtonActive : styles.railButton} type="button" aria-current={currentBeat === index ? "step" : undefined} onClick={() => moveToBeat(index)}>
                <span className={styles.railNumber}>{String(index + 1).padStart(2, "0")}</span>
                <span>{beatLabel(id)}</span>
              </button>
            ))}
          </nav>
          <p className={styles.railNote}>All chapters are optional.<br />Your reflections never<br />change the evidence.</p>
        </aside>

        <div className={styles.content}>
          <div className={styles.progressHeader}>
            <span>Beat {currentBeat + 1} of 9</span>
            <progress value={progressCount(journey)} max={9} aria-label="Story progress" />
            <span>{progressCount(journey)}/9 complete</span>
          </div>

          <section id="v6-beat-1" className={`${styles.beat} ${styles.beatEstimate}`} aria-labelledby="v6-beat-1-title">
            <BeatHeader number={1} id="self-estimate" beat={undefined} fallbackTitle="We sequenced your Dota." fallbackBody="Here’s what we found in the way you play." preferFallback={isV61} onSkip={() => skipBeat(0)} />
            <ChoiceQuestion
              legend="Before you look closer, which description feels most familiar?"
              choices={beats[0]?.options ?? report.identity_summary.options ?? []}
              selected={journey.user_reported.identity_estimate}
              onSelect={(choice) => chooseUserAnswer("identity_estimate", choice)}
              emptyMessage="This optional recognition prompt was not offered. Continue to the observed report."
            />
            <p className={styles.choiceBoundary}>Your answer is saved as your own reflection. It never changes the observed report.</p>
            <div className={styles.beatActions}>
              <button className={styles.primaryButton} type="button" onClick={() => finishBeat(0)}>Reveal your shape <span aria-hidden="true">→</span></button>
              <button className={styles.linkButton} type="button" onClick={() => skipBeat(0)}>Skip this beat</button>
            </div>
          </section>

          <section id="v6-beat-2" className={`${styles.beat} ${styles.beatIdentity}`} aria-labelledby="v6-beat-2-title">
            <BeatHeader number={2} id="identity-reveal" beat={undefined} fallbackTitle="Yep. This is you." fallbackBody="Your year is ready to recognize." preferFallback={isV61} onSkip={() => skipBeat(1)} />
            <div className={styles.identityReveal}>
              {journey.ui_state.identity_revealed ? (
                <>
                  <ProfileSpecimen identity={report.identity} />
                  <p className={styles.revealLabel}>Observed identity summary</p>
                  <h2 id="v6-identity-headline" className={styles.revealHeadline}>{identityStoryHeadline(report.identity_summary)}</h2>
                  {identityStoryState(report.identity_summary) === "qualified" && report.identity_summary.headline && <p className={styles.storyCue}>{report.identity_summary.headline}</p>}
                  <ul className={styles.supportList}>{(report.identity_summary.supporting_lines ?? report.identity_summary.support ?? []).map((line) => <li key={line}>{line}</li>)}</ul>
                  <ElementTeaser elements={report.elements} />
                  <details className={styles.disclosure}><summary>Evidence · all seven Elements</summary><div className={styles.disclosureBody}><ElementLedger elements={report.elements} /></div></details>
                </>
              ) : (
                <div className={styles.lockedReveal}>
                  <span aria-hidden="true">◇</span>
                  <p>Your reflection stays separate from this server-authored result.</p>
                  <button className={styles.primaryButton} type="button" onClick={() => revealObserved("identity_revealed", 2)}>Reveal observed shape</button>
                </div>
              )}
            </div>
            <BeatFooter index={1} onNext={() => finishBeat(1)} onSkip={() => skipBeat(1)} disabled={!journey.ui_state.identity_revealed} />
          </section>

          <section id="v6-beat-3" className={`${styles.beat} ${styles.beatPool}`} aria-labelledby="v6-beat-3-title">
            <BeatHeader number={3} id="pool-evolution" beat={undefined} fallbackTitle="Before the patterns, there are the heroes." fallbackBody="If we had to start with one hero…" preferFallback={isV61} onSkip={() => skipBeat(2)} />
            <HeroPool portfolio={report.hero_portfolio} timeline={timeline} selectedIndex={selectedTimelineIndex} onSelect={setTimeline} supportingEvidence={supportingEvidence} />
            <FamilyStory family="Pool Shape" question="Do your heroes solve the same job—or different ones?" finding={poolFinding} supportingEvidence={supportingEvidence} />
            <BeatFooter index={2} onNext={() => finishBeat(2)} onSkip={() => skipBeat(2)} />
          </section>

          <section id="v6-beat-4" className={`${styles.beat} ${styles.beatCombat}`} aria-labelledby="v6-beat-4-title">
            <BeatHeader number={4} id="combat-expression" beat={undefined} fallbackTitle="What survives when the hero changes?" fallbackBody="The comparison stays inside the supported hero boundary." preferFallback={isV61} onSkip={() => skipBeat(3)} />
            <FamilyStory family="Transfer" question="What survives when the hero changes?" finding={transferFinding} supportingEvidence={supportingEvidence} />
            <BeatFooter index={3} onNext={() => finishBeat(3)} onSkip={() => skipBeat(3)} />
          </section>

          <section id="v6-beat-5" className={`${styles.beat} ${styles.beatFinding}`} aria-labelledby="v6-beat-5-title">
            <BeatHeader number={5} id="strongest-finding" beat={undefined} fallbackTitle="What does your Dota look like after a loss?" fallbackBody="The next choice is shown only inside the supported same-session comparison." preferFallback={isV61} onSkip={() => skipBeat(4)} />
            <FamilyStory family="Post-loss Response" question="What does your Dota look like after a loss?" finding={lossFinding} supportingEvidence={supportingEvidence} />
            <BeatFooter index={4} onNext={() => finishBeat(4)} onSkip={() => skipBeat(4)} />
          </section>

          <section id="v6-beat-6" className={`${styles.beat} ${styles.beatLayers}`} aria-labelledby="v6-beat-6-title">
            <BeatHeader number={6} id="secondary-finding" beat={undefined} fallbackTitle="Once the horn sounds, what keeps showing up?" fallbackBody="Involvement and exposure stay as separate observed signals." preferFallback={isV61} onSkip={() => skipBeat(5)} />
            <FamilyStory family="Combat Expression" question="Once the horn sounds, what keeps showing up?" finding={combatFinding} supportingEvidence={supportingEvidence} />
            <BeatFooter index={5} onNext={() => finishBeat(5)} onSkip={() => skipBeat(5)} />
          </section>

          <section id="v6-beat-7" className={`${styles.beat} ${styles.beatAction}`} aria-labelledby="v6-beat-7-title">
            <BeatHeader number={7} id="recommendation" beat={undefined} fallbackTitle="One match shows expression. A session shows whether it holds." fallbackBody="Completed session positions keep the time boundary visible." preferFallback={isV61} onSkip={() => skipBeat(6)} />
            <FamilyStory family="Session Drift" question="One match shows expression. A session shows whether it holds." finding={sessionFinding} supportingEvidence={supportingEvidence} />
            <BeatFooter index={6} onNext={() => finishBeat(6)} onSkip={() => skipBeat(6)} />
          </section>

          <section id="v6-beat-8" className={`${styles.beat} ${styles.beatMirror}`} aria-labelledby="v6-beat-8-title">
            <BeatHeader number={8} id="hero-mirror" beat={undefined} fallbackTitle="None of these patterns lives alone." fallbackBody="They keep resolving into the same underlying shape." preferFallback={isV61} onSkip={() => skipBeat(7)} />
            <SignatureCard report={report} />
            <HeroMirrorCard mirror={mirror} revealed={Boolean(journey.ui_state.hero_mirror_revealed)} onReveal={() => updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, hero_mirror_revealed: true } }))} />
            <BeatFooter index={7} onNext={() => finishBeat(7)} onSkip={() => skipBeat(7)} />
          </section>

          <section id="v6-beat-9" className={`${styles.beat} ${styles.beatDeep}`} aria-labelledby="v6-beat-9-title">
            <BeatHeader number={9} id="deep-diagnostic" beat={undefined} fallbackTitle="Your Dota DNA, in pieces." fallbackBody="Choose the part that feels most like you." preferFallback={isV61} onSkip={() => skipBeat(8)} />
            <ShareComposer report={report} selected={journey.ui_state.selected_share_candidate} onSelect={(id) => updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, selected_share_candidate: id } }))} onCopy={(candidate) => void copyShareCandidate(candidate)} copied={shareCopied} />
            {recommendations.length > 0 && <section className={styles.aftercare} aria-label="Next experiment">
              <span className={styles.eyebrow}>Try this next</span>
              <RecommendationChooser recommendations={recommendations} selected={journey.user_reported.recommendation_id} onSelect={selectRecommendation} committed={Boolean(journey.user_reported.commitment)} onCommit={() => void commitRecommendation()} />
              {journey.user_reported.commitment && <FollowUpCard result={followUpResult} uiState={journey.ui_state.follow_up} onCheck={() => void checkFollowUp()} />}
            </section>}
            <form className={styles.deepForm} onSubmit={(event) => void chooseDiagnostic(event)}>
              <fieldset>
                <legend className={styles.questionLegend}>Which thread should Deep test?</legend>
                <div className={styles.questionList}>
                  {report.diagnostic_questions.filter(questionIsOffered).map((question) => {
                    const id = diagnosticQuestionId(question);
                    const selected = journey.ui_state.diagnostic_question_id === id;
                    return <label className={selected ? styles.questionOptionSelected : styles.questionOption} key={id}><input type="radio" name="v6-diagnostic" checked={selected} onChange={() => chooseDiagnosticQuestion(id)} /><span><strong>{firstNonEmpty(question.label, question.family, question.finding_family, "Deep question")}</strong><small>{firstNonEmpty(question.question, question.prompt, question.body, question.context, "")}</small></span></label>;
                  })}
                </div>
              </fieldset>
              {report.diagnostic_questions.filter(questionIsOffered).length === 0 && <EmptyState message="No evidence-qualified Deep question was offered for this report." />}
              <div className={styles.beatActions}>
                <button className={styles.primaryButton} type="submit" disabled={!journey.ui_state.diagnostic_question_id || deepLoading}>{deepLoading ? "Starting…" : "Send to Deep →"}</button>
                <button className={styles.linkButton} type="button" onClick={() => skipBeat(8)}>Skip Deep</button>
              </div>
              {deepResult !== null && deepResult !== undefined ? <ResultNotice result={deepResult} /> : null}
            </form>
            <section className={styles.methodology} aria-label="Methodology and cost">
              <span className={styles.eyebrow}>Free boundary</span>
              <p>{firstNonEmpty(...(report.methodology?.notes ?? []), "Summary-only evidence. Detail reads and parses are not used in Free.")}</p>
              <dl><div><dt>Detail reads</dt><dd>{report.cost?.detail_requests ?? 0}</dd></div><div><dt>Parses</dt><dd>{report.cost?.parse_requests ?? 0}</dd></div></dl>
            </section>
          </section>
        </div>
      </div>
    </main>
  );
}

function BeatHeader({ number, id, beat, fallbackTitle, fallbackBody, preferFallback = false, onSkip }: { number: number; id: BeatId; beat?: V6StoryBeat; fallbackTitle: string; fallbackBody: string; preferFallback?: boolean; onSkip: () => void }) {
  const title = preferFallback ? fallbackTitle : firstNonEmpty(storyCopy(beat, "title"), fallbackTitle);
  const body = preferFallback ? fallbackBody : firstNonEmpty(storyCopy(beat, "body"), storyCopy(beat, "prompt"), fallbackBody);
  return <header className={styles.beatHeader}><div className={styles.beatKicker}><span>{String(number).padStart(2, "0")}</span><span>{firstNonEmpty(beat?.eyebrow, storyCopy(beat, "eyebrow"), beatLabel(id))}</span><button className={styles.skipButton} type="button" onClick={onSkip}>Skip beat</button></div><h1 id={`v6-beat-${number}-title`}>{title}</h1><p>{body}</p></header>;
}

function BeatFooter({ index, onNext, onSkip, disabled }: { index: number; onNext: () => void; onSkip: () => void; disabled?: boolean }) {
  return <div className={styles.beatFooter}><button className={styles.primaryButton} type="button" disabled={disabled} onClick={onNext}>{index === 8 ? "Finish report" : "Continue"} <span aria-hidden="true">→</span></button><button className={styles.linkButton} type="button" onClick={onSkip}>Skip this beat</button></div>;
}

function ChoiceQuestion({ legend, choices, selected, onSelect, emptyMessage }: { legend: string; choices: V6Choice[]; selected?: string; onSelect: (choice: V6Choice) => void; emptyMessage: string }) {
  return <fieldset className={styles.choiceFieldset}><legend>{legend}</legend>{choices.length === 0 ? <EmptyState message={emptyMessage} /> : <div className={styles.choiceList}>{choices.map((choice) => { const value = choice.id ?? choice.key ?? choice.value ?? choice.label; const checked = selected === value; return <label key={value} className={checked ? styles.choiceSelected : styles.choice}><input type="radio" name={`choice-${legend}`} value={value} checked={checked} onChange={() => onSelect(choice)} /><span><strong>{choice.label}</strong>{choice.description && <small>{choice.description}</small>}</span></label>; })}</div>}</fieldset>;
}

function ProfileSpecimen({ identity }: { identity: V6StoryReport["identity"] }) {
  if (!identity.display_name && !identity.avatar_url) return null;
  return <div className={styles.profileSpecimen} aria-label={identity.display_name ? `Report for ${identity.display_name}` : "Report profile"}>{identity.avatar_url && <img className={styles.profileAvatar} src={identity.avatar_url} alt={identity.display_name ? `Portrait of ${identity.display_name}` : ""} />}{identity.display_name && <strong className={styles.profileName}>{identity.display_name}</strong>}</div>;
}

function identityStoryState(summary: V6IdentitySummary): FamilyState {
  const state = `${summary.status ?? ""} ${summary.state ?? ""}`.toLowerCase();
  if (state.includes("insufficient") || state.includes("limited")) return "insufficient";
  if (state.includes("mixed")) return "mixed";
  if (state.includes("neutral")) return "neutral";
  if (state.includes("unavailable") || state.includes("suppressed")) return "unavailable";
  return summary.slots?.primary?.text || summary.headline ? "qualified" : "neutral";
}

function identityStoryHeadline(summary: V6IdentitySummary): string {
  switch (identityStoryState(summary)) {
    case "neutral": return "No single finding owns the headline yet. Your Elements are the shape we can describe.";
    case "insufficient": return "Your identity is still forming from this sample.";
    case "mixed": return "Your shape has more than one side. The slots below keep them separate.";
    case "unavailable": return "Not available";
    default: return "Yep. This is you.";
  }
}

function displayElementState(status?: string | null): string {
  return humanize(status || "available");
}

function humanHeroLabel(value: string): string {
  const label = value.trim();
  return /^(?:stable core:\s*)?\d+(?:\s*,\s*\d+)*$/i.test(label) ? "" : label;
}

function signatureState(report: V6StoryReport, slotCount: number): FamilyState {
  const state = `${report.identity_summary.status ?? ""} ${report.identity_summary.state ?? ""}`.toLowerCase();
  if (state.includes("insufficient") || state.includes("limited")) return "insufficient";
  if (state.includes("mixed")) return "mixed";
  if (state.includes("unavailable")) return "unavailable";
  if (slotCount > 0) return "qualified";
  return report.elements.some((element) => !["suppressed", "unavailable"].includes(element.status ?? "available")) ? "neutral" : "insufficient";
}

function signatureStateCopy(state: FamilyState): string {
  if (state === "neutral") return "Your Dota Signature is still taking shape.";
  if (state === "insufficient") return "There is not enough stable evidence to name a Signature yet.";
  if (state === "mixed") return "Your Signature has a clear core and a context-dependent twist.";
  return "Not available";
}

function ElementTeaser({ elements }: { elements: V6Element[] }) {
  const available = elements.filter((element) => !["suppressed", "unavailable"].includes(element.status ?? "available"));
  if (available.length === 0) return <StateCard state="unavailable" title="Elements unavailable" body="No identity Element was available for this report." />;
  return <section className={styles.elementTeaser} aria-labelledby="v6-element-teaser-title"><p id="v6-element-teaser-title" className={styles.eyebrow}>Seven signals kept showing up.</p><p className={styles.storyCue}>Start with the strongest 2–3 available signals.</p><ul>{available.slice(0, 3).map((element) => <li key={element.key}><Glyph decorative glyph={elementGlyphKey(element.key)} size={25} /><span>{element.label}</span><small>{displayElementState(element.status)}</small></li>)}</ul></section>;
}

function HeroPool({ portfolio, timeline, selectedIndex, onSelect, supportingEvidence }: { portfolio: V6HeroPortfolio; timeline: V6TimelinePoint[]; selectedIndex: number; onSelect: (index: number) => void; supportingEvidence?: Record<string, Record<string, unknown> | undefined> }) {
  const heroes = (portfolio.heroes ?? []).filter((hero) => heroName(hero));
  const shape = asRecord(supportingEvidence?.portfolio_shape);
  const width = firstNonEmpty(recordText(shape, "pool_width"), recordText(shape, "width"));
  return <section className={styles.poolField} aria-label="Observed hero pool">
    <p className={styles.storyCue}>One hero doesn’t describe your Dota.<br />There’s a difference between a hero you’ve played…<br />…and a hero that actually belongs to your Dota.</p>
    <h2 className={styles.poolHeading}>Here’s who lives where.</h2>
    {width === "narrow" && <p className={styles.poolBoundary}>Narrow pool: fewer heroes, larger samples keep the field readable.</p>}
    {width === "broad" && <p className={styles.poolBoundary}>Broad pool: aggregation keeps the field readable.</p>}
    {heroes.length > 0 && <table className={styles.heroTable}><caption>Observed hero pool</caption><thead><tr><th scope="col">Hero</th><th scope="col">Matches</th><th scope="col">Pool share</th><th scope="col">Mapped jobs</th></tr></thead><tbody>{heroes.map((hero, index) => <HeroRowCard hero={hero} key={`${heroName(hero)}-${index}`} />)}</tbody></table>}
    {timeline.length > 0 && <TimelineScrubber points={timeline} selectedIndex={selectedIndex} onSelect={onSelect} />}
    {heroes.length === 0 && timeline.length === 0 && <StateCard state="insufficient" title="Not enough usable hero history to map the pool." body="The report did not include a human-labeled hero row or a chronological field." />}
  </section>;
}

function HeroRowCard({ hero }: { hero: V6HeroRow }) {
  const jobs = hero.functional_jobs ?? hero.jobs ?? [];
  return <tr><th scope="row">{heroName(hero)}{hero.band && <small>{humanize(hero.band)}</small>}</th><td>{typeof hero.match_count === "number" ? hero.match_count : "Not available"}</td><td>{typeof hero.share === "number" ? formatMetric(hero.share, "share") : "Not available"}</td><td>{jobs.length > 0 ? jobs.join(" · ") : "Not available"}</td></tr>;
}

function FamilyStory({ family, question, finding, supportingEvidence }: { family: string; question: string; finding: V6Finding | null; supportingEvidence?: Record<string, Record<string, unknown> | undefined> }) {
  const state = findingState(finding);
  if (!finding || state !== "qualified") return <article className={styles.stateCard} data-state={state} aria-label={`${family} ${stateLabel(state)}`}><span className={styles.familyState}>{stateLabel(state)}</span><h2>{question}</h2><p>{familyStateCopy(family, state, finding)}</p>{state === "mixed" && <details className={styles.disclosure}><summary>Show the comparison</summary><div className={styles.disclosureBody}><RelationshipEvidence finding={finding as V6Finding} supportingEvidence={supportingEvidence} />{finding?.comparison && <Comparison comparison={finding.comparison} label="Supported comparison" />}</div></details>}{finding && <><details className={styles.disclosure}><summary>Why this?</summary><div className={styles.disclosureBody}><p>{firstNonEmpty(findingEvidenceText(finding), "The supported range remains available in the evidence layer.")}</p></div></details><details className={styles.disclosure}><summary>How we measured this</summary><div className={styles.disclosureBody}><MetricReceipt item={finding} />{(finding.limitations ?? []).slice(0, 1).map((item) => <p className={styles.limitation} key={item}>{item}</p>)}</div></details></>}</article>;
  const layers = findingLayers(finding);
  return <article className={styles.familyCard} data-state={state}>
    <span className={styles.familyState}>Qualified finding</span>
    <h2>{firstNonEmpty(finding.claim, layers.claim, finding.title, finding.label, `${family} finding`)}</h2>
    <p>{firstNonEmpty(finding.interpretation, layers.interpretation, finding.observation, "This relationship is descriptive and bounded by the available evidence.")}</p>
    <details className={styles.disclosure}><summary>Why this?</summary><div className={styles.disclosureBody}><p>{firstNonEmpty(findingEvidenceText(finding), layers.evidence, "The supporting aggregates are available below.")}</p></div></details>
    <details className={styles.disclosure}><summary>See what changed</summary><div className={styles.disclosureBody}><RelationshipEvidence finding={finding} supportingEvidence={supportingEvidence} /></div></details>
    <details className={styles.disclosure}><summary>Show the comparison</summary><div className={styles.disclosureBody}>{finding.comparison ? <Comparison comparison={finding.comparison} label="Supported comparison" /> : <p>The supported components remain in the evidence contract above.</p>}</div></details>
    <details className={styles.disclosure}><summary>How we measured this</summary><div className={styles.disclosureBody}><MetricReceipt item={finding} />{(finding.limitations ?? []).map((item) => <p className={styles.limitation} key={item}>{item}</p>)}</div></details>
  </article>;
}

function StateCard({ state, title, body }: { state: FamilyState; title: string; body: string }) {
  return <article className={styles.stateCard} data-state={state} role="status"><span className={styles.familyState}>{stateLabel(state)}</span><h2>{title}</h2><p>{body}</p></article>;
}

function SignatureCard({ report }: { report: V6StoryReport }) {
  const summary = report.identity_summary;
  const slots = [summary.slots?.primary, summary.slots?.twist, summary.slots?.anchor].filter((slot): slot is NonNullable<typeof slot> => Boolean(slot?.text && (slot.kind !== "ANCHOR" || humanHeroLabel(slot.text))));
  const state = signatureState(report, slots.length);
  if (state !== "qualified") return <article className={styles.stateCard} data-state={state} aria-label={`Signature ${stateLabel(state)}`}><span className={styles.familyState}>{stateLabel(state)}</span><h2>Your Dota Signature.</h2><p>{signatureStateCopy(state)}</p><details className={styles.disclosure}><summary>Why this describes your Dota.</summary><div className={styles.disclosureBody}><p>Only the server-supplied Signature slots and public evidence can open this layer.</p></div></details></article>;
  return <article className={styles.signature} aria-label="Your Dota Signature"><p className={styles.signatureStrip}>YOUR DOTA SIGNATURE</p><h2>Your Dota Signature.</h2><div className={styles.signatureGrid}>{slots.map((slot) => <section className={styles.signatureSlot} key={`${slot.kind}-${slot.scope}`}><span>{slot.kind}</span>{slot.scope && <small>{slot.scope}</small>}<h3>{slot.text}</h3><p>{slot.evidence_refs?.length ?? 0} supporting source{slot.evidence_refs?.length === 1 ? "" : "s"}</p></section>)}</div><details className={styles.disclosure}><summary>Why this describes your Dota.</summary><div className={styles.disclosureBody}><ul className={styles.signatureEvidence}>{slots.map((slot) => <li key={`${slot.kind}-evidence`}><strong>{slot.kind === "PRIMARY" ? "Signals" : slot.kind === "TWIST" ? "Twist" : "Anchor"}</strong><span>{slot.scope ?? "Observed source"} · {slot.evidence_refs?.length ?? 0} evidence source{slot.evidence_refs?.length === 1 ? "" : "s"}</span></li>)}</ul></div></details><p className={styles.signatureBoundary}>Slots that were not supplied are omitted; this synthesis does not fill gaps client-side.</p></article>;
}

function ElementLedger({ elements }: { elements: V6Element[] }) {
  if (elements.length === 0) return <EmptyState message="The report did not publish its seven identity Elements." />;
  return <section className={styles.elementLedger} aria-label="Seven public identity Elements"><div className={styles.elementLedgerHeader}><span className={styles.eyebrow}>Seven public Elements</span><p>Observed summary signals stay distinct from your self-reported answers.</p></div><div className={styles.elementGrid}>{elements.map((element) => { const metric = metricFor(element); const value = metricValue(metric); const refs = element.evidence_refs?.length ?? element.evidence?.length ?? 0; return <article className={styles.elementCard} key={element.key}><div className={styles.elementHeader}><Glyph decorative glyph={elementGlyphKey(element.key)} size={32} /><strong>{element.label}</strong><span>{displayElementState(element.status)} · {displayConfidence(element.confidence ?? metric.confidence)}</span></div><p>{formatMetric(value, metric.unit ?? element.unit)}</p><small>{element.zone ?? metric.zone ?? "No zone"} · {element.sample_size ?? metric.sample_size ?? "—"} matches · {refs} evidence source{refs === 1 ? "" : "s"}</small>{element.limitations?.[0] && <p className={styles.limitation}>{element.limitations[0]}</p>}</article>; })}</div></section>;
}

function FindingReveal({ finding, revealed, onReveal }: { finding: V6Finding | null; revealed: boolean; onReveal: () => void }) {
  if (!finding) return <EmptyState message="Combat Expression is unavailable in this report." />;
  const text = findingLayers(finding);
  return <article className={styles.findingReveal}><span className={styles.eyebrow}><Glyph decorative glyph={familyGlyphKey(finding.family)} size={28} />{firstNonEmpty(finding.family, finding.label, "Observed finding")}</span>{revealed ? <><h2>{firstNonEmpty(finding.claim, text.claim, finding.title, finding.label, "Observed result unavailable")}</h2><p>{firstNonEmpty(findingEvidenceText(finding), text.evidence, finding.observation, "")}</p><MetricReceipt item={finding} /></> : <><p>Ready to compare your estimate with the observed evidence.</p><button className={styles.secondaryButton} type="button" onClick={onReveal}>Reveal observed expression</button></>}</article>;
}

function FindingPanel({ finding, comparisonLabel, supportingEvidence }: { finding: V6Finding | null; comparisonLabel: string; supportingEvidence?: Record<string, Record<string, unknown> | undefined> }) {
  if (!finding) return <EmptyState message="No strongest finding was published for this report." />;
  const layers = findingLayers(finding);
  return <article className={styles.findingPanel}><div className={styles.findingMain}><span className={styles.eyebrow}><Glyph decorative glyph={familyGlyphKey(finding.family)} size={28} />{firstNonEmpty(finding.family, "Finding")}</span><h2 id="v6-beat-5-title">{firstNonEmpty(finding.claim, layers.claim, finding.title, finding.label, "Finding claim unavailable")}</h2><p>{firstNonEmpty(finding.interpretation, layers.interpretation, "")}</p><MetricReceipt item={finding} /><RelationshipEvidence finding={finding} supportingEvidence={supportingEvidence} /></div>{finding.comparison && <Comparison comparison={finding.comparison} label={comparisonLabel} />}</article>;
}

function RelationshipEvidence({ finding, supportingEvidence }: { finding: V6Finding; supportingEvidence?: Record<string, Record<string, unknown> | undefined> }) {
  const kind = finding.interaction?.kind;
  if (!kind || finding.interaction?.enabled !== true) return null;
  const sourceKey = kind === "core_boundary" ? "transfer_frontier" : kind === "after_x" ? "result_response" : kind === "session_curve" ? "session_curve" : kind === "variance_decomposition" ? "consistency" : "portfolio_shape";
  const source = asRecord(supportingEvidence?.[sourceKey]);
  const nested = asRecord(source[kind === "core_boundary" ? "bands" : kind === "after_x" ? "states" : kind === "session_curve" ? "positions" : "component_variance"]);
  const rows = Object.entries(nested).slice(0, 6);
  const title = ({ core_boundary: "Supported distance frontier", after_x: "Observed result states", session_curve: "Direct session positions", two_versions: "Two supported versions", contradiction_reveal: "Surface and underlying evidence", variance_decomposition: "Localized repeatability", identity_eras: "Identity eras", hero_lifecycle: "Hero lifecycle", behavioral_loop: "Behavioral loop" } as const)[kind];
  return <details className={styles.relationshipEvidence}><summary>{title}</summary><p>Only supported aggregate evidence is shown. Unsupported states remain unavailable; the client does not recompute the Finding.</p>{rows.length > 0 ? <div className={styles.relationshipTable} role="table" aria-label={`${title} evidence`}><div role="row" className={styles.relationshipHeader}><span role="columnheader">State</span><span role="columnheader">Evidence</span></div>{rows.map(([label, raw]) => { const row = asRecord(raw); return <div role="row" key={label}><strong role="cell">{label.replaceAll("_", " ")}</strong><span role="cell">{relationshipSummary(row)}</span></div>; })}</div> : <p className={styles.relationshipFallback}>This relationship is qualified, but its visual state is unavailable. The claim and receipt above are the truthful fallback.</p>}</details>;
}

function relationshipSummary(row: Record<string, unknown>): string {
  const counts = [
    typeof row.match_count === "number" ? `${row.match_count} matches` : null,
    typeof row.matches === "number" ? `${row.matches} matches` : null,
    typeof row.opportunities === "number" ? `${row.opportunities} opportunities` : null,
    typeof row.sessions === "number" ? `${row.sessions} sessions` : null,
    typeof row.supported === "boolean" ? (row.supported ? "supported" : "unsupported") : null,
    typeof row.available === "boolean" ? (row.available ? "available" : "unavailable") : null,
  ].filter(Boolean);
  return counts.join(" · ") || "Aggregate comparison available in the evidence drawer";
}

function LayeredFinding({ finding, activeLayer, onLayerChange }: { finding: V6Finding | null; activeLayer: ClaimLayer; onLayerChange: (layer: ClaimLayer) => void }) {
  if (!finding) return <EmptyState message="No secondary or conditional finding was published for this report." />;
  const layers = findingLayers(finding);
  const values: Record<ClaimLayer, string> = {
    claim: firstNonEmpty(layers.claim, finding.claim, finding.title, finding.label, "Claim unavailable"),
    evidence: firstNonEmpty(layers.evidence, findingEvidenceText(finding), finding.observation, "Evidence unavailable"),
    interpretation: firstNonEmpty(layers.interpretation, finding.interpretation, "Interpretation unavailable"),
    recommendation: firstNonEmpty(recommendationBody(layers.recommendation), recommendationBody(finding.recommendation), "Recommendation unavailable"),
  };
  return <article className={styles.layeredFinding}><div className={styles.layerTabs} role="tablist" aria-label="Finding detail layers">{CLAIM_LAYERS.map((layer) => <button key={layer} className={activeLayer === layer ? styles.layerTabActive : styles.layerTab} type="button" role="tab" aria-selected={activeLayer === layer} aria-controls={`v6-layer-${layer}`} onClick={() => onLayerChange(layer)}>{layer}</button>)}</div><div className={styles.layerPanel} id={`v6-layer-${activeLayer}`} role="tabpanel" tabIndex={0}><span className={styles.eyebrow}>{activeLayer}</span><p>{values[activeLayer]}</p>{activeLayer === "evidence" && <MetricReceipt item={finding} />}</div><EvidenceRefs refs={findingEvidenceRefs(finding)} /></article>;
}

function Comparison({ comparison, label }: { comparison: V6Comparison; label: string }) {
  const [tab, setTab] = useState<"positive" | "negative" | "control">("positive");
  const rows = comparison[tab] ?? comparison.rows ?? comparison.contexts ?? [];
  const tabs = ["positive", "negative", "control"] as const;
  return <section className={styles.comparison} aria-label={label}><div className={styles.comparisonHeader}><span className={styles.eyebrow}>{label}</span><p>{firstNonEmpty(comparison.title, comparison.context_label, comparison.note, "")}</p></div><div className={styles.layerTabs} role="tablist" aria-label="Matched evidence contexts">{tabs.map((item) => <button key={item} className={tab === item ? styles.layerTabActive : styles.layerTab} type="button" role="tab" aria-selected={tab === item} onClick={() => setTab(item)}>{item}</button>)}</div>{rows.length === 0 ? <EmptyState message="No comparison rows are available for this context." /> : <div className={styles.comparisonRows}>{rows.map((row, index) => <div className={styles.comparisonRow} key={`${row.key ?? row.label}-${index}`}><span>{row.label}</span><strong>{formatRow(row)}</strong>{row.direction && <small>{row.direction}</small>}</div>)}</div>}</section>;
}

function TimelineScrubber({ points, selectedIndex, onSelect }: { points: V6TimelinePoint[]; selectedIndex: number; onSelect: (index: number) => void }) {
  if (points.length === 0) return <EmptyState message="Pool Evolution timeline is unavailable for this report." />;
  const selected = points[selectedIndex] ?? points[0];
  return <section className={styles.timeline} aria-label="Pool Evolution timeline"><div className={styles.timelineTopline}><span className={styles.eyebrow}>Pool Evolution scrub</span><strong>{selected.label}</strong></div><input type="range" min={0} max={Math.max(0, points.length - 1)} step={1} value={selectedIndex} onChange={(event) => onSelect(Number(event.target.value))} aria-label="Scrub Pool Evolution timeline" aria-valuetext={selected.label} /><div className={styles.timelineMarks}>{points.map((point, index) => <button key={`${point.id ?? point.label}-${index}`} className={index === selectedIndex ? styles.timelineMarkActive : styles.timelineMark} type="button" aria-label={`Show ${point.label}`} aria-pressed={index === selectedIndex} onClick={() => onSelect(index)}>{point.label}</button>)}</div><p>{firstNonEmpty(selected.summary, selected.evidence, "")}</p></section>;
}

function RecommendationChooser({ recommendations, selected, onSelect, committed, onCommit }: { recommendations: V6Choice[]; selected?: string; onSelect: (id: string) => void; committed: boolean; onCommit: () => void }) {
  return <section className={styles.recommendations} aria-label="Recommendation chooser"><div className={styles.choiceList}>{recommendations.map((choice) => { const value = choice.id ?? choice.key ?? choice.value ?? choice.label; const isSelected = selected === value; return <label className={isSelected ? styles.choiceSelected : styles.choice} key={value}><input type="radio" name="v6-recommendation" checked={isSelected} onChange={() => onSelect(value)} /><span><strong>{choice.label}</strong>{choice.description && <small>{choice.description}</small>}</span></label>; })}</div><button className={styles.primaryButton} type="button" disabled={!selected || committed} onClick={onCommit}>{committed ? "Check-in saved" : "Set a five-game check-in"}</button></section>;
}

function FollowUpCard({ result, uiState, onCheck }: { result: unknown; uiState: V6InteractionState["ui_state"]["follow_up"]; onCheck: () => void }) {
  const count = uiState?.eligible_games ?? recordNumber(result, "eligible_games") ?? 0;
  const target = uiState?.target_games ?? 5;
  const reached = count >= target;
  return <section className={styles.followUp} aria-live="polite"><div><span className={styles.eyebrow}>Five-game check-in</span><strong>{Math.min(count, target)} / {target} context-matching games</strong><progress value={Math.min(count, target)} max={target} aria-label="Five-game check-in progress" /></div><p>{reached ? firstNonEmpty(recordText(result, "summary"), recordText(result, "message"), "The five-game comparison is ready.") : "The check-in is not ready yet. Progress does not claim causality or a new identity."}</p><button className={styles.secondaryButton} type="button" onClick={onCheck}>Check progress</button></section>;
}

function HeroMirrorCard({ mirror, revealed, onReveal }: { mirror: V6HeroMirror | null; revealed: boolean; onReveal: () => void }) {
  if (!mirror) return <EmptyState message="Hero Mirror is unavailable for this report." />;
  const eligible = mirror.share_eligible === true && mirror.status !== "suppressed" && mirror.status !== "unavailable";
  return <article className={styles.mirror}><div className={styles.mirrorArt} aria-hidden="true">◐</div>{revealed ? <div className={styles.mirrorResult}><span className={styles.eyebrow}>{firstNonEmpty(mirror.title, "Hero Mirror")}</span><h2 id="v6-mirror-headline">{firstNonEmpty(mirror.headline, mirror.hero_name ? `A mirror in ${mirror.hero_name}` : "Mirror result unavailable")}</h2><p>{firstNonEmpty(mirror.body, "")}</p><div className={styles.mirrorFacts}>{Object.entries(mirror.player_behavior ?? {}).map(([key, value]) => <div key={key}><span>{humanize(key)}</span><strong>{value}</strong><small>{mirror.hero_behavior?.[key] ?? ""}</small></div>)}</div><p className={styles.eligibility}>{eligible ? "Eligible for a standalone share candidate." : firstNonEmpty(...(mirror.limitations ?? []), "Not eligible for standalone sharing.")}</p></div> : <div className={styles.lockedReveal}><span className={styles.eyebrow}>Hero Mirror</span><p>Reveal the server-qualified mirror when you are ready.</p><button className={styles.primaryButton} type="button" onClick={onReveal}>Reveal Hero Mirror</button></div>}</article>;
}

function ShareComposer({ report, selected, onSelect, onCopy, copied }: { report: V6StoryReport; selected?: string; onSelect: (id: string) => void; onCopy: (candidate: V6ShareCandidate) => void; copied: boolean }) {
  const [message, setMessage] = useState("");
  const eligible = report.share_candidates.filter((candidate) => candidate.eligible === true && candidate.status !== "suppressed" && candidate.status !== "unavailable" && shareCardType(candidate));
  const active = eligible.find((candidate) => shareCandidateId(candidate) === selected) ?? eligible[0];
  const cardType = active ? shareCardType(active) : null;
  const cardUrl = cardType && report.report_id ? `/v1/reports/${encodeURIComponent(report.report_id)}/share/${cardType}?show_name=${Boolean(report.identity.display_name)}&show_avatar=false` : "";
  const shareState = shareStateFor(report, eligible.length);
  const permalink = () => `${window.location.origin}/report/${encodeURIComponent(report.report_id ?? "")}`;
  async function copyLink(): Promise<void> { if (!navigator.clipboard) { setMessage("Copy is not available in this browser."); return; } await navigator.clipboard.writeText(permalink()); setMessage("Report link copied."); }
  async function nativeShare(): Promise<void> { try { if (navigator.share) { await navigator.share({ title: "My Dota DNA", url: permalink() }); setMessage("Share sheet opened."); } else await copyLink(); } catch (error) { if ((error as DOMException).name !== "AbortError") setMessage("Sharing is not available in this browser."); } }
  function download(): void { if (!cardUrl || !cardType) return; const anchor = document.createElement("a"); anchor.href = cardUrl; anchor.download = `dota-dna-${cardType}.svg`; anchor.click(); setMessage("Card download started."); }
  return <section className={styles.shareComposer} aria-label="Eligible share-card gallery"><div><span className={styles.eyebrow}>Share cards</span><h2>Your Dota DNA, in pieces.</h2><p>Choose the part that feels most like you.</p></div>{eligible.length === 0 ? <StateCard state={shareState} title={shareCopyFor(shareState)} body="Only server-eligible cards appear here. Your reflection and private identifiers are never used as evidence." /> : <><div className={styles.shareGrid}>{eligible.map((candidate) => { const id = shareCandidateId(candidate); const isSelected = active === candidate; return <label className={isSelected ? styles.shareCandidateSelected : styles.shareCandidate} key={id}><input type="radio" name="v6-share-candidate" checked={isSelected} onChange={() => onSelect(id)} /><span><strong>{firstNonEmpty(candidate.title, recordText(candidate.payload, "title"), humanize(candidate.kind), "Share card")}</strong><small>{firstNonEmpty(candidate.headline, candidate.body, candidate.reason, recordText(candidate.payload, "reason"), "")}</small></span></label>; })}</div>{active && cardUrl && <div className={styles.sharePreview}><img src={cardUrl} alt={`Preview of the selected ${cardType} share card`} onError={() => setMessage("This card could not be loaded. Copy the report link instead.")} /><div className={styles.shareActions}><button className={styles.primaryButton} type="button" onClick={() => void nativeShare()}>Share card</button><button className={styles.secondaryButton} type="button" onClick={download}>Download card</button><button className={styles.secondaryButton} type="button" onClick={() => void copyLink()}>Copy link</button><button className={styles.smallButton} type="button" onClick={() => onCopy(active)}>{copied ? "Text copied" : "Copy text"}</button></div></div>}<p className={styles.shareStatus} role="status" aria-live="polite">{shareState === "mixed" ? "Some parts are share-ready; the rest stays inside the report." : message}</p></>}</section>;
}

function MetricReceipt({ item }: { item: V6Finding }) {
  const metric = metricFor(item);
  const interval = metricInterval(metric);
  const value = metricValue(metric);
  return <dl className={styles.receipt}><div><dt>Estimate</dt><dd>{formatMetric(value, metric.unit)}</dd></div><div><dt>95% interval</dt><dd>{formatInterval(interval, metric.unit)}</dd></div><div><dt>Sample</dt><dd>{item.sample_size ?? metric.sample_size ?? "—"}</dd></div><div><dt>Sessions</dt><dd>{item.independent_sessions ?? metric.independent_sessions ?? "—"}</dd></div><div><dt>Confidence</dt><dd>{displayConfidence(item.confidence ?? metric.confidence)}</dd></div></dl>;
}

function EvidenceRefs({ refs }: { refs?: string[] }) {
  if (!refs || refs.length === 0) return null;
  return <p className={styles.evidenceRefs}>Evidence references: {refs.join(", ")}</p>;
}

function EmptyState({ message }: { message: string }) {
  return <div className={styles.empty} role="status"><strong>Not available</strong><p>{message}</p></div>;
}

function ResultNotice({ result }: { result: unknown }) {
  const record = asRecord(result);
  return <div className={styles.resultNotice} role="status"><span className={styles.eyebrow}>Deep response</span><p>{firstNonEmpty(recordText(record, "message"), recordText(record, "status"), "Your deeper question is queued.")}</p></div>;
}

function findFamily(findings: V6Finding[], family: string): V6Finding | null {
  return findings.find((finding) => `${finding.family} ${finding.key} ${finding.label ?? ""}`.toLowerCase().includes(family)) ?? null;
}

function isPublished(finding: V6Finding): boolean {
  return finding.published === true && finding.status !== "suppressed" && finding.status !== "unavailable";
}

function findingState(finding: V6Finding | null): FamilyState {
  if (!finding || finding.status === "unavailable") return "unavailable";
  if (finding.status === "suppressed") return "neutral";
  if (finding.status === "insufficient" || finding.status === "limited") return "insufficient";
  if (finding.status === "mixed" || finding.direction === "mixed") return "mixed";
  if (isPublished(finding)) return "qualified";
  return "neutral";
}

function stateLabel(state: FamilyState): string {
  return { qualified: "Qualified", neutral: "Neutral", insufficient: "Insufficient evidence", mixed: "Mixed", unavailable: "Unavailable" }[state];
}

function familyStateCopy(family: string, state: FamilyState, finding: V6Finding | null): string {
  const key = family.toLowerCase();
  const limitation = firstNonEmpty(finding?.limitations?.[0], "The supported comparison did not meet the minimum evidence requirement.");
  if (state === "neutral") {
    if (key.includes("pool")) return "No single pool shape separated cleanly.";
    if (key.includes("transfer")) return "The familiar and stretch parts of your pool stay within the supported range.";
    if (key.includes("post-loss")) return "Your next-choice movement stays about the same across the supported result states.";
    if (key.includes("combat")) return "Involvement and death exposure stay compatible in the supported comparison.";
    if (key.includes("session")) return "Your covered expression stays compatible across completed session positions.";
  }
  if (state === "insufficient") {
    const reason = key.includes("pool") ? limitation : key.includes("transfer") ? limitation : key.includes("post-loss") ? firstNonEmpty(finding?.limitations?.[0], "Not enough same-session transitions to call a post-loss pattern.") : key.includes("combat") ? firstNonEmpty(finding?.limitations?.[0], "Not enough context-resolved matches to call combat expression.") : key.includes("session") ? firstNonEmpty(finding?.limitations?.[0], "Not enough completed sessions to call a session pattern.") : limitation;
    return `Not enough signal to call this one. ${reason}`;
  }
  if (state === "mixed") {
    if (key.includes("pool")) return firstNonEmpty(finding?.interpretation, "Your pool has two valid layers: the names move, while the jobs hold.");
    if (key.includes("post-loss")) return firstNonEmpty(finding?.interpretation, "The one-loss and two-plus-loss states do not tell the same story.");
    if (key.includes("transfer")) return firstNonEmpty(finding?.interpretation, "Your answer changes by signal.");
    if (key.includes("combat")) return firstNonEmpty(finding?.interpretation, "One signal holds while another moves.");
    if (key.includes("session")) return firstNonEmpty(finding?.interpretation, "The session story changes by what you measure.");
  }
  return `${family} was not available for this report.`;
}

function heroName(hero: V6HeroRow): string {
  return firstNonEmpty(hero.display_name, hero.hero_name, hero.name);
}

function humanize(value?: string | null): string {
  if (!value) return "";
  return value.replaceAll("_", " ").replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function shareCardType(candidate: V6StoryReport["share_candidates"][number]): "identity" | "strongest-finding" | "hero-mirror" | null {
  const value = `${candidate.id ?? ""} ${candidate.candidate_id ?? ""} ${candidate.kind ?? ""}`.toLowerCase();
  if (value.includes("hero-mirror") || value.includes("hero_mirror")) return "hero-mirror";
  if (value.includes("strongest-finding") || value.includes("strongest_finding") || candidate.kind === "finding") return "strongest-finding";
  if (value.includes("identity")) return "identity";
  return null;
}

function questionIsOffered(question: V6StoryReport["diagnostic_questions"][number]): boolean {
  const confidence = question.confidence?.toLowerCase();
  return question.offered !== false && question.available !== false && question.eligibility !== "suppressed" && question.eligibility !== "unavailable" && (confidence === "high" || confidence === "moderate") && (question.evidence_refs?.length ?? 0) > 0 && (question.blocking_confounders?.length ?? 0) === 0;
}

function recommendationChoices(report: V6StoryReport, ...findings: Array<V6Finding | null>): V6Choice[] {
  const choices: V6Choice[] = [];
  for (const finding of findings) {
    if (report.schema_version === "free-dna-report-6.1.0" && !verifiedRecommendation(finding)) continue;
    const recommendation = finding?.recommendation ?? finding?.claim_contract?.recommendation;
    if (recommendation && typeof recommendation === "object") {
      const options = recommendation.options ?? [];
      if (options.length > 0) choices.push(...options);
      else choices.push({ id: recommendation.recommendation_id ?? recommendation.id ?? finding?.key ?? finding?.family, label: firstNonEmpty(recommendation.title, recommendation.label, recommendation.instruction, recommendation.action, finding?.label, "Recommendation"), description: firstNonEmpty(recommendation.body, recommendation.instruction, recommendation.rationale, recommendationContextText(recommendation.context)) });
    }
  }
  const beatOptions = storyPages(report).find((beat) => beat.kind === "recommendation" || beat.key === "recommendation")?.options ?? [];
  return uniqueChoices([...choices, ...beatOptions]);
}

function verifiedRecommendation(finding: V6Finding | null): boolean {
  const verification = finding?.claim_contract?.verification;
  return Boolean(verification && typeof verification.eligibility_games === "number" && verification.eligibility_games > 0 && verification.primary_metric && verification.guardrail_metric && verification.causal === false && verification.abstention);
}

function shareStateFor(report: V6StoryReport, eligibleCount: number): FamilyState {
  const candidates = report.share_candidates;
  if (eligibleCount > 0 && candidates.some((candidate) => candidate.eligible !== true || candidate.status === "suppressed" || candidate.status === "unavailable")) return "mixed";
  if (eligibleCount > 0) return "qualified";
  const quality = report.quality?.partial === true || report.identity_summary.status === "limited" || report.identity_summary.state === "limited" || report.identity_summary.status === "insufficient" || report.identity_summary.state === "insufficient";
  return quality ? "insufficient" : "neutral";
}

function shareCopyFor(state: FamilyState): string {
  if (state === "neutral") return "Your story is ready to keep, even when no standalone card clears the share gate.";
  if (state === "insufficient") return "No standalone share card is eligible from this report.";
  if (state === "mixed") return "Some parts are share-ready; the rest stays inside the report.";
  return "Your Dota DNA, in pieces.";
}

function uniqueChoices(choices: V6Choice[]): V6Choice[] {
  const seen = new Set<string>();
  return choices.filter((choice) => { const id = choice.id ?? choice.key ?? choice.value ?? choice.label; if (seen.has(id)) return false; seen.add(id); return true; });
}

function storyPages(report: V6StoryReport): V6StoryBeat[] {
  return Array.isArray(report.story) ? report.story : report.story.beats ?? report.pages ?? [];
}

function storyCopy(beat: V6StoryBeat | undefined, key: string): string {
  if (!beat) return "";
  const content = beat.content?.[key];
  const copy = beat.copy?.[key];
  return firstNonEmpty(beat[key as keyof V6StoryBeat] as string | null | undefined, typeof content === "string" ? content : null, copy);
}

function findingLayers(finding: V6Finding): V6ClaimLayers {
  return finding.claim_contract ?? finding.layers ?? {};
}

function findingEvidenceText(finding: V6Finding): string {
  if (typeof finding.evidence === "string") return finding.evidence;
  return firstNonEmpty(finding.evidence_text, ...(finding.evidence ?? []).map((item) => item.observation ?? item.label ?? item.key));
}

function findingEvidenceRefs(finding: V6Finding): string[] {
  if (finding.evidence_refs?.length) return finding.evidence_refs;
  return [...new Set((finding.evidence_items ?? []).flatMap((item) => item.references ?? (item.key ? [item.key] : [])))];
}

function diagnosticQuestionId(question: V6StoryReport["diagnostic_questions"][number]): string {
  return question.id ?? question.question_id ?? "";
}

function shareCandidateId(candidate: V6StoryReport["share_candidates"][number]): string {
  return candidate.id ?? candidate.candidate_id ?? "";
}

function recommendationBody(recommendation: V6Finding["recommendation"]): string {
  if (!recommendation) return "";
  return typeof recommendation === "string" ? recommendation : firstNonEmpty(recommendation.instruction, recommendation.body, recommendation.action, recommendation.rationale, recommendationContextText(recommendation.context), recommendation.title);
}

function recommendationContextText(context: V6Recommendation["context"]): string {
  if (typeof context === "string") return context;
  if (!context || typeof context !== "object") return "";
  return Object.entries(context)
    .filter(([, value]) => ["string", "number", "boolean"].includes(typeof value))
    .map(([key, value]) => `${key.replaceAll("_", " ")}: ${String(value)}`)
    .join(" · ");
}

function formatRow(row: { value?: string | number | null; estimate?: number | null; unit?: string | null }): string {
  if (typeof row.value === "string") return row.value;
  const value = typeof row.value === "number" ? row.value : row.estimate ?? null;
  return formatMetric(value, row.unit);
}

function formatMetric(value: number | null, unit?: string | null): string {
  if (value === null) return "Not available";
  if (unit?.includes("rate") || unit?.includes("share") || unit === "%") return `${Math.round(value * 100)}%`;
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function formatInterval(interval: ReturnType<typeof metricInterval>, unit?: string | null): string {
  if (!interval || interval.lower === null || interval.lower === undefined || interval.upper === null || interval.upper === undefined) return "Not available";
  return `${formatMetric(interval.lower, unit)} – ${formatMetric(interval.upper, unit)}`;
}

function normalizeInteractionState(state: V6InteractionState): V6InteractionState {
  const safeState = Object.fromEntries(Object.entries(state).filter(([key]) => !["observed", "computed", "evidence", "analytical_truth"].includes(key)));
  return {
    ...initialInteractionState(),
    ...safeState,
    current_beat: clampBeat(state.current_beat),
    completed_beats: uniqueNumbers(state.completed_beats ?? []).filter((item) => item >= 0 && item < 9 && !(state.skipped_beats ?? []).includes(item)),
    skipped_beats: uniqueNumbers(state.skipped_beats ?? []).filter((item) => item >= 0 && item < 9),
    user_reported: { ...(state.user_reported ?? {}) },
    ui_state: { ...(state.ui_state ?? {}) },
  };
}

function clampBeat(index: number): number {
  return Math.max(0, Math.min(BEAT_IDS.length - 1, Number.isFinite(index) ? Math.round(index) : 0));
}

function clampTimelineIndex(index: number | undefined, length: number): number {
  if (length <= 0) return 0;
  return Math.max(0, Math.min(length - 1, typeof index === "number" ? Math.round(index) : 0));
}

function uniqueNumbers(values: number[]): number[] {
  return [...new Set(values)];
}

function elementGlyphKey(key: string): string {
  if (key.includes("toolkit")) return "toolkit";
  if (key.includes("involvement")) return "involvement";
  if (key.includes("finishing")) return "finishing";
  if (key.includes("death")) return "death_exposure";
  if (key.includes("transfer")) return "transfer";
  if (key.includes("consistency")) return "consistency";
  return "breadth";
}

function familyGlyphKey(family: string): string {
  if (family.includes("transfer")) return "transfer_finding";
  if (family.includes("post_loss")) return "post_loss_response";
  if (family.includes("combat")) return "combat_expression";
  if (family.includes("session")) return "session_drift";
  return "pool_shape";
}

function progressCount(state: V6InteractionState): number {
  return Math.min(9, new Set([...(state.completed_beats ?? []), ...(state.skipped_beats ?? [])]).size);
}

function beatLabel(id: BeatId): string {
  return { "self-estimate": "Start", "identity-reveal": "Shape", "pool-evolution": "Pool", "combat-expression": "Change", "strongest-finding": "After loss", "secondary-finding": "Match", recommendation: "Session", "hero-mirror": "Signature", "deep-diagnostic": "Share" }[id];
}

function scrollToBeat(id: BeatId): void {
  if (typeof document === "undefined") return;
  const target = document.getElementById(`v6-beat-${BEAT_IDS.indexOf(id) + 1}`);
  const reduced = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
  target?.scrollIntoView({ behavior: reduced ? "auto" : "smooth", block: "start" });
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? value as Record<string, unknown> : {};
}

function recordText(value: unknown, key: string): string {
  const item = asRecord(value)[key];
  return typeof item === "string" ? item : "";
}

function recordNumber(value: unknown, key: string): number | null {
  const item = asRecord(value)[key];
  return typeof item === "number" ? item : null;
}

function followUpState(value: unknown): V6InteractionState["ui_state"]["follow_up"] {
  const record = asRecord(value);
  const eligible = recordNumber(record, "eligible_games") ?? recordNumber(record, "context_matching_games");
  const target = recordNumber(record, "target_games");
  return { eligible_games: eligible ?? 0, target_games: target === 5 ? 5 : 5, status: recordText(record, "status") || undefined };
}

function syncLabel(status: SyncStatus): string {
  return { idle: "", loading: "Resuming…", saving: "Saving…", saved: "Saved", resumed: "Resumed", deleted: "Deleted", conflict: "Needs review", error: "Not saved" }[status];
}

export { BEAT_IDS };
export { isFreeDnaReportV6, isFreeDnaReportV61 } from "./types";
export type { V6Report, V61Report, V6StoryReport } from "./types";
export { ReportStoryV6 };
