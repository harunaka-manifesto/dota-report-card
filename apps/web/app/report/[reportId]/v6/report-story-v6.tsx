"use client";

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
  type V6Element,
  type V6Report,
  type V6StoryBeat,
  type V6TimelinePoint,
} from "./types";
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

const CLAIM_LAYERS: readonly ClaimLayer[] = ["claim", "evidence", "interpretation", "recommendation"];

/** Dedicated v6 renderer. The parent route can select it by schema_version. */
export default function ReportStoryV6({ report }: { report: V6Report }) {
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
  const strongestFinding = useMemo(() => chooseStrongestFinding(report.findings), [report.findings]);
  const secondaryFinding = useMemo(() => chooseSecondaryFinding(report.findings, strongestFinding), [report.findings, strongestFinding]);
  const combatFinding = useMemo(() => findFamily(report.findings, "combat"), [report.findings]);
  const timeline = useMemo(() => {
    const evolution = report.hero_portfolio.evolution;
    return evolution?.points ?? evolution?.timeline ?? report.hero_portfolio.timeline ?? [];
  }, [report.hero_portfolio]);
  const mirror = report.hero_portfolio.mirror ?? report.hero_portfolio.hero_mirror ?? null;
  const recommendations = useMemo(() => recommendationChoices(report, strongestFinding, secondaryFinding), [report, strongestFinding, secondaryFinding]);
  const selectedTimelineIndex = clampTimelineIndex(journey.ui_state.pool_evolution_position, timeline.length);

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
      completed_beats: uniqueNumbers([...state.completed_beats, index]),
    }));
    if (next > index) scrollToBeat(BEAT_IDS[nextIndex]);
  }

  function skipBeat(index: number): void {
    updateJourney((state) => ({
      ...state,
      current_beat: clampBeat(index + 1),
      skipped_beats: uniqueNumbers([...state.skipped_beats, index]),
      completed_beats: uniqueNumbers([...state.completed_beats, index]),
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

  async function copyShareCandidate(candidate: { title?: string | null; headline?: string | null; body?: string | null }): Promise<void> {
    const text = [candidate.title, candidate.headline, candidate.body].filter(Boolean).join("\n\n");
    if (!text || typeof navigator === "undefined" || !navigator.clipboard) return;
    await navigator.clipboard.writeText(text);
    setShareCopied(true);
    setTimeout(() => setShareCopied(false), 2200);
  }

  return (
    <main className={styles.story} aria-label="Free DNA v6 identity report">
      <header className={styles.topbar}>
        <a className={styles.wordmark} href="#v6-beat-1">FREE DNA <span>06</span></a>
        <p className={styles.topline}>Summary-only identity report</p>
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
        <aside className={styles.rail} aria-label="Report beats">
          <div className={styles.railIntro}><span>V6</span><small>YOUR<br />SHAPE</small></div>
          <nav>
            {BEAT_IDS.map((id, index) => (
              <button key={id} className={currentBeat === index ? styles.railButtonActive : styles.railButton} type="button" aria-current={currentBeat === index ? "step" : undefined} onClick={() => moveToBeat(index)}>
                <span className={styles.railNumber}>{String(index + 1).padStart(2, "0")}</span>
                <span>{beatLabel(id)}</span>
              </button>
            ))}
          </nav>
          <p className={styles.railNote}>All beats are optional.<br />Your answers stay<br />under user_reported.</p>
        </aside>

        <div className={styles.content}>
          <div className={styles.progressHeader}>
            <span>Beat {currentBeat + 1} of 9</span>
            <progress value={journey.completed_beats.length + journey.skipped_beats.length} max={9} aria-label="Story progress" />
            <span>{journey.completed_beats.length + journey.skipped_beats.length}/9 complete</span>
          </div>

          <section id="v6-beat-1" className={`${styles.beat} ${styles.beatEstimate}`} aria-labelledby="v6-beat-1-title">
            <BeatHeader number={1} id="self-estimate" beat={beats[0]} fallbackTitle="Start with your read" fallbackBody="Before the report speaks, make a quick estimate." onSkip={() => skipBeat(0)} />
            <ChoiceQuestion
              legend={firstNonEmpty(storyCopy(beats[0], "prompt"), "Your estimate")}
              choices={beats[0]?.options ?? report.identity_summary.options ?? []}
              selected={journey.user_reported.identity_estimate}
              onSelect={(choice) => chooseUserAnswer("identity_estimate", choice)}
              emptyMessage="This self-estimate is not available in the report payload."
            />
            <div className={styles.beatActions}>
              <button className={styles.primaryButton} type="button" disabled={!journey.user_reported.identity_estimate} onClick={() => finishBeat(0)}>Reveal my report <span aria-hidden="true">→</span></button>
              <button className={styles.linkButton} type="button" onClick={() => skipBeat(0)}>Skip this beat</button>
            </div>
          </section>

          <section id="v6-beat-2" className={`${styles.beat} ${styles.beatIdentity}`} aria-labelledby="v6-beat-2-title">
            <BeatHeader number={2} id="identity-reveal" beat={beats[1]} fallbackTitle="The observed shape" fallbackBody="The headline below comes from the report’s observed evidence, not from your estimate." onSkip={() => skipBeat(1)} />
            <div className={styles.identityReveal}>
              <p className={styles.revealLabel}>Observed identity summary</p>
              {journey.ui_state.identity_revealed ? (
                <>
                  <h2 id="v6-beat-2-title" className={styles.revealHeadline}>{firstNonEmpty(report.identity_summary.headline, report.identity_summary.title, "") || "Identity summary unavailable"}</h2>
                  <ul className={styles.supportList}>{(report.identity_summary.supporting_lines ?? report.identity_summary.support ?? []).map((line) => <li key={line}>{line}</li>)}</ul>
                  <EvidenceRefs refs={report.identity_summary.evidence_refs} />
                  <ElementLedger elements={report.elements} />
                </>
              ) : (
                <div className={styles.lockedReveal}>
                  <span aria-hidden="true">◇</span>
                  <p>Ready when you are. Your self-estimate remains separate from the observed result.</p>
                  <button className={styles.primaryButton} type="button" onClick={() => revealObserved("identity_revealed", 2)}>Reveal observed identity</button>
                </div>
              )}
            </div>
            <BeatFooter index={1} onNext={() => finishBeat(1)} onSkip={() => skipBeat(1)} disabled={!journey.ui_state.identity_revealed} />
          </section>

          <section id="v6-beat-3" className={`${styles.beat} ${styles.beatPool}`} aria-labelledby="v6-beat-3-title">
            <BeatHeader number={3} id="pool-evolution" beat={beats[2]} fallbackTitle="Predict the pool" fallbackBody="Make a call, then scrub through the observed Pool Evolution." onSkip={() => skipBeat(2)} />
            <ChoiceQuestion
              legend={firstNonEmpty(storyCopy(beats[2], "prompt"), report.hero_portfolio.prediction?.prompt, "Your pool prediction")}
              choices={beats[2]?.options ?? report.hero_portfolio.prediction?.options ?? []}
              selected={journey.user_reported.hero_pool_prediction}
              onSelect={(choice) => chooseUserAnswer("hero_pool_prediction", choice)}
              emptyMessage="The report did not offer prediction choices."
            />
            <div className={styles.revealStrip}>
              <div><span className={styles.eyebrow}>Observed answer</span><strong>{firstNonEmpty(report.hero_portfolio.prediction?.answer, report.hero_portfolio.prediction?.observed, "Not available")}</strong></div>
              <p>{firstNonEmpty(report.hero_portfolio.prediction?.reveal, storyCopy(beats[2], "reveal"), "")}</p>
            </div>
            <TimelineScrubber points={timeline} selectedIndex={selectedTimelineIndex} onSelect={setTimeline} />
            <BeatFooter index={2} onNext={() => finishBeat(2)} onSkip={() => skipBeat(2)} disabled={!journey.user_reported.hero_pool_prediction && timeline.length === 0} />
          </section>

          <section id="v6-beat-4" className={`${styles.beat} ${styles.beatCombat}`} aria-labelledby="v6-beat-4-title">
            <BeatHeader number={4} id="combat-expression" beat={beats[3]} fallbackTitle="How do you show up in fights?" fallbackBody="Make a second self-estimate. The report keeps it separate from your observed Combat Expression." onSkip={() => skipBeat(3)} />
            <ChoiceQuestion
              legend={firstNonEmpty(storyCopy(beats[3], "prompt"), "Your combat-expression estimate")}
              choices={beats[3]?.options ?? []}
              selected={journey.user_reported.combat_expression_estimate}
              onSelect={(choice) => chooseUserAnswer("combat_expression_estimate", choice)}
              emptyMessage="The report did not offer a combat self-estimate."
            />
            <FindingReveal finding={combatFinding} revealed={Boolean(journey.ui_state.combat_expression_revealed)} onReveal={() => revealObserved("combat_expression_revealed", 4)} />
            <BeatFooter index={3} onNext={() => finishBeat(3)} onSkip={() => skipBeat(3)} disabled={!journey.ui_state.combat_expression_revealed && !combatFinding} />
          </section>

          <section id="v6-beat-5" className={`${styles.beat} ${styles.beatFinding}`} aria-labelledby="v6-beat-5-title">
            <BeatHeader number={5} id="strongest-finding" beat={beats[4]} fallbackTitle="The strongest finding" fallbackBody="Compare matched evidence before deciding what it means." onSkip={() => skipBeat(4)} />
            <FindingPanel finding={strongestFinding} comparisonLabel="Matched-evidence comparison" />
            <BeatFooter index={4} onNext={() => finishBeat(4)} onSkip={() => skipBeat(4)} disabled={!strongestFinding} />
          </section>

          <section id="v6-beat-6" className={`${styles.beat} ${styles.beatLayers}`} aria-labelledby="v6-beat-6-title">
            <BeatHeader number={6} id="secondary-finding" beat={beats[5]} fallbackTitle="Look underneath" fallbackBody="Open the claim in layers. Every layer stays bounded by its evidence." onSkip={() => skipBeat(5)} />
            <LayeredFinding finding={secondaryFinding} activeLayer={journey.ui_state.claim_layer ?? "claim"} onLayerChange={setClaimLayer} />
            <BeatFooter index={5} onNext={() => finishBeat(5)} onSkip={() => skipBeat(5)} disabled={!secondaryFinding} />
          </section>

          <section id="v6-beat-7" className={`${styles.beat} ${styles.beatAction}`} aria-labelledby="v6-beat-7-title">
            <BeatHeader number={7} id="recommendation" beat={beats[6]} fallbackTitle="Choose a next experiment" fallbackBody="Pick one server-authored recommendation, then predeclare a five-game check-in." onSkip={() => skipBeat(6)} />
            <RecommendationChooser recommendations={recommendations} selected={journey.user_reported.recommendation_id} onSelect={selectRecommendation} committed={Boolean(journey.user_reported.commitment)} onCommit={() => void commitRecommendation()} />
            {journey.user_reported.commitment && <FollowUpCard result={followUpResult} uiState={journey.ui_state.follow_up} onCheck={() => void checkFollowUp()} />}
            <BeatFooter index={6} onNext={() => finishBeat(6)} onSkip={() => skipBeat(6)} disabled={!journey.user_reported.recommendation_id} />
          </section>

          <section id="v6-beat-8" className={`${styles.beat} ${styles.beatMirror}`} aria-labelledby="v6-beat-8-title">
            <BeatHeader number={8} id="hero-mirror" beat={beats[7]} fallbackTitle="Meet your Hero Mirror" fallbackBody="A mirror is eligible only when the server says its evidence can stand alone." onSkip={() => skipBeat(7)} />
            <HeroMirrorCard mirror={mirror} revealed={Boolean(journey.ui_state.hero_mirror_revealed)} onReveal={() => updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, hero_mirror_revealed: true } }))} />
            <ShareComposer report={report} selected={journey.ui_state.selected_share_candidate} onSelect={(id) => updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, selected_share_candidate: id } }))} onCopy={(candidate) => void copyShareCandidate(candidate)} copied={shareCopied} />
            <BeatFooter index={7} onNext={() => finishBeat(7)} onSkip={() => skipBeat(7)} disabled={!mirror && report.share_candidates.length === 0} />
          </section>

          <section id="v6-beat-9" className={`${styles.beat} ${styles.beatDeep}`} aria-labelledby="v6-beat-9-title">
            <BeatHeader number={9} id="deep-diagnostic" beat={beats[8]} fallbackTitle="Choose your Deep question" fallbackBody="Route the next analysis from a question this report can actually support." onSkip={() => skipBeat(8)} />
            <form className={styles.deepForm} onSubmit={(event) => void chooseDiagnostic(event)}>
              <fieldset>
                <legend className={styles.questionLegend}>Which thread should Deep test?</legend>
                <div className={styles.questionList}>
                  {report.diagnostic_questions.map((question) => {
                    const id = diagnosticQuestionId(question);
                    const selected = journey.ui_state.diagnostic_question_id === id;
                    return <label className={selected ? styles.questionOptionSelected : styles.questionOption} key={id}><input type="radio" name="v6-diagnostic" checked={selected} onChange={() => chooseDiagnosticQuestion(id)} /><span><strong>{firstNonEmpty(question.label, question.family, question.finding_family, "Deep question")}</strong><small>{firstNonEmpty(question.question, question.prompt, question.body, question.context, "")}</small></span></label>;
                  })}
                </div>
              </fieldset>
              {report.diagnostic_questions.length === 0 && <EmptyState message="No evidence-qualified Deep question was offered for this report." />}
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

function BeatHeader({ number, id, beat, fallbackTitle, fallbackBody, onSkip }: { number: number; id: BeatId; beat?: V6StoryBeat; fallbackTitle: string; fallbackBody: string; onSkip: () => void }) {
  return <header className={styles.beatHeader}><div className={styles.beatKicker}><span>{String(number).padStart(2, "0")}</span><span>{firstNonEmpty(beat?.eyebrow, storyCopy(beat, "eyebrow"), beatLabel(id))}</span><button className={styles.skipButton} type="button" onClick={onSkip}>Skip beat</button></div><h1 id={`v6-beat-${number}-title`}>{firstNonEmpty(storyCopy(beat, "title"), fallbackTitle)}</h1><p>{firstNonEmpty(storyCopy(beat, "body"), storyCopy(beat, "prompt"), fallbackBody)}</p></header>;
}

function BeatFooter({ index, onNext, onSkip, disabled }: { index: number; onNext: () => void; onSkip: () => void; disabled?: boolean }) {
  return <div className={styles.beatFooter}><button className={styles.primaryButton} type="button" disabled={disabled} onClick={onNext}>{index === 8 ? "Finish report" : "Continue"} <span aria-hidden="true">→</span></button><button className={styles.linkButton} type="button" onClick={onSkip}>Skip this beat</button></div>;
}

function ChoiceQuestion({ legend, choices, selected, onSelect, emptyMessage }: { legend: string; choices: V6Choice[]; selected?: string; onSelect: (choice: V6Choice) => void; emptyMessage: string }) {
  return <fieldset className={styles.choiceFieldset}><legend>{legend}</legend>{choices.length === 0 ? <EmptyState message={emptyMessage} /> : <div className={styles.choiceList}>{choices.map((choice) => { const value = choice.id ?? choice.key ?? choice.value ?? choice.label; const checked = selected === value; return <label key={value} className={checked ? styles.choiceSelected : styles.choice}><input type="radio" name={`choice-${legend}`} value={value} checked={checked} onChange={() => onSelect(choice)} /><span><strong>{choice.label}</strong>{choice.description && <small>{choice.description}</small>}</span></label>; })}</div>}</fieldset>;
}

function ElementLedger({ elements }: { elements: V6Element[] }) {
  if (elements.length === 0) return <EmptyState message="The report did not publish its seven identity Elements." />;
  return <section className={styles.elementLedger} aria-label="Seven public identity Elements"><div className={styles.elementLedgerHeader}><span className={styles.eyebrow}>Seven public Elements</span><p>Observed summary signals stay distinct from your self-reported answers.</p></div><div className={styles.elementGrid}>{elements.map((element) => { const metric = metricFor(element); const value = metricValue(metric); return <article className={styles.elementCard} key={element.key}><div className={styles.elementHeader}><strong>{element.label}</strong><span>{displayConfidence(element.confidence ?? metric.confidence)}</span></div><p>{formatMetric(value, metric.unit ?? element.unit)}</p><small>{element.zone ?? metric.zone ?? "No zone"} · {element.sample_size ?? metric.sample_size ?? "—"} matches</small></article>; })}</div></section>;
}

function FindingReveal({ finding, revealed, onReveal }: { finding: V6Finding | null; revealed: boolean; onReveal: () => void }) {
  if (!finding) return <EmptyState message="Combat Expression is unavailable in this report." />;
  const text = findingLayers(finding);
  return <article className={styles.findingReveal}><span className={styles.eyebrow}>{firstNonEmpty(finding.family, finding.label, "Observed finding")}</span>{revealed ? <><h2>{firstNonEmpty(finding.claim, text.claim, finding.title, finding.label, "Observed result unavailable")}</h2><p>{firstNonEmpty(findingEvidenceText(finding), text.evidence, finding.observation, "")}</p><MetricReceipt item={finding} /></> : <><p>Ready to compare your estimate with the observed evidence.</p><button className={styles.secondaryButton} type="button" onClick={onReveal}>Reveal observed expression</button></>}</article>;
}

function FindingPanel({ finding, comparisonLabel }: { finding: V6Finding | null; comparisonLabel: string }) {
  if (!finding) return <EmptyState message="No strongest finding was published for this report." />;
  const layers = findingLayers(finding);
  return <article className={styles.findingPanel}><div className={styles.findingMain}><span className={styles.eyebrow}>{firstNonEmpty(finding.family, "Finding")}</span><h2 id="v6-beat-5-title">{firstNonEmpty(finding.claim, layers.claim, finding.title, finding.label, "Finding claim unavailable")}</h2><p>{firstNonEmpty(finding.interpretation, layers.interpretation, "")}</p><MetricReceipt item={finding} /></div>{finding.comparison && <Comparison comparison={finding.comparison} label={comparisonLabel} />}</article>;
}

function LayeredFinding({ finding, activeLayer, onLayerChange }: { finding: V6Finding | null; activeLayer: ClaimLayer; onLayerChange: (layer: ClaimLayer) => void }) {
  if (!finding) return <EmptyState message="No secondary or conditional finding was published for this report." />;
  const layers = findingLayers(finding);
  const values: Record<ClaimLayer, string> = {
    claim: firstNonEmpty(layers.claim, finding.claim, finding.title, finding.label, "Claim unavailable"),
    evidence: firstNonEmpty(layers.evidence, findingEvidenceText(finding), finding.observation, "Evidence unavailable"),
    interpretation: firstNonEmpty(layers.interpretation, finding.interpretation, "Interpretation unavailable"),
    recommendation: firstNonEmpty(layers.recommendation, recommendationBody(finding.recommendation), "Recommendation unavailable"),
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
  return <section className={styles.recommendations} aria-label="Recommendation chooser"><div className={styles.choiceList}>{recommendations.length === 0 ? <EmptyState message="No recommendation was published for this report." /> : recommendations.map((choice) => { const value = choice.id ?? choice.key ?? choice.value ?? choice.label; const isSelected = selected === value; return <label className={isSelected ? styles.choiceSelected : styles.choice} key={value}><input type="radio" name="v6-recommendation" checked={isSelected} onChange={() => onSelect(value)} /><span><strong>{choice.label}</strong>{choice.description && <small>{choice.description}</small>}</span></label>; })}</div><button className={styles.primaryButton} type="button" disabled={!selected || committed} onClick={onCommit}>{committed ? "Five-game check-in declared" : "Commit to five games"}</button></section>;
}

function FollowUpCard({ result, uiState, onCheck }: { result: unknown; uiState: V6InteractionState["ui_state"]["follow_up"]; onCheck: () => void }) {
  const count = uiState?.eligible_games ?? recordNumber(result, "eligible_games") ?? 0;
  const target = uiState?.target_games ?? 5;
  const reached = count >= target;
  return <section className={styles.followUp} aria-live="polite"><div><span className={styles.eyebrow}>Five-game follow-up</span><strong>{Math.min(count, target)} / {target} context-matching games</strong><progress value={Math.min(count, target)} max={target} aria-label="Five-game follow-up progress" /></div><p>{reached ? firstNonEmpty(recordText(result, "summary"), recordText(result, "message"), "The predeclared comparison is ready.") : "Progress only until five context-matching games are available. This does not claim causality or a new identity."}</p><button className={styles.secondaryButton} type="button" onClick={onCheck}>Check progress</button></section>;
}

function HeroMirrorCard({ mirror, revealed, onReveal }: { mirror: V6HeroMirror | null; revealed: boolean; onReveal: () => void }) {
  if (!mirror) return <EmptyState message="Hero Mirror is unavailable for this report." />;
  const eligible = mirror.share_eligible === true && mirror.status !== "suppressed" && mirror.status !== "unavailable";
  return <article className={styles.mirror}><div className={styles.mirrorArt} aria-hidden="true">◐</div>{revealed ? <div className={styles.mirrorResult}><span className={styles.eyebrow}>{firstNonEmpty(mirror.title, "Hero Mirror")}</span><h2 id="v6-beat-8-title">{firstNonEmpty(mirror.headline, mirror.hero_name ? `A mirror in ${mirror.hero_name}` : "Mirror result unavailable")}</h2><p>{firstNonEmpty(mirror.body, "")}</p><div className={styles.mirrorFacts}>{Object.entries(mirror.player_behavior ?? {}).map(([key, value]) => <div key={key}><span>{key}</span><strong>{value}</strong><small>{mirror.hero_behavior?.[key] ?? ""}</small></div>)}</div><p className={styles.eligibility}>{eligible ? "Eligible for a standalone share candidate." : firstNonEmpty(...(mirror.limitations ?? []), "Not eligible for standalone sharing.")}</p></div> : <div className={styles.lockedReveal}><span className={styles.eyebrow}>Hero Mirror</span><p>Reveal the server-qualified mirror when you are ready.</p><button className={styles.primaryButton} type="button" onClick={onReveal}>Reveal Hero Mirror</button></div>}</article>;
}

function ShareComposer({ report, selected, onSelect, onCopy, copied }: { report: V6Report; selected?: string; onSelect: (id: string) => void; onCopy: (candidate: { title?: string | null; headline?: string | null; body?: string | null }) => void; copied: boolean }) {
  const eligible = report.share_candidates.filter((candidate) => candidate.eligible === true && candidate.status !== "suppressed" && candidate.status !== "unavailable");
  return <section className={styles.shareComposer} aria-label="Eligible share-card composer"><div><span className={styles.eyebrow}>Share candidates</span><p>Only server-eligible cards appear here. Self-estimates are never used as evidence.</p></div>{eligible.length === 0 ? <EmptyState message="No standalone share card is eligible for this report." /> : <div className={styles.shareGrid}>{eligible.map((candidate) => { const id = shareCandidateId(candidate); const isSelected = selected === id; return <label className={isSelected ? styles.shareCandidateSelected : styles.shareCandidate} key={id}><input type="radio" name="v6-share-candidate" checked={isSelected} onChange={() => onSelect(id)} /><span><strong>{firstNonEmpty(candidate.title, recordText(candidate.payload, "title"), candidate.kind, "Share card")}</strong><small>{firstNonEmpty(candidate.headline, candidate.body, candidate.reason, recordText(candidate.payload, "reason"), "")}</small></span>{isSelected && <button className={styles.smallButton} type="button" onClick={(event) => { event.preventDefault(); onCopy(candidate); }}>{copied ? "Copied" : "Copy text"}</button>}</label>; })}</div>}</section>;
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
  return <div className={styles.resultNotice} role="status"><span className={styles.eyebrow}>Deep response</span><p>{firstNonEmpty(recordText(record, "message"), recordText(record, "status"), "Your diagnostic request was accepted.")}</p></div>;
}

function chooseStrongestFinding(findings: V6Finding[]): V6Finding | null {
  return findings.find((finding) => isPublished(finding) && (finding.confidence === "high" || finding.confidence === "moderate")) ?? findings.find(isPublished) ?? findings[0] ?? null;
}

function chooseSecondaryFinding(findings: V6Finding[], strongest: V6Finding | null): V6Finding | null {
  return findings.find((finding) => finding !== strongest && isPublished(finding)) ?? findings.find((finding) => finding !== strongest) ?? null;
}

function findFamily(findings: V6Finding[], family: string): V6Finding | null {
  return findings.find((finding) => `${finding.family} ${finding.key} ${finding.label ?? ""}`.toLowerCase().includes(family)) ?? null;
}

function isPublished(finding: V6Finding): boolean {
  if (finding.published === false) return false;
  return finding.status !== "suppressed" && finding.status !== "unavailable";
}

function recommendationChoices(report: V6Report, ...findings: Array<V6Finding | null>): V6Choice[] {
  const choices: V6Choice[] = [];
  for (const finding of findings) {
    const recommendation = finding?.recommendation;
    if (recommendation && typeof recommendation === "object") {
      const options = recommendation.options ?? [];
      if (options.length > 0) choices.push(...options);
      else choices.push({ id: recommendation.id ?? finding?.key ?? finding?.family, label: firstNonEmpty(recommendation.title, recommendation.label, recommendation.action, finding?.label, "Recommendation"), description: firstNonEmpty(recommendation.body, recommendation.context, "") });
    }
  }
  const beatOptions = storyPages(report).find((beat) => beat.kind === "recommendation" || beat.key === "recommendation")?.options ?? [];
  return uniqueChoices([...choices, ...beatOptions]);
}

function uniqueChoices(choices: V6Choice[]): V6Choice[] {
  const seen = new Set<string>();
  return choices.filter((choice) => { const id = choice.id ?? choice.key ?? choice.value ?? choice.label; if (seen.has(id)) return false; seen.add(id); return true; });
}

function storyPages(report: V6Report): V6StoryBeat[] {
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

function diagnosticQuestionId(question: V6Report["diagnostic_questions"][number]): string {
  return question.id ?? question.question_id ?? "";
}

function shareCandidateId(candidate: V6Report["share_candidates"][number]): string {
  return candidate.id ?? candidate.candidate_id ?? "";
}

function recommendationBody(recommendation: V6Finding["recommendation"]): string {
  if (!recommendation) return "";
  return typeof recommendation === "string" ? recommendation : firstNonEmpty(recommendation.body, recommendation.action, recommendation.context, recommendation.title);
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
    completed_beats: uniqueNumbers(state.completed_beats ?? []).filter((item) => item >= 0 && item < 9),
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

function beatLabel(id: BeatId): string {
  return { "self-estimate": "Estimate", "identity-reveal": "Identity", "pool-evolution": "Pool", "combat-expression": "Combat", "strongest-finding": "Finding", "secondary-finding": "Layers", recommendation: "Action", "hero-mirror": "Mirror", "deep-diagnostic": "Deep" }[id];
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
export { isFreeDnaReportV6 } from "./types";
export type { V6Report } from "./types";
export { ReportStoryV6 };
