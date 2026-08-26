"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { track } from "../../../../lib/analytics";
import {
  createInteractionSession, deleteInteractionSession, followUpInteractionSession,
  getInteractionSession, initialInteractionState, patchInteractionSession,
  readResumeFragment, resumeFragment, startDeepAnalysis, V6InteractionError,
  V6RevisionConflictError, withoutResumeFragment,
  type V6InteractionSession, type V6InteractionState,
} from "../../../../../lib/v6/interaction-client";
import type { V6Choice, V6DiagnosticQuestion, V6Finding, V6ShareCandidate } from "../types";
import { createArrivalData, ArrivalChapter, type ArrivalPhase } from "./chapters/arrival";
import { createHeroesData, HeroesChapter, type HeroesPhase } from "./chapters/heroes";
import { createPoolShapeData, PoolShapeChapter, type PoolShapePhase } from "./chapters/pool-shape";
import { createTransferData, TransferChapter } from "./chapters/transfer";
import { createPostLossData, PostLossChapter } from "./chapters/post-loss";
import { CombatExpressionChapter, createCombatExpressionData } from "./chapters/combat-expression/combat-expression-chapter";
import { SessionDriftChapter, createSessionDriftData } from "./chapters/session-drift/session-drift-chapter";
import { IdentityChapter } from "./chapters/identity/identity-chapter";
import { SynthesisChapter } from "./chapters/synthesis/synthesis-chapter";
import { PremiumChapter } from "./chapters/premium/premium-chapter";
import { ShareChapter } from "./chapters/share/share-chapter";
import { StoryProgress, StoryShell } from "./foundation";
import { OutcomeSequence } from "./outcomes/outcome-sequence";
import { OUTCOME_PHASES, type OutcomePhase } from "./outcomes/outcome-config";
import { shareCardType } from "./cards/share-card";
import { LEGACY_BEAT_IDS, clampLegacyBeat, legacyProgressCount, stepIndexForLegacyBeat, type LegacyBeatId } from "./story-navigation";
import type { StoryModel } from "./story-model";
import type { StoryStep } from "./story-sequence";
import styles from "./story-engine.module.css";

type SyncStatus = "idle" | "loading" | "saving" | "saved" | "resumed" | "deleted" | "conflict" | "error";

export default function StoryEngine({ model }: { model: StoryModel }) {
  const { report, sequence } = model;
  const [journey, setJourney] = useState<V6InteractionState>(() => initialInteractionState());
  const [syncStatus, setSyncStatus] = useState<SyncStatus>("idle");
  const [syncMessage, setSyncMessage] = useState("");
  const [conflictSession, setConflictSession] = useState<V6InteractionSession | null>(null);
  const [followUpResult, setFollowUpResult] = useState<unknown>(null);
  const [deepResult, setDeepResult] = useState<unknown>(null);
  const [deepLoading, setDeepLoading] = useState(false);
  const [shareMessage, setShareMessage] = useState("");
  const [downloadState, setDownloadState] = useState<"idle" | "downloading" | "saved" | "error">("idle");
  const sessionRef = useRef<V6InteractionSession | null>(null);
  const tokenRef = useRef<string | null>(null);
  const dirtyRef = useRef(false);
  const pendingStateRef = useRef<V6InteractionState | null>(null);
  const saveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const persistRef = useRef<(state: V6InteractionState) => void>(() => undefined);
  const currentIndex = resolveStepIndex(journey, sequence);
  const step = sequence[currentIndex] ?? sequence[0];
  const currentLegacyBeat = clampLegacyBeat(step?.legacyBeatIndex ?? journey.current_beat);

  const arrivalData = useMemo(() => createArrivalData(model), [model]);
  const heroesData = useMemo(() => createHeroesData(model), [model]);
  const poolData = useMemo(() => createPoolShapeData(model), [model]);
  const transferData = useMemo(() => createTransferData(model), [model]);
  const postLossData = useMemo(() => createPostLossData(model), [model]);
  const combatData = useMemo(() => createCombatExpressionData(model), [model]);
  const sessionData = useMemo(() => createSessionDriftData(model), [model]);
  const offeredQuestions = useMemo(() => report.diagnostic_questions.filter(questionIsOffered), [report.diagnostic_questions]);

  const schedulePersist = useCallback((state: V6InteractionState) => {
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current);
    saveTimerRef.current = setTimeout(() => persistRef.current(state), 350);
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
        setJourney(normalizeInteractionState(updated.state, sequence));
      } else {
        const created = await createInteractionSession(report.report_id ?? "", state);
        sessionRef.current = created.session;
        tokenRef.current = created.token;
        if (typeof window !== "undefined") window.history.replaceState(null, document.title, `${window.location.pathname}${window.location.search}${resumeFragment(created.session.session_id, created.token)}`);
        setJourney(normalizeInteractionState(created.session.state, sequence));
      }
      dirtyRef.current = false;
      setConflictSession(null);
      setSyncStatus("saved");
      setSyncMessage("Journey saved. You can resume it from this link.");
    } catch (error) {
      if (error instanceof V6RevisionConflictError) {
        let latest = error.latest;
        if (!latest && existing && token) latest = await getInteractionSession(existing.session_id, token).catch(() => null);
        if (latest) sessionRef.current = latest;
        setConflictSession(latest ?? existing);
        setSyncStatus("conflict");
        setSyncMessage("This journey changed in another tab. Choose which version to keep.");
      } else {
        setSyncStatus("error");
        setSyncMessage(error instanceof V6InteractionError ? error.message : "The journey could not be saved. You can keep playing and retry.");
      }
    }
  }, [report.report_id, sequence]);
  persistRef.current = (state) => void persist(state);

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
    void getInteractionSession(resume.sessionId, resume.token).then((session) => {
      sessionRef.current = session;
      setJourney(normalizeInteractionState(session.state, sequence));
      dirtyRef.current = false;
      setSyncStatus("resumed");
      setSyncMessage("Saved journey resumed.");
    }).catch((error: unknown) => {
      tokenRef.current = null;
      setSyncStatus("error");
      setSyncMessage(error instanceof V6InteractionError && error.status === 404 ? "This saved journey has expired." : "The saved journey could not be resumed.");
    });
  }, [sequence]);

  useEffect(() => () => { if (saveTimerRef.current) clearTimeout(saveTimerRef.current); }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement || event.target instanceof HTMLSelectElement) return;
      if (event.key === "ArrowRight") { event.preventDefault(); nextStep(); }
      if (event.key === "ArrowLeft") { event.preventDefault(); previousStep(); }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  });

  function setStep(nextIndex: number, complete = false): void {
    const target = sequence[clampStep(nextIndex, sequence.length)];
    if (!target) return;
    updateJourney((state) => ({
      ...state,
      current_beat: target.legacyBeatIndex,
      completed_beats: complete ? uniqueNumbers([...state.completed_beats, target.legacyBeatIndex]).filter((item) => !state.skipped_beats.includes(item)) : state.completed_beats,
      ui_state: { ...state.ui_state, story_step_index: clampStep(nextIndex, sequence.length), story_step_id: target.id },
    }));
  }

  function nextStep(): void {
    if (!step) return;
    if (step.chapter === "identity" && !journey.ui_state.identity_revealed) return;
    setStep(currentIndex + 1, currentIndex >= 0 && sequence[currentIndex + 1]?.chapter !== step.chapter);
  }

  function previousStep(): void { setStep(currentIndex - 1); }

  function skipChapter(): void {
    if (!step) return;
    const next = sequence.findIndex((candidate, index) => index > currentIndex && candidate.chapter !== step.chapter);
    updateJourney((state) => ({ ...state, current_beat: next >= 0 ? sequence[next].legacyBeatIndex : state.current_beat, skipped_beats: uniqueNumbers([...state.skipped_beats, step.legacyBeatIndex]), completed_beats: state.completed_beats.filter((item) => item !== step.legacyBeatIndex), ui_state: next >= 0 ? { ...state.ui_state, story_step_index: next, story_step_id: sequence[next].id } : state.ui_state }));
    track("report.v6.beat_skipped.v1", { beat: step.legacyBeatId });
  }

  function chooseUserAnswer(field: "identity_estimate" | "hero_pool_prediction" | "combat_expression_estimate", choice: V6Choice): void {
    const value = choice.id ?? choice.key ?? choice.value ?? choice.label;
    updateJourney((state) => ({ ...state, user_reported: { ...state.user_reported, [field]: value } }));
    track("report.v6.user_reported_selected.v1", { field, selected: true });
  }

  function revealIdentity(): void {
    updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, identity_revealed: true } }));
    track("report.v6.observed_reveal.v1", { field: "identity_revealed" });
  }

  function selectRecommendation(id: string): void {
    updateJourney((state) => ({ ...state, user_reported: { ...state.user_reported, recommendation_id: id } }));
    track("report.v6.recommendation_selected.v1", { has_selection: true });
  }

  async function commitRecommendation(): Promise<void> {
    const recommendationId = journey.user_reported.recommendation_id;
    if (!recommendationId) return;
    const committedState = { ...journey, user_reported: { ...journey.user_reported, commitment: { recommendation_id: recommendationId, target_games: 5 as const, started_at: new Date().toISOString() } } };
    dirtyRef.current = true;
    pendingStateRef.current = null;
    setJourney(committedState);
    track("report.v6.five_game_commitment.v1", { target_games: 5 });
    await persist(committedState);
  }

  async function checkFollowUp(): Promise<void> {
    const session = sessionRef.current;
    const token = tokenRef.current;
    if (!session || !token) { setSyncMessage("Save this journey before checking five-game progress."); return; }
    setSyncStatus("saving");
    try {
      const result = await followUpInteractionSession(session.session_id, token);
      setFollowUpResult(result);
      updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, follow_up: followUpState(result) } }));
      setSyncStatus("saved");
      setSyncMessage("Five-game progress updated from the server.");
    } catch (error) { setSyncStatus("error"); setSyncMessage(error instanceof V6InteractionError ? error.message : "Five-game progress is not available yet."); }
  }

  async function chooseDiagnostic(): Promise<void> {
    const questionId = journey.ui_state.diagnostic_question_id;
    if (!questionId) return;
    setDeepLoading(true);
    setDeepResult(null);
    try {
      const result = await startDeepAnalysis(report.report_id ?? "", questionId, sessionRef.current?.session_id, tokenRef.current);
      setDeepResult(result);
      setSyncMessage("Your diagnostic question was sent to Deep.");
      track("report.v6.deep_question_submitted.v1", { selected: true });
    } catch (error) { setSyncMessage(error instanceof V6InteractionError ? error.message : "Deep could not start this diagnostic yet."); }
    finally { setDeepLoading(false); }
  }

  function chooseDiagnosticQuestion(id: string): void { updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, diagnostic_question_id: id } })); }

  async function copyShareCandidate(candidate: V6ShareCandidate): Promise<void> {
    const text = [candidate.title, candidate.headline, candidate.body].filter(Boolean).join("\n\n");
    if (!text || !navigator.clipboard) return;
    await navigator.clipboard.writeText(text);
    setShareMessage("Text copied.");
  }

  async function shareCandidate(candidate: V6ShareCandidate): Promise<void> {
    const url = cardUrl(candidate);
    try {
      if (navigator.share) await navigator.share({ title: candidate.title ?? "My Dota DNA", url: url || window.location.href });
      else if (navigator.clipboard) { await navigator.clipboard.writeText(url || window.location.href); setShareMessage("Link copied."); }
      else setShareMessage("Sharing is not available in this browser.");
    } catch (error) { if ((error as DOMException).name !== "AbortError") setShareMessage("Sharing is not available in this browser."); }
  }

  function downloadCandidate(candidate: V6ShareCandidate): void {
    const url = cardUrl(candidate);
    if (!url) return;
    setDownloadState("downloading");
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `dota-dna-${shareCardType(candidate) ?? "card"}.svg`;
    anchor.click();
    setDownloadState("saved");
    setShareMessage("Card download started.");
  }

  async function saveJourney(): Promise<void> { dirtyRef.current = true; if (saveTimerRef.current) clearTimeout(saveTimerRef.current); await persist(journey); }
  async function deleteJourney(): Promise<void> {
    const session = sessionRef.current; const token = tokenRef.current;
    if (session && token) { try { await deleteInteractionSession(session.session_id, token); } catch { setSyncStatus("error"); setSyncMessage("The saved journey could not be deleted. Try again."); return; } }
    sessionRef.current = null; tokenRef.current = null; dirtyRef.current = false; withoutResumeFragment(); setJourney(initialInteractionState()); setSyncStatus("deleted"); setSyncMessage("Saved journey deleted from this device.");
  }
  function useServerVersion(): void { if (!conflictSession) return; sessionRef.current = conflictSession; setJourney(normalizeInteractionState(conflictSession.state, sequence)); dirtyRef.current = false; setConflictSession(null); setSyncStatus("saved"); setSyncMessage("Loaded the latest saved journey."); }
  function keepLocalVersion(): void { if (!conflictSession) return; sessionRef.current = conflictSession; setConflictSession(null); dirtyRef.current = true; setSyncMessage("Your local version is ready to save over the latest version."); schedulePersist(journey); }

  return (
    <StoryShell label={`Free DNA ${report.schema_version === "free-dna-report-6.1.0" ? "V6.1" : "V6"} identity report`} progress={<StoryProgress active={step?.progressIndex ?? 0} />} action={<Navigation current={currentIndex} total={sequence.length} onPrevious={previousStep} onNext={step?.chapter === "identity" && !journey.ui_state.identity_revealed ? revealIdentity : nextStep} reveal={step?.chapter === "identity" && !journey.ui_state.identity_revealed} disabledNext={!step} />}>
      <div className={styles.toolbar}><span>{step ? `${chapterLabel(step.chapter)} · ${step.phase + 1} / ${step.phaseCount}` : "Story"}</span><span role="status" aria-live="polite">{syncMessage || syncLabel(syncStatus)}</span><button type="button" onClick={() => void saveJourney()}>{sessionRef.current ? "Save now" : "Save journey"}</button>{sessionRef.current && <button type="button" onClick={() => void deleteJourney()}>Delete saved journey</button>}</div>
      {conflictSession && <aside className={styles.conflict} role="alert"><strong>This saved journey has a newer version.</strong><span>Choose which version to keep.</span><button type="button" onClick={useServerVersion}>Load latest</button><button type="button" onClick={keepLocalVersion}>Keep my version</button></aside>}
      <div className={styles.currentStep}>{step ? renderStep(step) : <p>No story steps are available for this report.</p>}</div>
      {step?.skippable && <button className={styles.skip} type="button" onClick={skipChapter}>Skip chapter</button>}
      {shareMessage && <p className={styles.status} role="status" aria-live="polite">{shareMessage}</p>}
    </StoryShell>
  );

  function renderStep(current: StoryStep) {
    const outcome = findingForChapter(model, current.chapter);
    const chapter = (() => {
      switch (current.chapter) {
        case "arrival": return <><ArrivalChapter data={arrivalData} phase={current.phase as ArrivalPhase} /><Reflection model={model} selected={journey.user_reported.identity_estimate} onSelect={(choice) => chooseUserAnswer("identity_estimate", choice)} /></>;
        case "heroes": return <HeroesChapter data={heroesData} phase={current.phase as HeroesPhase} />;
        case "pool-shape": return <><PoolShapeChapter data={poolData} phase={current.phase as PoolShapePhase} />{outcome && <FindingOutcome finding={outcome} phase={current.phase} />}</>;
        case "transfer": return <><TransferChapter data={transferData} phase={current.phase as 0|1|2|3|4|5|6|7|8} />{outcome && <FindingOutcome finding={outcome} phase={current.phase} />}</>;
        case "post-loss": return <><PostLossChapter data={postLossData} phase={current.phase as 0|1|2|3|4|5|6|7|8} />{outcome && <FindingOutcome finding={outcome} phase={current.phase} />}</>;
        case "combat-expression": return <><CombatExpressionChapter data={combatData} phase={current.phase as 0|1|2|3|4|5|6|7|8|9} />{outcome && <FindingOutcome finding={outcome} phase={current.phase} />}</>;
        case "session-drift": return <><SessionDriftChapter data={sessionData} phase={current.phase as 0|1|2|3|4|5|6|7|8} />{outcome && <FindingOutcome finding={outcome} phase={current.phase} />}</>;
        case "synthesis": return <SynthesisChapter elements={model.elements} identity={model.identity} phase={current.phase} />;
        case "identity": return <IdentityChapter identity={model.identity} phase={journey.ui_state.identity_revealed ? current.phase : 0} />;
        case "premium": return <><PremiumChapter identity={model.identity} questions={offeredQuestions} phase={current.phase} selectedQuestion={journey.ui_state.diagnostic_question_id} onSelectQuestion={chooseDiagnosticQuestion} onStart={() => void chooseDiagnostic()} loading={deepLoading} />{offeredQuestions.length === 0 && <p className={styles.status} role="status">No evidence-qualified Deep question was offered for this report.</p>}{deepResult != null && <p className={styles.status} role="status">Deep response received.</p>}<RecommendationPanel /></>;
        case "share": return <ShareChapter candidates={model.share} phase={current.phase} selectedId={journey.ui_state.selected_share_candidate} onSelect={(id) => updateJourney((state) => ({ ...state, ui_state: { ...state.ui_state, selected_share_candidate: id } }))} onShare={(candidate) => void shareCandidate(candidate)} onDownload={downloadCandidate} downloadState={downloadState} />;
      }
    })();
    return <div key={current.chapter} data-story-step={current.id} className={styles.step}>{chapter}</div>;
  }

  function RecommendationPanel() {
    const recommendations = recommendationChoices(report.findings);
    const selected = journey.user_reported.recommendation_id;
    if (recommendations.length === 0) return null;
    return <section className={styles.recommendations} aria-label="Recommendation chooser"><span>Try this next</span>{recommendations.map((choice) => { const id = choice.id ?? choice.key ?? choice.value ?? choice.label; return <label key={id}><input type="radio" name="story-recommendation" checked={selected === id} onChange={() => selectRecommendation(id)} />{choice.label}</label>; })}<button type="button" disabled={!selected || Boolean(journey.user_reported.commitment)} onClick={() => void commitRecommendation()}>{journey.user_reported.commitment ? "Check-in saved" : "Set a five-game check-in"}</button>{journey.user_reported.commitment && <button type="button" onClick={() => void checkFollowUp()}>Check progress</button>}{Boolean(followUpResult) && <span role="status">Five-game progress updated.</span>}</section>;
  }
}

function Navigation({ current, total, onPrevious, onNext, reveal = false, disabledNext }: { current: number; total: number; onPrevious: () => void; onNext: () => void; reveal?: boolean; disabledNext: boolean }) {
  return <div className={styles.navigation}><button type="button" onClick={onPrevious} disabled={current <= 0}>Previous</button><span aria-live="polite">Step {Math.max(1, current + 1)} of {total}</span><button type="button" onClick={onNext} disabled={disabledNext || current >= total - 1}>{reveal ? "Reveal observed shape" : current >= total - 1 ? "Finish" : "Continue"}</button></div>;
}

function Reflection({ model, selected, onSelect }: { model: StoryModel; selected?: string; onSelect: (choice: V6Choice) => void }) {
  const choices = model.beats[0]?.options ?? model.identity.options ?? [];
  if (choices.length === 0) return null;
  return <fieldset className={styles.reflection}><legend>Before you look closer, which description feels most familiar?</legend>{choices.map((choice) => { const value = choice.id ?? choice.key ?? choice.value ?? choice.label; return <label key={value}><input type="radio" name="story-reflection" checked={selected === value} onChange={() => onSelect(choice)} />{choice.label}</label>; })}<p>Your answer is saved as your own reflection. It never changes the observed report.</p></fieldset>;
}

function FindingOutcome({ finding, phase }: { finding: V6Finding; phase: number }) {
  const outcomePhase: OutcomePhase = OUTCOME_PHASES[Math.min(OUTCOME_PHASES.length - 1, phase < 1 ? 0 : phase < 4 ? 1 : phase < 7 ? 2 : 3)];
  return <OutcomeSequence outcome={finding} phase={outcomePhase} />;
}

function findingForChapter(model: StoryModel, chapter: StoryStep["chapter"]): V6Finding | null {
  return chapter === "pool-shape" ? model.pool.finding : chapter === "transfer" ? model.transfer.finding : chapter === "post-loss" ? model.postLoss.finding : chapter === "combat-expression" ? model.combat.finding : chapter === "session-drift" ? model.session.finding : null;
}

function resolveStepIndex(state: V6InteractionState, sequence: readonly StoryStep[]): number {
  if (sequence.length === 0) return 0;
  const id = state.ui_state.story_step_id;
  if (id) { const byId = sequence.findIndex((step) => step.id === id); if (byId >= 0) return byId; }
  const index = state.ui_state.story_step_index;
  if (typeof index === "number" && Number.isFinite(index)) return clampStep(index, sequence.length);
  return stepIndexForLegacyBeat(sequence, state.current_beat);
}

function normalizeInteractionState(state: V6InteractionState, sequence: readonly StoryStep[]): V6InteractionState {
  const safeState = Object.fromEntries(Object.entries(state).filter(([key]) => !["observed", "computed", "evidence", "analytical_truth"].includes(key))) as Partial<V6InteractionState>;
  const next = { ...initialInteractionState(), ...safeState, current_beat: clampLegacyBeat(state.current_beat), completed_beats: uniqueNumbers(state.completed_beats ?? []).filter((item) => item >= 0 && item < LEGACY_BEAT_IDS.length && !(state.skipped_beats ?? []).includes(item)), skipped_beats: uniqueNumbers(state.skipped_beats ?? []).filter((item) => item >= 0 && item < LEGACY_BEAT_IDS.length), user_reported: { ...(state.user_reported ?? {}) }, ui_state: { ...(state.ui_state ?? {}) } };
  const index = resolveStepIndex(next, sequence);
  const step = sequence[index];
  next.ui_state.story_step_index = index;
  next.ui_state.story_step_id = step?.id;
  return next;
}

function clampStep(index: number, length: number): number { return Math.max(0, Math.min(Math.max(0, length - 1), Number.isFinite(index) ? Math.round(index) : 0)); }
function uniqueNumbers(values: number[]): number[] { return [...new Set(values)]; }
function chapterLabel(chapter: StoryStep["chapter"]): string { return chapter.replaceAll("-", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
function syncLabel(status: SyncStatus): string { return { idle: "", loading: "Resuming…", saving: "Saving…", saved: "Saved", resumed: "Resumed", deleted: "Deleted", conflict: "Needs review", error: "Not saved" }[status]; }
function questionIsOffered(question: V6DiagnosticQuestion): boolean { const confidence = question.confidence?.toLowerCase(); return question.offered !== false && question.available !== false && question.eligibility !== "suppressed" && question.eligibility !== "unavailable" && (confidence === "high" || confidence === "moderate") && (question.evidence_refs?.length ?? 0) > 0 && (question.blocking_confounders?.length ?? 0) === 0; }
function recommendationChoices(findings: V6Finding[]): V6Choice[] { const seen = new Set<string>(); const choices: V6Choice[] = []; for (const finding of findings) { const recommendation = finding.recommendation ?? finding.claim_contract?.recommendation; if (!recommendation || typeof recommendation !== "object") continue; const options = recommendation.options ?? []; const candidates = options.length > 0 ? options : [{ id: recommendation.recommendation_id ?? recommendation.id ?? finding.key ?? finding.family, label: recommendation.title ?? recommendation.label ?? recommendation.instruction ?? finding.label ?? "Recommendation", description: recommendation.body ?? recommendation.instruction }]; for (const choice of candidates) { const id = choice.id ?? choice.key ?? choice.value ?? choice.label; if (!seen.has(id)) { seen.add(id); choices.push(choice); } } } return choices; }
function findingForShareType(candidate: V6ShareCandidate): string { return shareCardType(candidate) ?? "card"; }
function cardUrl(candidate: V6ShareCandidate): string { const type = findingForShareType(candidate); const reportId = typeof window !== "undefined" ? window.location.pathname.split("/").filter(Boolean).pop() : ""; return reportId && (candidate.id || candidate.candidate_id) ? `/v1/reports/${encodeURIComponent(reportId)}/share/${type === "finding" ? "strongest-finding" : type}?show_name=false&show_avatar=false` : ""; }
function followUpState(value: unknown): V6InteractionState["ui_state"]["follow_up"] { const record = value && typeof value === "object" ? value as Record<string, unknown> : {}; return { eligible_games: typeof record.eligible_games === "number" ? record.eligible_games : 0, target_games: 5, status: typeof record.status === "string" ? record.status : undefined }; }

export { LEGACY_BEAT_IDS as BEAT_IDS, StoryEngine };
